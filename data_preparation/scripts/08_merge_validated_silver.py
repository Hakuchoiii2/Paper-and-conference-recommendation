"""08_merge_validated_silver.py
Bước 6: Merge Validated Silver
Hợp nhất dữ liệu đã qua kiểm tra cấu trúc, alignment và semantic audit theo đúng Mục 2.5 & 3:
- Nguyên tắc vàng Mục 2.5: Qwen được đề xuất nhưng không tự ý ghi đè; chỉ nội dung được rule chấp nhận
  hoặc con người xác nhận (từ human_corrections.jsonl hoặc human_gold.jsonl) mới được vào Validated Silver.
- Facet REJECTED được tách riêng lưu vào rejected_facets.jsonl.
- Ghi rõ trạng thái (facet_status), quyết định (audit_decision), câu bằng chứng (evidence) và nguồn gốc (provenance).

Output:
- data_preparation/output/validated_silver.jsonl
- data_preparation/output/rejected_facets.jsonl
- data_preparation/output/data_quality_report.json
"""

import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERMEDIATE_DIR = PROJECT_ROOT / "data_preparation" / "intermediate"
OUTPUT_DIR = PROJECT_ROOT / "data_preparation" / "output"
INPUT_DIR = PROJECT_ROOT / "data_preparation" / "input"
HUMAN_DIR = PROJECT_ROOT / "data_preparation" / "human_review"

