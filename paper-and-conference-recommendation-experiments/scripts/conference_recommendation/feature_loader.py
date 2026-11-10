"""
Module: feature_loader.py
Nhiệm vụ:
  1. Trích xuất chuỗi văn bản cho Toàn văn (Title + Abstract) và từng Facet độc lập (Problem, Task, Method, Dataset, Contribution).
  2. Khái quát hóa không gian vector (Vector Space) hỗ trợ đa mô hình Embedding:
     - TF-IDF Sparse Vector (Mặc định - Siêu nhẹ trên CPU, không cần tải model nặng).
     - Dense Embeddings: SPECTER2, SciBERT, BGE, SentenceTransformers (Hỗ trợ mô hình học sâu học thuật).
     - Precomputed Embeddings: Nạp trực tiếp từ file vector đã tính toán trước (.npz, .npy, .jsonl).
     - Custom Embedding: Dễ dàng cắm hàm nhúng tùy biến của người dùng.
  3. Cung cấp hàm đo khoảng cách Cosine Similarity tổng quát (hỗ trợ cả Sparse Dict lẫn Dense Numpy/List).
"""

from abc import ABC, abstractmethod
import collections
import math
import os
from pathlib import Path
import re
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Các trường văn bản được quản lý
FIELD_NAMES = ("whole_text", "problem", "task", "method", "dataset", "contribution")


# ==============================================================================
# 1. TIỀN XỬ LÝ VĂN BẢN & CHUẨN HÓA ĐỘ ĐÀI VECTOR
# ==============================================================================

def normalize_text(text: Any) -> str:
    """Chuẩn hóa chuỗi văn bản về Unicode NFKC, viết thường và giữ token hợp lệ."""
    if not text:
        return ""
    if isinstance(text, list):
        text = " ".join(str(item) for item in text)
    text_nfkc = unicodedata.normalize("NFKC", str(text)).casefold()
    tokens = re.findall(r"\b\w\w+\b", text_nfkc)
    return " ".join(tokens)


def unit_vector_sparse(vec: Dict[str, float]) -> Dict[str, float]:
    """Chuẩn hóa vector thưa (Dictionary) về độ dài đơn vị Euclidean L2 = 1.0."""
    norm = math.sqrt(sum(v * v for v in vec.values()))
    if norm == 0.0:
        return {}
    return {k: v / norm for k, v in vec.items() if v != 0.0}


def unit_vector_dense(vec: Any) -> Any:
    """Chuẩn hóa vector đặc (Numpy array hoặc List) về độ dài đơn vị Euclidean L2 = 1.0."""
    try:
        import numpy as np
        if isinstance(vec, np.ndarray):
            norm = np.linalg.norm(vec)
            if norm == 0.0:
                return vec
            return vec / norm
    except ImportError:
        pass

    if isinstance(vec, (list, tuple)):
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0.0:
            return vec
        return [x / norm for x in vec]
    return vec


def cosine_similarity(v1: Any, v2: Any) -> float:
    """
    Tính Cosine Similarity tổng quát giữa 2 vector v1 và v2.
    Tự động nhận diện và xử lý:
      - Hai vector thưa (Sparse Dictionary: Dict[str, float])
      - Hai vector đặc (Dense Numpy Array hoặc List[float])
      - Vector rỗng / None (trả về 0.0)
    """
    if v1 is None or v2 is None:
        return 0.0

    # Trường hợp 1: Cả hai là dictionary thưa (TF-IDF)
    if isinstance(v1, dict) and isinstance(v2, dict):
        if not v1 or not v2:
            return 0.0
        if len(v1) > len(v2):
            v1, v2 = v2, v1
        return sum(val * v2.get(k, 0.0) for k, val in v1.items())

    # Trường hợp 2: Dense Numpy array
    try:
        import numpy as np
        if isinstance(v1, np.ndarray) and isinstance(v2, np.ndarray):
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            if norm1 == 0.0 or norm2 == 0.0:
                return 0.0
            return float(np.dot(v1, v2) / (norm1 * norm2))
    except ImportError:
        pass

    # Trường hợp 3: List / Tuple số thực
    if isinstance(v1, (list, tuple)) and isinstance(v2, (list, tuple)):
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot / (norm1 * norm2)

    return 0.0


