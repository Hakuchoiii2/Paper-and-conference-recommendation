"""Schema 2.0 gates: provenance, exposure links, hidden labels and per-case cutoffs."""
import collections
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_corpus import read_jsonl
from data.experiment_common import (normalized_weights,retrieval_grade,session_grade,validate_sampling,validate_simulator)
from download_sources import ROOT,sha256
from experiment_io import (CONTRACT_VERSION,FACETS,FILES,check_users,concept_sets,generator_files,input_paths,
                           load_silver,load_users,output_paths,project_path)
from validate_all import require,validate_time

def fields(row, expected, where):
    require(isinstance(row,dict) and set(row) == set(expected),f'{where}: wrong fields / observable schema')

def check_splits(records, splits, id_field):
    require(set(splits) == {'train','dev','test'},'Wrong split names')
    assigned = {}
    for side,ids in splits.items():
        require(isinstance(ids,list),'Split IDs must be lists')
        for key in ids:
            require(key not in assigned,'Duplicate split ID')
            assigned[key] = side
    require(set(assigned) == {r[id_field] for r in records},'Split IDs differ from queries')
    anchors = {}
    for row in records:
        require(anchors.setdefault(row['query_paper_id'],assigned[row[id_field]]) == assigned[row[id_field]],
                'Query anchor leaks across splits')

def check_profile(row, facets, temporal=False):
    expected = {'user_id','latent_preferences','facet_importance'}
    if temporal:
        expected |= {'period','start_timestamp','end_timestamp'}
    fields(row,expected,'hidden profile')
    preferences = row['latent_preferences']
    require(set(preferences) == set(FACETS),'Wrong profile facets')
    vocabulary = {f:set().union(*(r[f] for r in facets.values())) for f in FACETS}
    for f,values in preferences.items():
        require(isinstance(values,dict),'Profile concepts must be a map')
        require(all(c in vocabulary[f] and type(v) in (int,float) and math.isfinite(v) and -1 <= v <= 1
                    for c,v in values.items()),'Invalid latent preference')
    normalized_weights(row['facet_importance'])
    require(math.isclose(sum(row['facet_importance'].values()),1,abs_tol=1e-8),'Importance must sum to one')

def check_logs(events, queries, exposures, users, facets, exposure_size):
    by_query,by_exposure = {},{}
    for row in queries:
        fields(row,{'query_id','user_id','session_id','text','parent_query_id','timestamp'},'search')
        require(row['user_id'] in users and isinstance(row['text'],str) and row['text'].strip(),'Invalid search user/text')
        require(all(isinstance(row[k],str) and row[k] for k in ('query_id','session_id')),'Invalid search IDs')
        validate_time(row['timestamp'])
        key = row['query_id']
        require(key not in by_query or by_query[key] == row,'Conflicting duplicate query')
        by_query[key] = row
    for row in by_query.values():
        parent = row['parent_query_id']
        if parent is not None:
            require(parent in by_query,'Unknown parent query')
            old = by_query[parent]
            require((old['user_id'],old['session_id']) == (row['user_id'],row['session_id'])
                    and validate_time(old['timestamp']) < validate_time(row['timestamp']),'Invalid query reformulation order')
    for row in exposures:
        fields(row,{'exposure_id','user_id','session_id','query_id','paper_ids','timestamp'},'exposure')
        require(row['user_id'] in users,'Unknown exposure user')
        ids = row['paper_ids']
        require(isinstance(ids,list) and len(ids) == exposure_size and len(set(ids)) == len(ids)
                and all(pid in facets for pid in ids),'Invalid exposed paper IDs')
        require(all(isinstance(row[k],str) and row[k] for k in ('exposure_id','session_id')),'Invalid exposure IDs')
        time = validate_time(row['timestamp'])
        if row['query_id'] is not None:
            require(row['query_id'] in by_query,'Unknown exposure query')
            q = by_query[row['query_id']]
            require((q['user_id'],q['session_id']) == (row['user_id'],row['session_id'])
                    and validate_time(q['timestamp']) < time,'Query/exposure time or user mismatch')
        key = row['exposure_id']
        require(key not in by_exposure or by_exposure[key] == row,'Conflicting duplicate exposure')
        by_exposure[key] = row
    seen,last = {},{}
    for row in events:
        fields(row,{'user_id','paper_id','interaction_type','timestamp','session_id','exposure_id'},'interaction')
        require(row['user_id'] in users and row['paper_id'] in facets,'Unknown interaction user/paper')
        require(row['interaction_type'] in {'dislike','view','click','save','like'},'Invalid interaction type')
        require(row['exposure_id'] in by_exposure,'Unknown interaction exposure')
        x = by_exposure[row['exposure_id']]
        time = validate_time(row['timestamp'])
        require((x['user_id'],x['session_id']) == (row['user_id'],row['session_id'])
                and row['paper_id'] in x['paper_ids'] and validate_time(x['timestamp']) < time,
                'Interaction exposure membership/time mismatch')
        key = row['user_id'],row['session_id'],row['paper_id'],row['timestamp']
        require(key not in seen,'Duplicate interaction')
        seen[key] = row
        key = row['user_id'],row['session_id']
        require(key not in last or last[key] < time,'Interaction time order')
        last[key] = time

