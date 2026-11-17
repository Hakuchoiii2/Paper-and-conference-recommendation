"""Write manually source-authored batches; no model inference or automatic semantic labeling."""
import hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
POLICY=ROOT/'data/exp_a/finetuning/label_revision_v2'
spec=importlib.util.spec_from_file_location('root_author_schema',POLICY/'schema.py')
SCHEMA=importlib.util.module_from_spec(spec);spec.loader.exec_module(SCHEMA)
FACETS=('problem','task','method','dataset','contribution')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def draft(batch,manual,notes=None,difficult=()):
    b=Path(__file__).resolve().parent/'batches'/batch
    assert not (b/'draft_seal.json').exists(),'Existing draft is immutable'
    (b/'manual_candidate.json').write_text(json.dumps(dict(manual=manual,notes=notes or {},difficult=list(difficult)),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sources=[json.loads(l) for l in (b/'sources.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
    assert list(manual)==[v['paper_id'] for v in sources]
    rows=[]
    for source in sources:
        target=dict(paper_id=source['paper_id']);evidence=SCHEMA.base.evidence_options(source)
        assert len(manual[source['paper_id']])==5
        for facet,items in zip(FACETS,manual[source['paper_id']]):
            target[facet]=[]
            for item in items:
                if item.startswith('@'):
                    ids=item[1:].split(',');concept=' '.join(evidence[e]['evidence'] for e in ids)
                else:
                    concept,ids=item.rsplit('|',1);ids=ids.split(',')
                target[facet].append(dict(concept=concept,evidence_ids=ids))
        try:SCHEMA.ground_response(target,source)
        except Exception:
            print(source['paper_id'],target);raise
        rows.append(target)
    audits=[dict(paper_id=v['paper_id'],author_id='root',source_read='full supplied title and abstract',
        notes=(notes or {}).get(v['paper_id'],'Source-first; roles, conditions and negative findings retained; no external resource names inferred.'),
        requires_independent_review=v['paper_id'] in difficult,label_source='ai_reference',human_review_status='pending') for v in rows]
    for name,values in [('draft_annotations.jsonl',rows),('draft_audit.jsonl',audits)]:
        (b/name).write_text(''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in values),encoding='utf-8')
    seal=dict(author_id='root',paper_ids=list(manual),source_sha256=sha(b/'sources.jsonl'),
        annotations_sha256=sha(b/'draft_annotations.jsonl'),audit_sha256=sha(b/'draft_audit.jsonl'),
        policy_sha256=sha(POLICY/'policy_v2_2.md'),prompt_sha256=sha(POLICY/'prompt_v2_2.md'),schema_sha256=sha(POLICY/'response_schema.json'))
    (b/'draft_seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(batch,len(rows),sha(b/'draft_seal.json'))
