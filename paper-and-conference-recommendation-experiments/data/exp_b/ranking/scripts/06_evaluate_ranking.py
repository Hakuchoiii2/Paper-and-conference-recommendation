"""06_evaluate_ranking.py
Bước 6: Đánh giá chất lượng Ranking bằng Human Qrels (Mục 4.4).
- So sánh thứ tự xếp hạng của 3 phương pháp (Full-text, Equal-weight, Weighted) với Human Qrels (grade 0-3).
- Thang điểm Human Grade:
    0: Không liên quan
    1: Có liên quan nhẹ, giá trị sử dụng hạn chế
    2: Có liên quan đáng kể
    3: Rất liên quan, có giá trị tham khảo trực tiếp
- Các chỉ số đánh giá (Information Retrieval Metrics):
    * nDCG@10 (Metric chính - theo Mục 4.4)
    * nDCG@5
    * P@5, P@10 (Tỷ lệ bài relevant grade >= 2 trong Top-K)
    * MRR (Vị trí bài relevant grade >= 2 đầu tiên)
    * Recall@10, Recall@20 (Tỷ lệ tìm được các bài relevant)
    * Judged Coverage@10: Tỷ lệ các bài trong Top-10 đã được con người chấm nhãn (không tự ý gán unjudged = 0).
- Báo cáo phân tách riêng cho:
    * DEV (15 Queries): Dùng để kiểm tra và lựa chọn cấu hình trọng số.
    * TEST (35 Queries): Dùng để báo cáo kết quả cuối cùng đúng 1 lần.

Output:
- ranking/reports/ranking_metrics.json
- ranking/reports/ranking_comparison.csv
"""

import json
import math
import argparse
import csv
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RANKING_DIR = PROJECT_ROOT / "ranking"
CONFIG_PATH = RANKING_DIR / "config" / "ranking_config.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

REPO_ROOT = PROJECT_ROOT.parents[1]

def resolve_path(p_str):
    p = Path(p_str)
    if p.is_absolute():
        return p
    if (REPO_ROOT / p).exists():
        return REPO_ROOT / p
    return PROJECT_ROOT / p

def compute_dcg(gains, k):
    """Tính DCG@K với gain lũy thừa chuẩn TREC: (2^g - 1) / log2(i + 1)."""
    dcg = 0.0
    for i in range(min(k, len(gains))):
        grade = gains[i]
        dcg += (2.0 ** grade - 1.0) / math.log2(i + 2)
    return dcg

def compute_ndcg(retrieved_candidates, qrel_dict, k):
    """Tính nDCG@K cho 1 query."""
    # Lấy grade cho các bài được retrieved (unjudged được tính là 0 trong evaluation tạm thời, kèm ghi nhận unjudged_count)
    gains = []
    unjudged_count = 0
    for cand in retrieved_candidates[:k]:
        cid = cand["candidate_id"]
        if cid in qrel_dict:
            gains.append(qrel_dict[cid])
        else:
            gains.append(0)
            unjudged_count += 1

    actual_dcg = compute_dcg(gains, k)

    # Tính IDCG@K từ toàn bộ qrel_dict của query
    all_positive_grades = sorted(qrel_dict.values(), reverse=True)
    ideal_dcg = compute_dcg(all_positive_grades, k)

    ndcg = (actual_dcg / ideal_dcg) if ideal_dcg > 0 else 0.0
    coverage = (k - unjudged_count) / k if k > 0 else 1.0
    return ndcg, coverage

def compute_precision_recall_mrr(retrieved_candidates, qrel_dict, k, rel_threshold=2):
    """Tính Precision@K, Recall@K và Reciprocal Rank cho 1 query."""
    retrieved_k = retrieved_candidates[:k]
    rel_count = 0
    first_rel_rank = 0

    for i, cand in enumerate(retrieved_k, start=1):
        cid = cand["candidate_id"]
        grade = qrel_dict.get(cid, 0)
        if grade >= rel_threshold:
            rel_count += 1
            if first_rel_rank == 0:
                first_rel_rank = i

    precision = rel_count / k if k > 0 else 0.0

    # Tổng số bài relevant có trong qrels
    total_relevant = sum(1 for g in qrel_dict.values() if g >= rel_threshold)
    recall = (rel_count / total_relevant) if total_relevant > 0 else 0.0

    # Tìm first relevant rank trên toàn bộ danh sách nếu chưa thấy trong top K
    if first_rel_rank == 0:
        for i, cand in enumerate(retrieved_candidates, start=1):
            cid = cand["candidate_id"]
            if qrel_dict.get(cid, 0) >= rel_threshold:
                first_rel_rank = i
                break

    mrr = (1.0 / first_rel_rank) if first_rel_rank > 0 else 0.0
    return precision, recall, mrr

