"""
Module: reranker.py
Cài đặt thuật toán đề xuất và tái xếp hạng (Reranker) chính cho nhánh Hội nghị:
Gated 5-Facet k-NN Reranker
(Hệ thống Khuyến nghị Hội nghị Phân tầng có Cổng Ngữ Cảnh 5 Facets và Bỏ phiếu Láng giềng).
"""

import math
from typing import Any, Dict, List, Optional, Tuple, Union
from .feature_loader import FacetFeatureStore, cosine_similarity


def sigmoid(z: float) -> float:
    """Hàm Sigmoid numerically stable."""
    if z >= 20.0:
        return 1.0
    if z <= -20.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-z))


class GatedFacetKNNReranker:
    """
    Bộ tái xếp hạng (Reranker) và khuyến nghị hội nghị dựa trên:
      1. Cổng Ngữ Cảnh Bài toán: G_problem(q, p) = sigmoid(kappa * (cos_problem - tau))
      2. Tương đồng đa khía cạnh: Task, Method, Dataset, Contribution có trọng số động.
      3. Bỏ phiếu có trọng số theo Top-k bài Train tương đồng nhất (Kernel Voting).
    
    Hỗ trợ cả Sparse Vector (TF-IDF) lẫn Dense Embedding (SPECTER2, SciBERT...).
    """

    def __init__(
        self,
        feature_store: FacetFeatureStore,
        train_papers: List[Dict],
        k: int = 10,
        tau: float = 0.45,
        kappa: float = 10.0,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.feature_store = feature_store
        self.train_papers = train_papers
        self.k = k
        self.tau = tau
        self.kappa = kappa

        # Trọng số mặc định cho các facets giải pháp
        self.weights = weights or {
            "task": 0.3,
            "method": 0.3,
            "dataset": 0.2,
            "contribution": 0.2,
        }

        # Lưu danh sách ID và nhãn venue của tập train
        self.train_pids = [p["paper_id"] for p in train_papers]
        self.train_venues = [p["conference_id"] for p in train_papers]

    def compute_context_gate(
        self, q_vec: Any, p_vec: Any
    ) -> float:
        """
        Tính giá trị Cổng Ngữ Cảnh Problem:
        Nếu không có problem (vector rỗng), dùng ngưỡng trung tính 0.5.
        """
        if q_vec is None or p_vec is None:
            return 0.5
        # Kiểm tra nếu rỗng (dict hoặc array)
        if isinstance(q_vec, dict) and not q_vec:
            return 0.5
        if isinstance(p_vec, dict) and not p_vec:
            return 0.5

        cos_prob = cosine_similarity(q_vec, p_vec)
        return sigmoid(self.kappa * (cos_prob - self.tau))

    def compute_weighted_facets(
        self,
        q_vecs: Dict[str, Any],
        p_vecs: Dict[str, Any],
    ) -> float:
        """
        Tính tổng độ tương đồng Cosine của Task, Method, Dataset, Contribution.
        Tự động tái chuẩn hóa trọng số nếu có facet rỗng.
        """
        observed_weight_sum = 0.0
        weighted_score = 0.0

        for f, w in self.weights.items():
            qv = q_vecs.get(f)
            pv = p_vecs.get(f)
            if qv is not None and pv is not None:
                if isinstance(qv, dict) and not qv:
                    continue
                if isinstance(pv, dict) and not pv:
                    continue

                cos_f = cosine_similarity(qv, pv)
                weighted_score += w * cos_f
                observed_weight_sum += w

        if observed_weight_sum == 0.0:
            return 0.0
        # Chuẩn hóa về thang [0, 1] trên tập các facets quan sát được
        return weighted_score / observed_weight_sum

    def compute_paper_similarity(self, q_pid: str, p_pid: str) -> float:
        """
        Tính điểm tương đồng phân tầng Sim(q, p) giữa bản thảo q và bài train p.
        Sim(q, p) = Gate_problem * WeightedFacets
        """
        q_vecs = self.feature_store.get_vectors(q_pid)
        p_vecs = self.feature_store.get_vectors(p_pid)

        # 1. Cổng Ngữ Cảnh Problem
        gate = self.compute_context_gate(
            q_vecs.get("problem"), p_vecs.get("problem")
        )

        # 2. Điểm tương đồng các facets còn lại
        facet_sim = self.compute_weighted_facets(q_vecs, p_vecs)

        return gate * facet_sim

    def predict(
        self, q_pid: str, candidate_venues: List[str]
    ) -> List[Tuple[str, float]]:
        """
        Dự đoán và xếp hạng Top Hội nghị cho bài test q_pid.

        Returns:
            Danh sách sắp xếp giảm dần [(conference_id, score), ...]
        """
        # 1. Tính Sim(q, p) với tất cả các bài trong tập Train
        scores = []
        for p_pid, venue in zip(self.train_pids, self.train_venues):
            sim = self.compute_paper_similarity(q_pid, p_pid)
            scores.append((p_pid, venue, sim))

        # 2. Lấy Top-k bài train có độ tương đồng cao nhất
        scores.sort(key=lambda x: x[2], reverse=True)
        top_k = scores[: self.k]

        # 3. Bỏ phiếu tích lũy điểm cho từng hội nghị (Kernel Voting)
        venue_scores = {v: 0.0 for v in candidate_venues}
        for _, venue, sim in top_k:
            if venue in venue_scores:
                venue_scores[venue] += sim

        # 4. Sắp xếp các hội nghị theo điểm số giảm dần
        ranked = sorted(venue_scores.items(), key=lambda x: x[1], reverse=True)
        return ranked


# Alias tương thích ngược
GatedFacetKNNMatcher = GatedFacetKNNReranker
