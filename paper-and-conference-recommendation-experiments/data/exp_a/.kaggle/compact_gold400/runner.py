"""Compact extraction, then source-only indexed repairs; no coverage expansion."""
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

HERE = Path(__file__).resolve().parent
ARM = 'Compact-patch'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

helper = HERE/'r2a_runner.py'
if not helper.exists():
    helper = HERE.parent/'v_recall_gold400/release_20261026_v1/preflight_project/r2a_runner.py'
engine = load('compact_frozen_helpers', helper)
require, digest, load_shared = engine.require, engine.digest, engine.load_shared

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def shard(papers, index):
    require(type(index) is int and index in (0,1), 'Expected worker0 or1')
    return papers[index::2]

def verify(root, settings, *, evaluation=False):
    require(settings['signature']==digest({k:v for k,v in settings.items() if k!='signature'}), 'Settings signature differs')
    require(settings['model']==dict(model='Qwen/Qwen3-8B',revision='b968826d9c46dd6066d109eabc6255188de91218'), 'Model changed')
    require(settings['paper_count']==len(settings['paper_ids'])==len(set(settings['paper_ids']))==400, 'Changed cohort')
    require(settings['max_logical_calls']==3 and settings['max_new_tokens_per_call']==2048, 'Changed budget')
    for name, checksum in settings['files'].items():
        if not evaluation and name.startswith(('evaluation_only/','baseline/')):
            continue
        require(sha(root/name)==checksum, 'Changed frozen file: '+name)
    shared=load_shared(root)
    papers=shared.base.read_jsonl(root/'model_inputs/papers.jsonl')
    require([p['paper_id'] for p in papers]==settings['paper_ids'], 'Source cohort differs')
    require(all(set(p)=={'paper_id','title','abstract'} for p in papers), 'Generator source contains extra fields')
    config=settings['generation']
    require(config['model']==settings['model']['model'] and config['revision']==settings['model']['revision'], 'Generation model differs')
    require(config['max_attempts']==3 and config['max_new_tokens']==2048 and config['do_sample'] is False and 'adapter_path' not in config, 'Changed generation settings')
    instruction='\n\n'.join((root/config[k]).read_text(encoding='utf-8') for k in ('guideline','prompt'))
    require(hashlib.sha256(instruction.encode()).hexdigest()==settings['instruction_sha256'], 'Instruction differs')
    return shared,papers,config,instruction

