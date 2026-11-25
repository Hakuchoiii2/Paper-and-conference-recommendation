"""Isolated base-only R1/R2 interventions around the frozen v1 pipeline."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ARMS = ('R1', 'R2')
EXAMPLES = '''
Additional synthetic boundary examples (not labels for the current paper):
1. A0: "Earlier work used decision trees. We use random projection for image retrieval."
   method: [{"concept":"random projection","evidence_id":"A0"}].
   Do not include decision trees: they are prior work, not used by the authors.
2. A0: "We use random projection and nearest-neighbor search."
   method: [{"concept":"random projection","evidence_id":"A0"},
            {"concept":"nearest-neighbor search","evidence_id":"A0"}].
   They are independent techniques. Keep a compound technique name as one item.
3. A0: "We introduce ORBIT, a retrieval model. We use the existing TOOLBOX software."
   contribution: [{"concept":"ORBIT","evidence_id":"A0"}].
   TOOLBOX is an existing tool, not an introduced artifact. An explicitly used new
   model may also be method; this is not duplication within a facet.
4. A0: "On noisy inputs, ORBIT does not improve accuracy over the baseline."
   contribution: [{"concept":"On noisy inputs, ORBIT does not improve accuracy over the baseline",
                   "evidence_id":"A0"}].
   Do not shorten to "improve accuracy" or omit the noisy-input restriction.
These are illustrations of the existing rules, not instructions to fill empty
facets. Read the current paper independently and return the original JSON schema.
'''


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_shared(root):
    path = Path(root)/'data/exp_a/.kaggle/matrix.py'
    spec = importlib.util.spec_from_file_location('frozen_pilot_matrix', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def repair_packet(shared, paper, raw, config):
    _, selection, assessment = shared.v3.assess_generation(raw, paper, '3.1',
        prompt_version='3.7', dataset_resource_filter=config['dataset_resource_filter'])
    options = shared.base.evidence_options(paper)
    items, global_errors = [], []
    for error in assessment['validation_errors']:
        match = re.match(r'^(problem|task|method|dataset|contribution)\[(\d+)\]:', error)
        if not match:
            global_errors.append(error)
            continue
        facet, index = match[1], int(match[2])
        values = selection.get(facet, []) if isinstance(selection, dict) else []
        item = values[index] if isinstance(values, list) and index < len(values) else {}
        item = item if isinstance(item, dict) else {}
        eid = item.get('evidence_id')
        sentence = options.get(eid, {}).get('evidence') if isinstance(eid, str) else None
        items.append(dict(facet=facet, index=index, concept=item.get('concept'),
                          evidence_id=eid, source_sentence=sentence, error=error))
    return dict(paper_id=paper['paper_id'], invalid_items=items, global_errors=global_errors,
                valid_evidence_ids=list(options))


def annotate(shared, paper, instruction, config, runtime, generate, arm, failure_path, *, cached=None):
    require(arm in ARMS, 'Unknown experiment arm')
    require(config['max_attempts'] == 3 and config['max_new_tokens'] == 2048
            and config['do_sample'] is False, 'Changed generation budget')
    require((arm == 'R2') == (cached is not None), 'R2 requires an exact cached draft')
    if arm == 'R1':
        instruction += '\n\n' + EXAMPLES.strip()
    trace, new_usage, new_seconds = [], {}, 0.0

    def wrapped(messages, seed):
        nonlocal new_seconds
        inherited = arm == 'R2' and not trace
        actual = copy.deepcopy(messages)
        packet = None
        if inherited:
            require(cached['seed'] == seed and cached['stage'] == 'extract'
                    and cached['attempt'] == 1, 'Cached draft seed/stage differs')
            raw = cached['raw_output']
            statistics = dict(usage=copy.deepcopy(cached['usage']),
                              generation_seconds=cached['generation_seconds'])
        else:
            if arm == 'R2':
                packet = repair_packet(shared, paper, actual[-2]['content'], config)
                actual[-1]['content'] += (
                    '\nTARGETED REPAIR PACKET (source-derived, no reference labels):\n'
                    + json.dumps(packet, ensure_ascii=False)
                    + '\nRepair each flagged facet/index using the cited source sentence. If needed, '
                    'select a different supplied sentence that supports the concept. Copy source words '
                    'in order; retain subject, negation, metric, quantities, comparator and conditions. '
                    'Remove an item only if it cannot be supported. Preserve other supported items; '
                    'do not rewrite all lists merely to change the draft. No invented synonyms or '
                    'source completion. If no item errors are listed, still perform the original '
                    'source/coverage review. Return complete JSON with concept/evidence_id only.')
            raw, statistics = generate(actual, seed)
            for key, value in statistics.get('usage', {}).items():
                new_usage[key] = new_usage.get(key, 0) + value
            new_seconds += statistics.get('generation_seconds', 0)
        trace.append(dict(attempt=len(trace)+1, inherited=inherited, seed=seed,
                          messages_sha256=digest(actual), repair_packet=packet))
        return raw, statistics

    value, audit = shared.v3.annotate(paper, instruction, config, runtime, wrapped, failure_path)
    first_invalid = bool(audit['attempt_scores'][0]['validation_errors'])
    final_invalid = bool(audit['validation_errors'])
    return dict(paper_id=paper['paper_id'], arm=arm,
        facets=dict(paper_id=paper['paper_id'], **{f:[v['concept'] for v in value[f]] for f in shared.FACETS}),
        audit=audit, usage=audit['usage'], generation_seconds=audit['generation_seconds'],
        fallback_used=audit['fallback_used'], instruction_sha256=hashlib.sha256(instruction.encode()).hexdigest(),
        call_trace=trace, new_cost=dict(calls=sum(not t['inherited'] for t in trace),
            generation_seconds=new_seconds, **new_usage),
        repair_transitions=dict(draft_invalid=first_invalid, final_invalid=final_invalid,
            invalid_to_valid=first_invalid and not final_invalid,
            valid_to_invalid=not first_invalid and final_invalid))


def verify(root, settings):
    require(settings['signature'] == digest({k:v for k,v in settings.items() if k != 'signature'}),
            'Experiment settings signature differs')
    require(settings['arms'] == ['R1','R2'] and settings['model']['model'] == 'Qwen/Qwen3-8B',
            'Unapproved arms/model')
    original = read(root/'matrix_settings.json')
    require(original['generation_signature'] == settings['baseline_signature'], 'Wrong baseline release')
    for name, expected in original['files'].items():
        require(hashlib.sha256((root/name).read_bytes()).hexdigest() == expected, 'Changed frozen file: '+name)
    require(hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == settings['runner_sha256'], 'Runner changed')
    shared = load_shared(root)
    papers = shared.base.read_jsonl(root/'model_inputs/papers.jsonl')
    require([p['paper_id'] for p in papers] == settings['paper_ids'] and len(papers) == 50, 'Changed cohort')
    for pid in settings['paper_ids']:
        path = root/f'results/R0/records/{pid}.json'
        require(shared.base.sha256(path) == settings['r0_record_sha256'][pid], 'Changed R0 record: '+pid)
        shared.load_record(path, settings['baseline_signature'])
    return shared, papers, original


def load_result(shared, root, settings, arm, pid):
    result = shared.load_record(root/f'results/{arm}/records/{pid}.json', settings['signature'])
    require(result['arm'] == arm and result['paper_id'] == pid, 'Checkpoint identity differs')
    return result


def worker(root, settings, arm):
    shared, papers, original = verify(root, settings)
    config = dict(original['generation'], **settings['model'])
    require('adapter_path' not in config, 'Adapters are forbidden in this base-only experiment')
    instruction = '\n\n'.join((root/config[k]).read_text(encoding='utf-8') for k in ('guideline','prompt'))
    require(hashlib.sha256(instruction.encode()).hexdigest() == settings['instruction_sha256'], 'Instruction differs')
    missing = [p for p in papers if not (root/f'results/{arm}/records/{p["paper_id"]}.json').is_file()]
    generate, runtime = shared.load_generator(config) if missing else (None, None)
    for paper in papers:
        pid = paper['paper_id']; path = root/f'results/{arm}/records/{pid}.json'
        if path.exists():
            load_result(shared,root,settings,arm,pid)
            continue
        r0 = shared.load_record(root/f'results/R0/records/{pid}.json', settings['baseline_signature'])
        cached = r0['audit']['attempt_scores'][0] if arm == 'R2' else None
        record = annotate(shared,paper,instruction,config,runtime,generate,arm,
            root/f'results/{arm}/last_failure.json',cached=cached)
        record['baseline_record_sha256'] = settings['r0_record_sha256'][pid]
        shared.save_record(path,record,settings['signature'])
        print(f'{arm}: saved {pid}; fallback={record["fallback_used"]}',flush=True)


def evaluate(root, settings):
    shared, papers, _ = verify(root,settings)
    records = {'R0':[shared.load_record(root/f'results/R0/records/{p["paper_id"]}.json',
                    settings['baseline_signature']) for p in papers]}
    for arm in ARMS:
        records[arm] = [load_result(shared,root,settings,arm,p['paper_id']) for p in papers]
    # Open references only after both new prediction sets are sealed.
    refs = shared.base.read_jsonl(root/'evaluation_only/review_annotations.jsonl')
    labels = sorted({v for rows in records.values() for r in rows for f in shared.FACETS for v in r['facets'][f]}
                    | {v for r in refs for f in shared.FACETS for v in r['facets'][f]})
    vectors, embedding = shared.evaluator.encode_labels(root,labels)
    table = []
    for arm,rows in records.items():
        report = shared.score_rows(papers,rows,refs,vectors,threshold=0.85)
        shared.base.write_json(root/f'results/{arm}/evaluation.json',report)
        if arm == 'R0':
            require(all(report['micro'][k] == settings['baseline_counts'][k] for k in ('tp','fp','fn')),
                    'Historical R0 scoring drift; do not compare runs')
        row = dict(arm=arm, **report['micro'], macro_f1=report['macro_f1'],
            by_facet=report['by_facet'],fallback=sum(r['fallback_used'] for r in rows),
            calls=sum(r['audit']['attempts_used'] for r in rows),
            new_calls=sum(r.get('new_cost',{}).get('calls',0) for r in rows),
            inherited_calls=50 if arm=='R2' else 0,
            invalid_drafts=sum(bool(r['audit']['attempt_scores'][0]['validation_errors']) for r in rows),
            invalid_to_valid=sum(r.get('repair_transitions',{}).get('invalid_to_valid',False) for r in rows),
            valid_to_invalid=sum(r.get('repair_transitions',{}).get('valid_to_invalid',False) for r in rows),
            logical_output_tokens=sum(r['usage'].get('output_tokens',0) for r in rows),
            new_output_tokens=sum(r.get('new_cost',{}).get('output_tokens',0) for r in rows),
            new_generation_seconds=sum(r.get('new_cost',{}).get('generation_seconds',0) for r in rows))
        table.append(row)
    result = dict(status='complete',paper_count=50,arms=table,signature=settings['signature'],
        settings=settings,embedding=embedding,reference_kind='frozen_pilot50_ai_reference',
        human_review_status='pending',R4_performed=False,training_performed=False)
    shared.base.write_json(root/'results/experiment_summary.json',result)
    lines=['# Base v1 pilot50: R0 cached, R1 examples, R2 targeted repair','',
        'Reused development cohort; AI references, human review pending. No automatic winner or R4.', '',
        '| Arm | Micro F1 | Macro F1 | Precision | Recall | Fallback | New calls |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in table:
        lines.append(f'| {r["arm"]} | {100*r["f1"]:.2f} | {100*r["macro_f1"]:.2f} | '
            f'{100*r["precision"]:.2f} | {100*r["recall"]:.2f} | {r["fallback"]} | {r["new_calls"]} |')
    (root/'results/experiment_table.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)
    return result


def run(root, settings):
    import torch
    verify(root,settings)
    require(torch.cuda.device_count()==2, 'Exactly two GPUs are required for concurrent R1/R2')
    processes=[];started=time.monotonic()
    try:
        for gpu,arm in enumerate(ARMS):
            env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu),OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
            processes.append(subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),
                '--root',str(root),'--worker',arm],env=env))
        while any(p.poll() is None for p in processes):
            require(all(p.poll() in (None,0) for p in processes),'A worker failed; checkpoints retained')
            time.sleep(1)
        require(all(p.returncode==0 for p in processes),'A worker failed')
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate();p.wait()
    result=evaluate(root,settings);result['wall_seconds']=time.monotonic()-started
    load_shared(root).base.write_json(root/'results/experiment_summary.json',result)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--worker',choices=ARMS)
    args=parser.parse_args();settings=read(args.root/'improvement_settings.json')
    if args.worker:
        worker(args.root,settings,args.worker)
    else:
        run(args.root,settings)
