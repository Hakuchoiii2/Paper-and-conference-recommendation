"""
Module: baselines.py
Cài đặt các mô hình đối chứng (Baselines) để chứng minh tính vượt trội
của phương pháp Gated 5-Facet k-NN Reranker:
  1. WholeTextKNNReranker: Dùng toàn văn Title + Abstract (không chia facet, không cổng).
  2. FlatFacetKNNReranker: Dùng 5 facets nhưng cộng phẳng (không có Cổng Ngữ Cảnh Problem).
  3. RandomReranker: Xếp hạng ngẫu nhiên làm mốc sàn đối chứng.
"""

import random
from typing import Any, Dict, List, Optional, Tuple
from .feature_loader import FacetFeatureStore, cosine_similarity

ALL_FACETS = ("problem", "task", "method", "dataset", "contribution")


class WholeTextKNNReranker:
    """
    Baseline 1: Whole-Text k-NN Reranker.
    Tính Cosine trên chuỗi toàn văn (Title + Abstract) giữa bài test và bài train.
    """

    def __init__(
        self,
        feature_store: FacetFeatureStore,
        train_papers: List[Dict],
        k: int = 10,
    ):
        self.feature_store = feature_store
        self.k = k
        self.train_pids = [p["paper_id"] for p in train_papers]
        self.train_venues = [p["conference_id"] for p in train_papers]

    def predict(
        self, q_pid: str, candidate_venues: List[str]
    ) -> List[Tuple[str, float]]:
        q_vec = self.feature_store.get_vectors(q_pid).get("whole_text")

        scores = []
        for p_pid, venue in zip(self.train_pids, self.train_venues):
            p_vec = self.feature_store.get_vectors(p_pid).get("whole_text")
            sim = cosine_similarity(q_vec, p_vec)
            scores.append((venue, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        top_k = scores[: self.k]

        venue_scores = {v: 0.0 for v in candidate_venues}
        for venue, sim in top_k:
            if venue in venue_scores:
                venue_scores[venue] += sim

        ranked = sorted(venue_scores.items(), key=lambda x: x[1], reverse=True)
        return ranked


class FlatFacetKNNReranker:
    """
    Baseline 2: Flat 5-Facet k-NN Reranker (Không Cổng Ngữ Cảnh).
    Tính trung bình cộng Cosine trên toàn bộ 5 Facets mà không có Cổng G_problem.
    """

    def __init__(
        self,
        feature_store: FacetFeatureStore,
        train_papers: List[Dict],
        k: int = 10,
    ):
        self.feature_store = feature_store
        self.k = k
        self.train_pids = [p["paper_id"] for p in train_papers]
        self.train_venues = [p["conference_id"] for p in train_papers]

    def compute_flat_similarity(self, q_pid: str, p_pid: str) -> float:
        q_vecs = self.feature_store.get_vectors(q_pid)
        p_vecs = self.feature_store.get_vectors(p_pid)

        total_sim = 0.0
        count = 0
        for f in ALL_FACETS:
            qv = q_vecs.get(f)
            pv = p_vecs.get(f)
            if qv is not None and pv is not None:
                if isinstance(qv, dict) and not qv:
                    continue
                if isinstance(pv, dict) and not pv:
                    continue
                total_sim += cosine_similarity(qv, pv)
                count += 1
        return (total_sim / count) if count > 0 else 0.0

    def predict(
        self, q_pid: str, candidate_venues: List[str]
    ) -> List[Tuple[str, float]]:
        scores = []
        for p_pid, venue in zip(self.train_pids, self.train_venues):
            sim = self.compute_flat_similarity(q_pid, p_pid)
            scores.append((venue, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        top_k = scores[: self.k]

        venue_scores = {v: 0.0 for v in candidate_venues}
        for venue, sim in top_k:
            if venue in venue_scores:
                venue_scores[venue] += sim

        ranked = sorted(venue_scores.items(), key=lambda x: x[1], reverse=True)
        return ranked


class RandomReranker:
    """
    Baseline 3: Random Baseline (Xếp hạng ngẫu nhiên).
    """

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
