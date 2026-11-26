"""
Module: metrics.py
Thư viện chuẩn mực tính toán các chỉ số đánh giá Hệ thống Khuyến nghị Hội nghị:
  - Hit@1, Hit@3, Hit@5 (Micro & Macro)
  - MRR (Mean Reciprocal Rank)
  - Bảng thống kê chi tiết theo từng hội nghị (Per-Venue Breakdown)
"""

from collections import defaultdict
from typing import Dict, List, Tuple


def hit_at_k(ranked_predictions: List[Tuple[str, float]], true_venue: str, k: int) -> float:
    """Trả về 1.0 nếu hội nghị thực tế nằm trong Top-k gợi ý, ngược lại trả về 0.0."""
    top_venues = [v for v, _ in ranked_predictions[:k]]
    return 1.0 if true_venue in top_venues else 0.0


def reciprocal_rank(ranked_predictions: List[Tuple[str, float]], true_venue: str) -> float:
    """Tính Reciprocal Rank = 1 / (vị trí_đúng). Nếu không tìm thấy, trả về 0.0."""
    for rank, (venue, _) in enumerate(ranked_predictions, 1):
        if venue == true_venue:
            return 1.0 / rank
    return 0.0


def evaluate_predictions(
    predictions: Dict[str, List[Tuple[str, float]]],
    ground_truth: Dict[str, str],
    candidate_venues: List[str],
    top_k_list: List[int] = (1, 3, 5),
) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]]]:
    """
    Tính toán toàn diện các chỉ số Micro và Macro trên tập Test.

    Args:
        predictions: Dict[paper_id -> [(venue, score), ...]]
        ground_truth: Dict[paper_id -> true_conference_id]
        candidate_venues: Danh mục 30 hội nghị hợp lệ
        top_k_list: Danh sách các ngưỡng K cần đo

    Returns:
        (summary_metrics, per_venue_metrics)
    """
    total_test = len(predictions)
    if total_test == 0:
        return {}, {}

    # Lưu trữ kết quả từng bài theo từng hội nghị
    venue_hits = {k: defaultdict(list) for k in top_k_list}
    venue_mrrs = defaultdict(list)

    all_hits = {k: [] for k in top_k_list}
    all_mrrs = []

    for pid, ranked_list in predictions.items():
        true_venue = ground_truth.get(pid)
        if not true_venue:
            continue

        rr = reciprocal_rank(ranked_list, true_venue)
        all_mrrs.append(rr)
        venue_mrrs[true_venue].append(rr)

        for k in top_k_list:
            hit = hit_at_k(ranked_list, true_venue, k)
            all_hits[k].append(hit)
            venue_hits[k][true_venue].append(hit)

    # 1. Tính toán Micro Metrics (Tính bình quân trên toàn bộ 186 bài test)
    summary = {
        "total_test_papers": total_test,
        "mrr": sum(all_mrrs) / len(all_mrrs) if all_mrrs else 0.0,
    }
    for k in top_k_list:
        summary[f"hit@{k}"] = sum(all_hits[k]) / len(all_hits[k]) if all_hits[k] else 0.0

    # 2. Tính toán Macro Metrics (Bình quân giữa các hội nghị, chống thiên lệch NLP)
    active_venues = [v for v in candidate_venues if len(venue_mrrs[v]) > 0]
    num_active = len(active_venues)

    if num_active > 0:
        summary["macro_mrr"] = sum(
            sum(venue_mrrs[v]) / len(venue_mrrs[v]) for v in active_venues
        ) / num_active
        for k in top_k_list:
            summary[f"macro_hit@{k}"] = sum(
                sum(venue_hits[k][v]) / len(venue_hits[k][v]) for v in active_venues
            ) / num_active
    else:
        summary["macro_mrr"] = 0.0
        for k in top_k_list:
            summary[f"macro_hit@{k}"] = 0.0

    # 3. Thống kê chi tiết từng hội nghị
    per_venue = {}
    for v in candidate_venues:
        count = len(venue_mrrs[v])
        if count == 0:
            continue
        v_mrr = sum(venue_mrrs[v]) / count
        v_data = {"test_count": count, "mrr": v_mrr}
        for k in top_k_list:
            v_data[f"hit@{k}"] = sum(venue_hits[k][v]) / count
        per_venue[v] = v_data

    return summary, per_venue
