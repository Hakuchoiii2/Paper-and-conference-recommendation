"""Paired V versus task/method recall intervention; frozen pilot50."""
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
ARMS=('R2a-V','V-recall')
HERE=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
recall=load('v_recall_units',HERE/'recall.py')
vpath=HERE/'r2a_runner.py'
if not vpath.exists():vpath=HERE.parent/'r2a/release_20261024_v1/preflight_project/runner.py'
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
        else:
            record=recall.annotate(shared,paper,instruction,config,runtime,generate,root/f'results/{arm}/last_failure.json',cached=shared.load_record(root/f'results/R0/records/{pid}.json',settings['baseline_signature'])['audit']['attempt_scores'][0])
            record['baseline_record_sha256']=settings['r0_record_sha256'][pid]
        shared.save_record(path,record,settings['signature'])
        print(f'{arm}: saved {pid}; new_calls={record["new_cost"]["calls"]}; fallback={record["fallback_used"]}',flush=True)

def f2(counts):
    tp,fp,fn=(counts[k] for k in ('tp','fp','fn'))
    denom=5*tp+4*fn+fp
    return 5*tp/denom if denom else 0


def evaluate(root,settings):
    shared,papers,_=verify(root,settings)
    records={'R0':[shared.load_record(root/f'results/R0/records/{p["paper_id"]}.json',settings['baseline_signature']) for p in papers]}
    for arm in ARMS:records[arm]=[load_result(shared,root,settings,arm,p['paper_id']) for p in papers]
    intermediate=[]
    for row in records['V-recall']:
        base=row['coverage']['base_annotation'];audit=row['base_review_audit']
        intermediate.append(dict(paper_id=row['paper_id'],facets=dict(paper_id=row['paper_id'],**{f:[i['concept'] for i in base[f]] for f in shared.FACETS}),
            fallback_used=audit['fallback_used'],audit=audit))
    records['V-review1']=intermediate
    # Only evaluation opens reference, after both 50-paper prediction sets are sealed.
    refs=shared.base.read_jsonl(root/'evaluation_only/review_annotations.jsonl')
    labels=sorted({x for rs in records.values() for r in rs for f in shared.FACETS for x in r['facets'][f]}|{x for r in refs for f in shared.FACETS for x in r['facets'][f]})
    vectors,embedding=shared.evaluator.encode_labels(root,labels)
    reports={};table=[]
    for arm in ('R0','R2a-V','V-review1','V-recall'):
        rows=records[arm];report=shared.score_rows(papers,rows,refs,vectors,threshold=0.85);reports[arm]=report
        report['micro']['f2']=f2(report['micro'])
        for counts in report['by_facet'].values():counts['f2']=f2(counts)
        shared.base.write_json(root/f'results/{arm}/evaluation.json',report)
        if arm=='R0':require(all(report['micro'][k]==settings['baseline_counts'][k] for k in ('tp','fp','fn')),'R0 scorer drift')
        table.append(dict(arm=arm,**report['micro'],macro_f1=report['macro_f1'],by_facet=report['by_facet'],
            fallback=sum(r['fallback_used'] for r in rows),annotation_fallback=sum(r.get('annotation_fallback',r['fallback_used']) for r in rows),
            coverage_fallback=sum(r.get('coverage_fallback',False) for r in rows) if arm=='V-recall' else None,
            logical_calls=sum(r['audit']['attempts_used'] for r in rows),inherited_calls=50 if arm in ARMS else 0,
            new_calls=sum(r.get('new_cost',{}).get('calls',0) for r in rows) if arm in ARMS else None,
            new_input_tokens=sum(r.get('new_cost',{}).get('input_tokens',0) for r in rows) if arm in ARMS else None,
            new_output_tokens=sum(r.get('new_cost',{}).get('output_tokens',0) for r in rows) if arm in ARMS else None,
            new_generation_seconds=sum(r.get('new_cost',{}).get('generation_seconds',0) for r in rows) if arm in ARMS else None))
    details={d['paper_id']:d for d in reports['V-recall']['details']};addition_audit=[]
    for row in records['V-recall']:
        pid=row['paper_id'];items=[]
        for added in row['coverage']['accepted']:
            facet,item=added['facet'],added['item']
            matched={shared.evaluator.label_key(pair['silver']) for pair in details[pid]['comparison'][facet]['matched_pairs']}
            items.append(dict(**added,matched_to_reference=shared.evaluator.label_key(item['concept']) in matched))
        before=next(d for d in reports['V-review1']['details'] if d['paper_id']==pid)
        addition_audit.append(dict(paper_id=pid,additions=items,rejected=row['coverage']['rejected'],coverage_errors=row['coverage']['errors'],
            by_facet_delta={f:{k:details[pid]['comparison'][f][k]-before['comparison'][f][k] for k in ('tp','fp','fn')} for f in shared.FACETS}))
    shared.base.write_json(root/'results/coverage_addition_audit.json',addition_audit)
    result=dict(status='complete',paper_count=50,table=table,settings=settings,embedding=embedding,
        accepted_additions=sum(len(d['additions']) for d in addition_audit),
        additions_matched_to_reference=sum(x['matched_to_reference'] for d in addition_audit for x in d['additions']),
        additions_unmatched_to_reference=sum(not x['matched_to_reference'] for d in addition_audit for x in d['additions']),
        training_performed=False,reference_kind='frozen_pilot50_ai_reference',human_review_status='pending',
        limitation='Development cohort; AI reference; unchanged imperfect scorer. Matched/unmatched additions are not human semantic judgments. V-review1 is the intermediate output before coverage. Equal call caps, unequal actual costs.')
    shared.base.write_json(root/'results/experiment_summary.json',result)
    lines=['# Pilot50 V versus V-recall','',result['limitation'],'',
        '| Arm | Precision | Recall | F2 | F1 | Pipeline fallback | New calls |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in table:lines.append(f'| {r["arm"]} | {100*r["precision"]:.4f} | {100*r["recall"]:.4f} | {100*r["f2"]:.4f} | {100*r["f1"]:.4f} | {r["fallback"]} | {r["new_calls"]} |')
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