def annotate_fresh(shared, paper, instruction, config, runtime, generate, work, *, signature):
    require(config['max_attempts']==3 and config['max_new_tokens']==2048 and config['do_sample'] is False, 'Changed generation budget')
    seed=config['seed']+int(paper['paper_id'][1:])*3
    options={k:v['evidence'] for k,v in shared.base.evidence_options(paper).items()}
    source=dict(paper_id=paper['paper_id'],evidence_options=options)
    original=[dict(role='system',content=instruction+'\nReturn JSON only. Schema: '+json.dumps(shared.base.SCHEMA)),dict(role='user',content=json.dumps(source,ensure_ascii=False))]
    identity=digest(dict(paper=paper,instruction=instruction,config=config))
    draft_path=work/'drafts'/f'{paper["paper_id"]}.json'
    draft_resumed=draft_path.exists()
    if draft_resumed:
        cached=shared.load_record(draft_path,signature)
        require(cached['input_identity']==identity and cached['seed']==seed and cached['messages_sha256']==digest(original), 'Draft checkpoint identity differs')
    else:
        raw,stats=generate(original,seed)
        cached=dict(paper_id=paper['paper_id'],seed=seed,raw_output=raw,input_identity=identity,messages_sha256=digest(original),**stats)
        shared.save_record(draft_path,cached,signature)
    attempts=[];trace=[];candidates=[];current=cached['raw_output'];truncated=cached.get('reached_token_limit',False)
    protected=[]
    for step in range(3):
        patch_error=None;operations=[];messages=original;stage='extract';resumed=draft_resumed
        if step==0:
            stats={k:cached[k] for k in ('usage','generation_seconds','reached_token_limit') if k in cached}
            raw=current
        else:
            previous=attempts[-1];selection=candidates[-1][1]
            if not previous['validation_errors']:
                break
            if not previous['schema_valid'] or (previous['truncated'] and previous['stage']!='indexed_patch'):
                # A complete source-only regeneration is needed when there is no trustworthy schema.
                stage='schema_recovery'
                messages=copy.deepcopy(original)
                messages[0]['content']+='\nThe previous response was malformed or truncated. Return complete JSON within the output budget. Use compact task/method names and preserve finding scope.'
            else:
                stage='indexed_patch'
                targets=engine.repair.flagged_items(previous['validation_errors'])
                if not targets:
                    break
                packet=dict(paper_id=paper['paper_id'],annotation=selection,evidence_options=options,
                    flagged_items=[dict(facet=f,index=i,item=selection[f][i],errors=[e for e in previous['validation_errors'] if e.startswith(f'{f}[{i}]:')]) for f,i in sorted(targets)],
                    previous_patch_error=previous.get('patch_error'))
                messages=[dict(role='system',content=instruction+'\n\n'+engine.repair.PATCH_INSTRUCTION),dict(role='user',content=json.dumps(packet,ensure_ascii=False))]
            call_path=work/'calls'/f'{paper["paper_id"]}.{step+1}.json'
            call_identity=digest(dict(input_identity=identity,messages=messages,seed=seed+step))
            resumed=call_path.exists()
            if resumed:
                call=shared.load_record(call_path,signature)
                require(call['input_identity']==call_identity,'Repair checkpoint identity differs')
                raw=call['raw_output'];stats=call['stats']
            else:
                raw,stats=generate(messages,seed+step)
                shared.save_record(call_path,dict(input_identity=call_identity,raw_output=raw,stats=stats),signature)
            truncated=stats.get('reached_token_limit',False)
            if stage=='schema_recovery':
                current=raw
            else:
                try:
                    require(not truncated,'Patch reached token limit')
                    updated,operations=engine.repair.apply_patch(shared,selection,shared.base.parse_generation(raw),paper,targets)
                    current=json.dumps(updated,ensure_ascii=False)
                except (ValueError,TypeError,KeyError,IndexError) as exc:
                    patch_error=str(exc)
                    current=json.dumps(selection,ensure_ascii=False)
        value,selection,assessment=engine.repair.assess(shared,current,paper,scoped=True)
        if truncated and stage!='indexed_patch':
            assessment['validation_errors'].append('Response reached output token limit')
        if assessment['schema_valid'] and not truncated and not protected:
            targets=engine.repair.flagged_items(assessment['validation_errors'])
            protected=[(f,copy.deepcopy(item)) for f in shared.FACETS for i,item in enumerate(selection[f]) if (f,i) not in targets]
        if assessment['schema_valid']:
            require(all(item in selection[f] for f,item in protected), 'Protected item changed')
        attempts.append(dict(attempt=step+1,stage=stage,seed=seed+step,raw_output=raw,applied_output=current,patch_error=patch_error,operations=operations,truncated=bool(truncated),**stats,**assessment))
        trace.append(dict(attempt=step+1,stage=stage,inherited=False,resumed=resumed,seed=seed+step,messages_sha256=digest(messages),**stats))
        candidates.append((value,copy.deepcopy(selection)))
    index=max(range(len(attempts)),key=lambda i:(not attempts[i]['validation_errors'],not attempts[i]['truncated'],attempts[i]['schema_valid'],-len(attempts[i]['validation_errors']),attempts[i]['score'],-i))
    chosen=attempts[index];value,selection=candidates[index]
    value,post=shared.v3.filter_named_datasets(value,paper)
    usage={k:sum(t.get('usage',{}).get(k,0) for t in trace) for k in {k for t in trace for k in t.get('usage',{})}}
    seconds=sum(t['generation_seconds'] for t in trace)
    fallback=bool(chosen['validation_errors'])
    audit=dict(**runtime,paper_id=paper['paper_id'],attempts_used=len(attempts),attempt=index+1,attempt_scores=attempts,evidence_selection=selection,
        validation_errors=chosen['validation_errors'],fallback_used=fallback,validation_passed=not fallback,postprocessing=post)
    return dict(paper_id=paper['paper_id'],arm=ARM,source_sha256=digest(paper),facets=dict(paper_id=paper['paper_id'],**{f:[x['concept'] for x in value[f]] for f in shared.FACETS}),
        audit=audit,call_trace=trace,new_cost=dict(calls=len(trace),generation_seconds=seconds,**usage),usage=usage,generation_seconds=seconds,
        fallback_used=fallback,protected_items_changed=0,training_performed=False,inherited_calls=0,resumed_calls=sum(t['resumed'] for t in trace),instruction_sha256=hashlib.sha256(instruction.encode()).hexdigest())

