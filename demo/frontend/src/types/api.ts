export type FacetKey = 'problem' | 'task' | 'method' | 'dataset' | 'contribution';

export type AnalysisMode = 'live' | 'precomputed';

export type AnalysisSource = 'live' | 'cache' | 'precomputed';

export type JobStatusType =
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed';

export type JobStage =
  | 'queued'
  | 'loading_model'
  | 'extracting'
  | 'verifying_evidence'
  | 'extraction_complete'
  | 'ranking'
  | 'completed'
  | 'failed';

export interface HealthResponse {
  status: 'ok' | 'degraded';
  api_version: string;
  mode: string;
  session_id: string;
}

export interface ModelInfo {
  model_key: string;
  display_name: string;
  family: string;
  parameter_size: string;
  supported: boolean;
  precomputed_available: boolean;
  ranking_artifacts_ready: boolean;
  unavailable_reason?: string | null;
}

export interface RuntimeStatus {
  connected: boolean;
  loaded_model_key: string | null;
  intended_model_key: string | null;
  worker_busy: boolean;
  current_task: string | null;
  ranking_ready: boolean;
  device_summary?: string | null;
  last_error?: string | null;
  limits: {
    max_title_chars: number;
    max_abstract_chars: number;
    estimated_max_tokens: number;
  };
}

export interface LoadModelResponse {
  job_id: string;
  intended_model_key: string;
  status: JobStatusType;
}

export interface ExampleSummary {
  example_id: string;
  title: string;
  short_label: string;
  domain: string;
  available_models: string[];
}

export interface ExampleDetail extends ExampleSummary {
  abstract: string;
  default_model_key: string;
  precomputed_analyses: Record<string, string>; // model_key -> analysis_id
}

export interface EvidenceSpan {
  quote: string;
  source_field: 'title' | 'abstract';
  start_offset?: number | null;
  end_offset?: number | null;
  verified: boolean;
}

export interface FacetConcept {
  concept: string;
  evidences: EvidenceSpan[];
}

export type FacetStatus = 'ok' | 'empty' | 'not_analyzed' | 'error';

export interface FacetOutput {
  status: FacetStatus;
  items: FacetConcept[];
  error_message?: string | null;
}

export interface AnalysisTimings {
  model_load_ms?: number | null;
  extraction_ms?: number | null;
  ranking_ms?: number | null;
}

export interface AnalysisProvenance {
  model_key: string;
  model_display_name: string;
  source: AnalysisSource;
  prompt_version: string;
  adapter_version: string;
  session_id: string;
  created_at: string;
}

export interface AnalysisDetail {
  analysis_id: string;
  title: string;
  abstract: string;
  extraction_status: 'pending' | 'running' | 'completed' | 'failed';
  extraction_error?: string | null;
  paper_ranking_status: 'pending' | 'running' | 'completed' | 'unavailable' | 'failed';
  conference_ranking_status: 'pending' | 'running' | 'completed' | 'unavailable' | 'failed';
  facets: Record<FacetKey, FacetOutput>;
  provenance: AnalysisProvenance;
  timings: AnalysisTimings;
}

export type PaperRankingMethod = 'whole_text' | 'equal_facets' | 'weighted_facets';
export type ConferenceRankingMethod = 'whole_text_knn' | 'flat_facet_knn' | 'gated_knn';

export interface CreateAnalysisRequest {
  title: string;
  abstract: string;
  model_key: string;
  mode: AnalysisMode;
  embedding_model?: string;
  paper_ranking_method?: PaperRankingMethod;
  conference_ranking_method?: ConferenceRankingMethod;
  idempotency_key?: string;
}

export interface CreateAnalysisResponse {
  analysis_id: string;
  job_id: string;
  status: JobStatusType;
}

export interface JobResponse {
  job_id: string;
  job_type: 'load_model' | 'analysis';
  status: JobStatusType;
  stage: JobStage;
  stage_label: string;
  analysis_id?: string | null;
  model_key?: string | null;
  error?: {
    code: string;
    message: string;
    retryable: boolean;
  } | null;
}

export interface PaperRecommendationItem {
  rank: number;
  paper_id: string;
  title: string;
  authors?: string[] | null;
  year?: number | null;
  venue?: string | null;
  total_score: number;
  score_unit: string;
  supporting_facets: FacetKey[];
}

export interface PaperRankingResponse {
  analysis_id: string;
  status: 'pending' | 'running' | 'completed' | 'unavailable' | 'failed';
  scorer_name: string;
  score_unit: string;
  scorer_note: string;
  top_k: number;
  total_available: number;
  items: PaperRecommendationItem[];
  error_message?: string | null;
}

export interface ConferenceRecommendationItem {
  rank: number;
  conference_id: string;
  name: string;
  acronym: string;
  match_score: number;
  score_unit: string;
  prominent_facets: FacetKey[];
  historical_paper_count?: number | null;
}

export interface ConferenceRankingResponse {
  analysis_id: string;
  status: 'pending' | 'running' | 'completed' | 'unavailable' | 'failed';
  scorer_name: string;
  score_unit: string;
  disclaimer: string;
  top_k: number;
  total_available: number;
  items: ConferenceRecommendationItem[];
  error_message?: string | null;
}

export interface PaperDetail {
  paper_id: string;
  title: string;
  abstract: string;
  authors?: string[] | null;
  year?: number | null;
  venue?: string | null;
  doi?: string | null;
  url?: string | null;
  source?: string | null;
  in_corpus: boolean;
}

export interface FacetAlignmentBreakdown {
  facet: FacetKey;
  query_concepts: FacetConcept[];
  target_concepts: FacetConcept[];
  query_status: FacetStatus;
  target_status: FacetStatus;
  similarity_score: number | null;
  weight: number | null;
  contribution_score: number | null;
  note?: string | null;
}

export interface PaperExplanationResponse {
  analysis_id: string;
  paper_id: string;
  total_score: number;
  score_unit: string;
  scorer_name: string;
  formula_description: string;
  summary_explanation: string;
  facet_breakdowns: FacetAlignmentBreakdown[];
}

export interface ConferenceDetail {
  conference_id: string;
  name: string;
  acronym: string;
  url?: string | null;
  topic_profile_description: string;
  profile_built_from: string;
  historical_paper_count: number;
  year_range?: string | null;
  cutoff_note?: string | null;
  coverage_note?: string | null;
  sparse_profile_warning?: string | null;
}

export interface ConferenceFacetScore {
  facet: FacetKey;
  query_concepts: FacetConcept[];
  profile_keywords: string[];
  similarity_score: number | null;
  weight: number | null;
  contribution_score: number | null;
}

export interface ConferenceExplanationResponse {
  analysis_id: string;
  conference_id: string;
  match_score: number;
  score_unit: string;
  scorer_name: string;
  formula_description: string;
  disclaimer: string;
  summary_explanation: string;
  sparse_profile_warning?: string | null;
  facet_scores: ConferenceFacetScore[];
}

export interface RepresentativePaperItem {
  paper_id: string;
  in_corpus: boolean;
  title: string;
  year?: number | null;
  authors?: string[] | null;
  url?: string | null;
  abstract?: string | null;
  supporting_facets: FacetKey[];
  evidences: EvidenceSpan[];
  selection_rule: string;
}

export interface RepresentativePapersResponse {
  analysis_id: string;
  conference_id: string;
  selection_rule: string;
  note: string;
  items: RepresentativePaperItem[];
}
