"""Offline replay of downloaded V-recall records and stored scoring arithmetic."""
import collections
import hashlib
import importlib.util
import json
import math
import tempfile
from pathlib import Path
OUT=Path(__file__).resolve().parent
HERE=OUT.parent
FROZEN=HERE/'release_20261026_v1/preflight_project'
ROOT=OUT/'exp_a_v_recall'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
runner=load('audit_recall_runner',FROZEN/'runner.py')
settings=read(FROZEN/'improvement_settings.json')
shared,papers,original=runner.verify(FROZEN,settings)
config=dict(original['generation'],**settings['model'])
instruction='\n\n'.join((FROZEN/config[k]).read_text(encoding='utf-8') for k in ('guideline','prompt'))
paper_map={p['paper_id']:p for p in papers}
checks=[]
def check(value,label):
    if not value:raise AssertionError(label)
    checks.append(label)
def close(a,b):return math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12)
summary=read(ROOT/'results/experiment_summary.json')
check(summary['settings']==settings,'summary frozen settings')
check(read(ROOT/'improvement_settings.json')==settings,'downloaded frozen settings')
check(summary['status']=='complete' and summary['paper_count']==50,'complete cohort')
records={}
for arm in ('R0','R2a-V','V-recall'):
    fs=list((ROOT/f'results/{arm}/records').glob('*.json'))
    check(len(fs)==50,arm+' count')
    rows={}
    for f in fs:
        envelope=read(f);r=envelope['record'];pid=r['paper_id'];rows[pid]=r
        check(envelope['record_sha256']==runner.digest(r),arm+'/'+pid+' record checksum')
        check(envelope['signature']==(settings['baseline_signature'] if arm=='R0' else settings['signature']),arm+'/'+pid+' signature')
        if arm=='R0':
            check(hashlib.sha256(f.read_bytes()).hexdigest()==settings['r0_record_sha256'][pid],arm+'/'+pid+' frozen file')
        else:
            check(r['arm']==arm and len(r['call_trace'])==r['audit']['attempts_used']<=3,arm+'/'+pid+' logical call cap')
            check(sum(not t['inherited'] for t in r['call_trace'])==r['new_cost']['calls']<=2,arm+'/'+pid+' new call count')
            check(r['baseline_record_sha256']==settings['r0_record_sha256'][pid],arm+'/'+pid+' draft provenance')
            check([t['seed'] for t in r['call_trace']]==list(range(42+int(pid[1:])*3,42+int(pid[1:])*3+len(r['call_trace']))),arm+'/'+pid+' seed schedule')
    check(set(rows)==set(paper_map),arm+' IDs');records[arm]=rows
for pid,r in records['V-recall'].items():
    v=records['R2a-V'][pid];r0=records['R0'][pid]
    check(r['audit']['attempt_scores'][0]['raw_output']==r0['audit']['attempt_scores'][0]['raw_output'],pid+' inherited raw draft')
    check(r['base_review_audit']['attempt_scores'][1]['raw_output']==v['audit']['attempt_scores'][1]['raw_output'],pid+' first review output matches V')
    check(r['call_trace'][1]['messages_sha256']==v['call_trace'][1]['messages_sha256'],pid+' first review messages match V')
    coverage=r['coverage'];base=coverage['base_annotation'];paper=paper_map[pid]
    # Saved JSON sorts keys; replay the real pipeline to reconstruct prompt strings before serialization.
    replies=[(r['base_review_audit']['attempt_scores'][1]['raw_output'],r['call_trace'][1]),(coverage['raw_output'],coverage)]
    generated=[]
    def generate(messages,seed):
        raw,stats=replies[len(generated)];generated.append(messages)
        return raw,{k:stats[k] for k in ('usage','generation_seconds','reached_token_limit') if k in stats}
    with tempfile.TemporaryDirectory(dir=OUT) as tmp:
        replay=runner.recall.annotate(shared,paper,instruction,config,{},generate,Path(tmp)/'last_failure.json',cached=r0['audit']['attempt_scores'][0])
    check(replay['coverage']['messages_sha256']==coverage['messages_sha256'],pid+' coverage prompt/source hash')
    check(replay['facets']==r['facets'],pid+' full pipeline replay')
    check(replay['coverage']['base_annotation']==base,pid+' intermediate replay')
    final,audit=runner.recall.apply_additions(shared,paper,base,coverage['raw_output'],truncated=coverage.get('reached_token_limit',False))
    for key in ('accepted','accepted_count','rejected','duplicates','errors'):check(audit[key]==coverage[key],pid+' replay '+key)
    value,selection,assessment=runner.v.repair.assess(shared,json.dumps(final,ensure_ascii=False),paper,scoped=True)
    value,post=shared.v3.filter_named_datasets(value,paper)
    facets=dict(paper_id=pid,**{f:[i['concept'] for i in value[f]] for f in shared.FACETS})
    check(facets==r['facets'],pid+' final facets replay')
    check(bool(assessment['validation_errors'])==r['annotation_fallback'],pid+' annotation fallback')
    check(bool(audit['errors'] or audit['rejected'])==r['coverage_fallback'],pid+' coverage fallback')
    check(r['fallback_used']==(r['annotation_fallback'] or r['coverage_fallback']),pid+' pipeline fallback')
    for facet in ('problem','dataset','contribution'):
        # These facets must agree with the same base assessor after the named-resource filter.
        bv,_,_=runner.v.repair.assess(shared,json.dumps(base,ensure_ascii=False),paper,scoped=True)
        bv,_=shared.v3.filter_named_datasets(bv,paper)
        check(r['facets'][facet]==[i['concept'] for i in bv[facet]],pid+' non-target facet '+facet)
    stats=r['call_trace']
    for k in ('input_tokens','output_tokens'):
        check(sum(t.get('usage',{}).get(k,0) for t in stats)==r['usage'][k],pid+' logical '+k)
        check(sum(t.get('usage',{}).get(k,0) for t in stats[1:])==r['new_cost'][k],pid+' new '+k)