def check_cases(cases, facets, users, schema, candidate_count=None):
    by_id = {}
    for row in cases:
        fields(row,schema,'observable case')
        require(isinstance(row['case_id'],str) and row['case_id'] and row['case_id'] not in by_id,'Duplicate/invalid case ID')
        require(row['user_id'] in users,'Unknown case user')
        validate_time(row['cutoff'])
        ids = row['candidate_ids']
        require(isinstance(ids,list) and ids and len(ids) == len(set(ids)) and all(pid in facets for pid in ids),
                'Invalid case candidates')
        if candidate_count is not None:
            require(len(ids) == candidate_count,'Wrong candidate quota')
        if 'query_paper_id' in row:
            require(row['query_paper_id'] in facets and row['query_paper_id'] not in ids,'Invalid/self anchor')
        by_id[row['case_id']] = row
    return by_id

def check_b(observed, truth, facets, config, report):
    validate_sampling(config,'num_queries','candidates_per_query')
    require(config['label_rule_version'] == 'weighted_overlap_v2','Unsupported B label rule')
    require(type(config['positive_grade']) in (int,float) and 0 < config['positive_grade'] <= 2,'Invalid positive grade')
    weights = normalized_weights(config['fixed_weights'])
    records = observed['retrieval_queries.jsonl']
    pairs = {}
    query_ids,anchors = set(),set()
    for row in records:
        fields(row,{'query_id','query_paper_id','candidate_ids'},'retrieval query')
        require(row['query_paper_id'] in facets,'Unknown query anchor')
        require(isinstance(row['query_id'],str) and row['query_id'] and row['query_id'] not in query_ids
                and row['query_paper_id'] not in anchors,'Duplicate/invalid retrieval query ID or anchor')
        query_ids.add(row['query_id']); anchors.add(row['query_paper_id'])
        ids = row['candidate_ids']
        require(len(ids) == config['candidates_per_query'] and len(set(ids)) == len(ids)
                and row['query_paper_id'] not in ids and all(pid in facets for pid in ids),'Invalid retrieval candidates')
        for pid in ids:
            key = row['query_id'],pid
            require(key not in pairs,'Duplicate retrieval case')
            pairs[key] = retrieval_grade(facets[row['query_paper_id']],facets[pid],weights)
    seen = set()
    for row in truth['retrieval_labels.jsonl']:
        fields(row,{'query_id','candidate_id','relevance'},'retrieval label')
        key = row['query_id'],row['candidate_id']
        require(key in pairs and key not in seen and type(row['relevance']) in (int,float)
                and math.isfinite(row['relevance']) and math.isclose(row['relevance'],pairs[key]),
                'Retrieval relevance label violates rule')
        seen.add(key)
    require(seen == set(pairs),'Missing retrieval labels')
    seen = set()
    for row in truth['label_provenance.jsonl']:
        fields(row,{'query_id','candidate_id','label_source','rule_version'},'label provenance')
        key = row['query_id'],row['candidate_id']
        require(key in pairs and key not in seen and row['label_source'] == 'synthetic_rule'
                and row['rule_version'] == config['label_rule_version'],'Invalid label provenance')
        seen.add(key)
    require(seen == set(pairs),'Missing provenance')
    check_splits(records,observed['splits.json'],'query_id')
    require(report['shortfall'] == config['num_queries'] - len(records)
            and report['actual_pairs'] == len(pairs),'Wrong B report quota')
    for row in records:
        grades = [pairs[row['query_id'],pid] for pid in row['candidate_ids']]
        require(any(v >= config['positive_grade'] for v in grades)
                and any(v < config['positive_grade'] for v in grades),'B needs high/low relevance candidates')

