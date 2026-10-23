"""Validate D observation data and source boundaries, without running a model."""
import argparse
import collections
import json
from pathlib import Path

from prepare_source import FACETS, HERE, inside, load_bundle, read_json, read_rows, require, sha


def time(value):
    import datetime as dt
    result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'Timezone required')
    return result


def unique(rows, key):
    result = {r[key]:r for r in rows}
    require(len(rows) == len(result), f'Duplicate {key}')
    return result


def features(row):
    return {f:set(row[f]) for f in FACETS}


def signature(row):
    return tuple((f, tuple(sorted(row[f]))) for f in FACETS)


def relevance(anchor, candidate, context, focus, direction):
    if not all((anchor[context], anchor[focus], candidate[context], candidate[focus])):
        return 0
    if not anchor[context] & candidate[context]:
        return 0
    same = bool(anchor[focus] & candidate[focus])
    return 2 if same == (direction == 'similar') else 1


def validate_dataset(directory, allow_pending=False):
    directory = Path(directory).resolve()
    require(directory.is_relative_to(HERE) and directory != HERE, 'Dataset must stay inside D')
    require(not (directory / 'FAILED.json').exists(), 'Dataset previously failed validation')
    manifest = read_json(directory / 'manifest.json')
    require(manifest['protocol'] == 'd_observation_v1', 'Wrong dataset protocol')
    allowed_status = {'structurally_valid', 'pending_validation'} if allow_pending else {'structurally_valid'}
    require(manifest['status'] in allowed_status, 'Data generation is incomplete')
    actual_files = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()} - {'manifest.json'}
    require(actual_files == set(manifest['files']), 'Manifest missing or extra output files')
    for name, expected in manifest['files'].items():
        require(sha(inside(directory, name)) == expected, f'Output checksum mismatch: {name}')
    for name, expected in manifest['code_sha256'].items():
        require(sha(inside(HERE, name)) == expected, f'Generator/validator changed: {name}')
    source_path = inside(HERE, manifest['source_directory'])
    require(sha(source_path / 'manifest.json') == manifest['source_manifest_sha256'], 'Prepared input identity changed')
    source = load_bundle(source_path)
    config = read_json(directory / 'config.json')
    from build_observation_data import validate_config
    validate_config(config)
    expected_conditions = {f'seed_{s}_noise_{n:g}':dict(seed=s, noise=n)
                           for s in config['feedback_seeds'] for n in config['noise_levels']}
    require(manifest['conditions'] == expected_conditions, 'Incomplete seed/noise matrix')
    catalog_rows = read_rows(directory / 'catalog/facets.jsonl')
    catalog = unique(catalog_rows, 'paper_id')
    allowed_catalog = {'paper_id', 'source_kind', 'representation', *FACETS}
    for row in catalog.values():
        require(set(row) == allowed_catalog, 'Public catalog contains hidden fields')
        require(row['source_kind'] in ('real', 'synthetic'), 'Unknown source kind')
        require(all(isinstance(row[f], list) and row[f] == sorted(set(row[f])) and
                    all(isinstance(c, str) and c for c in row[f]) for f in FACETS), 'Invalid concept list')
        require(row['representation'] == ('A_silver' if row['source_kind'] == 'real' else 'controlled_facets'),
                'Synthetic record misrepresented as A silver')
    real_ids = {p for p,r in catalog.items() if r['source_kind'] == 'real'}
    synthetic_ids = set(catalog)-real_ids
    require(real_ids == set(source['facets']), 'Real facet coverage differs from verified A')
    require(all(features(catalog[p]) == source['facets'][p] for p in real_ids), 'Real facets were edited')
    raw_papers = unique(read_rows(directory / 'catalog/real_papers.jsonl'), 'paper_id')
    require(raw_papers == source['papers'], 'Canonical title/abstract/metadata were edited or fabricated')
    provenance = unique(read_rows(directory / 'ground_truth/synthetic_provenance.jsonl'), 'paper_id')
    require(set(provenance) == synthetic_ids, 'Missing/extra synthetic provenance')
    for pid, row in provenance.items():
        require(row['role'] in ('candidate', 'observation') and row['source_base_id'] in real_ids, 'Invalid synthetic role/base')
        require(set(row['field_sources']) == set(FACETS), 'Incomplete field-level provenance')
        require(row['annotation_kind'] == 'controlled_constructed_not_A_silver', 'Wrong synthetic annotation kind')
        for f, donor in row['field_sources'].items():
            require(donor in real_ids and features(catalog[pid])[f] == source['facets'][donor][f],
                    'Invented concept or incorrect donor provenance')
    candidate_synthetic = {p for p,r in provenance.items() if r['role'] == 'candidate'}
    observation_synthetic = synthetic_ids-candidate_synthetic
    case_rows = read_rows(directory / 'generated/sessions.jsonl')
    cases = unique(case_rows, 'case_id')
    truths = unique(read_rows(directory / 'ground_truth/session_intents.jsonl'), 'case_id')
    designs = unique(read_rows(directory / 'ground_truth/designs.jsonl'), 'design_id')
    work_groups = read_json(directory / 'ground_truth/work_groups.json')
    require(set(work_groups) == real_ids and all(v in real_ids for v in work_groups.values()), 'Invalid work groups')
    require(set(cases) == set(truths), 'Truth/case coverage differs')
    require(set(d['focus'] for d in designs.values()) == set(FACETS), 'Missing focus facet')
    design_cases = collections.defaultdict(list)
    for name, original in source['history'].items():
        require(read_rows(directory / 'history' / name) == original, 'C public history changed')
    users = {r['user_id'] for r in source['history']['users.jsonl']}
    for design in designs.values():
        anchor, context, focus = (design[k] for k in ('anchor', 'context', 'focus'))
        require(anchor in real_ids and context in FACETS and focus in FACETS and context != focus, 'Invalid anchor/context/focus')
        require(source['facets'][anchor][context] and source['facets'][anchor][focus], 'Anchor facet missing')
        pool = design['candidate_ids']
        require(len(pool) == len(set(pool)) == 20 and anchor not in pool, 'Invalid 20-candidate pool')
        require(set(pool) <= real_ids | candidate_synthetic, 'Observation/unknown ID became candidate')
        same, different, outside = [], [], []
        for pid in pool:
            require(catalog[pid][context] and catalog[pid][focus], 'Missing candidate facet is not valid different')
            if pid in real_ids:
                require(work_groups[pid] != work_groups[anchor], 'Related anchor version became candidate')
            if not set(catalog[pid][context]) & set(catalog[anchor][context]):
                outside.append(pid)
            elif set(catalog[pid][focus]) & set(catalog[anchor][focus]):
                same.append(pid)
            else:
                different.append(pid)
        require(len(same) == len(different) == 1 and len(outside) == 18, 'Pool does not contain 1 same/1 different/18 outside')
        require(set(same) == set(design['same_candidate_ids']) and set(different) == set(design['different_candidate_ids'])
                and set(outside) == set(design['outside_candidate_ids']), 'Hidden pool roles disagree with facets')
        constructed = set(pool) & candidate_synthetic
        if design['synthetic_fill_side']:
            require(focus == 'problem' and len(constructed) == 1 and design['candidate_source_group'] == 'mixed',
                    'Synthetic candidates must only fill one missing problem side')
            side = same if design['synthetic_fill_side'] == 'similar' else different
            require(constructed <= set(side), 'Constructed candidate on wrong side')
            # Confirm that the original real pool genuinely lacked this side.
            original_same, original_diff = [], []
            for p,r in source['facets'].items():
                if work_groups[p] == work_groups[anchor] or not r[context] or not r[focus]:
                    continue
                if r[context] & source['facets'][anchor][context]:
                    (original_same if r[focus] & source['facets'][anchor][focus] else original_diff).append(p)
            require(not (original_same if design['synthetic_fill_side'] == 'similar' else original_diff),
                    'Synthetic candidate manufactured despite available real side')
        else:
            require(not constructed and design['candidate_source_group'] == 'real_only', 'Wrong candidate source label')
        require(len(design['observation_pairs']) == config['observation_pairs'], 'Missing observation pair')
        candidate_signatures = {signature(catalog[p]) for p in pool}
        for a,b in design['observation_pairs']:
            require(a != b and {a,b} <= observation_synthetic and not {a,b} & (set(pool)|{anchor}), 'Observation/candidate role overlap')
            require(all(provenance[p]['design_id'] == design['design_id'] for p in (a,b)), 'Cross-design observation')
            require(all(signature(catalog[p]) not in candidate_signatures for p in (a,b)), 'Observation copies candidate facet content')
            require(bool(set(catalog[a][focus]) & set(catalog[anchor][focus])) !=
                    bool(set(catalog[b][focus]) & set(catalog[anchor][focus])), 'Observation lacks same/different contrast')
            for f in FACETS:
                if f != focus:
                    require(catalog[a][f] == catalog[b][f], 'Observation differs outside focus')
            require(set(catalog[a][context]) & set(catalog[anchor][context]), 'Observation outside context')
    for cid, case in cases.items():
        require(set(case) == {'case_id','user_id','query_paper_id','context_facet','candidate_ids','cutoff'}, 'Hidden field in public case')
        require(case['user_id'] in users, 'Unknown user')
        truth = truths[cid]
        require(set(truth) == {'case_id','design_id','focus_facet','directions','facet_importance','query_mode'}, 'Invalid truth schema')
        design = designs[truth['design_id']]
        require(case['query_paper_id'] == design['anchor'] and case['context_facet'] == design['context']
                and case['candidate_ids'] == design['candidate_ids'], 'Paired pool or anchor/context changed')
        require(truth['focus_facet'] == design['focus'] and truth['query_mode'] in config['query_modes'], 'Invalid intent')
        direction = truth['directions'][truth['focus_facet']]
        require(direction in ('similar','different'), 'Invalid direction')
        dirs = dict.fromkeys(FACETS, 'ignore')
        dirs[design['context']], dirs[design['focus']] = 'similar', direction
        weights = dict.fromkeys(FACETS, 0.)
        weights[design['context']], weights[design['focus']] = .6,.4
        require(truth['directions'] == dirs and truth['facet_importance'] == weights, 'Truth weights/directions changed')
        for name in ('interactions_train.jsonl','search_events.jsonl','exposures.jsonl'):
            require(all(time(r['timestamp']) < time(case['cutoff']) for r in source['history'][name]), 'Future C history')
        design_cases[truth['design_id']].append(case)
    for did, values in design_cases.items():
        require(len(values) == 6 and {(truths[c['case_id']]['query_mode'], truths[c['case_id']]['directions'][designs[did]['focus']])
                                     for c in values} == {(m,d) for m in config['query_modes'] for d in ('similar','different')},
                'Missing/duplicate paired intent or query mode')
        for mode in config['query_modes']:
            pair = [c for c in values if truths[c['case_id']]['query_mode'] == mode]
            require(pair[0]['user_id'] == pair[1]['user_id'] and pair[0]['cutoff'] == pair[1]['cutoff'], 'Paired profile/cutoff changed')
    require(set(design_cases) == set(designs), 'Unused design')
    label_rows = read_rows(directory / 'ground_truth/intent_labels.jsonl')
    labels = {(r['case_id'],r['candidate_id']):r['relevance'] for r in label_rows}
    require(len(labels) == len(label_rows) == 20*len(cases), 'Duplicate/missing candidate labels')
    for cid,case in cases.items():
        truth = truths[cid]
        for p in case['candidate_ids']:
            expected = relevance(features(catalog[case['query_paper_id']]), features(catalog[p]), case['context_facet'],
                                 truth['focus_facet'], truth['directions'][truth['focus_facet']])
            require(labels.get((cid,p)) == expected, 'Label disagrees with source-grounded overlap rule')
    queries = unique(read_rows(directory / 'generated/search_events.jsonl'), 'query_id')
    by_case_queries = collections.defaultdict(list)
    for query in queries.values():
        require(set(query) == {'query_id','user_id','session_id','text','parent_query_id','timestamp'}, 'Hidden field in query')
        require(query['session_id'] in cases, 'Unknown query session')
        case = cases[query['session_id']]
        require(query['user_id'] == case['user_id'] and time(query['timestamp']) < time(case['cutoff']), 'Future/cross-user query')
        if query['parent_query_id']:
            parent = queries.get(query['parent_query_id'])
            require(parent and parent['session_id'] == query['session_id'] and parent['user_id'] == query['user_id']
                    and time(parent['timestamp']) < time(query['timestamp']), 'Invalid query parent')
        by_case_queries[query['session_id']].append(query)
    for cid,case in cases.items():
        require(len(by_case_queries[cid]) == {'clear':2,'ambiguous':1,'none':0}[truths[cid]['query_mode']], 'Query mode mismatch')
        ordered = sorted(by_case_queries[cid], key=lambda q:time(q['timestamp']))
        if ordered:
            anchor = features(catalog[case['query_paper_id']])
            context, focus = case['context_facet'], truths[cid]['focus_facet']
            first = f'{context}: {sorted(anchor[context])[0]} papers'
            require(ordered[0]['text'] == first and ordered[0]['parent_query_id'] is None, 'Incorrect context query')
            if len(ordered) == 2:
                concept = sorted(anchor[focus])[0]
                direction = truths[cid]['directions'][focus]
                phrase = f'alternatives to {concept}' if direction == 'different' else f'more papers using {concept}'
                expected = f'{context}: {sorted(anchor[context])[0]}; {focus}: {phrase}'
                require(ordered[1]['text'] == expected and ordered[1]['parent_query_id'] == ordered[0]['query_id'],
                        'Clear query disagrees with simulator intent')
    condition_reports = {}
    actions = ('dislike','view','click','save','like')
    for name, spec in manifest['conditions'].items():
        folder = directory / 'conditions' / name
        exposures = unique(read_rows(folder / 'generated/exposures.jsonl'), 'exposure_id')
        events = read_rows(folder / 'generated/interactions_train.jsonl')
        hidden = read_rows(folder / 'ground_truth/reaction_provenance.jsonl')
        reactions = {(r['exposure_id'],r['paper_id']):r for r in events}
        utilities = {(r['exposure_id'],r['paper_id']):r for r in hidden}
        require(len(reactions) == len(events) == len(utilities) == len(hidden) == 2*len(exposures), 'Incomplete/duplicate reactions')
        require(set(reactions) == set(utilities), 'Reaction provenance differs')
        counts = collections.Counter()
        observed_pairs = collections.defaultdict(list)
        for xid, exposure in exposures.items():
            require(set(exposure) == {'exposure_id','user_id','session_id','query_id','paper_ids','timestamp'}, 'Hidden field in exposure')
            require(exposure['session_id'] in cases, 'Unknown exposure case')
            cid = exposure['session_id']
            case,truth = cases[cid],truths[cid]
            design = designs[truth['design_id']]
            require(exposure['user_id'] == case['user_id'] and time(exposure['timestamp']) < time(case['cutoff']), 'Invalid exposure user/time')
            require(len(exposure['paper_ids']) == 2 and len(set(exposure['paper_ids'])) == 2, 'Invalid exposure pair')
            require(frozenset(exposure['paper_ids']) in {frozenset(p) for p in design['observation_pairs']}, 'Unexpected observation pair')
            observed_pairs[cid].append(frozenset(exposure['paper_ids']))
            if exposure['query_id']:
                query = queries.get(exposure['query_id'])
                require(query and query['session_id'] == cid and time(query['timestamp']) < time(exposure['timestamp']), 'Exposure query link invalid')
            else:
                require(not by_case_queries[cid], 'Missing query link')
            counts[cid] += 1
            for pid in exposure['paper_ids']:
                event = reactions.get((xid,pid))
                require(event and set(event) == {'user_id','paper_id','interaction_type','timestamp','session_id','exposure_id'}, 'Invalid reaction schema')
                require(event['session_id'] == cid and event['user_id'] == case['user_id'] and
                        time(exposure['timestamp']) < time(event['timestamp']) < time(case['cutoff']), 'Future/cross-case reaction')
                utility = utilities[xid,pid]
                g = relevance(features(catalog[case['query_paper_id']]), features(catalog[pid]), case['context_facet'],
                              truth['focus_facet'], truth['directions'][truth['focus_facet']])
                baseline = config['utility_satisfied'] if g == 2 else config['utility_unsatisfied']
                expected_utility = baseline + spec['noise']*utility['gaussian_draw']
                require(utility['grade'] == g and abs(expected_utility-utility['utility']) < 1e-12, 'Reaction utility/provenance mismatch')
                action = actions[sum(expected_utility >= x for x in config['interaction_thresholds'])]
                require(event['interaction_type'] == action, 'Reaction not generated by declared simulator')
        require(set(counts) == set(cases) and all(n == config['observation_pairs'] for n in counts.values()), 'Incomplete pair coverage')
        for cid, pairs in observed_pairs.items():
            expected_pairs = [frozenset(p) for p in designs[truths[cid]['design_id']]['observation_pairs']]
            require(collections.Counter(pairs) == collections.Counter(expected_pairs), 'Repeated/missing observation pair')
        condition_reports[name] = dict(exposures=len(exposures), interactions=len(events),
                                      behavior_counts=dict(collections.Counter(e['interaction_type'] for e in events)))
    report = read_json(directory / 'generation_report.json')
    require(report['sessions'] == len(cases) and report['designs'] == len(designs) and report['candidate_labels'] == len(labels), 'Report counts mismatch')
    require(report['designs_by_focus'] == dict(collections.Counter(d['focus'] for d in designs.values())), 'Focus counts mismatch')
    require(manifest['no_experiments_run'] is True and manifest['semantic_review'] == 'pending', 'Wrong scope declaration')
    return dict(status='PASS', scope='structural_and_provenance_validation_only', sessions=len(cases),
                designs=len(designs), labels=len(labels), synthetic_candidates=len(candidate_synthetic),
                synthetic_observations=len(observation_synthetic), conditions=condition_reports,
                checked=['checksums','source identity','real text/facets unchanged','controlled field provenance',
                         'synthetic roles','missing-side-only candidates','20-paper shared pools','all five focus facets',
                         'paired intents','query and time links','disjoint observation IDs and candidate content',
                         'matched pairs','graded labels','C history prefix','no hidden fields in public schema',
                         'declared noisy reaction simulator','complete feedback seed/noise matrix'],
                semantic_review='pending', human_validation=False, no_models_run=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', type=Path)
    args = parser.parse_args()
    print(json.dumps(validate_dataset(args.dataset), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
