"""Compare verified Qwen silver with reviewed references and declare their origin."""
import argparse
import collections
from functools import lru_cache
import json
import math
import os
import re
import unicodedata
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiment_io import FACETS, ROOT, load_silver, project_path
from build_corpus import read_jsonl, write_jsonl
from download_sources import sha256, write_json
from validate_all import require

MATCHING_VERSION = 'nfkc_casefold_whitespace_v1'
MODEL_ID = 'Qwen/Qwen3-Embedding-0.6B'
MODEL_REVISION = '97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3'
MODEL_SHA256 = '0437e45c94563b09e13cb7a64478fc406947a93cb34a7e05870fc8dcd48e23fd'
MODEL_DIRECTORY = 'data/exp_a/evaluation/embedding_probe/.model_cache/' + MODEL_REVISION


def match_pairs(scores, threshold):
    # shortcut: current gold has at most six labels/facet; use a bipartite solver if lists grow beyond sixteen.
    require(not scores or len(scores[0]) <= 16, 'Embedding assignment supports at most 16 gold labels/facet')

    @lru_cache(None)
    def solve(i, used):
        if i == len(scores):
            return 0, 0.0, ()
        best = solve(i+1, used)
        for j, score in enumerate(scores[i]):
            if score >= threshold and not used & (1 << j):
                count, total, pairs = solve(i+1, used | (1 << j))
                candidate = count+1, total+score, ((i,j),)+pairs
                if candidate[:2] > best[:2]:
                    best = candidate
        return best
    return solve(0,0)[2]


def encode_labels(root, labels):
    runtime = dict(model=MODEL_ID, revision=MODEL_REVISION, device='not_loaded', model_files={})
    if not labels:
        return {}, runtime
    directory = project_path(root, MODEL_DIRECTORY)
    require((directory/'download_manifest.json').exists(), f'Missing cached Qwen embedding model: {directory}')
    download = json.loads((directory/'download_manifest.json').read_text(encoding='utf-8'))
    require(download['model'] == MODEL_ID and download['revision'] == MODEL_REVISION,
            'Embedding model identity/revision differs from the pinned Qwen model')
    require(download['files']['model.safetensors']['sha256'] == MODEL_SHA256, 'Unexpected Qwen embedding weights')
    model_files = {}
    for name, info in download['files'].items():
        path = (directory/name).resolve()
        require(directory in path.parents and path.is_file(), f'Invalid embedding model file: {name}')
        model_files[name] = sha256(path)
        require(model_files[name] == info['sha256'], f'Embedding model checksum mismatch: {name}')
    os.environ['USE_TF'] = '0'
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    try:
        import torch
        import transformers
        from transformers import AutoModel, AutoTokenizer
    except ImportError:
        raise ValueError('Run embedding evaluation with .venv-qwen/Scripts/python.exe; exact mode needs no model') from None
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    tokenizer = AutoTokenizer.from_pretrained(directory, local_files_only=True,
                                               trust_remote_code=False, padding_side='left')
    lengths = [len(ids) for ids in tokenizer(labels, truncation=False)['input_ids']]
    require(max(lengths) <= 512, 'Concept exceeds 512 tokens; refusing silent truncation')
    pooling = json.loads((directory/'1_Pooling/config.json').read_text(encoding='utf-8'))
    require(pooling['pooling_mode_lasttoken'] and not pooling['pooling_mode_mean_tokens'],
            'Pinned Qwen model must use last-token pooling')
    torch.set_num_threads(4)
    print(f'Embedding {len(labels)} unique labels with {MODEL_ID} on {device}...', flush=True)
    model = AutoModel.from_pretrained(directory, local_files_only=True, trust_remote_code=False,
                                      use_safetensors=True, dtype=torch.float32).to(device).eval()
    vectors = {}
    with torch.inference_mode():
        for start in range(0,len(labels),16):
            batch = labels[start:start+16]
            encoded = tokenizer(batch, padding=True, truncation=False, return_tensors='pt').to(device)
            require(bool(encoded['attention_mask'][:,-1].all()), 'Last embedding token cannot be padding')
            pooled = model(**encoded, use_cache=False).last_hidden_state[:,-1]
            normalized = torch.nn.functional.normalize(pooled,p=2,dim=1).cpu()
            require(bool(torch.isfinite(normalized).all()), 'Nonfinite embedding vector')
            require(bool(torch.allclose(normalized.norm(dim=1),torch.ones(len(batch)),atol=1e-5)),
                    'Embedding vectors must have unit norm')
            vectors.update(zip(batch,normalized.tolist()))
            if (start+16) % 512 == 0 or start+16 >= len(labels):
                print(f'Embedded {min(start+16,len(labels))}/{len(labels)} labels',flush=True)
    runtime.update(device=device, gpu=torch.cuda.get_device_name(0) if device == 'cuda' else None,
                   dtype='float32', pooling='last non-padding token + L2', instruction=None,
                   torch_version=torch.__version__, transformers_version=transformers.__version__,
                   encoded_labels=len(labels), max_label_tokens=max(lengths), model_files=model_files,
                   model_directory=MODEL_DIRECTORY)
    return vectors,runtime


