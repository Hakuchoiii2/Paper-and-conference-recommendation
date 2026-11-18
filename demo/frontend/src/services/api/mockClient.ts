import type { ApiClient } from './client';
import {
  MOCK_ANALYSES,
  MOCK_CONFERENCE_RANKINGS,
  MOCK_CONFERENCES,
  MOCK_EXAMPLES,
  MOCK_MODELS,
  MOCK_PAPER_RANKINGS,
  MOCK_PAPERS,
  buildMockConferenceExplanation,
  buildMockPaperExplanation,
  buildMockRepresentativePapers,
} from '../../mocks/fixtures';
import type {
  AnalysisDetail,
  ConferenceDetail,
  ConferenceExplanationResponse,
  ConferenceRankingResponse,
  CreateAnalysisRequest,
  CreateAnalysisResponse,
  ExampleDetail,
  ExampleSummary,
  FacetKey,
  FacetOutput,
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

const delay = (ms = 180) => new Promise((resolve) => setTimeout(resolve, ms));

interface MockJobRecord {
  job_id: string;
  job_type: 'load_model' | 'analysis';
  created_at: number;
  model_key: string;
  analysis_id?: string;
  is_precomputed?: boolean;
  is_error?: boolean;
  error_message?: string;
}

export class MockApiClient implements ApiClient {
  private runtime: RuntimeStatus = {
    connected: true,
    loaded_model_key: 'Qwen3-8B',
    intended_model_key: 'Qwen3-8B',
    worker_busy: false,
    current_task: null,
    ranking_ready: true,
    device_summary: 'Mock Mode (Không sử dụng GPU thật)',
    last_error: null,
    limits: {
      max_title_chars: 400,
      max_abstract_chars: 4000,
      estimated_max_tokens: 1024,
    },
  };

  private analyses: Record<string, AnalysisDetail> = { ...MOCK_ANALYSES };
  private jobs: Record<string, MockJobRecord> = {};
  private idempotencyMap: Record<string, CreateAnalysisResponse> = {};
  private jobCounter = 100;
  private analysisCounter = 100;

  async getHealth(): Promise<HealthResponse> {
    await delay(100);
    return {
      status: 'ok',
      api_version: 'v1-mock',
      mode: 'mock',
      session_id: 'mock-session-01',
    };
  }

  async getModels(): Promise<ModelInfo[]> {
    await delay(120);
    return MOCK_MODELS;
  }

  async getRuntime(): Promise<RuntimeStatus> {
    await delay(100);
    return { ...this.runtime };
  }

  async loadModel(modelKey: string): Promise<LoadModelResponse> {
    await delay(150);
    const model = MOCK_MODELS.find((m) => m.model_key === modelKey);
    if (!model) {
      throw new Error(`Model không tồn tại: ${modelKey}`);
    }
    this.jobCounter += 1;
    const jobId = `mock_load_${this.jobCounter}`;
    this.runtime.intended_model_key = modelKey;
    this.runtime.worker_busy = true;
    this.runtime.current_task = `Đang nạp ${model.display_name} (giả lập)`;
    this.jobs[jobId] = {
      job_id: jobId,
      job_type: 'load_model',
      created_at: Date.now(),
      model_key: modelKey,
    };
    return {
      job_id: jobId,
      intended_model_key: modelKey,
      status: 'queued',
    };
  }

  async getExamples(): Promise<ExampleSummary[]> {
    await delay(120);
    return MOCK_EXAMPLES.map(({ abstract: _a, default_model_key: _d, precomputed_analyses: _p, ...rest }) => rest);
  }

  async getExample(exampleId: string): Promise<ExampleDetail> {
    await delay(120);
    const found = MOCK_EXAMPLES.find((e) => e.example_id === exampleId);
    if (!found) {
      throw new Error(`Không tìm thấy bài mẫu ${exampleId}`);
    }
    return found;
  }

  async createAnalysis(request: CreateAnalysisRequest): Promise<CreateAnalysisResponse> {
    await delay(180);
    if (request.idempotency_key && this.idempotencyMap[request.idempotency_key]) {
      return this.idempotencyMap[request.idempotency_key];
    }

    const title = request.title.trim();
    const abstract = request.abstract.trim();

    if (!title || !abstract) {
      throw new Error('Title và Abstract đều bắt buộc.');
    }

    // Check exact precomputed example match
    const matchedExample = MOCK_EXAMPLES.find(
      (ex) => ex.title.trim() === title && ex.abstract.trim() === abstract
    );

    if (request.mode === 'precomputed') {
      if (!matchedExample) {
        throw new Error(
          'Chế độ "Mẫu có sẵn" chỉ hỗ trợ các bài mẫu khớp nguyên văn. Vui lòng chọn bài mẫu hoặc chuyển sang chế độ Trực tiếp (Live).'
        );
      }
      const preId =
        matchedExample.precomputed_analyses[request.model_key] ||
        matchedExample.precomputed_analyses[matchedExample.default_model_key];

      this.jobCounter += 1;
      const jobId = `mock_job_${this.jobCounter}`;
      this.jobs[jobId] = {
        job_id: jobId,
        job_type: 'analysis',
        created_at: Date.now(),
        model_key: request.model_key,
        analysis_id: preId,
        is_precomputed: true,
      };
      const resp: CreateAnalysisResponse = {
        analysis_id: preId,
        job_id: jobId,
        status: 'completed',
      };
      if (request.idempotency_key) this.idempotencyMap[request.idempotency_key] = resp;
      return resp;
    }

    // Live mode check: require loaded model to match
    if (this.runtime.loaded_model_key !== request.model_key) {
      throw new Error(
        `Model "${request.model_key}" chưa được nạp (hiện đang nạp "${this.runtime.loaded_model_key || 'chưa có'}"). Vui lòng nạp model trước khi chạy trực tiếp.`
      );
    }

    // Create a new live-simulated analysis
    this.analysisCounter += 1;
    this.jobCounter += 1;
    const analysisId = `analysis_live_${this.analysisCounter}`;
    const jobId = `mock_job_${this.jobCounter}`;

    // If it matches an example, clone its facets with source='live'
    const baseExampleAnalysis = matchedExample
      ? MOCK_ANALYSES[
          matchedExample.precomputed_analyses[request.model_key] ||
            matchedExample.precomputed_analyses[matchedExample.default_model_key]
        ]
      : null;

    const modelInfo = MOCK_MODELS.find((m) => m.model_key === request.model_key);

    this.analyses[analysisId] = {
      analysis_id: analysisId,
      title,
      abstract,
      extraction_status: 'completed',
      paper_ranking_status: 'completed',
      conference_ranking_status: 'completed',
      facets: baseExampleAnalysis
        ? baseExampleAnalysis.facets
        : this.buildSyntheticFacets(title, abstract),
      provenance: {
        model_key: request.model_key,
        model_display_name: modelInfo?.display_name || request.model_key,
        source: 'live',
        prompt_version: 'v3.7-source-first',
        adapter_version: 'ds300-demo-mock-1.0',
        session_id: 'mock-session-01',
        created_at: new Date().toISOString(),
      },
      timings: {
        model_load_ms: null,
        extraction_ms: 1340,
        ranking_ms: 92,
      },
    };

    this.jobs[jobId] = {
      job_id: jobId,
      job_type: 'analysis',
      created_at: Date.now(),
      model_key: request.model_key,
      analysis_id: analysisId,
      is_precomputed: false,
    };

    const resp: CreateAnalysisResponse = {
      analysis_id: analysisId,
      job_id: jobId,
      status: 'queued',
    };
    if (request.idempotency_key) this.idempotencyMap[request.idempotency_key] = resp;
    return resp;
  }

  private buildSyntheticFacets(
    title: string,
    abstract: string
  ): Record<FacetKey, FacetOutput> {
    const sentences = abstract
      .split(/(?<=[.!?])\s+/)
      .map((s) => s.trim())
      .filter(Boolean);

    const makeSpan = (quote: string, source_field: 'title' | 'abstract') => {
      const target = source_field === 'title' ? title : abstract;
      const idx = target.indexOf(quote);
      return {
        quote,
        source_field,
        start_offset: idx >= 0 ? idx : null,
        end_offset: idx >= 0 ? idx + quote.length : null,
        verified: idx >= 0,
      };
    };

    const s0 = sentences[0] || abstract.slice(0, 120);
    const s1 = sentences[1] || '';
    const sLast = sentences[sentences.length - 1] || '';

    return {
      problem: {
        status: 'ok',
        items: [
          {
            concept: `research challenge described in "${title.slice(0, 60)}"`,
            evidences: [makeSpan(s0, 'abstract')],
          },
        ],
      },
      task: {
        status: 'ok',
        items: [
          {
            concept: title,
            evidences: [makeSpan(title, 'title')],
          },
        ],
      },
      method: s1
        ? {
            status: 'ok',
            items: [
              {
                concept: 'proposed methodology from manuscript abstract',
                evidences: [makeSpan(s1, 'abstract')],
              },
            ],
          }
        : { status: 'empty', items: [] },
      dataset: {
        status: 'empty',
        items: [],
      },
      contribution:
        sLast && sLast !== s0
          ? {
              status: 'ok',
              items: [
                {
                  concept: 'key findings and contributions reported in abstract',
                  evidences: [makeSpan(sLast, 'abstract')],
                },
              ],
            }
          : { status: 'empty', items: [] },
    };
  }

  async getJob(jobId: string): Promise<JobResponse> {
    await delay(120);
    const job = this.jobs[jobId];
    if (!job) {
      throw new Error(`Không tìm thấy tác vụ ${jobId} (phiên mock có thể đã reset).`);
    }

    const elapsed = Date.now() - job.created_at;

    if (job.job_type === 'load_model') {
      if (elapsed < 900) {
        return {
          job_id: jobId,
          job_type: 'load_model',
          status: 'running',
          stage: 'loading_model',
          stage_label: `Đang nạp ${job.model_key} (giả lập)...`,
          model_key: job.model_key,
        };
      }
      this.runtime.loaded_model_key = job.model_key;
      this.runtime.worker_busy = false;
      this.runtime.current_task = null;
      return {
        job_id: jobId,
        job_type: 'load_model',
        status: 'completed',
        stage: 'completed',
        stage_label: `Đã nạp ${job.model_key}`,
        model_key: job.model_key,
      };
    }

    if (job.is_precomputed || elapsed >= 1800) {
      return {
        job_id: jobId,
        job_type: 'analysis',
        status: 'completed',
        stage: 'completed',
        stage_label: 'Hoàn tất phân tích và xếp hạng',
        analysis_id: job.analysis_id,
        model_key: job.model_key,
      };
    }

    if (elapsed < 450) {
      return {
        job_id: jobId,
        job_type: 'analysis',
        status: 'running',
        stage: 'extracting',
        stage_label: 'Đang trích xuất 5 facet từ title & abstract...',
        analysis_id: job.analysis_id,
        model_key: job.model_key,
      };
    }
    if (elapsed < 1000) {
      return {
        job_id: jobId,
        job_type: 'analysis',
        status: 'running',
        stage: 'verifying_evidence',
        stage_label: 'Đang kiểm tra bằng chứng (grounding evidence)...',
        analysis_id: job.analysis_id,
        model_key: job.model_key,
      };
    }
    return {
      job_id: jobId,
      job_type: 'analysis',
      status: 'running',
      stage: 'ranking',
      stage_label: 'Đã xong extraction — đang xếp hạng bài báo & hội nghị...',
      analysis_id: job.analysis_id,
      model_key: job.model_key,
    };
  }

  async getAnalysis(analysisId: string): Promise<AnalysisDetail> {
    await delay(140);
    const found = this.analyses[analysisId];
    if (!found) {
      throw new Error(
        `Không tìm thấy kết quả phân tích "${analysisId}". Phiên mock có thể đã được làm mới — vui lòng phân tích lại từ trang chủ.`
      );
    }
    return found;
  }

  async getPaperRankings(analysisId: string, topK = 10): Promise<PaperRankingResponse> {
    await delay(140);
    if (!this.analyses[analysisId]) {
      throw new Error(`Không tìm thấy analysis ${analysisId}`);
    }
    const items = MOCK_PAPER_RANKINGS.slice(0, topK);
    return {
      analysis_id: analysisId,
      status: 'completed',
      scorer_name: 'exp_b_weighted_facets_tfidf',
      score_unit: 'weighted_facet_cosine (0–1)',
      scorer_note:
        'Điểm số được tính theo tổng có trọng số độ tương đồng cosine TF-IDF trên 5 facet (thực nghiệm B).',
      top_k: topK,
      total_available: MOCK_PAPER_RANKINGS.length,
      items,
    };
  }

  async getConferenceRankings(
    analysisId: string,
    topK = 10
  ): Promise<ConferenceRankingResponse> {
    await delay(140);
    if (!this.analyses[analysisId]) {
      throw new Error(`Không tìm thấy analysis ${analysisId}`);
    }
    const items = MOCK_CONFERENCE_RANKINGS.slice(0, topK);
    return {
      analysis_id: analysisId,
      status: 'completed',
      scorer_name: 'venue_weighted_centroid_tfidf',
      score_unit: 'weighted_facet_centroid_cosine (0–1)',
      disclaimer:
        'Điểm biểu diễn mức phù hợp nội dung với hồ sơ lịch sử hội nghị, không phải xác suất nhận bài.',
      top_k: topK,
      total_available: MOCK_CONFERENCE_RANKINGS.length,
      items,
    };
  }

  async getPaper(paperId: string): Promise<PaperDetail> {
    await delay(120);
    const paper = MOCK_PAPERS[paperId];
    if (!paper) {
      throw new Error(`Không tìm thấy bài báo ${paperId}`);
    }
    return paper;
  }

  async getPaperExplanation(
    analysisId: string,
    paperId: string
  ): Promise<PaperExplanationResponse> {
    await delay(150);
    return buildMockPaperExplanation(analysisId, paperId);
  }

  async getConference(conferenceId: string): Promise<ConferenceDetail> {
    await delay(120);
    const conf = MOCK_CONFERENCES[conferenceId];
    if (!conf) {
      throw new Error(`Không tìm thấy hội nghị ${conferenceId}`);
    }
    return conf;
  }

  async getConferenceExplanation(
    analysisId: string,
    conferenceId: string
  ): Promise<ConferenceExplanationResponse> {
    await delay(150);
    return buildMockConferenceExplanation(analysisId, conferenceId);
  }

  async getRepresentativePapers(
    analysisId: string,
    conferenceId: string,
    limit = 5
  ): Promise<RepresentativePapersResponse> {
    await delay(140);
    return buildMockRepresentativePapers(analysisId, conferenceId, limit);
  }
}
