import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  Award,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Clock,
  Edit3,
  FileText,
  GitCompare,
  Info,
  Loader2,
  Quote,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { FacetBadge } from '../components/FacetBadge';
import { type ActiveEvidenceHighlight, HighlightedText } from '../components/HighlightedText';
import { FACET_META, FACET_ORDER } from '../constants/facets';
import { useSystem } from '../context/SystemContext';
import {
  getAnalysisSnapshot,
  saveAnalysisHistory,
  saveAnalysisSnapshot,
} from '../utils/history';
import { getExploreUserId, notifyProfileUpdated } from '../utils/userSession';
import type {
  AnalysisDetail,
  AnalysisSource,
  ConferenceRankingResponse,
  FacetKey,
  JobResponse,
  PaperRankingResponse,
} from '../types/api';

function cleanVenue(venue?: string | null): string | null {
  if (!venue) return null;
  const v = venue.trim();
  if (!v || v.toUpperCase() === 'CSFCUBE') return null;
  return v;
}

const SOURCE_LABELS: Record<AnalysisSource, { label: string; className: string }> = {
  live: { label: 'Trực tiếp', className: 'bg-blue-50 text-blue-700 border-blue-200' },
  cache: { label: 'Kho 5-Facet có sẵn', className: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  precomputed: { label: 'Mẫu có sẵn', className: 'bg-amber-50 text-amber-800 border-amber-200' },
};

export function AnalysisResultPage() {
  const { analysisId = '' } = useParams<{ analysisId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const {
    apiClient,
    runtime,
    exploreEmbedding,
    explorePaperMethod,
    exploreConfMethod,
  } = useSystem();

  const jobId = searchParams.get('job_id');
  const initialTab = searchParams.get('tab') === 'conferences' ? 'conferences' : 'papers';
  const initialTopK = Number(searchParams.get('top_k')) || 10;

  const [activeTab] = useState<'papers' | 'conferences'>(initialTab);
  const [topK, setTopK] = useState<number>([5, 10, 20].includes(initialTopK) ? initialTopK : 10);
  const [abstractExpanded, setAbstractExpanded] = useState(true);
  const [activeHighlight, setActiveHighlight] = useState<ActiveEvidenceHighlight | null>(null);

  const [job, setJob] = useState<JobResponse | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null);
  const [paperRanking, setPaperRanking] = useState<PaperRankingResponse | null>(null);
  const [confRanking, setConfRanking] = useState<ConferenceRankingResponse | null>(null);

  const [loading, setLoading] = useState(true);
  const [networkError, setNetworkError] = useState<string | null>(null);
  const [reExtracting, setReExtracting] = useState(false);
  const [reExtractError, setReExtractError] = useState<string | null>(null);

  const fetchAnalysisAndRankings = useCallback(
    async (k: number) => {
      try {
        setNetworkError(null);
        const detail = await apiClient.getAnalysis(analysisId);
        setAnalysis(detail);
        // Show Title + Abstract + 5-Facet immediately while rankings load below
        setLoading(false);
        saveAnalysisHistory({
          analysis_id: detail.analysis_id,
          title: detail.title,
          model_name: detail.provenance?.model_display_name || 'Qwen3-4B',
          source: detail.provenance?.source || 'live',
          created_at: detail.provenance?.created_at || new Date().toISOString(),
        });

        let loadedPapers: PaperRankingResponse | null = null;
        let loadedConfs: ConferenceRankingResponse | null = null;
        if (detail.extraction_status === 'completed') {
          const [papersRes, confsRes] = await Promise.allSettled([
            apiClient.getPaperRankings(analysisId, k),
            apiClient.getConferenceRankings(analysisId, k),
          ]);
          if (papersRes.status === 'fulfilled') {
            loadedPapers = papersRes.value;
            setPaperRanking(papersRes.value);
          }
          if (confsRes.status === 'fulfilled') {
            loadedConfs = confsRes.value;
            setConfRanking(confsRes.value);
          }
        }
        saveAnalysisSnapshot({
          analysis: detail,
          paperRanking: loadedPapers,
          confRanking: loadedConfs,
          saved_at: new Date().toISOString(),
        });

        // Automatically sync completed analysis into unified SQLite Profile & History
        if (detail.extraction_status === 'completed') {
          const facetConcepts = {} as Record<FacetKey, string[]>;
          for (const fk of FACET_ORDER) {
            facetConcepts[fk] = (detail.facets[fk]?.items || []).map((it) => it.concept);
          }
          const isFromExplore = searchParams.get('from') === 'explore';
          const profileSource = isFromExplore
            ? detail.provenance?.source === 'cache'
              ? 'explore_kb'
              : 'explore_openalex'
            : 'manuscript';
          try {
            const prof = await apiClient.exploreSyncProfile({
              user_id: getExploreUserId(),
              analysis_id: detail.analysis_id,
              title: detail.title,
              abstract: detail.abstract,
              source: profileSource,
              extraction_source: detail.provenance?.model_display_name || 'Qwen3-4B',
              facets: facetConcepts,
            });
            notifyProfileUpdated(prof.paper_count);
          } catch {
            // ignore transient sync failure
          }
        }
        setLoading(false);
      } catch (err) {
        // Fallback to localStorage snapshot so History still works after server/Kaggle restart
        const cached = getAnalysisSnapshot(analysisId);
        if (cached) {
          setAnalysis(cached.analysis);
          if (cached.paperRanking) setPaperRanking(cached.paperRanking);
          if (cached.confRanking) setConfRanking(cached.confRanking);
          setNetworkError(null);
          setLoading(false);
          return;
        }
        setNetworkError(err instanceof Error ? err.message : 'Lỗi kết nối khi tải kết quả.');
        setLoading(false);
      }
    },
    [analysisId, apiClient]
  );

  // Poll job if job_id is present and not finished
  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function run() {
      if (!jobId) {
        await fetchAnalysisAndRankings(topK);
        return;
      }

      try {
        setNetworkError(null);
        const j = await apiClient.getJob(jobId);
        if (cancelled) return;
        setJob(j);

        if (j.stage === 'extraction_complete' || j.stage === 'ranking') {
          // Partial result: load facets while ranking still runs
          apiClient
            .getAnalysis(analysisId)
            .then((d) => {
              if (!cancelled) setAnalysis(d);
            })
            .catch(() => {});
        }

        if (j.status === 'completed') {
          await fetchAnalysisAndRankings(topK);
        } else if (j.status === 'failed') {
          setLoading(false);
        } else {
          setLoading(false);
          timer = setTimeout(run, 400);
        }
      } catch (err) {
        if (!cancelled) {
          setNetworkError(err instanceof Error ? err.message : 'Mất kết nối khi theo dõi tác vụ.');
          setLoading(false);
        }
      }
    }

    run();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [analysisId, apiClient, fetchAnalysisAndRankings, jobId, topK]);

  // Separate effect for top-k change without re-running extraction
  const handleTopKChange = async (newK: number) => {
    setTopK(newK);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('top_k', String(newK));
    setSearchParams(nextParams, { replace: true });

    try {
      const [p, c] = await Promise.all([
        apiClient.getPaperRankings(analysisId, newK),
        apiClient.getConferenceRankings(analysisId, newK),
      ]);
      setPaperRanking(p);
      setConfRanking(c);
    } catch {
      // keep existing state on transient error
    }
  };

  const shortTitle = analysis?.title
    ? analysis.title.length > 55
      ? `${analysis.title.slice(0, 55)}...`
      : analysis.title
    : analysisId;

  const fromExplore = searchParams.get('from') === 'explore';
  const returnQuery = `tab=${activeTab}&top_k=${topK}${fromExplore ? '&from=explore' : ''}`;
  const activeExtractorModel = runtime?.loaded_model_key || 'Qwen3-4B';

  const handleReExtractLive = async () => {
    if (!analysis) return;
    setReExtracting(true);
    setReExtractError(null);
    try {
      const resp = await apiClient.createAnalysis({
        title: analysis.title,
        abstract: analysis.abstract,
        model_key: activeExtractorModel,
        mode: 'live',
        embedding_model: exploreEmbedding,
        paper_ranking_method: explorePaperMethod,
        conference_ranking_method: exploreConfMethod,
        use_kb_cache: false,
      });
      const params = new URLSearchParams();
      if (fromExplore) params.set('from', 'explore');
      if (resp.status !== 'completed' && resp.job_id) {
        params.set('job_id', resp.job_id);
      }
      const qs = params.toString();
      navigate(`/analyses/${encodeURIComponent(resp.analysis_id)}${qs ? `?${qs}` : ''}`, {
        state: fromExplore ? { from: 'explore' } : undefined,
      });
    } catch (err) {
      setReExtractError(
        err instanceof Error
          ? err.message
          : 'Không thể chạy trích xuất trực tiếp. Hãy kiểm tra model đang nạp trong bảng Hệ thống.'
      );
    } finally {
      setReExtracting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-xs text-slate-500">
        <Link to={fromExplore ? '/' : '/analyze'} className="hover:text-blue-600 font-medium">
          {fromExplore ? 'Tra cứu bài báo' : 'Phân tích manuscript'}
        </Link>
        <ChevronRight className="h-3.5 w-3.5" />
        <span className="truncate font-medium text-slate-800">{shortTitle}</span>
      </nav>

      {/* Job progress banner */}
      {job && job.status !== 'completed' && (
        <div
          className={`rounded-xl border p-4 flex items-center justify-between gap-4 ${
            job.status === 'failed'
              ? 'border-rose-200 bg-rose-50 text-rose-800'
              : 'border-blue-200 bg-blue-50 text-blue-900'
          }`}
        >
          <div className="flex items-center gap-3">
            {job.status === 'failed' ? (
              <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0" />
            ) : (
              <Loader2 className="h-5 w-5 animate-spin text-blue-600 shrink-0" />
            )}
            <div>
              <div className="text-sm font-semibold">
                {job.status === 'failed' ? 'Tác vụ phân tích gặp lỗi' : job.stage_label}
              </div>
              {job.error && <div className="text-xs mt-0.5">{job.error.message}</div>}
            </div>
          </div>
          {job.status === 'failed' && (
            <button
              type="button"
              onClick={() => navigate('/')}
              className="rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-rose-700"
            >
              Quay lại chạy lại
            </button>
          )}
        </div>
      )}

      {/* Network error banner with safe reconnect */}
      {networkError && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 flex flex-wrap items-center justify-between gap-3 text-sm text-amber-900">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="h-4.5 w-4.5 text-amber-600 shrink-0" />
            <span>{networkError}</span>
          </div>
          <button
            type="button"
            onClick={() => fetchAnalysisAndRankings(topK)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-900 hover:bg-amber-100"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Thử kết nối lại
          </button>
        </div>
      )}

      {loading && !analysis && (
        <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-sm text-slate-500">
          <Loader2 className="mx-auto h-6 w-6 animate-spin text-blue-600 mb-2" />
          Đang tải dữ liệu phân tích...
        </div>
      )}

      {analysis && (
        <>
          {/* A. Manuscript Summary */}
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-1.5 flex-1 min-w-[280px]">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${
                      SOURCE_LABELS[analysis.provenance.source].className
                    }`}
                  >
                    Nguồn: {SOURCE_LABELS[analysis.provenance.source].label}
                  </span>
                  <span className="inline-flex items-center rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-700">
                    Extractor: {analysis.provenance.model_display_name}
                  </span>
                  {analysis.timings && (
                    <span className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 py-0.5 text-xs text-slate-600 shadow-2xs">
                      <Clock className="h-3.5 w-3.5 text-blue-600" />
                      <span>
                        Tổng thời gian:{' '}
                        <strong className="text-slate-800 font-semibold">
                          {(((analysis.timings.extraction_ms || 0) + (analysis.timings.ranking_ms || 0)) / 1000).toFixed(2)}s
                        </strong>
                      </span>
                      <span className="text-slate-400 font-normal">
                        (Trích xuất: {analysis.timings.extraction_ms ? (analysis.timings.extraction_ms / 1000).toFixed(2) : '0.00'}s • Xếp hạng: {analysis.timings.ranking_ms ? (analysis.timings.ranking_ms / 1000).toFixed(2) : '0.00'}s)
                      </span>
                    </span>
                  )}
                </div>

                <h1 className="text-xl font-bold text-slate-900 leading-snug">
                  <HighlightedText
                    text={analysis.title}
                    field="title"
                    activeHighlight={activeHighlight}
                  />
                </h1>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {analysis.provenance.source !== 'live' && (
                  <button
                    type="button"
                    disabled={reExtracting}
                    onClick={handleReExtractLive}
                    title={`Chạy trích xuất 5-Facet trực tiếp bằng model hiện tại (${activeExtractorModel})`}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-60 transition"
                  >
                    {reExtracting ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5" />
                    )}
                    {reExtracting
                      ? 'Đang khởi chạy...'
                      : `Trích xuất lại (Live • ${activeExtractorModel})`}
                  </button>
                )}
                {!fromExplore && (
                  <button
                    type="button"
                    onClick={() =>
                      navigate('/analyze', {
                        state: {
                          title: analysis.title,
                          abstract: analysis.abstract,
                          fromAnalysisId: analysis.analysis_id,
                          mode: analysis.provenance.source === 'precomputed' ? 'precomputed' : 'live',
                        },
                      })
                    }
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    <Edit3 className="h-3.5 w-3.5" />
                    Chỉnh sửa và phân tích lại
                  </button>
                )}
                <button
                  type="button"
                  onClick={() =>
                    navigate('/compare', {
                      state: { title: analysis.title, abstract: analysis.abstract },
                    })
                  }
                  className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100"
                >
                  <GitCompare className="h-3.5 w-3.5" />
                  So sánh extractor
                </button>
              </div>
            </div>

            {reExtractError && (
              <div className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-xs text-rose-700">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>{reExtractError}</span>
              </div>
            )}

            {/* Expandable Abstract */}
            <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Abstract nguồn {activeHighlight && '— Đang làm nổi bật bằng chứng'}
                </span>
                <div className="flex items-center gap-3">
                  {activeHighlight && (
                    <button
                      type="button"
                      onClick={() => setActiveHighlight(null)}
                      className="text-xs font-medium text-blue-600 hover:underline"
                    >
                      Bỏ highlight
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setAbstractExpanded(!abstractExpanded)}
                    className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-slate-900"
                  >
                    {abstractExpanded ? (
                      <>
                        Thu gọn <ChevronUp className="h-3.5 w-3.5" />
                      </>
                    ) : (
                      <>
                        Mở rộng <ChevronDown className="h-3.5 w-3.5" />
                      </>
                    )}
                  </button>
                </div>
              </div>
              {abstractExpanded ? (
                <p className="text-sm leading-relaxed text-slate-700">
                  <HighlightedText
                    text={analysis.abstract}
                    field="abstract"
                    activeHighlight={activeHighlight}
                  />
                </p>
              ) : (
                <p className="text-sm text-slate-500 line-clamp-2">{analysis.abstract}</p>
              )}
            </div>
          </section>

          {/* Tier 2: Horizontal 5 Facets & Evidence */}
          <section className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-bold text-slate-900">Năm Facet & Bằng chứng</h2>
              <span className="text-xs text-slate-500">Bấm câu dẫn chứng để làm nổi bật trong Abstract</span>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {FACET_ORDER.map((facetKey) => {
                const meta = FACET_META[facetKey];
                const output = analysis.facets[facetKey];

                return (
                  <div
                    key={facetKey}
                    className={`rounded-xl border border-slate-200 border-l-4 ${meta.borderClass} bg-white p-3.5 shadow-xs space-y-2.5 flex flex-col`}
                  >
                    <div className="flex items-center justify-between gap-1">
                      <FacetBadge facet={facetKey} compact />
                      {output.status === 'ok' && (
                        <span className="text-[11px] text-slate-400">
                          {output.items.length}
                        </span>
                      )}
                    </div>

                    {output.status === 'empty' && (
                      <p className="text-xs italic text-slate-400">Chưa đề cập.</p>
                    )}

                    {output.status === 'not_analyzed' && (
                      <p className="text-xs italic text-amber-700">Chưa phân tích.</p>
                    )}

                    {output.status === 'error' && (
                      <p className="text-xs text-rose-600">
                        Lỗi xử lý: {output.error_message || 'Không xác định'}
                      </p>
                    )}

                    {output.status === 'ok' && (
                      <div className="space-y-2 flex-1">
                        {output.items.map((item, idx) => (
                          <div key={idx} className="space-y-1">
                            <div className="text-xs font-semibold text-slate-900 leading-snug">
                              • {item.concept}
                            </div>
                            {item.evidences.slice(0, 1).map((ev, evIdx) => {
                              const isSelected =
                                activeHighlight?.facet === facetKey &&
                                activeHighlight.evidence.quote === ev.quote;
                              return (
                                <button
                                  key={evIdx}
                                  type="button"
                                  onClick={() => {
                                    if (isSelected) {
                                      setActiveHighlight(null);
                                    } else {
                                      setAbstractExpanded(true);
                                      setActiveHighlight({ facet: facetKey, evidence: ev });
                                    }
                                  }}
                                  className={`w-full text-left rounded-lg border px-2 py-1.5 text-[11px] transition flex items-start gap-1.5 ${
                                    isSelected
                                      ? 'border-blue-400 bg-blue-50 text-blue-950'
                                      : 'border-slate-100 bg-slate-50 text-slate-600 hover:border-slate-300 hover:bg-slate-100'
                                  }`}
                                >
                                  <Quote className="h-3 w-3 shrink-0 mt-0.5 text-slate-400" />
                                  <span className="line-clamp-2 italic leading-snug">
                                    &ldquo;{ev.quote}&rdquo;
                                  </span>
                                </button>
                              );
                            })}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          {/* Tier 3: 2 Equal Side-by-Side Columns (Papers Left | Conferences Right) */}
          <section className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-base font-bold text-slate-900">
                Kết quả Khuyến nghị (Bài báo & Hội nghị)
              </h2>
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-500 font-medium">Hiển thị Top-k:</span>
                {[5, 10, 20].map((k) => (
                  <button
                    key={k}
                    type="button"
                    onClick={() => handleTopKChange(k)}
                    className={`rounded-md px-2.5 py-1 font-medium transition ${
                      topK === k
                        ? 'bg-blue-600 text-white'
                        : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    {k}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 items-start">
              {/* Left Column: Paper Recommendations */}
              <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
                <div className="flex items-center justify-between gap-2 border-b border-slate-200 bg-blue-50/50 px-4 py-3">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4.5 w-4.5 text-blue-600" />
                    <h3 className="text-sm font-bold text-slate-900">Gợi ý Bài báo liên quan</h3>
                  </div>
                  {paperRanking?.score_unit && (
                    <span className="rounded-md border border-blue-200 bg-white px-2 py-0.5 font-mono text-[10px] text-blue-700">
                      {paperRanking.score_unit}
                    </span>
                  )}
                </div>

                <div className="p-4 space-y-3">
                  {paperRanking?.status === 'unavailable' || paperRanking?.status === 'failed' ? (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                      Gợi ý bài báo hiện chưa khả dụng: {paperRanking.error_message || 'Thiếu artifact ranking.'}
                    </div>
                  ) : !paperRanking ? (
                    <div className="py-10 text-center text-sm text-slate-500">
                      <Loader2 className="mx-auto h-5 w-5 animate-spin text-blue-600 mb-2" />
                      Đang xếp hạng bài báo...
                    </div>
                  ) : (
                    <>
                      <div className="flex items-start gap-2 rounded-xl border border-blue-100 bg-blue-50/50 px-3 py-2 text-xs text-blue-950 leading-relaxed">
                        <Info className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
                        <span>{paperRanking.scorer_note}</span>
                      </div>

                      <div className="divide-y divide-slate-100">
                        {paperRanking.items.map((item) => {
                          const vLabel = cleanVenue(item.venue);
                          return (
                            <div
                              key={item.paper_id}
                              className="py-3.5 first:pt-1 last:pb-1 flex flex-col gap-2"
                            >
                              <div className="flex items-start justify-between gap-3">
                                <div className="flex items-start gap-2.5 min-w-0">
                                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-bold text-blue-700 border border-blue-200">
                                    #{item.rank}
                                  </span>
                                  <div className="space-y-0.5 min-w-0">
                                    <Link
                                      to={`/analyses/${encodeURIComponent(analysisId)}/papers/${encodeURIComponent(item.paper_id)}?${returnQuery}`}
                                      className="text-sm font-semibold text-slate-900 hover:text-blue-700 leading-snug block"
                                    >
                                      {item.title}
                                    </Link>
                                    <div className="text-xs text-slate-500">
                                      {item.year ? `${item.year}` : ''}
                                      {vLabel ? `${item.year ? ' • ' : ''}${vLabel}` : ''}
                                      {item.authors && item.authors.length > 0
                                        ? ` • ${item.authors.slice(0, 3).join(', ')}`
                                        : ''}
                                    </div>
                                  </div>
                                </div>

                                <div className="text-right shrink-0">
                                  <div className="text-sm font-bold text-blue-700">
                                    {(item.total_score * 100).toFixed(1)}%
                                  </div>
                                  <div className="text-[10px] text-slate-400">độ khớp</div>
                                </div>
                              </div>

                              <div className="flex flex-wrap items-center justify-between gap-2 pl-8">
                                <div className="flex flex-wrap items-center gap-1">
                                  {item.supporting_facets.map((f) => (
                                    <FacetBadge key={f} facet={f} compact />
                                  ))}
                                </div>

                                <Link
                                  to={`/analyses/${encodeURIComponent(analysisId)}/papers/${encodeURIComponent(item.paper_id)}?${returnQuery}`}
                                  className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-800"
                                >
                                  Xem giải thích
                                  <ArrowRight className="h-3.5 w-3.5" />
                                </Link>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Right Column: Conference Recommendations */}
              <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
                <div className="flex items-center justify-between gap-2 border-b border-slate-200 bg-indigo-50/50 px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Award className="h-4.5 w-4.5 text-indigo-600" />
                    <h3 className="text-sm font-bold text-slate-900">
                      {fromExplore
                        ? 'Hội nghị liên quan bạn có thể quan tâm'
                        : 'Gợi ý Hội nghị phù hợp'}
                    </h3>
                  </div>
                  {confRanking?.score_unit && (
                    <span className="rounded-md border border-indigo-200 bg-white px-2 py-0.5 font-mono text-[10px] text-indigo-700">
                      {confRanking.score_unit}
                    </span>
                  )}
                </div>

                <div className="p-4 space-y-3">
                  {confRanking?.status === 'unavailable' || confRanking?.status === 'failed' ? (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                      Gợi ý hội nghị hiện chưa khả dụng: {confRanking.error_message || 'Thiếu hồ sơ hội nghị.'}
                    </div>
                  ) : !confRanking ? (
                    <div className="py-10 text-center text-sm text-slate-500">
                      <Loader2 className="mx-auto h-5 w-5 animate-spin text-indigo-600 mb-2" />
                      Đang xếp hạng hội nghị...
                    </div>
                  ) : (
                    <>
                      <div className="flex items-start gap-2 rounded-xl border border-indigo-100 bg-indigo-50/50 px-3 py-2 text-xs text-indigo-950 leading-relaxed">
                        <Info className="h-4 w-4 text-indigo-600 shrink-0 mt-0.5" />
                        <span>{confRanking.disclaimer}</span>
                      </div>

                      <div className="divide-y divide-slate-100">
                        {confRanking.items.map((conf) => (
                          <div
                            key={conf.conference_id}
                            className="py-3.5 first:pt-1 last:pb-1 flex flex-col gap-2"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex items-start gap-2.5 min-w-0">
                                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-xs font-bold text-indigo-700 border border-indigo-200">
                                  #{conf.rank}
                                </span>
                                <div className="space-y-0.5 min-w-0">
                                  <Link
                                    to={`/analyses/${encodeURIComponent(analysisId)}/conferences/${encodeURIComponent(conf.conference_id)}?${returnQuery}`}
                                    className="text-sm font-semibold text-slate-900 hover:text-indigo-700 leading-snug block"
                                  >
                                    <span className="font-bold text-indigo-700 mr-1.5">
                                      [{conf.acronym}]
                                    </span>
                                    {conf.name}
                                  </Link>
                                  {conf.historical_paper_count != null && (
                                    <div className="text-xs text-slate-500">
                                      Hồ sơ từ {conf.historical_paper_count} bài báo lịch sử
                                    </div>
                                  )}
                                </div>
                              </div>

                              <div className="text-right shrink-0">
                                <div className="text-sm font-bold text-indigo-700">
                                  {(conf.match_score * 100).toFixed(1)}%
                                </div>
                                <div className="text-[10px] text-slate-400">phù hợp</div>
                              </div>
                            </div>

                            <div className="flex flex-wrap items-center justify-between gap-2 pl-8">
                              <div className="flex flex-wrap items-center gap-1">
                                {conf.prominent_facets.map((f) => (
                                  <FacetBadge key={f} facet={f} compact />
                                ))}
                              </div>

                              <Link
                                to={`/analyses/${encodeURIComponent(analysisId)}/conferences/${encodeURIComponent(conf.conference_id)}?${returnQuery}`}
                                className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                              >
                                Xem giải thích
                                <ArrowRight className="h-3.5 w-3.5" />
                              </Link>
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>

            {analysis.extraction_status === 'completed' && (
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500 px-1 pt-2 border-t border-slate-100">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                  <span>
                    Analysis ID: <code>{analysis.analysis_id}</code> • Đã tự động lưu vào Hồ sơ & Lịch sử
                  </span>
                </div>
                {analysis.timings && (
                  <div className="flex items-center gap-1.5 text-slate-500">
                    <Clock className="h-3.5 w-3.5 text-slate-400" />
                    <span>
                      Tổng thời gian:{' '}
                      <strong className="text-slate-700">
                        {(((analysis.timings.extraction_ms || 0) + (analysis.timings.ranking_ms || 0)) / 1000).toFixed(2)}s
                      </strong>
                    </span>
                  </div>
                )}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
