"""Paired frozen R2a-V versus source-unit-first inference on pilot50."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ARMS=('R2a-V','Source-first')
HERE=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
units=load('source_units',HERE/'units.py')
vpath=HERE/'r2a_runner.py'
if not vpath.exists():vpath=HERE.parent/'r2a/runner.py'
v=load('source_control_v',vpath)
require=v.require;read=v.read;digest=v.digest;load_shared=v.load_shared

def verify(root,settings):
    require(settings['signature']==digest({k:x for k,x in settings.items() if k!='signature'}),'Settings signature differs')
    require(settings['arms']==list(ARMS),'Changed experiment arms')
    require(settings['model']==dict(model='Qwen/Qwen3-8B',revision='b968826d9c46dd6066d109eabc6255188de91218'),'Changed model/adapter')
    for name,h in settings['code_sha256'].items():
        require(hashlib.sha256((root/name).read_bytes()).hexdigest()==h,'Changed code: '+name)
    for name,h in settings['old_files'].items():
        require(hashlib.sha256((root/name).read_bytes()).hexdigest()==h,'Changed frozen input: '+name)
    original=read(root/'matrix_settings.json')
    require(original['generation_signature']==settings['baseline_signature'],'Baseline signature differs')
    shared=load_shared(root);papers=shared.base.read_jsonl(root/'model_inputs/papers.jsonl')
    require([p['paper_id'] for p in papers]==settings['paper_ids'] and len(papers)==50,'Changed cohort')
    for pid,h in settings['r0_record_sha256'].items():
        path=root/f'results/R0/records/{pid}.json'
        require(shared.base.sha256(path)==h,'Changed cached raw draft');shared.load_record(path,settings['baseline_signature'])
    return shared,papers,original

def load_result(shared,root,settings,arm,pid):
    r=shared.load_record(root/f'results/{arm}/records/{pid}.json',settings['signature'])
    require(r['paper_id']==pid and r['arm']==arm,'Checkpoint identity differs')
    return r

def worker(root,settings,arm):
    require(arm in ARMS,'Unknown worker')
    shared,papers,original=verify(root,settings)
    config=dict(original['generation'],**settings['model'])
    require('adapter_path' not in config,'No adapter permitted')
    instruction='\n\n'.join((root/config[k]).read_text(encoding='utf-8') for k in ('guideline','prompt'))
    require(hashlib.sha256(instruction.encode()).hexdigest()==settings['instruction_sha256'],'Base instruction differs')
    missing=any(not (root/f'results/{arm}/records/{p["paper_id"]}.json').exists() for p in papers)
    generate,runtime=shared.load_generator(config) if missing else (None,None)
    for paper in papers:
        pid=paper['paper_id'];path=root/f'results/{arm}/records/{pid}.json'
        if path.exists():load_result(shared,root,settings,arm,pid);continue
        if arm=='R2a-V':
            r0=shared.load_record(root/f'results/R0/records/{pid}.json',settings['baseline_signature'])
            record=v.annotate(shared,paper,instruction,config,runtime,generate,arm,root/f'results/{arm}/last_failure.json',cached=r0['audit']['attempt_scores'][0])
            record['baseline_record_sha256']=settings['r0_record_sha256'][pid]
        else:record=units.annotate(shared,paper,instruction,config,runtime,generate)
        shared.save_record(path,record,settings['signature'])
        print(f'{arm}: saved {pid}; new_calls={record["new_cost"]["calls"]}; fallback={record["fallback_used"]}',flush=True)

def calls_at_output_token_cap(rows,arm,cap):
    # V traces omit usage; its original per-attempt audit retains it, including inherited draft.
    return sum(t.get('usage',{}).get('output_tokens',0)>=cap for r in rows
        for t in (r['call_trace'] if arm=='Source-first' else r['audit']['attempt_scores']))

def evaluate(root,settings):
    shared,papers,_=verify(root,settings)
    records={'R0':[shared.load_record(root/f'results/R0/records/{p["paper_id"]}.json',settings['baseline_signature']) for p in papers]}
    for arm in ARMS:records[arm]=[load_result(shared,root,settings,arm,p['paper_id']) for p in papers]
    # Reference is opened only here, after both complete prediction sets are loaded and verified.
    refs=shared.base.read_jsonl(root/'evaluation_only/review_annotations.jsonl')
    labels=sorted({x for rs in records.values() for r in rs for f in shared.FACETS for x in r['facets'][f]}|{x for r in refs for f in shared.FACETS for x in r['facets'][f]})
    vectors,embedding=shared.evaluator.encode_labels(root,labels)
    table=[]
    for arm,rows in records.items():
        report=shared.score_rows(papers,rows,refs,vectors,threshold=0.85)
        shared.base.write_json(root/f'results/{arm}/evaluation.json',report)
        if arm=='R0':require(all(report['micro'][k]==settings['baseline_counts'][k] for k in ('tp','fp','fn')),'R0 scorer drift')
        table.append(dict(arm=arm,**report['micro'],macro_f1=report['macro_f1'],by_facet=report['by_facet'],
            fallback=sum(r['fallback_used'] for r in rows),annotation_fallback=sum(r.get('annotation_fallback',r['fallback_used']) for r in rows),
            inventory_invalid=sum(not r['inventory_valid'] for r in rows) if arm=='Source-first' else None,
            inventory_units=sum(len(r['source_inventory']) for r in rows) if arm=='Source-first' else None,
            inventory_retry_papers=sum(len(r['inventory_attempts'])>1 for r in rows) if arm=='Source-first' else None,
            calls_at_output_token_cap=calls_at_output_token_cap(rows,arm,settings['max_new_tokens_per_call']),
            logical_calls=sum(r['audit']['attempts_used'] for r in rows),inherited_calls=50 if arm=='R2a-V' else 0,
            new_calls=sum(r.get('new_cost',{}).get('calls',0) for r in rows),
            new_input_tokens=sum(r.get('new_cost',{}).get('input_tokens',0) for r in rows),
            new_output_tokens=sum(r.get('new_cost',{}).get('output_tokens',0) for r in rows),
            new_generation_seconds=sum(r.get('new_cost',{}).get('generation_seconds',0) for r in rows)))
    result=dict(status='complete',paper_count=50,table=table,settings=settings,embedding=embedding,
        training_performed=False,reference_kind='frozen_pilot50_ai_reference',human_review_status='pending',
        limitation='Development cohort; unchanged imperfect scorer; equal logical call/token caps, unequal actual costs. Pipeline fallback for Source-first includes invalid inventory; annotation fallback is reported separately.')
    shared.base.write_json(root/'results/experiment_summary.json',result)
    lines=['# Pilot50: V versus Source-first','',result['limitation'],'',
        '| Arm | Micro F1 | Macro F1 | Pipeline fallback | Annotation fallback | Inventory invalid | New calls | Inherited calls |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in table:lines.append(f'| {r["arm"]} | {100*r["f1"]:.4f} | {100*r["macro_f1"]:.4f} | {r["fallback"]} | {r["annotation_fallback"]} | {r["inventory_invalid"]} | {r["new_calls"]} | {r["inherited_calls"]} |')
    (root/'results/experiment_table.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True);return result

def run(root,settings):
    import torch
    verify(root,settings);require(torch.cuda.device_count()==2,'Expected two T4 GPUs')
    processes=[];started=time.monotonic()
    try:
        for gpu,arm in enumerate(ARMS):
            env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu),OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
            processes.append(subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--root',str(root),'--worker',arm],env=env))
        while any(p.poll() is None for p in processes):
            require(all(p.poll() in (None,0) for p in processes),'Worker failed; checkpoints retained');time.sleep(1)
        require(all(p.returncode==0 for p in processes),'Worker failed')
    finally:
        for p in processes:
            if p.poll() is None:p.terminate();p.wait()
    result=evaluate(root,settings);result['wall_seconds']=time.monotonic()-started
    load_shared(root).base.write_json(root/'results/experiment_summary.json',result)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--worker',choices=ARMS)
    args=parser.parse_args();settings=read(args.root/'improvement_settings.json')
    if args.worker:worker(args.root,settings,args.worker)
    else:run(args.root,settings)
