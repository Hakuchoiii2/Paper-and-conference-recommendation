"""Build QUAN SAT: paired intents, real pools and missing-side problem candidates.

Data preparation only. No direction estimator, ranker, training or evaluation.
Synthetic objects contain controlled facets, never fabricated abstracts or DOIs.
"""
import argparse
import collections
import datetime as dt
import difflib
import hashlib
import json
from pathlib import Path
import random

from prepare_source import FACETS, HERE, load_bundle, normalize, read_json, require, sha, write_json, write_rows

PUBLIC_CASE_FIELDS = {'case_id', 'user_id', 'query_paper_id', 'context_facet', 'candidate_ids', 'cutoff'}


def opaque(prefix, *parts):
    return prefix + hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()[:20]


def clock(value):
    result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'Timezone required')
    return result


def timestamp(value):
    return value.astimezone(dt.timezone.utc).isoformat().replace('+00:00', 'Z')


def fingerprint(row):
    return json.dumps({f:sorted(row[f]) for f in FACETS}, sort_keys=True)


def grade(anchor, candidate, context, focus, direction):
    if not anchor[context] or not anchor[focus] or not candidate[context] or not candidate[focus]:
        return 0
    if not anchor[context] & candidate[context]:
        return 0
    return 2 if bool(anchor[focus] & candidate[focus]) == (direction == 'similar') else 1


def validate_config(config):
    require(config.get('protocol') == 'd_observation_v1', 'Unsupported observation protocol')
    for key in ('same_candidates', 'different_candidates', 'outside_candidates', 'observation_pairs'):
        require(type(config[key]) is int and config[key] > 0, f'Invalid {key}')
    require(config['same_candidates'] == config['different_candidates'] == 1,
            'v1 uses 1 same / 1 different; do not inflate synthetic copies')
    require(config['outside_candidates'] == 18 and config['observation_pairs'] == 4, 'v1 uses 20 candidates / 4 pairs')
    require(type(config['structure_seed']) is int, 'Invalid structure seed')
    require(config['feedback_seeds'] and len(set(config['feedback_seeds'])) == len(config['feedback_seeds'])
            and all(type(s) is int for s in config['feedback_seeds']), 'Invalid feedback seeds')
    require(config['noise_levels'] and len(set(config['noise_levels'])) == len(config['noise_levels'])
            and all(type(x) in (int, float) and 0 < x <= 1 for x in config['noise_levels']), 'Noise must be positive and <= 1')
    thresholds = config['interaction_thresholds']
    require(len(thresholds) == 4 and all(type(x) in (int, float) and abs(x) < 100 for x in thresholds)
            and all(a < b for a, b in zip(thresholds, thresholds[1:])), 'Invalid feedback thresholds')
    require(type(config['utility_satisfied']) in (int, float) and type(config['utility_unsatisfied']) in (int, float)
            and -1 <= config['utility_unsatisfied'] < config['utility_satisfied'] <= 1, 'Invalid utility')
    require(config['query_modes'] == ['clear', 'ambiguous', 'none'], 'Use all three query modes')
    require(config['synthetic_representation'] == 'controlled_facets_only', 'No fabricated paper content')
    require(type(config.get('max_real_designs_per_focus', 0)) is int and config.get('max_real_designs_per_focus', 0) >= 0,
            'Invalid real-design limit')
    clock(config['start_timestamp'])
    seen = set()
    for item in config['problem_designs']:
        key = item['anchor'], item['context']
        require(item['context'] in FACETS[1:] and key not in seen, 'Invalid or duplicate problem design')
        seen.add(key)


