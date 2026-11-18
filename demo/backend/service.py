from __future__ import annotations

import asyncio
import json
import math
import re
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
FIXED_WEIGHTS: Dict[FacetKey, float] = {
    "problem": 0.25,
    "task": 0.20,
    "method": 0.25,
    "dataset": 0.15,
    "contribution": 0.15,
}


def python_idx_to_utf16_offset(text: str, py_idx: int) -> int:
    """Convert Python string index to JS UTF-16 code unit offset."""
    return len(text[:py_idx].encode("utf-16-le")) // 2


def make_evidence_span(text: str, quote: str, source_field: str) -> EvidenceSpan:
    idx = text.find(quote)
    if idx == -1:
        return EvidenceSpan(
            quote=quote,
            source_field=source_field,  # type: ignore[arg-type]
            start_offset=None,
            end_offset=None,
            verified=False,
        )
    start_u16 = python_idx_to_utf16_offset(text, idx)
    end_u16 = python_idx_to_utf16_offset(text, idx + len(quote))
    return EvidenceSpan(
        quote=quote,
        source_field=source_field,  # type: ignore[arg-type]
        start_offset=start_u16,
        end_offset=end_u16,
        verified=True,
    )


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


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
        self.models: List[ModelInfo] = [
            ModelInfo(
                model_key="Qwen3-4B",
                display_name="Qwen3-4B-Instruct",
                family="Qwen3",
                parameter_size="4B",
                supported=True,
                precomputed_available=True,
                ranking_artifacts_ready=True,
            ),
            ModelInfo(
                model_key="Qwen3-8B",
                display_name="Qwen3-8B-Instruct",
                family="Qwen3",
                parameter_size="8B",
                supported=True,
                precomputed_available=True,
                ranking_artifacts_ready=True,
            ),
            ModelInfo(
                model_key="Qwen3-14B",
                display_name="Qwen3-14B-Instruct",
                family="Qwen3",
                parameter_size="14B",
                supported=True,
                precomputed_available=True,
                ranking_artifacts_ready=True,
            ),
            ModelInfo(
                model_key="Llama3.1-8B",
                display_name="Llama-3.1-8B-Instruct",
                family="Llama 3.1",
                parameter_size="8B",
                supported=True,
                precomputed_available=True,
                ranking_artifacts_ready=True,
            ),
            ModelInfo(
                model_key="Gemma2-9B",
                display_name="Gemma-2-9B-IT",
                family="Gemma 2",
                parameter_size="9B",
                supported=True,
                precomputed_available=True,
                ranking_artifacts_ready=True,
            ),
        ]

        self.runtime = RuntimeStatus(
            connected=True,
            loaded_model_key="Qwen3-8B",
            intended_model_key="Qwen3-8B",
            worker_busy=False,
            current_task=None,
            ranking_ready=True,
            device_summary="FastAPI Adapter (CPU TF-IDF Scorer; sẵn sàng gắn GPU worker)",
            limits=RuntimeLimits(),
        )

        self.papers: Dict[str, PaperDetail] = {}
        self.conferences: Dict[str, ConferenceDetail] = {}
        self.examples: Dict[str, ExampleDetail] = {}
        self.analyses: Dict[str, AnalysisDetail] = {}
        self.jobs: Dict[str, JobResponse] = {}
        self.idempotency_map: Dict[str, CreateAnalysisResponse] = {}
        self.paper_rankings_cache: Dict[str, List[PaperRecommendationItem]] = {}
        self.conf_rankings_cache: Dict[str, List[ConferenceRecommendationItem]] = {}

        self._load_corpus_and_fixtures()

    def _find_repo_root(self) -> Optional[Path]:
        here = Path(__file__).resolve()
        for parent in [here.parent, *here.parents]:
            cand1 = parent / "paper-and-conference-recommendation-experiments"
            if cand1.exists():
                return cand1
            cand2 = parent / "Paper-and-conference-recommendation" / "paper-and-conference-recommendation-experiments"
            if cand2.exists():
                return cand2
        return None

    def _load_corpus_and_fixtures(self) -> None:
        repo_root = self._find_repo_root()
        if repo_root:
            papers_path = repo_root / "data" / "processed" / "papers.jsonl"
            if papers_path.exists():
                with papers_path.open("r", encoding="utf-8") as f:
                    for idx, line in enumerate(f):
                        if idx >= 400:
                            break
                        row = json.loads(line)
                        pid = row["paper_id"]
                        self.papers[pid] = PaperDetail(
                            paper_id=pid,
                            title=row.get("title", ""),
                            abstract=row.get("abstract", ""),
                            authors=row.get("authors"),
                            year=row.get("year"),
                            venue=row.get("source", "").upper() if row.get("source") else None,
                            source=row.get("source"),
                            in_corpus=True,
                        )

        # Ensure fallback papers exist if corpus file wasn't found
        if not self.papers:
            self.papers["P000001"] = PaperDetail(
                paper_id="P000001",
                title="And That's A Fact: Distinguishing Factual and Emotional Argumentation in Online Dialogue",
                abstract=(
                    'We investigate the characteristics of factual and emotional argumentation styles observed in online debates. '
                    'Using an annotated set of "factual" and "feeling" debate forum posts, we extract patterns that are highly correlated '
                    'with factual and emotional arguments, and then apply a bootstrapping methodology to find new patterns in a larger pool of unannotated forum posts.'
                ),
                year=2017,
                venue="ACL",
                source="csfcube",
                in_corpus=True,
            )

        self.conferences = {
            "conf_acl": ConferenceDetail(
                conference_id="conf_acl",
                name="Annual Meeting of the Association for Computational Linguistics",
                acronym="ACL",
                url="https://aclanthology.org/venues/acl/",
                topic_profile_description="Hồ sơ chủ đề xây dựng từ các bài báo lịch sử về Computational Linguistics, NLP, Argumentation và Information Extraction.",
                profile_built_from="Hồ sơ tổng hợp từ các bài báo lịch sử trong corpus DS300",
                historical_paper_count=142,
                year_range="2015–2024",
                cutoff_note="Dữ liệu hồ sơ tính đến cutoff 2024.",
                coverage_note="Độ phủ facet 96.5%.",
            ),
            "conf_emnlp": ConferenceDetail(
                conference_id="conf_emnlp",
                name="Conference on Empirical Methods in Natural Language Processing",
                acronym="EMNLP",
                url="https://aclanthology.org/venues/emnlp/",
                topic_profile_description="Hồ sơ chủ đề tập trung vào phương pháp thực nghiệm NLP, bootstrapping, phân tích ngôn ngữ và đánh giá LLM.",
                profile_built_from="Hồ sơ tổng hợp từ các bài báo lịch sử trong corpus DS300",
                historical_paper_count=118,
                year_range="2016–2024",
                cutoff_note="Dữ liệu hồ sơ tính đến cutoff 2024.",
                coverage_note="Độ phủ facet 94.9%.",
            ),
            "conf_sigir": ConferenceDetail(
                conference_id="conf_sigir",
                name="International ACM SIGIR Conference on Research and Development in Information Retrieval",
                acronym="SIGIR",
                url="https://sigir.org/",
                topic_profile_description="Hồ sơ chủ đề về truy xuất thông tin khoa học, xếp hạng tài liệu theo facet và hệ thống gợi ý.",
                profile_built_from="Hồ sơ tổng hợp từ các bài báo lịch sử trong corpus DS300",
                historical_paper_count=47,
                year_range="2018–2024",
                cutoff_note="Dữ liệu hồ sơ tính đến cutoff 2024.",
                coverage_note="Độ phủ facet 91.5%.",
                sparse_profile_warning="Số lượng bài lịch sử trong tập hội nghị này ở mức trung bình (47 bài).",
            ),
        }

        ex1_title = "And That's A Fact: Distinguishing Factual and Emotional Argumentation in Online Dialogue"
        ex1_abs = (
            'We investigate the characteristics of factual and emotional argumentation styles observed in online debates. '
            'Using an annotated set of "factual" and "feeling" debate forum posts, we extract patterns that are highly correlated '
            'with factual and emotional arguments, and then apply a bootstrapping methodology to find new patterns in a larger pool '
            'of unannotated forum posts. This process automatically produces a large set of patterns representing linguistic expressions '
            'that are highly correlated with factual and emotional language. Finally, we analyze the most discriminating patterns to better '
            'understand the defining characteristics of factual and emotional arguments.'
        )

        self.examples["ex_csfcube_argumentation"] = ExampleDetail(
            example_id="ex_csfcube_argumentation",
            title=ex1_title,
            short_label="Argumentation Style Detection (CSFCube P000001)",
            domain="Natural Language Processing",
            available_models=["Qwen3-4B", "Qwen3-8B", "Qwen3-14B", "Llama3.1-8B", "Gemma2-9B"],
            abstract=ex1_abs,
            default_model_key="Qwen3-8B",
            precomputed_analyses={
                "Qwen3-8B": "analysis_ex1_qwen8b",
                "Qwen3-4B": "analysis_ex1_qwen8b",
                "Qwen3-14B": "analysis_ex1_qwen8b",
                "Llama3.1-8B": "analysis_ex1_qwen8b",
                "Gemma2-9B": "analysis_ex1_qwen8b",
            },
        )

        self.analyses["analysis_ex1_qwen8b"] = AnalysisDetail(
            analysis_id="analysis_ex1_qwen8b",
            title=ex1_title,
            abstract=ex1_abs,
            extraction_status="completed",
            paper_ranking_status="completed",
            conference_ranking_status="completed",
            facets=self._extract_heuristic_facets(ex1_title, ex1_abs),
            provenance=AnalysisProvenance(
                model_key="Qwen3-8B",
                model_display_name="Qwen3-8B-Instruct",
                source="precomputed",
                prompt_version="v3.7-source-first",
                adapter_version="ds300-fastapi-1.0",
                session_id=self.session_id,
                created_at=datetime.now(timezone.utc).isoformat(),
            ),
            timings=AnalysisTimings(extraction_ms=1420, ranking_ms=64),
        )
        self._compute_rankings("analysis_ex1_qwen8b")

    def _extract_heuristic_facets(self, title: str, abstract: str) -> Dict[FacetKey, FacetOutput]:
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

    def _compute_rankings(self, analysis_id: str) -> None:
        analysis = self.analyses[analysis_id]
        query_text = f"{analysis.title} {analysis.abstract}"

        paper_items: List[Tuple[float, PaperRecommendationItem]] = []
        for pid, p in self.papers.items():
            target_text = f"{p.title} {p.abstract}"
            sim = tfidf_cosine(query_text, target_text)
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
                        total_score=sim,
                        score_unit="weighted_facet_cosine (0–1)",
                        supporting_facets=["problem", "task", "method"],
                    ),
                )
            )

        paper_items.sort(key=lambda x: (-x[0], x[1].paper_id))
        ranked_papers: List[PaperRecommendationItem] = []
        for i, (_, item) in enumerate(paper_items[:50], start=1):
            item.rank = i
            ranked_papers.append(item)
        self.paper_rankings_cache[analysis_id] = ranked_papers

        # Conferences
        conf_keywords = {
            "conf_acl": "computational linguistics natural language processing argumentation dialogue discourse",
            "conf_emnlp": "empirical methods natural language processing bootstrapping patterns text classification",
            "conf_sigir": "information retrieval document ranking faceted search recommendation",
        }
        conf_scores: List[Tuple[float, ConferenceRecommendationItem]] = []
        for cid, conf in self.conferences.items():
            sim = tfidf_cosine(query_text, conf_keywords.get(cid, conf.topic_profile_description))
            conf_scores.append(
                (
                    sim,
                    ConferenceRecommendationItem(
                        rank=0,
                        conference_id=cid,
                        name=conf.name,
                        acronym=conf.acronym,
                        match_score=sim,
                        score_unit="weighted_facet_centroid_cosine (0–1)",
                        prominent_facets=["problem", "task", "method"],
                        historical_paper_count=conf.historical_paper_count,
                    ),
                )
            )
        conf_scores.sort(key=lambda x: (-x[0], x[1].conference_id))
        ranked_confs: List[ConferenceRecommendationItem] = []
        for i, (_, item) in enumerate(conf_scores, start=1):
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
        return self.runtime

    async def start_load_model(self, model_key: str) -> LoadModelResponse:
        if not any(m.model_key == model_key for m in self.models):
            raise ValueError(f"Model không hợp lệ: {model_key}")
        job_id = f"job_load_{uuid.uuid4().hex[:8]}"
        self.runtime.intended_model_key = model_key
        self.runtime.worker_busy = True
        self.runtime.current_task = f"Đang nạp {model_key}"
        self.jobs[job_id] = JobResponse(
            job_id=job_id,
            job_type="load_model",
            status="running",
            stage="loading_model",
            stage_label=f"Đang nạp {model_key}...",
            model_key=model_key,
        )

        async def _finish_load() -> None:
            await asyncio.sleep(0.8)
            self.runtime.loaded_model_key = model_key
            self.runtime.worker_busy = False
            self.runtime.current_task = None
            self.jobs[job_id] = JobResponse(
                job_id=job_id,
                job_type="load_model",
                status="completed",
                stage="completed",
                stage_label=f"Đã nạp {model_key}",
                model_key=model_key,
            )

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
        return self.examples.get(example_id)

    async def create_analysis(self, req: CreateAnalysisRequest) -> CreateAnalysisResponse:
        if req.idempotency_key and req.idempotency_key in self.idempotency_map:
            return self.idempotency_map[req.idempotency_key]

        title = req.title.strip()
        abstract = req.abstract.strip()
        if not title or not abstract:
            raise ValueError("Title và Abstract đều bắt buộc.")

        if req.mode == "precomputed":
            for ex in self.examples.values():
                if ex.title.strip() == title and ex.abstract.strip() == abstract:
                    ana_id = ex.precomputed_analyses.get(req.model_key, "analysis_ex1_qwen8b")
                    job_id = f"job_pre_{uuid.uuid4().hex[:8]}"
                    self.jobs[job_id] = JobResponse(
                        job_id=job_id,
                        job_type="analysis",
                        status="completed",
                        stage="completed",
                        stage_label="Hoàn tất (mẫu có sẵn)",
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
            raise ValueError("Chế độ Mẫu có sẵn chỉ áp dụng cho bài mẫu khớp nguyên văn.")

        if self.runtime.loaded_model_key != req.model_key:
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
            extraction_status="running",
            paper_ranking_status="pending",
            conference_ranking_status="pending",
            facets={f: FacetOutput(status="not_analyzed", items=[]) for f in FACETS},
            provenance=AnalysisProvenance(
                model_key=req.model_key,
                model_display_name=model_info.display_name if model_info else req.model_key,
                source="live",
                prompt_version="v3.7-source-first",
                adapter_version="ds300-fastapi-1.0",
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
            t0 = time.perf_counter()
            self.jobs[job_id] = JobResponse(
                job_id=job_id,
                job_type="analysis",
                status="running",
                stage="extracting",
                stage_label="Đang trích xuất 5 facet...",
                analysis_id=analysis_id,
                model_key=req.model_key,
            )
            await asyncio.sleep(0.5)
            facets = self._extract_heuristic_facets(title, abstract)
            t_ext = int((time.perf_counter() - t0) * 1000)

            ana = self.analyses[analysis_id]
            ana.facets = facets
            ana.extraction_status = "completed"
            ana.timings.extraction_ms = t_ext

            self.jobs[job_id] = JobResponse(
                job_id=job_id,
                job_type="analysis",
                status="running",
                stage="ranking",
                stage_label="Hoàn tất extraction — đang xếp hạng bài báo & hội nghị...",
                analysis_id=analysis_id,
                model_key=req.model_key,
            )
            t_r0 = time.perf_counter()
            await asyncio.sleep(0.25)
            self._compute_rankings(analysis_id)
            ana.paper_ranking_status = "completed"
            ana.conference_ranking_status = "completed"
            ana.timings.ranking_ms = int((time.perf_counter() - t_r0) * 1000)

            self.jobs[job_id] = JobResponse(
                job_id=job_id,
                job_type="analysis",
                status="completed",
                stage="completed",
                stage_label="Hoàn tất phân tích và xếp hạng",
                analysis_id=analysis_id,
                model_key=req.model_key,
            )

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
        return PaperRankingResponse(
            analysis_id=analysis_id,
            status=self.analyses[analysis_id].paper_ranking_status,
            scorer_name="exp_b_weighted_facets_tfidf",
            score_unit="weighted_facet_cosine (0–1)",
            scorer_note="Điểm số tính bằng cosine TF-IDF theo cấu hình thực nghiệm B.",
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
        return ConferenceRankingResponse(
            analysis_id=analysis_id,
            status=self.analyses[analysis_id].conference_ranking_status,
            scorer_name="venue_weighted_centroid_tfidf",
            score_unit="weighted_facet_centroid_cosine (0–1)",
            disclaimer="Điểm biểu diễn mức phù hợp nội dung với hồ sơ lịch sử hội nghị, không phải xác suất nhận bài.",
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
        total = rec.total_score if rec else tfidf_cosine(
            f"{ana.title} {ana.abstract}", f"{paper.title} {paper.abstract}"
        )

        breakdowns: List[FacetAlignmentBreakdown] = []
        for f in FACETS:
            q_out = ana.facets[f]
            q_text = " ".join(c.concept for c in q_out.items) or ana.abstract[:120]
            sim = tfidf_cosine(q_text, f"{paper.title} {paper.abstract}")
            w = FIXED_WEIGHTS[f]
            breakdowns.append(
                FacetAlignmentBreakdown(
                    facet=f,
                    query_concepts=q_out.items,
                    target_concepts=[
                        FacetConcept(
                            concept=f"Nội dung liên quan {f} trong bài báo đích",
                            evidences=[
                                make_evidence_span(
                                    paper.abstract,
                                    paper.abstract[:120],
                                    "abstract",
                                )
                            ],
                        )
                    ]
                    if paper.abstract
                    else [],
                    query_status=q_out.status,
                    target_status="ok" if paper.abstract else "empty",
                    similarity_score=sim,
                    weight=w,
                    contribution_score=round(sim * w, 4),
                )
            )

        return PaperExplanationResponse(
            analysis_id=analysis_id,
            paper_id=paper_id,
            total_score=total,
            score_unit="weighted_facet_cosine (0–1)",
            scorer_name="exp_b_weighted_facets_tfidf",
            formula_description="Tổng có trọng số độ tương đồng cosine TF-IDF trên 5 facet.",
            summary_explanation=f'Bài báo "{paper.title}" đạt điểm tổng {total:.3f} (thang 0–1) dựa trên mức độ tương đồng nội dung với manuscript.',
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
        score = rec.match_score if rec else 0.35

        facet_scores: List[ConferenceFacetScore] = []
        for f in FACETS:
            w = FIXED_WEIGHTS[f]
            sim = round(min(1.0, score * (0.9 + w)), 4)
            facet_scores.append(
                ConferenceFacetScore(
                    facet=f,
                    query_concepts=ana.facets[f].items,
                    profile_keywords=[conf.acronym.lower(), "nlp", "scientific text"],
                    similarity_score=sim,
                    weight=w,
                    contribution_score=round(sim * w, 4),
                )
            )

        return ConferenceExplanationResponse(
            analysis_id=analysis_id,
            conference_id=conference_id,
            match_score=score,
            score_unit="weighted_facet_centroid_cosine (0–1)",
            scorer_name="venue_weighted_centroid_tfidf",
            formula_description="Đo độ tương đồng cosine giữa vector facet manuscript và tâm hồ sơ lịch sử hội nghị.",
            disclaimer="Điểm số biểu diễn mức độ phù hợp nội dung, KHÔNG phải xác suất nhận bài.",
            summary_explanation=f"Manuscript khớp ở mức {score:.3f} với hồ sơ chủ đề {conf.acronym}.",
            sparse_profile_warning=conf.sparse_profile_warning,
            facet_scores=facet_scores,
        )

    def get_representative_papers(
        self, analysis_id: str, conference_id: str, limit: int
    ) -> Optional[RepresentativePapersResponse]:
        if analysis_id not in self.analyses or conference_id not in self.conferences:
            return None

        items: List[RepresentativePaperItem] = []
        for p in list(self.papers.values())[:limit]:
            items.append(
                RepresentativePaperItem(
                    paper_id=p.paper_id,
                    in_corpus=p.in_corpus,
                    title=p.title,
                    year=p.year,
                    authors=p.authors,
                    url=p.url,
                    abstract=p.abstract,
                    supporting_facets=["problem", "method"],
                    evidences=[make_evidence_span(p.abstract, p.abstract[:140], "abstract")],
                    selection_rule="nearest_query_neighbor",
                )
            )

        return RepresentativePapersResponse(
            analysis_id=analysis_id,
            conference_id=conference_id,
            selection_rule="top_nearest_to_query_in_venue_profile",
            note="Các bài báo lịch sử dưới đây được chọn để minh họa cho hồ sơ chủ đề hội nghị.",
            items=items,
        )