# ==============================================================================
# 2. KHUNG GIAO DIỆN BACKEND EMBEDDING (ABSTRACT & CONCRETE BACKENDS)
# ==============================================================================

class BaseEmbeddingBackend(ABC):
    """Lớp cơ sở trừu tượng cho tất cả các mô hình nhúng (Embedding Backends)."""

    @abstractmethod
    def encode_batch(self, texts: List[str]) -> List[Any]:
        """
        Mã hóa một danh sách các chuỗi văn bản thành các vector đã chuẩn hóa L2.
        Trả về: Danh sách các vector (Dict thưa hoặc Numpy/List đặc).
        """
        pass

    def encode_single(self, text: str) -> Any:
        """Mã hóa một chuỗi văn bản đơn lẻ."""
        return self.encode_batch([text])[0]


class TfidfEmbeddingBackend(BaseEmbeddingBackend):
    """
    Backend TF-IDF mặc định (Thuần Python CPU - Zero Dependencies).
    Học IDF từ toàn bộ corpus và xuất vector thưa chuẩn hóa L2.
    """

    def __init__(self, corpus_texts: Optional[List[str]] = None):
        self.idf_dict: Dict[str, float] = {}
        if corpus_texts:
            self.fit(corpus_texts)

    def fit(self, corpus_texts: List[str]) -> None:
        """Tính toán bảng trọng số IDF từ tập văn bản huấn luyện."""
        doc_count = len(corpus_texts)
        doc_freq = collections.Counter()

        for doc in corpus_texts:
            tokens = set(doc.split())
            for t in tokens:
                doc_freq[t] += 1

        # Smooth IDF: log((1 + N) / (1 + df)) + 1
        self.idf_dict = {
            t: math.log((1.0 + doc_count) / (1.0 + count)) + 1.0
            for t, count in doc_freq.items()
        }

    def encode_batch(self, texts: List[str]) -> List[Dict[str, float]]:
        vectors = []
        for text in texts:
            if not text:
                vectors.append({})
                continue
            tokens = text.split()
            tf = collections.Counter(tokens)
            raw_vec = {t: count * self.idf_dict.get(t, 1.0) for t, count in tf.items()}
            vectors.append(unit_vector_sparse(raw_vec))
        return vectors


