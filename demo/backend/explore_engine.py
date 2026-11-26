from __future__ import annotations

import asyncio
import json
import math
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from schemas import (
    ExploreConferenceItem,
    ExploreOpenPaperRequest,
    ExploreOpenPaperResponse,
    ExplorePaperItem,
    ExploreProfileItem,
    ExploreProfileResponse,
    ExploreProfileSyncRequest,
    ExploreRecommendationItem,
    ExploreRecommendationsResponse,
    ExploreSearchResponse,
    FacetKey,
)
from service import (
    CONF_GATE_KAPPA,
    CONF_GATE_TAU,
    CONF_KNN_K,
    CONF_SOLUTION_WEIGHTS,
    build_tfidf_vector,
    sigmoid,
)

FACETS: List[FacetKey] = ["problem", "task", "method", "dataset", "contribution"]
FIELDS: List[str] = ["whole_text", *FACETS]

FIXED_WEIGHTS: Dict[FacetKey, float] = {
    "problem": 0.40,
    "task": 0.20,
    "method": 0.20,
    "dataset": 0.10,
    "contribution": 0.10,
}


def reconstruct_openalex_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    pos_to_word: Dict[int, str] = {}
    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        for pos in positions:
            pos_to_word[int(pos)] = word
    if not pos_to_word:
        return ""
    max_pos = max(pos_to_word.keys())
    return " ".join(pos_to_word.get(i, "") for i in range(max_pos + 1)).strip()


def _tokenize_simple(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) >= 2]


def _pack_vectors(vecs: Dict[str, np.ndarray], dim: int = 768) -> bytes:
    arr = np.zeros((len(FIELDS), dim), dtype=np.float32)
    for i, f in enumerate(FIELDS):
        v = vecs.get(f)
        if v is not None and v.shape == (dim,):
            arr[i] = v.astype(np.float32)
    return arr.tobytes()


def _unpack_vectors(blob: Optional[bytes], dim: int = 768) -> Dict[str, np.ndarray]:
    if not blob:
        return {f: np.zeros(dim, dtype=np.float32) for f in FIELDS}
    arr = np.frombuffer(blob, dtype=np.float32)
    if arr.size != len(FIELDS) * dim:
        return {f: np.zeros(dim, dtype=np.float32) for f in FIELDS}
    arr = arr.reshape((len(FIELDS), dim))
    return {f: arr[i].copy() for i, f in enumerate(FIELDS)}