def check_behavior(experiment, observed, truth, facets, config, report, shared_users=None):
    users = observed['users.jsonl'] if experiment == 'c' else shared_users
    check_users(users)
    ids = {u['user_id'] for u in users}
    history,future = observed['interactions_train.jsonl'],truth['interactions_test.jsonl']
    # E's periods 2/3 occur in both storage partitions for rolling evaluation; require identical copies.
    merged = {}
    for row in history + future:
        key = row['user_id'],row['session_id'],row['paper_id'],row['timestamp']
        require(key not in merged or merged[key] == row,'Conflicting rolling feedback')
        merged[key] = row
    check_logs(list(merged.values()),observed['search_events.jsonl'] + truth['search_events_test.jsonl'],
               observed['exposures.jsonl'] + truth['exposures_test.jsonl'],ids,facets,config['exposure_size'])
    profiles = truth['latent_user_profiles.jsonl' if experiment == 'c' else 'temporal_profiles.jsonl']
    by_profile = {}
    boundaries = [validate_time(t) for t in config['period_boundaries']] if experiment == 'e' else None
    for row in profiles:
        check_profile(row,facets,experiment == 'e')
        require(row['user_id'] in ids,'Unknown profile user')
        key = row['user_id'],row.get('period',0)
        require(key not in by_profile,'Duplicate latent profile')
        if boundaries:
            require(type(row['period']) is int and 1 <= row['period'] <= 4,'Invalid profile period')
            p = row['period']
            require(validate_time(row['start_timestamp']) == boundaries[p-1]
                    and validate_time(row['end_timestamp']) == boundaries[p],'Profile period boundaries differ')
        by_profile[key] = row
    periods = (1,2,3,4) if boundaries else (0,)
    require(set(by_profile) == {(u,p) for u in ids for p in periods},'Missing latent profiles')
    schema = {'case_id','user_id','candidate_ids','cutoff'} | ({'period'} if boundaries else set())
    cases = check_cases(observed['cases.jsonl'],facets,ids,schema,
                        config['events_per_user_per_period'] if boundaries else
                        config['events_per_user'] - config['history_events_per_user'])
    expected = len(ids)*3 if boundaries else len(ids)
    require(len(cases) == expected,'Wrong behavior case quota')
    user_periods = set()
    for case in cases.values():
        user,cutoff = case['user_id'],validate_time(case['cutoff'])
        period = case.get('period',0)
        require((user,period) not in user_periods,'Duplicate user/period case')
        user_periods.add((user,period))
        if boundaries:
            require(type(period) is int and 2 <= period <= 4 and cutoff == boundaries[period-1],'Wrong rolling cutoff')
            judged = [r for r in future if r['user_id'] == user and cutoff <= validate_time(r['timestamp']) < boundaries[period]]
        else:
            judged = [r for r in future if r['user_id'] == user]
            require(sum(r['user_id'] == user for r in history) == config['history_events_per_user'],
                    'Wrong C history quota')
            for name in ('interactions_train.jsonl','search_events.jsonl','exposures.jsonl'):
                require(all(validate_time(r['timestamp']) < cutoff for r in observed[name] if r['user_id'] == user),
                        'Future event leaked into C history')
        require(set(case['candidate_ids']) == {r['paper_id'] for r in judged} and len(judged) == len(case['candidate_ids'])
                and all(validate_time(r['timestamp']) >= cutoff for r in judged),'Holdout candidates/time differ')
    if boundaries:
        metadata = truth['period_metadata.json']
        fields(metadata,{'groups','boundaries','drift_coefficients'},'period metadata')
        require(set(metadata['groups']) == ids and set(metadata['groups'].values()) <= {'stable','drift'},
                'Invalid E groups')
        require(metadata['boundaries'] == config['period_boundaries']
                and metadata['drift_coefficients'] == config['drift_coefficients'],'Wrong E schedule')
        require(sum(v == 'stable' for v in metadata['groups'].values()) == int(len(ids)*config['stable_fraction']),
                'Wrong stable quota')
        for user,group in metadata['groups'].items():
            old,new = by_profile[user,1],by_profile[user,3]
            for period in periods:
                row = by_profile[user,period]
                coefficient = 0 if group == 'stable' else config['drift_coefficients'][period-1]
                for f in FACETS:
                    concepts = old['latent_preferences'][f].keys() | new['latent_preferences'][f].keys()
                    expected_p = {c:(1-coefficient)*old['latent_preferences'][f].get(c,0)
                                  + coefficient*new['latent_preferences'][f].get(c,0) for c in concepts}
                    actual = row['latent_preferences'][f]
                    require(all(math.isclose(actual.get(c,0),expected_p[c],abs_tol=1e-8) for c in concepts)
                            and set(actual) <= concepts,'Temporal preference interpolation differs')
                    expected_w = (1-coefficient)*old['facet_importance'][f] + coefficient*new['facet_importance'][f]
                    require(math.isclose(row['facet_importance'][f],expected_w,abs_tol=1e-8),'Temporal importance differs')
            if group == 'drift':
                require(old['latent_preferences'] != new['latent_preferences'],'Drift profile did not change')
        for name in ('interactions_train.jsonl','search_events.jsonl','exposures.jsonl'):
            require(all(boundaries[0] <= validate_time(r['timestamp']) < boundaries[3] for r in observed[name]),
                    'Future event leaked into E history')
        for user in ids:
            for period in periods:
                require(sum(r['user_id'] == user and boundaries[period-1] <= validate_time(r['timestamp']) < boundaries[period]
                            for r in merged.values()) == config['events_per_user_per_period'],'Wrong E period quota')
        require(report['group_counts'] == dict(collections.Counter(metadata['groups'].values())),'Wrong E group report')
    else:
        require(len(users) == config['num_users'],'Wrong C user quota')
    require(report['shortfall'] == 0 and report['actual_users'] == len(ids)
            and report['actual_events'] == (len(ids)*4*config['events_per_user_per_period'] if boundaries else
                                           len(history)+len(future)),'Wrong behavior report counts')

