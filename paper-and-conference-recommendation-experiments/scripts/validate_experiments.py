"""Validate B–E schemas, semantic rules, references, hashes and temporal leakage."""
import collections
import json
import math
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_corpus import read_jsonl
from data.experiment_common import facet_relevance, intent_satisfaction, validate_sampling, validate_simulator
from data.exp_c.build_exp_c import validate_templates
from download_sources import ROOT, sha256
from experiment_io import (FACETS, FILES, check_users, concept_sets, input_paths,
                           generator_files, load_silver, load_users, output_paths, project_path)
from validate_all import require, validate_temporal, validate_time


def fields(row, expected, where):
    require(isinstance(row,dict) and set(row) == set(expected), f'{where}: wrong fields / observable schema')


def check_splits(records, splits, id_field):
    require(set(splits) == {'train','dev','test'}, 'Wrong split names')
    assigned = {}
    for name, ids in splits.items():
        require(isinstance(ids,list), 'Split IDs must be lists')
        for value in ids:
            require(value not in assigned, 'Duplicate split ID')
            assigned[value] = name
    require(set(assigned) == {row[id_field] for row in records}, 'Split IDs differ from queries/cases')
    anchors = {}
    for row in records:
        anchor, side = row['query_paper_id'], assigned[row[id_field]]
        require(anchors.setdefault(anchor,side) == side, 'Query anchor leaks across splits')


