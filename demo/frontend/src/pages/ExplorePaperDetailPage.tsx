import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  ChevronRight,
  Database,
  ExternalLink,
  Globe,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { useSystem } from '../context/SystemContext';
import type { ExplorePaperItem } from '../types/api';
import { getExploreUserId } from '../utils/userSession';

function cleanVenue(venue?: string | null): string | null {
  if (!venue) return null;
  const v = venue.trim();
  if (!v || v.toUpperCase() === 'CSFCUBE') return null;
  return v;
}

export function ExplorePaperDetailPage() {
  const { paperId = '' } = useParams<{ paperId: string }>();
  const decodedId = decodeURIComponent(paperId);
  const location = useLocation();
  const navigate = useNavigate();
  const {
    apiClient: api,
    exploreEmbedding,
    setExploreEmbedding,
    explorePaperMethod,
    setExplorePaperMethod,
    exploreConfMethod,
    setExploreConfMethod,
    runtime,
  } = useSystem();
  const userId = getExploreUserId();

  const passedPaper =
    (location.state as { paper?: Partial<ExplorePaperItem> } | null)?.paper || null;

  const [paper, setPaper] = useState<ExplorePaperItem | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(true);
  const [autoOpeningKb, setAutoOpeningKb] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openAnalysisForPaper = async (targetPaper: ExplorePaperItem, replaceNav = false) => {
    setAnalyzing(true);
    setError(null);
    try {
      const activeModel = runtime?.loaded_model_key || 'Qwen3-4B';
      const resp = await api.createAnalysis({
        title: targetPaper.title,
        abstract: targetPaper.abstract || targetPaper.abstract_snippet || targetPaper.title,
        model_key: activeModel,
        mode: 'live',
        embedding_model: exploreEmbedding,
        paper_ranking_method: explorePaperMethod,
        conference_ranking_method: exploreConfMethod,
        use_kb_cache: true,
      });
      const params = new URLSearchParams({ from: 'explore' });
      if (resp.status !== 'completed' && resp.job_id) {
        params.set('job_id', resp.job_id);
      }
      navigate(`/analyses/${encodeURIComponent(resp.analysis_id)}?${params.toString()}`, {
        replace: replaceNav,
        state: { from: 'explore' },
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Không thể khởi chạy phân tích bài báo. Hãy kiểm tra model trong bảng Hệ thống.'
      );
      setAnalyzing(false);
      setAutoOpeningKb(false);
    }
  };

  const handleAnalyze = async () => {
    if (!paper) return;
    await openAnalysisForPaper(paper, false);
  };

  useEffect(() => {
    let cancelled = false;
    window.scrollTo({ top: 0, behavior: 'smooth' });
    setError(null);

    async function initPreview() {
      let resolvedPaper: ExplorePaperItem | null = null;

      if (passedPaper?.title && passedPaper?.abstract) {
        resolvedPaper = {
          paper_id: decodedId,
          title: passedPaper.title,
          abstract: passedPaper.abstract,
          abstract_snippet: passedPaper.abstract_snippet || passedPaper.abstract.slice(0, 240),
          authors: passedPaper.authors || [],
          year: passedPaper.year ?? null,
          venue: passedPaper.venue ?? null,
          url: passedPaper.url ?? null,
          cited_by_count: passedPaper.cited_by_count ?? null,
          source: passedPaper.source || 'openalex',
          has_facets: Boolean(passedPaper.has_facets),
        };
      } else {
        setLoadingPreview(true);
        try {
          const prev = await api.explorePreviewPaper(decodedId, userId);
          resolvedPaper = prev.paper;
        } catch (err) {
          if (!cancelled) {
            setError(err instanceof Error ? err.message : 'Không tìm thấy nội dung bài báo.');
            setLoadingPreview(false);
          }
          return;
        }
      }

      if (cancelled || !resolvedPaper) return;

      setPaper(resolvedPaper);
      setLoadingPreview(false);

      // Papers already in the 4,210 KB corpus have pre-extracted 5-Facet data:
      // jump straight to the analysis result view without requiring an extra click.
      if (resolvedPaper.source === 'local') {
        setAutoOpeningKb(true);
        await openAnalysisForPaper(resolvedPaper, true);
      }
    }

    initPreview();
    return () => {
      cancelled = true;
    };
  }, [decodedId]);

  const renderSourceBadge = (source: string, year?: number | null) => {
    if (source === 'openalex') {
      return (
        <span className="inline-flex items-center gap-1 rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-xs font-semibold text-sky-700">
          <Globe className="h-3.5 w-3.5" />
          OpenAlex{year ? ` • ${year}` : ''}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
        <Database className="h-3.5 w-3.5" />
        Kho bài báo{year ? ` • ${year}` : ''}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb & Back */}
      <div className="flex items-center justify-between gap-3">
        <nav className="flex items-center gap-1.5 text-xs text-slate-500">
          <Link to="/" className="font-medium text-blue-600 hover:underline">
            Tra cứu bài báo
          </Link>
          <ChevronRight className="h-3.5 w-3.5 text-slate-400" />
          <span className="font-medium text-slate-700 truncate max-w-[360px]">
            {paper?.title || decodedId}
          </span>
        </nav>

        <button
          type="button"
          onClick={() => navigate('/')}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-2xs hover:bg-slate-50 transition"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Quay lại tra cứu
        </button>
      </div>

      {loadingPreview ? (
        <div className="flex items-center justify-center gap-2.5 rounded-2xl border border-slate-200 bg-white py-16 text-sm text-slate-500 shadow-2xs">
          <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
          Đang tải nội dung bài báo...
        </div>
      ) : error && !paper ? (
        <div className="flex items-center gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      ) : paper ? (
        <div className="space-y-6">
          <article className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 shadow-2xs space-y-6">
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-5">
              <div className="min-w-0 flex-1 space-y-2.5">
                <div className="flex flex-wrap items-center gap-2">
                  {renderSourceBadge(paper.source, paper.year)}
                  {autoOpeningKb && (
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      Đang nạp 5-Facet có sẵn & xếp hạng...
                    </span>
                  )}
                </div>

                <h1 className="text-xl sm:text-2xl font-bold text-slate-900 leading-snug">
                  {paper.title}
                </h1>

                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  {paper.authors.length > 0 && (
                    <span className="font-medium text-slate-700">
                      {paper.authors.slice(0, 6).join(', ')}
                    </span>
                  )}
                  {cleanVenue(paper.venue) && <span>• {cleanVenue(paper.venue)}</span>}
                  {typeof paper.cited_by_count === 'number' && (
                    <span>• {paper.cited_by_count.toLocaleString()} trích dẫn</span>
                  )}
                  {paper.url && (
                    <a
                      href={paper.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 font-semibold text-blue-600 hover:underline"
                    >
                      Mở liên kết gốc <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  )}
                </div>
              </div>

              {!autoOpeningKb && (
                <button
                  type="button"
                  disabled={analyzing}
                  onClick={handleAnalyze}
                  className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 disabled:opacity-60 transition"
                >
                  {analyzing ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4" />
                  )}
                  {analyzing ? 'Đang khởi chạy...' : 'Phân tích bài báo'}
                </button>
              )}
            </div>

            {error && (
              <div className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-700">
                <AlertCircle className="h-4 w-4 shrink-0" />
                {error}
              </div>
            )}

            {paper.abstract && (
              <div className="space-y-2">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Tóm tắt (Abstract)
                </h2>
                <p className="rounded-xl border border-slate-100 bg-slate-50/70 p-4 text-sm leading-relaxed text-slate-700">
                  {paper.abstract}
                </p>
              </div>
            )}

            {/* Compact Ranking Method Controls (for OpenAlex / manual trigger) */}
            {!autoOpeningKb && (
              <div className="grid grid-cols-1 gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-4 sm:grid-cols-3">
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Mô hình Embedding
                  </span>
                  <select
                    value={exploreEmbedding}
                    onChange={(e) => setExploreEmbedding(e.target.value as 'bert-base' | 'tfidf')}
                    className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs font-semibold text-slate-700 focus:border-blue-500 focus:outline-none"
                  >
                    <option value="bert-base">BERT-base-uncased (768d)</option>
                    <option value="tfidf">TF-IDF Cosine (Baseline nhẹ)</option>
                  </select>
                </div>

                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Phương pháp khuyến nghị Bài báo
                  </span>
                  <select
                    value={explorePaperMethod}
                    onChange={(e) =>
                      setExplorePaperMethod(
                        e.target.value as 'weighted_facets' | 'equal_facets' | 'whole_text'
                      )
                    }
                    className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs font-semibold text-slate-700 focus:border-blue-500 focus:outline-none"
                  >
                    <option value="weighted_facets">Weighted 5-Facet (0.4/0.2/0.2/0.1/0.1)</option>
                    <option value="equal_facets">Equal 5-Facet (Trọng số đều 0.2)</option>
                    <option value="whole_text">Whole-Text (So sánh toàn văn)</option>
                  </select>
                </div>

                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Phương pháp khuyến nghị Hội nghị
                  </span>
                  <select
                    value={exploreConfMethod}
                    onChange={(e) =>
                      setExploreConfMethod(
                        e.target.value as 'gated_knn' | 'flat_facet_knn' | 'whole_text_knn'
                      )
                    }
                    className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs font-semibold text-slate-700 focus:border-blue-500 focus:outline-none"
                  >
                    <option value="gated_knn">Gated 5-Facet k-NN (Cổng Problem)</option>
                    <option value="flat_facet_knn">Flat 5-Facet k-NN (Phẳng)</option>
                    <option value="whole_text_knn">Whole-Text k-NN (Toàn văn)</option>
                  </select>
                </div>
              </div>
            )}
          </article>

          {/* Progressive loading skeletons for 5-Facet & Rankings while KB fast-path finishes */}
          {autoOpeningKb && (
            <div className="space-y-6">
              <section className="space-y-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                  Đang tải 5-Facet trích xuất...
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div
                      key={i}
                      className="h-36 animate-pulse rounded-xl border border-slate-200 bg-white p-4 space-y-2.5"
                    >
                      <div className="h-5 w-20 rounded-md bg-slate-200" />
                      <div className="h-3 w-full rounded bg-slate-100" />
                      <div className="h-3 w-4/5 rounded bg-slate-100" />
                    </div>
                  ))}
                </div>
              </section>

              <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                    <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                    Đang xếp hạng Bài báo liên quan...
                  </div>
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-100" />
                  ))}
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                    <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
                    Đang xếp hạng Hội nghị liên quan...
                  </div>
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-100" />
                  ))}
                </div>
              </section>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