def work_groups(papers, eligible):
    """Conservative mechanical version grouping; semantic same-work review remains pending."""
    parent = {p:p for p in eligible}
    def find(p):
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p
    def union(a, b):
        a, b = find(a), find(b)
        parent[max(a, b)] = min(a, b)
    title_index, abstract_index = collections.defaultdict(list), collections.defaultdict(list)
    for p in sorted(eligible):
        title_index[normalize(papers[p]['title'])].append(p)
        text = normalize(papers[p]['abstract'])
        abstract_index[' '.join(text.split()[:12])].append(p)
    for values in title_index.values():
        for p in values[1:]:
            union(values[0], p)
    for values in abstract_index.values():
        if len(values) > 50:  # A generic opening is not enough to claim related versions.
            continue
        for i, a in enumerate(values):
            for b in values[i+1:]:
                aa, bb = normalize(papers[a]['abstract']), normalize(papers[b]['abstract'])
                if len(aa) > 150 and difflib.SequenceMatcher(None, aa, bb).ratio() >= .95:
                    union(a, b)
    return {p:find(p) for p in eligible}


def index_facets(facets):
    result = {f:collections.defaultdict(set) for f in FACETS}
    for p, row in facets.items():
        for f in FACETS:
            for concept in row[f]:
                result[f][concept].add(p)
    return result


def available_groups(facets, index, groups, anchor, context, focus):
    row = facets[anchor]
    matching = lambda f:set().union(*(index[f][v] for v in sorted(row[f]))) if row[f] else set()
    eligible = {p for p, r in facets.items() if r[context] and r[focus] and groups[p] != groups[anchor]}
    related = eligible & matching(context)
    same = related & matching(focus)
    return sorted(same), sorted(related-same), sorted(eligible-related)


