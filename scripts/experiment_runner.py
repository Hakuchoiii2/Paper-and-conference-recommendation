"""Validate datasets, run CPU scorers, then evaluate against separate truth."""
import argparse
import csv
import json
import math
from pathlib import Path

from baseline_common import (BEHAVIOR_GRADES, BEHAVIOR_WEIGHTS, aggregate, ranking_metrics,
                             facet_vectors, intent_scores, ranked)
from experiment_io import ROOT, FACETS, BEHAVIOR_FILES, concept_sets, load_silver, output_paths, project_path
from build_corpus import read_jsonl, write_jsonl
from download_sources import sha256, write_json
from validate_all import require, validate_temporal, validate_time
from validate_experiments import validate_experiment

RESULT_FILES = {'predictions.jsonl', 'details.jsonl', 'report.json', 'summary.csv', 'report.md', 'manifest.json'}


def evaluation_cases(root, experiment, config, split):
    directory,hidden = output_paths(root,config,experiment)
    history = [] if experiment == 'b' else read_jsonl(directory / 'interactions_train.jsonl')
    if experiment == 'b':
        selected = set(json.loads((directory / 'splits.json').read_text(encoding='utf-8'))[split])
        cases = [dict(r,case_id=r['query_id']) for r in read_jsonl(directory / 'retrieval_queries.jsonl')
                 if r['query_id'] in selected]
        groups = {r['case_id']:'retrieval' for r in cases}
        labels = {r['case_id']:{} for r in cases}
        for r in read_jsonl(hidden / 'retrieval_labels.jsonl'):
            if r['query_id'] in labels:
                labels[r['query_id']][r['candidate_id']] = r['relevance']
    elif experiment == 'd':
        cases = read_jsonl(directory / 'sessions.jsonl')
        labels = {r['case_id']:{} for r in cases}
        for r in read_jsonl(hidden / 'intent_labels.jsonl'):
            labels[r['case_id']][r['candidate_id']] = r['relevance']
        intents = read_jsonl(hidden / 'session_intents.jsonl')
        groups = {r['case_id']:r['query_mode'] for r in intents}
        history = read_jsonl(project_path(root,config['users_path']).parent / 'interactions_train.jsonl') + history
    else:
        cases = read_jsonl(directory / 'cases.jsonl')
        future = read_jsonl(hidden / 'interactions_test.jsonl')
        labels = {}
        for case in cases:
            candidates = set(case['candidate_ids'])
            cutoff = validate_time(case['cutoff'])
            end = validate_time(config['period_boundaries'][case['period']]) if experiment == 'e' else None
            labels[case['case_id']] = {r['paper_id']:BEHAVIOR_GRADES[r['interaction_type']]
                for r in future if r['user_id'] == case['user_id'] and r['paper_id'] in candidates
                and validate_time(r['timestamp']) >= cutoff and (end is None or validate_time(r['timestamp']) < end)}
        groups = {r['case_id']:'holdout' for r in cases}
        if experiment == 'e':
            users = json.loads((hidden / 'period_metadata.json').read_text(encoding='utf-8'))['groups']
            groups = {r['case_id']:users[r['user_id']] for r in cases}
    require(cases,f'No cases in selected {split} split / holdout')
    return cases,labels,groups,history


def evaluation_truth(root, experiment, config, cases):
    _,hidden = output_paths(root,config,experiment)
    if experiment == 'b':
        return {}
    if experiment == 'd':
        return {r['case_id']:r for r in read_jsonl(hidden / 'session_intents.jsonl')}
    name = 'latent_user_profiles.jsonl' if experiment == 'c' else 'temporal_profiles.jsonl'
    profiles = {(r['user_id'],r.get('period',0)):r for r in read_jsonl(hidden / name)}
    return {r['case_id']:profiles[r['user_id'],r.get('period',0)] for r in cases}


