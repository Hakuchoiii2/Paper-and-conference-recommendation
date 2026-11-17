"""09_evaluate_audit.py
Đánh giá chất lượng và hiệu chuẩn pipeline tự động dựa trên tập 400 bài Gold Facets (con người duyệt):
1. Chia 400 bài thành 70% Calibration (280 bài) và 30% Held-out Evaluation (120 bài).
2. Đo độ tương đồng ngữ nghĩa và tỷ lệ trùng khớp trạng thái (PRESENT / NOT_MENTIONED).
3. Đánh giá khả năng phát hiện lỗi của quy trình tự động so với chuẩn người duyệt.
Output:
- data_preparation/evaluation/gold_calibration.jsonl
- data_preparation/evaluation/gold_heldout.jsonl
- data_preparation/evaluation/audit_evaluation_report.json
"""

import json
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = PROJECT_ROOT / "data_preparation" / "input"
OUTPUT_DIR = PROJECT_ROOT / "data_preparation" / "output"
EVAL_DIR = PROJECT_ROOT / "data_preparation" / "evaluation"

FACETS = ("problem", "task", "method", "dataset", "contribution")

def normalize_text(text):
    return set(text.lower().replace(";", " ").split())

def main():
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    gold_path = INPUT_DIR / "gold_facets_400.jsonl"
    val_silver_path = OUTPUT_DIR / "validated_silver.jsonl"

    if not gold_path.exists() or not val_silver_path.exists():
        print("Error: Missing gold or validated_silver file!")
        return

    print("--> Đang tải dữ liệu Gold 400 bài và Validated Silver...")
    gold_records = [json.loads(line) for line in open(gold_path, encoding="utf-8")]
    val_silver_by_pid = {r["paper_id"]: r for r in (json.loads(line) for line in open(val_silver_path, encoding="utf-8"))}

    print(f"--> Đã nạp {len(gold_records)} bài Gold (Người duyệt).")

    # 1. Chia tập 70% Calibration (280 bài) và 30% Held-out (120 bài) cố định theo seed
    rng = random.Random(42)
    sorted_gold = sorted(gold_records, key=lambda x: x["paper_id"])
    shuffled_indices = list(range(len(sorted_gold)))
    rng.shuffle(shuffled_indices)

    split_point = int(len(sorted_gold) * 0.7)
    calib_indices = set(shuffled_indices[:split_point])
    
    calib_records = [sorted_gold[i] for i in range(len(sorted_gold)) if i in calib_indices]
    heldout_records = [sorted_gold[i] for i in range(len(sorted_gold)) if i not in calib_indices]

    # Lưu 2 tập
    with open(EVAL_DIR / "gold_calibration.jsonl", "w", encoding="utf-8") as f:
        for r in calib_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(EVAL_DIR / "gold_heldout.jsonl", "w", encoding="utf-8") as f:
        for r in heldout_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"--> Đã chia tập: {len(calib_records)} Calibration (70%) và {len(heldout_records)} Held-out Evaluation (30%).")

    # 2. Đánh giá trên tập Held-out (120 bài chưa từng thấy)
    evaluation_results = {
        "heldout_papers_count": len(heldout_records),
        "facet_metrics": {}
    }

    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_tn = 0

    print("\n==================== KẾT QUẢ ĐÁNH GIÁ TRÊN TẬP HELDOUT (30%) ====================")
    for f in FACETS:
        tp, fp, fn, tn = 0, 0, 0, 0
        jaccard_scores = []

        for g_row in heldout_records:
            pid = g_row["paper_id"]
            v_row = val_silver_by_pid.get(pid)
            if not v_row:
                continue

            gold_concepts = g_row.get("facets", {}).get(f, [])
            gold_present = bool(gold_concepts)

            val_status = v_row.get("facet_status", {}).get(f)
            val_present = (val_status == "PRESENT")

            if gold_present and val_present:
                tp += 1
                g_words = normalize_text(" ".join(gold_concepts))
                v_words = normalize_text(v_row.get("facets", {}).get(f, ""))
                if g_words or v_words:
                    jaccard = len(g_words & v_words) / len(g_words | v_words)
                    jaccard_scores.append(jaccard)
            elif not gold_present and val_present:
                fp += 1
            elif gold_present and not val_present:
                fn += 1
            else:
                tn += 1

        total_tp += tp
        total_fp += fp
        total_fn += fn
        total_tn += tn

        acc = (tp + tn) / len(heldout_records) if heldout_records else 0.0
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        avg_jaccard = sum(jaccard_scores) / len(jaccard_scores) if jaccard_scores else 0.0

        evaluation_results["facet_metrics"][f] = {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "concept_token_jaccard": round(avg_jaccard, 4),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn
        }

        print(f"Khía cạnh: {f.upper():12s} | Acc: {acc*100:5.1f}% | Prec: {prec*100:5.1f}% | Rec: {rec*100:5.1f}% | F1: {f1*100:5.1f}% | Jaccard: {avg_jaccard:.3f}")

    overall_acc = (total_tp + total_tn) / (len(heldout_records) * len(FACETS))
    overall_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    overall_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    overall_f1 = 2 * overall_prec * overall_rec / (overall_prec + overall_rec) if (overall_prec + overall_rec) > 0 else 0.0

    evaluation_results["overall"] = {
        "accuracy": round(overall_acc, 4),
        "precision": round(overall_prec, 4),
        "recall": round(overall_rec, 4),
        "f1_score": round(overall_f1, 4)
    }

    print("-" * 80)
    print(f"TOÀN CỤC (OVERALL): Accuracy: {overall_acc*100:.2f}% | Precision: {overall_prec*100:.2f}% | Recall: {overall_rec*100:.2f}% | F1: {overall_f1*100:.2f}%")
    print("=" * 80)

    report_path = EVAL_DIR / "audit_evaluation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(evaluation_results, f, indent=2, ensure_ascii=False)

    print(f"\n-> Báo cáo hiệu chuẩn chi tiết đã lưu tại: {report_path}")

if __name__ == "__main__":
    main()