def assemble(source, config):
    validate_config(config)
    real, papers = source['facets'], source['papers']
    users = sorted(source['history']['users.jsonl'], key=lambda x:x['user_id'])
    require(users, 'No C users')
    start = clock(config['start_timestamp'])
    for name in ('interactions_train.jsonl', 'search_events.jsonl', 'exposures.jsonl'):
        require(all(clock(r['timestamp']) < start for r in source['history'][name]), 'C prefix is not before D start')
    groups = work_groups(papers, real)
    index = index_facets(real)
    rng = random.Random(config['structure_seed'])
    all_facets = {p:{f:set(v) for f,v in row.items()} for p,row in real.items()}
    provenance, designs, skipped, synthetic = [], [], [], {}

    def synth(design_id, role, slot, base, replacements):
        pid = opaque('SX', config['structure_seed'], design_id, role, slot)
        row = {f:set(real[base][f]) for f in FACETS}
        field_sources = dict.fromkeys(FACETS, base)
        for f, donor in replacements.items():
            row[f] = set(real[donor][f])
            field_sources[f] = donor
        require(pid not in all_facets, 'Synthetic ID collision')
        all_facets[pid] = synthetic[pid] = row
        provenance.append(dict(paper_id=pid, design_id=design_id, role=role, source_base_id=base,
                               field_sources=field_sources, annotation_kind='controlled_constructed_not_A_silver'))
        return pid

    requests = []
    selected_counts = collections.Counter()
    if config['include_real_designs_for_other_facets']:
        for anchor, row in sorted(real.items()):
            for context in FACETS:
                for focus in FACETS[1:]:
                    if context == focus or not row[context] or not row[focus]:
                        continue
                    same, different, outside = available_groups(real, index, groups, anchor, context, focus)
                    if same and different and len(outside) >= config['outside_candidates']:
                        limit = config.get('max_real_designs_per_focus', 0)
                        if limit and selected_counts[focus] >= limit:
                            continue
                        requests.append((anchor, context, focus, False))
                        selected_counts[focus] += 1
    requests += [(r['anchor'], r['context'], 'problem', True) for r in config['problem_designs']]
    for number, (anchor, context, focus, allow_fill) in enumerate(requests):
        if anchor not in real or not real[anchor][context] or not real[anchor][focus]:
            skipped.append(dict(anchor=anchor, context=context, focus=focus, reason='anchor_missing_required_facet'))
            continue
        same, different, outside = available_groups(real, index, groups, anchor, context, focus)
        if len(outside) < config['outside_candidates'] or not (same or different):
            skipped.append(dict(anchor=anchor, context=context, focus=focus, reason='insufficient_real_pool'))
            continue
        if (not same or not different) and not allow_fill:
            continue
        did = opaque('DS', anchor, context, focus)
        fill = None
        selected_same = rng.choice(same) if same else None
        selected_different = rng.choice(different) if different else None
        if not same:
            # Keep the actual non-focus background of a related real paper, not an exact clone of the anchor.
            selected_same = synth(did, 'candidate', 0, selected_different, {focus:anchor})
            fill = 'similar'
        elif not different:
            donor_pool = [p for p in sorted(real) if real[p][focus] and not real[p][focus] & real[anchor][focus]
                          and groups[p] != groups[anchor]]
            if not donor_pool:
                skipped.append(dict(anchor=anchor, context=context, focus=focus, reason='no_disjoint_focus_donor'))
                continue
            # Prefer a donor already sharing context; this is compatibility, not a method-score filter.
            compatible = [p for p in donor_pool if real[p][context] & real[anchor][context]]
            donor = rng.choice(compatible or donor_pool)
            selected_different = synth(did, 'candidate', 0, selected_same, {focus:donor})
            fill = 'different'
        pool = [selected_same, selected_different] + rng.sample(outside, config['outside_candidates'])
        rng.shuffle(pool)
        candidate_fingerprints = {fingerprint(all_facets[p]) for p in pool}
        banned_groups = {groups[p] for p in pool if p in real} | {groups[anchor]}
        donors = [p for p in sorted(real) if p not in pool and groups[p] not in banned_groups
                  and real[p][focus] and not real[p][focus] & real[anchor][focus]]
        require(len(donors) >= config['observation_pairs'], 'Not enough independent donor records for observation draws')
        rng.shuffle(donors)
        # Candidate/anchor work versions cannot become observation background sources.
        backgrounds = [p for p in sorted(real) if groups[p] not in banned_groups]
        related_backgrounds = [p for p in backgrounds if real[p][context] & real[anchor][context]]
        other_backgrounds = [p for p in backgrounds if p not in set(related_backgrounds)]
        rng.shuffle(related_backgrounds)
        rng.shuffle(other_backgrounds)
        backgrounds = related_backgrounds + other_backgrounds
        pairs = []
        for pair_index in range(config['observation_pairs']):
            donor = donors[pair_index]
            # A controlled context substitution permits disjoint observations despite sparse real pools.
            base = next((p for p in backgrounds
                         if all(fingerprint({f:set(real[d][f]) if f == focus else set(real[anchor][f]) if f == context
                                             else set(real[p][f]) for f in FACETS}) not in candidate_fingerprints
                                for d in (anchor, donor))), None)
            require(base is not None, 'Cannot create observation without copying candidate facet content')
            backgrounds = [p for p in backgrounds if p != base] + [base]
            same_obs = synth(did, 'observation', pair_index*2, base, {context:anchor, focus:anchor})
            diff_obs = synth(did, 'observation', pair_index*2+1, base, {context:anchor, focus:donor})
            pair = [same_obs, diff_obs]
            rng.shuffle(pair)
            pairs.append(pair)
        designs.append(dict(design_id=did, anchor=anchor, context=context, focus=focus,
                            candidate_ids=pool, same_candidate_ids=[selected_same],
                            different_candidate_ids=[selected_different], outside_candidate_ids=[p for p in pool if p not in (selected_same, selected_different)],
                            observation_pairs=pairs, synthetic_fill_side=fill,
                            candidate_source_group='mixed' if fill else 'real_only', work_group=groups[anchor]))
    require(designs, 'No designs')
    require(set(d['focus'] for d in designs) == set(FACETS), 'Not all five focus facets are feasible; no output emitted')
    cases, intents, labels, queries = [], [], [], []
    for di, design in enumerate(designs):
        anchor, context, focus = (design[k] for k in ('anchor', 'context', 'focus'))
        for mi, mode in enumerate(config['query_modes']):
            user = users[(di*3+mi) % len(users)]['user_id']
            cutoff = start + dt.timedelta(minutes=di*3+mi+2)
            for direction in ('similar', 'different'):
                cid = opaque('D', config['structure_seed'], design['design_id'], mode, direction)
                cases.append(dict(case_id=cid, user_id=user, query_paper_id=anchor, context_facet=context,
                                  candidate_ids=list(design['candidate_ids']), cutoff=timestamp(cutoff)))
                directions = dict.fromkeys(FACETS, 'ignore')
                directions[context], directions[focus] = 'similar', direction
                weights = dict.fromkeys(FACETS, 0.)
                weights[context], weights[focus] = .6, .4
                intents.append(dict(case_id=cid, design_id=design['design_id'], focus_facet=focus,
                                    directions=directions, facet_importance=weights, query_mode=mode))
                labels.extend(dict(case_id=cid, candidate_id=p,
                                   relevance=grade(real[anchor], all_facets[p], context, focus, direction)) for p in design['candidate_ids'])
                previous = None
                if mode != 'none':
                    concept = sorted(real[anchor][context])[0]
                    texts = [f'{context}: {concept} papers']
                    if mode == 'clear':
                        focus_concept = sorted(real[anchor][focus])[0]
                        phrase = f'alternatives to {focus_concept}' if direction == 'different' else f'more papers using {focus_concept}'
                        texts.append(f'{context}: {concept}; {focus}: {phrase}')
                    for qi, text in enumerate(texts):
                        qid = opaque('Q', cid, qi)
                        queries.append(dict(query_id=qid, user_id=user, session_id=cid, text=text,
                                            parent_query_id=previous, timestamp=timestamp(cutoff-dt.timedelta(seconds=60-qi))))
                        previous = qid
    truths, by_design = {r['case_id']:r for r in intents}, {d['design_id']:d for d in designs}
    conditions = {}
    for seed in config['feedback_seeds']:
        for noise in config['noise_levels']:
            exposures, events, reaction_truth = [], [], []
            for case in cases:
                cid = case['case_id']
                intent = truths[cid]
                design = by_design[intent['design_id']]
                crng = random.Random(opaque('RNG', seed, cid))
                query_rows = [q for q in queries if q['session_id'] == cid]
                for pi, pair in enumerate(design['observation_pairs']):
                    shown = list(pair)
                    crng.shuffle(shown)
                    when = clock(case['cutoff'])-dt.timedelta(seconds=30-pi*5)
                    xid = opaque('EX', cid, pi)
                    exposures.append(dict(exposure_id=xid, user_id=case['user_id'], session_id=cid,
                                          query_id=query_rows[-1]['query_id'] if query_rows else None,
                                          paper_ids=shown, timestamp=timestamp(when)))
                    for order, pid in enumerate(shown):
                        g = grade(real[case['query_paper_id']], all_facets[pid], design['context'], design['focus'],
                                  intent['directions'][design['focus']])
                        utility = config['utility_satisfied'] if g == 2 else config['utility_unsatisfied']
                        draw = crng.gauss(0, 1)
                        utility += noise*draw
                        action = ('dislike', 'view', 'click', 'save', 'like')[sum(utility >= x for x in config['interaction_thresholds'])]
                        events.append(dict(user_id=case['user_id'], paper_id=pid, interaction_type=action,
                                           timestamp=timestamp(when+dt.timedelta(seconds=order+1)), session_id=cid, exposure_id=xid))
                        reaction_truth.append(dict(exposure_id=xid, paper_id=pid, grade=g, gaussian_draw=draw, utility=utility))
            conditions[f'seed_{seed}_noise_{noise:g}'] = dict(seed=seed, noise=noise, exposures=exposures,
                                                          interactions=events, reaction_truth=reaction_truth)
    fingerprints = collections.Counter(fingerprint(row) for row in synthetic.values())
    report = dict(designs=len(designs), unique_anchors=len({d['anchor'] for d in designs}), sessions=len(cases),
                  candidate_labels=len(labels), real_papers=len(papers), approved_real_facets=len(real),
                  synthetic_candidate_records=sum(p['role'] == 'candidate' for p in provenance),
                  synthetic_observation_records=sum(p['role'] == 'observation' for p in provenance),
                  unique_synthetic_facet_profiles=len(fingerprints), repeated_synthetic_profiles=sum(n-1 for n in fingerprints.values()),
                  designs_by_focus=dict(collections.Counter(d['focus'] for d in designs)),
                  designs_by_candidate_source=dict(collections.Counter(d['candidate_source_group'] for d in designs)),
                  skipped=skipped, observation_pairs_per_session=config['observation_pairs'],
                  conditions=len(conditions), observations_are_real_papers=False, semantic_review='pending',
                  evidence_unit='independent Gaussian feedback draws are not independent people or publications',
                  compliance_ceiling_at_5=.2, compliance_ceiling_at_10=.1)
    return dict(facets=all_facets, synthetic=synthetic, provenance=provenance, designs=designs,
                cases=cases, intents=intents, labels=labels, queries=queries, conditions=conditions,
                work_groups=groups, report=report)


