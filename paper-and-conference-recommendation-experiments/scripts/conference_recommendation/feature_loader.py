r"""
Module: feature_loader.py
Nhiệm vụ:
  1. Trích xuất chuỗi văn bản cho Toàn văn (Title + Abstract) và từng Facet độc lập (Problem, Task, Method, Dataset, Contribution).
     - Với TF-IDF: dùng normalize_text() (Unicode NFKC, casefold, lọc token \b\w\w+\b).
     - Với Dense Encoders (BERT, SPECTER2, BGE...): giữ nguyên văn bản tự nhiên theo đúng chuẩn Exp B:
       * whole_text = f"{title}. {abstract}".strip()
       * facet text = "; ".join(concepts)
  2. Khái quát hóa không gian vector (Vector Space) hỗ trợ đa mô hình Embedding:
     - 'tfidf': TF-IDF Sparse Vector thuần CPU.
     - 'bert': google-bert/bert-base-uncased (mean pooling, 768d, L2-normalized) đồng nhất 100% với Exp B.
     - 'specter2': allenai/specter2_base (Exp C1 Encoder Robustness Check).
     - 'bge-base': BAAI/bge-base-en-v1.5 (Exp C1 alternative).
     - 'specter', 'bge-small', 'sentence_transformers', 'precomputed', CustomCallableBackend.
  3. Cung cấp hàm đo khoảng cách Cosine Similarity tổng quát.
"""

from abc import ABC, abstractmethod
import collections
import hashlib
import math
from pathlib import Path
import re
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Các trường văn bản được quản lý
FIELD_NAMES = ("whole_text", "problem", "task", "method", "dataset", "contribution")


# ==============================================================================
# 1. TIỀN XỬ LÝ VĂN BẢN & CHUẨN HÓA ĐỘ DÀI VECTOR
# ==============================================================================

def normalize_text(text: Any) -> str:
    """Chuẩn hóa chuỗi văn bản về Unicode NFKC, viết thường và giữ token hợp lệ (dùng cho TF-IDF)."""
    if not text:
        return ""
    if isinstance(text, list):
        text = " ".join(str(item) for item in text)
    text_nfkc = unicodedata.normalize("NFKC", str(text)).casefold()
    tokens = re.findall(r"\b\w\w+\b", text_nfkc)
    return " ".join(tokens)


def format_dense_whole_text(title: Any, abstract: Any) -> str:
    """Giữ nguyên văn bản tự nhiên theo đúng hợp đồng Exp B (02_prepare_embeddings.py)."""
    t = str(title or "").strip()
    a = str(abstract or "").strip()
    if t and a:
        return f"{t}. {a}".strip()
    return (t or a).strip()


def format_dense_facet_text(value: Any) -> str:
    """Nối danh sách concept của một facet bằng '; ' mà không cắt dấu câu/chữ hoa."""
    if not value:
        return ""
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if item is not None and str(item).strip()]
        return "; ".join(parts)
    return str(value).strip()


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
    """Tính Cosine Similarity tổng quát giữa 2 vector v1 và v2."""
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
        """Mã hóa danh sách chuỗi văn bản thành các vector đã chuẩn hóa L2."""
        pass

    def encode_single(self, text: str) -> Any:
        """Mã hóa một chuỗi văn bản đơn lẻ."""
        return self.encode_batch([text])[0]


class TfidfEmbeddingBackend(BaseEmbeddingBackend):
    """Backend TF-IDF mặc định (Thuần Python CPU - Zero Dependencies)."""

    def __init__(self, corpus_texts: Optional[List[str]] = None):
        self.idf_dict: Dict[str, float] = {}
        if corpus_texts:
            self.fit(corpus_texts)

    def fit(self, corpus_texts: List[str]) -> None:
        doc_count = len(corpus_texts)
        doc_freq = collections.Counter()

        for doc in corpus_texts:
            tokens = set(doc.split())
            for t in tokens:
                doc_freq[t] += 1

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
            # Validation/test vocabulary must not alter the fitted feature space.
            raw_vec = {t: count * self.idf_dict[t] for t, count in tf.items() if t in self.idf_dict}
            vectors.append(unit_vector_sparse(raw_vec))
        return vectors


