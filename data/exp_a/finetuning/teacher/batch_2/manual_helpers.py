"""Formatting and grounding checks for manually interpreted GPT drafts."""
import json
from pathlib import Path
import sys
BATCH = Path(__file__).resolve().parent
ROOT = BATCH.parents[4]
sys.path.insert(0, str(ROOT / "data/exp_a"))
import build_exp_a as base
import extraction_v3 as v3
SOURCES = [json.loads(line) for line in (BATCH / "sources.jsonl").read_text(encoding="utf-8").splitlines()]

def show(start, end):
    for index in range(start, end):
        paper = SOURCES[index]
        print(json.dumps(dict(index=index, paper_id=paper["paper_id"], evidence={key:value["evidence"] for key,value in base.evidence_options(paper).items()}),ensure_ascii=False))

def save(part, specs):
    rows=[]
    for spec in specs:
        row=dict(paper_id=spec[0])
        for facet,items in zip(base.FACET_NAMES,spec[1:]):
            row[facet]=[dict(evidence_id=item[0],concept=item[1]) for item in items]
        rows.append(row)
    path=BATCH/"drafts"/f"part_{part:02d}.jsonl"
    path.write_text("".join(json.dumps(row,ensure_ascii=False)+"\n" for row in rows),encoding="utf-8")
    errors=[]
    for row in rows:
        paper=next(p for p in SOURCES if p["paper_id"]==row["paper_id"])
        for facet in base.FACET_NAMES:
            for item in row[facet]:
                one=dict(paper_id=row["paper_id"],**{key:[] for key in base.FACET_NAMES})
                one[facet]=[item]
                try:
                    grounded=v3.ground_response(one,paper)
                    if facet=="dataset" and v3.filter_named_datasets(grounded,paper)[1]["removed"]:
                        raise ValueError("unnamed dataset")
                except ValueError as error:
                    errors.append(dict(paper_id=row["paper_id"],facet=facet,item=item,error=str(error)))
    for error in errors:
        print(json.dumps(error,ensure_ascii=False))
    print(f"Saved {path.name}: {len(rows)} draft rows; {len(errors)} grounding errors")
    return errors