evaluations={}
for row in summary['table']:
    arm=row['arm'];e=read(ROOT/f'results/{arm}/evaluation.json');evaluations[arm]={d['paper_id']:d for d in e['details']}
    check(set(evaluations[arm])==set(paper_map),arm+' evaluation IDs')
    for k in ('tp','fp','fn'):
        check(sum(c[k] for d in e['details'] for c in d['comparison'].values())==row[k]==e['micro'][k],arm+' '+k+' sums')
    check(close(runner.f2(row),row['f2']),arm+' F2')
    check(close(2*row['tp']/(2*row['tp']+row['fp']+row['fn']),row['f1']),arm+' F1')
    check(close(row['tp']/(row['tp']+row['fn']),row['recall']),arm+' recall')
    check(close(row['tp']/(row['tp']+row['fp']),row['precision']),arm+' precision')
    for facet,c in row['by_facet'].items():
        for k in ('tp','fp','fn'):check(sum(d['comparison'][facet][k] for d in e['details'])==c[k],arm+'/'+facet+' '+k)
        check(close(runner.f2(c),c['f2']),arm+'/'+facet+' F2')
    if arm in records:
        check(sum(r['fallback_used'] for r in records[arm].values())==row['fallback'],arm+' fallback sum')
        if arm!='R0':
            for key,cost in [('new_calls','calls'),('new_input_tokens','input_tokens'),('new_output_tokens','output_tokens'),('new_generation_seconds','generation_seconds')]:
                check(close(sum(r['new_cost'][cost] for r in records[arm].values()),row[key]),arm+' '+key)
addition_audit=read(ROOT/'results/coverage_addition_audit.json')
check(len(addition_audit)==50,'addition audit count')
for d in addition_audit:
    pid=d['paper_id'];r=records['V-recall'][pid]
    check(len(d['additions'])==r['coverage']['accepted_count'],pid+' accepted addition count')
    for x in d['additions']:
        matched={shared.evaluator.label_key(p['silver']) for p in evaluations['V-recall'][pid]['comparison'][x['facet']]['matched_pairs']}
        check(x['matched_to_reference']==(shared.evaluator.label_key(x['item']['concept']) in matched),pid+' addition reference decision')
    for f,counts in d['by_facet_delta'].items():
        check(all(v==evaluations['V-recall'][pid]['comparison'][f][k]-evaluations['V-review1'][pid]['comparison'][f][k] for k,v in counts.items()),pid+'/'+f+' before/after delta')
check(sum(len(d['additions']) for d in addition_audit)==summary['accepted_additions'],'total additions')
check(sum(x['matched_to_reference'] for d in addition_audit for x in d['additions'])==summary['additions_matched_to_reference'],'total matched additions')
rejected=collections.Counter('source_word_order' if 'source words in their original order' in x['error'] else 'wrong_keys' if x['error']=='Expected concept/evidence_id only' else x['error'] for d in addition_audit for x in d['rejected'])
report=dict(status='passed',check_count=len(checks),checks=checks,coverage_replays=50,source_code_and_draft_hashes_verified=True,
    raw_coverage_proposals=sum(sum(len(json.loads(r['coverage']['raw_output'])[f]) for f in ('task','method')) for r in records['V-recall'].values()),duplicate_proposals=sum(len(r['coverage']['duplicates']) for r in records['V-recall'].values()),accepted_additions=summary['accepted_additions'],additions_matched=summary['additions_matched_to_reference'],additions_unmatched=summary['additions_unmatched_to_reference'],rejected_by_class=dict(rejected),
    limitation='Replayed source/validator path and stored metric arithmetic; did not rerun embedding inference. AI reference on reused development cohort, human review pending.')
(OUT/'completion_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='checks'},ensure_ascii=False,indent=2))
