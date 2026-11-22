"""Import manually graded workbook rows as initial EXP-B qrels."""

import argparse
import json
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    with (args.root / "output/human_review_queue.jsonl").open(encoding="utf-8") as file:
        queue = {row["pair_id"]: row for row in map(json.loads, file)}
    workbook = load_workbook(args.workbook, read_only=True)
    judgments = {}
    try:
        for sheet in workbook:
            if sheet.title == "Guide":
                continue
            for pair_id, candidate_id, _, grade, notes in sheet.iter_rows(
                min_row=5, max_col=5, values_only=True
            ):
                if grade is None or grade == "":
                    continue
                pair = queue.get(pair_id)
                if not pair or pair["query_id"] != sheet.title or pair["candidate_id"] != candidate_id:
                    raise ValueError(f"Unknown or mismatched pair: {pair_id}")
                if pair_id in judgments or str(grade) not in {"0", "1", "2", "3"}:
                    raise ValueError(f"Duplicate grade or invalid 0–3 grade: {pair_id}")
                judgments[pair_id] = {
                    "pair_id": pair_id, "query_id": pair["query_id"],
                    "candidate_id": candidate_id, "split": pair["split"],
                    "grade": int(grade), "notes": str(notes or ""),
                }
    finally:
        workbook.close()
    review = args.root / "human_review"
    if not judgments and (review / "human_judgments.jsonl").stat().st_size:
        raise ValueError("The workbook has no grades, but saved judgments exist")
    for name in ("human_judgments.jsonl", "initial_human_qrels.jsonl"):
        with (review / name).open("w", encoding="utf-8") as file:
            for row in judgments.values():
                file.write(json.dumps(row, ensure_ascii=False) + "\n")
    (review / "review_progress.json").write_text(json.dumps({
        "pairs": len(queue), "graded": len(judgments), "pending": len(queue) - len(judgments),
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {len(judgments)} human grades")


if __name__ == "__main__":
    main()
