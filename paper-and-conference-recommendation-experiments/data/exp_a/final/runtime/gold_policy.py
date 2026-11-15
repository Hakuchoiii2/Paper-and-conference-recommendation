"""Frozen V-recall on all accepted human-gold400 papers; two source-only workers."""
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
HERE=Path(__file__).resolve().parent
ARM='V-recall'
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
rpath=HERE/'recall.py'
if not rpath.exists():rpath=HERE.parent/'v_recall/release_20261026_v1/preflight_project/recall.py'
recall=load('human_gold400_recall',rpath)
require=recall.require;digest=recall.digest;load_shared=recall.v.load_shared

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def shard(papers,index):
    require(type(index) is int and index in (0,1),'Expected worker0 or1')
    return papers[index::2]
def f2(counts):
    tp,fp,fn=(counts[k] for k in ('tp','fp','fn'));denom=5*tp+4*fn+fp
    return 5*tp/denom if denom else 0

def verify(root,settings,*,evaluation=False):
    require(settings['signature']==digest({k:v for k,v in settings.items() if k!='signature'}),'Settings signature differs')
    require(settings['model']==dict(model='Qwen/Qwen3-8B',revision='b968826d9c46dd6066d109eabc6255188de91218'),'Model/adapter changed')
    require(settings['paper_count']==400 and len(settings['paper_ids'])==len(set(settings['paper_ids']))==400,'Changed gold400 cohort')
    require(settings['max_logical_calls']==3 and settings['max_new_tokens_per_call']==2048,'Changed budget')
    for name,h in settings['files'].items():
        if not evaluation and name.startswith('evaluation_only/'):continue
        require(sha(root/name)==h,'Changed frozen file: '+name)
    shared=load_shared(root);papers=shared.base.read_jsonl(root/'model_inputs/papers.jsonl')
    require([p['paper_id'] for p in papers]==settings['paper_ids'],'Source cohort differs')
    require(all(set(p)=={'paper_id','title','abstract'} for p in papers),'Generator source contains extra fields')
    config=settings['generation']
    require(config['model']==settings['model']['model'] and config['revision']==settings['model']['revision'],'Generation model differs')
    require(config['do_sample'] is False and config['max_attempts']==3 and config['max_new_tokens']==2048 and 'adapter_path' not in config,'Changed generation settings')
    instruction='\n\n'.join((root/config[k]).read_text(encoding='utf-8') for k in ('guideline','prompt'))
    require(hashlib.sha256(instruction.encode()).hexdigest()==settings['instruction_sha256'],'Base instruction differs')
    return shared,papers,config,instruction

def annotate_fresh(shared,paper,instruction,config,runtime,generate,work,*,signature):
    require(config['max_attempts']==3 and config['max_new_tokens']==2048 and config['do_sample'] is False,'Changed generation budget')
    pid=paper['paper_id'];seed=config['seed']+int(pid[1:])*3
    source=dict(paper_id=pid,evidence_options={k:v['evidence'] for k,v in shared.base.evidence_options(paper).items()})
    messages=[dict(role='system',content=instruction+'\nReturn JSON only. Schema: '+json.dumps(shared.base.SCHEMA)),dict(role='user',content=json.dumps(source,ensure_ascii=False))]
    identity=digest(dict(paper=paper,instruction=instruction,config=config))
    path=work/'drafts'/f'{pid}.json'
    if path.exists():
        cached=shared.load_record(path,signature)
        require(cached['input_identity']==identity and cached['seed']==seed and cached['paper_id']==pid,'Draft checkpoint input differs')
    else:
        raw,stats=generate(messages,seed)
        raw=raw.encode('utf-8',errors='backslashreplace').decode('utf-8')
        cached=dict(paper_id=pid,stage='extract',attempt=1,seed=seed,raw_output=raw,input_identity=identity,messages_sha256=digest(messages),**stats)
        shared.save_record(path,cached,signature)
    result=recall.annotate(shared,paper,instruction,config,runtime,generate,work/'last_failure.json',cached=cached)
    # The cached first pass belongs to THIS run, so its cost is fresh rather than inherited pilot cost.
    result['call_trace'][0].update(inherited=False,stage='extract',reached_token_limit=cached.get('reached_token_limit',False))
    result['new_cost']=dict(calls=3,generation_seconds=result['generation_seconds'],**result['usage'])
    result.update(inherited_calls=0,draft_origin='fresh_same_model',source_sha256=digest(paper),draft_record_sha256=digest(cached))
    require(len(result['call_trace'])==3 and all(not t['inherited'] for t in result['call_trace']),'Wrong fresh call accounting')
    return result

