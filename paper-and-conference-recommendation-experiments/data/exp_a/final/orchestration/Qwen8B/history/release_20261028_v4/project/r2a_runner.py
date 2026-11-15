"""Pilot50 R2a ablation: V scoped validator, P indexed patches, full V+P."""
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

ARMS=('R2a-V','R2a-P','R2a-full')


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


repair=load('r2a_repair',Path(__file__).with_name('repair.py'))
legacy_path=Path(__file__).with_name('legacy.py')
if not legacy_path.exists():legacy_path=Path(__file__).parent.parent/'base_improvement/improvement.py'
legacy=load('r2a_legacy',legacy_path)
load_shared=legacy.load_shared
read=legacy.read
digest=legacy.digest
require=legacy.require


def annotate(shared,paper,instruction,config,runtime,generate,arm,failure_path,*,cached):
    require(arm in ARMS,'Unknown experiment arm')
    require(config['max_attempts']==3 and config['max_new_tokens']==2048
            and config['do_sample'] is False,'Changed generation budget')
    require(cached['stage']=='extract' and cached['attempt']==1 and
            cached['seed']==config['seed']+int(paper['paper_id'][1:])*3,'Wrong cached draft identity')
    scoped=arm in ('R2a-V','R2a-full')
    if arm=='R2a-V':
        with repair.scope_validator(shared,True):
            record=legacy.annotate(shared,paper,instruction,config,runtime,generate,'R2',failure_path,cached=cached)
        record['arm']=arm
    else:
        attempts=[]; candidates=[];trace=[];new_usage={};new_seconds=0
        identities=None;editable_original=set()
        current=cached['raw_output']; last_patch_error=None
        for step in range(3):
            raw=current; patch_error=None;operations=[]
            if step==0:
                statistics=dict(usage=copy.deepcopy(cached['usage']),generation_seconds=cached['generation_seconds'])
            else:
                previous=attempts[-1];selection=candidates[-1][1]
                if not previous['schema_valid']:
                    break
                targets={(f,i) for f,i in repair.flagged_items(previous['validation_errors'])
                         if (f,identities[f][i]) in editable_original}
                if not targets:break
                packet=dict(paper_id=paper['paper_id'],annotation=selection,
                    evidence_options={k:v['evidence'] for k,v in shared.base.evidence_options(paper).items()},
                    flagged_items=[dict(facet=f,index=i,item=selection[f][i],errors=[e for e in previous['validation_errors']
                        if e.startswith(f'{f}[{i}]:')]) for f,i in sorted(targets)],
                    previous_patch_error=last_patch_error)
                messages=[dict(role='system',content=instruction+'\n\n'+repair.PATCH_INSTRUCTION),
                          dict(role='user',content=json.dumps(packet,ensure_ascii=False))]
                raw,statistics=generate(messages,cached['seed']+step)
                raw=raw.encode('utf-8',errors='backslashreplace').decode('utf-8')
                for k,v in statistics.get('usage',{}).items():new_usage[k]=new_usage.get(k,0)+v
                new_seconds+=statistics.get('generation_seconds',0)
                try:
                    reply=shared.base.parse_generation(raw)
                    updated,operations=repair.apply_patch(shared,selection,reply,paper,targets)
                    current=json.dumps(updated,ensure_ascii=False)
                    for edit in sorted(operations,key=lambda e:(e['facet'],e['index']),reverse=True):
                        if edit['op']=='remove':identities[edit['facet']].pop(edit['index'])
                except (ValueError,TypeError,KeyError,IndexError) as exc:
                    patch_error=str(exc)
                trace.append(dict(attempt=step+1,inherited=False,seed=cached['seed']+step,
                                  messages_sha256=digest(messages),operations=operations,patch_error=patch_error))
            value,selection,assessment=repair.assess(shared,current,paper,scoped=scoped)
            if step==0 and assessment['schema_valid']:
                identities={f:list(range(len(selection[f]))) for f in shared.FACETS}
                editable_original=repair.flagged_items(assessment['validation_errors'])
            candidates.append((value,selection,copy.deepcopy(identities)))
            attempts.append(dict(attempt=step+1,stage='extract' if step==0 else 'review',
                seed=cached['seed']+step,raw_output=raw,applied_output=current,
                response_format='annotation' if step==0 else 'indexed_patch_v1',
                patch_error=patch_error,operations=operations,**assessment,
                usage=copy.deepcopy(statistics.get('usage',{})),generation_seconds=statistics.get('generation_seconds',0)))
            last_patch_error=patch_error
            if not assessment['validation_errors']:
                break
        index=max(range(len(attempts)),key=lambda i:(not attempts[i]['validation_errors'],
                  attempts[i]['schema_valid'],attempts[i]['score'],-len(attempts[i]['validation_errors']),i))
        chosen=attempts[index];value,selected,selected_ids=candidates[index]
        fallback=bool(chosen['validation_errors'])
        errors=chosen['validation_errors']+([shared.v3.NO_VALID_REVIEW] if fallback else [])
        value,postprocessing=shared.v3.filter_named_datasets(value,paper)
        usage={k:sum(a['usage'].get(k,0) for a in attempts) for k in {k for a in attempts for k in a['usage']}}
        audit=dict(**runtime,paper_id=paper['paper_id'],attempt=index+1,attempts_used=len(attempts),
            seed=chosen['seed'],selected_score=chosen['score'],attempt_scores=attempts,evidence_selection=selected,
            usage=usage,generation_seconds=sum(a['generation_seconds'] for a in attempts),
            fallback_used=fallback,validation_passed=not fallback,validation_errors=errors,
            self_review_completed=len(attempts)>1,review_kind='validator_targeted_patch_not_semantic_certification',
            source_quality=shared.v3.source_quality(paper,attempts,policy='3.1'),postprocessing=postprocessing,
            request_parameters=dict(max_new_tokens=2048,max_attempts=3,do_sample=False,
                extraction_prompt_version='3.7',extraction_policy_version='3.1',scoped_negation=scoped,
                review_application='indexed_patch_v1',dataset_resource_filter=True))
        first=attempts[0]['validation_errors']
        record=dict(paper_id=paper['paper_id'],arm=arm,facets=dict(paper_id=paper['paper_id'],
            **{f:[v['concept'] for v in value[f]] for f in shared.FACETS}),audit=audit,usage=usage,
            generation_seconds=audit['generation_seconds'],fallback_used=fallback,
            instruction_sha256=hashlib.sha256(instruction.encode()).hexdigest(),
            call_trace=[dict(attempt=1,inherited=True,seed=cached['seed'])]+trace,
            new_cost=dict(calls=len(trace),generation_seconds=new_seconds,**new_usage),
            repair_transitions=dict(draft_invalid=bool(first),final_invalid=fallback,
                invalid_to_valid=bool(first) and not fallback,valid_to_invalid=not first and fallback))
        original_selection=candidates[0][1]
        located={(f,oid):selected[f][i] for f,ids in (selected_ids or {}).items() for i,oid in enumerate(ids)}
        record['protected_items_changed']=sum(located.get((f,i))!=item for f in shared.FACETS
            for i,item in enumerate((original_selection or {}).get(f,[])) if (f,i) not in editable_original)
        record['selected_item_origins']=selected_ids
        audit_path=failure_path.parent/'attempt_audits'/f'{paper["paper_id"]}.json'
        shared.base.write_json(audit_path,audit)
        if fallback:shared.base.write_json(failure_path,audit)
    final=record['audit']['evidence_selection']
    if isinstance(final,dict):
        final=copy.deepcopy(final)
        final['dataset']=[i for i in final['dataset'] if i['concept'] in record['facets']['dataset']]
    gates={name:repair.assess(shared,json.dumps(final),paper,scoped=enabled)[2]
           for name,enabled in (('original',False),('scoped',True))}
    record['common_gate']={k:dict(valid=not v['validation_errors'],errors=v['validation_errors']) for k,v in gates.items()}
    draft=shared.base.parse_generation(cached['raw_output'])
    draft_assessment=repair.assess(shared,cached['raw_output'],paper,scoped=scoped)[2]
    flagged=repair.flagged_items(draft_assessment['validation_errors'])
    if arm=='R2a-V':
        record['protected_items_changed']=sum(item not in (final or {}).get(f,[]) for f in shared.FACETS
            for i,item in enumerate(draft.get(f,[])) if (f,i) not in flagged)
    record['common_dataset_filter_removed']=len(record['audit'].get('postprocessing',{}).get('removed',[]))
    record['protection_scope']='patch application before unchanged named-dataset postfilter; V is unrestricted review'
    record['draft_items_removed_or_reworded']=sum(item not in (final or {}).get(f,[]) for f in shared.FACETS for item in draft.get(f,[]))
    record['intervention']=dict(scoped_validator=scoped,indexed_patch=arm!='R2a-V',coverage_added=False)
    return record