def load_result(shared, root, settings, paper):
    record=shared.load_record(root/f'results/{ARM}/records/{paper["paper_id"]}.json',settings['signature'])
    require(record['paper_id']==paper['paper_id'] and record['arm']==ARM and record['source_sha256']==digest(paper), 'Result source identity differs')
    n=record['new_cost']['calls']
    require(1<=n<=3 and n==len(record['call_trace'])==record['audit']['attempts_used'], 'Call budget differs')
    require(all(not t['inherited'] and t.get('usage',{}).get('output_tokens',0)<=2048 for t in record['call_trace']), 'Invalid trace/budget')
    require(record['protected_items_changed']==0, 'Protected item changed')
    return record

def worker(root, settings, index):
    shared,papers,config,instruction=verify(root,settings)
    todo=shard(papers,index)
    missing=any(not (root/f'results/{ARM}/records/{p["paper_id"]}.json').exists() for p in todo)
    generate,runtime=shared.load_generator(config) if missing else (None,None)
    for paper in todo:
        path=root/f'results/{ARM}/records/{paper["paper_id"]}.json'
        if path.exists():
            load_result(shared,root,settings,paper)
            continue
        result=annotate_fresh(shared,paper,instruction,config,runtime,generate,root/f'results/{ARM}',signature=settings['signature'])
        shared.save_record(path,result,settings['signature'])
        print(f'worker{index}: saved {paper["paper_id"]}; calls={result["new_cost"]["calls"]}; fallback={result["fallback_used"]}',flush=True)

def f2(counts):
    tp,fp,fn=(counts[k] for k in ('tp','fp','fn'))
    return 5*tp/(5*tp+4*fn+fp) if 5*tp+4*fn+fp else 0

