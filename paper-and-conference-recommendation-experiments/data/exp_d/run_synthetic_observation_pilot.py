"""Controlled synthetic-observation pilot; never modifies the real A/C/D handoff.

Run from the experiments project: python -B data/exp_d/run_synthetic_observation_pilot.py
Source defaults to the validated workspace snapshot. Output is a separate D overlay,
not a canonical real corpus or an A silver handoff. No model or network is used.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import sys


HERE = Path(__file__).resolve().parent
PROTOCOL = 'd_synthetic_observation_overlay_v1'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows), encoding='utf-8')


def select_cases(cases, truth, facets, seed):
    """One case per focus/direction/query-mode cell: 30 cases, without metric selection."""
    rng = random.Random(seed)
    chosen, used = [], set()
    for focus in facets:
        for direction in ('similar', 'different'):
            for mode in ('clear', 'ambiguous', 'none'):
                options = sorted((c for c in cases if truth[c['case_id']]['focus_facet'] == focus
                                  and truth[c['case_id']]['directions'][focus] == direction
                                  and truth[c['case_id']]['query_mode'] == mode), key=lambda c: c['case_id'])
                require(options, f'No source case for {focus}/{direction}/{mode}')
                unused = [c for c in options if c['query_paper_id'] not in used]
                case = rng.choice(unused or options)
                chosen.append(case)
                used.add(case['query_paper_id'])
    return sorted(chosen, key=lambda c: c['case_id'])


def make_observations(cases, truth, real_facets, queries, config, seed, noise, pair_count, api):
    """Generator-only truth access. Public rows have no true focus/direction/weights."""
    rng = random.Random(seed)
    synthetic, provenance, exposures, events = {}, [], [], []
    for case in cases:
        cid, anchor_id = case['case_id'], case['query_paper_id']
        anchor = real_facets[anchor_id]
        intent = truth[cid]
        focus = intent['focus_facet']
        # Donors supply existing concept vocabulary, never fabricated claims/results.
        donors = sorted(pid for pid, row in real_facets.items()
                        if row[focus] and not row[focus] & anchor[focus])
        require(len(donors) >= pair_count, f'Insufficient disjoint focus donors: {cid}')
        donors = rng.sample(donors, pair_count)
        session_queries = sorted((q for q in queries if q['session_id'] == cid), key=lambda q: q['timestamp'])
        cutoff = api['validate_time'](case['cutoff'])
        first_time = cutoff - dt.timedelta(seconds=5 * pair_count + 2)
        require(not session_queries or api['validate_time'](session_queries[-1]['timestamp']) < first_time,
                'Not enough time between query and cutoff for pilot observations')
        for i, donor in enumerate(donors):
            ids = [f'DOBS_{cid}_{i:02}_{j}' for j in range(2)]
            rng.shuffle(ids)  # ID/order must not encode the same/different side.
            same_id, different_id = ids
            for pid, is_same in ((same_id, True), (different_id, False)):
                row = {f: set(values) for f, values in anchor.items()}
                row[focus] = set(anchor[focus] if is_same else real_facets[donor][focus])
                synthetic[pid] = row
                provenance.append(dict(paper_id=pid, synthetic=True, source_anchor_id=anchor_id,
                                       focus_donor_id=anchor_id if is_same else donor,
                                       true_focus=focus, same_focus=is_same,
                                       annotation_kind='controlled_constructed_not_A_silver'))
            shown = [same_id, different_id]
            rng.shuffle(shown)
            time = first_time + dt.timedelta(seconds=5 * i)
            xid = f'DOBS_{cid}_X{i:02}'
            exposures.append(dict(exposure_id=xid, user_id=case['user_id'], session_id=cid,
                                  query_id=session_queries[-1]['query_id'] if session_queries else None,
                                  paper_ids=shown, timestamp=api['timestamp'](time)))
            for j, pid in enumerate(shown):
                grade = api['session_grade'](anchor, synthetic[pid], focus,
                                             intent['directions'][focus], case['context_facet'])
                utility = (.7 if grade == 2 else .05) + rng.gauss(0, noise)
                events.append(dict(user_id=case['user_id'], paper_id=pid,
                                   interaction_type=api['behavior'](utility, config),
                                   timestamp=api['timestamp'](time + dt.timedelta(seconds=j + 1)),
                                   session_id=cid, exposure_id=xid))
    return synthetic, provenance, exposures, events


def validate_overlay(cases, truth, labels, queries, real_facets, synthetic, provenance,
                     exposures, events, users, config, pair_count, api):
    require(not set(synthetic) & set(real_facets), 'Synthetic IDs collide with real IDs')
    require(len(synthetic) == 2 * pair_count * len(cases), 'Wrong synthetic count')
    require(len({p['paper_id'] for p in provenance}) == len(synthetic), 'Duplicate provenance')
    cases_by_id = {c['case_id']: c for c in cases}
    used = set()
    for exposure in exposures:
        case = cases_by_id[exposure['session_id']]
        require(not set(exposure['paper_ids']) & (set(case['candidate_ids']) | {case['query_paper_id']}),
                'Observation overlaps real anchor/candidates')
        require(set(exposure['paper_ids']) <= set(synthetic), 'Non-synthetic observation in pilot')
        require(not used & set(exposure['paper_ids']), 'Observation ID reused')
        used.update(exposure['paper_ids'])
    for p in provenance:
        require(p['source_anchor_id'] in real_facets and p['focus_donor_id'] in real_facets,
                'Unknown vocabulary donor')
        require(p['synthetic'] is True, 'Missing synthetic provenance')
    all_facets = {**real_facets, **synthetic}
    report = dict(shortfall=len(users) * config['sessions_per_user'] - len(cases),
                  actual_cases=len(cases), actual_pairs=len(labels))
    # Apply the existing D structural/matching/time/label checks to the overlay.
    # This is NOT a claim that synthetic records passed A's real-paper handoff.
    api['check_d'](dict(**{'sessions.jsonl': cases, 'search_events.jsonl': queries,
                         'exposures.jsonl': exposures, 'interactions_train.jsonl': events}),
                   {'session_intents.jsonl': [truth[c['case_id']] for c in cases],
                    'intent_labels.jsonl': labels}, all_facets, config, report, users)
    require(len(events) == 2 * len(exposures), 'Missing observation reactions')
    counts = collections.Counter(x['session_id'] for x in exposures)
    require(all(counts[c['case_id']] == pair_count for c in cases), 'Wrong pair coverage')


def public_predictions(cases, real_facets, observed_facets, c_history, c_queries, queries,
                       exposures, events, config, vectors, api):
    """Public scorer interface: deliberately has no truth/labels/provenance argument."""
    predictions = []
    for cutoff in sorted({c['cutoff'] for c in cases}):
        batch = [c for c in cases if c['cutoff'] == cutoff]
        users = {c['user_id'] for c in batch}
        def prefix(rows):
            return [r for r in rows if r['user_id'] in users
                    and api['validate_time'](r['timestamp']) < api['validate_time'](cutoff)]
        profiles = api['facet_profiles'](prefix(c_history), prefix(c_queries), real_facets, cutoff)
        q, x, history = prefix(queries), prefix(exposures), prefix(events)
        for case in batch:
            weights = profiles[case['user_id']]['facet_importance']
            similar = dict.fromkeys(api['FACETS'], 'similar')
            behavior, bc = api['direction_estimate'](case, history, [], x, observed_facets,
                margin=config['direction_margin'], minimum_pairs=config['min_direction_pairs'], use_search=False)
            searched, sc = api['direction_estimate'](case, history, q, x, observed_facets,
                margin=config['direction_margin'], minimum_pairs=config['min_direction_pairs'])
            for model, w, directions, confidence in (
                ('fixed_similar', dict.fromkeys(api['FACETS'], .2), similar, dict.fromkeys(api['FACETS'], 1.)),
                ('profile_similar', weights, similar, dict.fromkeys(api['FACETS'], 1.)),
                ('direction_behavior', weights, behavior, bc), ('direction_search', weights, searched, sc)):
                row = api['ranked'](case, model, api['intent_scores'](case, w, directions, vectors))
                row.update(facet_importance=w, directions=directions, direction_confidence=confidence)
                predictions.append(row)
    return predictions


def result_bundle(destination, predictions, cases, truth, labels, groups, seed, noise, api):
    judged = {c['case_id']: {} for c in cases}
    for row in labels:
        judged[row['case_id']][row['candidate_id']] = row['relevance']
    details = api['evaluate_predictions'](predictions, cases, judged, groups, [5, 10], truth)
    report = dict(experiment='d', evaluation_version=PROTOCOL, dataset_kind='synthetic_observation_overlay',
                  dataset_status='pilot', protocol=PROTOCOL, cases=len(cases), seed=seed, noise_std=noise,
                  summary=api['aggregate'](details), notes=[
                      'Real source anchors, candidates, labels, queries and C profiles are unchanged.',
                      'Synthetic observations are controlled facet constructions, NOT real papers or A silver.',
                      'Repeated matched synthetic profiles are feedback draws, not independent real-paper evidence.',
                      'Candidate TF-IDF is frozen on original real facets in both conditions; no IDF confound.',
                      'No-observation vs synthetic-observation conditions share every input except observations/reactions.',
                      'This pilot establishes behavior under the specified simulator, not human relevance or novelty.',
                      'Hidden intent is used by simulator and evaluator only; public scorer receives no hidden fields.'
                  ])
    write_rows(destination / 'predictions.jsonl', predictions)
    write_rows(destination / 'details.jsonl', details)
    write_json(destination / 'report.json', report)
    (destination / 'report.md').write_text(api['markdown_report'](report), encoding='utf-8')
    fields = ['model', 'group', 'cases', 'positive_cases'] + list(report['summary'][0]['defined_cases'])
    with (destination / 'summary.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(report['summary'])
    focus_metrics = []
    for model in sorted({r['model'] for r in predictions}):
        for group in ['overall', 'clear', 'ambiguous', 'none']:
            rows = [r for r in predictions if r['model'] == model
                    and (group == 'overall' or groups[r['case_id']] == group)]
            pairs = [(truth[r['case_id']]['directions'][truth[r['case_id']]['focus_facet']],
                      r['directions'][truth[r['case_id']]['focus_facet']]) for r in rows]
            f1 = []
            for label in ('similar', 'different'):
                tp = sum(t == p == label for t, p in pairs)
                fp = sum(p == label and t != label for t, p in pairs)
                fn = sum(t == label and p != label for t, p in pairs)
                f1.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.)
            focus_metrics.append(dict(model=model, group=group, cases=len(rows),
                focus_accuracy=sum(t == p for t, p in pairs) / len(pairs),
                focus_coverage=sum(p in ('similar', 'different') for _, p in pairs) / len(pairs),
                focus_macro_f1=sum(f1) / 2))
    write_json(destination / 'focus_metrics.json', focus_metrics)
    write_json(destination / 'manifest.json', dict(protocol=PROTOCOL,
        files={p.name: digest(p) for p in sorted(destination.iterdir()) if p.is_file()},
        seed=seed, noise_std=noise))
    return report, focus_metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=HERE / 'workspace')
    parser.add_argument('--output', type=Path, default=HERE / 'evaluation/synthetic_observation_pilot_v1')
    parser.add_argument('--selection-seed', type=int, default=20261015)
    parser.add_argument('--seeds', type=int, nargs='+', default=[42, 43, 44])
    parser.add_argument('--noise-levels', type=float, nargs='+', default=[.2, .5])
    parser.add_argument('--pairs', type=int, default=4)
    args = parser.parse_args()
    source, output = args.source_root.resolve(), args.output.resolve()
    require(HERE in output.parents and 'workspace' not in output.relative_to(HERE).parts,
            'Pilot output must stay in exp_d, outside the source workspace')
    require(not output.exists(), 'Pilot output exists; choose a new --output (no overwrite)')
    require(len(set(args.seeds)) == len(args.seeds) and args.seeds, 'Duplicate/empty seeds')
    require(len(set(args.noise_levels)) == len(args.noise_levels)
            and all(math.isfinite(x) and 0 <= x <= 1 for x in args.noise_levels), 'Invalid noise levels')
    require(args.pairs >= 2 and args.pairs <= 4, 'Pilot uses two to four independent feedback draws')
    # Resolve all shared imports from the validated source snapshot, never patch ROOT/hash gates.
    sys.path[:0] = [str(source / 'scripts'), str(source)]
    from experiment_io import FACETS, concept_sets, load_silver
    from validate_experiments import validate_experiment, check_d
    from validate_all import validate_time
    from data.experiment_common import behavior, session_grade, timestamp
    from baseline_common import (aggregate, facet_vectors, facet_profiles, direction_estimate,
                                 intent_scores, ranked)
    from experiment_runner import evaluate_predictions, markdown_report
    api = dict(FACETS=FACETS, check_d=check_d, validate_time=validate_time, behavior=behavior,
               session_grade=session_grade, timestamp=timestamp, aggregate=aggregate,
               facet_vectors=facet_vectors, facet_profiles=facet_profiles, direction_estimate=direction_estimate,
               intent_scores=intent_scores, ranked=ranked, evaluate_predictions=evaluate_predictions,
               markdown_report=markdown_report)
    source_manifest = validate_experiment(source, 'd')
    config = source_manifest['config']
    require(args.pairs >= config['min_direction_pairs'], 'Pair count below source estimator minimum')
    watched = {**source_manifest['input_hashes'], **source_manifest['files'],
               **source_manifest['generator_hashes']}
    watched[config['output_dir'] + '/manifest.json'] = digest(source / config['output_dir'] / 'manifest.json')
    for name in ['scripts/baseline_common.py', 'scripts/experiment_runner.py', 'scripts/validate_experiments.py',
                 'scripts/validate_all.py', 'scripts/exp_d/run_exp_d.py', 'scripts/download_sources.py']:
        watched[name] = digest(source / name)
    require(all(digest(source / name) == value for name, value in watched.items()), 'Source hash mismatch')
    _, raw, metadata, _ = load_silver(source, Path(config['facets_path']).parent)
    real_facets = concept_sets(raw, metadata)
    observed_dir, hidden_dir = source / config['output_dir'], source / config['truth_dir']
    all_cases = read_rows(observed_dir / 'sessions.jsonl')
    truth = {r['case_id']: r for r in read_rows(hidden_dir / 'session_intents.jsonl')}
    cases = select_cases(all_cases, truth, FACETS, args.selection_seed)
    selected = {c['case_id'] for c in cases}
    truth = {cid: truth[cid] for cid in selected}
    labels = [r for r in read_rows(hidden_dir / 'intent_labels.jsonl') if r['case_id'] in selected]
    queries = [r for r in read_rows(observed_dir / 'search_events.jsonl') if r['session_id'] in selected]
    handoff = source / Path(config['users_path']).parent
    users = read_rows(source / config['users_path'])
    c_history, c_queries = read_rows(handoff / 'interactions_train.jsonl'), read_rows(handoff / 'search_events.jsonl')
    vectors = facet_vectors(real_facets)  # Frozen real-corpus representation for every arm.
    groups = {cid: t['query_mode'] for cid, t in truth.items()}
    control = public_predictions(cases, real_facets, real_facets, c_history, c_queries, queries,
                                 [], [], config, vectors, api)
    # Exact parity with the original public baseline before the intervention.
    spec = importlib.util.spec_from_file_location('source_d_baseline', source / 'scripts/exp_d/run_exp_d.py')
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    reference = []
    for cutoff in sorted({c['cutoff'] for c in cases}):
        batch = [c for c in cases if c['cutoff'] == cutoff]
        batch_users = {c['user_id'] for c in batch}
        def prefix(rows):
            return [r for r in rows if r['user_id'] in batch_users and validate_time(r['timestamp']) < validate_time(cutoff)]
        options = dict(cutoff=cutoff, profile_history=prefix(c_history), profile_searches=prefix(c_queries),
                       searches=prefix(c_queries + queries), exposures=[],
                       direction_margin=config['direction_margin'], min_direction_pairs=config['min_direction_pairs'])
        reference.extend(baseline.predict({}, real_facets, batch, [], options))
    require(control == reference, 'Control differs from source baseline')
    write_rows(output / 'generated/sessions.jsonl', cases)
    write_rows(output / 'generated/search_events.jsonl', queries)
    write_rows(output / 'ground_truth/session_intents.jsonl', [truth[c['case_id']] for c in cases])
    write_rows(output / 'ground_truth/intent_labels.jsonl', labels)
    all_focus = []
    for seed in args.seeds:
        for noise in args.noise_levels:
            run = output / f'seed_{seed}_noise_{noise:g}'
            synthetic, provenance, exposures, events = make_observations(
                cases, truth, real_facets, queries, config, seed, noise, args.pairs, api)
            validate_overlay(cases, truth, labels, queries, real_facets, synthetic, provenance,
                             exposures, events, users, config, args.pairs, api)
            # Same seed + noise must reproduce the complete overlay exactly.
            require((synthetic, provenance, exposures, events) == make_observations(
                cases, truth, real_facets, queries, config, seed, noise, args.pairs, api), 'Non-deterministic overlay')
            augmented = public_predictions(cases, real_facets, {**real_facets, **synthetic},
                c_history, c_queries, queries, exposures, events, config, vectors, api)
            predictions = []
            for arm, rows in [('no_observations', control), ('synthetic_observations', augmented)]:
                predictions.extend(dict(r, model=r['model'] + '__' + arm) for r in rows)
                for case in cases:  # Evaluator-owned privileged reference only.
                    t = truth[case['case_id']]
                    row = ranked(case, 'oracle_intent__' + arm,
                                 intent_scores(case, t['facet_importance'], t['directions'], vectors))
                    row.update(directions=t['directions'], facet_importance=t['facet_importance'], privileged_information=True)
                    predictions.append(row)
            # Observation-only intervention cannot change fixed/profile predictions.
            for model in ('fixed_similar', 'profile_similar'):
                require([r['ranking'] for r in control if r['model'] == model] ==
                        [r['ranking'] for r in augmented if r['model'] == model], 'Control scorer changed')
            write_rows(run / 'generated/observation_facets.jsonl',
                       [dict(paper_id=pid, **{f: sorted(v) for f, v in row.items()}) for pid, row in sorted(synthetic.items())])
            write_rows(run / 'generated/observation_papers.jsonl', [dict(paper_id=pid, synthetic=True,
                title='Hypothetical controlled observation',
                abstract='Synthetic facet description; not a published paper or scientific result. ' +
                         '; '.join(f + ': ' + ', '.join(sorted(row[f])) for f in FACETS))
                for pid, row in sorted(synthetic.items())])
            write_rows(run / 'generated/exposures.jsonl', exposures)
            write_rows(run / 'generated/interactions_train.jsonl', events)
            write_rows(run / 'ground_truth/observation_provenance.jsonl', provenance)
            _, focus = result_bundle(run / 'results', predictions, cases, truth, labels, groups, seed, noise, api)
            all_focus.extend(dict(row, seed=seed, noise_std=noise) for row in focus)
            print(f'PASS seed={seed} noise={noise:g}: {len(cases)} cases, {len(exposures)} pairs, {len(events)} reactions', flush=True)
    require(all(digest(source / name) == value for name, value in watched.items()), 'Source changed during pilot')
    write_json(output / 'focus_sensitivity.json', all_focus)
    write_json(output / 'manifest.json', dict(protocol=PROTOCOL, source_root=str(source),
        source_hashes=watched, code_sha256=digest(Path(__file__)),
        selection_seed=args.selection_seed, selected_case_ids=[c['case_id'] for c in cases],
        selection_policy='one_case_per_focus_direction_query_mode_prefer_unique_anchor_not_metric_selected',
        unique_anchors=len({c['query_paper_id'] for c in cases}), pairs_per_case=args.pairs,
        seeds=args.seeds, noise_levels=args.noise_levels, source_unchanged=True,
        synthetic_scope='observation_only_controlled_facets_not_real_corpus_or_A_silver',
        files={p.relative_to(output).as_posix(): digest(p) for p in sorted(output.rglob('*')) if p.is_file()}))
    print(f'Pilot complete: {output}', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        print(f'FAILED synthetic D pilot: {error}', file=sys.stderr)
        raise SystemExit(1)
