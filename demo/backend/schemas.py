from __future__ import annotations

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field

FacetKey = Literal["problem", "task", "method", "dataset", "contribution"]
AnalysisMode = Literal["live", "precomputed"]
AnalysisSource = Literal["live", "cache", "precomputed"]
PaperRankingMethod = Literal["whole_text", "equal_facets", "weighted_facets"]
ConferenceRankingMethod = Literal["whole_text_knn", "flat_facet_knn", "gated_knn"]
JobStatusType = Literal["queued", "running", "completed", "failed"]
JobStage = Literal[
    "queued",
    "loading_model",
    "extracting",
    "verifying_evidence",
    "extraction_complete",
    "ranking",
    "completed",
    "failed",
]
FacetStatus = Literal["ok", "empty", "not_analyzed", "error"]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    api_version: str
    mode: str
    session_id: str


class ModelInfo(BaseModel):
    model_key: str
    display_name: str
    family: str
    parameter_size: str
    supported: bool
    precomputed_available: bool
    ranking_artifacts_ready: bool
    unavailable_reason: Optional[str] = None


class RuntimeLimits(BaseModel):
    max_title_chars: int = 400
    max_abstract_chars: int = 4000
    estimated_max_tokens: int = 1024


class RuntimeStatus(BaseModel):
    connected: bool = True
    loaded_model_key: Optional[str] = None
    intended_model_key: Optional[str] = None
    worker_busy: bool = False
    current_task: Optional[str] = None
    ranking_ready: bool = True
    device_summary: Optional[str] = None
    last_error: Optional[str] = None
    limits: RuntimeLimits = Field(default_factory=RuntimeLimits)


class LoadModelRequest(BaseModel):
    model_key: str


class LoadModelResponse(BaseModel):
    job_id: str
    intended_model_key: str
    status: JobStatusType


class ExampleSummary(BaseModel):
    example_id: str
    title: str
    short_label: str
    domain: str
    available_models: List[str]


class ExampleDetail(ExampleSummary):
    abstract: str
    default_model_key: str
    precomputed_analyses: Dict[str, str]


class EvidenceSpan(BaseModel):
    quote: str
    source_field: Literal["title", "abstract"]
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    verified: bool = False


class FacetConcept(BaseModel):
    concept: str
    evidences: List[EvidenceSpan] = Field(default_factory=list)


class FacetOutput(BaseModel):
    status: FacetStatus
    items: List[FacetConcept] = Field(default_factory=list)
    error_message: Optional[str] = None


class AnalysisTimings(BaseModel):
    model_load_ms: Optional[int] = None
    extraction_ms: Optional[int] = None
    ranking_ms: Optional[int] = None


class AnalysisProvenance(BaseModel):
    model_key: str
    model_display_name: str
    source: AnalysisSource
    prompt_version: str
    adapter_version: str
    session_id: str
    created_at: str


class AnalysisDetail(BaseModel):
    analysis_id: str
    title: str
    abstract: str
    extraction_status: Literal["pending", "running", "completed", "failed"]
    extraction_error: Optional[str] = None
    paper_ranking_status: Literal["pending", "running", "completed", "unavailable", "failed"]
    conference_ranking_status: Literal["pending", "running", "completed", "unavailable", "failed"]
    facets: Dict[FacetKey, FacetOutput]
    provenance: AnalysisProvenance
    timings: AnalysisTimings


class CreateAnalysisRequest(BaseModel):
    title: str
    abstract: str
    model_key: str
    mode: AnalysisMode = "live"
    embedding_model: Optional[str] = "tfidf"
    paper_ranking_method: PaperRankingMethod = "whole_text"
    conference_ranking_method: ConferenceRankingMethod = "whole_text_knn"
    idempotency_key: Optional[str] = None


class CreateAnalysisResponse(BaseModel):
    analysis_id: str
    job_id: str
    status: JobStatusType


class JobError(BaseModel):
    code: str
    message: str
    retryable: bool = True


class JobResponse(BaseModel):
    job_id: str
    job_type: Literal["load_model", "analysis"]
    status: JobStatusType
    stage: JobStage
    stage_label: str
    analysis_id: Optional[str] = None
    model_key: Optional[str] = None
    error: Optional[JobError] = None


class PaperRecommendationItem(BaseModel):
    rank: int
    paper_id: str
    title: str
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    total_score: float
    score_unit: str
    supporting_facets: List[FacetKey]


class PaperRankingResponse(BaseModel):
    analysis_id: str
    status: Literal["pending", "running", "completed", "unavailable", "failed"]
    scorer_name: str
    score_unit: str
    scorer_note: str
    top_k: int
    total_available: int
    items: List[PaperRecommendationItem]
    error_message: Optional[str] = None


class ConferenceRecommendationItem(BaseModel):
    rank: int
    conference_id: str
    name: str
    acronym: str
    match_score: float
    score_unit: str
    prominent_facets: List[FacetKey]
    historical_paper_count: Optional[int] = None


class ConferenceRankingResponse(BaseModel):
    analysis_id: str
    status: Literal["pending", "running", "completed", "unavailable", "failed"]
    scorer_name: str
    score_unit: str
    disclaimer: str
    top_k: int
    total_available: int
    items: List[ConferenceRecommendationItem]
    error_message: Optional[str] = None


class PaperDetail(BaseModel):
    paper_id: str
    title: str
    abstract: str
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    in_corpus: bool = True


class FacetAlignmentBreakdown(BaseModel):
    facet: FacetKey
    query_concepts: List[FacetConcept]
    target_concepts: List[FacetConcept]
    query_status: FacetStatus
    target_status: FacetStatus
    similarity_score: Optional[float] = None
    weight: Optional[float] = None
    contribution_score: Optional[float] = None
    note: Optional[str] = None


class PaperExplanationResponse(BaseModel):
    analysis_id: str
    paper_id: str
    total_score: float
    score_unit: str
    scorer_name: str
    formula_description: str
    summary_explanation: str
    facet_breakdowns: List[FacetAlignmentBreakdown]


class ConferenceDetail(BaseModel):
    conference_id: str
    name: str
    acronym: str
    url: Optional[str] = None
    topic_profile_description: str
    profile_built_from: str
    historical_paper_count: int
    year_range: Optional[str] = None
    cutoff_note: Optional[str] = None
    coverage_note: Optional[str] = None
    sparse_profile_warning: Optional[str] = None


class ConferenceFacetScore(BaseModel):
    facet: FacetKey
    query_concepts: List[FacetConcept]
    profile_keywords: List[str]
    similarity_score: Optional[float] = None
    weight: Optional[float] = None
    contribution_score: Optional[float] = None


class ConferenceExplanationResponse(BaseModel):
    analysis_id: str
    conference_id: str
    match_score: float
    score_unit: str
    scorer_name: str
    formula_description: str
    disclaimer: str
    summary_explanation: str
    sparse_profile_warning: Optional[str] = None
    facet_scores: List[ConferenceFacetScore]


class RepresentativePaperItem(BaseModel):
    paper_id: str
    in_corpus: bool
    title: str
    year: Optional[int] = None
    authors: Optional[List[str]] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    supporting_facets: List[FacetKey]
    evidences: List[EvidenceSpan]
    selection_rule: str


class RepresentativePapersResponse(BaseModel):
    analysis_id: str
    conference_id: str
    selection_rule: str
    note: str
    items: List[RepresentativePaperItem]