def build(source_directory, config_path, output, dry_run=False):
    source_directory, output = Path(source_directory).resolve(), Path(output).resolve()
    require(source_directory.is_relative_to(HERE), 'Use a D-owned prepared source bundle')
    require(output.is_relative_to(HERE) and output != HERE and 'backup' not in output.relative_to(HERE).parts,
            'Output must stay inside D, outside backup')
    require(not output.exists(), 'Output already exists; choose a new version')
    source = load_bundle(source_directory)
    config = read_json(config_path)
    data = assemble(source, config)
    if dry_run:
        return data['report']
    write_json(output / 'config.json', config)
    write_rows(output / 'catalog/real_papers.jsonl', [source['papers'][p] for p in sorted(source['papers'])])
    write_rows(output / 'catalog/facets.jsonl', [dict(paper_id=p, source_kind='synthetic' if p in data['synthetic'] else 'real',
               representation='controlled_facets' if p in data['synthetic'] else 'A_silver',
               **{f:sorted(row[f]) for f in FACETS}) for p,row in sorted(data['facets'].items())])
    for name, values in source['history'].items():
        write_rows(output / 'history' / name, values)
    for name, key in [('sessions', 'cases'), ('search_events', 'queries')]:
        write_rows(output / 'generated' / (name+'.jsonl'), data[key])
    for name, key in [('session_intents', 'intents'), ('intent_labels', 'labels'), ('designs', 'designs'), ('synthetic_provenance', 'provenance')]:
        write_rows(output / 'ground_truth' / (name+'.jsonl'), data[key])
    write_json(output / 'ground_truth/work_groups.json', data['work_groups'])
    for name, condition in data['conditions'].items():
        folder = output / 'conditions' / name
        write_rows(folder / 'generated/exposures.jsonl', condition['exposures'])
        write_rows(folder / 'generated/interactions_train.jsonl', condition['interactions'])
        write_rows(folder / 'ground_truth/reaction_provenance.jsonl', condition['reaction_truth'])
    write_json(output / 'generation_report.json', data['report'])
    code = {p.name:sha(p) for p in (Path(__file__), HERE / 'prepare_source.py', HERE / 'validate_observation_data.py')}
    manifest = dict(protocol='d_observation_v1', status='pending_validation', dataset_kind='controlled_mock_with_synthetic_candidates',
                    source_directory=source_directory.relative_to(HERE).as_posix(), source_manifest_sha256=source['manifest_sha256'],
                    code_sha256=code, conditions={name:dict(seed=c['seed'], noise=c['noise']) for name,c in data['conditions'].items()},
                    semantic_review='pending', no_experiments_run=True,
                    files={p.relative_to(output).as_posix():sha(p) for p in output.rglob('*') if p.is_file()})
    write_json(output / 'manifest.json', manifest)
    from validate_observation_data import validate_dataset
    try:
        validation = validate_dataset(output, allow_pending=True)
    except Exception as error:
        write_json(output / 'FAILED.json', dict(error=str(error), status='invalid_do_not_use'))
        raise
    write_json(output / 'validation_report.json', validation)
    manifest['files']['validation_report.json'] = sha(output / 'validation_report.json')
    manifest['status'] = 'structurally_valid'
    write_json(output / 'manifest.json', manifest)
    return data['report']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=HERE / 'inputs/base_v1')
    parser.add_argument('--config', type=Path, default=HERE / 'observation_config.json')
    parser.add_argument('--output', type=Path, default=HERE / 'datasets/observation_v1')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.config, args.output, args.dry_run), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
