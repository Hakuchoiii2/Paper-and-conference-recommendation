"""
Package: scripts.conference_recommendation
Hệ thống Khuyến nghị Hội nghị Khoa học dựa trên 5 Facets và Bỏ phiếu Láng giềng.
"""

from .data_loader import get_repo_root, load_dataset, load_facets
from .feature_loader import (
    FacetFeatureStore,
    cosine_similarity,
    BaseEmbeddingBackend,
    TfidfEmbeddingBackend,
    SentenceTransformerBackend,
    PrecomputedEmbeddingBackend,
)
from .reranker import GatedFacetKNNReranker, GatedFacetKNNMatcher
from .baselines import (
    WholeTextKNNReranker,
    FlatFacetKNNReranker,
    RandomReranker,
    WholeTextKNNMatcher,
    FlatFacetKNNMatcher,
    RandomMatcher,
)
from .metrics import evaluate_predictions, hit_at_k, reciprocal_rank

__all__ = [
    "get_repo_root",
    "load_dataset",
    "load_facets",
    "FacetFeatureStore",
    "cosine_similarity",
    "BaseEmbeddingBackend",
    "TfidfEmbeddingBackend",
    "SentenceTransformerBackend",
    "PrecomputedEmbeddingBackend",
    "GatedFacetKNNReranker",
    "GatedFacetKNNMatcher",
    "WholeTextKNNReranker",
    "FlatFacetKNNReranker",
    "RandomReranker",
    "WholeTextKNNMatcher",
    "FlatFacetKNNMatcher",
    "RandomMatcher",
    "evaluate_predictions",
    "hit_at_k",
    "reciprocal_rank",
]
