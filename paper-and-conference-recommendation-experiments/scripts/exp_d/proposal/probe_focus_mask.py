"""Exploratory active-facet probe and explicitly privileged oracle diagnostics.

Does not change the original benchmark, scorer, C weights or dataset.
"""
import argparse
import collections
import math
import random
import statistics
from pathlib import Path

from data_io import (DATA_ROOT, FACETS, PROJECT, load_public, new_output, read_json, read_rows,
                     require, sha, write_json, write_rows)
from baseline_common import facet_vectors, intent_scores, ranked, ranking_metrics
from evaluate import load_truth, predicted_focus, quantile, write_csv
from focus_masked import active_directions
from run_benchmark import protected_inputs

MODELS = ('direction_search', 'active_similar', 'delta_active', 'oracle_sign_only', 'oracle_full_intent')
METRICS = ('direction_accuracy', 'joint_accuracy', 'coverage', 'ndcg10', 'pair_strict')


def score(row, case, truth):
    intent = truth['intents'][row['case_id']]
    design = truth['designs'][intent['design_id']]
    grades = truth['label_map'][row['case_id']]
    order = [r['paper_id'] for r in row['ranking']]
    scores = {r['paper_id']:r['score'] for r in row['ranking']}
    positive = next(p for p, v in grades.items() if v == 2)
    negative = next(p for p, v in grades.items() if v == 1)
    focus = intent['focus_facet']
    direction = row['directions'][focus]
    return dict(model=row['model'], case_id=row['case_id'], condition=row['condition'],
                design=intent['design_id'], cluster=design['work_group'], source=design['candidate_source_group'],
                query_mode=intent['query_mode'],
                metrics=dict(direction_accuracy=float(direction == intent['directions'][focus]),
                             joint_accuracy=float(direction == intent['directions'][focus]
                                                  and predicted_focus(case, row['directions']) == focus),
                             coverage=float(direction in ('similar','different')),
                             ndcg10=ranking_metrics(order, grades, [10])['ndcg@10'],
                             pair_strict=float(scores[positive] > scores[negative])))


def summarize_probe(details):
    cells = collections.defaultdict(list)
    for row in details:
        for group in ('overall', 'source:'+row['source'], 'query:'+row['query_mode']):
            cells[row['model'], group, row['cluster'], row['design']].append(row['metrics'])
    cluster_cells = collections.defaultdict(list)
    for (model, group, cluster, _), values in cells.items():
        cluster_cells[model, group, cluster].append({m:statistics.mean(r[m] for r in values) for m in METRICS})
    clusters = {key:{m:statistics.mean(r[m] for r in values) for m in METRICS}
                for key, values in cluster_cells.items()}
    summary = []
    for group in sorted({g for _, g, _ in clusters}):
        for model in MODELS:
            values = [r for (name, g, _), r in clusters.items() if name == model and g == group]
            summary.append(dict(model=model, group=group, clusters=len(values),
                                privileged_oracle=model.startswith('oracle_'),
                                **{m:statistics.mean(r[m] for r in values) for m in METRICS}))
    return summary, clusters


def compare(clusters):
    output = []
    for group in ('overall','source:real_only','source:mixed'):
        for method, control in (('delta_active','direction_search'), ('delta_active','active_similar'),
                                ('oracle_sign_only','direction_search'), ('oracle_full_intent','oracle_sign_only')):
            units = sorted(c for m,g,c in clusters if m == method and g == group)
            for metric in ('direction_accuracy','ndcg10','pair_strict'):
                delta = [clusters[method,group,c][metric]-clusters[control,group,c][metric] for c in units]
                rng = random.Random(group+'|'+method+'|'+control+'|'+metric)
                draws = [statistics.mean(rng.choices(delta, k=len(delta))) for _ in range(2000)]
                output.append(dict(method=method, baseline=control, group=group, metric=metric,
                                   delta=statistics.mean(delta), ci_low=quantile(draws,.025), ci_high=quantile(draws,.975),
                                   clusters=len(units), exploratory=True))
    return output