def label_key(value):
    # Preserve punctuation: C++, C and C# are different labels.
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def canonical_label(value, facet, source=''):
    key, text = label_key(value), label_key(source)
    if facet == 'dataset':
        key = re.sub(r'^(?:a |an |the )?(?:new )?(?:dataset|corpus) (?:called|named) ', '', key)
        key = re.sub(r'^(?:a |an |the )', '', key)
        key = re.sub(r' (?:benchmark )?(?:dataset|corpus|collection)$', '', key)
    # Only accept abbreviations defined in this source and matching the full label's initials.
    parenthesized = re.fullmatch(r'(.+?)\s+\(([a-z0-9-]+)\)',key)
    expansion = parenthesized[1] if parenthesized and key in text else key
    words = re.findall(r'[a-z0-9]+', expansion)
    initials = ''.join(w[0] for w in words if w not in {'a','an','the','of','for','and','in','on','to'})
    if len(words) > 1 and len(initials) >= 2:
        definition = re.search(r'(?<!\w)' + re.escape(expansion) + r'\s*\(([a-z0-9-]+)\)', text)
        if definition and definition[1] == initials:
            key = definition[1]
    if facet in ('method','contribution'):
        named = re.fullmatch(r'(?:[\w-]+ ){1,12}(called|named|dubbed) ([\w+.-]+)',key)
        if named and key in text:
            if not re.search(r'\b(and|or|outperform\w*|achiev\w*|improv\w*|accuracy|correlation)\b',key):
                key = named[2]
    return key


