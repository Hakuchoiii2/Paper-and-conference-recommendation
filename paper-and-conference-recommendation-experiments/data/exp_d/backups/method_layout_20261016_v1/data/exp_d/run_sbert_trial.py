"""Run frozen SBERT ablations with all model/download/embedding caches on E: in exp_d/model."""
from model_storage import configure
MODEL_ROOT = configure()

import argparse
import csv
import importlib.metadata
import json
import os
from pathlib import Path
import sys

from run_improve_trial import read, rows, digest, write, write_rows, verify, focus_metrics

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]


def encode_facets(facets, download, device):
    # Imports happen after configure(), and inference must never fetch network artifacts.
    os.environ['HF_HUB_OFFLINE'] = '1'
    import numpy as np
    import torch
    from sentence_transformers import SentenceTransformer
    model_dir = MODEL_ROOT / 'all-MiniLM-L6-v2'
    verify(model_dir, download['files'])
    entries = {(pid, f): ' '.join(sorted(values)) for pid, row in facets.items()
               for f, values in row.items() if values}
    texts = sorted(set(entries.values()))
    import hashlib
    signature = hashlib.sha256(json.dumps(dict(texts=texts, model=download['files'],
          revision=download['revision'], normalize=True, max_seq_length=256), sort_keys=True).encode()).hexdigest()
    cache = MODEL_ROOT / 'embeddings' / (signature + '.npz')
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        with np.load(cache, allow_pickle=False) as saved:
            assert saved['texts'].tolist() == texts
            matrix = saved['vectors'].copy()
        actual_device = 'cached'
    else:
        torch.set_num_threads(4)
        torch.manual_seed(42)
        actual_device = ('cuda' if torch.cuda.is_available() else 'cpu') if device == 'auto' else device
        print(f'Loading LOCAL SBERT on {actual_device}; encoding {len(texts)} unique facet texts', flush=True)
        encoder = SentenceTransformer(str(model_dir), device=actual_device, local_files_only=True,
                                      trust_remote_code=False, cache_folder=str(MODEL_ROOT / 'sentence_transformers'))
        encoder.max_seq_length = 256
        matrix = encoder.encode(texts, batch_size=64, normalize_embeddings=True,
                                convert_to_numpy=True, show_progress_bar=True)
        np.savez_compressed(cache, texts=np.array(texts), vectors=matrix)
    if matrix.shape != (len(texts), 384) or not np.isfinite(matrix).all():
        raise ValueError('Invalid embedding cache')
    by_text = {text: matrix[i] for i, text in enumerate(texts)}
    embeddings = {key: by_text[text] for key, text in entries.items()}
    return embeddings, dict(cache=str(cache), sha256=digest(cache), unique_texts=len(texts),
                           device=actual_device, dimensions=384, max_seq_length=256,
                           input='sorted facet concept text without hidden intent', normalized=True)