def evaluate_predictions(predictions, cases, labels, groups, ks, truth=None):
    truth = truth or {}
    by_id = {c['case_id']:c for c in cases}
    require(predictions,'Scorer produced no predictions')
    seen,models,details = set(),set(),[]
    for row in predictions:
        key = row['case_id'],row['model']
        require(key not in seen and row['case_id'] in by_id,'Unknown or duplicate prediction case/model')
        seen.add(key); models.add(row['model'])
        case,judged = by_id[row['case_id']],labels[row['case_id']]
        require(all(type(v['score']) in (int,float) and math.isfinite(v['score']) for v in row['ranking']),'Non-finite score')
        ranking = [v['paper_id'] for v in row['ranking']]
        require(set(ranking) == set(case['candidate_ids']),'Prediction candidates differ from observable pool')
        require(row['ranking'] == sorted(row['ranking'],key=lambda v:(-v['score'],v['paper_id'])),'Prediction is not ordered')
        metrics = ranking_metrics(ranking,judged,ks)
        hidden = truth.get(row['case_id'])
        direction_pairs = []
        if hidden:
            weights = row.get('facet_importance')
            metrics['importance_mae'] = None
            if weights is not None:
                require(set(weights) == set(FACETS) and all(type(v) in (int,float) and math.isfinite(v) and v >= 0
                        for v in weights.values()) and math.isclose(sum(weights.values()),1,abs_tol=1e-8),
                        'Invalid predicted importance')
                metrics['importance_mae'] = sum(abs(weights[f]-hidden['facet_importance'][f]) for f in FACETS)/len(FACETS)
            if 'directions' in hidden:
                directions = row.get('directions',dict.fromkeys(FACETS,'unknown'))
                require(set(directions) == set(FACETS) and set(directions.values()) <=
                        {'similar','different','ignore','unknown'},'Invalid predicted directions')
                active = [f for f in FACETS if hidden['directions'][f] != 'ignore']
                direction_pairs = [(hidden['directions'][f],directions[f]) for f in active]
                metrics['direction_accuracy'] = sum(t == p for t,p in direction_pairs)/len(active)
                metrics['direction_coverage'] = sum(p in ('similar','different') for _,p in direction_pairs)/len(active)
                for k in ks:
                    metrics[f'intent_compliance@{k}'] = sum(judged[pid] == 2 for pid in ranking[:k])/len(ranking[:k])
        row_groups = [groups[row['case_id']]]
        if 'period' in case:
            row_groups += [f"period_{case['period']}",f"{groups[row['case_id']]}_period_{case['period']}"]
        details.append(dict(case_id=row['case_id'],model=row['model'],group=groups[row['case_id']],groups=row_groups,
                            cutoff=case.get('cutoff'),candidates=len(judged),
                            positive_candidates=sum(v > 0 for v in judged.values()),labels=judged,metrics=metrics,
                            direction_pairs=direction_pairs))
    require(seen == {(cid,model) for cid in by_id for model in models},'Missing model/case predictions')
    return details


def markdown_report(report):
    metrics = list(report['summary'][0]['defined_cases'])
    lines = [f"# Experiment {report['experiment'].upper()} — CPU methods", '',
             f"Dataset: **{report['dataset_kind']}**, status: **{report['dataset_status']}**, "
             f"evaluation: **{report['protocol']}**, cases: **{report['cases']}**.", '',
             '| Model | Group | Cases | Positive cases | ' + ' | '.join(metrics) + ' |',
             '|---|---|---:|---:|' + '---:|' * len(metrics)]
    for row in report['summary']:
        scores = ['N/A' if row[key] is None else f'{row[key]:.4f}' for key in metrics]
        lines.append(f"| {row['model']} | {row['group']} | {row['cases']} | {row['positive_cases']} | "
                     + ' | '.join(scores) + ' |')
    lines.extend(['', '## Protocol and limits', ''] + ['- ' + note for note in report['notes']])
    lines.extend(['', 'Per-case labels and metrics: `details.jsonl`; ranked scores: `predictions.jsonl`.',
                  'Undefined nDCG/Recall/MRR for cases without positives are excluded from their means;',
                  '`defined_cases` in report.json records each metric denominator.', ''])
    return '\n'.join(lines)


def check_destination(destination, overwrite):
    if destination.exists():
        entries = list(destination.iterdir())
        require(overwrite or not entries, f'Results already exist: {destination}; use --overwrite or a new --output')
        require(all(path.is_file() and not path.is_symlink() and path.name in RESULT_FILES for path in entries),
                'Result directory contains unrelated files or another active run')


