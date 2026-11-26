import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Database,
  Globe,
  Layers,
  Loader2,
  Search,
  Sparkles,
  X,
} from 'lucide-react';
import { FACET_META } from '../constants/facets';
import { useSystem } from '../context/SystemContext';
import type {
  ExplorePaperItem,
  ExploreRecommendationItem,
  ExploreRecommendationsResponse,
  ExploreSearchResponse,
} from '../types/api';
import {
  getExploreUserId,
  notifyProfileUpdated,
  PROFILE_UPDATED_EVENT,
} from '../utils/userSession';

type SearchScope = 'all' | 'local' | 'external';

function cleanVenue(venue?: string | null): string | null {
  if (!venue) return null;
  const v = venue.trim();
  if (!v || v.toUpperCase() === 'CSFCUBE') return null;
  return v;
}

const QUICK_TOPICS = [
  'Graph Neural Networks',
  'DeepSeek-R1',
  'Retrieval-Augmented Generation',
  'Attention Is All You Need',
  'Fake News Detection',
  'Diffusion Models',
];

const PAGE_SIZE = 18;

export function ExplorePage() {
  const navigate = useNavigate();
  const {
    apiClient: api,
    exploreEmbedding,
    setExploreEmbedding,
    explorePaperMethod,
    setExplorePaperMethod,
  } = useSystem();
  const userId = getExploreUserId();

  // Search state
  const [query, setQuery] = useState('');
  const [searchScope, setSearchScope] = useState<SearchScope>('all');
  const [searchRes, setSearchRes] = useState<ExploreSearchResponse | null>(null);
  const [searching, setSearching] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const searchBoxRef = useRef<HTMLDivElement>(null);

  // Personalized feed state with clean pagination
  const [page, setPage] = useState(1);
  const [feed, setFeed] = useState<ExploreRecommendationsResponse | null>(null);
  const [loadingFeed, setLoadingFeed] = useState(false);
  const feedSectionRef = useRef<HTMLElement>(null);

  const fetchFeedPage = async (
    targetPage: number,
    emb: 'bert-base' | 'tfidf' = exploreEmbedding,
    m: 'weighted_facets' | 'equal_facets' | 'whole_text' = explorePaperMethod,
    shouldNotifyProfile = false
  ) => {
    setLoadingFeed(true);
    try {
      const offset = (targetPage - 1) * PAGE_SIZE;
      const res = await api.exploreGetRecommendations(userId, emb, m, PAGE_SIZE, offset);
      setFeed(res);
      if (shouldNotifyProfile) {
        notifyProfileUpdated(res.profile_size);
      }
    } catch {
      // ignore
    } finally {
      setLoadingFeed(false);
    }
  };

  // Reset to page 1 when embedding or paper method changes
  useEffect(() => {
    setPage(1);
    fetchFeedPage(1, exploreEmbedding, explorePaperMethod, false);
  }, [exploreEmbedding, explorePaperMethod]);

  // Re-fetch page 1 whenever profile is modified from ProfileDrawer
  useEffect(() => {
    const onUpdated = () => {
      setPage(1);
      fetchFeedPage(1, exploreEmbedding, explorePaperMethod, false);
    };
    window.addEventListener(PROFILE_UPDATED_EVENT, onUpdated);
    return () => window.removeEventListener(PROFILE_UPDATED_EVENT, onUpdated);
  }, [api, exploreEmbedding, explorePaperMethod, userId]);

  const handlePageChange = (nextPage: number) => {
    setPage(nextPage);
    fetchFeedPage(nextPage, exploreEmbedding, explorePaperMethod, false);
    feedSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const totalAvailable = Math.max(
    0,
    (feed?.corpus_size || 4210) - (feed?.profile_size || 0)
  );
  const totalPages = Math.max(1, Math.ceil(totalAvailable / PAGE_SIZE));

  const getPageNumbers = (): (number | '...')[] => {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    const pages: (number | '...')[] = [1];
    if (page > 3) pages.push('...');
    const start = Math.max(2, page - 1);
    const end = Math.min(totalPages - 1, page + 1);
    for (let p = start; p <= end; p++) pages.push(p);
    if (page < totalPages - 2) pages.push('...');
    pages.push(totalPages);
    return pages;
  };

  // Close search dropdown when clicking outside
  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (searchBoxRef.current && !searchBoxRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  // Debounced live search (Shopee-style autocomplete)
  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setSearchRes(null);
      return;
    }
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await api.exploreSearch(
          trimmed,
          10,
          searchScope !== 'local',
          searchScope
        );
        setSearchRes(res);
        setDropdownOpen(true);
      } catch {
        // ignore transient search error
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [api, query, searchScope]);

  const runSearchNow = async (qOverride?: string, scopeOverride?: SearchScope) => {
    const target = (qOverride ?? query).trim();
    const targetScope = scopeOverride ?? searchScope;
    if (!target) return;
    if (qOverride !== undefined) setQuery(qOverride);
    setSearching(true);
    try {
      const res = await api.exploreSearch(
        target,
        12,
        targetScope !== 'local',
        targetScope
      );
      setSearchRes(res);
      setDropdownOpen(true);
    } finally {
      setSearching(false);
    }
  };

  const openPaperDetail = (
    item: Partial<ExplorePaperItem> & { paper_id: string; title: string }
  ) => {
    setDropdownOpen(false);
    navigate(`/explore/papers/${encodeURIComponent(item.paper_id)}`, {
      state: { paper: item },
    });
  };

  const renderSourceBadge = (source: string, year?: number | null) => {
    if (source === 'openalex') {
      return (
        <span className="inline-flex items-center gap-1 rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-[10px] font-semibold text-sky-700">
          <Globe className="h-3 w-3" />
          Mới{year ? ` • ${year}` : ''} (OpenAlex)
        </span>
      );
    }
    if (source === 'cached') {
      return (
        <span className="inline-flex items-center gap-1 rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-[10px] font-semibold text-violet-700">
          Đã cache 5-Facet{year ? ` • ${year}` : ''}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
        Kho 5-Facet{year ? ` • ${year}` : ''}
      </span>
    );
  };

  return (
    <div className="space-y-8">
      {/* 1. Refined Academic Search Hero */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 shadow-xs">
        <div className="mx-auto max-w-4xl space-y-5">
          <div className="text-center space-y-2">
            <div className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
              <Sparkles className="h-3.5 w-3.5" />
              Tra cứu bài báo đến hiện tại • Gợi ý cá nhân hóa theo 5-Facet
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
              Tìm bài báo bạn đang đọc
            </h1>
            <p className="mx-auto max-w-2xl text-xs sm:text-sm text-slate-500">
              Tìm trong kho chuẩn hóa 4.210 bài báo (hiển thị sẵn kết quả 5-Facet và gợi ý) hoặc
              tra cứu bài mới nhất từ OpenAlex để <strong>Phân tích bài báo</strong> trực tiếp và
              cập nhật hồ sơ đọc của bạn.
            </p>
          </div>

          {/* 3-Way Scope Selector */}
          <div className="flex justify-center">
            <div className="inline-flex flex-wrap items-center gap-1 rounded-xl border border-slate-200 bg-slate-100/80 p-1">
              <button
                type="button"
                onClick={() => setSearchScope('all')}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  searchScope === 'all'
                    ? 'bg-white text-blue-700 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Layers className="h-3.5 w-3.5" />
                Tất cả (Kho + OpenAlex)
              </button>
              <button
                type="button"
                onClick={() => setSearchScope('local')}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  searchScope === 'local'
                    ? 'bg-white text-emerald-700 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Database className="h-3.5 w-3.5" />
                Chỉ kho có sẵn (4.210 bài)
              </button>
              <button
                type="button"
                onClick={() => setSearchScope('external')}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  searchScope === 'external'
                    ? 'bg-white text-sky-700 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Globe className="h-3.5 w-3.5" />
                Chỉ bài mới (OpenAlex)
              </button>
            </div>
          </div>

          {/* Search Input + Dropdown */}
          <div ref={searchBoxRef} className="relative">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                runSearchNow();
              }}
              className="flex flex-col sm:flex-row gap-2.5"
            >
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute left-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={query}
                  onFocus={() => {
                    if (searchRes && searchRes.items.length > 0) setDropdownOpen(true);
                  }}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Nhập tên bài báo hoặc từ khóa (vd: DeepSeek-R1, Graph Neural Networks, Fake News...)"
                  className="h-12 w-full rounded-xl border border-slate-300 bg-slate-50/40 pl-11 pr-10 text-sm text-slate-900 shadow-2xs placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-4 focus:ring-blue-500/10 transition"
                />
                {query && (
                  <button
                    type="button"
                    onClick={() => {
                      setQuery('');
                      setSearchRes(null);
                      setDropdownOpen(false);
                    }}
                    className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>

              <button
                type="submit"
                disabled={searching || !query.trim()}
                className="inline-flex h-12 shrink-0 items-center justify-center gap-2 rounded-xl bg-blue-600 px-6 text-sm font-semibold text-white shadow-xs hover:bg-blue-700 disabled:opacity-60 transition"
              >
                {searching ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                Tìm kiếm
              </button>
            </form>

            {/* Quick Topics */}
            <div className="mt-3 flex flex-wrap items-center justify-center gap-1.5 text-xs">
              <span className="text-[11px] font-medium text-slate-400">Gợi ý nhanh:</span>
              {QUICK_TOPICS.map((topic) => (
                <button
                  key={topic}
                  type="button"
                  onClick={() => runSearchNow(topic)}
                  className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-[11px] font-medium text-slate-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 transition"
                >
                  {topic}
                </button>
              ))}
            </div>

            {/* Autocomplete Dropdown */}
            {dropdownOpen && searchRes && (
              <div className="absolute left-0 right-0 top-[54px] z-40 max-h-[440px] overflow-y-auto rounded-xl border border-slate-200 bg-white text-slate-900 shadow-2xl">
                <div className="sticky top-0 flex items-center justify-between border-b border-slate-100 bg-slate-50 px-4 py-2 text-[11px] text-slate-500">
                  <span>
                    Tìm thấy <strong>{searchRes.total}</strong> bài (
                    {searchRes.local_count} kho local • {searchRes.external_count} OpenAlex)
                  </span>
                  <span>{searchRes.latency_ms} ms</span>
                </div>

                {searchRes.external_warning && (
                  <div className="flex items-center gap-1.5 bg-amber-50 px-4 py-1.5 text-[11px] text-amber-800 border-b border-amber-100">
                    <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                    {searchRes.external_warning}
                  </div>
                )}

                {searchRes.items.length === 0 ? (
                  <div className="p-6 text-center text-sm text-slate-500">
                    Không tìm thấy bài báo nào khớp với &ldquo;{searchRes.query}&rdquo;.
                  </div>
                ) : (
                  <ul className="divide-y divide-slate-100">
                    {searchRes.items.map((item) => (
                      <li key={item.paper_id}>
                        <button
                          type="button"
                          onClick={() => openPaperDetail(item)}
                          className="w-full px-4 py-3 text-left hover:bg-blue-50/60 transition flex items-start justify-between gap-3"
                        >
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-1.5 mb-1">
                              {renderSourceBadge(item.source, item.year)}
                              {cleanVenue(item.venue) && (
                                <span className="text-[11px] text-slate-500 truncate max-w-[260px]">
                                  {cleanVenue(item.venue)}
                                </span>
                              )}
                              {typeof item.cited_by_count === 'number' && (
                                <span className="text-[11px] text-slate-400">
                                  • {item.cited_by_count.toLocaleString()} trích dẫn
                                </span>
                              )}
                            </div>
                            <div className="text-sm font-semibold text-slate-900 leading-snug">
                              {item.title}
                            </div>
                            {item.abstract_snippet && (
                              <p className="mt-1 line-clamp-2 text-xs text-slate-500">
                                {item.abstract_snippet}
                              </p>
                            )}
                          </div>
                          <span className="shrink-0 rounded-lg border border-blue-200 bg-blue-50 px-2.5 py-1 text-[11px] font-semibold text-blue-700">
                            Xem chi tiết
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* 2. Personalized Feed ("Gợi ý dành riêng cho bạn") */}
      <section ref={feedSectionRef} className="space-y-4 scroll-mt-20">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-blue-600" />
              {feed?.mode === 'personalized'
                ? 'Gợi ý dành riêng cho bạn'
                : 'Khám phá bài báo nổi bật trong kho (Bấm xem để lập hồ sơ)'}
            </h2>
            <p className="mt-0.5 text-xs text-slate-500">
              {feed ? (
                <>
                  Đang xếp hạng trên kho chuẩn hóa{' '}
                  <strong>{feed.corpus_size.toLocaleString()} bài báo</strong> (5-facet)
                  {feed.mode === 'personalized'
                    ? ` dựa trên ${feed.profile_size} bài bạn đã đọc • ${feed.latency_ms} ms.`
                    : ' — Hãy tìm kiếm hoặc bấm vào 1 bài bên dưới để kích hoạt hồ sơ 5-facet.'}
                </>
              ) : (
                'Đang tải danh sách bài báo...'
              )}
            </p>
          </div>

          {/* Live Encoder & Paper Method Switchers (2 clean controls on 1 row) */}
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Mô hình Embedding
              </span>
              <select
                value={exploreEmbedding}
                onChange={(e) => setExploreEmbedding(e.target.value as 'bert-base' | 'tfidf')}
                className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs font-semibold text-slate-700 shadow-2xs focus:border-blue-500 focus:outline-none"
              >
                <option value="bert-base">BERT-base-uncased (768d)</option>
                <option value="tfidf">TF-IDF Cosine (Baseline nhẹ)</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Khuyến nghị Bài báo
              </span>
              <select
                value={explorePaperMethod}
                onChange={(e) =>
                  setExplorePaperMethod(
                    e.target.value as 'weighted_facets' | 'equal_facets' | 'whole_text'
                  )
                }
                className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs font-semibold text-slate-700 shadow-2xs focus:border-blue-500 focus:outline-none"
              >
                <option value="weighted_facets">Weighted 5-Facet (0.4/0.2/0.2/0.1/0.1)</option>
                <option value="equal_facets">Equal 5-Facet (Trọng số đều 0.2)</option>
                <option value="whole_text">Whole-Text (So sánh toàn văn)</option>
              </select>
            </div>
          </div>
        </div>

        {loadingFeed ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                className="h-44 animate-pulse rounded-xl border border-slate-200 bg-white p-4"
              />
            ))}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {(feed?.items || []).map((rec: ExploreRecommendationItem) => {
                const venueLabel = cleanVenue(rec.venue);
                return (
                  <div
                    key={rec.paper_id}
                    onClick={() =>
                      openPaperDetail({
                        paper_id: rec.paper_id,
                        title: rec.title,
                        year: rec.year,
                        venue: rec.venue,
                        source: rec.source,
                      })
                    }
                    className="group cursor-pointer flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-2xs hover:border-blue-400 hover:shadow-md transition"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="text-[11px] font-medium text-slate-500">
                          {rec.year ?? '—'}
                          {venueLabel ? ` • ${venueLabel}` : ''}
                        </span>
                      </div>

                      <h3 className="text-sm font-bold text-slate-900 group-hover:text-blue-700 leading-snug line-clamp-2">
                        {rec.title}
                      </h3>

                      <p className="mt-1.5 text-xs text-slate-600 line-clamp-3 leading-relaxed">
                        {rec.abstract_snippet}
                      </p>
                    </div>

                    {rec.supporting_facets.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-slate-100 flex flex-wrap items-center gap-1.5">
                        <span className="text-[10px] font-medium text-slate-400">
                          Liên quan về:
                        </span>
                        {rec.supporting_facets.map((sf) => (
                          <span
                            key={sf}
                            className={`rounded-md border px-1.5 py-0.5 text-[10px] font-medium ${FACET_META[sf].badgeClass}`}
                          >
                            {FACET_META[sf].labelEn}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Clean Numbered Pagination Bar */}
            {totalPages > 1 && (
              <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-slate-200">
                <span className="text-xs text-slate-500">
                  Trang <strong>{page}</strong> / {totalPages.toLocaleString()} ({totalAvailable.toLocaleString()} bài báo)
                </span>

                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    disabled={page <= 1}
                    onClick={() => handlePageChange(page - 1)}
                    className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40 transition"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                    Trước
                  </button>

                  {getPageNumbers().map((p, idx) =>
                    p === '...' ? (
                      <span key={`dots-${idx}`} className="px-2 text-xs text-slate-400">
                        ...
                      </span>
                    ) : (
                      <button
                        key={p}
                        type="button"
                        onClick={() => handlePageChange(p)}
                        className={`h-8 min-w-[32px] rounded-lg px-2 text-xs font-semibold transition ${
                          p === page
                            ? 'bg-blue-600 text-white shadow-2xs'
                            : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                        }`}
                      >
                        {p}
                      </button>
                    )
                  )}

                  <button
                    type="button"
                    disabled={page >= totalPages}
                    onClick={() => handlePageChange(page + 1)}
                    className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40 transition"
                  >
                    Sau
                    <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
