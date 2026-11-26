import type { ApiClient } from './client';
import type {
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
  LoadModelResponse,
  ModelInfo,
  PaperDetail,
  PaperExplanationResponse,
  PaperRankingResponse,
  RepresentativePapersResponse,
  RuntimeStatus,
} from '../../types/api';

export class HttpApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = 'HttpApiError';
    this.status = status;
    this.code = code;
  }
}

export class HttpApiClient implements ApiClient {
  private getBaseUrl: () => string;

  constructor(getBaseUrl: () => string) {
    this.getBaseUrl = getBaseUrl;
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const base = this.getBaseUrl().replace(/\/+$/, '');
    const url = `${base}${path}`;

    let res: Response;
    try {
      res = await fetch(url, {
        ...init,
        headers: {
          'Content-Type': 'application/json',
          ...(init?.headers || {}),
        },
      });
    } catch {
      throw new HttpApiError(
        `Không thể kết nối tới backend (${base}). Vui lòng kiểm tra server hoặc cấu hình lại địa chỉ API trong bảng Hệ thống.`,
        0,
        'NETWORK_ERROR'
      );
    }

    const contentType = res.headers.get('content-type') || '';
    if (!res.ok) {
      let detail = `Lỗi HTTP ${res.status}`;
      let code: string | undefined;
      if (contentType.includes('application/json')) {
        try {
          const body = await res.json();
          detail = body.detail || body.message || detail;
          code = body.code;
        } catch {
          // ignore JSON parse error
        }
      }
      throw new HttpApiError(detail, res.status, code);
    }

    if (!contentType.includes('application/json')) {
      throw new HttpApiError(
        'Phản hồi từ server không phải JSON hợp lệ (có thể đường dẫn API đang trỏ nhầm vào trang HTML).',
        res.status,
        'INVALID_CONTENT_TYPE'
      );
    }

    return (await res.json()) as T;
  }

  getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }

  getModels(): Promise<ModelInfo[]> {
    return this.request<ModelInfo[]>('/models');
  }

  getRuntime(): Promise<RuntimeStatus> {
    return this.request<RuntimeStatus>('/runtime');
  }

  loadModel(modelKey: string): Promise<LoadModelResponse> {
    return this.request<LoadModelResponse>('/runtime/model', {
      method: 'POST',
      body: JSON.stringify({ model_key: modelKey }),
    });
  }

  getExamples(): Promise<ExampleSummary[]> {
    return this.request<ExampleSummary[]>('/examples');
  }

  getExample(exampleId: string): Promise<ExampleDetail> {
    return this.request<ExampleDetail>(`/examples/${encodeURIComponent(exampleId)}`);
  }

  createAnalysis(request: CreateAnalysisRequest): Promise<CreateAnalysisResponse> {
    return this.request<CreateAnalysisResponse>('/analyses', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  getJob(jobId: string): Promise<JobResponse> {
    return this.request<JobResponse>(`/jobs/${encodeURIComponent(jobId)}`);
  }

  getAnalysis(analysisId: string): Promise<AnalysisDetail> {
    return this.request<AnalysisDetail>(`/analyses/${encodeURIComponent(analysisId)}`);
  }

  getPaperRankings(analysisId: string, topK = 10): Promise<PaperRankingResponse> {
    return this.request<PaperRankingResponse>(
      `/analyses/${encodeURIComponent(analysisId)}/papers?top_k=${topK}`
    );
  }

  getConferenceRankings(analysisId: string, topK = 10): Promise<ConferenceRankingResponse> {
    return this.request<ConferenceRankingResponse>(
      `/analyses/${encodeURIComponent(analysisId)}/conferences?top_k=${topK}`
    );
  }

  getPaper(paperId: string): Promise<PaperDetail> {
    return this.request<PaperDetail>(`/papers/${encodeURIComponent(paperId)}`);
  }

  getPaperExplanation(analysisId: string, paperId: string): Promise<PaperExplanationResponse> {
    return this.request<PaperExplanationResponse>(
      `/analyses/${encodeURIComponent(analysisId)}/papers/${encodeURIComponent(paperId)}/explanation`
    );
  }

  getConference(conferenceId: string): Promise<ConferenceDetail> {
    return this.request<ConferenceDetail>(`/conferences/${encodeURIComponent(conferenceId)}`);
  }

  getConferenceExplanation(
    analysisId: string,
    conferenceId: string
  ): Promise<ConferenceExplanationResponse> {
    return this.request<ConferenceExplanationResponse>(
      `/analyses/${encodeURIComponent(analysisId)}/conferences/${encodeURIComponent(conferenceId)}/explanation`
    );
  }

  getRepresentativePapers(
    analysisId: string,
    conferenceId: string,
    limit = 5
  ): Promise<RepresentativePapersResponse> {
    return this.request<RepresentativePapersResponse>(
      `/analyses/${encodeURIComponent(analysisId)}/conferences/${encodeURIComponent(conferenceId)}/representative-papers?limit=${limit}`
    );
  }

  exploreSearch(
    query: string,
    limit = 12,
    includeExternal = true,
    scope: 'all' | 'local' | 'external' = 'all'
  ): Promise<ExploreSearchResponse> {
    const params = new URLSearchParams({
      q: query,
      limit: String(limit),
      include_external: includeExternal ? 'true' : 'false',
      scope,
    });
    return this.request<ExploreSearchResponse>(`/explore/search?${params.toString()}`);
  }

  explorePreviewPaper(
    paperId: string,
    userId: string
  ): Promise<{ paper: import('../../types/api').ExplorePaperItem; in_profile: boolean; is_analyzed: boolean }> {
    return this.request(
      `/explore/papers/${encodeURIComponent(paperId)}?user_id=${encodeURIComponent(userId)}`
    );
  }

  exploreOpenPaper(request: ExploreOpenPaperRequest): Promise<ExploreOpenPaperResponse> {
    return this.request<ExploreOpenPaperResponse>('/explore/papers/open', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  exploreGetProfile(userId: string): Promise<ExploreProfileResponse> {
    return this.request<ExploreProfileResponse>(
      `/explore/profile?user_id=${encodeURIComponent(userId)}`
    );
  }

  exploreSyncProfile(request: ExploreProfileSyncRequest): Promise<ExploreProfileResponse> {
    return this.request<ExploreProfileResponse>('/explore/profile/sync', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  exploreDeleteProfile(userId: string, paperId?: string): Promise<ExploreProfileResponse> {
    const params = new URLSearchParams({ user_id: userId });
    if (paperId) params.set('paper_id', paperId);
    return this.request<ExploreProfileResponse>(`/explore/profile?${params.toString()}`, {
      method: 'DELETE',
    });
  }

  exploreGetRecommendations(
    userId: string,
    embedding: 'bert-base' | 'tfidf' = 'bert-base',
    method: 'whole_text' | 'equal_facets' | 'weighted_facets' = 'weighted_facets',
    topK = 18,
    offset = 0
  ): Promise<ExploreRecommendationsResponse> {
    const params = new URLSearchParams({
      user_id: userId,
      embedding,
      method,
      top_k: String(topK),
      offset: String(offset),
    });
    return this.request<ExploreRecommendationsResponse>(
      `/explore/recommendations?${params.toString()}`
    );
  }
}