def check_d(observed, truth, facets, config, report, users):
    ids = {u['user_id'] for u in users}
    cases = check_cases(observed['sessions.jsonl'],facets,ids,
                        {'case_id','user_id','query_paper_id','context_facet','candidate_ids','cutoff'},config['candidates_per_case'])
    intents = {}
    for row in truth['session_intents.jsonl']:
        fields(row,{'case_id','focus_facet','directions','facet_importance','query_mode'},'hidden session intent')
        require(row['case_id'] in cases and row['case_id'] not in intents,'Unknown/duplicate session intent')
        require(row['focus_facet'] in FACETS and cases[row['case_id']]['context_facet'] in FACETS
                and row['focus_facet'] != cases[row['case_id']]['context_facet'] and set(row['directions']) == set(FACETS)
                and set(row['directions'].values()) <= {'similar','different','ignore'}
                and row['query_mode'] in {'clear','ambiguous','none'},'Invalid session direction')
        expected = dict.fromkeys(FACETS,'ignore')
        expected[cases[row['case_id']]['context_facet']] = 'similar'
        expected[row['focus_facet']] = row['directions'][row['focus_facet']]
        require(expected == row['directions'] and row['directions'][row['focus_facet']] != 'ignore','Invalid active intent')
        normalized_weights(row['facet_importance'])
        expected_weights = dict.fromkeys(FACETS,0.0)
        expected_weights[cases[row['case_id']]['context_facet']] = .6
        expected_weights[row['focus_facet']] = .4
        require(all(math.isclose(row['facet_importance'][f],expected_weights[f],abs_tol=1e-8) for f in FACETS),
                'Session importance differs from simulator')
        require(facets[cases[row['case_id']]['query_paper_id']][row['focus_facet']]
                and facets[cases[row['case_id']]['query_paper_id']][cases[row['case_id']]['context_facet']],
                'Session anchor lacks active facet evidence')
        intents[row['case_id']] = row
    require(set(intents) == set(cases),'Missing session intent')
    check_logs(observed['interactions_train.jsonl'],observed['search_events.jsonl'],observed['exposures.jsonl'],
               ids,facets,2)
    for name in ('interactions_train.jsonl','search_events.jsonl','exposures.jsonl'):
        for row in observed[name]:
            require(row['session_id'] in cases and row['user_id'] == cases[row['session_id']]['user_id']
                    and validate_time(row['timestamp']) < validate_time(cases[row['session_id']]['cutoff']),
                    'Session observation user/cutoff mismatch')
    for x in observed['exposures.jsonl']:
        case = cases[x['session_id']]
        anchor = facets[case['query_paper_id']]
        focus = intents[case['case_id']]['focus_facet']
        left,right = (facets[pid] for pid in x['paper_ids'])
        require(not set(x['paper_ids']) & set(case['candidate_ids']),'Observed paper leaked into session holdout')
        require(all((None if not anchor[f] or not left[f] else bool(anchor[f] & left[f]))
                    == (None if not anchor[f] or not right[f] else bool(anchor[f] & right[f]))
                    for f in FACETS if f != focus)
                and bool(anchor[focus] & left[focus]) != bool(anchor[focus] & right[focus]),
                'Exposure pair is not matched on the other facets')
    seen = set()
    for row in truth['intent_labels.jsonl']:
        fields(row,{'case_id','candidate_id','relevance'},'intent label')
        key = row['case_id'],row['candidate_id']
        require(key[0] in cases and key[1] in cases[key[0]]['candidate_ids'] and key not in seen,'Unknown/duplicate intent label')
        case,intent = cases[key[0]],intents[key[0]]
        expected = session_grade(facets[case['query_paper_id']],facets[key[1]],intent['focus_facet'],
                                 intent['directions'][intent['focus_facet']],case['context_facet'])
        require(type(row['relevance']) is int and row['relevance'] == expected,'Intent relevance label violates rule')
        seen.add(key)
    require(seen == {(c['case_id'],pid) for c in cases.values() for pid in c['candidate_ids']},'Missing intent labels')
    require(all(sum(c['user_id'] == user for c in cases.values()) <= config['sessions_per_user'] for user in ids),
            'Too many sessions for user')
    require(report['shortfall'] == len(ids)*config['sessions_per_user'] - len(cases)
            and report['actual_cases'] == len(cases) and report['actual_pairs'] == len(seen),'Wrong D report quota')

