from __future__ import annotations

import asyncio
import json
import math
import os
import re
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from model_runner import MODEL_REGISTRY, ModelRunnerManager
from schemas import (
    AnalysisDetail,
    AnalysisProvenance,
    AnalysisTimings,
    ConferenceDetail,
    ConferenceExplanationResponse,
    ConferenceFacetScore,
    ConferenceRankingResponse,
    ConferenceRecommendationItem,
    CreateAnalysisRequest,
    CreateAnalysisResponse,
    EvidenceSpan,
    ExampleDetail,
    ExampleSummary,
    FacetAlignmentBreakdown,
    FacetConcept,
    FacetKey,
    FacetOutput,
    HealthResponse,
    JobError,
    JobResponse,
    LoadModelResponse,
    ModelInfo,
    PaperDetail,
    PaperExplanationResponse,
    PaperRankingResponse,
    PaperRecommendationItem,
    RepresentativePaperItem,
    RepresentativePapersResponse,
    RuntimeLimits,
    RuntimeStatus,
)

FACETS: List[FacetKey] = ["problem", "task", "method", "dataset", "contribution"]
FIELDS: List[str] = ["whole_text", *FACETS]

# Chuẩn Exp B (configs/exp_b.json)
FIXED_WEIGHTS: Dict[FacetKey, float] = {
    "problem": 0.40,
    "task": 0.20,
    "method": 0.20,
    "dataset": 0.10,
    "contribution": 0.10,
}

# Chuẩn Gated 5-Facet k-NN (configs/conference_recommendation/config.json)
CONF_GATE_TAU: float = 0.45
CONF_GATE_KAPPA: float = 10.0
CONF_KNN_K: int = 10
CONF_SOLUTION_WEIGHTS: Dict[FacetKey, float] = {
    "task": 0.30,
    "method": 0.30,
    "dataset": 0.20,
    "contribution": 0.20,
}


def load_dotenv_file(env_path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not env_path.exists():
        return env
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def resolve_path(base_dir: Path, raw_path: str) -> Path:
    p = Path(raw_path)
    return p if p.is_absolute() else (base_dir / p).resolve()


def sigmoid(z: float) -> float:
    if z >= 20.0:
        return 1.0
    if z <= -20.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-z))


def python_idx_to_utf16_offset(text: str, py_idx: int) -> int:
    """Convert Python string index to JS UTF-16 code unit offset."""
    return len(text[:py_idx].encode("utf-16-le")) // 2


def make_evidence_span(text: str, quote: str, source_field: str) -> EvidenceSpan:
    idx = text.find(quote)
    if idx == -1 and quote:
        idx = text.lower().find(quote.lower())
    if idx == -1 or not quote:
        return EvidenceSpan(
            quote=quote,
            source_field=source_field,  # type: ignore[arg-type]
            start_offset=None,
            end_offset=None,
            verified=False,
        )
    actual_quote = text[idx : idx + len(quote)]
    start_u16 = python_idx_to_utf16_offset(text, idx)
    end_u16 = python_idx_to_utf16_offset(text, idx + len(actual_quote))
    return EvidenceSpan(
        quote=actual_quote,
        source_field=source_field,  # type: ignore[arg-type]
        start_offset=start_u16,
        end_offset=end_u16,
        verified=True,
    )


def tokenize(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) >= 2]


def build_tfidf_vector(text: str, idf: Dict[str, float], default_idf: float) -> Dict[str, float]:
    toks = tokenize(text)
    if not toks:
        return {}
    counts = Counter(toks)
    vec = {t: c * idf.get(t, default_idf) for t, c in counts.items()}
    norm = math.sqrt(sum(v * v for v in vec.values()))
    if norm == 0.0:
        return {}
    return {t: v / norm for t, v in vec.items()}