class SentenceTransformerBackend(BaseEmbeddingBackend):
    """
    Backend cho các mô hình Dense Embedding của HuggingFace / SentenceTransformers.
    Hỗ trợ pooling="mean" tường minh (khớp 100% với data/exp_b/ranking/scripts/02_prepare_embeddings.py)
    cho google-bert/bert-base-uncased, cũng như allenai/specter2_base, BAAI/bge-base-en-v1.5...
    """

    def __init__(
        self,
        model_name: str = "google-bert/bert-base-uncased",
        device: Optional[str] = None,
        batch_size: int = 16,
        pooling: Optional[str] = None,
        cache_dir: Optional[Union[str, Path]] = None,
    ):
        self.model_name = model_name
        self.pooling = pooling
        if device is None:
            try:
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.device = "cpu"
        else:
            self.device = device
        self.batch_size = batch_size
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self._model = None
        self._mem_cache: Dict[str, Any] = {}

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer, models
            except ImportError:
                raise ImportError(
                    "Thư viện 'sentence-transformers' chưa được cài đặt. "
                    "Vui lòng chạy: pip install sentence-transformers torch "
                    "để sử dụng backend Dense Embedding."
                )
            print(f"[*] Đang tải mô hình Dense Embedding: {self.model_name} (pooling={self.pooling or 'default'})...")
            if self.pooling == "mean":
                encoder = models.Transformer(self.model_name)
                pool = models.Pooling(encoder.get_word_embedding_dimension(), pooling_mode="mean")
                self._model = SentenceTransformer(modules=[encoder, pool], device=self.device)
            else:
                self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def _cache_file(self, texts: List[str]) -> Optional[Path]:
        if self.cache_dir is None:
            return None
        key = hashlib.sha256(
            f"{self.model_name}|{self.pooling}|".encode("utf-8")
            + "\n".join(texts).encode("utf-8")
        ).hexdigest()[:24]
        safe_model = re.sub(r"[^a-zA-Z0-9._-]+", "_", self.model_name)
        return self.cache_dir / f"{safe_model}_{self.pooling or 'default'}_{key}.npz"

    def encode_batch(self, texts: List[str]) -> List[Any]:
        import numpy as np

        cache_path = self._cache_file(texts)
        if cache_path is not None and cache_path.exists():
            data = np.load(cache_path)
            embs = data["embeddings"]
            mask = data["mask"]
            return [embs[i].astype(np.float32) if bool(mask[i]) else None for i in range(len(texts))]

        non_empty_indices = [i for i, t in enumerate(texts) if t and t.strip()]
        results: List[Any] = [None] * len(texts)

        if non_empty_indices:
            # Reuse in-memory cache for identical texts within the same process
            to_encode_idx = []
            to_encode_texts = []
            for idx in non_empty_indices:
                txt = texts[idx]
                if txt in self._mem_cache:
                    results[idx] = self._mem_cache[txt]
                else:
                    to_encode_idx.append(idx)
                    to_encode_texts.append(txt)

            if to_encode_texts:
                model = self._load_model()
                encoded = model.encode(
                    to_encode_texts,
                    batch_size=self.batch_size,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                )
                for idx, txt, vec in zip(to_encode_idx, to_encode_texts, encoded):
                    arr = np.asarray(vec, dtype=np.float32)
                    self._mem_cache[txt] = arr
                    results[idx] = arr

        if cache_path is not None and non_empty_indices:
            dim = len(results[non_empty_indices[0]])
            embs = np.zeros((len(texts), dim), dtype=np.float32)
            mask = np.zeros(len(texts), dtype=bool)
            for idx in non_empty_indices:
                embs[idx] = results[idx]
                mask[idx] = True
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(cache_path, embeddings=embs, mask=mask)

        return results


class PrecomputedEmbeddingBackend(BaseEmbeddingBackend):
    """Backend nạp vector Dense đã được tính toán và lưu sẵn trên đĩa (.npz hoặc .jsonl)."""

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
            import numpy as np
            data = np.load(self.precomputed_path)
            for k in data.files:
                if "__" in k:
                    pid, field = k.split("__", 1)
                    self.cached_vectors[(pid, field)] = unit_vector_dense(data[k])
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
        return [None] * len(texts)