def validate_experiment(root, experiment, config_path=None, allow_shortfall=False):
    root = Path(root).resolve()
    require(experiment in FILES,'Unknown experiment')
    config_path = config_path or f'configs/exp_{experiment}.json'
    config = json.loads(project_path(root,config_path).read_text(encoding='utf-8'))
    require(config['dataset_kind'] == 'mock' and type(config['seed']) is int and config['seed'] >= 0,'Invalid mock config')
    directory,hidden = output_paths(root,config,experiment)
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    require(manifest['contract_version'] == CONTRACT_VERSION and manifest['generator_version'] == CONTRACT_VERSION
            and manifest['experiment'] == experiment and manifest['dataset_kind'] == 'mock'
            and manifest['seed'] == config['seed'] and manifest['config'] == config,'Wrong manifest provenance/config; rebuild v2')
    require(set(manifest['input_hashes']) == set(input_paths(config,experiment,config_path)),'Missing or extra input hashes')
    for name,value in manifest['input_hashes'].items():
        require(sha256(project_path(root,name)) == value,f'Input checksum mismatch: {name}')
    require(manifest['generator_hashes'] == {name:sha256(ROOT / name) for name in generator_files(experiment)},
            'Generator hashes changed; rebuild required')
    expected = {(p / n).relative_to(root).as_posix() for p,names in
                ((directory,FILES[experiment][0]),(hidden,FILES[experiment][1])) for n in names}
    expected.add((directory / 'generation_report.json').relative_to(root).as_posix())
    require(set(manifest['files']) == expected,'Missing or extra output checksums')
    for name,value in manifest['files'].items():
        require(sha256(project_path(root,name)) == value,f'Output checksum mismatch: {name}')
    observed,truth = [{n:read_jsonl(p / n) if n.endswith('.jsonl') else
                      json.loads((p / n).read_text(encoding='utf-8')) for n in names}
                      for p,names in ((directory,FILES[experiment][0]),(hidden,FILES[experiment][1]))]
    counts = {n:len(rows) for data in (observed,truth) for n,rows in data.items() if n.endswith('.jsonl')}
    require(manifest['counts'] == counts,'Manifest record counts differ')
    for data in (observed,truth):
        for name,rows in data.items():
            key = 'query_id' if name.startswith('search_events') else 'exposure_id' if name.startswith('exposures') else None
            if key:
                require(len({r[key] for r in rows}) == len(rows),'Duplicate search/exposure ID within partition')
    report = json.loads((directory / 'generation_report.json').read_text(encoding='utf-8'))
    _,raw,metadata,_ = load_silver(root,Path(config['facets_path']).parent)
    facets = concept_sets(raw,metadata)
    require(report['excluded_flagged_count'] == len(raw) - len(facets),'Wrong excluded A annotation count')
    if experiment == 'b':
        check_b(observed,truth,facets,config,report)
    else:
        users = load_users(root,config) if experiment in ('d','e') else None
        if experiment == 'd':
            check_d(observed,truth,facets,config,report,users)
        else:
            validate_simulator(config)
            check_behavior(experiment,observed,truth,facets,config,report,users)
        require(report['behavior_counts'] == dict(collections.Counter(r['interaction_type']
                    for r in observed['interactions_train.jsonl'])),'Behavior report must contain history only')
    require(type(report['shortfall']) is int and report['shortfall'] >= 0,'Invalid shortfall')
    require(manifest['status'] == ('partial' if report['shortfall'] else 'complete'),'Completion status differs')
    require(allow_shortfall or manifest['status'] == 'complete','Target shortfall: dataset remains partial')
    return manifest
