import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  ChevronRight,
  ExternalLink,
  Info,
  Loader2,
  Quote,
} from 'lucide-react';
import { FacetBadge } from '../components/FacetBadge';
import { useSystem } from '../context/SystemContext';
import type {
  AnalysisDetail,
  PaperDetail,
  PaperExplanationResponse,
} from '../types/api';

export function PaperDetailPage() {
  const { analysisId = '', paperId = '' } = useParams<{
    analysisId: string;
    paperId: string;
  }>();
  const [searchParams] = useSearchParams();
  const { apiClient } = useSystem();

  const returnQuery = searchParams.toString();
  const backUrl = `/analyses/${encodeURIComponent(analysisId)}${
    returnQuery ? `?${returnQuery}` : ''
  }`;

  const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null);
  const [paper, setPaper] = useState<PaperDetail | null>(null);
  const [explanation, setExplanation] = useState<PaperExplanationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      apiClient.getAnalysis(analysisId),
      apiClient.getPaper(paperId),
      apiClient.getPaperExplanation(analysisId, paperId),
    ])
      .then(([ana, pap, exp]) => {
        if (cancelled) return;
        setAnalysis(ana);
        setPaper(pap);
        setExplanation(exp);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Không tải được chi tiết bài báo.');
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [analysisId, apiClient, paperId]);

  const shortQueryTitle = analysis?.title
    ? analysis.title.length > 42
      ? `${analysis.title.slice(0, 42)}...`
      : analysis.title
    : analysisId;

  return (
    <div className="space-y-6">
      {/* Breadcrumb + Back */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav className="flex items-center gap-1.5 text-xs text-slate-500">
          <Link to="/" className="hover:text-blue-600 font-medium">
            Phân tích manuscript
          </Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <Link to={backUrl} className="hover:text-blue-600 font-medium">
            {shortQueryTitle}
          </Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <span className="font-medium text-slate-800">Chi tiết bài báo ({paperId})</span>
        </nav>

        <Link
          to={backUrl}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Quay lại kết quả
        </Link>
      </div>

      {loading && (
        <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-sm text-slate-500">
          <Loader2 className="mx-auto h-6 w-6 animate-spin text-blue-600 mb-2" />
          Đang tải chi tiết bài báo và giải thích...
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          {error}
        </div>
      )}

      {!loading && paper && explanation && (
        <>
          {/* Paper Metadata & Abstract */}
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-1.5 flex-1">
                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-slate-700">
                    {paper.paper_id}
                  </span>
                  {paper.year && <span>Năm: {paper.year}</span>}
                  {paper.venue && <span>• Hội nghị/Nguồn: {paper.venue}</span>}
                  {paper.doi && <span>• DOI: {paper.doi}</span>}
                </div>

                <h1 className="text-xl font-bold text-slate-900 leading-snug">{paper.title}</h1>
                {paper.authors && paper.authors.length > 0 && (
                  <p className="text-sm text-slate-600">{paper.authors.join(', ')}</p>
                )}
              </div>

              {paper.url && (
                <a
                  href={paper.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3.5 py-2 text-xs font-semibold text-blue-700 hover:bg-blue-100"
                >
                  Mở nguồn bài báo
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
            </div>

            <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4 space-y-1">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Abstract bài được gợi ý
              </div>
              <p className="text-sm leading-relaxed text-slate-700">{paper.abstract}</p>
            </div>
          </section>

          {/* Overall Score & Explanation */}
          <section className="rounded-2xl border border-blue-200 bg-blue-50/40 p-6 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-bold text-slate-900">
                  Giải thích mức độ liên quan với manuscript
                </h2>
                <p className="text-xs text-slate-600 mt-0.5">
                  Scorer: <code>{explanation.scorer_name}</code> • {explanation.formula_description}
                </p>
              </div>
              <div className="rounded-xl border border-blue-200 bg-white px-4 py-2 text-right shadow-xs">
                <div className="text-xl font-bold text-blue-700">
                  {explanation.total_score.toFixed(3)}
                </div>
                <div className="text-[11px] text-slate-500">{explanation.score_unit}</div>
              </div>
            </div>

            <p className="text-sm text-slate-800 leading-relaxed">
              {explanation.summary_explanation}
            </p>
          </section>

          {/* 5-Facet Breakdown */}
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900">
                Đối chiếu theo từng Facet (Manuscript ↔ Bài gợi ý)
              </h2>
              <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                <Info className="h-3.5 w-3.5" />
                Các thành phần điểm trích xuất trực tiếp từ scorer
              </span>
            </div>

            <div className="space-y-3">
              {explanation.facet_breakdowns.map((row) => (
                <div
                  key={row.facet}
                  className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs space-y-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-100">
                    <FacetBadge facet={row.facet} />
                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600">
                      <span>
                        Tương đồng:{' '}
                        <strong className="text-slate-900">
                          {row.similarity_score != null ? row.similarity_score.toFixed(3) : 'N/A'}
                        </strong>
                      </span>
                      <span>
                        Trọng số:{' '}
                        <strong className="text-slate-900">
                          {row.weight != null ? row.weight.toFixed(2) : 'N/A'}
                        </strong>
                      </span>
                      <span className="rounded bg-blue-50 px-2 py-0.5 text-blue-800 font-semibold">
                        Đóng góp:{' '}
                        {row.contribution_score != null
                          ? row.contribution_score.toFixed(4)
                          : 'N/A'}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    {/* Query side */}
                    <div className="rounded-lg border border-slate-100 bg-slate-50/70 p-3 space-y-2">
                      <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                        Manuscript của bạn
                      </div>
                      {row.query_status === 'empty' || row.query_concepts.length === 0 ? (
                        <p className="text-xs italic text-slate-400">Không có dữ liệu facet này.</p>
                      ) : (
                        row.query_concepts.map((c, idx) => (
                          <div key={idx} className="space-y-1">
                            <div className="text-xs font-semibold text-slate-800">• {c.concept}</div>
                            {c.evidences.map((ev, eIdx) => (
                              <div
                                key={eIdx}
                                className="flex items-start gap-1.5 pl-2 text-[11px] italic text-slate-600"
                              >
                                <Quote className="h-3 w-3 shrink-0 mt-0.5 text-slate-400" />
                                <span>"{ev.quote}"</span>
                              </div>
                            ))}
                          </div>
                        ))
                      )}
                    </div>

                    {/* Target paper side */}
                    <div className="rounded-lg border border-slate-100 bg-slate-50/70 p-3 space-y-2">
                      <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                        Bài báo được gợi ý
                      </div>
                      {row.target_status === 'empty' || row.target_concepts.length === 0 ? (
                        <p className="text-xs italic text-slate-400">
                          Thiếu thông tin / không ghi nhận concept ở facet này.
                        </p>
                      ) : (
                        row.target_concepts.map((c, idx) => (
                          <div key={idx} className="space-y-1">
                            <div className="text-xs font-semibold text-slate-800">• {c.concept}</div>
                            {c.evidences.map((ev, eIdx) => (
                              <div
                                key={eIdx}
                                className="flex items-start gap-1.5 pl-2 text-[11px] italic text-slate-600"
                              >
                                <Quote className="h-3 w-3 shrink-0 mt-0.5 text-slate-400" />
                                <span>"{ev.quote}"</span>
                              </div>
                            ))}
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {row.note && (
                    <p className="text-xs text-slate-500 italic">{row.note}</p>
                  )}
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
