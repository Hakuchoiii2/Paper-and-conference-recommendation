"""Aggregate actual independent GPT reviews; never generate or repair labels."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]/'data/exp_a/.kaggle/matrix'))
import matrix

DRAFTERS = {'batch_1':'/root/sft_data_audit','batch_2':'/root/cleanup_exp_a','batch_3':'/root/qlora_trainer'}


def keyed(paths):
    rows = [row for path in paths for row in matrix.base.read_jsonl(path)]
    result = {row['paper_id']:row for row in rows}
    matrix.base.require(len(rows)==len(result), 'Duplicate teacher paper_id')
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def write_group(destination, papers, references, evidence, audit, metadata):
    destination.mkdir(parents=True,exist_ok=True)
    for name,rows in [('source_papers.jsonl',papers),('review_annotations.jsonl',references),
                      ('review_evidence.jsonl',evidence),('review_audit.jsonl',audit)]:
        matrix.base.write_jsonl(destination/name,rows)
    manifest = dict(metadata,count=len(papers),annotation_kind='ai_reference',human_review_status='pending',
        source_confirmation_pending_ids=[],files={name:matrix.base.sha256(destination/name) for name in
        ('source_papers.jsonl','review_annotations.jsonl','review_evidence.jsonl','review_audit.jsonl')})
    matrix.base.write_json(destination/'manifest.json',manifest)
    return manifest


def aggregate(teacher, destination):
    teacher,destination = Path(teacher),Path(destination)
    selection=json.loads((teacher/'selection.json').read_text(encoding='utf-8'))
    source_path=teacher/'source_candidates.jsonl'
    # select_teacher hashes UTF-8 text before Windows translates LF into CRLF.
    text_sha256=hashlib.sha256(source_path.read_text(encoding='utf-8').encode()).hexdigest()
    matrix.base.require(text_sha256==selection['source_sha256'], 'Frozen teacher sources changed')
    sources=keyed([source_path])
    matrix.base.require(set(sources)==set(selection['paper_ids']) and len(sources)==selection['count'], 'Teacher selection differs')
    reviewed, drafts, assigned, inputs = {}, {}, set(), {}
    for batch in sorted(teacher.glob('batch_*')):
        batch_sources=keyed([batch/'sources.jsonl'])
        matrix.base.require(not assigned & set(batch_sources), 'Teacher batches overlap')
        assigned.update(batch_sources)
        matrix.base.require(all(p==sources.get(pid) for pid,p in batch_sources.items()), 'Batch sources differ')
        draft_paths=sorted((batch/'drafts').glob('part_*.jsonl'))
        review_paths=sorted((batch/'reviewed').glob('part_*.jsonl'))
        batch_drafts=keyed(draft_paths)
        batch_reviews=keyed(review_paths)
        matrix.base.require(set(batch_drafts)==set(batch_sources), 'Incomplete draft coverage')
        matrix.base.require(set(batch_reviews)==set(batch_sources), 'Incomplete independent review coverage')
        for pid,row in batch_reviews.items():
            matrix.base.require(row['paper_id']==row['response']['paper_id'], 'Reviewed response ID differs')
            matrix.base.require(row['draft_agent']==DRAFTERS[batch.name] and row['review_agent']!=row['draft_agent']
                and (row['review_agent']=='/root' or row['review_agent'].startswith('/root/')), 'Review must be independent of the draft agent')
            matrix.base.require(row['review_status']=='reviewed' and row['reviewer_type']=='ai'
                and row['human_review_status']=='pending', 'Unexpected teacher review provenance')
            matrix.base.require(isinstance(row['review_notes'],list) and row['review_notes']
                and all(isinstance(note,str) and note.strip() for note in row['review_notes']), 'Missing actual source review notes')
            matrix.base.require(row['source_status'] in ('usable','incomplete'), 'Source review status missing')
        reviewed.update(batch_reviews)
        drafts.update(batch_drafts)
        for path in [batch/'sources.jsonl',*draft_paths,*review_paths]:
            inputs[str(path.relative_to(teacher))]=matrix.base.sha256(path)
    matrix.base.require(assigned==set(sources), 'Teacher batches do not cover the selection')
    papers,references,proofs,audit,rejected = [],[],[],[],[]
    for pid,paper in sorted(sources.items()):
        row=reviewed[pid]
        log=dict(row,draft_sha256=digest(drafts[pid]),review_sha256=digest(row),source_sha256=digest(paper))
        try:
            matrix.base.require(row['source_status']=='usable', 'Source incomplete: '+'; '.join(row['review_notes']))
            grounded=matrix.v3.ground_response(row['response'],paper)
            matrix.v3.validate_response(grounded,paper,policy='3.1')
        except (ValueError,KeyError,TypeError) as error:
            rejection=dict(paper_id=pid,reason=str(error))
            rejected.append(rejection)
            audit.append(dict(log,eligibility='rejected_whole_paper',reason=str(error)))
            continue
        papers.append(paper)
        references.append(dict(paper_id=pid,facets={f:[item['concept'] for item in grounded[f]] for f in matrix.FACETS},
            reviewer_type='ai',review_status='reviewed',human_review_status='pending',
            draft_agent=row['draft_agent'],review_agent=row['review_agent']))
        proofs.append(dict(paper_id=pid,source_sha256=digest(paper),
            annotation_origin='codex_gpt_independent_source_review_qlora_v1',
            draft_agent=row['draft_agent'],review_agent=row['review_agent'],review_sha256=digest(row),
            evidence={f:[dict(item,evidence_id=raw['evidence_id'],grounding_kind='source_phrase')
                for item,raw in zip(grounded[f],row['response'][f])] for f in matrix.FACETS}))
        audit.append(dict(log,eligibility='grounding_valid'))
    return write_group(destination,papers,references,proofs,audit,dict(
        protocol=selection.get('review_protocol','GPT extraction followed by independent GPT source review'),
        reviewed_count=len(reviewed),rejected_papers=rejected,input_sha256=inputs,
        selection_sha256=matrix.base.sha256(teacher/'selection.json'),source_sha256=selection['source_sha256'],
        source_file_sha256=matrix.base.sha256(source_path)))


def freeze(pool, destination, eligible_ids, count=303, seed=44, excluded=None):
    """Select whole reviewed papers after the unchanged tokenizer preflight."""
    pool,destination=Path(pool),Path(destination)
    papers=keyed([pool/'source_papers.jsonl'])
    excluded=excluded or {}
    eligible=sorted((set(papers)&set(eligible_ids))-set(excluded))
    matrix.base.require(len(eligible)>=count, f'Need {count} valid additional papers; only {len(eligible)} available')
    chosen=sorted(random.Random(seed).sample(eligible,count))
    selected=set(chosen)
    groups=[matrix.base.read_jsonl(pool/name) for name in
        ('source_papers.jsonl','review_annotations.jsonl','review_evidence.jsonl','review_audit.jsonl')]
    groups=[[row for row in rows if row['paper_id'] in selected] for rows in groups]
    return write_group(destination,*groups,dict(protocol='Frozen subset of independently GPT-reviewed source papers',
        seed=seed,paper_ids=chosen,eligible_count=len(eligible),excluded_valid_ids=sorted(set(eligible)-selected),
        source_quality_exclusions=excluded,
        pool_manifest_sha256=matrix.base.sha256(pool/'manifest.json'),
        selection_basis='Whole-paper grounding and token limits only; no student predictions or scores'))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--teacher',type=Path,default=HERE/'teacher')
    parser.add_argument('--destination',type=Path,default=HERE/'teacher/reviewed_pool')
    args=parser.parse_args()
    print(json.dumps(aggregate(args.teacher,args.destination),ensure_ascii=False,indent=2))