FACETS = ("problem", "task", "method", "dataset", "contribution")

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    silver_path = INPUT_DIR / "silver_facets.jsonl"
    decisions_path = INTERMEDIATE_DIR / "automated_decisions.jsonl"
    ev_path = INTERMEDIATE_DIR / "evidence_candidates.jsonl"
    gold_path = INPUT_DIR / "gold_facets_400.jsonl"
    human_corr_path = HUMAN_DIR / "human_corrections.jsonl"

    print("--> Đang tải dữ liệu để tiến hành Merge Validated Silver theo Mục 2.5...")
    silver_by_pid = {r["paper_id"]: r for r in (json.loads(line) for line in open(silver_path, encoding="utf-8"))}
    dec_by_pid = {r["paper_id"]: r for r in (json.loads(line) for line in open(decisions_path, encoding="utf-8"))}
    ev_by_pid = {r["paper_id"]: r["evidence"] for r in (json.loads(line) for line in open(ev_path, encoding="utf-8"))}
    gold_by_pid = {r["paper_id"]: r for r in (json.loads(line) for line in open(gold_path, encoding="utf-8"))} if gold_path.exists() else {}

    # Đọc sửa đổi thủ công từ con người nếu có
    human_corrections = {}
    if human_corr_path.exists():
        for line in open(human_corr_path, encoding="utf-8"):
            r = json.loads(line)
            if r.get("human_decision") in ("ACCEPT", "REJECT", "REVISE"):
                human_corrections[(r["paper_id"], r["facet"])] = r

    validated_records = []
    rejected_records = []

    stats = {
        "generated_at": datetime.now().isoformat(),
        "total_records": len(dec_by_pid),
        "validated_papers": 0,
        "needs_review_papers": 0,
        "rejected_papers": 0,
        "human_verified_papers": 0,
        "facet_coverage": {f: {"present": 0, "not_mentioned": 0, "evidence_grounded": 0, "rejected": 0} for f in FACETS}
    }

    for pid in sorted(dec_by_pid.keys()):
        dec_row = dec_by_pid[pid]
        s_row = silver_by_pid.get(pid, {})
        ev_row = dict(ev_by_pid.get(pid, {}))
        g_row = gold_by_pid.get(pid)

        f_status = dict(dec_row["facet_status"])
        a_dec = dict(dec_row["audit_decision"])
        paper_status = dec_row["paper_validation_status"]

        human_reviewed = False
        audit_model = "Qwen3-4B-Instruct"

        # Nếu bài thuộc tập 400 Gold đã được người thẩm định
        if g_row and g_row.get("review_status") == "reviewed":
            human_reviewed = True
            audit_model = "Human_Gold_Verified"

        final_facets = {}

        for f in FACETS:
            original_concepts = list(s_row.get(f, []))
            current_concepts = list(original_concepts)
            corr = human_corrections.get((pid, f))

            # 1. Nếu có sửa đổi của con người trong Bước 5
            if corr:
                human_reviewed = True
                h_decision = corr["human_decision"]
                if h_decision == "ACCEPT":
                    a_dec[f] = "AUTO_ACCEPT"
                    f_status[f] = "PRESENT"
                elif h_decision == "REJECT":
                    a_dec[f] = "REJECTED"
                    f_status[f] = "NOT_MENTIONED"
                    current_concepts = []
                elif h_decision == "REVISE":
                    a_dec[f] = "AUTO_ACCEPT"
                    f_status[f] = "PRESENT"
                    rev = corr.get("human_revised_facet")
                    current_concepts = [rev] if isinstance(rev, str) else rev

            # 2. Xử lý trường hợp REJECTED theo đúng Mục 2.5
            if a_dec[f] == "REJECTED":
                stats["facet_coverage"][f]["rejected"] += 1
                rejected_records.append({
                    "paper_id": pid,
                    "facet": f,
                    "rejected_concepts": original_concepts,
                    "reason": "Unsupported by source evidence (Qwen Semantic Audit / Low Alignment / Non-informative filler)"
                })
                # Theo Mục 2.5: Không dùng nội dung bị reject, chuyển thành NOT_MENTIONED
                final_facets[f] = ""
                f_status[f] = "NOT_MENTIONED"
                ev_row[f] = []
            else:
                final_facets[f] = "; ".join(current_concepts) if current_concepts else ""

            # Thống kê độ phủ
            if f_status[f] == "PRESENT":
                stats["facet_coverage"][f]["present"] += 1
                if ev_row.get(f):
                    stats["facet_coverage"][f]["evidence_grounded"] += 1
            else:
                stats["facet_coverage"][f]["not_mentioned"] += 1

        # Xác định trạng thái của toàn bộ paper:
        # Nếu mọi facet đều đã được duyệt chấp nhận (AUTO_ACCEPT) hoặc đã được con người xử lý (REJECT/REVISE)
        unresolved_facets = [f for f in FACETS if a_dec[f] == "NEEDS_REVIEW" and (pid, f) not in human_corrections]
        if not unresolved_facets:
            paper_status = "VALIDATED"
        else:
            paper_status = "NEEDS_REVIEW"

        if paper_status == "VALIDATED":
            stats["validated_papers"] += 1
        elif paper_status == "NEEDS_REVIEW":
            stats["needs_review_papers"] += 1
        else:
            stats["rejected_papers"] += 1

        if human_reviewed:
            stats["human_verified_papers"] += 1

        rec = {
            "paper_id": pid,
            "facets": final_facets,
            "facet_status": f_status,
            "audit_decision": a_dec,
            "evidence": ev_row,
            "paper_validation_status": paper_status,
            "provenance": {
                "source": "exp_a_silver",
                "embedding_model": "all-MiniLM-L6-v2",
                "audit_model": audit_model,
                "human_reviewed": human_reviewed,
                "review_version": "data_preparation_v1",
                "timestamp": stats["generated_at"]
            }
        }
        validated_records.append(rec)

    out_file = OUTPUT_DIR / "validated_silver.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for r in validated_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    rej_file = OUTPUT_DIR / "rejected_facets.jsonl"
    with open(rej_file, "w", encoding="utf-8") as f:
        for r in rejected_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    report_file = OUTPUT_DIR / "data_quality_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"\n==================== KẾT QUẢ MERGE VALIDATED SILVER (CHUẨN MỤC 2.5 & 3) ====================")
    print(f"Tổng số bài xuất xưởng: {len(validated_records)}")
    print(f"  - Bài VALIDATED (sạch & có căn cứ bằng chứng): {stats['validated_papers']} ({stats['validated_papers']/len(validated_records)*100:.1f}%)")
    print(f"  - Bài NEEDS_REVIEW (chờ kiểm duyệt): {stats['needs_review_papers']} ({stats['needs_review_papers']/len(validated_records)*100:.1f}%)")
    print(f"  - Bài được con người xác thực (Human Verified): {stats['human_verified_papers']} bài (tập Gold 400 bài)")
    print(f"  - Số facet bị REJECTED (tách riêng): {len(rejected_records)}")
    print("\nChi tiết độ phủ từng khía cạnh:")
    for f in FACETS:
        cov = stats["facet_coverage"][f]
        print(f"  - {f:12s}: {cov['present']:4d} PRESENT (Bằng chứng: {cov['evidence_grounded']:4d}) | {cov['not_mentioned']:4d} NOT_MENTIONED | {cov['rejected']:2d} REJECTED")
    print(f"\n-> Đã lưu tập dữ liệu chuẩn tại: {out_file}")
    print(f"-> Đã lưu danh sách facet bị loại tại: {rej_file}")
    print(f"-> Đã lưu báo cáo chất lượng tại: {report_file}")

if __name__ == "__main__":
    main()
