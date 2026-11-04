"""Freeze additional corpus sources for GPT extraction and independent review."""
import hashlib
import json
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'data/exp_a/.kaggle/matrix'))
import matrix


def select(count=330):
    base = matrix.base
    corpus = base.read_jsonl(ROOT/'data/processed/papers.jsonl')
    old = base.read_jsonl(ROOT/'data/exp_a/ground_truth/gold_review/review_papers.jsonl')
    pilot = base.read_jsonl(ROOT/'data/exp_a/pilot50/ai_reference_v1/source_papers.jsonl')
    excluded = {p['paper_id'] for p in old+pilot}
    instruction = '\n\n'.join((ROOT/name).read_text(encoding='utf-8') for name in (
        'data/exp_a/prompts/facet_guideline_v3.md', 'data/exp_a/prompts/extraction_v3_7.md'))
    excluded.update(re.findall(r'P\d{6}', instruction))
    titles = {' '.join(p['title'].casefold().split()) for p in old+pilot}
    candidates = []
    for row in sorted(corpus, key=lambda p:p['paper_id']):
        title = ' '.join(row['title'].casefold().split())
        if row['paper_id'] in excluded or title in titles or not row['abstract'].strip():
            continue
        titles.add(title)
        candidates.append({k:row[k] for k in ('paper_id','title','abstract')})
    assert len(candidates) >= count and not ({p['paper_id'] for p in candidates} & excluded)
    selected = random.Random(43).sample(candidates, count)
    selected.sort(key=lambda p:p['paper_id'])
    destination = ROOT/'data/exp_a/finetuning/teacher'
    destination.mkdir(parents=True, exist_ok=True)
    sources = destination/'source_candidates.jsonl'
    payload = ''.join(json.dumps(p, ensure_ascii=False)+'\n' for p in selected)
    if sources.exists():
        assert sources.read_text(encoding='utf-8') == payload, 'Frozen teacher selection differs'
    else:
        sources.write_text(payload, encoding='utf-8')
    for batch in range(3):
        rows = selected[batch::3]
        base.write_jsonl(destination/f'batch_{batch+1}/sources.jsonl', rows)
    manifest = dict(seed=43, count=count, candidate_count=len(candidates),
        corpus_sha256=base.sha256(ROOT/'data/processed/papers.jsonl'),
        excluded_existing_reference_count=len(old), excluded_pilot_count=len(pilot),
        paper_ids=[p['paper_id'] for p in selected], source_sha256=hashlib.sha256(payload.encode()).hexdigest(),
        review_protocol='GPT extraction followed by independent GPT source/evidence/coverage review; AI reference, not human gold')
    base.write_json(destination/'selection.json', manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k!='paper_ids'}, indent=2))


if __name__ == '__main__':
    select()
