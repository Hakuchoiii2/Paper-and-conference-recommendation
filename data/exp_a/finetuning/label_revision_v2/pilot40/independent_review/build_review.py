"""Build only reviewer-owned artifacts after the strict source-only seal."""
import copy,hashlib,importlib.util,json,sys
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
PILOT=HERE.parent
REV=PILOT.parent
FACETS=('problem','task','method','dataset','contribution')
read=lambda path:[json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
write=lambda path,rows:path.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows),encoding='utf-8')
config=json.loads((HERE/'review_config.json').read_text(encoding='utf-8'))
papers=read(PILOT/'source_papers.jsonl')
draft=read(HERE/'blind_annotations.jsonl')
current=read(PILOT/'adjudicated_annotations.jsonl')
decisions=read(PILOT/'facet_decisions.jsonl')
source_pending=read(PILOT/'source_confirmation_pending.jsonl')
supplement=read(PILOT/'source_verification.jsonl')
seal=json.loads((HERE/'BLIND_SEAL.json').read_text(encoding='utf-8'))
hashfile=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(hashfile(HERE/h['file'])==h['sha256'] for h in seal['hashes'])
assert len(papers)==len(draft)==len(current)==40
assert {p['paper_id'] for p in papers}=={p['paper_id'] for p in draft}=={p['paper_id'] for p in current}
assert len(decisions)==200
sources={x['paper_id']:x for x in papers}
blind={x['paper_id']:x for x in draft}
provisional={x['paper_id']:x for x in current}
finding={(x['paper_id'],x['facet']):x for x in config['findings']}
assert len(finding)==len(config['findings'])
decision={(x['paper_id'],x['facet']):x for x in decisions}
proposed=copy.deepcopy(current)
proposed_by={x['paper_id']:x for x in proposed}
reviews=[]
for paper in papers:
 pid=paper['paper_id']
 for index,facet in enumerate(FACETS):
  prior=provisional[pid][facet]
  own=blind[pid][facet]
  issue=finding.get((pid,facet))
  status=issue['status'] if issue else ('accept_exact' if prior==own else 'accept_provisional_after_source_reconciliation')
  out=dict(paper_id=pid,facet=facet,reviewer=config['reviewer'],human_review_status='pending',review_type='independent_ai_source_review',status=status,material=bool(issue and issue['material']),issue_types=issue['issue_types'] if issue else [],reason=issue['reason'] if issue else config['facet_notes'][pid][index],source_review_note=config['facet_notes'][pid][index],blind_items=own,provisional_items=prior,operations=issue.get('operations',[]) if issue else [],prior_decision_reason=decision[pid,facet]['reason'])
  if issue:
   for key in ('alternatives','pending_source_ids','pending_verbatim'):
    if key in issue:out[key]=issue[key]
   if issue['material'] and issue['operations']:
    items=proposed_by[pid][facet]
    for op in issue['operations']:
     if op['op']=='replace':items[op['index']]=copy.deepcopy(op['item'])
     elif op['op']=='remove':items.pop(op['index'])
     elif op['op']=='add':items.append(copy.deepcopy(op['item']))
     else:raise ValueError(op)
   evidence_ids=set()
   for op in issue['operations']:
    evidence_ids.update(op.get('item',{}).get('evidence_ids',[]))
   evidence_ids.update(issue.get('pending_source_ids',[]))
   for alt in issue.get('alternatives',[]):
    for item in alt.get('items',[]):evidence_ids.update(item['evidence_ids'])
   order=lambda eid:-1 if eid=='T0' else int(eid[1:])
   out['source_evidence']=[dict(evidence_id=eid,**paper['evidence_options'][eid]) for eid in sorted(evidence_ids,key=order)]
  out['proposed_items']=proposed_by[pid][facet]
  reviews.append(out)
write(HERE/'semantic_review.jsonl',reviews)
write(HERE/'semantic_findings.jsonl',[x for x in reviews if x['operations'] or x.get('alternatives')])
write(HERE/'proposed_annotations.jsonl',proposed)

spec=importlib.util.spec_from_file_location('review_v21_schema',REV/'schema.py')
schema=importlib.util.module_from_spec(spec)
spec.loader.exec_module(schema)
validation=[]
for row in proposed:
 try:
  schema.ground_response(row,sources[row['paper_id']])
 except Exception as exc:validation.append(dict(paper_id=row['paper_id'],error=str(exc)))
assert not validation,validation
summary=dict(reviewer=config['reviewer'],human_review_status='pending',papers=40,facets_reviewed=200,status_counts=dict(Counter(x['status'] for x in reviews)),material_facets=sum(x['material'] for x in reviews),material_papers=len({x['paper_id'] for x in reviews if x['material']}),advisory_facets=sum(x['status']=='advisory' for x in reviews),accepted_facets=sum(x['status'].startswith('accept_') for x in reviews),blind_schema_pass=40,proposed_schema_pass=40,sealed_hashes_unchanged=True,policy_stability_certified=False,rollout_recommended=False,post_comparison_policy_changes_require_fresh_sample=True,source_quality_cases=len(source_pending),source_verification_note='Supplemental parent report reviewed after seal; primary web sources not independently fetched in this review.',pending_source_case_added=dict(paper_id='P003168',issue='97_percent_denominator_absent_from_input'),captured_after_reveal_sha256={str(p.relative_to(REV)):hashfile(p) for p in [REV/'policy_v2_1.md',REV/'prompt_v2_1.md',PILOT/'source_papers.jsonl',PILOT/'adjudicated_annotations.jsonl',PILOT/'facet_decisions.jsonl',PILOT/'source_confirmation_pending.jsonl',PILOT/'source_verification.jsonl']})
(HERE/'REVIEW_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
