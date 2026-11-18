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

    const res = await fetch(url, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers || {}),
      },
    });

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      let code: string | undefined;
      try {
        const body = await res.json();
        detail = body.detail || body.message || detail;
        code = body.code;
      } catch {
        // ignore JSON parse error
      }
      throw new HttpApiError(detail, res.status, code);
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
}
