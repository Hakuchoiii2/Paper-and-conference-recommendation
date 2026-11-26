from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from explore_engine import ExploreEngine
from schemas import (
    AnalysisDetail,
    ConferenceDetail,
    ConferenceExplanationResponse,
    ConferenceRankingResponse,
    CreateAnalysisRequest,
    CreateAnalysisResponse,
    ExampleDetail,
    ExampleSummary,
    ExploreOpenPaperRequest,
    ExploreOpenPaperResponse,
    ExploreProfileResponse,
    ExploreProfileSyncRequest,
    ExploreRecommendationsResponse,
    ExploreSearchResponse,
    HealthResponse,
    JobResponse,
    LoadModelRequest,
    LoadModelResponse,
    ModelInfo,
    PaperDetail,
    PaperExplanationResponse,
    PaperRankingResponse,
    RepresentativePapersResponse,
    RuntimeStatus,
)
from service import DemoBackendService


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Pre-warm BERT-base-uncased in background at startup so first ranking takes ~0.4s instead of ~80s
    asyncio.create_task(asyncio.to_thread(service._get_dense_model))
    yield


app = FastAPI(title="DS300 FacetRec Demo API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = DemoBackendService()
explore_engine = ExploreEngine(
    service=service,
    db_path=service._cfg_path("DEMO_ARTIFACTS_DIR", "../_local/demo_artifacts") / "user_profiles.db",
)
api_v1 = APIRouter(prefix="/api/v1", tags=["v1"])


@api_v1.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return service.get_health()


@api_v1.get("/models", response_model=List[ModelInfo])
def list_models() -> List[ModelInfo]:
    return service.get_models()


@api_v1.get("/runtime", response_model=RuntimeStatus)
def get_runtime() -> RuntimeStatus:
    return service.get_runtime()


@api_v1.post("/runtime/model", response_model=LoadModelResponse, status_code=202)
async def load_model(req: LoadModelRequest) -> LoadModelResponse:
    try:
        return await service.start_load_model(req.model_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@api_v1.get("/examples", response_model=List[ExampleSummary])
def list_examples() -> List[ExampleSummary]:
    return service.get_examples()


@api_v1.get("/examples/{example_id}", response_model=ExampleDetail)
def get_example(example_id: str) -> ExampleDetail:
    ex = service.get_example(example_id)
    if not ex:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy bài mẫu {example_id}")
    return ex


@api_v1.post("/analyses", response_model=CreateAnalysisResponse, status_code=202)
async def create_analysis(req: CreateAnalysisRequest) -> CreateAnalysisResponse:
    try:
        return await service.create_analysis(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@api_v1.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy tác vụ {job_id} (phiên server có thể đã khởi động lại).",
        )
    return job


@api_v1.get("/analyses/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(analysis_id: str) -> AnalysisDetail:
    ana = service.get_analysis(analysis_id)
    if not ana:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy kết quả {analysis_id} (phiên server có thể đã khởi động lại).",
        )
    return ana


@api_v1.get("/analyses/{analysis_id}/papers", response_model=PaperRankingResponse)
def get_paper_rankings(
    analysis_id: str, top_k: int = Query(10, ge=1, le=50)
) -> PaperRankingResponse:
    res = service.get_paper_rankings(analysis_id, top_k)
    if not res:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy analysis {analysis_id}")
    return res


@api_v1.get("/analyses/{analysis_id}/conferences", response_model=ConferenceRankingResponse)
def get_conference_rankings(
    analysis_id: str, top_k: int = Query(10, ge=1, le=50)
) -> ConferenceRankingResponse:
    res = service.get_conference_rankings(analysis_id, top_k)
    if not res:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy analysis {analysis_id}")
    return res


@api_v1.get("/papers/{paper_id}", response_model=PaperDetail)
def get_paper(paper_id: str) -> PaperDetail:
    paper = service.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy bài báo {paper_id}")
    return paper


@api_v1.get(
    "/analyses/{analysis_id}/papers/{paper_id}/explanation",
    response_model=PaperExplanationResponse,
)
def get_paper_explanation(analysis_id: str, paper_id: str) -> PaperExplanationResponse:
    exp = service.get_paper_explanation(analysis_id, paper_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu giải thích bài báo")
    return exp


@api_v1.get("/conferences/{conference_id}", response_model=ConferenceDetail)
def get_conference(conference_id: str) -> ConferenceDetail:
    conf = service.get_conference(conference_id)
    if not conf:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hội nghị {conference_id}")
    return conf


@api_v1.get(
    "/analyses/{analysis_id}/conferences/{conference_id}/explanation",
    response_model=ConferenceExplanationResponse,
)
def get_conference_explanation(
    analysis_id: str, conference_id: str
) -> ConferenceExplanationResponse:
    exp = service.get_conference_explanation(analysis_id, conference_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu giải thích hội nghị")
    return exp


@api_v1.get(
    "/analyses/{analysis_id}/conferences/{conference_id}/representative-papers",
    response_model=RepresentativePapersResponse,
)
def get_representative_papers(
    analysis_id: str, conference_id: str, limit: int = Query(5, ge=1, le=20)
) -> RepresentativePapersResponse:
    reps = service.get_representative_papers(analysis_id, conference_id, limit)
    if not reps:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài báo lịch sử đại diện")
    return reps


# ==============================================================================
# Shopee-style Explore Search & 5-Facet Mean-Vector User Profile Endpoints
# ==============================================================================
@api_v1.get("/explore/search", response_model=ExploreSearchResponse)
async def explore_search(
    q: str = Query("", description="Từ khóa hoặc tên bài báo cần tìm"),
    limit: int = Query(12, ge=1, le=30),
    include_external: bool = Query(True, description="Tìm thêm bài mới từ OpenAlex API"),
    scope: str = Query("all", description="Phạm vi tìm kiếm: all | local | external"),
) -> ExploreSearchResponse:
    return await explore_engine.search(
        query=q,
        limit=limit,
        include_external=include_external,
        scope=scope,
    )


@api_v1.get("/explore/papers/{paper_id}")
def explore_preview_paper(
    paper_id: str,
    user_id: str = Query("default_user"),
):
    res = explore_engine.preview_paper(paper_id=paper_id, user_id=user_id)
    if not res:
        raise HTTPException(status_code=404, detail="Bài báo chưa có trong kho cục bộ.")
    return res


@api_v1.post("/explore/papers/open", response_model=ExploreOpenPaperResponse)
async def explore_open_paper(req: ExploreOpenPaperRequest) -> ExploreOpenPaperResponse:
    try:
        return await explore_engine.open_paper(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@api_v1.get("/explore/profile", response_model=ExploreProfileResponse)
def explore_get_profile(user_id: str = Query("default_user")) -> ExploreProfileResponse:
    return explore_engine.get_profile(user_id=user_id)


@api_v1.post("/explore/profile/sync", response_model=ExploreProfileResponse)
async def explore_sync_profile(req: ExploreProfileSyncRequest) -> ExploreProfileResponse:
    return await explore_engine.sync_analysis_to_profile(req)


@api_v1.delete("/explore/profile", response_model=ExploreProfileResponse)
def explore_delete_profile(
    user_id: str = Query("default_user"),
    paper_id: Optional[str] = Query(None),
) -> ExploreProfileResponse:
    return explore_engine.delete_profile(user_id=user_id, paper_id=paper_id)


@api_v1.get("/explore/recommendations", response_model=ExploreRecommendationsResponse)
def explore_get_recommendations(
    user_id: str = Query("default_user"),
    embedding: str = Query("bert-base"),
    method: str = Query("weighted_facets"),
    top_k: int = Query(18, ge=1, le=60),
    offset: int = Query(0, ge=0),
) -> ExploreRecommendationsResponse:
    return explore_engine.get_recommendations(
        user_id=user_id,
        embedding=embedding,
        method=method,
        top_k=top_k,
        offset=offset,
    )


app.include_router(api_v1)

# Serve built React static files when deployed together (e.g. Kaggle or production)
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Never fall back API routes to index.html
        if full_path.startswith("api/") or full_path == "api":
            return JSONResponse(status_code=404, content={"detail": "API route not found"})
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(FRONTEND_DIST / "index.html"))
