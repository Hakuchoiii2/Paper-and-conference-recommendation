"""Compare verified Qwen silver with independently reviewed human forms."""
import argparse
import collections
import json
import unicodedata
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiment_io import FACETS, ROOT, load_silver, project_path
from build_corpus import read_jsonl, write_jsonl
from download_sources import sha256, write_json
from validate_all import require

MATCHING_VERSION = 'nfkc_casefold_whitespace_v1'


def label_key(value):
    # Preserve punctuation: C++, C and C# are different labels.
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def metrics(tp, fp, fn):
    return dict(tp=tp, fp=fp, fn=fn,
                precision=tp/(tp+fp) if tp+fp else None,
                recall=tp/(tp+fn) if tp+fn else None,
                f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None)


def reviewed_gold(path, silver, expected_count):
    require(type(expected_count) is int and expected_count > 0, 'Invalid expected gold count')
    rows = read_jsonl(path)
    require(len(rows) == expected_count, f'Gold count must be {expected_count}; got {len(rows)}')
    gold = {}
    for row in rows:
        pid = row['paper_id']
        require(pid in silver, f'Gold paper ID absent from silver: {pid}')
        require(pid != 'P000001', 'Prompt-development paper P000001 must not enter held-out gold')
        require(pid not in gold, f'Duplicate gold paper ID: {pid}')
        require(row.get('review_status') == 'reviewed', f'{pid}: gold is pending or review incomplete')
        require(isinstance(row.get('reviewer'), str) and row['reviewer'].strip(), f'{pid}: missing human reviewer')
        require(isinstance(row.get('facets'), dict) and set(row['facets']) == set(FACETS),
                f'{pid}: gold needs all five facet keys')
        for facet, values in row['facets'].items():
            require(isinstance(values, list) and all(isinstance(value, str) and label_key(value) for value in values),
                    f'{pid}/{facet}: expected list of nonempty concept strings')
            require(len(set(map(label_key, values))) == len(values), f'{pid}/{facet}: duplicate normalized concepts')
        gold[pid] = row
    return gold