def verify(root,settings):
    require(settings['signature']==digest({k:v for k,v in settings.items() if k!='signature'}),'Settings signature differs')
    require(settings['arms']==list(ARMS),'Changed arms')
    for name,h in settings['code_sha256'].items():
        require(hashlib.sha256((root/name).read_bytes()).hexdigest()==h,'Changed experiment code: '+name)
    original=read(root/'matrix_settings.json')
    require(original['generation_signature']==settings['baseline_signature'],'Wrong baseline generation')
    for name,h in settings['old_files'].items():
        require(hashlib.sha256((root/name).read_bytes()).hexdigest()==h,'Changed frozen file: '+name)
    shared=legacy.load_shared(root)
    papers=shared.base.read_jsonl(root/'model_inputs/papers.jsonl')
    require([p['paper_id'] for p in papers]==settings['paper_ids'] and len(papers)==50,'Changed cohort')
    for pid,h in settings['r0_record_sha256'].items():
        require(shared.base.sha256(root/f'results/R0/records/{pid}.json')==h,'Changed R0 record')
    return shared,papers,original


def worker(root,settings,arms):
    shared,papers,original=verify(root,settings)
    config=dict(original['generation'],**settings['model'])
    require('adapter_path' not in config,'No adapter allowed')
    instruction='\n\n'.join((root/config[k]).read_text(encoding='utf-8') for k in ('guideline','prompt'))
    require(hashlib.sha256(instruction.encode()).hexdigest()==settings['instruction_sha256'],'Instruction differs')
    generate,runtime=shared.load_generator(config)
    for arm in arms:
        for paper in papers:
            pid=paper['paper_id'];path=root/f'results/{arm}/records/{pid}.json'
            if path.exists():shared.load_record(path,settings['signature']);continue
            r0=shared.load_record(root/f'results/R0/records/{pid}.json',settings['baseline_signature'])
            record=annotate(shared,paper,instruction,config,runtime,generate,arm,
                root/f'results/{arm}/last_failure.json',cached=r0['audit']['attempt_scores'][0])
            record['baseline_record_sha256']=settings['r0_record_sha256'][pid]
            shared.save_record(path,record,settings['signature'])
            print(f'{arm}: saved {pid}; calls={record["new_cost"]["calls"]}; fallback={record["fallback_used"]}',flush=True)