def bundle(data, old_result, output, facets, vectors, embeddings, api, condition):
    cases = rows(data / 'generated/sessions.jsonl')
    case_map = {c['case_id']: c for c in cases}
    original = rows(old_result / 'predictions.jsonl')
    additions = []
    references = {}
    for base in original:
        if base['model'].partition('__')[0] not in ('direction_behavior', 'direction_search'):
            continue
        case = case_map[base['case_id']]
        lexical_active = api['lexical'].rerank(case, facets, vectors, base, 'active')
        additions.append(lexical_active)
        for mode in ('full', 'active', 'hybrid'):
            prediction = api['semantic'].rerank(case, facets, vectors, embeddings, base, mode)
            additions.append(prediction)
            references[prediction['model']] = (base['model'], lexical_active['model'])
    predictions = original + additions
    # Hidden data is read only for the evaluation stage, after public reranking.
    truth = {r['case_id']: r for r in rows(data / 'ground_truth/session_intents.jsonl')}
    groups = {cid: r['query_mode'] for cid, r in truth.items()}
    labels = {cid: {} for cid in truth}
    for r in rows(data / 'ground_truth/intent_labels.jsonl'):
        labels[r['case_id']][r['candidate_id']] = r['relevance']
    details = api['evaluate'](predictions, cases, labels, groups, [5, 10], truth)
    old_report = read(old_result / 'report.json')
    old_details = api['evaluate'](original, cases, labels, groups, [5, 10], truth)
    if api['aggregate'](old_details) != old_report['summary']:
        raise ValueError('Original baseline metrics differ')
    summary = api['aggregate'](details)
    report = dict(old_report, summary=summary, evaluation_version='d_sbert_diagnostic_v1',
                  notes=old_report['notes'] + [
                      'Development diagnostic, frozen all-MiniLM-L6-v2; no fine-tuning or label-based selection.',
                      'Directions and confidence unchanged. Original predictions and lexical context gate preserved.',
                      'Full dense changes representation only; dense active and fixed 50/50 hybrid compare with lexical active.',
                      'Unknown/tied focus falls back exactly in active policies; dense full does not require focus.',
                      'All model and temporary caches configured in data/exp_d/model before library imports.'
                  ])
    output.mkdir(parents=True, exist_ok=False)
    write_rows(output / 'predictions.jsonl', predictions)
    write_rows(output / 'details.jsonl', details)
    write(output / 'report.json', report)
    write(output / 'focus_metrics.json', focus_metrics(predictions, truth, groups))
    (output / 'report.md').write_text(api['markdown'](report), encoding='utf-8')
    with (output / 'summary.csv').open('w', encoding='utf-8', newline='') as stream:
        fields = ['model', 'group', 'cases', 'positive_cases'] + list(summary[0]['defined_cases'])
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(summary)
    overall = {r['model']: r for r in summary if r['group'] == 'overall'}
    comparisons = []
    for model, (base, active) in sorted(references.items()):
        for reference in (base, active) if not model.startswith('semantic_full_') else (base,):
            comparisons.append(dict(condition=condition, model=model, reference=reference,
                  ndcg=overall[model]['ndcg@10'], compliance=overall[model]['intent_compliance@5'],
                  delta_ndcg=overall[model]['ndcg@10'] - overall[reference]['ndcg@10'],
                  delta_compliance=overall[model]['intent_compliance@5'] - overall[reference]['intent_compliance@5']))
    write(output / 'comparison.json', comparisons)
    write(output / 'manifest.json', dict(condition=condition, data=str(data), baseline_result=str(old_result),
          files={p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()}))
    print(f'PASS {condition}: {len(cases)} cases; {len(predictions)} predictions', flush=True)
    return comparisons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=HERE / 'workspace_baseline_20261016_v1')
    parser.add_argument('--baseline', type=Path, default=HERE / 'results/baseline_20261016_v1')
    parser.add_argument('--synthetic', type=Path, default=HERE / 'results/baseline_20261016_v1_synthetic')
    parser.add_argument('--output', type=Path, default=HERE / 'results/improve_sbert_20261016_v1')
    parser.add_argument('--device', choices=['auto', 'cpu', 'cuda'], default='auto')
    args = parser.parse_args()
    source, baseline, synthetic, output = [p.resolve() for p in
                                          (args.source_root, args.baseline, args.synthetic, args.output)]
    if HERE not in output.parents or output.exists():
        raise ValueError('Choose a NEW output directory inside data/exp_d')
    for path in (source, baseline, synthetic, MODEL_ROOT):
        if path == output or path in output.parents or output in path.parents:
            raise ValueError('Output overlaps protected inputs/model storage')
    sys.path[:0] = [str(source / 'scripts'), str(source), str(PROJECT / 'scripts/exp_d')]
    from validate_experiments import validate_experiment
    from experiment_io import load_silver, concept_sets
    from experiment_runner import evaluate_predictions, markdown_report
    from baseline_common import facet_vectors, aggregate
    import intent_priority
    import semantic_ranker
    source_manifest = validate_experiment(source, 'd')
    bm, sm = read(baseline / 'manifest.json'), read(synthetic / 'manifest.json')
    verify(source, bm['input_hashes'])
    verify(source, bm['code_hashes'])
    verify(baseline, bm['files'])
    verify(source, sm['source_hashes'])
    verify(synthetic, sm['files'])
    watched = {p: digest(p) for base in (source, baseline, synthetic) for p in base.rglob('*')
               if p.is_file() and '__pycache__' not in p.parts}
    config = source_manifest['config']
    _, raw, metadata, _ = load_silver(source, Path(config['facets_path']).parent)
    facets = concept_sets(raw, metadata)
    vectors = facet_vectors(facets)
    download = read(MODEL_ROOT / 'sbert_download_manifest.json')
    embeddings, encoding = encode_facets(facets, download, args.device)
    api = dict(lexical=intent_priority, semantic=semantic_ranker, evaluate=evaluate_predictions,
               markdown=markdown_report, aggregate=aggregate)
    output.mkdir(parents=True, exist_ok=False)
    comparisons = bundle(source / 'data/exp_d', baseline, output / 'canonical', facets, vectors,
                         embeddings, api, 'canonical')
    for seed in sm['seeds']:
        for noise in sm['noise_levels']:
            name = f'seed_{seed}_noise_{noise:g}'
            comparisons += bundle(synthetic, synthetic / name / 'results', output / 'synthetic' / name,
                                  facets, vectors, embeddings, api, name)
    for path, value in watched.items():
        if digest(path) != value:
            raise ValueError('Source changed during inference: ' + str(path))
    write(output / 'comparison.json', comparisons)
    lines = ['# D: frozen SBERT development trial', '',
             'No fine-tuning; original estimator, inputs and evaluator retained. Not a held-out test.', '',
             '| Condition | Model | Reference | nDCG@10 | Compliance@5 | Delta nDCG | Delta compliance |',
             '|---|---|---|---:|---:|---:|---:|']
    for r in comparisons:
        lines.append(f"| {r['condition']} | {r['model']} | {r['reference']} | {r['ndcg']:.4f} | "
                     f"{r['compliance']:.4f} | {r['delta_ndcg']:+.4f} | {r['delta_compliance']:+.4f} |")
    (output / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    code = [Path(__file__), HERE / 'model_storage.py', HERE / 'prepare_sbert_model.py',
            HERE / 'run_improve_trial.py', PROJECT / 'scripts/exp_d/semantic_ranker.py',
            PROJECT / 'scripts/exp_d/intent_priority.py']
    write(output / 'manifest.json', dict(protocol='d_sbert_diagnostic_v1', model=download, encoding=encoding,
          source_unchanged=True, fine_tuning=False, hybrid_dense_weight=.5,
          packages={p: importlib.metadata.version(p) for p in
                    ('torch', 'transformers', 'sentence-transformers', 'huggingface-hub', 'numpy')},
          code_hashes={str(p.relative_to(PROJECT)): digest(p) for p in code},
          input_hashes={str(p): h for p, h in watched.items()},
          files={p.relative_to(output).as_posix(): digest(p) for p in sorted(output.rglob('*')) if p.is_file()}))
    print('SBERT TRIAL COMPLETE: ' + str(output), flush=True)


if __name__ == '__main__':
    main()