def evaluate(root, settings):
    shared,papers,_,_=verify(root,settings)
    final=[load_result(shared,root,settings,p) for p in papers]
    shared.base.write_json(root/'results/prediction_manifest.json',dict(paper_count=400,signature=settings['signature'],records={p['paper_id']:sha(root/f'results/{ARM}/records/{p["paper_id"]}.json') for p in papers}))
    verify(root,settings,evaluation=True)
    refs=shared.base.read_jsonl(root/'evaluation_only/human_gold.jsonl')
    require(len(refs)==400 and {r['paper_id'] for r in refs}==set(settings['paper_ids']), 'Gold IDs differ')
    require(all(r.get('human_review_status')=='accepted' and r.get('reviewer_type')=='human' and r.get('review_status')=='reviewed' for r in refs),'Gold acceptance differs')
    drafts=[]
    for paper,record in zip(papers,final):
        attempt=record['audit']['attempt_scores'][0]
        value,_,_=engine.repair.assess(shared,attempt['applied_output'],paper,scoped=True)
        value,_=shared.v3.filter_named_datasets(value,paper)
        drafts.append(dict(paper_id=paper['paper_id'],facets=dict(paper_id=paper['paper_id'],**{f:[x['concept'] for x in value[f]] for f in shared.FACETS}),fallback_used=bool(attempt['validation_errors'])))
    stages={'Compact-draft':drafts,ARM:final}
    labels=sorted({x for rows in stages.values() for r in rows for f in shared.FACETS for x in r['facets'][f]}|{x for r in refs for f in shared.FACETS for x in r['facets'][f]})
    vectors,embedding=shared.evaluator.encode_labels(root,labels)
    table=[]
    baseline=read(root/'baseline/experiment_summary.json')
    require(baseline['gold_sha256']==settings['gold_sha256'] and baseline['source_sha256']==settings['source_sha256'] and baseline['threshold']==.85, 'Baseline cohort/scorer differs')
    for row in baseline['table']:
        table.append(dict(row,stage='Prior-'+row['stage']))
    for name,rows in stages.items():
        report=shared.score_rows(papers,rows,refs,vectors,threshold=.85)
        report['micro']['f2']=f2(report['micro'])
        for counts in report['by_facet'].values():counts['f2']=f2(counts)
        shared.base.write_json(root/f'results/{name}/evaluation.json',report)
        table.append(dict(stage=name,**report['micro'],macro_f1=report['macro_f1'],by_facet=report['by_facet'],fallback=sum(r['fallback_used'] for r in rows)))
    result=dict(status='complete',paper_count=400,excluded_papers=0,table=table,gold_sha256=settings['gold_sha256'],source_sha256=settings['source_sha256'],threshold=.85,
        reference_kind='human_gold',human_review_status='accepted',embedding=embedding,settings=settings,fresh_calls=sum(r['new_cost']['calls'] for r in final),inherited_calls=0,
        input_tokens=sum(r['usage']['input_tokens'] for r in final),output_tokens=sum(r['usage']['output_tokens'] for r in final),generation_seconds=sum(r['generation_seconds'] for r in final),
        checkpointed_calls_reused=sum(r.get('resumed_calls',0) for r in final),cost_note='Fresh calls/tokens include each unique same-run checkpoint once; resumed outputs do not trigger duplicate generation. Inherited means external prior-run generations; none are used.',
        annotation_fallback=sum(r['fallback_used'] for r in final),protected_items_changed=sum(r['protected_items_changed'] for r in final),
        calls_at_output_token_cap=sum(t.get('reached_token_limit',False) for r in final for t in r['call_trace']),training_performed=False,adapters_enabled=False,
        limitation='Exploratory development on previously inspected accepted AI-assisted human gold400; not an independent holdout. Approximate embedding matching. Compact draft + up to2 indexed repairs; no coverage expansion. Prior rows are frozen observed baselines; actual model call costs differ.')
    shared.base.write_json(root/'results/experiment_summary.json',result)
    lines=['# Compact extraction and targeted repair on human gold400','',result['limitation'],'','| Stage | Precision | Recall | F1 | F2 | Macro F1 | Fallback |','|---|---:|---:|---:|---:|---:|---:|']
    def percent(value):return 'n/a' if value is None else f'{100*value:.4f}'
    for row in table:lines.append('| '+row['stage']+' | '+' | '.join(percent(row[k]) for k in ('precision','recall','f1','f2','macro_f1'))+f' | {row["fallback"]} |')
    (root/'results/experiment_table.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)
    return result

def run(root, settings):
    import torch
    verify(root,settings)
    require(torch.cuda.device_count()==2,'Expected two T4 GPUs')
    processes=[];started=time.monotonic()
    try:
        for index in (0,1):
            env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(index),OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
            processes.append(subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--root',str(root),'--worker',str(index)],env=env))
        while any(p.poll() is None for p in processes):
            require(all(p.poll() in (None,0) for p in processes),'Worker failed; checkpoints retained')
            time.sleep(1)
        require(all(p.returncode==0 for p in processes),'Worker failed')
    finally:
        for process in processes:
            if process.poll() is None:process.terminate();process.wait()
    result=evaluate(root,settings)
    result['wall_seconds']=time.monotonic()-started
    load_shared(root).base.write_json(root/'results/experiment_summary.json',result)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--worker',type=int,choices=(0,1));args=parser.parse_args()
    settings=read(args.root/'settings.json')
    if args.worker is not None:worker(args.root,settings,args.worker)
    else:run(args.root,settings)