def run_experiment(root, experiment, predictor, *, config_path=None, split='test', ks=(5, 10),
                   half_life_days=30, output=None, allow_shortfall=False, overwrite=False, dry_run=False):
    root = Path(root).resolve()
    require(experiment in ('b', 'c', 'd', 'e'), 'Expected experiment B–E')
    require(split in ('train', 'dev', 'test'), 'Invalid evaluation split')
    require(ks and all(type(k) is int and k > 0 for k in ks), 'Invalid metric cutoffs')
    require(math.isfinite(half_life_days) and half_life_days > 0, 'Half-life must be positive and finite')
    ks = sorted(set(ks))
    config_path = config_path or f'configs/exp_{experiment}.json'
    dataset = validate_experiment(root, experiment, config_path, allow_shortfall=allow_shortfall)
    config = dataset['config']
    manifest_path = (project_path(root, config['output_dir']) / 'manifest.json').relative_to(root).as_posix()
    inputs = {**dataset['input_hashes'], **dataset['files'], manifest_path: sha256(root / manifest_path)}
    papers, raw, metadata, _ = load_silver(root, Path(config['facets_path']).parent)
    facets = concept_sets(raw, metadata)
    cases, labels, groups, history = evaluation_cases(root, experiment, config, split)
    options = dict(seed=config['seed'])
    if experiment == 'b':
        options['fixed_weights'] = config['fixed_weights']
    elif experiment == 'd':
        options.update(direction_margin=config['direction_margin'],min_direction_pairs=config['min_direction_pairs'])
        require(type(options['min_direction_pairs']) is int and options['min_direction_pairs'] >= 1
                and type(options['direction_margin']) in (int,float)
                and math.isfinite(options['direction_margin']) and options['direction_margin'] > 0,
                'Invalid direction thresholds')
    elif experiment == 'e':
        options['half_life_days'] = half_life_days
    protocol = f'fixed_candidates_{split}' if experiment == 'b' else 'session_prefix' if experiment == 'd' else \
               'rolling_period_prefix' if experiment == 'e' else 'history_holdout'
    destination = project_path(root,output or f"results/exp_{experiment}/" + (split if experiment == 'b' else 'holdout'))
    require(root / 'results' in destination.parents,'Results must stay under project/results')
    directory,_ = output_paths(root,config,experiment)
    queries = [] if experiment == 'b' else read_jsonl(directory / 'search_events.jsonl')
    exposures = [] if experiment == 'b' else read_jsonl(directory / 'exposures.jsonl')
    profile_history,profile_searches = [],[]
    if experiment == 'd':
        handoff = project_path(root,config['users_path']).parent
        profile_history = read_jsonl(handoff / 'interactions_train.jsonl')
        profile_searches = read_jsonl(handoff / 'search_events.jsonl')
        queries = profile_searches + queries
    truth = evaluation_truth(root,experiment,config,cases)
    require(inputs == {name: sha256(project_path(root, name)) for name in inputs},
            'Inputs changed while loading; rerun after dataset generation finishes')
    if dry_run:
        return dict(experiment=experiment, cases=len(cases), protocol=protocol, output=str(destination), dry_run=True)
    check_destination(destination, overwrite)
    predictions = []
    if experiment == 'b':
        predictions = predictor(papers,facets,cases,history,options)
    else:
        cutoffs = sorted({c['cutoff'] for c in cases},key=validate_time)
        for cutoff in cutoffs:
            batch = [c for c in cases if c['cutoff'] == cutoff]
            users = {c['user_id'] for c in batch}
            def prefix(rows):
                return [r for r in rows if r['user_id'] in users
                        and validate_time(r['timestamp']) < validate_time(cutoff)]
            current = dict(options,cutoff=cutoff,searches=prefix(queries),exposures=prefix(exposures))
            if experiment == 'd':
                current.update(profile_history=prefix(profile_history),profile_searches=prefix(profile_searches))
            if experiment == 'e':
                current['recent_start'] = config['period_boundaries'][batch[0]['period']-2]
            predictions.extend(predictor(papers,facets,batch,prefix(history),current))
    if experiment == 'd':
        # The oracle is evaluator-owned; public scorers never receive hidden intent or weights.
        vectors = facet_vectors(facets)
        for case in cases:
            intent = truth[case['case_id']]
            row = ranked(case,'oracle_intent',intent_scores(case,intent['facet_importance'],intent['directions'],vectors))
            row.update(facet_importance=intent['facet_importance'],directions=intent['directions'],
                       privileged_information=True)
            predictions.append(row)
    details = evaluate_predictions(predictions,cases,labels,groups,ks,truth)
    notes = [
        'Contract/evaluation 2.0: C is preference inference; D is automatic session direction (formerly D/C).',
        'B–E are mock scenarios on real papers/silver facets; scores do not establish human relevance or novelty.',
        'Public scorers receive only observable prefixes and fixed candidate IDs, never labels or latent profiles.',
        'All methods in each case share candidates and cutoffs; unobserved papers are not labeled negative.',
        'nDCG gain is 2^grade-1; positive means grade > 0. Ties use ascending paper ID.',
        'TF-IDF and query parsing are lexical CPU references; parameters are fixed before test.',
        'A facet-importance MAE exists only for models returning normalized facet importance.'
    ]
    if experiment == 'b':
        notes.append('B labels are weighted concept-overlap rules, not independent expert relevance judgments.')
    if experiment == 'd':
        notes += [
            'Oracle_intent alone receives true session directions/importance, in the evaluator; it is a privileged reference.',
            'Direction macro-F1 pools active similar/different facets across cases; unknown counts as a missed prediction.',
            'True ignore facets are excluded from direction F1/coverage; unknown is not interpreted as ignore.',
            'D controls one similar context facet and one similar/different focus facet, across all five facets; arbitrary multi-facet combinations need additional scenarios.',
            'Intent compliance counts grade=2; grade=1 is related but violates the requested direction.',
            'Matched exposure pairs control other facets overlap states; this is not a causal claim on real logs.'
        ]
    if experiment == 'e':
        notes.append('E evaluates periods 2/3/4; each scorer sees only previous-period history, searches and exposures.')
    if dataset['status'] == 'partial':
        notes.append('Dataset has an explicit target shortfall; results cover only the available cases.')
    report = dict(evaluation_version='2.0', experiment=experiment, dataset_kind=dataset['dataset_kind'],
                  dataset_status=dataset['status'], protocol=protocol, cases=len(cases), ks=ks, options=options,
                  behavior_weights=BEHAVIOR_WEIGHTS if history else None,
                  summary=aggregate(details), notes=notes)
    require(inputs == {name: sha256(project_path(root, name)) for name in inputs},
            'Inputs changed while scoring; results not published')
    destination.mkdir(parents=True, exist_ok=True)
    lock = destination / '.run.lock'
    handle = lock.open('x', encoding='utf-8')
    try:
        with handle:
            # Check again after acquiring the lock; never delete unrelated user files.
            existing = [path for path in destination.iterdir() if path != lock]
            require(overwrite or not existing, 'Another run already published results')
            require(all(path.is_file() and not path.is_symlink() and path.name in RESULT_FILES for path in existing),
                    'Unrelated result files')
            write_jsonl(destination / 'predictions.jsonl', predictions)
            write_jsonl(destination / 'details.jsonl', details)
            write_json(destination / 'report.json', report)
            fields = ['model', 'group', 'cases', 'positive_cases'] + list(report['summary'][0]['defined_cases'])
            csv_path = destination / 'summary.csv.tmp'
            with csv_path.open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(report['summary'])
            csv_path.replace(destination / 'summary.csv')
            (destination / 'report.md').write_text(markdown_report(report), encoding='utf-8')
            code = ['scripts/baseline_common.py', 'scripts/experiment_runner.py',
                    f'scripts/exp_{experiment}/run_exp_{experiment}.py', 'scripts/build_corpus.py',
                    'scripts/experiment_io.py', 'scripts/download_sources.py', 'scripts/validate_experiments.py',
                    'scripts/validate_all.py']
            write_json(destination / 'manifest.json', dict(evaluation_version='1.0', experiment=experiment,
                       input_hashes=inputs, code_hashes={name: sha256(ROOT / name) for name in code},
                       options=options, ks=ks, protocol=protocol,
                       files={name: sha256(destination / name) for name in sorted(RESULT_FILES - {'manifest.json'})}))
    finally:
        lock.unlink()
    return report


def main(experiment, predictor):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', help='Dataset config for one experiment')
    parser.add_argument('--split', choices=['train', 'dev', 'test'], default='test', help='B only; C/D/E use temporal prefixes')
    parser.add_argument('--ks', type=int, nargs='+', default=[5, 10])
    parser.add_argument('--half-life-days', type=float, default=30, help='E decay baseline, fixed before test')
    parser.add_argument('--output', help='One experiment only, under project/results')
    parser.add_argument('--allow-shortfall', action='store_true')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--dry-run', action='store_true', help='Validate inputs without scoring/writing')
    args = parser.parse_args()
    try:
        report = run_experiment(ROOT, experiment, predictor, config_path=args.config, split=args.split, ks=args.ks,
                                half_life_days=args.half_life_days, output=args.output,
                                allow_shortfall=args.allow_shortfall, overwrite=args.overwrite, dry_run=args.dry_run)
        print(f"{'DRY RUN' if args.dry_run else 'PASS'} {experiment.upper()}: {report['cases']} cases; "
              f"{report['protocol']}")
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f'FAILED {experiment.upper()}: {error}\n')