def evaluate_method_for_split(ranked_records_by_qid, qrels_by_qid, query_ids, rel_threshold=2):
    """Đánh giá 1 phương pháp trên 1 tập queries (DEV hoặc TEST)."""
    if not query_ids:
        return {}

    metrics_acc = defaultdict(list)

    for qid in query_ids:
        ranked = ranked_records_by_qid.get(qid, [])
        qrel = qrels_by_qid.get(qid, {})

        if not qrel:
            continue

        ndcg_5, cov_5 = compute_ndcg(ranked, qrel, k=5)
        ndcg_10, cov_10 = compute_ndcg(ranked, qrel, k=10)
        p_5, _, _ = compute_precision_recall_mrr(ranked, qrel, k=5, rel_threshold=rel_threshold)
        p_10, rec_10, mrr = compute_precision_recall_mrr(ranked, qrel, k=10, rel_threshold=rel_threshold)
        _, rec_20, _ = compute_precision_recall_mrr(ranked, qrel, k=20, rel_threshold=rel_threshold)

        metrics_acc["nDCG@5"].append(ndcg_5)
        metrics_acc["nDCG@10"].append(ndcg_10)
        metrics_acc["P@5"].append(p_5)
        metrics_acc["P@10"].append(p_10)
        metrics_acc["Recall@10"].append(rec_10)
        metrics_acc["Recall@20"].append(rec_20)
        metrics_acc["MRR"].append(mrr)
        metrics_acc["Judged_Coverage@10"].append(cov_10)

    # Tính trung bình cộng macro
    avg_metrics = {}
    evaluated_queries_count = len(metrics_acc["nDCG@10"])
    avg_metrics["evaluated_queries"] = evaluated_queries_count

    for metric_name, values in metrics_acc.items():
        avg_metrics[metric_name] = round(sum(values) / len(values), 4) if values else 0.0

    return avg_metrics

