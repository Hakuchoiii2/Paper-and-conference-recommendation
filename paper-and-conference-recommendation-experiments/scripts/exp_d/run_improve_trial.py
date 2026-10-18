"""Replay fixed public direction predictions through new, training-free rerankers.

Read-only inputs; writes a fresh result directory. No generator or baseline edits.
This is a development diagnostic on existing data, not a held-out final evaluation.
"""
import argparse
import collections
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT = SCRIPT_DIR.parents[1]
HERE = PROJECT / 'data/exp_d'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def write_rows(path, values):
    path.write_text(''.join(json.dumps(v, ensure_ascii=False, sort_keys=True) + '\n' for v in values), encoding='utf-8')


def verify(base, hashes):
    for name, expected in hashes.items():
        if digest(base / name) != expected:
            raise ValueError('Hash mismatch: ' + str(base / name))


def focus_metrics(predictions, truth, groups):
    result = []
    for model in sorted({r['model'] for r in predictions}):
        for group in ('overall', 'clear', 'ambiguous', 'none'):
            subset = [r for r in predictions if r['model'] == model
                      and (group == 'overall' or groups[r['case_id']] == group)]
            if not subset:
                continue
            pairs = [(truth[r['case_id']]['directions'][truth[r['case_id']]['focus_facet']],
                      r['directions'][truth[r['case_id']]['focus_facet']]) for r in subset]
            f1 = []
            for label in ('similar', 'different'):
                tp = sum(t == p == label for t, p in pairs)
                fp = sum(t != label and p == label for t, p in pairs)
                fn = sum(t == label and p != label for t, p in pairs)
                f1.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0)
            result.append(dict(model=model, group=group, cases=len(pairs),
                               focus_accuracy=sum(t == p for t, p in pairs) / len(pairs),
                               focus_coverage=sum(p in ('similar', 'different') for _, p in pairs) / len(pairs),
                               focus_macro_f1=sum(f1) / 2))
    return result