def markdown_report(report):
    def percent(value):
        return 'N/A' if value is None else f'{100*value:.2f}%'
    lines = ['# Đánh giá Qwen silver bằng human gold', '',
             f"Đã đối chiếu {report['gold_count']} bài người review hoàn tất.", '',
             '| Facet | TP | FP | FN | Precision | Recall | F1 |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for facet, values in list(report['by_facet'].items()) + [('micro', report['micro'])]:
        lines.append(f"| {facet} | {values['tp']} | {values['fp']} | {values['fn']} | "
                     f"{percent(values['precision'])} | {percent(values['recall'])} | {percent(values['f1'])} |")
    lines.extend(['', f"Macro F1 trên các facet có mẫu: {percent(report['macro_f1'])}.",
                  f"Bài khớp cả năm facet: {report['exact_papers']}/{report['gold_count']} "
                  '(tính cả hai list cùng rỗng).', '',
                  'TP: nhãn Qwen khớp gold trong cùng facet; FP: nhãn Qwen dư so với gold;',
                  'FN: nhãn gold Qwen bỏ sót. N/A nghĩa là mẫu số bằng 0, không phải 100%.', '',
                  'So khớp NFKC + bỏ khác biệt hoa/thường và khoảng trắng; giữ dấu câu.',
                  'Không tự gộp từ đồng nghĩa, viết tắt hoặc nhãn rộng/hẹp. Extra/missing là',
                  'chênh lệch chữ cần review, chưa tự chứng minh lỗi ngữ nghĩa.', '',
                  'Mở per_paper.jsonl để đọc bài, gold/silver, dẫn chứng, extra/missing và',
                  'các trường hợp có thể nhầm facet. Nhãn cùng nghĩa khác chữ phải đối chiếu',
                  'bằng quy tắc thống nhất, không sửa gold để làm tăng điểm Qwen.', '',
                  'Cohort: ' + report['cohort']['selection_bias'], '',
                  'Chỉ số trên cohort này không tự đại diện toàn corpus. Corpus audit chỉ',
                  'thống kê coverage/fallback/facet trống, không đo accuracy ngoài gold.',
                  'Điểm selected_score 0–100 của generator là kiểm tra bám nguồn/cấu trúc,',
                  'không phải Precision, F1 hoặc xác suất nhãn đúng ngữ nghĩa.', ''])
    return '\n'.join(lines)


def evaluate(root, source='data/exp_a/generated',
             gold='data/exp_a/ground_truth/gold_review/review_annotations.jsonl',
             output='data/exp_a/evaluation/gold_400', expected_count=400):
    root = Path(root).resolve()
    destination = project_path(root, output)
    base = root / 'data/exp_a/evaluation'
    require(destination == base or base in destination.parents, 'Output must stay inside experiment A evaluation')
    source_directory = project_path(root, source)
    require(destination != source_directory and destination not in source_directory.parents
            and source_directory not in destination.parents, 'Evaluation output must not overlap the silver source')
    gold_path = project_path(root, gold)
    require(destination not in gold_path.parents, 'Evaluation must not overwrite human gold')
    papers, silver, notes, source_manifest = load_silver(root, source_directory, complete=False)
    truth = reviewed_gold(gold_path, silver, expected_count)
    cohort_path = gold_path.parent / 'manifest.json'
    source_hash = sha256(project_path(root, source) / 'manifest.json')
    cohort = dict(selection_policy='unknown', selection_bias='Unknown sampling policy; do not infer corpus-wide quality.')
    if cohort_path.exists():
        selection = json.loads(cohort_path.read_text(encoding='utf-8'))
        require(selection.get('tier') == 'review_queue', 'Gold cohort manifest must describe a review queue')
        require(len(selection['selected_ids']) == expected_count and len(set(selection['selected_ids'])) == expected_count
                and set(selection['selected_ids']) == set(truth), 'Gold IDs differ from selected review cohort')
        cohort.update(selection_policy=selection['selection_policy'], selection_bias=selection['selection_bias'],
                      source_unchanged_since_selection=selection['source_manifest_sha256'] == source_hash)
    totals = {facet: collections.Counter(tp=0, fp=0, fn=0, exact=0) for facet in FACETS}
    details = []
    for pid in sorted(truth):
        gold_sets = {facet: set(map(label_key, truth[pid]['facets'][facet])) for facet in FACETS}
        comparison = {}
        for facet in FACETS:
            predicted, reference = set(map(label_key, silver[pid][facet])), gold_sets[facet]
            matched, extra, missing = predicted & reference, predicted-reference, reference-predicted
            totals[facet].update(tp=len(matched), fp=len(extra), fn=len(missing), exact=int(predicted == reference))
            cross = {concept:[other for other in FACETS if other != facet and concept in gold_sets[other]]
                     for concept in sorted(extra)}
            comparison[facet] = dict(silver=silver[pid][facet], gold=truth[pid]['facets'][facet],
                                     matched=sorted(matched), extra=sorted(extra), missing=sorted(missing),
                                     possible_cross_facet={concept: targets for concept,targets in cross.items() if targets},
                                     silver_evidence=notes[pid]['evidence'][facet])
        details.append(dict(paper_id=pid, title=papers[pid]['title'], abstract=papers[pid]['abstract'],
                            reviewer=truth[pid]['reviewer'], comparison=comparison,
                            exact=all(not value['extra'] and not value['missing'] for value in comparison.values())))
    by_facet = {facet: dict(metrics(values['tp'],values['fp'],values['fn']), exact=values['exact'])
                for facet,values in totals.items()}
    summed = {key: sum(values[key] for values in totals.values()) for key in ('tp','fp','fn')}
    defined_f1 = [values['f1'] for values in by_facet.values() if values['f1'] is not None]
    report = dict(evaluation_version='1.0', evaluation_kind='lexical_agreement_with_human_gold',
                  matching_version=MATCHING_VERSION, gold_count=len(truth),
                  micro=metrics(**summed), by_facet=by_facet,
                  macro_f1=sum(defined_f1)/len(defined_f1) if defined_f1 else None,
                  exact_papers=sum(row['exact'] for row in details), cohort=cohort,
                  corpus_audit=dict(corpus_papers=len(papers), available_annotations=len(silver),
                                    missing_annotations=len(papers)-len(silver), input_status=source_manifest['status'],
                                    fallback_papers=sum(bool(row.get('fallback_used')) for row in notes.values()),
                                    flagged_papers=sum(bool(row.get('fallback_used') or row.get('validation_errors'))
                                                      for row in notes.values()),
                                    nonempty_by_facet={facet:sum(bool(row[facet]) for row in silver.values()) for facet in FACETS},
                                    empty_facet_distribution={str(n):sum(sum(not row[f] for f in FACETS) == n
                                                                        for row in silver.values()) for n in range(6)}))
    write_json(destination / 'summary.json', report)
    write_jsonl(destination / 'per_paper.jsonl', details)
    (destination / 'report.md').write_text(markdown_report(report), encoding='utf-8')
    manifest = dict(evaluation_version='1.0', evaluator_sha256=sha256(Path(__file__)),
                    silver_source=project_path(root, source).relative_to(root).as_posix(),
                    gold_path=gold_path.relative_to(root).as_posix(), gold_sha256=sha256(gold_path),
                    source_manifest_sha256=source_hash,
                    cohort_manifest_sha256=sha256(cohort_path) if cohort_path.exists() else None,
                    files={name:sha256(destination/name) for name in ('summary.json','per_paper.jsonl','report.md')})
    write_json(destination / 'manifest.json', manifest)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='data/exp_a/generated')
    parser.add_argument('--gold', default='data/exp_a/ground_truth/gold_review/review_annotations.jsonl')
    parser.add_argument('--output', default='data/exp_a/evaluation/gold_400')
    parser.add_argument('--expected-count', type=int, default=400)
    args = parser.parse_args()
    try:
        report = evaluate(ROOT, args.source, args.gold, args.output, args.expected_count)
        print(f"EVALUATED: {report['gold_count']} human-reviewed papers; micro={report['micro']}; output={args.output}")
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f'QWEN EVALUATION FAILED: {error}\n')


if __name__ == '__main__':
    main()
