"""Paired 4B/8B x original/source-first experiments; references are read only by scoring."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'data/exp_a'))
sys.path.insert(0, str(ROOT / 'scripts/exp_a'))
import build_exp_a as base
import extraction_v3 as v3
import evaluate_exp_a as evaluator

FACETS = base.FACET_NAMES
ARMS = ('4b_original', '4b_source_first', '8b_original', '8b_source_first')
TARGETS = ('method', 'contribution')
METHOD = '''Extract ONLY methods actually used in this paper. Inspect the title and every
abstract sentence independently. Include named models, learning/inference algorithms,
features and analytical procedures actually used; exclude background alternatives,
research objectives and future work. One independent technique per item. Keep names
compact but preserve their distinguishing qualifiers. Do not output parent/child or
acronym/expanded-name duplicates. A task or metric alone is not a method.'''
CONTRIBUTION = '''Extract ONLY explicitly claimed contributions from the title and abstract.
Inspect every sentence for TWO roles: (artifact) a new method/model/representation,
resource or framework explicitly introduced by the authors; (finding) an actual result
or conclusion. A named artifact may be a contribution even when it is also a method.
An evaluation procedure, research objective or vague novelty adjective alone is not a
contribution. Include positive, negative and null findings. Keep one independent idea
per item. For findings preserve the subject, population/language, leading conditions,
negation, numbers, metric, comparison and limiting clause needed for the claim to hold.
A finding can be a full clause; artifact labels should be compact. Do not complete a
truncated source or repair broken words using outside knowledge.'''
COMMON = '''Read ONLY the supplied source. First choose evidence_id and copy a contiguous
span verbatim from that sentence; then select the concept using words within that span
in their original order. Do not invent names, synonyms or unsupported facts. Return []
when this facet has no explicit support; empty output is allowed. Return JSON only:
{"paper_id":"...","items":[{"evidence_id":"A0","span":"exact source substring",
"concept":"source words in order","kind":"KIND"}]}. No other keys.
For method use kind="method"; for contribution use kind="artifact" or "finding".'''


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def save_record(path, record, signature):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    value = dict(signature=signature, record=record, record_sha256=digest(record))
    base.write_json(path, value)


def load_record(path, signature):
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    base.require(value['signature'] == signature, 'Checkpoint signature differs; use a new run directory')
    base.require(digest(value['record']) == value['record_sha256'], 'Checkpoint checksum differs')
    return value['record']


def parse_items(raw, paper, facet):
    items, errors = [], []
    try:
        response = json.loads(raw)
        base.require(isinstance(response, dict) and set(response) == {'paper_id', 'items'}
                     and response['paper_id'] == paper['paper_id'] and isinstance(response['items'], list),
                     'Expected paper_id and items for this source paper')
    except (ValueError, TypeError) as error:
        return [], [str(error)]
    options, seen = base.evidence_options(paper), set()
    for index, item in enumerate(response['items']):
        try:
            base.require(isinstance(item, dict) and set(item) == {'evidence_id','span','concept','kind'}, 'Wrong item keys')
            base.require(all(isinstance(v, str) and v.strip() for v in item.values()), 'Item fields must be nonempty strings')
            base.require(item['kind'] in (('method',) if facet == 'method' else ('artifact','finding')), 'Wrong contribution/method role')
            base.require(item['evidence_id'] in options, 'Unknown evidence_id')
            sentence = options[item['evidence_id']]['evidence']
            base.require(item['span'] in sentence, 'span must be copied verbatim from the selected source sentence')
            v3.matching_span(item['concept'], item['span'])
            selected = dict(paper_id=paper['paper_id'], **{f: [] for f in FACETS})
            selected[facet] = [dict(concept=item['concept'], evidence_id=item['evidence_id'])]
            grounded = v3.ground_response(selected, paper)
            if item['kind'] == 'finding':
                v3.validate_response(grounded, paper, policy='3.2')
                start, end = sentence.index(item['span']), sentence.index(item['span']) + len(item['span'])
                boundaries = list(re.finditer(r';|\b(?:but|whereas|however|although|while)\b', sentence, re.I))
                left = max([0] + [m.end() for m in boundaries if m.end() <= start])
                right = min([len(sentence)] + [m.start() for m in boundaries if m.start() >= end])
                def negations(text):
                    text = re.sub(r"n['’]t\b", ' not', text.casefold())
                    text = re.sub(r'\bnot\s+(?:only|just)\b', '', text)
                    return set(re.findall(r'\b(?:no|not|never|without|cannot|neither|nor|unable)\b', text))
                # shortcut: contrast boundaries approximate polarity scope; semantic review still needed.
                base.require(negations(sentence[left:right]) <= negations(item['concept']),
                             'Finding drops source-clause negation; preserve the full negative claim')
            key = evaluator.label_key(item['concept'])
            base.require(key not in seen, 'Duplicate concept')
            seen.add(key)
            items.append(item)
        except (ValueError, TypeError, KeyError) as error:
            errors.append(f'{facet}[{index}]: {error}')
    return items, errors


def split_paper(paper, baseline, generate, *, seed):
    facets = {f: list(baseline[f]) for f in FACETS}
    facets['paper_id'] = paper['paper_id']
    audit, usage, seconds = {}, Counter(), 0.0
    for facet_index, facet in enumerate(TARGETS):
        source = dict(paper_id=paper['paper_id'], evidence_options={k:v['evidence'] for k,v in base.evidence_options(paper).items()})
        original = [dict(role='system', content=(METHOD if facet == 'method' else CONTRIBUTION) + '\n' + COMMON),
                    dict(role='user', content=json.dumps(source, ensure_ascii=False))]
        attempts, messages = [], original
        for attempt in range(2):
            attempt_seed = seed + int(paper['paper_id'][1:]) * 10 + facet_index * 2 + attempt
            raw, stats = generate(messages, attempt_seed)
            items, errors = parse_items(raw, paper, facet)
            usage.update(stats.get('usage', {}))
            seconds += stats.get('generation_seconds', 0)
            attempts.append(dict(raw_output=raw, seed=attempt_seed, items=items, errors=errors, **stats))
            if not errors:
                break
            # Repair only this facet; the other facet always starts from source alone.
            messages = original + [dict(role='assistant', content=raw), dict(role='user', content=(
                'Repair the invalid items using the original source. Preserve supported items.\n'
                + '\n'.join(errors) + '\nReturn the complete paper_id/items JSON for this facet.'))]
        chosen = min(range(len(attempts)), key=lambda i: (len(attempts[i]['errors']), -len(attempts[i]['items'])))
        selected = attempts[chosen]
        facets[facet] = [item['concept'] for item in selected['items']]
        audit[facet] = dict(attempts=attempts, selected_attempt=chosen+1, fallback_used=bool(selected['errors']))
    return dict(paper_id=paper['paper_id'], facets=facets, audit=audit, usage=dict(usage),
                generation_seconds=seconds, fallback_used=any(a['fallback_used'] for a in audit.values()))


def score_rows(papers, rows, references, vectors, threshold=0.85):
    ids = {p['paper_id'] for p in papers}
    predicted = {r['facets']['paper_id']:r['facets'] for r in rows}
    truth = {r['paper_id']:r for r in references}
    base.require(len(ids) == len(papers) == len(rows) == len(predicted) == len(references) == len(truth)
                 and ids == set(predicted) == set(truth), 'Experiment/reference IDs are incomplete or duplicated')
    totals = {f:Counter(tp=0,fp=0,fn=0,exact=0) for f in FACETS}
    details = []
    for paper in papers:
        pid, comparison = paper['paper_id'], {}
        for facet in FACETS:
            pred = {evaluator.label_key(v):v for v in predicted[pid][facet]}
            gold = {evaluator.label_key(v):v for v in truth[pid]['facets'][facet]}
            common = pred.keys() & gold.keys()
            extra, missing = set(pred)-common, set(gold)-common
            pairs = [dict(silver=pred[k], gold=gold[k], similarity=1.0, match_type='exact') for k in sorted(common)]
            rejected = []
            if extra and missing:
                pkeys, gkeys = sorted(extra), sorted(missing)
                scores = [[max(-1.0, min(1.0, math.fsum(a*b for a,b in zip(vectors[pred[p]], vectors[gold[g]]))))
                           for g in gkeys] for p in pkeys]
                decisions = [[evaluator.pair_score(pred[p], gold[g], facet, scores[i][j], paper['title']+'\n'+paper['abstract'])
                              for j,g in enumerate(gkeys)] for i,p in enumerate(pkeys)]
                for i,p in enumerate(pkeys):
                    for j,g in enumerate(gkeys):
                        if decisions[i][j]['blocked_reason'] and scores[i][j] >= threshold:
                            rejected.append(dict(silver=pred[p], gold=gold[g], reason=decisions[i][j]['blocked_reason']))
                for i,j in evaluator.match_pairs([[d['score'] for d in row] for row in decisions], threshold):
                    extra.remove(pkeys[i])
                    missing.remove(gkeys[j])
                    pairs.append(dict(silver=pred[pkeys[i]], gold=gold[gkeys[j]], similarity=scores[i][j],
                                      match_type=decisions[i][j]['match_type']))
            counts = dict(tp=len(pairs), fp=len(extra), fn=len(missing), exact=int(set(pred) == set(gold)))
            totals[facet].update(counts)
            comparison[facet] = dict(**counts, extra=[pred[k] for k in sorted(extra)],
                                     missing=[gold[k] for k in sorted(missing)], matched_pairs=pairs, rejected_pairs=rejected)
        details.append(dict(paper_id=pid, comparison=comparison))
    target = {k:sum(totals[f][k] for f in TARGETS) for k in ('tp','fp','fn')}
    return dict(**evaluator.summarize(totals), target_micro=evaluator.metrics(**target), details=details)


def memory_efficient_attention(module, query, key, value, attention_mask, dropout=0.0,
                               scaling=None, is_causal=None, **kwargs):
    import torch
    from torch.nn.attention import sdpa_kernel, SDPBackend
    from transformers.integrations.sdpa_attention import repeat_kv
    # Native GQA excludes the efficient kernel; T4 otherwise falls back to quadratic FP32 math.
    groups = query.shape[1] // key.shape[1]
    key, value = repeat_kv(key, groups), repeat_kv(value, groups)
    if attention_mask is not None and attention_mask.ndim == 4:
        attention_mask = attention_mask[:, :, :, :key.shape[-2]]
    if is_causal is None:
        is_causal = query.shape[-2] > 1 and attention_mask is None and getattr(module, 'is_causal', True)
    backend = SDPBackend.EFFICIENT_ATTENTION if query.is_cuda else SDPBackend.MATH
    with sdpa_kernel(backend):
        result = torch.nn.functional.scaled_dot_product_attention(query, key, value,
            attn_mask=attention_mask, dropout_p=dropout, scale=scaling, is_causal=is_causal)
    return result.transpose(1, 2).contiguous(), None


def install_attention():
    from transformers import AttentionInterface, AttentionMaskInterface
    from transformers.masking_utils import sdpa_mask
    name = 'matrix_efficient_no_gqa'
    AttentionInterface.register(name, memory_efficient_attention)
    AttentionMaskInterface.register(name, sdpa_mask)
    return name


def load_generator(config):
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    base.require(torch.cuda.device_count() == 1, 'Each worker must see exactly one GPU')
    options = dict(revision=config['revision'], cache_dir=config.get('cache_dir', '/tmp/exp_a_huggingface'),
                   local_files_only=config.get('offline', False), token=False, trust_remote_code=False)
    tokenizer = AutoTokenizer.from_pretrained(config['model'], **options)
    attention = install_attention() if config['model'] == 'Qwen/Qwen3-8B' else 'sdpa'
    model = AutoModelForCausalLM.from_pretrained(config['model'], **options, use_safetensors=True,
        torch_dtype=torch.float16, device_map='cuda', attn_implementation=attention,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16)).eval()
    if config.get('adapter_path'):
        from peft import PeftModel
        model = PeftModel.from_pretrained(model,config['adapter_path'],is_trainable=False).eval()
    runtime = dict(model=config['model'], model_revision=model.config._commit_hash,
        torch_version=torch.__version__, transformers_version=transformers.__version__,
        quantization='nf4_double', gpu_name=torch.cuda.get_device_name(0), enable_thinking=False,
        attention_implementation=attention)
    base.require(runtime['model_revision'] == config['revision'], 'Loaded model revision differs')
    def generate(messages, seed):
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        encoded = tokenizer(text, return_tensors='pt').to(model.device)
        length = encoded['input_ids'].shape[-1]
        base.require(length + config['max_new_tokens'] <= model.config.max_position_embeddings, 'Source exceeds context; no truncation permitted')
        started = time.monotonic()
        with torch.inference_mode():
            output = model.generate(**encoded, max_new_tokens=config['max_new_tokens'], do_sample=False,
                                    pad_token_id=tokenizer.eos_token_id)[0, length:]
        return tokenizer.decode(output, skip_special_tokens=True).strip(), dict(
            usage=dict(input_tokens=length, output_tokens=len(output)), generation_seconds=time.monotonic()-started,
            reached_token_limit=len(output) == config['max_new_tokens'])
    return generate, runtime


def worker(root, model_key, gpu):
    root = Path(root)
    settings = json.loads((root/'matrix_settings.json').read_text(encoding='utf-8'))
    config = dict(settings['generation'], **settings['models'][model_key])
    papers = base.read_jsonl(root/'model_inputs/papers.jsonl')[gpu::2]
    signature = settings['generation_signature']
    required = [root/f'results/{model_key}_{arm}/records/{p["paper_id"]}.json'
                for p in papers for arm in (('source_first',) if model_key == '4b' else ('original','source_first'))]
    if all(path.is_file() for path in required):
        for path in required:
            load_record(path, signature)
        print(f'{model_key} GPU {gpu}: all {len(papers)} papers restored; model load skipped',flush=True)
        return
    if model_key == '8b':
        papers.sort(key=lambda p: p['paper_id'] != 'P001604')
    cached = {r['paper_id']:r for r in base.read_jsonl(root/'model_inputs/baseline_records.jsonl')}
    instruction = '\n\n'.join((root/config[k]).read_text(encoding='utf-8') for k in ('guideline','prompt'))
    generate, runtime = load_generator(config)
    for paper in papers:
        pid = paper['paper_id']
        if model_key == '4b':
            original = cached[pid]
        else:
            path = root/f'results/{model_key}_original/records/{pid}.json'
            if path.exists():
                original = load_record(path, signature)
            else:
                value, metadata = v3.annotate(paper, instruction, config, runtime, generate,
                    root/f'results/{model_key}_original/last_failure.json')
                original = dict(paper_id=pid, facets={f:[v['concept'] for v in value[f]] for f in FACETS},
                    audit=metadata, usage=metadata['usage'], generation_seconds=metadata['generation_seconds'],
                    fallback_used=metadata['fallback_used'])
                original['facets']['paper_id'] = pid
                save_record(path, original, signature)
        path = root/f'results/{model_key}_source_first/records/{pid}.json'
        if not path.exists():
            result = split_paper(paper, original['facets'], generate, seed=config['seed'])
            result.update(runtime=runtime, inherited_from=f'{model_key}_original', inherited_fallback=original['fallback_used'])
            save_record(path, result, signature)
        else:
            load_record(path, signature)
        print(f'{model_key} GPU {gpu}: completed {pid}', flush=True)


def evaluate_matrix(root):
    root = Path(root)
    settings = json.loads((root/'matrix_settings.json').read_text(encoding='utf-8'))
    papers = base.read_jsonl(root/'model_inputs/papers.jsonl')
    references = base.read_jsonl(root/'evaluation_only/review_annotations.jsonl')
    arms = {arm:[load_record(root/f'results/{arm}/records/{p["paper_id"]}.json', settings['generation_signature'])
                  for p in papers] for arm in ARMS}
    labels = set()
    for rows in arms.values():
        for row in rows:
            for facet in FACETS:
                labels.update(row['facets'][facet])
    for row in references:
        for facet in FACETS:
            labels.update(row['facets'][facet])
    vectors, runtime = evaluator.encode_labels(root, sorted(labels))
    reports, table = {}, []
    for arm, rows in arms.items():
        report = score_rows(papers, rows, references, vectors)
        base.write_json(root/f'results/{arm}/evaluation.json', report)
        reports[arm] = report
        base.write_jsonl(root/f'results/{arm}/facets_silver.jsonl', [r['facets'] for r in rows])
        is_split = arm.endswith('source_first')
        originals = arms[arm.replace('source_first','original')]
        generation_seconds = sum(r['generation_seconds'] for r in rows)
        tokens = sum(r['usage'].get('output_tokens',0) for r in rows)
        # Split arms inherit three facets, so report that prerequisite generation cost too.
        if is_split:
            generation_seconds += sum(r['generation_seconds'] for r in originals)
            tokens += sum(r['usage'].get('output_tokens',0) for r in originals)
        table.append(dict(arm=arm, count=len(rows), precision=report['micro']['precision'], recall=report['micro']['recall'],
            micro_f1=report['micro']['f1'], macro_f1=report['macro_f1'], target_f1=report['target_micro']['f1'],
            **{f'{f}_f1':report['by_facet'][f]['f1'] for f in FACETS},
            tp=report['micro']['tp'],fp=report['micro']['fp'],fn=report['micro']['fn'],
            output_tokens=tokens, generation_seconds=generation_seconds,
            validation_fallback_count=sum(r['fallback_used'] for r in rows),
            inherited_fallback_count=sum(r.get('inherited_fallback',False) for r in rows),
            original_origin='cached_kernel9' if arm.startswith('4b') else 'fresh_same_kernel'))
    baseline = reports['4b_original']
    base.require({k:baseline['micro'][k] for k in ('tp','fp','fn')} == settings['baseline_expected_counts'],
                 'Cached baseline score differs from frozen evaluation; comparison is invalid')
    destination = root/'results'
    with (destination/'experiment_table.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    percent = lambda v: 'N/A' if v is None else f'{100*v:.2f}'
    lines = ['# Exp A: paired model/workflow comparison', '',
        '50 reused development papers; frozen AI reference, not human gold. Semantic matching threshold 0.85.',
        'Source-first changes only method/contribution; other facets come from the same-model original.',
        '4B original is reused from completed kernel 9; 8B original is generated here.',
        f"4B source-first records restored from matrix v1: {settings.get('resumed_4b_source_first_count',0)}/50. Both 8B arms use efficient attention without native GQA.",
        '4B-Instruct-2507 and 8B differ in training as well as size; this is not a pure parameter-scaling experiment.',
        'Generation seconds are summed across papers/GPUs and include inherited original cost for split arms.', '',
        '| Arm | Precision % | Recall % | Micro F1 % | Macro F1 % | Method F1 % | Contribution F1 % | Target F1 % |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for row in table:
        lines.append('| '+row['arm']+' | '+' | '.join(percent(row[k]) for k in (
            'precision','recall','micro_f1','macro_f1','method_f1','contribution_f1','target_f1'))+' |')
    lines.extend(['', 'See each arm/evaluation.json for per-paper extra/missing labels and rejected semantic matches.',
                  'No winner is selected automatically from micro F1 alone. Human source review and fresh papers remain necessary.'])
    (destination/'experiment_table.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    base.write_json(destination/'experiment_summary.json', dict(status='complete', table=table,
        reference_kind='ai', threshold=0.85, embedding=runtime, settings=settings,
        reference_sha256=base.sha256(root/'evaluation_only/review_annotations.jsonl'),
        evaluator_sha256=base.sha256(Path(evaluator.__file__)), runner_sha256=base.sha256(Path(__file__))))
    print('\n'.join(lines), flush=True)
    return table


def run(root):
    import torch
    root = Path(root)
    base.require(torch.cuda.device_count() == 2 and all('T4' in torch.cuda.get_device_name(i) for i in range(2)), 'Requires T4 x2')
    settings = json.loads((root/'matrix_settings.json').read_text(encoding='utf-8'))
    for record in base.read_jsonl(root/'model_inputs/baseline_records.jsonl'):
        save_record(root/f'results/4b_original/records/{record["paper_id"]}.json', record, settings['generation_signature'])
    recovered = root/'model_inputs/completed_4b_source_first.jsonl'
    if recovered.exists():
        for record in base.read_jsonl(recovered):
            save_record(root/f'results/4b_source_first/records/{record["paper_id"]}.json', record, settings['generation_signature'])
    for model_key in ('4b','8b'):
        processes = []
        try:
            for gpu in range(2):
                env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
                processes.append(subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),
                    '--root',str(root),'--worker',model_key,'--gpu',str(gpu)], env=env))
            for process in processes:
                base.require(process.wait() == 0, f'{model_key} worker failed; checkpoints retained; no complete table published')
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate()
                    process.wait()
    return evaluate_matrix(root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--worker', choices=('4b','8b'))
    parser.add_argument('--gpu', type=int, choices=(0,1))
    parser.add_argument('--evaluate-only', action='store_true')
    args = parser.parse_args()
    if args.worker:
        worker(args.root, args.worker, args.gpu)
    elif args.evaluate_only:
        evaluate_matrix(args.root)
    else:
        run(args.root)
