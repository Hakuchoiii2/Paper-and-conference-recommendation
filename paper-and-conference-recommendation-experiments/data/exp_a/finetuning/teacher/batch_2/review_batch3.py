"""Format separately reasoned GPT reviews; validation is diagnostic only."""
import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
BATCH=ROOT/"data/exp_a/finetuning/teacher/batch_3"
sys.path.insert(0,str(ROOT/"data/exp_a"))
import build_exp_a as base
import extraction_v3 as v3
SOURCES=[json.loads(s) for s in (BATCH/"sources.jsonl").read_text(encoding="utf-8").splitlines()]
DRAFTS={r["paper_id"]:r for p in (BATCH/"drafts").glob("part_*.jsonl") for r in [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines()]}
def show(start,end):
 for index,paper in enumerate(SOURCES[start:end],start):
  print(json.dumps(dict(index=index,paper_id=paper["paper_id"],source={k:v["evidence"] for k,v in base.evidence_options(paper).items()},draft=DRAFTS.get(paper["paper_id"])),ensure_ascii=False))
def review(part,specs):
 rows=[]
 for pid,status,notes,edits in specs:
  assert status in ("usable","incomplete") and notes
  row=copy.deepcopy(DRAFTS[pid])
  for facet,items in edits.items(): row[facet]=[dict(evidence_id=e,concept=c) for e,c in items]
  paper=next(p for p in SOURCES if p["paper_id"]==pid)
  try:
   grounded=v3.ground_response(row,paper)
   removed=v3.filter_named_datasets(grounded,paper)[1]["removed"]
   if removed: print(json.dumps(dict(paper_id=pid,named_resource_guard=removed),ensure_ascii=False))
  except ValueError as error: print(json.dumps(dict(paper_id=pid,validation_error=str(error)),ensure_ascii=False))
  rows.append(dict(paper_id=pid,response=row,draft_agent="/root/qlora_trainer",review_agent="/root/cleanup_exp_a",review_status="reviewed",reviewer_type="ai",human_review_status="pending",source_status=status,review_notes=notes))
 folder=BATCH/"reviewed"
 folder.mkdir(exist_ok=True)
 path=folder/f"part_{part:02d}.jsonl"
 path.write_text("".join(json.dumps(row,ensure_ascii=False)+"\n" for row in rows),encoding="utf-8")
 print(f"Saved {path.name}: {len(rows)} independently read reviews")