def main():
    parser = argparse.ArgumentParser(description="Bước 6: Đánh giá xếp hạng Ranking với Human Qrels")
    parser.add_argument("--threshold", type=int, default=2, help="Ngưỡng grade coi là relevant (mặc định: 2 - có liên quan đáng kể)")
    args = parser.parse_args()

    config = load_config()
    paths = config.get("paths", {})

    print("="*75)
    print("BƯỚC 6: ĐÁNH GIÁ CHẤT LƯỢNG RANKING BẰNG HUMAN QRELS (IR METRICS)")
    print("="*75)

    # Tải Human Qrels
    qrels_path = resolve_path(paths.get("human_qrels", "ranking/input/human_qrels.jsonl"))
    if not qrels_path.exists():
        qrels_path = RANKING_DIR / "input" / "human_qrels.template.jsonl"
        print(f"[*] Chưa có human_qrels.jsonl chính thức, đang dùng template {qrels_path.name} để kiểm tra quy trình.")

    qrels_by_qid = defaultdict(dict)
    if qrels_path.exists():
        with open(qrels_path, "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                qrels_by_qid[r["query_id"]][r["candidate_id"]] = int(r["grade"])
        print(f"[+] Đã nạp nhãn Human Qrels: {len(qrels_by_qid)} queries có đánh giá.")
    else:
        print("[!] Không tìm thấy file Human Qrels để đánh giá.")
        return

    # Tải Query Split
    split_path = resolve_path(paths.get("query_split", "ranking/input/query_split.json"))
    if not split_path.exists():
        split_path = RANKING_DIR / "input" / "query_split.template.json"

    dev_queries, test_queries = [], []
    if split_path.exists():
        with open(split_path, "r", encoding="utf-8") as f:
            split_data = json.load(f)
            dev_queries = split_data.get("dev", [])
            test_queries = split_data.get("test", [])

    # Danh sách 3 phương pháp cần đánh giá
    methods = [
        ("Method 1: Full-text Embedding", resolve_path(paths.get("output_fulltext", "ranking/output/fulltext_ranking.jsonl"))),
        ("Method 2: Equal-weight Facet", resolve_path(paths.get("output_equal_weight", "ranking/output/equal_weight_ranking.jsonl"))),
        ("Method 3: Weighted Facet (0.4 Problem)", resolve_path(paths.get("output_weighted", "ranking/output/weighted_ranking.jsonl")))
    ]

    all_results = {
        "evaluation_config": {
            "primary_metric": "nDCG@10",
            "binary_relevance_threshold": args.threshold,
            "dev_queries_count": len(dev_queries),
            "test_queries_count": len(test_queries)
        },
        "dev_results": {},
        "test_results": {}
    }

    comparison_rows = []

    for method_name, file_path in methods:
        if not file_path.exists():
            print(f"[!] Chưa có kết quả của {method_name} tại {file_path.name}")
            continue

        print(f"\n--> Đang đánh giá {method_name}...")
        ranked_by_qid = {}
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                ranked_by_qid[r["query_id"]] = r["ranking"]

        dev_metrics = evaluate_method_for_split(ranked_by_qid, qrels_by_qid, dev_queries, rel_threshold=args.threshold)
        test_metrics = evaluate_method_for_split(ranked_by_qid, qrels_by_qid, test_queries, rel_threshold=args.threshold)

        all_results["dev_results"][method_name] = dev_metrics
        all_results["test_results"][method_name] = test_metrics

        print(f"    [DEV  (15 Queries)] nDCG@10: {dev_metrics.get('nDCG@10', 0):.4f} | P@10: {dev_metrics.get('P@10', 0):.4f} | MRR: {dev_metrics.get('MRR', 0):.4f} | Coverage@10: {dev_metrics.get('Judged_Coverage@10', 0)*100:.1f}%")
        print(f"    [TEST (35 Queries)] nDCG@10: {test_metrics.get('nDCG@10', 0):.4f} | P@10: {test_metrics.get('P@10', 0):.4f} | MRR: {test_metrics.get('MRR', 0):.4f} | Coverage@10: {test_metrics.get('Judged_Coverage@10', 0)*100:.1f}%")

        # Lưu vào bảng CSV
        comparison_rows.append({
            "Method": method_name,
            "Split": "DEV (15)",
            "nDCG@10 (Primary)": dev_metrics.get("nDCG@10", 0),
            "nDCG@5": dev_metrics.get("nDCG@5", 0),
            "P@10": dev_metrics.get("P@10", 0),
            "Recall@10": dev_metrics.get("Recall@10", 0),
            "MRR": dev_metrics.get("MRR", 0),
            "Judged_Coverage@10": dev_metrics.get("Judged_Coverage@10", 0)
        })
        comparison_rows.append({
            "Method": method_name,
            "Split": "TEST (35)",
            "nDCG@10 (Primary)": test_metrics.get("nDCG@10", 0),
            "nDCG@5": test_metrics.get("nDCG@5", 0),
            "P@10": test_metrics.get("P@10", 0),
            "Recall@10": test_metrics.get("Recall@10", 0),
            "MRR": test_metrics.get("MRR", 0),
            "Judged_Coverage@10": test_metrics.get("Judged_Coverage@10", 0)
        })

    # Lưu kết quả JSON và CSV
    rep_metrics_path = resolve_path(paths.get("report_metrics", "ranking/reports/ranking_metrics.json"))
    rep_csv_path = resolve_path(paths.get("report_comparison", "ranking/reports/ranking_comparison.csv"))
    rep_metrics_path.parent.mkdir(parents=True, exist_ok=True)

    with open(rep_metrics_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    if comparison_rows:
        with open(rep_csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(comparison_rows[0].keys()))
            writer.writeheader()
            writer.writerows(comparison_rows)

    print(f"\n[+] Đã lưu báo cáo Metric chi tiết tại: {rep_metrics_path}")
    print(f"[+] Đã lưu bảng đối chiếu CSV tại: {rep_csv_path}")
    print("--> Hoàn tất Bước 6.")

if __name__ == "__main__":
    main()
