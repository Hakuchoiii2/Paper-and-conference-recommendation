"""06_make_decisions.py
Bước 4: Automated Decision (Python)
Tổng hợp 3 nguồn tín hiệu:
1. Lỗi cấu trúc (structural_report.jsonl)
2. Tín hiệu embedding & cosine similarity (embedding_audit.jsonl)
3. Kết quả Semantic Audit từ Qwen (qwen_audit.jsonl)

Áp dụng chặt chẽ Mục 2.5 - Quy định về việc tự động sửa facet:
- Tình huống 1: Facet đúng, đủ thông tin -> PRESENT + AUTO_ACCEPT (Giữ nguyên)
- Tình huống 2: Facet diễn đạt chưa rõ nhưng ý đúng -> PRESENT + NEEDS_REVIEW (Qwen đề xuất, chờ Human Review)
- Tình huống 3: Facet có phần suy diễn -> PRESENT + NEEDS_REVIEW
- Tình huống 4: Facet không được nguồn hỗ trợ -> REJECTED (Reject nội dung hiện tại)
- Tình huống 5: Nguồn không đề cập -> NOT_MENTIONED + AUTO_ACCEPT (Không tự suy diễn)
- Tình huống 6: Nguồn thiếu/bị cắt -> SOURCE_MISSING + REJECTED
- Tình huống 7: Trích xuất lỗi -> EXTRACTION_FAILED + REJECTED

Output:
- data_preparation/intermediate/automated_decisions.jsonl
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERMEDIATE_DIR = PROJECT_ROOT / "data_preparation" / "intermediate"
INPUT_DIR = PROJECT_ROOT / "data_preparation" / "input"

FACETS = ("problem", "task", "method", "dataset", "contribution")

def main():
    struct_path = INTERMEDIATE_DIR / "structural_report.jsonl"
    ev_path = INTERMEDIATE_DIR / "evidence_candidates.jsonl"
    audit_path = INTERMEDIATE_DIR / "embedding_audit.jsonl"
    qwen_path = INTERMEDIATE_DIR / "qwen_audit.jsonl"
    silver_path = INPUT_DIR / "silver_facets.jsonl"

    print("--> Đang tải dữ liệu tổng hợp từ Bước 1, 2 và 3...")
    struct_by_pid = {row["paper_id"]: row for row in (json.loads(line) for line in open(struct_path, encoding="utf-8"))}
    ev_by_pid = {row["paper_id"]: row["evidence"] for row in (json.loads(line) for line in open(ev_path, encoding="utf-8"))}
    audit_by_pid = {row["paper_id"]: row for row in (json.loads(line) for line in open(audit_path, encoding="utf-8"))}
    qwen_by_pid = {row["paper_id"]: row["semantic_audit"] for row in (json.loads(line) for line in open(qwen_path, encoding="utf-8"))}
    silver_by_pid = {row["paper_id"]: row for row in (json.loads(line) for line in open(silver_path, encoding="utf-8"))}

    decisions = []
    stats = {
        "total_papers": len(struct_by_pid),
        "facet_status": {s: 0 for s in ["PRESENT", "NOT_MENTIONED", "SOURCE_MISSING", "TRUNCATED", "EXTRACTION_FAILED"]},
        "audit_decision": {d: 0 for d in ["AUTO_ACCEPT", "NEEDS_REVIEW", "REJECTED"]},
        "paper_status": {"VALIDATED": 0, "NEEDS_REVIEW": 0, "REJECTED": 0}
    }

    for pid in sorted(struct_by_pid.keys()):
        s_rep = struct_by_pid[pid]
        s_row = silver_by_pid.get(pid, {})
        ev_row = ev_by_pid.get(pid, {})
        a_row = audit_by_pid.get(pid, {})
        q_row = qwen_by_pid.get(pid, {})

        issues = s_rep.get("issues", [])
        sims = a_row.get("similarities", {})
        audit_flags = a_row.get("audit_flags", {})

        facet_status = {}
        audit_decision = {}
        qwen_proposals = {}

        has_reject = False
        has_review = False

        # Tình huống 6: Thiếu nguồn hoặc nguồn bị cắt
        if "PAPER_NOT_IN_CORPUS" in issues or "EMPTY_ABSTRACT" in issues:
            for f in FACETS:
                facet_status[f] = "SOURCE_MISSING"
                audit_decision[f] = "REJECTED"
                stats["facet_status"]["SOURCE_MISSING"] += 1
                stats["audit_decision"]["REJECTED"] += 1
            has_reject = True
        else:
            for f in FACETS:
                concepts = s_row.get(f, [])
                q_aud = q_row.get(f, {})
                q_supp = q_aud.get("support_status", "NOT_MENTIONED")
                q_issue = q_aud.get("detected_issues", "none")
                q_prop = q_aud.get("proposed_revision")
                flag = audit_flags.get(f, "EMPTY")

                if not concepts:
                    # Tình huống 5: Nguồn không đề cập facet -> Đặt NOT_MENTIONED
                    facet_status[f] = "NOT_MENTIONED"
                    audit_decision[f] = "AUTO_ACCEPT"
                    stats["facet_status"]["NOT_MENTIONED"] += 1
                    stats["audit_decision"]["AUTO_ACCEPT"] += 1
                else:
                    if q_supp == "UNSUPPORTED" or q_issue == "hallucination":
                        # Tình huống 4: Facet hoàn toàn không được hỗ trợ -> REJECTED
                        facet_status[f] = "PRESENT"
                        audit_decision[f] = "REJECTED"
                        stats["facet_status"]["PRESENT"] += 1
                        stats["audit_decision"]["REJECTED"] += 1
                        has_reject = True
                        qwen_proposals[f] = q_prop
                    elif q_supp == "PARTIALLY_SUPPORTED" or flag == "WEAK_EVIDENCE" or q_issue == "speculation":
                        # Tình huống 2 & 3: Diễn đạt chưa rõ hoặc có phần suy diễn -> NEEDS_REVIEW
                        facet_status[f] = "PRESENT"
                        audit_decision[f] = "NEEDS_REVIEW"
                        stats["facet_status"]["PRESENT"] += 1
                        stats["audit_decision"]["NEEDS_REVIEW"] += 1
                        has_review = True
                        qwen_proposals[f] = q_prop
                    elif q_issue == "truncated":
                        facet_status[f] = "TRUNCATED"
                        audit_decision[f] = "NEEDS_REVIEW"
                        stats["facet_status"]["TRUNCATED"] += 1
                        stats["audit_decision"]["NEEDS_REVIEW"] += 1
                        has_review = True
                    else:
                        # Tình huống 1: Facet đúng, đủ thông tin -> Giữ nguyên (AUTO_ACCEPT)
                        facet_status[f] = "PRESENT"
                        audit_decision[f] = "AUTO_ACCEPT"
                        stats["facet_status"]["PRESENT"] += 1
                        stats["audit_decision"]["AUTO_ACCEPT"] += 1

        if has_reject:
            p_status = "REJECTED" if all(audit_decision[f] == "REJECTED" for f in FACETS) else "NEEDS_REVIEW"
        elif has_review:
            p_status = "NEEDS_REVIEW"
        else:
            p_status = "VALIDATED"

        stats["paper_status"][p_status] += 1

        decisions.append({
            "paper_id": pid,
            "facet_status": facet_status,
            "audit_decision": audit_decision,
            "evidence": ev_row,
            "qwen_proposals": qwen_proposals,
            "paper_validation_status": p_status
        })

    out_path = INTERMEDIATE_DIR / "automated_decisions.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for r in decisions:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n==================== KẾT QUẢ AUTOMATED DECISION (BƯỚC 4) ====================")
    print(f"Tổng số bài báo: {stats['total_papers']}")
    print(f"  - Bài đạt chuẩn VALIDATED: {stats['paper_status']['VALIDATED']} ({stats['paper_status']['VALIDATED']/stats['total_papers']*100:.1f}%)")
    print(f"  - Bài cần Human Review (NEEDS_REVIEW): {stats['paper_status']['NEEDS_REVIEW']} ({stats['paper_status']['NEEDS_REVIEW']/stats['total_papers']*100:.1f}%)")
    print(f"  - Bài bị REJECTED: {stats['paper_status']['REJECTED']}")
    print(f"\nThống kê quyết định từng facet (21.050 lượt):")
    print(f"  - AUTO_ACCEPT : {stats['audit_decision']['AUTO_ACCEPT']:5d} ({stats['audit_decision']['AUTO_ACCEPT']/(stats['total_papers']*5)*100:.1f}%)")
    print(f"  - NEEDS_REVIEW: {stats['audit_decision']['NEEDS_REVIEW']:5d} ({stats['audit_decision']['NEEDS_REVIEW']/(stats['total_papers']*5)*100:.1f}%)")
    print(f"  - REJECTED    : {stats['audit_decision']['REJECTED']:5d} ({stats['audit_decision']['REJECTED']/(stats['total_papers']*5)*100:.1f}%)")
    print(f"\n-> Đã lưu danh sách quyết định tích hợp tại: {out_path}")

if __name__ == "__main__":
    main()