def load_result(shared,root,settings,paper):
    r=shared.load_record(root/f'results/{ARM}/records/{paper["paper_id"]}.json',settings['signature'])
    require(r['paper_id']==paper['paper_id'] and r['arm']==ARM and r['source_sha256']==digest(paper),'Result/source identity differs')
    require(r['audit']['attempts_used']==3 and r['new_cost']['calls']==3 and len(r['call_trace'])==3,'Result budget differs')
    require(all(not t['inherited'] for t in r['call_trace']),'Unexpected inherited cost')
    return r

def worker(root,settings,index):
    shared,papers,config,instruction=verify(root,settings)
    todo=shard(papers,index)
    missing=any(not (root/f'results/{ARM}/records/{p["paper_id"]}.json').exists() for p in todo)
    generate,runtime=shared.load_generator(config) if missing else (None,None)
    work=root/f'results/{ARM}'
    for paper in todo:
        path=work/'records'/f'{paper["paper_id"]}.json'
        if path.exists():load_result(shared,root,settings,paper);continue
        result=annotate_fresh(shared,paper,instruction,config,runtime,generate,work,signature=settings['signature'])
        shared.save_record(path,result,settings['signature'])
        print(f'worker{index}: saved {paper["paper_id"]}; calls=3; fallback={result["fallback_used"]}',flush=True)

