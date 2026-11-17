"""07_export_human_review.py
Bước 5: Human Quality Control
Xuất danh sách các trường hợp cần duyệt tay (NEEDS_REVIEW, REJECTED) và mẫu phân tầng từ AUTO_ACCEPT:
- Cung cấp đầy đủ: Title, Abstract, Facet hiện tại, Evidence sentence, Cảnh báo lỗi, và Đề xuất của Qwen.
- Chuẩn bị file template human_corrections.jsonl để người duyệt điền xác nhận.

Output:
- data_preparation/human_review/review_queue.jsonl
- data_preparation/human_review/human_corrections.jsonl
"""

import json
from pathlib import Path
import random

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERMEDIATE_DIR = PROJECT_ROOT / "data_preparation" / "intermediate"
HUMAN_REVIEW_DIR = PROJECT_ROOT / "data_preparation" / "human_review"
INPUT_DIR = PROJECT_ROOT / "data_preparation" / "input"

FACETS = ("problem", "task", "method", "dataset", "contribution")

def main():
    HUMAN_REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    dec_path = INTERMEDIATE_DIR / "automated_decisions.jsonl"
    papers_path = INPUT_DIR / "papers.jsonl"
    silver_path = INPUT_DIR / "silver_facets.jsonl"
    sents_path = INTERMEDIATE_DIR / "source_sentences.jsonl"
    qwen_path = INTERMEDIATE_DIR / "qwen_audit.jsonl"

    print("--> Đang chuẩn bị hàng đợi duyệt cho Con người (Bước 5)...")
    decisions = [json.loads(line) for line in open(dec_path, encoding="utf-8")]
    papers_by_pid = {r["paper_id"]: r for r in (json.loads(line) for line in open(papers_path, encoding="utf-8"))}
    silver_by_pid = {r["paper_id"]: r for r in (json.loads(line) for line in open(silver_path, encoding="utf-8"))}
    sents_by_pid = {r["paper_id"]: r["sentences"] for r in (json.loads(line) for line in open(sents_path, encoding="utf-8"))}
    qwen_by_pid = {r["paper_id"]: r["semantic_audit"] for r in (json.loads(line) for line in open(qwen_path, encoding="utf-8"))}

    review_queue = []
    auto_accept_cases = []

    for d_row in decisions:
        pid = d_row["paper_id"]
        p_row = papers_by_pid.get(pid, {})
        s_row = silver_by_pid.get(pid, {})
        sents = sents_by_pid.get(pid, [])
        q_aud = qwen_by_pid.get(pid, {})
        ev_row = d_row.get("evidence", {})

        title = p_row.get("title", "")
        abstract = p_row.get("abstract", "")

        for f in FACETS:
            dec = d_row["audit_decision"].get(f)
            status = d_row["facet_status"].get(f)
            concepts = s_row.get(f, [])
            f_qwen = q_aud.get(f, {})
            ev_sents = ev_row.get(f, [])

            # Lấy text câu bằng chứng
            ev_texts = [s["text"] for s in sents if s["sentence_id"] in ev_sents]

            case_item = {
                "paper_id": pid,
                "facet": f,
                "current_concepts": concepts,
                "facet_status": status,
                "audit_decision": dec,
                "evidence_sentence_ids": ev_sents,
                "evidence_texts": ev_texts,
                "qwen_support_status": f_qwen.get("support_status"),
                "qwen_detected_issues": f_qwen.get("detected_issues"),
                "qwen_proposed_revision": f_qwen.get("proposed_revision"),
                "qwen_explanation": f_qwen.get("explanation"),
                "title": title,
                "abstract": abstract,
                "abstract_snippet": abstract[:300] + "..." if len(abstract) > 300 else abstract
            }

            if dec in ("NEEDS_REVIEW", "REJECTED"):
                review_queue.append(case_item)
            elif dec == "AUTO_ACCEPT" and status == "PRESENT":
                auto_accept_cases.append(case_item)

    # Lấy mẫu phân tầng 5% từ AUTO_ACCEPT để kiểm tra kiểm soát chất lượng (Quality Control Sample)
    rng = random.Random(42)
    sample_size = int(len(auto_accept_cases) * 0.05)
    qc_sample = rng.sample(auto_accept_cases, sample_size)
    for c in qc_sample:
        c["audit_decision"] = "AUTO_ACCEPT_QC_SAMPLE"
        review_queue.append(c)

    # Sắp xếp hàng đợi theo mức độ ưu tiên: REJECTED trước, sau đó tới NEEDS_REVIEW, cuối cùng tới QC_SAMPLE
    priority_order = {"REJECTED": 0, "NEEDS_REVIEW": 1, "AUTO_ACCEPT_QC_SAMPLE": 2}
    review_queue.sort(key=lambda x: (priority_order.get(x["audit_decision"], 3), x["paper_id"], x["facet"]))

    out_queue_path = HUMAN_REVIEW_DIR / "review_queue.jsonl"
    with open(out_queue_path, "w", encoding="utf-8") as f:
        for item in review_queue:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    out_corr_path = HUMAN_REVIEW_DIR / "human_corrections.jsonl"
    existing_corrections = {}
    if out_corr_path.exists():
        for line in open(out_corr_path, encoding="utf-8"):
            try:
                r = json.loads(line)
                existing_corrections[(r.get("paper_id"), r.get("facet"))] = r
            except Exception:
                pass

    # Tạo template human_corrections.jsonl (bảo tồn các quyết định đã có từ trước)
    template_records = []
    for item in review_queue:
        key = (item["paper_id"], item["facet"])
        if key in existing_corrections and existing_corrections[key].get("human_decision") != "PENDING":
            template_records.append(existing_corrections[key])
        else:
            template_records.append({
                "paper_id": item["paper_id"],
                "facet": item["facet"],
                "human_decision": "PENDING",  # Người duyệt đổi thành: ACCEPT, REJECT, hoặc REVISE
                "human_revised_facet": item["qwen_proposed_revision"] or item["current_concepts"],
                "human_notes": ""
            })

    with open(out_corr_path, "w", encoding="utf-8") as f:
        for r in template_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n==================== KẾT QUẢ XUẤT HÀNG ĐỢI HUMAN REVIEW ====================")
    print(f"Tổng số trường hợp đưa vào hàng đợi: {len(review_queue)}")
    print(f"  - Trường hợp REJECTED (rủi ro cao nhất)   : {sum(1 for x in review_queue if x['audit_decision'] == 'REJECTED')}")
    print(f"  - Trường hợp NEEDS_REVIEW (cần xác nhận)  : {sum(1 for x in review_queue if x['audit_decision'] == 'NEEDS_REVIEW')}")
    print(f"  - Mẫu phân tầng kiểm tra (QC Sample 5%)    : {len(qc_sample)}")
    print(f"\n-> Đã lưu danh sách xem xét đầy đủ tại: {out_queue_path}")
    print(f"-> Đã tạo template duyệt tay tại: {out_corr_path}")

if __name__ == "__main__":
    main()