def evaluate(root,settings):
    shared,papers,_=verify(root,settings)
    records={'R0':[shared.load_record(root/f'results/R0/records/{p["paper_id"]}.json',settings['baseline_signature']) for p in papers]}
    for arm in ARMS:
        records[arm]=[shared.load_record(root/f'results/{arm}/records/{p["paper_id"]}.json',settings['signature']) for p in papers]
    refs=shared.base.read_jsonl(root/'evaluation_only/review_annotations.jsonl')
    labels=sorted({v for rows in records.values() for r in rows for f in shared.FACETS for v in r['facets'][f]}
                  |{v for r in refs for f in shared.FACETS for v in r['facets'][f]})
    vectors,embedding=shared.evaluator.encode_labels(root,labels)
    table=[]
    for arm,rows in records.items():
        report=shared.score_rows(papers,rows,refs,vectors,threshold=0.85)
        shared.base.write_json(root/f'results/{arm}/evaluation.json',report)
        if arm=='R0':require(all(report['micro'][k]==settings['baseline_counts'][k] for k in ('tp','fp','fn')),'Baseline scoring drift')
        table.append(dict(arm=arm,**report['micro'],macro_f1=report['macro_f1'],by_facet=report['by_facet'],
            fallback=sum(r['fallback_used'] for r in rows),new_calls=sum(r.get('new_cost',{}).get('calls',0) for r in rows),
            logical_calls=sum(r['audit']['attempts_used'] for r in rows),inherited_calls=50 if arm!='R0' else 0,
            new_output_tokens=sum(r.get('new_cost',{}).get('output_tokens',0) for r in rows),
            new_generation_seconds=sum(r.get('new_cost',{}).get('generation_seconds',0) for r in rows),
            common_original_valid=sum(r.get('common_gate',{}).get('original',{}).get('valid',False) for r in rows) if arm!='R0' else None,
            common_scoped_valid=sum(r.get('common_gate',{}).get('scoped',{}).get('valid',False) for r in rows) if arm!='R0' else None,
            protected_items_changed=sum(r.get('protected_items_changed',0) for r in rows) if arm!='R0' else None,
            common_dataset_filter_removed=sum(r.get('common_dataset_filter_removed',0) for r in rows) if arm!='R0' else None,
            removals=sum(op['op']=='remove' for r in rows for t in r['audit']['attempt_scores'] for op in t.get('operations',[])),
            patch_failures=sum(bool(t.get('patch_error')) for r in rows for t in r['audit']['attempt_scores'])))
    historical=settings['historical_R2']
    table.insert(1,dict(historical,arm='R2_historical',new_calls=0,inherited_calls=historical['calls']))
    result=dict(status='complete',paper_count=50,table=table,settings=settings,embedding=embedding,
                reference_kind='frozen_pilot50_ai_reference',human_review_status='pending',training_performed=False,
                limitation='Scorer unchanged, known semantic matching issues; no automatic winner.')
    shared.base.write_json(root/'results/experiment_summary.json',result)
    lines=['# Pilot50: R2a-V / R2a-P / R2a-full','',result['limitation'],'',
        'Protection is measured before the unchanged common named-dataset filter; filter removals are separate. '
        'Historical controls have zero new cost; R2a draft-valid papers may need no patch call.', '',
        '| Arm | Micro F1 | Macro F1 | Fallback | New calls | Original gate valid | Protected items changed | Common filter removed |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in table:
        lines.append(f'| {r["arm"]} | {100*r["f1"]:.4f} | {100*r["macro_f1"]:.4f} | {r["fallback"]} | {r["new_calls"]} | {r.get("common_original_valid")} | {r.get("protected_items_changed")} | {r.get("common_dataset_filter_removed")} |')
    (root/'results/experiment_table.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)
    return result


def run(root,settings):
    import torch
    verify(root,settings)
    require(torch.cuda.device_count()==2,'Two T4 GPUs required')
    processes=[];started=time.monotonic()
    try:
        for gpu,arms in enumerate((('R2a-V',),('R2a-P','R2a-full'))):
            env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu),OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
            processes.append(subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--root',str(root),'--worker',','.join(arms)],env=env))
        while any(p.poll() is None for p in processes):
            require(all(p.poll() in (None,0) for p in processes),'Worker failed; checkpoints retained')
            time.sleep(1)
        require(all(p.returncode==0 for p in processes),'Worker failed')
    finally:
        for p in processes:
            if p.poll() is None:p.terminate();p.wait()
    result=evaluate(root,settings);result['wall_seconds']=time.monotonic()-started
    legacy.load_shared(root).base.write_json(root/'results/experiment_summary.json',result)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--worker')
    args=parser.parse_args();settings=read(args.root/'improvement_settings.json')
    if args.worker:
        arms=args.worker.split(',');require(all(a in ARMS for a in arms),'Unknown worker arm');worker(args.root,settings,arms)
    else:run(args.root,settings)