def evaluate(root,settings):
    shared,papers,_,_=verify(root,settings)
    final=[load_result(shared,root,settings,p) for p in papers]
    shared.base.write_json(root/'results/prediction_manifest.json',dict(paper_count=400,signature=settings['signature'],records={p['paper_id']:sha(root/f'results/{ARM}/records/{p["paper_id"]}.json') for p in papers}))
    # Parse gold labels only after every prediction is loaded and the record hashes are sealed.
    verify(root,settings,evaluation=True)
    refs=shared.base.read_jsonl(root/'evaluation_only/human_gold.jsonl')
    require(len(refs)==400 and {r['paper_id'] for r in refs}==set(settings['paper_ids']),'Gold IDs differ')
    require(all(r.get('human_review_status')=='accepted' and r.get('reviewer_type')=='human' and r.get('review_status')=='reviewed' for r in refs),'Gold acceptance differs')
    stages={'Draft':[],'V-review1':[],'V-recall':final}
    for paper,r in zip(papers,final):
        value,_,assessment=recall.v.repair.assess(shared,r['audit']['attempt_scores'][0]['raw_output'],paper,scoped=True)
        value,_=shared.v3.filter_named_datasets(value,paper)
        stages['Draft'].append(dict(paper_id=paper['paper_id'],facets=dict(paper_id=paper['paper_id'],**{f:[x['concept'] for x in value[f]] for f in shared.FACETS}),fallback_used=bool(assessment['validation_errors'])))
        base=r['coverage']['base_annotation']
        stages['V-review1'].append(dict(paper_id=paper['paper_id'],facets=dict(paper_id=paper['paper_id'],**{f:[x['concept'] for x in base[f]] for f in shared.FACETS}),fallback_used=r['base_review_audit']['fallback_used']))
    labels=sorted({x for rows in stages.values() for r in rows for f in shared.FACETS for x in r['facets'][f]}|{x for r in refs for f in shared.FACETS for x in r['facets'][f]})
    vectors,embedding=shared.evaluator.encode_labels(root,labels);table=[];reports={}
    for name,rows in stages.items():
        report=shared.score_rows(papers,rows,refs,vectors,threshold=.85)
        report['micro']['f2']=f2(report['micro'])
        for counts in report['by_facet'].values():counts['f2']=f2(counts)
        shared.base.write_json(root/f'results/{name}/evaluation.json',report);reports[name]=report
        table.append(dict(stage=name,**report['micro'],macro_f1=report['macro_f1'],by_facet=report['by_facet'],fallback=sum(r['fallback_used'] for r in rows)))
    scored={d['paper_id']:d for d in reports[ARM]['details']};prior={d['paper_id']:d for d in reports['V-review1']['details']};addition_audit=[]
    for r in final:
        pid=r['paper_id'];items=[]
        for added in r['coverage']['accepted']:
            matched={shared.evaluator.label_key(x['silver']) for x in scored[pid]['comparison'][added['facet']]['matched_pairs']}
            items.append(dict(**added,matched_to_gold=shared.evaluator.label_key(added['item']['concept']) in matched))
        addition_audit.append(dict(paper_id=pid,additions=items,rejected=r['coverage']['rejected'],coverage_errors=r['coverage']['errors'],by_facet_delta={f:{k:scored[pid]['comparison'][f][k]-prior[pid]['comparison'][f][k] for k in ('tp','fp','fn')} for f in shared.FACETS}))
    shared.base.write_json(root/'results/coverage_addition_audit.json',addition_audit)
    result=dict(status='complete',paper_count=400,table=table,gold_sha256=settings['gold_sha256'],source_sha256=settings['source_sha256'],reference_kind='human_gold',human_review_status='accepted',
        threshold=.85,embedding=embedding,settings=settings,training_performed=False,adapters_enabled=False,excluded_papers=0,
        fresh_calls=sum(r['new_cost']['calls'] for r in final),inherited_calls=0,
        input_tokens=sum(r['usage']['input_tokens'] for r in final),output_tokens=sum(r['usage']['output_tokens'] for r in final),generation_seconds=sum(r['generation_seconds'] for r in final),
        annotation_fallback=sum(r['annotation_fallback'] for r in final),coverage_fallback=sum(r['coverage_fallback'] for r in final),
        accepted_additions=sum(len(x['additions']) for x in addition_audit),additions_matched_to_gold=sum(a['matched_to_gold'] for x in addition_audit for a in x['additions']),
        calls_at_output_token_cap=sum(t.get('usage',{}).get('output_tokens',0)>=2048 for r in final for t in r['call_trace']),
        limitation='Accepted AI-assisted human gold; purposively selected cohort and prior development history. Unchanged embedding scorer is approximate matching. All400 retained including audit-noted sources. No fine-tuning. Draft/first-review are diagnostics from the same3 calls, not extra arms.')
    shared.base.write_json(root/'results/experiment_summary.json',result)
    lines=['# V-recall on accepted human gold400','',result['limitation'],'',f'Gold SHA256: {settings["gold_sha256"]}','',
        '| Stage | Precision | Recall | F1 | F2 | Macro F1 | Fallback |','|---|---:|---:|---:|---:|---:|---:|']
    for row in table:lines.append(f'| {row["stage"]} | {100*row["precision"]:.4f} | {100*row["recall"]:.4f} | {100*row["f1"]:.4f} | {100*row["f2"]:.4f} | {100*row["macro_f1"]:.4f} | {row["fallback"]} |')
    (root/'results/experiment_table.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True);return result

def run(root,settings):
    import torch
    verify(root,settings);require(torch.cuda.device_count()==2,'Expected two T4 GPUs')
    processes=[];started=time.monotonic()
    try:
        for index in (0,1):
            env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(index),OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
            processes.append(subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--root',str(root),'--worker',str(index)],env=env))
        while any(p.poll() is None for p in processes):
            require(all(p.poll() in (None,0) for p in processes),'Worker failed; checkpoints retained');time.sleep(1)
        require(all(p.returncode==0 for p in processes),'Worker failed')
    finally:
        for p in processes:
            if p.poll() is None:p.terminate();p.wait()
    result=evaluate(root,settings);result['wall_seconds']=time.monotonic()-started
    load_shared(root).base.write_json(root/'results/experiment_summary.json',result)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--worker',type=int,choices=(0,1));args=parser.parse_args();settings=read(args.root/'settings.json')
    if args.worker is not None:worker(args.root,settings,args.worker)
    else:run(args.root,settings)