class ExploreEngine:
    """Shopee-style Hybrid Paper Search + 5-Facet Mean-Vector User Profile Engine.

    Syncs 100% with data/exp_b/ranking:
    - Encoders: google-bert/bert-base-uncased (768d, mean pooling, L2-normalized) + TF-IDF baseline
    - PRESENT-facet masking for both mean user profile and normalized cosine aggregation
    - Persistent SQLite storage for cached external papers and per-user reading profiles
    """

    def __init__(self, service: Any, db_path: Path) -> None:
        self.service = service
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.dim = 768
        if self.service.corpus_dense.get("whole_text") is not None:
            self.dim = int(self.service.corpus_dense["whole_text"].shape[1])

        # Precompute lowercase title index for instant local search
        self._pid_to_idx: Dict[str, int] = {
            pid: i for i, pid in enumerate(self.service.corpus_pids)
        }
        self._local_search_index: List[Tuple[str, str, set[str], Optional[int]]] = []
        for pid in self.service.corpus_pids:
            p = self.service.papers[pid]
            t_low = p.title.strip().lower()
            toks = set(_tokenize_simple(f"{p.title} {p.venue or ''}"))
            self._local_search_index.append((pid, t_low, toks, p.year))

        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cached_papers (
                    paper_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    abstract TEXT NOT NULL,
                    authors_json TEXT NOT NULL,
                    year INTEGER,
                    venue TEXT,
                    url TEXT,
                    cited_by_count INTEGER,
                    source TEXT NOT NULL,
                    facets_json TEXT NOT NULL,
                    extraction_source TEXT NOT NULL,
                    bert_vecs_blob BLOB,
                    bert_masks_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS profile_interactions (
                    user_id TEXT NOT NULL,
                    paper_id TEXT NOT NULL,
                    analysis_id TEXT,
                    title TEXT NOT NULL,
                    abstract TEXT NOT NULL,
                    authors_json TEXT NOT NULL,
                    year INTEGER,
                    venue TEXT,
                    url TEXT,
                    source TEXT NOT NULL,
                    facets_json TEXT NOT NULL,
                    extraction_source TEXT NOT NULL,
                    bert_vecs_blob BLOB,
                    bert_masks_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, paper_id)
                )
                """
            )
            # Safe migration for existing SQLite databases created before analysis_id was added
            cols = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(profile_interactions)").fetchall()
            }
            if "analysis_id" not in cols:
                conn.execute("ALTER TABLE profile_interactions ADD COLUMN analysis_id TEXT")
            conn.commit()

    # ------------------------------------------------------------------
    # 1. Hybrid Search (Local 4,210 KB + Cached + Live OpenAlex up to present)
    # ------------------------------------------------------------------
    def _search_local(self, query: str, limit: int) -> List[ExplorePaperItem]:
        q_low = query.strip().lower()
        q_toks = _tokenize_simple(q_low)
        if not q_low:
            return []

        scored: List[Tuple[float, ExplorePaperItem]] = []
        seen_titles: set[str] = set()

        # Check cached external papers first
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM cached_papers ORDER BY created_at DESC").fetchall()
        for r in rows:
            t_low = (r["title"] or "").strip().lower()
            t_toks = set(_tokenize_simple(r["title"]))
            score = 0.0
            if q_low in t_low:
                score += 3.0 + (1.0 if t_low.startswith(q_low) else 0.0)
            if q_toks:
                overlap = sum(1 for t in q_toks if t in t_toks) / len(q_toks)
                score += 2.0 * overlap
            if score >= 0.8:
                seen_titles.add(t_low)
                abstract = r["abstract"] or ""
                scored.append(
                    (
                        score,
                        ExplorePaperItem(
                            paper_id=r["paper_id"],
                            title=r["title"],
                            abstract=abstract,
                            abstract_snippet=abstract[:240] + ("..." if len(abstract) > 240 else ""),
                            authors=json.loads(r["authors_json"] or "[]"),
                            year=r["year"],
                            venue=r["venue"],
                            url=r["url"],
                            cited_by_count=r["cited_by_count"],
                            source="cached",
                            has_facets=True,
                        ),
                    )
                )

        # Search 4,210 local corpus papers
        for pid, t_low, t_toks, year in self._local_search_index:
            if t_low in seen_titles:
                continue
            score = 0.0
            if q_low in t_low:
                score += 3.0 + (1.0 if t_low.startswith(q_low) else 0.0)
            if q_toks:
                overlap = sum(1 for t in q_toks if t in t_toks) / len(q_toks)
                score += 2.0 * overlap
            if score < 0.75:
                continue
            p = self.service.papers[pid]
            abstract = p.abstract or ""
            scored.append(
                (
                    score,
                    ExplorePaperItem(
                        paper_id=pid,
                        title=p.title,
                        abstract=abstract,
                        abstract_snippet=abstract[:240] + ("..." if len(abstract) > 240 else ""),
                        authors=p.authors,
                        year=year,
                        venue=p.venue,
                        url=p.url,
                        cited_by_count=None,
                        source="local",
                        has_facets=True,
                    ),
                )
            )

        scored.sort(key=lambda x: (-x[0], -(x[1].year or 0), x[1].paper_id))
        return [item for _, item in scored[:limit]]

    def _search_openalex_sync(self, query: str, limit: int) -> Tuple[List[ExplorePaperItem], Optional[str]]:
        if not query.strip():
            return [], None
        params = urllib.parse.urlencode(
            {
                "search": query.strip(),
                "filter": "has_abstract:true,primary_topic.field.id:fields/17",
                "per-page": str(min(max(limit, 5), 20)),
                "select": "id,title,abstract_inverted_index,publication_year,authorships,primary_location,cited_by_count,doi",
            }
        )
        url = f"https://api.openalex.org/works?{params}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "DS300-FacetRec-Demo/1.0 (academic research demo)",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=4.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            return [], f"OpenAlex tạm thời không phản hồi ({exc.__class__.__name__})"

        items: List[ExplorePaperItem] = []
        for w in data.get("results", []):
            title = (w.get("title") or "").strip()
            if not title:
                continue
            abstract = reconstruct_openalex_abstract(w.get("abstract_inverted_index"))
            if not abstract:
                continue
            oa_raw_id = (w.get("id") or "").rsplit("/", 1)[-1]
            if not oa_raw_id:
                continue
            paper_id = f"OA_{oa_raw_id}"
            authors = []
            for a in (w.get("authorships") or [])[:5]:
                name = (a.get("author") or {}).get("display_name")
                if name:
                    authors.append(name)
            venue = None
            pl = w.get("primary_location") or {}
            src = pl.get("source") or {}
            if src.get("display_name"):
                venue = str(src["display_name"])
            paper_url = w.get("doi") or pl.get("landing_page_url") or w.get("id")
            items.append(
                ExplorePaperItem(
                    paper_id=paper_id,
                    title=title,
                    abstract=abstract,
                    abstract_snippet=abstract[:240] + ("..." if len(abstract) > 240 else ""),
                    authors=authors,
                    year=w.get("publication_year"),
                    venue=venue,
                    url=paper_url,
                    cited_by_count=w.get("cited_by_count"),
                    source="openalex",
                    has_facets=False,
                )
            )
        return items[:limit], None

    async def search(
        self,
        query: str,
        limit: int = 12,
        include_external: bool = True,
        scope: str = "all",
    ) -> ExploreSearchResponse:
        t0 = time.perf_counter()
        q = query.strip()
        if not q:
            return ExploreSearchResponse(
                query="",
                total=0,
                local_count=0,
                external_count=0,
                latency_ms=0.0,
                items=[],
            )

        effective_scope = (scope or "all").lower()
        if not include_external and effective_scope == "all":
            effective_scope = "local"

        local_items: List[ExplorePaperItem] = []
        external_items: List[ExplorePaperItem] = []
        external_warning: Optional[str] = None

        if effective_scope in ("all", "local"):
            local_items = self._search_local(q, limit=limit)

        if effective_scope in ("all", "external"):
            external_items, external_warning = await asyncio.to_thread(
                self._search_openalex_sync, q, limit
            )

        # Interleave / merge with title deduplication (keep newer OpenAlex + Local)
        seen_titles = {it.title.strip().lower() for it in local_items}
        unique_ext = [
            it for it in external_items if it.title.strip().lower() not in seen_titles
        ]

        # Present balanced mix: up to half local, half OpenAlex (or fill from whichever has more)
        merged: List[ExplorePaperItem] = []
        if effective_scope == "local":
            merged = local_items[:limit]
        elif effective_scope == "external":
            merged = external_items[:limit]
        elif unique_ext and local_items:
            half = max(1, limit // 2)
            merged.extend(unique_ext[:half])
            merged.extend(local_items[: limit - len(merged)])
            if len(merged) < limit:
                used_ids = {m.paper_id for m in merged}
                for it in unique_ext + local_items:
                    if it.paper_id not in used_ids and len(merged) < limit:
                        merged.append(it)
                        used_ids.add(it.paper_id)
        else:
            merged = (local_items + unique_ext)[:limit]

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        return ExploreSearchResponse(
            query=q,
            total=len(merged),
            local_count=sum(1 for x in merged if x.source in ("local", "cached")),
            external_count=sum(1 for x in merged if x.source == "openalex"),
            external_warning=external_warning,
            latency_ms=elapsed_ms,
            items=merged,
        )

    # ------------------------------------------------------------------
    # 2. Open Paper -> Extract 5 Facets -> Encode BERT -> Save Profile -> Related Papers
    # ------------------------------------------------------------------
    def _encode_6fields_single(
        self, title: str, abstract: str, facets: Dict[FacetKey, List[str]]
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, bool]]:
        texts_map: Dict[str, str] = {
            "whole_text": f"{title.strip()}. {abstract.strip()}".strip(". ")
        }
        for f in FACETS:
            concepts = [c.strip() for c in facets.get(f, []) if c and c.strip()]
            texts_map[f] = "; ".join(concepts)

        non_empty = [f for f in FIELDS if texts_map[f]]
        vecs: Dict[str, np.ndarray] = {f: np.zeros(self.dim, dtype=np.float32) for f in FIELDS}
        masks: Dict[str, bool] = {f: False for f in FIELDS}

        if non_empty:
            model = self.service._get_dense_model()
            embs = model.encode(
                [texts_map[f] for f in non_empty],
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            for idx, f in enumerate(non_empty):
                vecs[f] = embs[idx].astype(np.float32)
                masks[f] = True
        return vecs, masks

    def _extract_facets_for_external(
        self, title: str, abstract: str, use_llm: bool
    ) -> Tuple[Dict[FacetKey, List[str]], str]:
        if use_llm and self.service.model_runner.enable_real_llm:
            try:
                model_key = self.service.model_runner.loaded_model_key or "Qwen3-4B"
                if not self.service.model_runner.loaded_model_key:
                    self.service.model_runner.load_model(model_key)
                raw = self.service.model_runner.extract_facets(title, abstract, model_key)
                facets_out: Dict[FacetKey, List[str]] = {}
                for f in FACETS:
                    fo = raw.get(f)
                    if fo is not None and hasattr(fo, "items"):
                        facets_out[f] = [
                            item.concept.strip()
                            for item in fo.items
                            if getattr(item, "concept", "").strip()
                        ]
                    else:
                        facets_out[f] = []
                return facets_out, model_key
            except Exception:
                pass

        # Fast heuristic extraction (when LLM not loaded or user chooses instant preview)
        h_out = self.service._extract_heuristic_facets(title, abstract)
        facets_out = {
            f: [item.concept for item in h_out[f].items if item.concept.strip()]
            for f in FACETS
        }
        return facets_out, "heuristic_fast"

    def preview_paper(self, paper_id: str, user_id: str = "") -> Optional[Dict[str, Any]]:
        """Read-only preview of a paper from Local KB or cached_papers without mutating profile."""
        pid = paper_id.strip()
        in_profile = False
        if user_id.strip():
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT 1 FROM profile_interactions WHERE user_id = ? AND paper_id = ?",
                    (user_id.strip(), pid),
                ).fetchone()
                in_profile = row is not None

        if pid in self.service.papers:
            p = self.service.papers[pid]
            abstract = p.abstract or ""
            return {
                "paper": ExplorePaperItem(
                    paper_id=pid,
                    title=p.title,
                    abstract=abstract,
                    abstract_snippet=abstract[:240] + ("..." if len(abstract) > 240 else ""),
                    authors=p.authors,
                    year=p.year,
                    venue=p.venue,
                    url=p.url,
                    cited_by_count=None,
                    source="local",
                    has_facets=True,
                ),
                "in_profile": in_profile,
                "is_analyzed": in_profile,
            }

        with self._connect() as conn:
            cached = conn.execute(
                "SELECT * FROM cached_papers WHERE paper_id = ?", (pid,)
            ).fetchone()
        if cached is not None:
            abstract = cached["abstract"] or ""
            return {
                "paper": ExplorePaperItem(
                    paper_id=pid,
                    title=cached["title"],
                    abstract=abstract,
                    abstract_snippet=abstract[:240] + ("..." if len(abstract) > 240 else ""),
                    authors=json.loads(cached["authors_json"] or "[]"),
                    year=cached["year"],
                    venue=cached["venue"],
                    url=cached["url"],
                    cited_by_count=cached["cited_by_count"],
                    source="cached",
                    has_facets=cached["extraction_source"] != "heuristic_fast",
                ),
                "in_profile": in_profile,
                "is_analyzed": in_profile and cached["extraction_source"] != "heuristic_fast",
            }
        return None

    async def open_paper(self, req: ExploreOpenPaperRequest) -> ExploreOpenPaperResponse:
        t0 = time.perf_counter()
        pid = req.paper_id.strip()

        title = (req.title or "").strip()
        abstract = (req.abstract or "").strip()
        authors = list(req.authors or [])
        year = req.year
        venue = req.venue
        url = req.url
        cited_by_count = req.cited_by_count
        source = req.source or "local"

        facets: Dict[FacetKey, List[str]] = {f: [] for f in FACETS}
        extraction_source = "precomputed_kb"
        vecs: Dict[str, np.ndarray] = {}
        masks: Dict[str, bool] = {}

        # Case A: Paper exists in Local 4,210 KB
        if pid in self.service.papers:
            p = self.service.papers[pid]
            idx = self._pid_to_idx[pid]
            title = p.title
            abstract = p.abstract
            authors = p.authors
            year = p.year
            venue = p.venue
            url = p.url
            source = "local"
            facets = {f: list(self.service.paper_facets.get(pid, {}).get(f, [])) for f in FACETS}
            extraction_source = "Qwen3-4B (KB)"
            for f in FIELDS:
                vecs[f] = self.service.corpus_dense[f][idx].astype(np.float32)
                masks[f] = bool(self.service.corpus_dense_mask[f][idx])
        else:
            # Case B: Check cached_papers SQLite table
            with self._connect() as conn:
                cached = conn.execute(
                    "SELECT * FROM cached_papers WHERE paper_id = ?", (pid,)
                ).fetchone()

            need_reextract = cached is None or (
                req.use_llm and cached["extraction_source"] == "heuristic_fast"
            )

            if not need_reextract and cached is not None:
                title = cached["title"]
                abstract = cached["abstract"]
                authors = json.loads(cached["authors_json"] or "[]")
                year = cached["year"]
                venue = cached["venue"]
                url = cached["url"]
                cited_by_count = cached["cited_by_count"]
                source = "cached"
                facets = json.loads(cached["facets_json"] or "{}")
                for f in FACETS:
                    facets.setdefault(f, [])
                extraction_source = cached["extraction_source"]
                vecs = _unpack_vectors(cached["bert_vecs_blob"], self.dim)
                masks = json.loads(cached["bert_masks_json"] or "{}")
                for f in FIELDS:
                    masks.setdefault(f, False)
            else:
                # Case C: Brand-new external paper (OpenAlex) -> extract 5 facets + encode BERT
                if not title:
                    raise ValueError("Thiếu tiêu đề bài báo để phân tích.")
                facets, extraction_source = await asyncio.to_thread(
                    self._extract_facets_for_external, title, abstract, req.use_llm
                )
                vecs, masks = await asyncio.to_thread(
                    self._encode_6fields_single, title, abstract, facets
                )
                now_iso = datetime.now(timezone.utc).isoformat()
                with self._connect() as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO cached_papers (
                            paper_id, title, abstract, authors_json, year, venue, url,
                            cited_by_count, source, facets_json, extraction_source,
                            bert_vecs_blob, bert_masks_json, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            pid,
                            title,
                            abstract,
                            json.dumps(authors, ensure_ascii=False),
                            year,
                            venue,
                            url,
                            cited_by_count,
                            source,
                            json.dumps(facets, ensure_ascii=False),
                            extraction_source,
                            _pack_vectors(vecs, self.dim),
                            json.dumps(masks),
                            now_iso,
                        ),
                    )
                    conn.commit()

        # Save to User Profile Storage if requested
        if req.add_to_profile and req.user_id.strip():
            now_iso = datetime.now(timezone.utc).isoformat()
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO profile_interactions (
                        user_id, paper_id, title, abstract, authors_json, year, venue, url,
                        source, facets_json, extraction_source, bert_vecs_blob, bert_masks_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        req.user_id.strip(),
                        pid,
                        title,
                        abstract,
                        json.dumps(authors, ensure_ascii=False),
                        year,
                        venue,
                        url,
                        source,
                        json.dumps(facets, ensure_ascii=False),
                        extraction_source,
                        _pack_vectors(vecs, self.dim),
                        json.dumps(masks),
                        now_iso,
                    ),
                )
                conn.commit()

        # Compute Item-to-Item related papers from the 4,210 KB
        related, _ = self._rank_against_kb_bert(
            query_vecs=vecs,
            query_masks=masks,
            exclude_ids={pid},
            exclude_titles={title.strip().lower()},
            method=req.method,
            top_k=req.top_k,
        )

        # Compute related conferences via Gated 5-Facet k-NN on 602 Train papers
        related_confs = self._rank_conferences_bert(
            query_vecs=vecs,
            query_masks=masks,
            top_k=5,
        )

        profile_count = 0
        if req.user_id.strip():
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) AS c FROM profile_interactions WHERE user_id = ?",
                    (req.user_id.strip(),),
                ).fetchone()
                profile_count = int(row["c"]) if row else 0

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        return ExploreOpenPaperResponse(
            paper=ExplorePaperItem(
                paper_id=pid,
                title=title,
                abstract=abstract,
                abstract_snippet=abstract[:240] + ("..." if len(abstract) > 240 else ""),
                authors=authors,
                year=year,
                venue=venue,
                url=url,
                cited_by_count=cited_by_count,
                source=source,
                has_facets=True,
            ),
            facets=facets,
            facet_masks={f: bool(masks.get(f, False)) for f in FACETS},
            extraction_source=extraction_source,
            added_to_profile=bool(req.add_to_profile and req.user_id.strip()),
            profile_count=profile_count,
            latency_ms=elapsed_ms,
            related_papers=related,
            related_conferences=related_confs,
        )

    def _rank_conferences_bert(
        self,
        query_vecs: Dict[str, np.ndarray],
        query_masks: Dict[str, bool],
        top_k: int = 5,
    ) -> List[ExploreConferenceItem]:
        """Rank top-K conferences for the currently viewed paper using Gated 5-Facet k-NN."""
        n_train = len(self.service.conf_train_pool)
        if n_train == 0 or not self.service.conf_train_dense:
            return []

        whole_qv = query_vecs.get("whole_text")
        whole_sims = (
            np.clip(self.service.conf_train_dense["whole_text"] @ whole_qv, 0.0, 1.0)
            if whole_qv is not None and query_masks.get("whole_text", False)
            else np.zeros(n_train, dtype=np.float32)
        )

        facet_sims: Dict[FacetKey, np.ndarray] = {}
        for f in FACETS:
            if query_masks.get(f, False):
                raw = np.clip(self.service.conf_train_dense[f] @ query_vecs[f], 0.0, 1.0)
                facet_sims[f] = np.where(self.service.conf_train_dense_mask[f], raw, -1.0)
            else:
                facet_sims[f] = np.full(n_train, -1.0, dtype=np.float32)

        has_any_facet = any(query_masks.get(f, False) for f in FACETS)
        neighbor_scores: List[Tuple[float, int]] = []
        for i in range(n_train):
            if not has_any_facet:
                score = float(whole_sims[i])
            else:
                prob_s = float(facet_sims["problem"][i])
                gate = sigmoid(CONF_GATE_KAPPA * (prob_s - CONF_GATE_TAU)) if prob_s >= 0.0 else 0.5
                sol_num = 0.0
                sol_den = 0.0
                for sf, w in CONF_SOLUTION_WEIGHTS.items():
                    s_val = float(facet_sims[sf][i])
                    if s_val >= 0.0:
                        sol_num += w * s_val
                        sol_den += w
                sol = (sol_num / sol_den) if sol_den > 0.0 else float(whole_sims[i])
                score = gate * sol
            neighbor_scores.append((score, i))

        neighbor_scores.sort(key=lambda x: -x[0])
        top_neighbors = neighbor_scores[:CONF_KNN_K]

        cid_votes: Dict[str, int] = {}
        cid_score_sum: Dict[str, float] = {}
        cid_facet_acc: Dict[str, Dict[FacetKey, List[float]]] = {}

        for sc, idx in top_neighbors:
            row = self.service.conf_train_pool[idx]
            cid = row["conference_id"]
            cid_votes[cid] = cid_votes.get(cid, 0) + 1
            cid_score_sum[cid] = cid_score_sum.get(cid, 0.0) + sc
            if cid not in cid_facet_acc:
                cid_facet_acc[cid] = {f: [] for f in FACETS}
            for f in FACETS:
                val = float(facet_sims[f][idx])
                if val >= 0.0:
                    cid_facet_acc[cid][f].append(val)

        ranked_cids = sorted(
            cid_score_sum.keys(),
            key=lambda c: (-cid_score_sum[c], -cid_votes[c], c),
        )
        max_sum = max(cid_score_sum.values()) if cid_score_sum else 1.0
        max_sum = max(max_sum, 1e-6)

        out: List[ExploreConferenceItem] = []
        for rank_idx, cid in enumerate(ranked_cids[:top_k], start=1):
            conf = self.service.conferences.get(cid)
            if not conf:
                continue
            avg_by_f = {
                f: (sum(vals) / len(vals) if vals else 0.0)
                for f, vals in cid_facet_acc[cid].items()
            }
            supporting = sorted(
                [f for f in FACETS if avg_by_f[f] > 0.20],
                key=lambda f: -avg_by_f[f],
            )[:3]
            if not supporting:
                supporting = ["problem", "task", "method"]
            # Normalized display match score (avg neighbor similarity * vote confidence)
            avg_sim = cid_score_sum[cid] / max(cid_votes[cid], 1)
            norm_score = min(1.0, 0.6 * avg_sim + 0.4 * (cid_score_sum[cid] / max_sum))
            out.append(
                ExploreConferenceItem(
                    rank=rank_idx,
                    conference_id=cid,
                    acronym=conf.acronym,
                    canonical_name=conf.name,
                    match_score=round(float(norm_score), 4),
                    vote_count=cid_votes[cid],
                    homepage_url=conf.url,
                    supporting_facets=supporting,
                )
            )
        return out

    # ------------------------------------------------------------------
    # 3. User Profile Retrieval & Reset
    # ------------------------------------------------------------------
    async def sync_analysis_to_profile(
        self, req: ExploreProfileSyncRequest
    ) -> ExploreProfileResponse:
        """Sync any completed analysis (from Explore or Manuscript) into the unified User Profile."""
        uid = req.user_id.strip() or "default_user"
        pid = (req.paper_id or req.analysis_id).strip()
        title = req.title.strip()
        abstract = req.abstract.strip()

        clean_facets: Dict[FacetKey, List[str]] = {
            f: [c.strip() for c in (req.facets.get(f) or []) if c and c.strip()]
            for f in FACETS
        }

        # Reuse precomputed BERT vectors if paper_id matches Local KB; otherwise encode
        vecs: Dict[str, np.ndarray] = {}
        masks: Dict[str, bool] = {}
        matched_kb_pid = pid if pid in self._pid_to_idx else None
        if not matched_kb_pid:
            t_low = title.lower()
            for kb_pid, p_obj in self.service.papers.items():
                if p_obj.title.strip().lower() == t_low:
                    matched_kb_pid = kb_pid
                    break

        if matched_kb_pid and matched_kb_pid in self._pid_to_idx:
            idx = self._pid_to_idx[matched_kb_pid]
            for f in FIELDS:
                vecs[f] = self.service.corpus_dense[f][idx].astype(np.float32)
                masks[f] = bool(self.service.corpus_dense_mask[f][idx])
        else:
            vecs, masks = await asyncio.to_thread(
                self._encode_6fields_single, title, abstract, clean_facets
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO profile_interactions (
                    user_id, paper_id, analysis_id, title, abstract, authors_json, year, venue, url,
                    source, facets_json, extraction_source, bert_vecs_blob, bert_masks_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uid,
                    pid,
                    req.analysis_id,
                    title,
                    abstract,
                    "[]",
                    req.year,
                    req.venue,
                    None,
                    req.source,
                    json.dumps(clean_facets, ensure_ascii=False),
                    req.extraction_source,
                    _pack_vectors(vecs, self.dim),
                    json.dumps(masks),
                    now_iso,
                ),
            )
            conn.commit()
        return self.get_profile(uid)

    def get_profile(self, user_id: str) -> ExploreProfileResponse:
        uid = user_id.strip()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT paper_id, analysis_id, title, year, venue, source, facets_json, extraction_source, bert_masks_json, created_at
                FROM profile_interactions
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (uid,),
            ).fetchall()

        items: List[ExploreProfileItem] = []
        facet_counters: Dict[FacetKey, Counter] = {f: Counter() for f in FACETS}
        facet_coverage: Dict[FacetKey, int] = {f: 0 for f in FACETS}

        for r in rows:
            f_dict = json.loads(r["facets_json"] or "{}")
            m_dict = json.loads(r["bert_masks_json"] or "{}")
            clean_facets: Dict[FacetKey, List[str]] = {}
            for f in FACETS:
                vals = [str(x).strip() for x in (f_dict.get(f) or []) if str(x).strip()]
                clean_facets[f] = vals
                if m_dict.get(f, bool(vals)):
                    facet_coverage[f] += 1
                for c in vals:
                    facet_counters[f][c] += 1

            items.append(
                ExploreProfileItem(
                    paper_id=r["paper_id"],
                    analysis_id=r["analysis_id"],
                    title=r["title"],
                    year=r["year"],
                    venue=r["venue"],
                    source=r["source"],
                    extraction_source=r["extraction_source"],
                    facets=clean_facets,
                    created_at=r["created_at"],
                )
            )

        top_concepts: Dict[FacetKey, List[str]] = {
            f: [c for c, _ in facet_counters[f].most_common(6)] for f in FACETS
        }

        return ExploreProfileResponse(
            user_id=uid,
            paper_count=len(items),
            facet_coverage=facet_coverage,
            top_concepts=top_concepts,
            items=items,
        )

    def delete_profile(self, user_id: str, paper_id: Optional[str] = None) -> ExploreProfileResponse:
        uid = user_id.strip()
        with self._connect() as conn:
            if paper_id:
                conn.execute(
                    "DELETE FROM profile_interactions WHERE user_id = ? AND paper_id = ?",
                    (uid, paper_id.strip()),
                )
            else:
                conn.execute("DELETE FROM profile_interactions WHERE user_id = ?", (uid,))
            conn.commit()
        return self.get_profile(uid)

    # ------------------------------------------------------------------
    # 4. Personalized Recommendations (5-Facet Mean Vector -> Cosine vs KB)
    # ------------------------------------------------------------------
    def _rank_against_kb_bert(
        self,
        query_vecs: Dict[str, np.ndarray],
        query_masks: Dict[str, bool],
        exclude_ids: set[str],
        exclude_titles: set[str],
        method: str = "weighted_facets",
        top_k: int = 18,
        offset: int = 0,
    ) -> Tuple[List[ExploreRecommendationItem], bool]:
        n_papers = len(self.service.corpus_pids)
        per_facet_sims: Dict[FacetKey, np.ndarray] = {
            f: np.zeros(n_papers, dtype=np.float32) for f in FACETS
        }
        has_any_facet = any(query_masks.get(f, False) for f in FACETS)

        if method == "whole_text" or not has_any_facet:
            qv = query_vecs.get("whole_text")
            if qv is not None and query_masks.get("whole_text", False):
                total_scores = np.clip(self.service.corpus_dense["whole_text"] @ qv, 0.0, 1.0)
            else:
                total_scores = np.zeros(n_papers, dtype=np.float32)
        else:
            weights = {f: 0.20 for f in FACETS} if method == "equal_facets" else FIXED_WEIGHTS
            weighted_sum = np.zeros(n_papers, dtype=np.float32)
            weight_denom = np.zeros(n_papers, dtype=np.float32)
            for f in FACETS:
                if query_masks.get(f, False):
                    qv = query_vecs[f]
                    raw = np.clip(self.service.corpus_dense[f] @ qv, 0.0, 1.0)
                    valid = self.service.corpus_dense_mask[f]
                    sims = np.where(valid, raw, 0.0)
                    weighted_sum += np.where(valid, weights[f] * raw, 0.0)
                    weight_denom += np.where(valid, weights[f], 0.0)
                else:
                    sims = np.zeros(n_papers, dtype=np.float32)
                per_facet_sims[f] = sims
            total_scores = np.where(
                weight_denom > 0.0, weighted_sum / np.maximum(weight_denom, 1e-8), 0.0
            )

        sorted_indices = np.argsort(-total_scores)
        out: List[ExploreRecommendationItem] = []
        valid_seen = 0
        has_more = False

        for idx in sorted_indices:
            i = int(idx)
            pid = self.service.corpus_pids[i]
            if pid in exclude_ids:
                continue
            p = self.service.papers[pid]
            if p.title.strip().lower() in exclude_titles:
                continue
            if valid_seen < offset:
                valid_seen += 1
                continue
            if len(out) >= top_k:
                has_more = True
                break
            valid_seen += 1

            score = float(total_scores[i])
            f_scores = {f: round(float(per_facet_sims[f][i]), 4) for f in FACETS}
            supporting = sorted(
                [f for f in FACETS if f_scores[f] > 0.20],
                key=lambda f: -f_scores[f],
            )[:3]
            if not supporting:
                supporting = ["problem", "task", "method"]

            abstract = p.abstract or ""
            out.append(
                ExploreRecommendationItem(
                    rank=offset + len(out) + 1,
                    paper_id=pid,
                    title=p.title,
                    abstract_snippet=abstract[:220] + ("..." if len(abstract) > 220 else ""),
                    authors=p.authors,
                    year=p.year,
                    venue=p.venue,
                    url=p.url,
                    source="local",
                    total_score=round(score, 4),
                    per_facet_scores=f_scores,
                    supporting_facets=supporting,
                    facets=self.service.paper_facets.get(pid, {f: [] for f in FACETS}),
                )
            )
        return out, has_more

    def _rank_against_kb_tfidf(
        self,
        profile_rows: List[sqlite3.Row],
        exclude_ids: set[str],
        exclude_titles: set[str],
        method: str = "weighted_facets",
        top_k: int = 18,
        offset: int = 0,
    ) -> Tuple[List[ExploreRecommendationItem], bool]:
        # Build mean TF-IDF profile vector per field across read papers
        mean_vecs: Dict[str, Dict[str, float]] = {}
        has_field: Dict[str, bool] = {}

        for field in FIELDS:
            acc: Dict[str, float] = {}
            count = 0
            for r in profile_rows:
                if field == "whole_text":
                    txt = f"{r['title']}. {r['abstract']}"
                else:
                    f_dict = json.loads(r["facets_json"] or "{}")
                    txt = "; ".join(f_dict.get(field) or [])
                if not txt.strip():
                    continue
                vec = build_tfidf_vector(txt, self.service.idf, self.service.default_idf)
                if not vec:
                    continue
                count += 1
                for tok, w in vec.items():
                    acc[tok] = acc.get(tok, 0.0) + w
            if count > 0 and acc:
                norm = math.sqrt(sum(v * v for v in acc.values())) or 1.0
                mean_vecs[field] = {k: v / norm for k, v in acc.items()}
                has_field[field] = True
            else:
                mean_vecs[field] = {}
                has_field[field] = False

        def dot_sparse(a: Dict[str, float], b: Dict[str, float]) -> float:
            if not a or not b:
                return 0.0
            if len(a) > len(b):
                a, b = b, a
            return sum(v * b[k] for k, v in a.items() if k in b)

        has_any_facet = any(has_field[f] for f in FACETS)
        weights = {f: 0.20 for f in FACETS} if method == "equal_facets" else FIXED_WEIGHTS
        scored: List[Tuple[float, Dict[FacetKey, float], int]] = []

        for i, pid in enumerate(self.service.corpus_pids):
            if pid in exclude_ids:
                continue
            p = self.service.papers[pid]
            if p.title.strip().lower() in exclude_titles:
                continue

            f_scores: Dict[FacetKey, float] = {f: 0.0 for f in FACETS}
            if method == "whole_text" or not has_any_facet:
                total = dot_sparse(mean_vecs["whole_text"], self.service.corpus_tfidf["whole_text"][i])
            else:
                w_sum = 0.0
                w_den = 0.0
                for f in FACETS:
                    doc_vec = self.service.corpus_tfidf[f][i]
                    if has_field[f] and doc_vec:
                        s = dot_sparse(mean_vecs[f], doc_vec)
                        f_scores[f] = round(s, 4)
                        w_sum += weights[f] * s
                        w_den += weights[f]
                total = (w_sum / w_den) if w_den > 0 else 0.0
            scored.append((total, f_scores, i))

        scored.sort(key=lambda x: -x[0])
        has_more = (offset + top_k) < len(scored)
        out: List[ExploreRecommendationItem] = []
        for total, f_scores, i in scored[offset : offset + top_k]:
            pid = self.service.corpus_pids[i]
            p = self.service.papers[pid]
            supporting = sorted(
                [f for f in FACETS if f_scores[f] > 0.05],
                key=lambda f: -f_scores[f],
            )[:3]
            if not supporting:
                supporting = ["problem", "task", "method"]
            abstract = p.abstract or ""
            out.append(
                ExploreRecommendationItem(
                    rank=offset + len(out) + 1,
                    paper_id=pid,
                    title=p.title,
                    abstract_snippet=abstract[:220] + ("..." if len(abstract) > 220 else ""),
                    authors=p.authors,
                    year=p.year,
                    venue=p.venue,
                    url=p.url,
                    source="local",
                    total_score=round(float(total), 4),
                    per_facet_scores=f_scores,
                    supporting_facets=supporting,
                    facets=self.service.paper_facets.get(pid, {f: [] for f in FACETS}),
                )
            )
        return out, has_more

    def get_recommendations(
        self,
        user_id: str,
        embedding: str = "bert-base",
        method: str = "weighted_facets",
        top_k: int = 18,
        offset: int = 0,
    ) -> ExploreRecommendationsResponse:
        t0 = time.perf_counter()
        uid = user_id.strip()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM profile_interactions WHERE user_id = ? ORDER BY created_at DESC",
                (uid,),
            ).fetchall()

        corpus_size = len(self.service.corpus_pids)

        # Cold-start: user hasn't read any papers yet -> paginate through diverse KB papers
        if not rows:
            starter_items: List[ExploreRecommendationItem] = []
            valid_seen = 0
            has_more = False
            for pid in self.service.corpus_pids:
                pf = self.service.paper_facets.get(pid, {})
                if valid_seen < offset:
                    valid_seen += 1
                    continue
                if len(starter_items) >= top_k:
                    has_more = True
                    break
                valid_seen += 1
                p = self.service.papers[pid]
                abstract = p.abstract or ""
                starter_items.append(
                    ExploreRecommendationItem(
                        rank=offset + len(starter_items) + 1,
                        paper_id=pid,
                        title=p.title,
                        abstract_snippet=abstract[:220] + ("..." if len(abstract) > 220 else ""),
                        authors=p.authors,
                        year=p.year,
                        venue=p.venue,
                        url=p.url,
                        source="local",
                        total_score=0.0,
                        per_facet_scores={f: 0.0 for f in FACETS},
                        supporting_facets=[f for f in FACETS if pf.get(f)][:3],
                        facets=pf,
                    )
                )

            return ExploreRecommendationsResponse(
                user_id=uid,
                mode="cold_start",
                embedding=embedding,
                method=method,
                profile_size=0,
                corpus_size=corpus_size,
                offset=offset,
                has_more=has_more,
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 1),
                items=starter_items,
            )

        exclude_ids = {r["paper_id"] for r in rows}
        exclude_titles = {(r["title"] or "").strip().lower() for r in rows}

        use_tfidf = "tfidf" in (embedding or "").lower()
        if use_tfidf:
            items, has_more = self._rank_against_kb_tfidf(
                profile_rows=rows,
                exclude_ids=exclude_ids,
                exclude_titles=exclude_titles,
                method=method,
                top_k=top_k,
                offset=offset,
            )
            emb_used = "tfidf"
        else:
            # Compute 5-Facet Mean Vector User Profile (averaging only PRESENT facets, then L2-normalizing)
            mean_vecs: Dict[str, np.ndarray] = {}
            mean_masks: Dict[str, bool] = {}
            for field in FIELDS:
                acc = np.zeros(self.dim, dtype=np.float32)
                cnt = 0
                for r in rows:
                    m_dict = json.loads(r["bert_masks_json"] or "{}")
                    if not m_dict.get(field, False):
                        continue
                    v_dict = _unpack_vectors(r["bert_vecs_blob"], self.dim)
                    vec = v_dict[field]
                    if np.linalg.norm(vec) > 0:
                        acc += vec
                        cnt += 1
                if cnt > 0:
                    mean_v = acc / float(cnt)
                    norm = float(np.linalg.norm(mean_v))
                    mean_vecs[field] = (mean_v / norm).astype(np.float32) if norm > 0 else acc
                    mean_masks[field] = norm > 0
                else:
                    mean_vecs[field] = acc
                    mean_masks[field] = False

            items, has_more = self._rank_against_kb_bert(
                query_vecs=mean_vecs,
                query_masks=mean_masks,
                exclude_ids=exclude_ids,
                exclude_titles=exclude_titles,
                method=method,
                top_k=top_k,
                offset=offset,
            )
            emb_used = "bert-base"

        return ExploreRecommendationsResponse(
            user_id=uid,
            mode="personalized",
            embedding=emb_used,
            method=method,
            profile_size=len(rows),
            corpus_size=corpus_size,
            offset=offset,
            has_more=has_more,
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 1),
            items=items,
        )