class CustomCallableBackend(BaseEmbeddingBackend):
    """Backend cho phép truyền hàm mã hóa tùy biến: fn(texts: List[str]) -> List[Any]."""

    def __init__(self, encode_fn: Callable[[List[str]], List[Any]]):
        self.encode_fn = encode_fn

    def encode_batch(self, texts: List[str]) -> List[Any]:
        raw_vecs = self.encode_fn(texts)
        return [unit_vector_dense(v) if v is not None else None for v in raw_vecs]


# ==============================================================================
# 3. KHO ĐẶC TRƯNG TỔNG QUÁT (FACET FEATURE STORE)
# ==============================================================================

class FacetFeatureStore:
    """
    Kho lưu trữ và tính toán vector cho bài báo khoa học trên Toàn văn và 5 Facets.
    Hỗ trợ:
      - 'tfidf': TF-IDF Sparse Vector thuần CPU (áp dụng normalize_text).
      - 'bert': google-bert/bert-base-uncased (pooling='mean', 768d, giữ nguyên văn bản gốc).
      - 'specter2': allenai/specter2_base (Exp C1).
      - 'bge-base': BAAI/bge-base-en-v1.5 (Exp C1).
      - 'specter', 'bge-small', 'sentence_transformers', 'precomputed', BaseEmbeddingBackend.
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
        pids = [p["paper_id"] for p in self.all_papers]
        if len(pids) != len(set(pids)):
            raise ValueError("Duplicate paper_id or overlapping train/query sets")
        self.backend_config = backend_config or {}
        self.use_tfidf_norm = (
            (isinstance(backend, str) and backend.lower().strip() in ("tfidf", "sparse"))
            or isinstance(backend, TfidfEmbeddingBackend)
        )

        # 1. Trích xuất văn bản cho toàn văn và 5 facets (tách biệt quy tắc TF-IDF vs Dense)
        self.text_store = self._build_text_store(use_tfidf_norm=self.use_tfidf_norm)

        # 2. Khởi tạo Backend Embedding theo cấu hình
        self.backend = self._init_backend(backend)

        # 3. Vector hóa toàn bộ bài báo
        self.vector_store = self._vectorize_all()

    def _build_text_store(self, use_tfidf_norm: bool = True) -> Dict[str, Dict[str, str]]:
        """Tạo từ điển [paper_id -> {whole_text, problem, task, method, dataset, contribution}]."""
        store = {}
        for p in self.all_papers:
            pid = p["paper_id"]
            facets = p.get("facets", {})
            title = p.get("title", "")
            abstract = p.get("abstract", "")

            if use_tfidf_norm:
                store[pid] = {
                    "whole_text": normalize_text(f"{title} {abstract}"),
                    "problem": normalize_text(facets.get("problem", [])),
                    "task": normalize_text(facets.get("task", [])),
                    "method": normalize_text(facets.get("method", [])),
                    "dataset": normalize_text(facets.get("dataset", [])),
                    "contribution": normalize_text(facets.get("contribution", [])),
                }
            else:
                store[pid] = {
                    "whole_text": format_dense_whole_text(title, abstract),
                    "problem": format_dense_facet_text(facets.get("problem", [])),
                    "task": format_dense_facet_text(facets.get("task", [])),
                    "method": format_dense_facet_text(facets.get("method", [])),
                    "dataset": format_dense_facet_text(facets.get("dataset", [])),
                    "contribution": format_dense_facet_text(facets.get("contribution", [])),
                }
        return store

    def _init_backend(
        self, backend: Union[str, BaseEmbeddingBackend]
    ) -> BaseEmbeddingBackend:
        """Khởi tạo embedding backend tương ứng."""
        if isinstance(backend, BaseEmbeddingBackend):
            return backend

        backend_str = str(backend).lower().strip()
        device = self.backend_config.get("device")
        cache_dir = self.backend_config.get("cache_dir")

        if backend_str in ("tfidf", "sparse"):
            corpus_texts = [self.text_store[p["paper_id"]]["whole_text"] for p in self.train_papers]
            return TfidfEmbeddingBackend(corpus_texts=corpus_texts)

        elif backend_str in ("bert", "bert-base-uncased", "bert_base_uncased"):
            model_name = self.backend_config.get("model_name", "google-bert/bert-base-uncased")
            batch_size = self.backend_config.get("batch_size", 16)
            pooling = self.backend_config.get("pooling", "mean")
            return SentenceTransformerBackend(
                model_name=model_name,
                device=device,
                batch_size=batch_size,
                pooling=pooling,
                cache_dir=cache_dir,
            )

        elif backend_str in ("specter2", "specter2_base"):
            model_name = self.backend_config.get("model_name", "allenai/specter2_base")
            batch_size = self.backend_config.get("batch_size", 32)
            pooling = self.backend_config.get("pooling")
            return SentenceTransformerBackend(
                model_name=model_name,
                device=device,
                batch_size=batch_size,
                pooling=pooling,
                cache_dir=cache_dir,
            )

        elif backend_str == "specter":
            model_name = self.backend_config.get(
                "model_name", "sentence-transformers/allenai-specter"
            )
            batch_size = self.backend_config.get("batch_size", 64)
            return SentenceTransformerBackend(
                model_name=model_name, device=device, batch_size=batch_size, cache_dir=cache_dir
            )

        elif backend_str in ("bge-base", "bge_base"):
            model_name = self.backend_config.get("model_name", "BAAI/bge-base-en-v1.5")
            batch_size = self.backend_config.get("batch_size", 32)
            return SentenceTransformerBackend(
                model_name=model_name, device=device, batch_size=batch_size, cache_dir=cache_dir
            )

        elif backend_str in ("bge", "bge-small", "bge_small"):
            model_name = self.backend_config.get(
                "model_name", "BAAI/bge-small-en-v1.5"
            )
            batch_size = self.backend_config.get("batch_size", 64)
            return SentenceTransformerBackend(
                model_name=model_name, device=device, batch_size=batch_size, cache_dir=cache_dir
            )

        elif backend_str in ("sentence_transformers", "dense", "hf"):
            model_name = self.backend_config.get("model_name", "all-MiniLM-L6-v2")
            batch_size = self.backend_config.get("batch_size", 32)
            pooling = self.backend_config.get("pooling")
            return SentenceTransformerBackend(
                model_name=model_name,
                device=device,
                batch_size=batch_size,
                pooling=pooling,
                cache_dir=cache_dir,
            )

        elif backend_str in ("precomputed", "file"):
            precomputed_path = self.backend_config.get("path")
            if not precomputed_path:
                raise ValueError("Backend 'precomputed' yêu cầu cấu hình 'path' tới file vector.")
            return PrecomputedEmbeddingBackend(precomputed_path=precomputed_path)

        else:
            raise ValueError(
                f"Backend '{backend}' không được hỗ trợ. "
                "Chọn trong: ['tfidf', 'bert', 'specter2', 'bge-base', 'specter', 'bge-small', "
                "'sentence_transformers', 'precomputed'] hoặc truyền instance của BaseEmbeddingBackend."
            )

    def _vectorize_all(self) -> Dict[str, Dict[str, Any]]:
        """Mã hóa văn bản thành các vector biểu diễn tương ứng."""
        if isinstance(self.backend, PrecomputedEmbeddingBackend):
            vector_store = {}
            for pid in self.text_store:
                vector_store[pid] = {
                    field: self.backend.get_cached_vector(pid, field)
                    for field in FIELD_NAMES
                }
            return vector_store

        vector_store = {pid: {} for pid in self.text_store}
        self.field_backends = {}
        for field in FIELD_NAMES:
            pids = list(self.text_store.keys())
            texts = [self.text_store[pid][field] for pid in pids]
            encoder = self.backend
            if isinstance(encoder, TfidfEmbeddingBackend):
                encoder = TfidfEmbeddingBackend([
                    self.text_store[p["paper_id"]][field] for p in self.train_papers
                ])
                self.field_backends[field] = encoder
            field_vectors = encoder.encode_batch(texts)
            for pid, vec in zip(pids, field_vectors):
                vector_store[pid][field] = vec

        return vector_store

    def get_vectors(self, paper_id: str) -> Dict[str, Any]:
        """Lấy toàn bộ các vector biểu diễn của một bài báo."""
        return self.vector_store.get(paper_id, {})