def check_retrieval(experiment, observed, truth, facets, config, report, templates=None):
    is_b = experiment == 'b'
    id_field, label_field = ('query_id','relevance') if is_b else ('intent_id','satisfies_intent')
    records = observed['retrieval_queries.jsonl' if is_b else 'intents.jsonl']
    labels = truth['retrieval_labels.jsonl' if is_b else 'intent_labels.jsonl']
    schema = {id_field,'query_paper_id','candidate_ids'} | ({'target_facet'} if is_b else {'intent_type','constraints'})
    by_id, pairs, anchors = {}, {}, set()
    template_map = {row['intent_type']:row for row in templates['templates']} if templates else {}
    for row in records:
        fields(row,schema,'query/intent')
        rid, anchor, candidates = row[id_field], row['query_paper_id'], row['candidate_ids']
        require(isinstance(rid,str) and re.fullmatch(('Q' if is_b else 'I')+r'[0-9]{4}',rid)
                and rid not in by_id, 'Invalid or duplicate query/intent ID')
        require(anchor in facets, 'Query anchor has no clean A facets')
        require(isinstance(candidates,list) and len(candidates) == config['candidates_per_query' if is_b else 'candidates_per_case']
                and len(candidates) == len(set(candidates)) and anchor not in candidates, 'Wrong/self/duplicate candidates')
        if is_b:
            require(row['target_facet'] in config['target_facets'], 'Invalid target facet')
            group = row['target_facet']
        else:
            require(row['intent_type'] in template_map and row['constraints'] == template_map[row['intent_type']]['constraints'],
                    'Intent constraints differ from template')
            group = row['intent_type']
        require((anchor,group) not in anchors, 'Duplicate anchor/facet or anchor/template case')
        anchors.add((anchor,group))
        by_id[rid] = row
        for pid in candidates:
            require(pid in facets, 'Candidate has no clean A facets')
            answer = (facet_relevance(facets[anchor][group],facets[pid][group]) if is_b
                      else intent_satisfaction(facets[anchor],facets[pid],row['constraints']))
            require(answer is not None, 'Missing constrained facet makes candidate ineligible')
            pairs[(rid,pid)] = answer
    seen = set()
    outcomes = collections.defaultdict(set)
    for row in labels:
        fields(row,{id_field,'candidate_id',label_field},'label')
        pair = row[id_field], row['candidate_id']
        value = row[label_field]
        require(pair in pairs and pair not in seen, 'Unknown or duplicate label pair')
        require(type(value) is (int if is_b else bool) and value == pairs[pair], 'Relevance/intent label violates rule')
        seen.add(pair)
        outcomes[pair[0]].add(bool(value))
    require(seen == set(pairs), 'Labels missing from candidate set')
    require(all(outcomes[rid] == {False,True} for rid in by_id), 'Each query/intent needs positive and negative candidates')
    seen = set()
    for row in truth['label_provenance.jsonl']:
        expected = {id_field,'candidate_id','label_source','rule_version','candidate_role'}
        expected |= {'target_facet','anchor_concepts','candidate_concepts'} if is_b else {'template_version'}
        fields(row,expected,'label provenance')
        pair = row[id_field],row['candidate_id']
        require(pair in pairs and pair not in seen and row['label_source'] == 'synthetic_rule'
                and row['rule_version'] == config['label_rule_version'], 'Wrong label provenance')
        query, pid = by_id[pair[0]],pair[1]
        anchor = query['query_paper_id']
        if is_b:
            facet = query['target_facet']
            require(row['target_facet'] == facet and row['anchor_concepts'] == sorted(facets[anchor][facet])
                    and row['candidate_concepts'] == sorted(facets[pid][facet]), 'Provenance facet concepts differ')
            hard = any(facets[anchor][other] & facets[pid][other] for other in FACETS if other != facet)
            role = 'positive' if pairs[pair] else 'hard_negative' if hard else 'easy_negative'
        else:
            require(row['template_version'] == templates['version'], 'Wrong template provenance')
            active = [facet for facet in FACETS if query['constraints'][facet] != 'ignore']
            failures = sum(bool(facets[anchor][facet] & facets[pid][facet]) != (query['constraints'][facet] == 'similar')
                           for facet in active)
            role = 'positive' if pairs[pair] else 'hard_negative' if failures == 1 else 'negative'
        require(row['candidate_role'] == role, 'Candidate role differs from facet rules')
        seen.add(pair)
    require(seen == set(pairs), 'Missing label provenance')
    check_splits(records,observed['splits.json'],id_field)
    target = config['num_queries' if is_b else 'num_cases']
    require(len(records) <= target and report['shortfall'] == target-len(records), 'Wrong target shortfall')
    require(report['actual_pairs'] == len(labels), 'Wrong reported pair count')
    actual = collections.Counter(row['target_facet' if is_b else 'intent_type'] for row in records)
    if is_b:
        targets = config['target_facets']
        requested = {facet:target//len(targets)+(i < target%len(targets)) for i,facet in enumerate(targets)}
        require(report['requested_by_facet'] == requested and report['actual_by_facet'] == {k:actual[k] for k in requested},
                'Wrong facet quota report')
    else:
        requested = {name:row['quota'] for name,row in template_map.items()}
        require(report['requested_by_type'] == requested and report['actual_by_type'] == {k:actual[k] for k in requested},
                'Wrong intent quota report')
    require(all(actual[key] <= value for key,value in requested.items()), 'Per-type quota exceeded')


def check_profile(profile, vocabulary):
    require(isinstance(profile,dict) and set(profile) == set(FACETS), 'Wrong latent profile facets')
    for facet, weights in profile.items():
        require(isinstance(weights,dict), 'Latent preferences must be concept maps')
        for concept, weight in weights.items():
            require(concept in vocabulary[facet], 'Latent profile has unknown concept')
            require(type(weight) in (int,float) and math.isfinite(weight) and -1 <= weight <= 1,
                    'Latent weights must be finite numbers in [-1,1]')


def check_behavior(experiment, observed, truth, facets, config, report, shared_users=None):
    users = observed['users.jsonl'] if experiment == 'd' else shared_users
    check_users(users)
    user_ids = {row['user_id'] for row in users}
    if experiment == 'd':
        require(len(users) == config['num_users'], 'Wrong D user quota')
    vocabulary = {facet:set().union(*(row[facet] for row in facets.values())) for facet in FACETS}
    profiles = truth['latent_user_profiles.jsonl' if experiment == 'd' else 'temporal_profiles.jsonl']
    by_profile = {}
    boundaries = [validate_time(value) for value in config['period_boundaries']] if experiment == 'e' else None
    for row in profiles:
        expected = {'user_id','latent_preferences'}
        if experiment == 'e':
            expected |= {'period','start_timestamp','end_timestamp'}
        fields(row,expected,'latent profile')
        require(row['user_id'] in user_ids, 'Profile has unknown shared user')
        period = row.get('period',0)
        if experiment == 'e':
            require(type(period) is int and 1 <= period <= 4, 'Invalid profile period')
            require(validate_time(row['start_timestamp']) == boundaries[period-1]
                    and validate_time(row['end_timestamp']) == boundaries[period], 'Profile time boundaries differ')
        key = row['user_id'],period
        require(key not in by_profile, 'Duplicate user/period profile')
        check_profile(row['latent_preferences'],vocabulary)
        by_profile[key] = row['latent_preferences']
    periods = range(1,5) if experiment == 'e' else (0,)
    require(set(by_profile) == {(user,period) for user in user_ids for period in periods}, 'Missing user/period profiles')
    history, future = observed['interactions_train.jsonl'], truth['interactions_test.jsonl']
    counts, exposures, event_keys = collections.Counter(),set(),set()
    for rows, side in ((history,'history'),(future,'future')):
        last = {}
        for row in rows:
            fields(row,{'user_id','paper_id','interaction_type','timestamp'},'observable event')
            user, paper, time = row['user_id'],row['paper_id'],validate_time(row['timestamp'])
            require(user in user_ids, 'Event has unknown shared user')
            require(paper in facets and any(facets[paper].values()), 'Event paper has no eligible A facets')
            require(row['interaction_type'] in {'view','click','save','like','dislike'}, 'Invalid interaction type')
            require(user not in last or last[user] < time, 'Event time order must be strict per user')
            last[user] = time
            require((user,time) not in event_keys, 'Duplicate user/event time')
            event_keys.add((user,time))
            period = 0
            if experiment == 'e':
                period = next((i for i in range(1,5) if boundaries[i-1] <= time < boundaries[i]), None)
                require(period is not None, 'Event outside E time periods')
                require((period in config['history_periods']) == (side == 'history'), 'Future period leaked into history')
            require((user,period,paper) not in exposures, 'Exposure repeats within user/period')
            exposures.add((user,period,paper))
            counts[user,side,period] += 1
    validate_temporal(history,future)
    if experiment == 'd':
        for user in user_ids:
            require(counts[user,'history',0] == config['history_events_per_user']
                    and counts[user,'future',0] == config['events_per_user']-config['history_events_per_user'],
                    'Wrong D event quotas')
    else:
        for user in user_ids:
            for period in range(1,5):
                side = 'history' if period in config['history_periods'] else 'future'
                require(counts[user,side,period] == config['events_per_user_per_period'], 'Wrong E period quota')
        metadata = truth['period_metadata.json']
        fields(metadata,{'groups','boundaries','drift_coefficients'},'period metadata')
        groups = metadata['groups']
        require(set(groups) == user_ids and set(groups.values()) <= {'stable','drift'}, 'Wrong E scenario groups')
        require(metadata['boundaries'] == config['period_boundaries']
                and metadata['drift_coefficients'] == config['drift_coefficients'], 'Wrong E temporal metadata')
        stable_count = sum(value == 'stable' for value in groups.values())
        require(stable_count == int(len(users)*config['stable_fraction'])
                and report['group_counts'] == {'stable':stable_count,'drift':len(users)-stable_count}, 'Wrong stable/drift counts')
        for user, group in groups.items():
            old, new = by_profile[user,1],by_profile[user,3]
            if group == 'stable':
                require(all(by_profile[user,period] == old for period in range(1,5)), 'Stable profile changed')
            else:
                require(old != new and by_profile[user,4] == new, 'Drift profiles did not move old to new')
                for facet in FACETS:
                    concepts = old[facet].keys() | new[facet].keys()
                    expected = {concept:round((1-config['drift_coefficients'][1])*old[facet].get(concept,0)
                                              + config['drift_coefficients'][1]*new[facet].get(concept,0),6)
                                for concept in concepts}
                    require(by_profile[user,2][facet] == expected, 'Transition profile violates drift rule')
    require(report['shortfall'] == 0 and report['actual_users'] == len(users)
            and report['actual_events'] == len(history)+len(future), 'Wrong behavior report counts')
    require(report['behavior_counts'] == dict(collections.Counter(row['interaction_type'] for row in history)),
            'Wrong history behavior distribution or future-data leakage')


def validate_experiment(root, experiment, config_path=None, allow_shortfall=False):
    root = Path(root).resolve()
    require(experiment in FILES, 'Unknown experiment')
    config_path = config_path or f'configs/exp_{experiment}.json'
    config = json.loads(project_path(root,config_path).read_text(encoding='utf-8'))
    require(config['dataset_kind'] == 'mock', 'B–E datasets must be mock')
    directory, hidden = output_paths(root,config,experiment)
    manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    require(manifest['contract_version'] == '1.0' and manifest['dataset_kind'] == 'mock'
            and manifest['experiment'] == experiment and manifest['generator_version'] == '1.0'
            and manifest['seed'] == config['seed'] and manifest['config'] == config, 'Wrong manifest provenance/config')
    expected_inputs = input_paths(config,experiment,config_path)
    require(set(manifest['input_hashes']) == set(expected_inputs), 'Missing or extra input hashes')
    for name, value in manifest['input_hashes'].items():
        require(sha256(project_path(root,name)) == value, f'Input checksum mismatch: {name}')
    expected_generators = {name:sha256(ROOT/name) for name in generator_files(experiment)}
    require(manifest['generator_hashes'] == expected_generators, 'Generator hashes changed; rebuild required')
    expected_files = {(path/name).relative_to(root).as_posix()
                      for path,names in ((directory,FILES[experiment][0]),(hidden,FILES[experiment][1])) for name in names}
    expected_files.add((directory/'generation_report.json').relative_to(root).as_posix())
    require(set(manifest['files']) == expected_files, 'Missing or extra output checksums')
    for name, value in manifest['files'].items():
        require(sha256(project_path(root,name)) == value, f'Output checksum mismatch: {name}')
    artifacts = []
    for path, names in ((directory,FILES[experiment][0]),(hidden,FILES[experiment][1])):
        artifacts.append({name:read_jsonl(path/name) if name.endswith('.jsonl')
                          else json.loads((path/name).read_text(encoding='utf-8')) for name in names})
    observed, truth = artifacts
    counts = {name:len(rows) for values in artifacts for name,rows in values.items() if name.endswith('.jsonl')}
    require(manifest['counts'] == counts, 'Manifest record counts differ')
    report = json.loads((directory/'generation_report.json').read_text(encoding='utf-8'))
    _, raw, metadata, _ = load_silver(root,Path(config['facets_path']).parent)
    facets = concept_sets(raw,metadata)
    require(report['excluded_flagged_count'] == len(raw)-len(facets), 'Wrong excluded A annotation count')
    if experiment in ('b','c'):
        validate_sampling(config,'num_queries' if experiment == 'b' else 'num_cases',
                          'candidates_per_query' if experiment == 'b' else 'candidates_per_case')
        templates = json.loads(project_path(root,config['templates_path']).read_text(encoding='utf-8')) if experiment == 'c' else None
        if templates:
            validate_templates(templates,config['num_cases'])
        check_retrieval(experiment,observed,truth,facets,config,report,templates)
    else:
        validate_simulator(config)
        users = load_users(root,config) if experiment == 'e' else None
        check_behavior(experiment,observed,truth,facets,config,report,users)
    require(type(report['shortfall']) is int and report['shortfall'] >= 0, 'Invalid shortfall')
    expected_status = 'partial' if report['shortfall'] else 'complete'
    require(manifest['status'] == expected_status, 'Completion status differs from actual quota')
    require(allow_shortfall or manifest['status'] == 'complete', 'Target shortfall: dataset remains partial')
    return manifest
