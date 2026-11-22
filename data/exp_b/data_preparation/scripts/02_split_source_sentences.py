"""02_split_source_sentences.py
Tách Title và Abstract thành danh sách các câu có gắn sentence_id:
- sentence_id = 0 : Title
- sentence_id = 1, 2, ... : Các câu trong Abstract
Output: data_preparation/intermediate/source_sentences.jsonl
"""

import json
import re
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from data_preparation.pipeline_scope import get_scope_ids

INPUT_DIR = PROJECT_ROOT / "data_preparation" / "input"
INTERMEDIATE_DIR = PROJECT_ROOT / "data_preparation" / "intermediate"

def split_into_sentences(text):
    if not text or not text.strip():
        return []
    # Quy tắc tách câu chuẩn tiếng Anh tránh tách nhầm viết tắt (e.g., i.e., vs., Fig.)
    raw_sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\'\(\[])', text.strip())
    sentences = []
    for s in raw_sentences:
        s_clean = s.strip()
        if s_clean:
            sentences.append(s_clean)
    return sentences

def main():
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    papers_path = INPUT_DIR / "papers.jsonl"
    out_path = INTERMEDIATE_DIR / "source_sentences.jsonl"

    print(f"--> Đang đọc {papers_path}...")
    records = []
    total_sentences = 0
    scope_ids = get_scope_ids()

    with open(papers_path, "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            pid = row["paper_id"]
            if scope_ids is not None and pid not in scope_ids:
                continue
            title = row.get("title", "").strip()
            abstract = row.get("abstract", "").strip()

            sentences = []
            # Câu 0 luôn là Title
            if title:
                sentences.append({"sentence_id": 0, "text": title, "type": "title"})

            # Các câu 1..k là Abstract
            abs_sents = split_into_sentences(abstract)
            for idx, s_text in enumerate(abs_sents, start=1):
                sentences.append({"sentence_id": idx, "text": s_text, "type": "abstract"})

            total_sentences += len(sentences)
            records.append({
                "paper_id": pid,
                "sentences": sentences,
                "num_sentences": len(sentences)
            })

    with open(out_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"--> Đã xử lý {len(records)} bài báo.")
    print(f"--> Tổng số câu tách được: {total_sentences} câu (Trung bình {total_sentences / len(records):.1f} câu/bài).")
    print(f"--> Đã lưu kết quả tại: {out_path}")

if __name__ == "__main__":
    main()