class SentenceTransformerBackend(BaseEmbeddingBackend):
    """
    Backend cho các mô hình Dense Embedding của HuggingFace / SentenceTransformers.
    Mặc định hỗ trợ:
      - 'allenai/specter2_base' (Chuyên biệt cho bài báo khoa học)
      - 'allenai/scibert_scivocab_uncased'
      - 'BAAI/bge-small-en-v1.5'
      - Bất kỳ mô hình HuggingFace nào khác.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/allenai-specter",
        device: Optional[str] = None,
        batch_size: int = 64,
    ):
        self.model_name = model_name
        if device is None:
            try:
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.device = "cpu"
        else:
            self.device = device
        self.batch_size = batch_size
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError(
                    "Thư viện 'sentence-transformers' chưa được cài đặt. "
                    "Vui lòng chạy: pip install sentence-transformers torch "
                    "để sử dụng backend Dense Embedding."
                )
            print(f"[*] Đang tải mô hình Dense Embedding: {self.model_name}...")
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def encode_batch(self, texts: List[str]) -> List[Any]:
        model = self._load_model()
        # Thay thế chuỗi rỗng bằng chuỗi giả để tránh lỗi tensor rỗng
        clean_texts = [t if t.strip() else " " for t in texts]
        embeddings = model.encode(
            clean_texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return [embeddings[i] if texts[i].strip() else None for i in range(len(texts))]


class PrecomputedEmbeddingBackend(BaseEmbeddingBackend):
    """
    Backend nạp vector Dense đã được tính toán và lưu sẵn trên đĩa (.npz hoặc .jsonl).
    Cấu trúc mong đợi: Dict[(paper_id, field) -> vector].
    """

    def __init__(self, precomputed_path: Union[str, Path]):
        self.precomputed_path = Path(precomputed_path)
        self.cached_vectors: Dict[Tuple[str, str], Any] = {}
        self._load_cache()

    def _load_cache(self):
        if not self.precomputed_path.exists():
            raise FileNotFoundError(
                f"Không tìm thấy file precomputed embedding tại: {self.precomputed_path}"
            )
        suffix = self.precomputed_path.suffix.lower()
        print(f"[*] Đang nạp precomputed embeddings từ {self.precomputed_path}...")

        if suffix == ".npz":
            try:
                import numpy as np
                data = np.load(self.precomputed_path)
                for k in data.files:
                    # Giả định key có dạng 'paper_id__field'
                    if "__" in k:
                        pid, field = k.split("__", 1)
                        self.cached_vectors[(pid, field)] = unit_vector_dense(data[k])
            except ImportError:
                raise ImportError("Cần cài đặt thư viện 'numpy' để đọc file .npz.")
        elif suffix in (".jsonl", ".json"):
            import json
            with open(self.precomputed_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    pid = row.get("paper_id")
                    for field in FIELD_NAMES:
                        if field in row:
                            self.cached_vectors[(pid, field)] = unit_vector_dense(row[field])
        else:
            raise ValueError(f"Định dạng precomputed chưa được hỗ trợ: {suffix}")

    def get_cached_vector(self, paper_id: str, field: str) -> Optional[Any]:
        return self.cached_vectors.get((paper_id, field))

    def encode_batch(self, texts: List[str]) -> List[Any]:
        # Precomputed backend không encode text runtime, trả về None nếu không có trong cache
        return [None] * len(texts)


class CustomCallableBackend(BaseEmbeddingBackend):
    """Backend cho phép truyền hàm mã hóa tùy biến: fn(texts: List[str]) -> List[Any]."""

    def __init__(self, encode_fn: Callable[[List[str]], List[Any]]):
        self.encode_fn = encode_fn

    def encode_batch(self, texts: List[str]) -> List[Any]:
        raw_vecs = self.encode_fn(texts)
        return [unit_vector_dense(v) for v in raw_vecs]


# ==============================================================================
# 3. KHO ĐẶC TRƯNG TỔNG QUÁT (FACET FEATURE STORE)
# ==============================================================================

class FacetFeatureStore:
    """
    Kho lưu trữ và tính toán vector cho bài báo khoa học trên Toàn văn và 5 Facets.
    Hỗ trợ chuyển đổi linh hoạt qua tham số backend:
      - 'tfidf': TF-IDF Sparse Vector thuần CPU (Mặc định).
      - 'specter2' / 'specter': Dense Transformer chuyên biệt cho bài báo.
      - 'sentence_transformers': Bất kỳ mô hình SentenceTransformer nào.
      - 'precomputed': Vector tính sẵn từ tệp .npz / .jsonl.
      - Hoặc truyền trực tiếp một instance của BaseEmbeddingBackend.
    """

    def __init__(
        self,
        train_papers: List[Dict],
        test_papers: List[Dict],
        backend: Union[str, BaseEmbeddingBackend] = "tfidf",
        backend_config: Optional[Dict[str, Any]] = None,
    ):
        self.train_papers = train_papers
        self.test_papers = test_papers
        self.all_papers = train_papers + test_papers
        self.backend_config = backend_config or {}

        # 1. Trích xuất văn bản phẳng cho toàn văn và 5 facets
        self.text_store = self._build_text_store()

        # 2. Khởi tạo Backend Embedding theo cấu hình
        self.backend = self._init_backend(backend)

        # 3. Vector hóa toàn bộ bài báo
        self.vector_store = self._vectorize_all()

    def _build_text_store(self) -> Dict[str, Dict[str, str]]:
        """Tạo từ điển [paper_id -> {whole_text, problem, task, method, dataset, contribution}]."""
        store = {}
        for p in self.all_papers:
            pid = p["paper_id"]
            facets = p.get("facets", {})
            title = p.get("title", "")
            abstract = p.get("abstract", "")

            store[pid] = {
                "whole_text": normalize_text(f"{title} {abstract}"),
                "problem": normalize_text(facets.get("problem", [])),
                "task": normalize_text(facets.get("task", [])),
                "method": normalize_text(facets.get("method", [])),
                "dataset": normalize_text(facets.get("dataset", [])),
                "contribution": normalize_text(facets.get("contribution", [])),
            }
        return store

    def _init_backend(
        self, backend: Union[str, BaseEmbeddingBackend]
    ) -> BaseEmbeddingBackend:
        """Khởi tạo embedding backend tương ứng."""
        if isinstance(backend, BaseEmbeddingBackend):
            return backend

        backend_str = str(backend).lower().strip()

        if backend_str in ("tfidf", "sparse"):
            # Thu thập toàn bộ văn bản để fit IDF
            corpus_texts = []
            for fields in self.text_store.values():
                for t in fields.values():
                    if t:
                        corpus_texts.append(t)
            return TfidfEmbeddingBackend(corpus_texts=corpus_texts)

        elif backend_str in ("specter2", "specter"):
            model_name = self.backend_config.get(
                "model_name", "sentence-transformers/allenai-specter"
            )
            device = self.backend_config.get("device")
            batch_size = self.backend_config.get("batch_size", 32)
            return SentenceTransformerBackend(
                model_name=model_name, device=device, batch_size=batch_size
            )

        elif backend_str in ("sentence_transformers", "dense", "hf"):
            model_name = self.backend_config.get(
                "model_name", "all-MiniLM-L6-v2"
            )
            device = self.backend_config.get("device")
            batch_size = self.backend_config.get("batch_size", 32)
            return SentenceTransformerBackend(
                model_name=model_name, device=device, batch_size=batch_size
            )

        elif backend_str in ("precomputed", "file"):
            precomputed_path = self.backend_config.get("path")
            if not precomputed_path:
                raise ValueError("Backend 'precomputed' yêu cầu cấu hình 'path' tới file vector.")
            return PrecomputedEmbeddingBackend(precomputed_path=precomputed_path)

        else:
            raise ValueError(
                f"Backend '{backend}' không được hỗ trợ. "
                "Chọn trong: ['tfidf', 'specter2', 'sentence_transformers', 'precomputed'] "
                "hoặc truyền instance của BaseEmbeddingBackend."
            )

    def _vectorize_all(self) -> Dict[str, Dict[str, Any]]:
        """Mã hóa văn bản thành các vector biểu diễn tương ứng."""
        # Nếu là precomputed backend, lấy trực tiếp từ cache
        if isinstance(self.backend, PrecomputedEmbeddingBackend):
            vector_store = {}
            for pid in self.text_store:
                vector_store[pid] = {
                    field: self.backend.get_cached_vector(pid, field)
                    for field in FIELD_NAMES
                }
            return vector_store

        # Thu thập theo batch theo từng field để tối ưu tốc độ encoding của Transformer / TF-IDF
        vector_store = {pid: {} for pid in self.text_store}
        for field in FIELD_NAMES:
            pids = list(self.text_store.keys())
            texts = [self.text_store[pid][field] for pid in pids]
            field_vectors = self.backend.encode_batch(texts)
            for pid, vec in zip(pids, field_vectors):
                vector_store[pid][field] = vec

        return vector_store

    def get_vectors(self, paper_id: str) -> Dict[str, Any]:
        """Lấy toàn bộ các vector biểu diễn của một bài báo."""
        return self.vector_store.get(paper_id, {})
