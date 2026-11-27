import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
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
  ConferenceDetail,
  ConferenceExplanationResponse,
  RepresentativePaperItem,
  RepresentativePapersResponse,
} from '../types/api';

export function ConferenceDetailPage() {
  const { analysisId = '', conferenceId = '' } = useParams<{
    analysisId: string;
    conferenceId: string;
  }>();
  const [searchParams] = useSearchParams();
  const { apiClient } = useSystem();

  const returnQuery = searchParams.toString();
  const backUrl = `/analyses/${encodeURIComponent(analysisId)}${
    returnQuery ? `?${returnQuery}` : ''
  }`;

  const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null);
  const [conference, setConference] = useState<ConferenceDetail | null>(null);
  const [explanation, setExplanation] = useState<ConferenceExplanationResponse | null>(null);
  const [repPapers, setRepPapers] = useState<RepresentativePapersResponse | null>(null);
  const [selectedExternalPaper, setSelectedExternalPaper] =
    useState<RepresentativePaperItem | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      apiClient.getAnalysis(analysisId),
      apiClient.getConference(conferenceId),
      apiClient.getConferenceExplanation(analysisId, conferenceId),
      apiClient.getRepresentativePapers(analysisId, conferenceId, 5),
    ])
      .then(([ana, conf, exp, reps]) => {
        if (cancelled) return;
        setAnalysis(ana);
        setConference(conf);
        setExplanation(exp);
        setRepPapers(reps);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Không tải được hồ sơ hội nghị.');
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [analysisId, apiClient, conferenceId]);

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
          <span className="font-medium text-slate-800">
            Hội nghị ({conference?.acronym || conferenceId})
          </span>
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
          <Loader2 className="mx-auto h-6 w-6 animate-spin text-indigo-600 mb-2" />
          Đang tải hồ sơ hội nghị và bài lịch sử...
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          {error}
        </div>
      )}

      {!loading && conference && explanation && (
        <>
          {/* Conference Profile Header */}
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-1.5 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-md bg-indigo-100 px-2.5 py-0.5 text-xs font-bold text-indigo-800">
                    {conference.acronym}
                  </span>
                  <span className="text-xs text-slate-500">
                    {conference.profile_built_from}
                  </span>
                </div>
                <h1 className="text-xl font-bold text-slate-900">{conference.name}</h1>
              </div>

              {conference.url && (
                <a
                  href={conference.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3.5 py-2 text-xs font-semibold text-indigo-700 hover:bg-indigo-100"
                >
                  Trang nguồn hội nghị
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
            </div>

            <p className="text-sm text-slate-700 leading-relaxed">
              {conference.topic_profile_description}
            </p>

            <div className="grid grid-cols-1 gap-3 rounded-xl border border-slate-100 bg-slate-50 p-4 text-xs text-slate-600 sm:grid-cols-3">
              <div>
                <span className="font-semibold text-slate-800">Số bài lịch sử:</span>{' '}
                {conference.historical_paper_count} bài
              </div>
              <div>
                <span className="font-semibold text-slate-800">Khoảng năm:</span>{' '}
                {conference.year_range || 'Không rõ'}
              </div>
              <div>
                <span className="font-semibold text-slate-800">Độ phủ dữ liệu:</span>{' '}
                {conference.coverage_note || 'Theo dữ liệu corpus hiện hành'}
              </div>
              {conference.cutoff_note && (
                <div className="sm:col-span-3 text-slate-500 pt-1 border-t border-slate-200/70">
                  {conference.cutoff_note}
                </div>
              )}
            </div>

            {conference.sparse_profile_warning && (
              <div className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-900">
                <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                <span>{conference.sparse_profile_warning}</span>
              </div>
            )}
          </section>

          {/* Match Score & Disclaimer */}
          <section className="rounded-2xl border border-indigo-200 bg-indigo-50/40 p-6 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-bold text-slate-900">
                  Mức phù hợp nội dung với manuscript
                </h2>
                <p className="text-xs text-slate-600 mt-0.5">
                  Scorer: <code>{explanation.scorer_name}</code> • {explanation.formula_description}
                </p>
              </div>
              <div className="rounded-xl border border-indigo-200 bg-white px-4 py-2 text-right shadow-xs">
                <div className="text-xl font-bold text-indigo-700">
                  {explanation.match_score.toFixed(3)}
                </div>
                <div className="text-[11px] text-slate-500">{explanation.score_unit}</div>
              </div>
            </div>

            <p className="text-sm text-slate-800 leading-relaxed">
              {explanation.summary_explanation}
            </p>

            <div className="flex items-start gap-2 rounded-lg border border-indigo-100 bg-white/80 px-3 py-2 text-xs text-indigo-900">
              <Info className="h-4 w-4 text-indigo-600 shrink-0 mt-0.5" />
              <span>{explanation.disclaimer}</span>
            </div>
          </section>

          {/* 5-Facet Profile Alignment */}
          <section className="space-y-3">
            <h2 className="text-base font-bold text-slate-900">
              Giải thích đóng góp theo 5 Facet
            </h2>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {explanation.facet_scores.map((fs) => (
                <div
                  key={fs.facet}
                  className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs space-y-2.5"
                >
                  <div className="flex items-center justify-between">
                    <FacetBadge facet={fs.facet} />
                    <div className="text-xs text-slate-600">
                      Tương đồng:{' '}
                      <strong>
                        {fs.similarity_score != null ? fs.similarity_score.toFixed(3) : 'N/A'}
                      </strong>{' '}
                      • Đóng góp:{' '}
                      <strong className="text-indigo-700">
                        {fs.contribution_score != null ? fs.contribution_score.toFixed(4) : 'N/A'}
                      </strong>
                    </div>
                  </div>

                  <div className="text-xs space-y-1.5">
                    <div>
                      <span className="font-semibold text-slate-700">Manuscript: </span>
                      {fs.query_concepts.length > 0 ? (
                        <span className="text-slate-600">
                          {fs.query_concepts.map((c) => c.concept).join('; ')}
                        </span>
                      ) : (
                        <span className="italic text-slate-400">Trống</span>
                      )}
                    </div>
                    <div>
                      <span className="font-semibold text-slate-700">Từ khóa hồ sơ {conference.acronym}: </span>
                      <span className="text-slate-600">{fs.profile_keywords.join(', ')}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Representative Historical Papers */}
          {repPapers && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <BookOpen className="h-4.5 w-4.5 text-indigo-600" />
                    Bài báo lịch sử đại diện
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">{repPapers.note}</p>
                </div>
                <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-mono text-slate-600">
                  Quy tắc: {repPapers.selection_rule}
                </span>
              </div>

              <div className="divide-y divide-slate-100">
                {repPapers.items.map((rp) => (
                  <div key={rp.paper_id} className="py-3.5 first:pt-1 last:pb-1 space-y-2">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="space-y-1">
                        {rp.in_corpus ? (
                          <Link
                            to={`/analyses/${encodeURIComponent(analysisId)}/papers/${encodeURIComponent(rp.paper_id)}?${returnQuery}`}
                            className="text-sm font-semibold text-slate-900 hover:text-indigo-700"
                          >
                            {rp.title}
                          </Link>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setSelectedExternalPaper(rp)}
                            className="text-left text-sm font-semibold text-slate-900 hover:text-indigo-700"
                          >
                            {rp.title}
                          </button>
                        )}
                        <div className="text-xs text-slate-500">
                          {rp.authors?.join(', ')} {rp.year ? `• ${rp.year}` : ''}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {rp.in_corpus ? (
                          <Link
                            to={`/analyses/${encodeURIComponent(analysisId)}/papers/${encodeURIComponent(rp.paper_id)}?${returnQuery}`}
                            className="text-xs font-semibold text-indigo-600 hover:underline"
                          >
                            Xem giải thích
                          </Link>
                        ) : (
                          rp.url && (
                            <a
                              href={rp.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-indigo-700"
                            >
                              Nguồn <ExternalLink className="h-3 w-3" />
                            </a>
                          )
                        )}
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5">
                      {rp.supporting_facets.map((f) => (
                        <FacetBadge key={f} facet={f} compact />
                      ))}
                    </div>

                    {rp.evidences.map((ev, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-1.5 rounded-lg bg-slate-50 px-3 py-1.5 text-xs italic text-slate-600"
                      >
                        <Quote className="h-3.5 w-3.5 shrink-0 mt-0.5 text-slate-400" />
                        <span>"{ev.quote}"</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Simple modal for non-corpus paper metadata */}
          {selectedExternalPaper && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
              <div className="max-w-lg w-full rounded-2xl bg-white p-6 shadow-xl space-y-3">
                <h3 className="text-base font-bold text-slate-900">
                  {selectedExternalPaper.title}
                </h3>
                <p className="text-xs text-slate-500">
                  {selectedExternalPaper.authors?.join(', ')} • {selectedExternalPaper.year}
                </p>
                {selectedExternalPaper.abstract && (
                  <p className="text-sm text-slate-700 leading-relaxed max-h-60 overflow-y-auto">
                    {selectedExternalPaper.abstract}
                  </p>
                )}
                <div className="flex justify-end gap-2 pt-2">
                  {selectedExternalPaper.url && (
                    <a
                      href={selectedExternalPaper.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700"
                    >
                      Mở liên kết nguồn
                    </a>
                  )}
                  <button
                    type="button"
                    onClick={() => setSelectedExternalPaper(null)}
                    className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-medium text-white"
                  >
                    Đóng
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