def sparse_cosine(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    if len(vec_a) > len(vec_b):
        vec_a, vec_b = vec_b, vec_a
    dot = sum(val * vec_b[t] for t, val in vec_a.items() if t in vec_b)
    return round(max(0.0, min(1.0, dot)), 4)


def tfidf_cosine(text_a: str, text_b: str) -> float:
    toks_a = tokenize(text_a)
    toks_b = tokenize(text_b)
    if not toks_a or not toks_b:
        return 0.0
    ca = Counter(toks_a)
    cb = Counter(toks_b)
    common = set(ca.keys()) & set(cb.keys())
    if not common:
        return 0.0
    dot = sum(ca[t] * cb[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in ca.values()))
    norm_b = math.sqrt(sum(v * v for v in cb.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return round(dot / (norm_a * norm_b), 4)


class DemoBackendService:
    def __init__(self) -> None:
        self.session_id = f"sess_{uuid.uuid4().hex[:8]}"
        self.demo_dir = Path(__file__).resolve().parent.parent
        self.env = load_dotenv_file(self.demo_dir / ".env")
        self.model_runner = ModelRunnerManager()

        # Tự động phát hiện khả năng chạy trực tiếp của từng model dựa trên adapter thực tế + GPU VRAM
        self.models: List[ModelInfo] = []
        for spec in MODEL_REGISTRY.values():
            can_run, reason = self.model_runner.is_local_runnable(spec.model_key)
            self.models.append(
                ModelInfo(
                    model_key=spec.model_key,
                    display_name=spec.display_name,
                    family=spec.family,
                    parameter_size=spec.parameter_size,
                    supported=can_run,
                    precomputed_available=True,
                    ranking_artifacts_ready=True,
                    unavailable_reason=None if can_run else reason,
                )
            )

        supported_keys = [m.model_key for m in self.models if m.supported]
        default_model_key = (
            "Qwen3-4B"
            if "Qwen3-4B" in supported_keys
            else (supported_keys[0] if supported_keys else None)
        )

        self.runtime = RuntimeStatus(
            connected=True,
            loaded_model_key=default_model_key,
            intended_model_key=default_model_key,
            worker_busy=False,
            current_task=None,
            ranking_ready=True,
            device_summary=(
                f"GPU {self.model_runner.device.upper()} (Real 4-bit LoRA LLM + BERT-base-uncased)"
                if self.model_runner.enable_real_llm
                else "CPU Adapter (Heuristic Live + Real Precomputed 5 LLMs)"
            ),
            limits=RuntimeLimits(),
        )

        # Core data stores (strictly loaded from _local/demo_artifacts)
        self.papers: Dict[str, PaperDetail] = {}
        self.paper_facets: Dict[str, Dict[FacetKey, List[str]]] = {}
        self.corpus_pids: List[str] = []

        self.conferences: Dict[str, ConferenceDetail] = {}
        self.conf_cids: List[str] = []
        self.conf_top_keywords: Dict[str, Dict[FacetKey, List[str]]] = {}

        # Strictly 602 Train papers for Conference Recommendation (zero leakage)
        self.conf_train_pool: List[Dict] = []

        # Strictly 168 Clean Test papers as Demo Examples (all 5 real LLM outputs)
        self.examples: Dict[str, ExampleDetail] = {}
        self.example_precomputed_facets: Dict[str, Dict[str, Dict[str, List[Dict]]]] = {}
        self.example_ground_truth: Dict[str, Dict[str, str]] = {}

        # Runtime caches
        self.analyses: Dict[str, AnalysisDetail] = {}
        self.analysis_meta: Dict[str, Dict[str, str]] = {}
        self.jobs: Dict[str, JobResponse] = {}
        self.idempotency_map: Dict[str, CreateAnalysisResponse] = {}
        self.paper_rankings_cache: Dict[str, List[PaperRecommendationItem]] = {}
        self.conf_rankings_cache: Dict[str, List[ConferenceRecommendationItem]] = {}
        self.conf_voting_neighbors: Dict[str, Dict[str, List[Tuple[float, Dict]]]] = {}

        # Sparse TF-IDF precomputed vectors (6 fields)
        self.idf: Dict[str, float] = {}
        self.default_idf: float = 1.0
        self.corpus_tfidf: Dict[str, List[Dict[str, float]]] = {}
        self.conf_train_tfidf: Dict[str, List[Dict[str, float]]] = {}

        # Dense BERT-base-uncased precomputed vectors (6 fields + masks, 768d)
        self.corpus_dense: Dict[str, np.ndarray] = {}
        self.corpus_dense_mask: Dict[str, np.ndarray] = {}
        self.conf_train_dense: Dict[str, np.ndarray] = {}
        self.conf_train_dense_mask: Dict[str, np.ndarray] = {}
        self.conf_centroids_dense: Dict[str, np.ndarray] = {}
        self._dense_model = None

        self._load_demo_artifacts()

    def _cfg_path(self, key: str, default: str) -> Path:
        val = os.environ.get(key) or self.env.get(key) or default
        return resolve_path(self.demo_dir, val)

    def _get_dense_model(self):
        if self._dense_model is None:
            import torch
            from sentence_transformers import SentenceTransformer, models as st_models

            model_path = self._cfg_path("BERT_MODEL_PATH", "../_local/models/bert-base-uncased")
            # Nhường toàn bộ VRAM cho LLM 4-bit trên GPU <= 6GB để tránh tràn sang Shared RAM
            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cuda" and self.model_runner.enable_real_llm:
                try:
                    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                    if vram_gb <= 6.5:
                        device = "cpu"
                except Exception:
                    device = "cpu"

            if model_path.exists() and (model_path / "modules.json").exists():
                self._dense_model = SentenceTransformer(
                    str(model_path),
                    device=device,
                    local_files_only=True,
                    model_kwargs={"local_files_only": True, "low_cpu_mem_usage": False},
                )
            else:
                src_name = str(model_path) if model_path.exists() else "google-bert/bert-base-uncased"
                encoder = st_models.Transformer(
                    src_name,
                    model_args={"low_cpu_mem_usage": False},
                )
                pool = st_models.Pooling(encoder.get_word_embedding_dimension(), pooling_mode="mean")
                self._dense_model = SentenceTransformer(modules=[encoder, pool], device=device)
        return self._dense_model

    def _load_demo_artifacts(self) -> None:
        artifacts_dir = self._cfg_path("DEMO_ARTIFACTS_DIR", "../_local/demo_artifacts")
        corpus_path = artifacts_dir / "paper_corpus.jsonl"
        conf_catalog_path = artifacts_dir / "conference_catalog.json"
        conf_train_path = artifacts_dir / "conference_train_pool.jsonl"
        examples_path = artifacts_dir / "demo_examples.json"

        if not corpus_path.exists() or not examples_path.exists():
            raise RuntimeError(
                f"Không tìm thấy bộ artifacts demo mới tại {artifacts_dir}. "
                "Vui lòng chạy: python demo/script/build_demo_artifacts.py"
            )

        # 1. Load paper_corpus.jsonl (4,210 papers + real 5 facets)
        with corpus_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                p = json.loads(line)
                pid = p["paper_id"]
                self.corpus_pids.append(pid)
                self.papers[pid] = PaperDetail(
                    paper_id=pid,
                    title=p.get("title", ""),
                    abstract=p.get("abstract", ""),
                    authors=p.get("authors") or [],
                    year=p.get("year"),
                    venue=p.get("venue"),
                    source=p.get("source"),
                    in_corpus=True,
                )
                raw_f = p.get("facets") or {}
                self.paper_facets[pid] = {
                    f_key: [str(x).strip() for x in (raw_f.get(f_key) or []) if str(x).strip()]
                    for f_key in FACETS
                }

        # 2. Load conference_catalog.json (30 conferences)
        confs_data = json.loads(conf_catalog_path.read_text(encoding="utf-8"))
        for c in confs_data:
            cid = c["conference_id"]
            self.conf_cids.append(cid)
            self.conferences[cid] = ConferenceDetail(
                conference_id=cid,
                name=c.get("canonical_name", ""),
                acronym=c.get("acronym", ""),
                url=c.get("url"),
                topic_profile_description=c.get("topic_profile_description", ""),
                profile_built_from=c.get("coverage_note", "Hồ sơ tổng hợp từ 602 bài Train (1982–2015)"),
                historical_paper_count=int(c.get("historical_paper_count", 0)),
                year_range=c.get("year_range", "1982–2015"),
                cutoff_note=c.get("cutoff_note"),
                coverage_note=c.get("coverage_note"),
                sparse_profile_warning=c.get("sparse_profile_warning"),
            )
            kw_map = c.get("top_keywords_by_facet") or {}
            self.conf_top_keywords[cid] = {
                f_key: list(kw_map.get(f_key) or []) for f_key in FACETS
            }

        # 3. Load conference_train_pool.jsonl (602 train papers strictly)
        with conf_train_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self.conf_train_pool.append(json.loads(line))

        # 4. Load demo_examples.json (168 clean test papers × 5 real LLMs)
        examples_data = json.loads(examples_path.read_text(encoding="utf-8"))
        for ex in examples_data:
            ex_id = ex["example_id"]
            avail_models = list(ex.get("available_models") or [])
            pre_map = ex.get("precomputed_facets") or {}
            self.example_precomputed_facets[ex_id] = pre_map
            self.example_ground_truth[ex_id] = {
                "conference_id": ex.get("ground_truth_venue_id", ""),
                "acronym": ex.get("ground_truth_venue_acronym", ""),
                "name": ex.get("ground_truth_venue_name", ""),
            }
            self.examples[ex_id] = ExampleDetail(
                example_id=ex_id,
                title=ex.get("title", ""),
                short_label=ex.get("short_label", ""),
                domain=ex.get("domain", "Computer Science"),
                available_models=avail_models,
                abstract=ex.get("abstract", ""),
                default_model_key=ex.get("default_model_key", "Qwen3-4B"),
                precomputed_analyses={mk: f"ana_pre_{ex_id}_{mk}" for mk in avail_models},
            )

        # 5. Load precomputed 6-field BERT-base-uncased dense matrices
        corpus_dense_path = artifacts_dir / "corpus_bert_base_6fields.npz"
        train_dense_path = artifacts_dir / "conf_train_bert_base_6fields.npz"
        centroids_dense_path = artifacts_dir / "conf_centroids_bert_base.npz"

        if corpus_dense_path.exists():
            npz = np.load(corpus_dense_path)
            for field in FIELDS:
                self.corpus_dense[field] = npz[field].astype(np.float32)
                self.corpus_dense_mask[field] = npz[f"mask_{field}"].astype(bool)

        if train_dense_path.exists():
            npz = np.load(train_dense_path)
            for field in FIELDS:
                self.conf_train_dense[field] = npz[field].astype(np.float32)
                self.conf_train_dense_mask[field] = npz[f"mask_{field}"].astype(bool)

        if centroids_dense_path.exists():
            npz = np.load(centroids_dense_path)
            for field in FIELDS:
                self.conf_centroids_dense[field] = npz[field].astype(np.float32)

        # 6. Build shared IDF + sparse TF-IDF vectors for all 6 fields (fast in-memory)
        self._build_tfidf_indices()

    def _build_tfidf_indices(self) -> None:
        df: Counter = Counter()
        total_docs = 0

        # Compute shared IDF over corpus whole_text + 5 facet docs (matches Exp B)
        for pid in self.corpus_pids:
            p = self.papers[pid]
            docs = [f"{p.title} {p.abstract}"]
            f_map = self.paper_facets.get(pid, {})
            for f_key in FACETS:
                txt = " ".join(f_map.get(f_key, []))
                if txt:
                    docs.append(txt)
            for doc in docs:
                toks = set(tokenize(doc))
                if toks:
                    total_docs += 1
                    for t in toks:
                        df[t] += 1

        self.default_idf = math.log((1 + total_docs) / 1.0) + 1.0
        self.idf = {t: math.log((1 + total_docs) / (1 + cnt)) + 1.0 for t, cnt in df.items()}

        self.corpus_tfidf = {field: [] for field in FIELDS}
        for pid in self.corpus_pids:
            p = self.papers[pid]
            f_map = self.paper_facets.get(pid, {})
            self.corpus_tfidf["whole_text"].append(
                build_tfidf_vector(f"{p.title} {p.abstract}", self.idf, self.default_idf)
            )
            for f_key in FACETS:
                txt = " ".join(f_map.get(f_key, []))
                self.corpus_tfidf[f_key].append(
                    build_tfidf_vector(txt, self.idf, self.default_idf) if txt else {}
                )

        self.conf_train_tfidf = {field: [] for field in FIELDS}
        for r in self.conf_train_pool:
            f_map = r.get("facets") or {}
            self.conf_train_tfidf["whole_text"].append(
                build_tfidf_vector(f"{r.get('title', '')} {r.get('abstract', '')}", self.idf, self.default_idf)
            )
            for f_key in FACETS:
                txt = " ".join(f_map.get(f_key, []))
                self.conf_train_tfidf[f_key].append(
                    build_tfidf_vector(txt, self.idf, self.default_idf) if txt else {}
                )

    def _hydrate_precomputed_facets(
        self, raw_model_facets: Dict[str, List[Dict]], title: str, abstract: str
    ) -> Dict[FacetKey, FacetOutput]:
        result: Dict[FacetKey, FacetOutput] = {}
        for f_key in FACETS:
            raw_items = raw_model_facets.get(f_key) or []
            concepts: List[FacetConcept] = []
            for entry in raw_items:
                concept_text = str(entry.get("concept", "")).strip()
                if not concept_text:
                    continue
                ev_spans: List[EvidenceSpan] = []
                for ev in entry.get("evidences") or []:
                    quote = str(ev.get("quote", "")).strip()
                    src = ev.get("source_field", "abstract")
                    if src not in ("title", "abstract"):
                        src = "abstract"
                    target_text = title if src == "title" else abstract
                    if quote:
                        ev_spans.append(make_evidence_span(target_text, quote, src))
                concepts.append(FacetConcept(concept=concept_text, evidences=ev_spans))
            result[f_key] = FacetOutput(
                status="ok" if concepts else "empty",
                items=concepts,
            )
        return result

    def _extract_heuristic_facets(self, title: str, abstract: str) -> Dict[FacetKey, FacetOutput]:
        """Fallback only for LIVE mode when GPU LLM worker is not enabled."""
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", abstract) if s.strip()]
        s0 = sentences[0] if sentences else abstract[:140]
        s1 = sentences[1] if len(sentences) > 1 else ""
        s_last = sentences[-1] if len(sentences) > 2 else ""

        return {
            "problem": FacetOutput(
                status="ok",
                items=[
                    FacetConcept(
                        concept=f"Problem addressed in {title[:60]}",
                        evidences=[make_evidence_span(abstract, s0, "abstract")],
                    )
                ],
            ),
            "task": FacetOutput(
                status="ok",
                items=[
                    FacetConcept(
                        concept=title,
                        evidences=[make_evidence_span(title, title, "title")],
                    )
                ],
            ),
            "method": FacetOutput(
                status="ok" if s1 else "empty",
                items=(
                    [
                        FacetConcept(
                            concept="Methodology described in abstract",
                            evidences=[make_evidence_span(abstract, s1, "abstract")],
                        )
                    ]
                    if s1
                    else []
                ),
            ),
            "dataset": FacetOutput(status="empty", items=[]),
            "contribution": FacetOutput(
                status="ok" if s_last else "empty",
                items=(
                    [
                        FacetConcept(
                            concept="Primary findings and contributions",
                            evidences=[make_evidence_span(abstract, s_last, "abstract")],
                        )
                    ]
                    if s_last
                    else []
                ),
            ),
        }

    def _query_facet_texts(self, analysis: AnalysisDetail) -> Dict[str, str]:
        out: Dict[str, str] = {
            "whole_text": f"{analysis.title.strip()}. {analysis.abstract.strip()}".strip(". ")
        }
        for f_key in FACETS:
            f_out = analysis.facets.get(f_key)
            if f_out and f_out.items:
                out[f_key] = "; ".join(item.concept.strip() for item in f_out.items if item.concept.strip())
            else:
                out[f_key] = ""
        return out

    def _compute_rankings(
        self,
        analysis_id: str,
        embedding_model: str = "tfidf",
        paper_method: str = "whole_text",
        conf_method: str = "whole_text_knn",
    ) -> None:
        analysis = self.analyses[analysis_id]
        q_title_norm = analysis.title.strip().lower()
        q_texts = self._query_facet_texts(analysis)
        has_any_facet = any(bool(q_texts[f]) for f in FACETS)

        emb_low = (embedding_model or "").lower()
        use_dense = (
            ("bert" in emb_low or "dense" in emb_low)
            and bool(self.corpus_dense)
            and bool(self.conf_train_dense)
        )

        if use_dense:
            try:
                self._compute_rankings_dense(
                    analysis_id, q_title_norm, q_texts, has_any_facet, paper_method, conf_method
                )
                return
            except Exception:
                pass

        self._compute_rankings_tfidf(
            analysis_id, q_title_norm, q_texts, has_any_facet, paper_method, conf_method
        )

    def _compute_rankings_dense(
        self,
        analysis_id: str,
        q_title_norm: str,
        q_texts: Dict[str, str],
        has_any_facet: bool,
        paper_method: str,
        conf_method: str,
    ) -> None:
        dense_model = self._get_dense_model()
        q_vecs: Dict[str, Optional[np.ndarray]] = {}
        non_empty_fields = [f for f in FIELDS if q_texts.get(f)]
        if non_empty_fields:
            embs = dense_model.encode(
                [q_texts[f] for f in non_empty_fields],
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            for idx, f in enumerate(non_empty_fields):
                q_vecs[f] = embs[idx].astype(np.float32)
        for f in FIELDS:
            q_vecs.setdefault(f, None)

        # 1. Paper Recommendation (normalized by common PRESENT facets, matching data/exp_b/ranking)
        n_papers = len(self.corpus_pids)
        per_facet_sims: Dict[FacetKey, np.ndarray] = {f: np.zeros(n_papers, dtype=np.float32) for f in FACETS}
        if paper_method == "whole_text" or not has_any_facet:
            qv = q_vecs["whole_text"]
            total_scores = np.clip(self.corpus_dense["whole_text"] @ qv, 0.0, 1.0) if qv is not None else np.zeros(n_papers, dtype=np.float32)
            paper_score_unit = "whole_text_bert_cosine (0–1)"
        else:
            weights = {f: 0.20 for f in FACETS} if paper_method == "equal_facets" else FIXED_WEIGHTS
            weighted_sum = np.zeros(n_papers, dtype=np.float32)
            weight_denom = np.zeros(n_papers, dtype=np.float32)
            for f_key in FACETS:
                qv = q_vecs.get(f_key)
                if qv is not None:
                    raw = np.clip(self.corpus_dense[f_key] @ qv, 0.0, 1.0)
                    valid = self.corpus_dense_mask[f_key]
                    sims = np.where(valid, raw, 0.0)
                    weighted_sum += np.where(valid, weights[f_key] * raw, 0.0)
                    weight_denom += np.where(valid, weights[f_key], 0.0)
                else:
                    sims = np.zeros(n_papers, dtype=np.float32)
                per_facet_sims[f_key] = sims
            total_scores = np.where(weight_denom > 0.0, weighted_sum / np.maximum(weight_denom, 1e-8), 0.0)
            paper_score_unit = (
                "equal_5facet_bert_cosine (0–1)"
                if paper_method == "equal_facets"
                else "weighted_5facet_bert_cosine (0–1)"
            )

        paper_items: List[Tuple[float, PaperRecommendationItem]] = []
        for i, pid in enumerate(self.corpus_pids):
            p = self.papers[pid]
            if p.title.strip().lower() == q_title_norm:
                continue
            sim = float(total_scores[i])
            supporting = sorted(
                [f for f in FACETS if per_facet_sims[f][i] > 0.15],
                key=lambda f: -float(per_facet_sims[f][i]),
            )[:3]
            if not supporting:
                supporting = ["problem", "task", "method"]
            paper_items.append(
                (
                    sim,
                    PaperRecommendationItem(
                        rank=0,
                        paper_id=pid,
                        title=p.title,
                        authors=p.authors,
                        year=p.year,
                        venue=p.venue,
                        total_score=round(sim, 4),
                        score_unit=paper_score_unit,
                        supporting_facets=supporting,
                    ),
                )
            )
        paper_items.sort(key=lambda x: (-x[0], x[1].paper_id))
        ranked_papers: List[PaperRecommendationItem] = []
        for i, (_, item) in enumerate(paper_items[:50], start=1):
            item.rank = i
            ranked_papers.append(item)
        self.paper_rankings_cache[analysis_id] = ranked_papers

        # 2. Conference Recommendation on 602 Train papers
        n_train = len(self.conf_train_pool)
        train_whole_sims = (
            np.clip(self.conf_train_dense["whole_text"] @ q_vecs["whole_text"], 0.0, 1.0)
            if q_vecs["whole_text"] is not None
            else np.zeros(n_train, dtype=np.float32)
        )
        train_facet_sims: Dict[FacetKey, np.ndarray] = {}
        for f_key in FACETS:
            qv = q_vecs.get(f_key)
            if qv is not None:
                raw = np.clip(self.conf_train_dense[f_key] @ qv, 0.0, 1.0)
                train_facet_sims[f_key] = np.where(self.conf_train_dense_mask[f_key], raw, -1.0)
            else:
                train_facet_sims[f_key] = np.full(n_train, -1.0, dtype=np.float32)

        self._rank_conferences_knn(
            analysis_id,
            conf_method=conf_method,
            train_whole_sims=train_whole_sims,
            train_facet_sims=train_facet_sims,
            emb_label="bert",
        )
        self.analysis_meta[analysis_id] = {
            "embedding": "bert-base",
            "paper_method": paper_method,
            "conf_method": conf_method,
            "paper_scorer": f"paper_{paper_method}_bert_base",
            "conf_scorer": f"conf_{conf_method}_bert_base",
        }

    def _compute_rankings_tfidf(
        self,
        analysis_id: str,
        q_title_norm: str,
        q_texts: Dict[str, str],
        has_any_facet: bool,
        paper_method: str,
        conf_method: str,
    ) -> None:
        q_vecs: Dict[str, Dict[str, float]] = {
            field: build_tfidf_vector(q_texts.get(field, ""), self.idf, self.default_idf)
            for field in FIELDS
        }

        # 1. Paper Recommendation
        use_whole = paper_method == "whole_text" or not has_any_facet
        weights = {f: 0.20 for f in FACETS} if paper_method == "equal_facets" else FIXED_WEIGHTS
        paper_score_unit = (
            "whole_text_tfidf_cosine (0–1)"
            if use_whole
            else (
                "equal_5facet_tfidf_cosine (0–1)"
                if paper_method == "equal_facets"
                else "weighted_5facet_tfidf_cosine (0–1)"
            )
        )

        paper_items: List[Tuple[float, PaperRecommendationItem]] = []
        for i, pid in enumerate(self.corpus_pids):
            p = self.papers[pid]
            if p.title.strip().lower() == q_title_norm:
                continue
            if use_whole:
                score = sparse_cosine(q_vecs["whole_text"], self.corpus_tfidf["whole_text"][i])
                supporting = ["problem", "task", "method"]
            else:
                score = 0.0
                facet_scores: Dict[FacetKey, float] = {}
                for f_key in FACETS:
                    s_f = sparse_cosine(q_vecs[f_key], self.corpus_tfidf[f_key][i])
                    facet_scores[f_key] = s_f
                    score += weights[f_key] * s_f
                supporting = sorted(
                    [f for f in FACETS if facet_scores[f] > 0.0],
                    key=lambda f: -facet_scores[f],
                )[:3]

            paper_items.append(
                (
                    score,
                    PaperRecommendationItem(
                        rank=0,
                        paper_id=pid,
                        title=p.title,
                        authors=p.authors,
                        year=p.year,
                        venue=p.venue,
                        total_score=round(score, 4),
                        score_unit=paper_score_unit,
                        supporting_facets=supporting or ["problem", "task", "method"],
                    ),
                )
            )
        paper_items.sort(key=lambda x: (-x[0], x[1].paper_id))
        ranked_papers: List[PaperRecommendationItem] = []
        for i, (_, item) in enumerate(paper_items[:50], start=1):
            item.rank = i
            ranked_papers.append(item)
        self.paper_rankings_cache[analysis_id] = ranked_papers

        # 2. Conference Recommendation on 602 Train papers
        n_train = len(self.conf_train_pool)
        train_whole_sims = np.zeros(n_train, dtype=np.float32)
        if q_vecs["whole_text"]:
            for i in range(n_train):
                train_whole_sims[i] = sparse_cosine(q_vecs["whole_text"], self.conf_train_tfidf["whole_text"][i])

        train_facet_sims: Dict[FacetKey, np.ndarray] = {}
        for f_key in FACETS:
            qv = q_vecs[f_key]
            arr = np.full(n_train, -1.0, dtype=np.float32)
            if qv:
                for i in range(n_train):
                    pv = self.conf_train_tfidf[f_key][i]
                    if pv:
                        arr[i] = sparse_cosine(qv, pv)
            train_facet_sims[f_key] = arr

        self._rank_conferences_knn(
            analysis_id,
            conf_method=conf_method,
            train_whole_sims=train_whole_sims,
            train_facet_sims=train_facet_sims,
            emb_label="tfidf",
        )
        self.analysis_meta[analysis_id] = {
            "embedding": "tfidf",
            "paper_method": paper_method,
            "conf_method": conf_method,
            "paper_scorer": f"paper_{paper_method}_tfidf",
            "conf_scorer": f"conf_{conf_method}_tfidf",
        }

    def _rank_conferences_knn(
        self,
        analysis_id: str,
        conf_method: str,
        train_whole_sims: np.ndarray,
        train_facet_sims: Dict[FacetKey, np.ndarray],
        emb_label: str,
    ) -> None:
        """Supports whole_text_knn, flat_facet_knn (equal 5-facet), and gated_knn (Problem gate)."""
        n_train = len(self.conf_train_pool)
        score_unit = f"{conf_method}_{emb_label} (0–1)"
        neighbor_scores: List[Tuple[float, Dict, List[FacetKey]]] = []

        for i in range(n_train):
            if conf_method == "whole_text_knn":
                sim = float(train_whole_sims[i])
                top_f: List[FacetKey] = ["problem", "task", "method"]
            elif conf_method == "flat_facet_knn":
                vals = []
                contrib_facets: List[Tuple[float, FacetKey]] = []
                for f_key in FACETS:
                    s_f = float(train_facet_sims[f_key][i])
                    if s_f >= 0.0:
                        vals.append(s_f)
                        if s_f > 0.0:
                            contrib_facets.append((s_f, f_key))
                sim = (sum(vals) / len(vals)) if vals else float(train_whole_sims[i])
                top_f = [f for _, f in sorted(contrib_facets, key=lambda x: -x[0])[:3]] or ["problem", "task", "method"]
            else:
                # gated_knn (Problem gate × 4 solution facets)
                prob_sim = float(train_facet_sims["problem"][i])
                gate = 0.5 if prob_sim < 0.0 else sigmoid(CONF_GATE_KAPPA * (prob_sim - CONF_GATE_TAU))
                obs_w = 0.0
                w_sum = 0.0
                contrib_facets = []
                for f_key, w in CONF_SOLUTION_WEIGHTS.items():
                    s_f = float(train_facet_sims[f_key][i])
                    if s_f >= 0.0:
                        w_sum += w * s_f
                        obs_w += w
                        if s_f > 0.0:
                            contrib_facets.append((s_f * w, f_key))
                weighted_sol = (w_sum / obs_w) if obs_w > 0.0 else 0.0
                sim = gate * weighted_sol
                top_f = [f for _, f in sorted(contrib_facets, key=lambda x: -x[0])[:3]]
                if prob_sim > CONF_GATE_TAU and "problem" not in top_f:
                    top_f = ["problem", *top_f[:2]]
                if not top_f:
                    top_f = ["problem", "task", "method"]

            neighbor_scores.append((sim, self.conf_train_pool[i], top_f))

        neighbor_scores.sort(key=lambda x: (-x[0], x[1]["paper_id"]))
        top_k_neighbors = neighbor_scores[:CONF_KNN_K]

        vote_totals: Dict[str, float] = defaultdict(float)
        vote_facets: Dict[str, Counter] = defaultdict(Counter)
        neighbors_by_conf: Dict[str, List[Tuple[float, Dict]]] = defaultdict(list)

        for sim, row, top_f in top_k_neighbors:
            cid = row["conference_id"]
            vote_totals[cid] += sim
            neighbors_by_conf[cid].append((sim, row))
            for f_key in top_f:
                vote_facets[cid][f_key] += 1

        all_by_conf: Dict[str, List[Tuple[float, Dict]]] = defaultdict(list)
        for sim, row, _ in neighbor_scores:
            cid = row["conference_id"]
            if len(all_by_conf[cid]) < 10:
                all_by_conf[cid].append((sim, row))
        self.conf_voting_neighbors[analysis_id] = {
            cid: (neighbors_by_conf[cid] if neighbors_by_conf[cid] else all_by_conf[cid])
            for cid in self.conf_cids
        }

        total_vote_mass = sum(vote_totals.values())
        c_items: List[Tuple[float, ConferenceRecommendationItem]] = []
        for cid in self.conf_cids:
            conf = self.conferences[cid]
            raw_vote = vote_totals.get(cid, 0.0)
            norm_score = (raw_vote / total_vote_mass) if total_vote_mass > 0.0 else 0.0
            best_in_venue = all_by_conf[cid][0][0] if all_by_conf[cid] else 0.0
            display_score = norm_score if raw_vote > 0.0 else round(best_in_venue * 0.1, 4)
            prominent = [f for f, _ in vote_facets[cid].most_common(3)] or ["problem", "task", "method"]
            c_items.append(
                (
                    display_score,
                    ConferenceRecommendationItem(
                        rank=0,
                        conference_id=cid,
                        name=conf.name,
                        acronym=conf.acronym,
                        match_score=round(display_score, 4),
                        score_unit=score_unit,
                        prominent_facets=prominent,
                        historical_paper_count=conf.historical_paper_count,
                    ),
                )
            )
        c_items.sort(key=lambda x: (-x[0], x[1].conference_id))
        ranked_confs: List[ConferenceRecommendationItem] = []
        for i, (_, item) in enumerate(c_items, start=1):
            item.rank = i
            ranked_confs.append(item)
        self.conf_rankings_cache[analysis_id] = ranked_confs

    def get_health(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            api_version="v1",
            mode="fastapi-adapter",
            session_id=self.session_id,
        )

    def get_models(self) -> List[ModelInfo]:
        return self.models

    def get_runtime(self) -> RuntimeStatus:
        self.runtime.resident_models = self.model_runner.get_resident_models()
        if self.model_runner.enable_real_llm:
            self.runtime.loaded_model_key = self.model_runner.loaded_model_key
        return self.runtime

    async def start_load_model(self, model_key: str) -> LoadModelResponse:
        model = next((m for m in self.models if m.model_key == model_key), None)
        if not model:
            raise ValueError(f"Model không hợp lệ: {model_key}")
        if not model.supported:
            raise ValueError(model.unavailable_reason or f"Model {model_key} chưa được tải về máy cục bộ.")

        target_gpu = self.model_runner.get_model_gpu(model_key)
        gpu_busy_reason = self.model_runner.get_gpu_busy_reason(target_gpu)
        if gpu_busy_reason:
            raise ValueError(
                f"GPU {target_gpu} hiện {gpu_busy_reason}. Không thể nạp hoặc chuyển sang {model_key} trên GPU {target_gpu} lúc này — vui lòng đợi tác vụ hiện tại hoàn tất."
            )

        job_id = f"job_load_{uuid.uuid4().hex[:8]}"
        resident_map = self.model_runner.get_resident_models()
        is_pool_hit = model_key in resident_map
        self.runtime.intended_model_key = model_key
        self.runtime.worker_busy = True
        self.runtime.current_task = (
            f"Đang chuyển nhanh sang {model_key} (0s)"
            if is_pool_hit
            else f"Đang nạp {model_key} lên GPU {target_gpu}"
        )
        self.jobs[job_id] = JobResponse(
            job_id=job_id,
            job_type="load_model",
            status="running",
            stage="loading_model",
            stage_label=(
                f"Đang chuyển nhanh sang {model_key} (GPU {resident_map[model_key]})..."
                if is_pool_hit
                else f"Đang nạp {model_key} lên GPU {target_gpu}..."
            ),
            model_key=model_key,
        )

        async def _finish_load() -> None:
            try:
                await asyncio.to_thread(self.model_runner.load_model, model_key)
                self.runtime.loaded_model_key = model_key
                self.runtime.intended_model_key = model_key
                self.runtime.resident_models = self.model_runner.get_resident_models()
                self.runtime.last_error = None
                gid = self.runtime.resident_models.get(model_key, target_gpu)
                self.jobs[job_id] = JobResponse(
                    job_id=job_id,
                    job_type="load_model",
                    status="completed",
                    stage="completed",
                    stage_label=(
                        f"Đã chuyển nhanh sang {model_key} (0s • GPU {gid})"
                        if is_pool_hit
                        else f"Đã nạp {model_key} lên GPU {gid}"
                    ),
                    model_key=model_key,
                )
            except Exception as exc:
                self.runtime.resident_models = self.model_runner.get_resident_models()
                self.runtime.loaded_model_key = self.model_runner.loaded_model_key
                self.runtime.intended_model_key = self.model_runner.loaded_model_key
                self.runtime.last_error = str(exc)
                self.jobs[job_id] = JobResponse(
                    job_id=job_id,
                    job_type="load_model",
                    status="failed",
                    stage="failed",
                    stage_label=f"Lỗi nạp {model_key}",
                    model_key=model_key,
                    error=JobError(code="LOAD_MODEL_FAILED", message=str(exc), retryable=True),
                )
            finally:
                self.runtime.worker_busy = False
                self.runtime.current_task = None

        asyncio.create_task(_finish_load())
        return LoadModelResponse(job_id=job_id, intended_model_key=model_key, status="queued")

    def get_examples(self) -> List[ExampleSummary]:
        return [
            ExampleSummary(
                example_id=e.example_id,
                title=e.title,
                short_label=e.short_label,
                domain=e.domain,
                available_models=e.available_models,
            )
            for e in self.examples.values()
        ]

    def get_example(self, example_id: str) -> Optional[ExampleDetail]:
        if example_id in self.examples:
            return self.examples[example_id]
        alt_id = f"ex_{example_id.lower()}"
        if alt_id in self.examples:
            return self.examples[alt_id]
        return None

    async def create_analysis(self, req: CreateAnalysisRequest) -> CreateAnalysisResponse:
        if req.idempotency_key and req.idempotency_key in self.idempotency_map:
            return self.idempotency_map[req.idempotency_key]

        title = req.title.strip()
        abstract = req.abstract.strip()
        if not title or not abstract:
            raise ValueError("Title và Abstract đều bắt buộc.")

        embedding_model = getattr(req, "embedding_model", "tfidf") or "tfidf"
        paper_method = getattr(req, "paper_ranking_method", "whole_text") or "whole_text"
        conf_method = getattr(req, "conference_ranking_method", "whole_text_knn") or "whole_text_knn"
        needs_facets = not (paper_method == "whole_text" and conf_method == "whole_text_knn")

        if req.mode == "precomputed":
            matched_ex = None
            for ex in self.examples.values():
                if ex.title.strip().lower() == title.lower() and ex.abstract.strip().lower() == abstract.lower():
                    matched_ex = ex
                    break
            if not matched_ex:
                raise ValueError(
                    "Chế độ Mẫu có sẵn chỉ áp dụng cho 168 bài mẫu Test khớp nguyên văn (không dùng dữ liệu giả lập)."
                )

            raw_model_facets = self.example_precomputed_facets.get(matched_ex.example_id, {}).get(req.model_key)
            if raw_model_facets is None:
                raise ValueError(
                    f"Chưa có kết quả tính trước từ LLM thật cho model {req.model_key} với bài mẫu này."
                )

            emb_tag = "bert" if ("bert" in embedding_model.lower() or "dense" in embedding_model.lower()) else "tfidf"
            ana_id = f"ana_pre_{matched_ex.example_id}_{req.model_key}_{emb_tag}_{paper_method}_{conf_method}"
            if ana_id not in self.analyses:
                t_r0 = time.perf_counter()
                facets = self._hydrate_precomputed_facets(raw_model_facets, title, abstract)
                model_info = next((m for m in self.models if m.model_key == req.model_key), None)
                self.analyses[ana_id] = AnalysisDetail(
                    analysis_id=ana_id,
                    title=title,
                    abstract=abstract,
                    extraction_status="completed",
                    paper_ranking_status="completed",
                    conference_ranking_status="completed",
                    facets=facets,
                    provenance=AnalysisProvenance(
                        model_key=req.model_key,
                        model_display_name=model_info.display_name if model_info else req.model_key,
                        source="precomputed",
                        prompt_version="exp_a_qlora_real",
                        adapter_version="ds300-demo-artifacts-2.0",
                        session_id=self.session_id,
                        created_at=datetime.now(timezone.utc).isoformat(),
                    ),
                    timings=AnalysisTimings(model_load_ms=0, extraction_ms=0, ranking_ms=0),
                )
                self._compute_rankings(
                    ana_id,
                    embedding_model=embedding_model,
                    paper_method=paper_method,
                    conf_method=conf_method,
                )
                self.analyses[ana_id].timings.ranking_ms = max(1, int((time.perf_counter() - t_r0) * 1000))

            job_id = f"job_pre_{uuid.uuid4().hex[:8]}"
            self.jobs[job_id] = JobResponse(
                job_id=job_id,
                job_type="analysis",
                status="completed",
                stage="completed",
                stage_label=f"Hoàn tất (dữ liệu LLM thật: {req.model_key})",
                analysis_id=ana_id,
                model_key=req.model_key,
            )
            resp = CreateAnalysisResponse(
                analysis_id=ana_id,
                job_id=job_id,
                status="completed",
            )
            if req.idempotency_key:
                self.idempotency_map[req.idempotency_key] = resp
            return resp

        # Fast-path for Explore KB papers (when use_kb_cache=True and paper is already in 4,210 KB)
        if req.use_kb_cache and needs_facets:
            title_low = title.lower()
            matched_kb_pid = None
            for pid, p_obj in self.papers.items():
                if p_obj.title.strip().lower() == title_low:
                    matched_kb_pid = pid
                    break
            if matched_kb_pid and matched_kb_pid in self.paper_facets:
                emb_tag = "bert" if ("bert" in embedding_model.lower() or "dense" in embedding_model.lower()) else "tfidf"
                ana_id = f"ana_kb_{matched_kb_pid.lower()}_{emb_tag}_{paper_method}_{conf_method}"
                if ana_id not in self.analyses:
                    t_r0 = time.perf_counter()
                    raw_f = {
                        f: [{"concept": c, "evidences": []} for c in self.paper_facets[matched_kb_pid].get(f, [])]
                        for f in FACETS
                    }
                    facets = self._hydrate_precomputed_facets(raw_f, title, abstract)
                    self.analyses[ana_id] = AnalysisDetail(
                        analysis_id=ana_id,
                        title=title,
                        abstract=abstract,
                        extraction_status="completed",
                        paper_ranking_status="completed",
                        conference_ranking_status="completed",
                        facets=facets,
                        provenance=AnalysisProvenance(
                            model_key="Qwen3-4B",
                            model_display_name="Qwen3-4B-Instruct (KB)",
                            source="cache",
                            prompt_version="exp_a_qlora_real",
                            adapter_version="ds300-demo-artifacts-2.0",
                            session_id=self.session_id,
                            created_at=datetime.now(timezone.utc).isoformat(),
                        ),
                        timings=AnalysisTimings(model_load_ms=0, extraction_ms=0, ranking_ms=1),
                    )
                    self._compute_rankings(
                        ana_id,
                        embedding_model=embedding_model,
                        paper_method=paper_method,
                        conf_method=conf_method,
                    )
                    self.analyses[ana_id].timings.ranking_ms = max(1, int((time.perf_counter() - t_r0) * 1000))
                job_id = f"job_kb_{uuid.uuid4().hex[:8]}"
                self.jobs[job_id] = JobResponse(
                    job_id=job_id,
                    job_type="analysis",
                    status="completed",
                    stage="completed",
                    stage_label="Hoàn tất (dữ liệu 5-Facet có sẵn trong kho)",
                    analysis_id=ana_id,
                    model_key="Qwen3-4B",
                )
                return CreateAnalysisResponse(
                    analysis_id=ana_id,
                    job_id=job_id,
                    status="completed",
                )

        # Live mode (quy tắc: chỉ suy luận trên model đã thực sự nằm trong VRAM và GPU đó KHÔNG đang nạp/bận)
        if needs_facets:
            target_gpu = self.model_runner.get_model_gpu(req.model_key)
            loading_mk = self.model_runner.get_loading_model_on_gpu(target_gpu)
            if loading_mk:
                raise ValueError(
                    f"GPU {target_gpu} đang bận nạp model {loading_mk}. Không được phép suy luận trên GPU {target_gpu} trong lúc đang nạp model — vui lòng đợi nạp xong hoặc chuyển sang model ở GPU khác."
                )
            gpu_busy_reason = self.model_runner.get_gpu_busy_reason(target_gpu)
            if gpu_busy_reason:
                raise ValueError(
                    f"GPU {target_gpu} hiện {gpu_busy_reason}. Vui lòng đợi hoàn tất rồi thử lại."
                )
            resident_map = self.model_runner.get_resident_models()
            if self.model_runner.enable_real_llm:
                if req.model_key not in resident_map:
                    raise ValueError(
                        f"Model {req.model_key} chưa được nạp trong VRAM (GPU {target_gpu}). Vui lòng mở nút 'Hệ thống' ở góc trên phải để nạp model trước khi phân tích."
                    )
            elif self.runtime.loaded_model_key != req.model_key:
                raise ValueError(
                    f"Model {req.model_key} chưa được nạp (hiện tại: {self.runtime.loaded_model_key})."
                )

        analysis_id = f"ana_{uuid.uuid4().hex[:10]}"
        job_id = f"job_{uuid.uuid4().hex[:10]}"

        model_info = next((m for m in self.models if m.model_key == req.model_key), None)
        self.analyses[analysis_id] = AnalysisDetail(
            analysis_id=analysis_id,
            title=title,
            abstract=abstract,
            extraction_status="running" if needs_facets else "completed",
            paper_ranking_status="pending",
            conference_ranking_status="pending",
            facets={f: FacetOutput(status="not_analyzed", items=[]) for f in FACETS},
            provenance=AnalysisProvenance(
                model_key=req.model_key if needs_facets else "Whole-Text (No LLM)",
                model_display_name=(
                    (model_info.display_name if model_info else req.model_key)
                    if needs_facets
                    else "Toàn văn (Không trích Facet)"
                ),
                source="live",
                prompt_version="v3.7-source-first" if needs_facets else "whole-text-direct",
                adapter_version="ds300-demo-artifacts-2.0",
                session_id=self.session_id,
                created_at=datetime.now(timezone.utc).isoformat(),
            ),
            timings=AnalysisTimings(),
        )

        self.jobs[job_id] = JobResponse(
            job_id=job_id,
            job_type="analysis",
            status="queued",
            stage="queued",
            stage_label="Đang chờ trong hàng đợi...",
            analysis_id=analysis_id,
            model_key=req.model_key,
        )

        async def _run_pipeline() -> None:
            ana = self.analyses[analysis_id]
            self.runtime.worker_busy = True
            self.runtime.current_task = f"Đang phân tích ({req.model_key})"
            try:
                if needs_facets:
                    t0 = time.perf_counter()
                    self.jobs[job_id] = JobResponse(
                        job_id=job_id,
                        job_type="analysis",
                        status="running",
                        stage="extracting",
                        stage_label=(
                            f"Đang chạy {req.model_key} trên GPU trích xuất 5 facet..."
                            if self.model_runner.enable_real_llm
                            else "Đang trích xuất 5 facet..."
                        ),
                        analysis_id=analysis_id,
                        model_key=req.model_key,
                    )
                    facets = await asyncio.to_thread(
                        self.model_runner.extract_facets, title, abstract, req.model_key
                    )
                    ana.facets = facets
                    ana.extraction_status = "completed"
                    ana.timings.extraction_ms = int((time.perf_counter() - t0) * 1000)
                else:
                    ana.timings.extraction_ms = 0

                self.jobs[job_id] = JobResponse(
                    job_id=job_id,
                    job_type="analysis",
                    status="running",
                    stage="ranking",
                    stage_label="Đang xếp hạng bài báo & hội nghị...",
                    analysis_id=analysis_id,
                    model_key=req.model_key,
                )
                t_r0 = time.perf_counter()
                await asyncio.to_thread(
                    self._compute_rankings,
                    analysis_id,
                    embedding_model,
                    paper_method,
                    conf_method,
                )
                ana.paper_ranking_status = "completed"
                ana.conference_ranking_status = "completed"
                ana.timings.ranking_ms = max(1, int((time.perf_counter() - t_r0) * 1000))

                self.jobs[job_id] = JobResponse(
                    job_id=job_id,
                    job_type="analysis",
                    status="completed",
                    stage="completed",
                    stage_label="Hoàn tất phân tích và xếp hạng",
                    analysis_id=analysis_id,
                    model_key=req.model_key,
                )
            except Exception as exc:
                self.runtime.last_error = str(exc)
                ana.extraction_status = "failed"
                ana.extraction_error = str(exc)
                ana.paper_ranking_status = "failed"
                ana.conference_ranking_status = "failed"
                self.jobs[job_id] = JobResponse(
                    job_id=job_id,
                    job_type="analysis",
                    status="failed",
                    stage="failed",
                    stage_label=f"Lỗi xử lý: {exc}",
                    analysis_id=analysis_id,
                    model_key=req.model_key,
                    error=JobError(code="ANALYSIS_FAILED", message=str(exc), retryable=True),
                )
            finally:
                self.runtime.worker_busy = False
                self.runtime.current_task = None

        asyncio.create_task(_run_pipeline())
        resp = CreateAnalysisResponse(analysis_id=analysis_id, job_id=job_id, status="queued")
        if req.idempotency_key:
            self.idempotency_map[req.idempotency_key] = resp
        return resp

    def get_job(self, job_id: str) -> Optional[JobResponse]:
        return self.jobs.get(job_id)

    def get_analysis(self, analysis_id: str) -> Optional[AnalysisDetail]:
        return self.analyses.get(analysis_id)

    def get_paper_rankings(self, analysis_id: str, top_k: int) -> Optional[PaperRankingResponse]:
        if analysis_id not in self.analyses:
            return None
        items = self.paper_rankings_cache.get(analysis_id, [])
        meta = self.analysis_meta.get(analysis_id, {})
        emb = meta.get("embedding", "tfidf")
        p_method = meta.get("paper_method", "whole_text")
        notes = {
            "whole_text": f"Toàn văn (Whole-Text): so sánh trực tiếp Title + Abstract trên 4,210 bài corpus ({emb}).",
            "equal_facets": f"5-Facet Trọng số đều (Equal 0.2 × 5) trên 4,210 bài corpus ({emb}).",
            "weighted_facets": f"5-Facet Có trọng số (problem 0.4, task 0.2, method 0.2, dataset 0.1, contribution 0.1) trên 4,210 bài corpus ({emb}).",
        }
        return PaperRankingResponse(
            analysis_id=analysis_id,
            status=self.analyses[analysis_id].paper_ranking_status,
            scorer_name=meta.get("paper_scorer", f"paper_{p_method}_{emb}"),
            score_unit=f"{p_method}_{emb}_cosine (0–1)",
            scorer_note=notes.get(p_method, notes["whole_text"]),
            top_k=top_k,
            total_available=len(items),
            items=items[:top_k],
        )

    def get_conference_rankings(
        self, analysis_id: str, top_k: int
    ) -> Optional[ConferenceRankingResponse]:
        if analysis_id not in self.analyses:
            return None
        items = self.conf_rankings_cache.get(analysis_id, [])
        meta = self.analysis_meta.get(analysis_id, {})
        emb = meta.get("embedding", "tfidf")
        c_method = meta.get("conf_method", "whole_text_knn")
        disclaimers = {
            "whole_text_knn": "Toàn văn k-NN (Top-10 bỏ phiếu theo Title + Abstract từ 602 bài Train 1982–2015). Điểm biểu diễn mức phù hợp nội dung, không phải xác suất nhận bài.",
            "flat_facet_knn": "5-Facet Trọng số đều k-NN (cộng phẳng 5 facet, Top-10 bỏ phiếu từ 602 bài Train 1982–2015). Điểm biểu diễn mức phù hợp nội dung, không phải xác suất nhận bài.",
            "gated_knn": "Gated 5-Facet k-NN (cổng Problem τ=0.45, κ=10; Top-10 bỏ phiếu từ 602 bài Train 1982–2015). Điểm biểu diễn mức phù hợp nội dung, không phải xác suất nhận bài.",
        }
        return ConferenceRankingResponse(
            analysis_id=analysis_id,
            status=self.analyses[analysis_id].conference_ranking_status,
            scorer_name=meta.get("conf_scorer", f"conf_{c_method}_{emb}"),
            score_unit=f"{c_method}_{emb} (0–1)",
            disclaimer=disclaimers.get(c_method, disclaimers["whole_text_knn"]),
            top_k=top_k,
            total_available=len(items),
            items=items[:top_k],
        )

    def get_paper(self, paper_id: str) -> Optional[PaperDetail]:
        return self.papers.get(paper_id)

    def get_paper_explanation(
        self, analysis_id: str, paper_id: str
    ) -> Optional[PaperExplanationResponse]:
        ana = self.analyses.get(analysis_id)
        paper = self.papers.get(paper_id)
        if not ana or not paper:
            return None

        ranked = self.paper_rankings_cache.get(analysis_id, [])
        rec = next((r for r in ranked if r.paper_id == paper_id), None)
        target_f_map = self.paper_facets.get(paper_id, {})
        meta = self.analysis_meta.get(analysis_id, {})

        breakdowns: List[FacetAlignmentBreakdown] = []
        calc_total = 0.0
        for f_key in FACETS:
            q_out = ana.facets[f_key]
            q_text = " ".join(c.concept for c in q_out.items)
            t_concepts_raw = target_f_map.get(f_key, [])
            t_text = " ".join(t_concepts_raw)
            q_vec = build_tfidf_vector(q_text, self.idf, self.default_idf) if q_text else {}
            t_vec = build_tfidf_vector(t_text, self.idf, self.default_idf) if t_text else {}
            sim = sparse_cosine(q_vec, t_vec) if (q_vec and t_vec) else 0.0
            w = FIXED_WEIGHTS[f_key]
            contrib = round(sim * w, 4)
            calc_total += contrib

            target_concepts = [
                FacetConcept(concept=c, evidences=[])
                for c in t_concepts_raw[:5]
            ]
            breakdowns.append(
                FacetAlignmentBreakdown(
                    facet=f_key,
                    query_concepts=q_out.items,
                    target_concepts=target_concepts,
                    query_status=q_out.status,
                    target_status="ok" if target_concepts else "empty",
                    similarity_score=sim,
                    weight=w,
                    contribution_score=contrib,
                )
            )

        total = rec.total_score if rec else round(calc_total, 4)
        return PaperExplanationResponse(
            analysis_id=analysis_id,
            paper_id=paper_id,
            total_score=total,
            score_unit=rec.score_unit if rec else "weighted_facet_tfidf_cosine (0–1)",
            scorer_name=meta.get("paper_scorer", "exp_b_weighted_facets_tfidf"),
            formula_description="Tổng có trọng số độ tương đồng trên 5 facet (problem 0.4, task 0.2, method 0.2, dataset 0.1, contribution 0.1).",
            summary_explanation=f'Bài báo "{paper.title}" đạt điểm tổng {total:.3f} (thang 0–1) từ đối chiếu 5 facet thực tế.',
            facet_breakdowns=breakdowns,
        )

    def get_conference(self, conference_id: str) -> Optional[ConferenceDetail]:
        return self.conferences.get(conference_id)

    def get_conference_explanation(
        self, analysis_id: str, conference_id: str
    ) -> Optional[ConferenceExplanationResponse]:
        ana = self.analyses.get(analysis_id)
        conf = self.conferences.get(conference_id)
        if not ana or not conf:
            return None

        ranked = self.conf_rankings_cache.get(analysis_id, [])
        rec = next((r for r in ranked if r.conference_id == conference_id), None)
        score = rec.match_score if rec else 0.0
        meta = self.analysis_meta.get(analysis_id, {})
        kw_map = self.conf_top_keywords.get(conference_id, {})

        facet_scores: List[ConferenceFacetScore] = []
        for f_key in FACETS:
            q_out = ana.facets[f_key]
            q_text = " ".join(c.concept for c in q_out.items)
            profile_kws = kw_map.get(f_key, [])[:6]
            p_text = " ".join(profile_kws)
            q_vec = build_tfidf_vector(q_text, self.idf, self.default_idf) if q_text else {}
            p_vec = build_tfidf_vector(p_text, self.idf, self.default_idf) if p_text else {}
            sim = sparse_cosine(q_vec, p_vec) if (q_vec and p_vec) else 0.0
            w = CONF_SOLUTION_WEIGHTS.get(f_key, 0.0) if f_key != "problem" else 1.0
            facet_scores.append(
                ConferenceFacetScore(
                    facet=f_key,
                    query_concepts=q_out.items,
                    profile_keywords=profile_kws,
                    similarity_score=sim,
                    weight=w,
                    contribution_score=round(sim * w, 4),
                )
            )

        c_method = meta.get("conf_method", "whole_text_knn")
        formula_map = {
            "whole_text_knn": "Toàn văn k-NN: So sánh trực tiếp Title + Abstract với 602 bài Train (1982–2015), lấy Top-10 láng giềng gần nhất bỏ phiếu có trọng số.",
            "flat_facet_knn": "5-Facet Trọng số đều k-NN: Trung bình đều độ tương đồng trên 5 facet (không cổng ngữ cảnh), lấy Top-10 bài Train bỏ phiếu có trọng số.",
            "gated_knn": "Gated 5-Facet k-NN: Cổng Problem σ(10·(cos_prob - 0.45)) × tổng trọng số 4 facet giải pháp (task 0.3, method 0.3, dataset 0.2, contribution 0.2), bỏ phiếu Top-10 từ 602 bài Train.",
        }
        method_label_map = {
            "whole_text_knn": "Toàn văn k-NN",
            "flat_facet_knn": "5-Facet Trọng số đều k-NN",
            "gated_knn": "Gated 5-Facet k-NN",
        }
        return ConferenceExplanationResponse(
            analysis_id=analysis_id,
            conference_id=conference_id,
            match_score=score,
            score_unit=rec.score_unit if rec else f"{c_method} (0–1)",
            scorer_name=meta.get("conf_scorer", f"conf_{c_method}_tfidf"),
            formula_description=formula_map.get(c_method, formula_map["whole_text_knn"]),
            disclaimer="Điểm số biểu diễn tỷ trọng phiếu bầu mức phù hợp nội dung, KHÔNG phải xác suất nhận bài.",
            summary_explanation=f"Hội nghị {conf.acronym} đạt điểm phù hợp {score:.3f} dựa trên bỏ phiếu láng giềng {method_label_map.get(c_method, c_method)} trong tập 602 bài Train.",
            sparse_profile_warning=conf.sparse_profile_warning,
            facet_scores=facet_scores,
        )

    def get_representative_papers(
        self, analysis_id: str, conference_id: str, limit: int
    ) -> Optional[RepresentativePapersResponse]:
        if analysis_id not in self.analyses or conference_id not in self.conferences:
            return None

        neighbors = self.conf_voting_neighbors.get(analysis_id, {}).get(conference_id, [])
        items: List[RepresentativePaperItem] = []
        for sim, row in neighbors[:limit]:
            pid = row["paper_id"]
            p = self.papers.get(pid)
            abstract = row.get("abstract") or (p.abstract if p else "")
            items.append(
                RepresentativePaperItem(
                    paper_id=pid,
                    in_corpus=pid in self.papers,
                    title=row.get("title") or (p.title if p else ""),
                    year=row.get("year") or (p.year if p else None),
                    authors=p.authors if p else [],
                    url=p.url if p else None,
                    abstract=abstract,
                    supporting_facets=["problem", "task", "method"],
                    evidences=[make_evidence_span(abstract, abstract[:160], "abstract")] if abstract else [],
                    selection_rule=f"gated_5facet_knn_neighbor (sim={sim:.3f})",
                )
            )

        return RepresentativePapersResponse(
            analysis_id=analysis_id,
            conference_id=conference_id,
            selection_rule="top_gated_5facet_knn_train_neighbors",
            note="Các bài báo lịch sử dưới đây thuộc tập 602 bài Train (1982–2015) của chính hội nghị này, được chọn vì có độ tương đồng Gated 5-Facet cao nhất với manuscript.",
            items=items,
        )