def pair_score(silver, gold, facet, cosine, source=''):
    left, right = label_key(silver), label_key(gold)
    numbers = [set(re.sub(r'[,\s]', '', n).replace('percent','%')
                   for n in re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:%|percent))?',
                                       re.sub(r'\bf1(?:-score)?\b','f-score',v)))
               for v in (left,right)]
    blocked = None
    if all(numbers) and numbers[0] != numbers[1]:
        blocked = 'numeric_mismatch'
    if facet == 'contribution':
        finding = r'\b(achiev\w*|improv\w*|increas\w*|reduc\w*|outperform\w*|performance|accuracy|correlation|f1)\b'
        if bool(numbers[0]) != bool(numbers[1]) and any(re.search(finding,v) for v in (left,right)):
            blocked = blocked or 'missing_quantity'
        negation = r"\b(not(?! (only|just)\b)|no|without|never|cannot|can't|doesn't|isn't)\b"
        if bool(re.search(negation,left)) != bool(re.search(negation,right)):
            blocked = blocked or 'negation_mismatch'
        patterns = {'accuracy':r'\baccuracy\b', 'correlation':r'\bcorrelation\b',
                    'f1':r'\b(f1|f-score|f1-score)\b', 'auc':r'\bauc\b',
                    'perplexity':r'\bperplexity\b', 'mse':r'\b(mse|mean squared error)\b',
                    'wer':r'\b(word error|wer)\b'}
        metrics = [{k for k,pattern in patterns.items() if re.search(pattern,v)} for v in (left,right)]
        if all(metrics) and metrics[0].isdisjoint(metrics[1]):
            blocked = blocked or 'metric_mismatch'
        delta = [bool(re.search(r'\b(improv\w*|increas\w*|decreas\w*|reduc\w*|gain\w*)'
                                r'(?:\W+\w+){0,8}\s+(by|of)\s*[~≈]?\s*\d',v)) for v in (left,right)]
        level = [bool(re.search(r'\b(achiev\w*|obtain\w*|reach\w*)|\b(accuracy|correlation|f-score) of\b',v))
                 for v in (left,right)]
        if (delta[0] and level[1] and not delta[1]) or (delta[1] and level[0] and not delta[0]):
            blocked = blocked or 'quantity_role_mismatch'
    if facet == 'task':
        measurement = [bool(re.search(r'\bmeasurement study\b|\bcharacteriz\w*',v)) for v in (left,right)]
        prediction = [bool(re.search(r'\b(detect\w*|classif\w*|predict\w*)\b',v)) for v in (left,right)]
        if (measurement[0] and prediction[1] and not prediction[0]) or (
                measurement[1] and prediction[0] and not prediction[1]):
            blocked = blocked or 'different_task_operations'
    canonical = canonical_label(silver,facet,source) == canonical_label(gold,facet,source)
    return dict(score=-1.0 if blocked else 1.0 if canonical else cosine, similarity=cosine,
                match_type='canonical' if canonical else 'embedding', blocked_reason=blocked)


def metrics(tp, fp, fn):
    return dict(tp=tp, fp=fp, fn=fn,
                precision=tp/(tp+fp) if tp+fp else None,
                recall=tp/(tp+fn) if tp+fn else None,
                f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None)