def evaluate_bundle(data, baseline_result, destination, facets, vectors, api, reranker, condition):
    cases = rows(data / 'generated/sessions.jsonl')
    truth = {r['case_id']: r for r in rows(data / 'ground_truth/session_intents.jsonl')}
    labels = {c['case_id']: {} for c in cases}
    for r in rows(data / 'ground_truth/intent_labels.jsonl'):
        labels[r['case_id']][r['candidate_id']] = r['relevance']
    groups = {cid: r['query_mode'] for cid, r in truth.items()}
    original = rows(baseline_result / 'predictions.jsonl')
    # First verify old predictions still reproduce their saved metrics.
    old_details = api['evaluate'](original, cases, labels, groups, [5, 10], truth)
    if api['aggregate'](old_details) != read(baseline_result / 'report.json')['summary']:
        raise ValueError('Baseline report cannot be reproduced')
    by_id = {c['case_id']: c for c in cases}
    improved = []
    for baseline in original:
        if baseline['model'].partition('__')[0] in ('direction_behavior', 'direction_search'):
            for policy in ('active', 'priority'):
                # Public reranker gets no truth, labels, groups or provenance.
                improved.append(reranker.rerank(by_id[baseline['case_id']], facets, vectors, baseline, policy))
    predictions = original + improved
    details = api['evaluate'](predictions, cases, labels, groups, [5, 10], truth)
    summary = api['aggregate'](details)
    old_report = read(baseline_result / 'report.json')
    report = dict(old_report, summary=summary,
                  evaluation_version='d_rerank_diagnostic_v1',
                  notes=old_report['notes'] + [
                      'Development diagnostic; no training, tuning or held-out generalization claim.',
                      'Original baseline predictions preserved; same candidates, labels and cutoffs.',
                      'Estimator directions/confidence unchanged; only ranking policy changes.',
                      'Priority tiers use observed concept overlap; active policy masks C weights.',
                      'Focus chosen from unique strongest non-context observed direction; ties/unknown fall back.',
                      'Priority can bypass missing-facet penalties on inactive facets; not a semantic encoder gain.'
                  ])
    destination.mkdir(parents=True, exist_ok=False)
    write_rows(destination / 'predictions.jsonl', predictions)
    write_rows(destination / 'details.jsonl', details)
    write(destination / 'report.json', report)
    (destination / 'report.md').write_text(api['markdown'](report), encoding='utf-8')
    with (destination / 'summary.csv').open('w', encoding='utf-8', newline='') as stream:
        fields = ['model', 'group', 'cases', 'positive_cases'] + list(summary[0]['defined_cases'])
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(summary)
    write(destination / 'focus_metrics.json', focus_metrics(predictions, truth, groups))
    # Paired changes and an anchor-group view, not an independence assumption over sessions.
    detail_map = {(r['case_id'], r['model']): r for r in details}
    comparison = []
    for model in sorted({r['model'] for r in improved}):
        policy, channel_arm = model.removeprefix('intent_').split('_', 1)
        reference = 'direction_' + channel_arm
        selected = [r for r in improved if r['model'] == model]
        pairs = [(detail_map[r['case_id'], reference], detail_map[r['case_id'], model]) for r in selected]
        metric_changes = {}
        for metric in ('ndcg@10', 'intent_compliance@5', 'intent_compliance@10'):
            delta = [b['metrics'][metric] - a['metrics'][metric] for a, b in pairs
                     if a['metrics'][metric] is not None and b['metrics'][metric] is not None]
            metric_changes[metric] = dict(mean_delta=sum(delta) / len(delta) if delta else None,
                                         wins=sum(v > 1e-12 for v in delta),
                                         ties=sum(abs(v) <= 1e-12 for v in delta),
                                         losses=sum(v < -1e-12 for v in delta))
        comparison.append(dict(condition=condition, model=model, baseline=reference,
                               cases=len(selected), fallback_cases=sum(r['fallback_to_baseline'] for r in selected),
                               metrics=metric_changes))
    write(destination / 'comparison.json', comparison)
    anchor_groups = collections.defaultdict(list)
    for c in cases:
        anchor_groups[c['query_paper_id']].append(c['case_id'])
    write(destination / 'anchor_groups.json', dict(purpose='diagnostic only; not a train/test split', groups=anchor_groups))
    write(destination / 'manifest.json', dict(condition=condition, baseline_result=str(baseline_result),
          data=str(data), baseline_predictions_sha256=digest(baseline_result / 'predictions.jsonl'),
          files={p.name: digest(p) for p in sorted(destination.iterdir()) if p.is_file()}))
    print(f'PASS {condition}: {len(cases)} cases, {len(predictions)} predictions', flush=True)
    return comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=HERE / 'workspace_baseline_20261016_v1')
    parser.add_argument('--baseline', type=Path, default=HERE / 'results/baseline_20261016_v1')
    parser.add_argument('--synthetic', type=Path, default=HERE / 'results/baseline_20261016_v1_synthetic')
    parser.add_argument('--output', type=Path, default=HERE / 'results/improve_m0_20261016_v1')
    args = parser.parse_args()
    source, baseline, synthetic, output = [p.resolve() for p in
                                          (args.source_root, args.baseline, args.synthetic, args.output)]
    if HERE not in output.parents or output.exists():
        raise ValueError('Choose a NEW output directory inside data/exp_d')
    if any(output == p or output in p.parents or p in output.parents for p in (source, baseline, synthetic)):
        raise ValueError('Output must be separate from all input directories')
    sys.path[:0] = [str(source / 'scripts'), str(source)]
    from validate_experiments import validate_experiment
    from experiment_io import concept_sets, load_silver
    from baseline_common import aggregate, facet_vectors
    from experiment_runner import evaluate_predictions, markdown_report
    validated = validate_experiment(source, 'd')
    original_manifest = read(baseline / 'manifest.json')
    pilot_manifest = read(synthetic / 'manifest.json')
    verify(source, original_manifest['input_hashes'])
    verify(source, original_manifest['code_hashes'])
    verify(baseline, original_manifest['files'])
    verify(source, pilot_manifest['source_hashes'])
    verify(synthetic, pilot_manifest['files'])
    # Watch all input files, including manifests and the user's original baseline code.
    watched = {p: digest(p) for base in (source, baseline, synthetic)
               for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for p in (PROJECT / 'scripts/exp_d/run_exp_d.py', PROJECT / 'scripts/baseline_common.py',
              HERE / 'run_synthetic_observation_pilot.py'):
        watched[p] = digest(p)
    module_path = PROJECT / 'scripts/exp_d/intent_priority.py'
    spec = importlib.util.spec_from_file_location('d_intent_priority', module_path)
    reranker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reranker)
    config = validated['config']
    _, raw, metadata, _ = load_silver(source, Path(config['facets_path']).parent)
    facets = concept_sets(raw, metadata)
    vectors = facet_vectors(facets)
    api = dict(evaluate=evaluate_predictions, aggregate=aggregate, markdown=markdown_report)
    output.mkdir(parents=True, exist_ok=False)
    comparisons = evaluate_bundle(source / 'data/exp_d', baseline, output / 'canonical',
                                  facets, vectors, api, reranker, 'canonical')
    for seed in pilot_manifest['seeds']:
        for noise in pilot_manifest['noise_levels']:
            name = f'seed_{seed}_noise_{noise:g}'
            comparisons += evaluate_bundle(synthetic, synthetic / name / 'results', output / 'synthetic' / name,
                                           facets, vectors, api, reranker, name)
    if any(digest(p) != h for p, h in watched.items()):
        raise ValueError('An input changed during trial')
    write(output / 'comparison.json', comparisons)
    lines = ['# D: development reranking trial', '',
             'Same saved public predictions, inputs and evaluator; no training or parameter search.',
             'This is a development diagnostic, not a held-out final evaluation.', '',
             '| Condition | Method | Baseline | Delta nDCG@10 | Delta compliance@5 | Fallback cases |',
             '|---|---|---|---:|---:|---:|']
    for r in comparisons:
        lines.append(f"| {r['condition']} | {r['model']} | {r['baseline']} | "
                     f"{r['metrics']['ndcg@10']['mean_delta']:+.4f} | "
                     f"{r['metrics']['intent_compliance@5']['mean_delta']:+.4f} | {r['fallback_cases']} |")
    (output / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    write(output / 'manifest.json', dict(protocol='d_rerank_diagnostic_v1', training=False,
          source_unchanged=True, source_root=str(source), baseline=str(baseline), synthetic=str(synthetic),
          code_hashes={str(p.relative_to(PROJECT)): digest(p) for p in (Path(__file__), module_path)},
          input_hashes={str(p): h for p, h in watched.items()},
          files={p.relative_to(output).as_posix(): digest(p) for p in sorted(output.rglob('*')) if p.is_file()}))
    print('TRIAL COMPLETE: ' + str(output), flush=True)


if __name__ == '__main__':
    main()
