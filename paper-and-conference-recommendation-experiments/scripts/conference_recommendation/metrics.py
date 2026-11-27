"""
Module: metrics.py
Thư viện chuẩn mực tính toán các chỉ số đánh giá Hệ thống Khuyến nghị Hội nghị:
  - Hit@1, Hit@3, Hit@5 (Micro & Macro)
  - MRR (Mean Reciprocal Rank)
  - Per-Venue Breakdown
  - Head / Mid / Tail Tier Breakdown (dựa trên N_v của tập Train)
  - Discipline Hit@1 & Cross-Discipline Error Rate (ánh xạ 30 hội nghị -> 4 cụm ngành)
  - Per-Query Arrays phục vụ kiểm định thống kê bắt cặp (McNemar, Permutation, Bootstrap)
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple


# Ánh xạ đầy đủ 30 hội nghị trong temporal_2015_2016_2019_clean/conference_catalog.jsonl về 4 cụm lĩnh vực khoa học
VENUE_DISCIPLINE_MAP: Dict[str, str] = {
    # 1. NLP / Computational Linguistics (11 venues)
    "CONF_ACL": "NLP",
    "CONF_EMNLP": "NLP",
    "CONF_NAACL": "NLP",
    "CONF_COLING": "NLP",
    "CONF_EACL": "NLP",
    "CONF_CONLL": "NLP",
    "CONF_LREC": "NLP",
    "CONF_IJCNLP": "NLP",
    "CONF_RANLP": "NLP",
    "CONF_SIGDIAL": "NLP",
    "CONF_ACL_STARSEM": "NLP",
    # 2. AI / Machine Learning / Robotics (4 venues)
    "CONF_ICML": "AI_ML",
    "CONF_ICLR": "AI_ML",
    "CONF_ICORE_1123": "AI_ML",  # ICMLC: Machine Learning and Cybernetics
    "CONF_ICORE_792": "AI_ML",   # IROS: Intelligent Robots and Systems
    # 3. IR / Data Mining / Knowledge / Databases (8 venues)
    "CONF_KDD": "IR_DM_DB",
    "CONF_SIGIR": "IR_DM_DB",
    "CONF_CIKM": "IR_DM_DB",
    "CONF_WSDM": "IR_DM_DB",
    "CONF_SIGMOD": "IR_DM_DB",
    "CONF_ICORE_642": "IR_DM_DB",   # ICDM: IEEE International Conference on Data Mining
    "CONF_ICORE_2311": "IR_DM_DB",  # ASONAM: Social Networks Analysis and Mining
    "CONF_ICORE_2268": "IR_DM_DB",  # LAK: Learning Analytics and Knowledge
    # 4. Vision / Multimedia / Speech / HCI (7 venues)
    "CONF_CVPR": "CV_MM_SPEECH_HCI",
    "CONF_ICPR": "CV_MM_SPEECH_HCI",
    "CONF_ACM_MM": "CV_MM_SPEECH_HCI",
    "CONF_ICASSP": "CV_MM_SPEECH_HCI",
    "CONF_CHI": "CV_MM_SPEECH_HCI",
    "CONF_ICORE_664": "CV_MM_SPEECH_HCI",  # ICME: Multimedia and Expo
    "CONF_ICORE_13": "CV_MM_SPEECH_HCI",   # CSCW: Computer Supported Cooperative Work
}


def classify_venue_tier(train_count: int) -> str:
    """Phân tầng hội nghị theo quy mô tập Train N_v: Head (>=20), Mid (5..19), Tail (<=4)."""
    if train_count >= 20:
        return "head"
    if train_count >= 5:
        return "mid"
    return "tail"


def hit_at_k(ranked_predictions: List[Tuple[str, float]], true_venue: str, k: int) -> float:
    """Trả về 1.0 nếu hội nghị thực tế nằm trong Top-k gợi ý, ngược lại trả về 0.0."""
    top_venues = [v for v, _ in ranked_predictions[:k]]
    return 1.0 if true_venue in top_venues else 0.0


def true_venue_rank(ranked_predictions: List[Tuple[str, float]], true_venue: str) -> int:
    """Trả về thứ hạng (1-based) của hội nghị thực tế, hoặc len(ranked_predictions) + 1 nếu không thấy."""
    for rank, (venue, _) in enumerate(ranked_predictions, 1):
        if venue == true_venue:
            return rank
    return len(ranked_predictions) + 1


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
    top_k_list: Sequence[int] = (1, 3, 5),
) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]]]:
    """
    Tính toán toàn diện các chỉ số Micro và Macro trên tập đánh giá.

    Returns:
        (summary_metrics, per_venue_metrics)
    """
    detailed = evaluate_predictions_detailed(
        predictions=predictions,
        ground_truth=ground_truth,
        candidate_venues=candidate_venues,
        train_venue_counts=None,
        top_k_list=top_k_list,
    )
    return detailed["metrics"], detailed["per_venue"]


def evaluate_predictions_detailed(
    predictions: Dict[str, List[Tuple[str, float]]],
    ground_truth: Dict[str, str],
    candidate_venues: List[str],
    train_venue_counts: Optional[Dict[str, int]] = None,
    top_k_list: Sequence[int] = (1, 3, 5),
    discipline_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Tính toán đầy đủ các chỉ số Micro, Macro, phân tầng Head/Mid/Tail,
    Discipline Hit@1 / Cross-Discipline Error Rate và mảng kết quả từng truy vấn.
    """
    pids = sorted(pid for pid in predictions if pid in ground_truth and ground_truth[pid])
    total_test = len(pids)
    if total_test == 0:
        return {
            "metrics": {},
            "per_venue": {},
            "tier_metrics": {},
            "discipline_confusion": {},
            "per_query": {},
        }

    disc_map = VENUE_DISCIPLINE_MAP if discipline_map is None else discipline_map
    venue_hits = {k: defaultdict(list) for k in top_k_list}
    venue_mrrs = defaultdict(list)

    all_hits = {k: [] for k in top_k_list}
    all_mrrs: List[float] = []
    all_ranks: List[int] = []

    disc_hits: List[float] = []
    disc_confusion: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    top1_errors = 0
    cross_disc_errors_given_wrong = 0

    for pid in pids:
        ranked_list = predictions[pid]
        true_venue = ground_truth[pid]

        rr = reciprocal_rank(ranked_list, true_venue)
        rank = true_venue_rank(ranked_list, true_venue)
        all_mrrs.append(rr)
        all_ranks.append(rank)
        venue_mrrs[true_venue].append(rr)

        for k in top_k_list:
            hit = hit_at_k(ranked_list, true_venue, k)
            all_hits[k].append(hit)
            venue_hits[k][true_venue].append(hit)

        if ranked_list:
            pred_top1 = ranked_list[0][0]
            true_disc = disc_map.get(true_venue)
            pred_disc = disc_map.get(pred_top1)
            if true_disc is not None and pred_disc is not None:
                is_same_disc = 1.0 if true_disc == pred_disc else 0.0
                disc_hits.append(is_same_disc)
                disc_confusion[true_disc][pred_disc] += 1
                if pred_top1 != true_venue:
                    top1_errors += 1
                    if true_disc != pred_disc:
                        cross_disc_errors_given_wrong += 1

    # 1. Micro Metrics
    summary: Dict[str, Any] = {
        "total_test_papers": total_test,
        "mrr": sum(all_mrrs) / total_test,
    }
    for k in top_k_list:
        summary[f"hit@{k}"] = sum(all_hits[k]) / total_test

    # 2. Macro Metrics (trung bình đều trên các hội nghị có mẫu Test)
    active_venues = [v for v in candidate_venues if len(venue_mrrs[v]) > 0]
    num_active = len(active_venues)
    summary["active_venues_count"] = num_active

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

    # 3. Discipline Metrics
    if disc_hits:
        disc_hit1 = sum(disc_hits) / len(disc_hits)
        summary["discipline_hit@1"] = disc_hit1
        summary["cross_discipline_error_rate"] = 1.0 - disc_hit1
        summary["cross_discipline_share_of_top1_errors"] = (
            cross_disc_errors_given_wrong / top1_errors if top1_errors > 0 else 0.0
        )

    # 4. Per-venue breakdown
    per_venue: Dict[str, Dict[str, float]] = {}
    for v in candidate_venues:
        count = len(venue_mrrs[v])
        if count == 0:
            continue
        v_data: Dict[str, float] = {"test_count": count, "mrr": sum(venue_mrrs[v]) / count}
        for k in top_k_list:
            v_data[f"hit@{k}"] = sum(venue_hits[k][v]) / count
        per_venue[v] = v_data

    # 5. Tier breakdown (Head / Mid / Tail) based on Train venue counts
    tier_metrics: Dict[str, Dict[str, Any]] = {}
    if train_venue_counts is not None:
        tiers: Dict[str, List[str]] = {"head": [], "mid": [], "tail": []}
        for v in candidate_venues:
            tiers[classify_venue_tier(train_venue_counts.get(v, 0))].append(v)

        for tier_name, tier_venues in tiers.items():
            tier_pids = [pid for pid in pids if ground_truth[pid] in tier_venues]
            t_active = [v for v in tier_venues if len(venue_mrrs[v]) > 0]
            if not tier_pids:
                tier_metrics[tier_name] = {
                    "venue_count_total": len(tier_venues),
                    "venue_count_active": 0,
                    "test_count": 0,
                    "hit@1": 0.0,
                    "hit@3": 0.0,
                    "hit@5": 0.0,
                    "mrr": 0.0,
                    "macro_hit@3": 0.0,
                    "macro_mrr": 0.0,
                }
                continue
            idx_map = {pid: i for i, pid in enumerate(pids)}
            t_indices = [idx_map[pid] for pid in tier_pids]
            t_data: Dict[str, Any] = {
                "venue_count_total": len(tier_venues),
                "venue_count_active": len(t_active),
                "test_count": len(tier_pids),
                "mrr": sum(all_mrrs[i] for i in t_indices) / len(t_indices),
                "macro_mrr": (
                    sum(sum(venue_mrrs[v]) / len(venue_mrrs[v]) for v in t_active) / len(t_active)
                    if t_active else 0.0
                ),
            }
            for k in top_k_list:
                t_data[f"hit@{k}"] = sum(all_hits[k][i] for i in t_indices) / len(t_indices)
                t_data[f"macro_hit@{k}"] = (
                    sum(sum(venue_hits[k][v]) / len(venue_hits[k][v]) for v in t_active) / len(t_active)
                    if t_active else 0.0
                )
            tier_metrics[tier_name] = t_data

        if "tail" in tier_metrics:
            summary["tail_hit@3"] = tier_metrics["tail"]["hit@3"]
            summary["tail_mrr"] = tier_metrics["tail"]["mrr"]

    per_query = {
        "paper_ids": pids,
        "true_rank": all_ranks,
        "rr": all_mrrs,
        **{f"hit@{k}": all_hits[k] for k in top_k_list},
    }

    return {
        "metrics": summary,
        "per_venue": per_venue,
        "tier_metrics": tier_metrics,
        "discipline_confusion": {k: dict(v) for k, v in disc_confusion.items()},
        "per_query": per_query,
    }