def summarize(totals):
    by_facet = {facet: dict(metrics(values['tp'],values['fp'],values['fn']), exact=values['exact'])
                for facet,values in totals.items()}
    summed = {key:sum(values[key] for values in totals.values()) for key in ('tp','fp','fn')}
    defined = [values['f1'] for values in by_facet.values() if values['f1'] is not None]
    return dict(micro=metrics(**summed), by_facet=by_facet,
                macro_f1=sum(defined)/len(defined) if defined else None)


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
        require(row.get('reviewer_type', 'human') in ('human', 'ai'), f'{pid}: invalid reviewer_type')
        if row.get('reviewer_type', 'human') == 'human':
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
    reference = {'human': 'human gold', 'ai': 'nhãn tham chiếu AI',
                 'mixed': 'nhãn tham chiếu hỗn hợp người/AI'}[report['reference_kind']]
    lines = [f"# Đánh giá Qwen silver bằng {reference} ({report['matching']})", '',
             f"Đã đối chiếu {report['gold_count']} bài; nguồn nhãn: {report['reference_counts']}.", '',
             '| Facet | TP | FP | FN | Precision | Recall | F1 |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for facet, values in list(report['by_facet'].items()) + [('micro', report['micro'])]:
        lines.append(f"| {facet} | {values['tp']} | {values['fp']} | {values['fn']} | "
                     f"{percent(values['precision'])} | {percent(values['recall'])} | {percent(values['f1'])} |")
    lines.extend(['', f"Macro F1 trên các facet có mẫu: {percent(report['macro_f1'])}.",
                  f"Bài khớp cả năm facet: {report['exact_papers']}/{report['gold_count']} "
                  '(khớp chữ, tính cả hai list cùng rỗng).',
                  f"Bài ghép đủ cả năm facet theo cách so đang dùng: {report['matched_papers']}/{report['gold_count']}.", '',
                  'TP: nhãn Qwen ghép được với gold trong cùng facet; FP: nhãn Qwen dư so với gold;',
                  'FN: nhãn gold Qwen bỏ sót. N/A nghĩa là mẫu số bằng 0, không phải 100%.', '',
                  'Chuẩn hóa NFKC + hoa/thường + khoảng trắng; giữ dấu câu.',
                  'Mở per_paper.jsonl để đọc gold/silver, evidence, matched_pairs có similarity,',
                  'extra/missing và các trường hợp có thể nhầm facet.', '',
                  'Cohort: ' + report['cohort']['selection_bias'], '',
                  'Chỉ số trên cohort này không tự đại diện toàn corpus. Corpus audit chỉ',
                  'thống kê coverage/fallback/facet trống, không đo accuracy ngoài gold.',
                  'Điểm selected_score 0–100 của generator là kiểm tra bám nguồn/cấu trúc,',
                  'không phải Precision, F1 hoặc xác suất nhãn đúng ngữ nghĩa.', ''])
    if report['matching'] == 'embedding':
        baseline, current = report['lexical_baseline']['micro'], report['micro']
        lines.extend([f"Encoder: {report['embedding']['model']}; threshold cosine ≥ {report['threshold']:.2f}.",
                      'Ưu tiên các cặp khớp chữ; similarity=1.0 của match_type=exact là quy ước, không phải cosine đã tính.',
                      'Chuẩn hóa hậu tố dataset/corpus/collection và alias có định nghĩa trong chính nguồn.',
                      'Cặp canonical có assignment_score=1 theo quy tắc tên; similarity vẫn là cosine thật.',
                      'Chặn các ứng viên khác số liệu, metric, phủ định hoặc thao tác task được quy tắc nhận diện.',
                      'Phần còn lại ghép một–một trong cùng paper/facet: tối đa số cặp rồi tối đa tổng assignment_score.',
                      'Model dùng last non-padding token + L2; không thêm instruction tìm kiếm.', '',
                      '| Cách so | Precision | Recall | F1 |', '|---|---:|---:|---:|',
                      f"| Khớp chữ | {percent(baseline['precision'])} | {percent(baseline['recall'])} | {percent(baseline['f1'])} |",
                      f"| Qwen embedding | {percent(current['precision'])} | {percent(current['recall'])} | {percent(current['f1'])} |", '',
                      'Ngưỡng mặc định vẫn là 0.85: ứng viên 0.78 chưa đạt precision 90% trên 44 cặp kiểm tra.',
                      'Tập cặp do Codex rà, chưa được người xác nhận; xem scripts/exp_a/MATCHER_REFERENCE_REPORT.md.',
                      'Quy tắc không phát hiện được mọi khác biệt về phạm vi, điều kiện hoặc độ chi tiết. Các TP ở đây',
                      'là match theo ngưỡng; đây là mức đồng thuận xấp xỉ, chưa phải semantic accuracy đã xác nhận.', ''])
    else:
        lines.extend(['Exact mode không tự gộp từ đồng nghĩa, viết tắt hoặc nhãn rộng/hẹp.',
                      'Extra/missing là chênh lệch chữ cần review, chưa tự chứng minh lỗi ngữ nghĩa.', ''])
    if report['reference_kind'] != 'human':
        lines.extend(['Nhãn do AI review chưa phải human gold độc lập. Các điểm trên chỉ đo',
                      'mức đồng thuận với nhãn tham chiếu AI; cần người kiểm tra để xác nhận chất lượng.', ''])
    return '\n'.join(lines)


def evaluate(root, source='data/exp_a/generated',
             gold='data/exp_a/ground_truth/gold_review/review_annotations.jsonl',
             output=None, expected_count=400, matching='embedding', threshold=0.85):
    require(matching in ('exact','embedding'), 'Invalid matching mode')
    require(type(threshold) in (int,float) and math.isfinite(threshold) and 0 < threshold <= 1,
            'Embedding threshold must be finite and in (0, 1]')
    root = Path(root).resolve()
    output = output or ('data/exp_a/evaluation/embedding_400_revised' if matching == 'embedding'
                        else 'data/exp_a/evaluation/gold_400')
    destination = project_path(root, output)
    base = root / 'data/exp_a/evaluation'
    require(destination == base or base in destination.parents, 'Output must stay inside experiment A evaluation')
    source_directory = project_path(root, source)
    require(destination != source_directory and destination not in source_directory.parents
            and source_directory not in destination.parents, 'Evaluation output must not overlap the silver source')
    gold_path = project_path(root, gold)
    require(destination not in gold_path.parents, 'Evaluation must not overwrite human gold')
    if matching == 'embedding':
        model_directory = project_path(root,MODEL_DIRECTORY)
        require(destination != model_directory and destination not in model_directory.parents
                and model_directory not in destination.parents, 'Evaluation output must not overlap the embedding model cache')
    papers, silver, notes, source_manifest = load_silver(root, source_directory, complete=False)
    truth = reviewed_gold(gold_path, silver, expected_count)
    reference_counts = dict(collections.Counter(row.get('reviewer_type', 'human') for row in truth.values()))
    reference_kind = next(iter(reference_counts)) if len(reference_counts) == 1 else 'mixed'
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
    vectors, runtime = {}, None
    if matching == 'embedding':
        labels = set()
        for pid, row in truth.items():
            for facet in FACETS:
                predicted = {label_key(v):v for v in silver[pid][facet]}
                reference = {label_key(v):v for v in row['facets'][facet]}
                extra, missing = predicted.keys()-reference.keys(), reference.keys()-predicted.keys()
                if extra and missing:
                    labels.update(predicted[k] for k in extra)
                    labels.update(reference[k] for k in missing)
        vectors, runtime = encode_labels(root,sorted(labels))
    totals = {facet: collections.Counter(tp=0, fp=0, fn=0, exact=0) for facet in FACETS}
    lexical_totals = {facet: collections.Counter(tp=0, fp=0, fn=0, exact=0) for facet in FACETS}
    details = []
    guard_counts = collections.Counter()
    match_types = collections.Counter()
    for pid in sorted(truth):
        gold_sets = {facet: set(map(label_key, truth[pid]['facets'][facet])) for facet in FACETS}
        comparison = {}
        for facet in FACETS:
            predicted_labels = {label_key(v):v for v in silver[pid][facet]}
            reference_labels = {label_key(v):v for v in truth[pid]['facets'][facet]}
            predicted, reference = set(predicted_labels), gold_sets[facet]
            matched, extra, missing = predicted & reference, predicted-reference, reference-predicted
            lexical_totals[facet].update(tp=len(matched),fp=len(extra),fn=len(missing),exact=int(predicted == reference))
            matched_pairs = [dict(silver=predicted_labels[k],gold=reference_labels[k],similarity=1.0,match_type='exact')
                             for k in sorted(matched)]
            rejected_pairs = []
            if matching == 'embedding' and extra and missing:
                pkeys, gkeys = sorted(extra), sorted(missing)
                scores = [[max(-1.0,min(1.0,math.fsum(a*b for a,b in zip(vectors[predicted_labels[p]],
                                                                     vectors[reference_labels[g]]))))
                           for g in gkeys] for p in pkeys]
                decisions = [[pair_score(predicted_labels[p],reference_labels[g],facet,scores[i][j],
                                        papers[pid]['title'] + '\n' + papers[pid]['abstract'])
                              for j,g in enumerate(gkeys)] for i,p in enumerate(pkeys)]
                for i,p in enumerate(pkeys):
                    for j,g in enumerate(gkeys):
                        decision = decisions[i][j]
                        if decision['blocked_reason'] and scores[i][j] >= threshold:
                            guard_counts[decision['blocked_reason']] += 1
                            rejected_pairs.append(dict(silver=predicted_labels[p],gold=reference_labels[g],
                                                       similarity=scores[i][j],reason=decision['blocked_reason']))
                for i,j in match_pairs([[d['score'] for d in row] for row in decisions],threshold):
                    matched.add(pkeys[i])
                    extra.remove(pkeys[i])
                    missing.remove(gkeys[j])
                    decision = decisions[i][j]
                    matched_pairs.append(dict(silver=predicted_labels[pkeys[i]],gold=reference_labels[gkeys[j]],
                                              similarity=scores[i][j],assignment_score=decision['score'],
                                              match_type=decision['match_type']))
            match_types.update(p['match_type'] for p in matched_pairs)
            totals[facet].update(tp=len(matched), fp=len(extra), fn=len(missing), exact=int(predicted == reference))
            cross = {concept:[other for other in FACETS if other != facet and concept in gold_sets[other]]
                     for concept in sorted(extra)}
            comparison[facet] = dict(silver=silver[pid][facet], gold=truth[pid]['facets'][facet],
                                     matched=sorted(matched), extra=sorted(extra), missing=sorted(missing),
                                     matched_pairs=matched_pairs, rejected_pairs=rejected_pairs,
                                     possible_cross_facet={concept: targets for concept,targets in cross.items() if targets},
                                     silver_evidence=notes[pid]['evidence'][facet])
        details.append(dict(paper_id=pid, title=papers[pid]['title'], abstract=papers[pid]['abstract'],
                            reviewer=truth[pid].get('reviewer'),
                            reviewer_type=truth[pid].get('reviewer_type', 'human'), comparison=comparison,
                            exact=all(set(map(label_key,silver[pid][f])) == gold_sets[f] for f in FACETS),
                            fully_matched=all(not value['extra'] and not value['missing'] for value in comparison.values())))
    prefix = 'embedding' if matching == 'embedding' else 'lexical'
    evaluation_kind = (f'{prefix}_agreement_with_human_gold' if reference_kind == 'human'
                       else f'{prefix}_agreement_with_{reference_kind}_reference')
    report = dict(evaluation_version='2.1', evaluation_kind=evaluation_kind,
                  reference_kind=reference_kind, reference_counts=reference_counts,
                  matching=matching, threshold=threshold if matching == 'embedding' else None, embedding=runtime,
                  matching_version='exact_canonical_guarded_qwen3_one_to_one_v2' if matching == 'embedding' else MATCHING_VERSION,
                  matching_diagnostics=dict(match_types=dict(match_types),blocked_candidates=dict(guard_counts)),
                  gold_count=len(truth), **summarize(totals),
                  exact_papers=sum(row['exact'] for row in details), cohort=cohort,
                  matched_papers=sum(row['fully_matched'] for row in details),
                  corpus_audit=dict(corpus_papers=len(papers), available_annotations=len(silver),
                                    missing_annotations=len(papers)-len(silver), input_status=source_manifest['status'],
                                    fallback_papers=sum(bool(row.get('fallback_used')) for row in notes.values()),
                                    flagged_papers=sum(bool(row.get('fallback_used') or row.get('validation_errors'))
                                                      for row in notes.values()),
                                    nonempty_by_facet={facet:sum(bool(row[facet]) for row in silver.values()) for facet in FACETS},
                                    empty_facet_distribution={str(n):sum(sum(not row[f] for f in FACETS) == n
                                                                        for row in silver.values()) for n in range(6)}))
    if matching == 'embedding':
        report['lexical_baseline'] = dict(**summarize(lexical_totals),exact_papers=report['exact_papers'])
    write_json(destination / 'summary.json', report)
    write_jsonl(destination / 'per_paper.jsonl', details)
    (destination / 'report.md').write_text(markdown_report(report), encoding='utf-8')
    manifest = dict(evaluation_version='2.1', reference_kind=reference_kind,
                    matching_version=report['matching_version'],threshold=report['threshold'],embedding=runtime,
                    evaluator_sha256=sha256(Path(__file__)),
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
    parser.add_argument('--output')
    parser.add_argument('--expected-count', type=int, default=400)
    parser.add_argument('--matching', choices=('embedding','exact'), default='embedding')
    parser.add_argument('--threshold', type=float, default=0.85)
    args = parser.parse_args()
    try:
        output = args.output or ('data/exp_a/evaluation/embedding_400_revised' if args.matching == 'embedding'
                                else 'data/exp_a/evaluation/gold_400')
        report = evaluate(ROOT,args.source,args.gold,output,args.expected_count,args.matching,args.threshold)
        print(f"EVALUATED: {report['gold_count']} papers; reference={report['reference_kind']}; "
              f"micro={report['micro']}; output={output}")
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        parser.exit(1, f'QWEN EVALUATION FAILED: {error}\n')


if __name__ == '__main__':
    main()
