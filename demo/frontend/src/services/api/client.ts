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

export interface ApiClient {
  getHealth(): Promise<HealthResponse>;
  getModels(): Promise<ModelInfo[]>;
  getRuntime(): Promise<RuntimeStatus>;
  loadModel(modelKey: string): Promise<LoadModelResponse>;
  getExamples(): Promise<ExampleSummary[]>;
  getExample(exampleId: string): Promise<ExampleDetail>;
  createAnalysis(request: CreateAnalysisRequest): Promise<CreateAnalysisResponse>;
  getJob(jobId: string): Promise<JobResponse>;
  getAnalysis(analysisId: string): Promise<AnalysisDetail>;
  getPaperRankings(analysisId: string, topK?: number): Promise<PaperRankingResponse>;
  getConferenceRankings(analysisId: string, topK?: number): Promise<ConferenceRankingResponse>;
  getPaper(paperId: string): Promise<PaperDetail>;
  getPaperExplanation(analysisId: string, paperId: string): Promise<PaperExplanationResponse>;
  getConference(conferenceId: string): Promise<ConferenceDetail>;
  getConferenceExplanation(
    analysisId: string,
    conferenceId: string
  ): Promise<ConferenceExplanationResponse>;
  getRepresentativePapers(
    analysisId: string,
    conferenceId: string,
    limit?: number
  ): Promise<RepresentativePapersResponse>;
  exploreSearch(
    query: string,
    limit?: number,
    includeExternal?: boolean,
    scope?: 'all' | 'local' | 'external'
  ): Promise<ExploreSearchResponse>;
  explorePreviewPaper(
    paperId: string,
    userId: string
  ): Promise<{ paper: import('../../types/api').ExplorePaperItem; in_profile: boolean; is_analyzed: boolean }>;
  exploreOpenPaper(request: ExploreOpenPaperRequest): Promise<ExploreOpenPaperResponse>;
  exploreGetProfile(userId: string): Promise<ExploreProfileResponse>;
  exploreSyncProfile(request: ExploreProfileSyncRequest): Promise<ExploreProfileResponse>;
  exploreDeleteProfile(userId: string, paperId?: string): Promise<ExploreProfileResponse>;
  exploreGetRecommendations(
    userId: string,
    embedding?: 'bert-base' | 'tfidf',
    method?: 'whole_text' | 'equal_facets' | 'weighted_facets',
    topK?: number,
    offset?: number
  ): Promise<ExploreRecommendationsResponse>;
}