def run(source_run, output):
    source_run = Path(source_run).resolve()
    require(source_run.is_relative_to(DATA_ROOT/'results'), 'Source must be an existing D proposal run')
    source_manifest = read_json(source_run/'manifest.json')
    require(source_manifest['status']=='complete', 'Source benchmark incomplete')
    # Fail rather than silently probing predictions whose original files changed.
    for name, expected in source_manifest['output_sha256'].items():
        require(sha(source_run/name)==expected, 'Original benchmark output changed: '+name)
    config = read_json(source_run/'config.json')
    dataset = PROJECT/config['input_dataset']
    protected = protected_inputs(dataset)
    source_before = {p.name:sha(p) for p in source_run.iterdir() if p.is_file()}
    public = load_public(dataset)
    cases = {r['case_id']:r for r in public['cases']}
    vectors = facet_vectors(public['facets'])
    baseline = [r for r in read_rows(source_run/'predictions.jsonl') if r['model']=='direction_search']
    output = new_output(output)
    output.mkdir(parents=True)
    # Legitimate candidate method only sees estimated directions and public context.
    # Compute/persist all of these predictions before reading any truth.
    predictions = []
    for row in baseline:
        case = cases[row['case_id']]
        predictions.append(dict(row))
        for model, force_similar in (('delta_active',False), ('active_similar',True)):
            directions = active_directions(case['context_facet'], row['directions'], force_similar)
            result = ranked(case, model, intent_scores(case, row['facet_importance'], directions, vectors))
            result.update(condition=row['condition'], directions=directions, facet_importance=dict(row['facet_importance']))
            predictions.append(result)
    write_rows(output/'predictions.jsonl', predictions)

    truth = load_truth(dataset)
    truth['label_map'] = collections.defaultdict(dict)
    for row in truth['labels']:
        truth['label_map'][row['case_id']][row['candidate_id']] = row['relevance']
    oracles = []
    for row in baseline:
        case = cases[row['case_id']]
        intent = truth['intents'][row['case_id']]
        for model in ('oracle_sign_only','oracle_full_intent'):
            directions = dict.fromkeys(FACETS, 'unknown') if model=='oracle_sign_only' else dict(intent['directions'])
            directions[case['context_facet']] = 'similar'
            directions[intent['focus_facet']] = intent['directions'][intent['focus_facet']]
            result = ranked(case, model, intent_scores(case, row['facet_importance'], directions, vectors))
            result.update(condition=row['condition'], directions=directions, facet_importance=dict(row['facet_importance']),
                          privileged_diagnostic=True)
            oracles.append(result)
    write_rows(output/'oracle_predictions.jsonl', oracles)
    details = [score(r, cases[r['case_id']], truth) for r in predictions+oracles]
    summary, clusters = summarize_probe(details)
    original_summary = {r['model']:r for r in read_json(source_run/'summary.json') if r['group']=='overall'}
    reproduced = next(r for r in summary if r['group']=='overall' and r['model']=='direction_search')
    require(all(abs(reproduced[m]-original_summary['direction_search'][m]) < 1e-12 for m in METRICS),
            'Independent probe evaluation did not reproduce original baseline')
    comparisons = compare(clusters)
    write_rows(output/'details.jsonl', details)
    write_json(output/'summary.json', summary)
    write_csv(output/'summary.csv', [r for r in summary if r['group']=='overall'])
    write_csv(output/'groups.csv', summary)
    write_csv(output/'paired_comparisons.csv', comparisons)
    write_json(output/'protocol.json', dict(exploratory_after_main_results=True, independent_test=False,
               no_new_thresholds=True, scorer='original intent_scores', C_weights_input_unchanged=True,
               effective_active_weights_change=True, data_unchanged=True,
               method='Unique inferred focus -> other facets ignore; ambiguous focus -> original fallback',
               control='Same inferred focus/mask, force focus similar',
               oracle='Evaluator-only true focus/direction. No true weights. Not a deployable method or mathematical maximum.'))
    overall = {r['model']:r for r in summary if r['group']=='overall'}
    wrong_order = (1+3/math.log2(3))/(3+1/math.log2(3))
    lines = ['# Thăm dò: dự đoán facet hoạt động và chẩn đoán oracle', '',
             '**Đây là phân tích thăm dò được đề xuất sau khi xem benchmark trước, không phải test độc lập hoặc chứng minh tính mới.**',
             'Không sửa dataset, baseline/scorer hoặc trọng số C đầu vào. Mask ignore thay tập facet hoạt động và mẫu số trong scorer, nên không được gọi là chỉ cải thiện dấu similar/different.', '',
             '| Method | Accuracy hướng | nDCG@10 | Điểm grade 2 > grade 1 |', '|---|---:|---:|---:|']
    for model in MODELS:
        r = overall[model]
        lines.append(f"| {model} | {r['direction_accuracy']:.2%} | {r['ndcg10']:.4f} | {r['pair_strict']:.2%} |")
    lines += ['', 'active_similar dùng cùng focus suy được và cùng mask, chỉ buộc hướng similar. delta_active giữ hướng DELTA+query và dự đoán các facet khác ignore.',
              'Hai oracle dùng đáp án ẩn CHỈ trong evaluator. oracle_sign_only giữ facet khác unknown; oracle_full_intent biết cả ignore. Không đưa oracle vào bảng phương pháp cạnh tranh.',
              '', f'Chỉ hai bài có nhãn dương ở top 2 nhưng sai thứ tự vẫn có nDCG@10={wrong_order:.4f}; nDCG 0.8 không tương đương 80% chọn đúng nhu cầu.',
              '', 'Chi tiết source real_only/mixed ở groups.csv, khoảng paired thăm dò ở paired_comparisons.csv. Các khoảng không xử lý việc lựa chọn method sau khi xem kết quả.',
              'Hướng này phải được khóa và đánh giá thêm trên nội dung độc lập trước khi khẳng định ưu thế tổng quát. Không đổi dữ liệu hiện tại để tạo thắng lợi.', '']
    (output/'report.md').write_text('\n'.join(lines), encoding='utf-8')
    require(all(sha(PROJECT/name)==h for name,h in protected.items()), 'Dataset or baseline changed')
    require(all(sha(source_run/name)==h for name,h in source_before.items()), 'Original run changed')
    write_json(output/'manifest.json', dict(status='complete', exploratory=True, independent_test=False,
               source_run=str(source_run.relative_to(PROJECT)), source_run_sha256=source_before,
               protected_inputs=protected, original_summary_reproduced=True,
               code_sha256={str(p.relative_to(PROJECT)).replace('\\','/'):sha(p) for p in
                            (Path(__file__), Path(__file__).with_name('focus_masked.py'), Path(__file__).with_name('test_focus_masked.py'))},
               output_sha256={p.name:sha(p) for p in output.iterdir() if p.is_file()}))
    print(__import__('json').dumps(overall, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run', type=Path, default=DATA_ROOT/'results/benchmark_7_20261021_01')
    parser.add_argument('--output', type=Path, default=DATA_ROOT/'results/focus_probe_20261021_01')
    args = parser.parse_args()
    run(args.source_run, args.output)
