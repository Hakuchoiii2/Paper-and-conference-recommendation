"""
Module: baselines.py
Cài đặt 3 phương pháp chuẩn đồng bộ với Exp B (Method 1, Method 2, Method 3) và mốc Random:
  1. WholeTextKNNReranker (Method 1: Full-text Embedding).
  2. FlatFacetKNNReranker (Method 2: Equal-weight Facet & Method 3: Weighted Facet với
     tái chuẩn hóa mẫu số động theo Exp B hoặc Zero-Imputation đối chứng cho Exp C3).
  3. RandomReranker (Mốc sàn ngẫu nhiên).
"""

import random
from typing import Any, Dict, List, Optional, Tuple
from .feature_loader import FacetFeatureStore, cosine_similarity
from .ranking import observed, validate_weights, rank_neighbors, aggregate_venue_scores

ALL_FACETS = ("problem", "task", "method", "dataset", "contribution")


class WholeTextKNNReranker:
    """
    Method 1: Full-text Embedding Reranker.
    Tính Cosine trên chuỗi toàn văn (Title + Abstract) giữa bài test và bài train.
    """

    def __init__(
        self,
        feature_store: FacetFeatureStore,
        train_papers: List[Dict],
        k: int = 10,
        aggregation_config: Optional[Dict[str, Any]] = None,
    ):
        self.feature_store = feature_store
        self.k = k
        self.aggregation_config = aggregation_config or {"aggregation": "sum_knn", "k": k}
        self.train_pids = [p["paper_id"] for p in train_papers]
        self.train_venues = [p["conference_id"] for p in train_papers]

    def predict(
        self, q_pid: str, candidate_venues: List[str]
    ) -> List[Tuple[str, float]]:
        q_vec = self.feature_store.get_vectors(q_pid).get("whole_text")

        scores = []
        for p_pid in self.train_pids:
            p_vec = self.feature_store.get_vectors(p_pid).get("whole_text")
            scores.append(cosine_similarity(q_vec, p_vec))

        cfg = {**self.aggregation_config, "k": self.k}
        return aggregate_venue_scores(
            self.train_pids, self.train_venues, scores, candidate_venues, cfg
        )


class FlatFacetKNNReranker:
    """
    Method 2 (Equal-weight Facet) & Method 3 (Weighted Facet) — Đồng bộ 100% Exp B.
    - missing_policy="renormalize": Chia cho tổng trọng số của các facet cùng có mặt V(q, p),
      và loại bỏ các cặp có denominator == 0 (khớp valid_pairs = denominator > 0 của Exp B).
    - missing_policy="zero_impute": Giữ mẫu số = 1.0, gán cosine = 0 cho facet khuyết (Exp C3).
    """

    def __init__(
        self,
        feature_store: FacetFeatureStore,
        train_papers: List[Dict],
        k: int = 10,
        weights: Optional[Dict[str, float]] = None,
        missing_policy: str = "renormalize",
        aggregation_config: Optional[Dict[str, Any]] = None,
    ):
        if missing_policy not in ("renormalize", "zero_impute"):
            raise ValueError(f"Unsupported missing_policy: {missing_policy}")
        self.feature_store = feature_store
        self.k = k
        self.weights = validate_weights(
            weights if weights is not None else dict.fromkeys(ALL_FACETS, 0.2),
            ALL_FACETS,
        )
        self.missing_policy = missing_policy
        self.aggregation_config = aggregation_config or {"aggregation": "sum_knn", "k": k}
        self.train_pids = [p["paper_id"] for p in train_papers]
        self.train_venues = [p["conference_id"] for p in train_papers]

    def compute_flat_similarity_with_validity(self, q_pid: str, p_pid: str) -> Tuple[float, bool]:
        q_vecs = self.feature_store.get_vectors(q_pid)
        p_vecs = self.feature_store.get_vectors(p_pid)

        numerator = 0.0
        denominator = 0.0
        for f in ALL_FACETS:
            qv = q_vecs.get(f)
            pv = p_vecs.get(f)
            if observed(qv) and observed(pv):
                if isinstance(qv, dict) and not qv:
                    continue
                if isinstance(pv, dict) and not pv:
                    continue
                numerator += self.weights[f] * cosine_similarity(qv, pv)
                denominator += self.weights[f]

        if self.missing_policy == "zero_impute":
            return numerator, True
        if denominator > 0.0:
            return numerator / denominator, True
        return float("-inf"), False

    def compute_flat_similarity(self, q_pid: str, p_pid: str) -> float:
        score, valid = self.compute_flat_similarity_with_validity(q_pid, p_pid)
        return score if valid else 0.0

    def predict(
        self, q_pid: str, candidate_venues: List[str]
    ) -> List[Tuple[str, float]]:
        scores = []
        valid_mask = []
        for p_pid in self.train_pids:
            sim, valid = self.compute_flat_similarity_with_validity(q_pid, p_pid)
            scores.append(sim)
            valid_mask.append(valid)

        cfg = {**self.aggregation_config, "k": self.k}
        return aggregate_venue_scores(
            self.train_pids,
            self.train_venues,
            scores,
            candidate_venues,
            cfg,
            valid_mask=valid_mask,
        )


class RandomReranker:
    """Baseline sàn: Xếp hạng ngẫu nhiên."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def predict(
        self, q_pid: str, candidate_venues: List[str]
    ) -> List[Tuple[str, float]]:
        shuffled = list(candidate_venues)
        self.rng.shuffle(shuffled)
        return [(v, 1.0 / (i + 1)) for i, v in enumerate(shuffled)]


# Aliases tương thích ngược
WholeTextKNNMatcher = WholeTextKNNReranker
FlatFacetKNNMatcher = FlatFacetKNNReranker
RandomMatcher = RandomReranker
