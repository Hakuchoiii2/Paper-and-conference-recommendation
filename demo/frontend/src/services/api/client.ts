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
}
