import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Eraser,
  ExternalLink,
  GitCompare,
  Loader2,
  Play,
  Search,
  ServerOff,
} from 'lucide-react';
import { FacetBadge } from '../components/FacetBadge';
import { FACET_ORDER } from '../constants/facets';
import { useSystem } from '../context/SystemContext';
import type { AnalysisDetail, AnalysisMode, ExampleSummary } from '../types/api';

type ModelRunState = 'idle' | 'queued' | 'loading_model' | 'extracting' | 'done' | 'error';

interface ModelComparisonEntry {
  model_key: string;
  state: ModelRunState;
  status_label: string;
  analysis?: AnalysisDetail;
  error?: string;
}

export function ComparePage() {
  const location = useLocation();
  const { apiClient, models, runtime, triggerLoadModel, setDrawerOpen } = useSystem();
  const navState = (location.state as { title?: string; abstract?: string } | null) || null;

  const [examples, setExamples] = useState<ExampleSummary[]>([]);
  const [exampleSearch, setExampleSearch] = useState<string>('');
  const [selectedExampleId, setSelectedExampleId] = useState<string>('');
  const [title, setTitle] = useState(navState?.title || '');
  const [abstract, setAbstract] = useState(navState?.abstract || '');

  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [mobilePair, setMobilePair] = useState<[string, string]>(['', '']);
  const [mode, setMode] = useState<AnalysisMode>('precomputed');
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<Record<string, ModelComparisonEntry>>({});
  const [globalError, setGlobalError] = useState<string | null>(null);

  useEffect(() => {
    if (models.length > 0 && selectedModels.length === 0) {
      const defaults = models
        .filter((m) => m.supported)
        .slice(0, 3)
        .map((m) => m.model_key);
      setSelectedModels(defaults);
    }
  }, [models, selectedModels.length]);

  useEffect(() => {
    if (!runtime?.connected) {
      setExamples([]);
      return;
    }
    apiClient
      .getExamples()
      .then(async (list) => {
        setExamples(list);
        if (!navState?.title && list.length > 0) {
          const first = await apiClient.getExample(list[0].example_id);
          setSelectedExampleId(first.example_id);
          setTitle(first.title);
          setAbstract(first.abstract);
        }
      })
      .catch(() => {});
  }, [apiClient, navState?.title, runtime?.connected]);

  const handleSelectExample = async (exampleId: string) => {
    setSelectedExampleId(exampleId);
    setGlobalError(null);
    if (!exampleId) return;
    try {
      const detail = await apiClient.getExample(exampleId);
      setTitle(detail.title);
      setAbstract(detail.abstract);
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'Không tải được bài mẫu.');
    }
  };

  const handleClear = () => {
    setTitle('');
    setAbstract('');
    setSelectedExampleId('');
    setExampleSearch('');
    setGlobalError(null);
  };

  const filteredExamples = examples.filter((ex) => {
    if (!exampleSearch.trim()) return true;
    const kw = exampleSearch.trim().toLowerCase();
    return (
      ex.title.toLowerCase().includes(kw) ||
      ex.short_label.toLowerCase().includes(kw) ||
      ex.example_id.toLowerCase().includes(kw)
    );
  });

  const maxTitle = runtime?.limits.max_title_chars ?? 400;
  const maxAbstract = runtime?.limits.max_abstract_chars ?? 4000;
  const titleTooLong = title.length > maxTitle;
  const abstractTooLong = abstract.length > maxAbstract;

  const toggleModel = (modelKey: string) => {
    setSelectedModels((prev) => {
      if (prev.includes(modelKey)) {
        return prev.filter((k) => k !== modelKey);
      }
      if (prev.length >= 5) return prev;
      return [...prev, modelKey];
    });
  };

  const handleRunCompare = async () => {
    setGlobalError(null);
    if (!runtime?.connected) {
      setGlobalError('Chưa kết nối được với Backend API.');
      return;
    }
    if (!title.trim() || !abstract.trim()) {
      setGlobalError('Vui lòng nhập hoặc chọn bài mẫu có đầy đủ Title và Abstract.');
      return;
    }
    if (titleTooLong || abstractTooLong) {
      setGlobalError('Nội dung vượt quá giới hạn ký tự khuyến nghị. Vui lòng rút gọn trước khi so sánh.');
      return;
    }
    if (selectedModels.length < 2) {
      setGlobalError('Vui lòng chọn từ 2 đến 5 extractor để so sánh.');
      return;
    }

    setRunning(true);
    const initial: Record<string, ModelComparisonEntry> = {};
    selectedModels.forEach((mk) => {
      initial[mk] = { model_key: mk, state: 'queued', status_label: 'Đang chờ lượt' };
    });
    setResults(initial);

    // Run sequentially (never run 5 models concurrently)
    for (const modelKey of selectedModels) {
      try {
        if (mode === 'live' && runtime?.loaded_model_key !== modelKey) {
          setResults((prev) => ({
            ...prev,
            [modelKey]: {
              model_key: modelKey,
              state: 'loading_model',
              status_label: 'Đang nạp model...',
            },
          }));
          await triggerLoadModel(modelKey);
        }

        setResults((prev) => ({
          ...prev,
          [modelKey]: {
            model_key: modelKey,
            state: 'extracting',
            status_label: 'Đang trích xuất...',
          },
        }));

        const created = await apiClient.createAnalysis({
          title: title.trim(),
          abstract: abstract.trim(),
          model_key: modelKey,
          mode,
          idempotency_key: `cmp_${modelKey}_${Date.now()}`,
        });

        let finished = false;
        while (!finished) {
          const job = await apiClient.getJob(created.job_id);
          if (job.status === 'completed') {
            finished = true;
          } else if (job.status === 'failed') {
            throw new Error(job.error?.message || 'Lỗi trích xuất');
          } else {
            await new Promise((r) => setTimeout(r, 450));
          }
        }

        const detail = await apiClient.getAnalysis(created.analysis_id);
        setResults((prev) => ({
          ...prev,
          [modelKey]: {
            model_key: modelKey,
            state: 'done',
            status_label: 'Hoàn tất',
            analysis: detail,
          },
        }));
      } catch (err) {
        setResults((prev) => ({
          ...prev,
          [modelKey]: {
            model_key: modelKey,
            state: 'error',
            status_label: 'Lỗi',
            error: err instanceof Error ? err.message : String(err),
          },
        }));
      }
    }

    setRunning(false);
  };

  const activeColumns = selectedModels.filter((mk) => results[mk]?.analysis);

  useEffect(() => {
    if (activeColumns.length >= 2) {
      setMobilePair(([a, b]) => [
        activeColumns.includes(a) ? a : activeColumns[0],
        activeColumns.includes(b) ? b : activeColumns[1],
      ]);
    } else if (activeColumns.length === 1) {
      setMobilePair([activeColumns[0], activeColumns[0]]);
    }
  }, [activeColumns.join(',')]);

  return (
    <div className="space-y-6">
      {runtime && !runtime.connected && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <div className="flex items-center gap-2.5">
            <ServerOff className="h-4.5 w-4.5 shrink-0 text-amber-600" />
            <span>Chưa kết nối được tới Backend API để tải danh sách extractor.</span>
          </div>
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            className="rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-semibold text-amber-900 hover:bg-amber-100"
          >
            Mở Hệ thống
          </button>
        </div>
      )}

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <GitCompare className="h-5 w-5 text-blue-600" />
              So sánh đầu ra các Extractor
            </h1>
            <p className="text-sm text-slate-600 mt-0.5">
              Đối chiếu 5 facet và bằng chứng trích xuất của 2–5 model trên cùng một manuscript (chạy tuần tự để bảo toàn bộ nhớ GPU).
            </p>
          </div>
        </div>

        {/* Example selector + Search + Clear */}
        <div className="space-y-2.5 pt-2 pb-3 border-t border-b border-slate-100">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Chọn bài mẫu từ Corpus ({examples.length} bài sẵn có)
            </span>
            <button
              type="button"
              onClick={handleClear}
              disabled={running}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
            >
              <Eraser className="h-3.5 w-3.5" />
              Xóa nội dung
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
            {/* Ô tìm kiếm nhanh */}
            <div className="md:col-span-2 relative">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
              <input
                type="text"
                value={exampleSearch}
                onChange={(e) => setExampleSearch(e.target.value)}
                disabled={running}
                placeholder="Lọc bài mẫu (VD: NLP, neural, ACL...)"
                className="w-full rounded-lg border border-slate-300 bg-white pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none disabled:bg-slate-50"
              />
            </div>

            {/* Dropdown danh sách bài mẫu đã lọc */}
            <div className="md:col-span-3">
              <select
                id="compare-example-select"
                value={selectedExampleId}
                onChange={(e) => handleSelectExample(e.target.value)}
                disabled={running || filteredExamples.length === 0}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-800 focus:border-blue-500 focus:outline-none disabled:bg-slate-50 disabled:text-slate-400"
              >
                <option value="">
                  {filteredExamples.length > 0
                    ? `-- Chọn bài mẫu (${filteredExamples.length} bài khớp) --`
                    : '-- Không tìm thấy bài mẫu khớp từ khóa --'}
                </option>
                {filteredExamples.map((ex) => (
                  <option key={ex.example_id} value={ex.example_id}>
                    {ex.short_label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Title */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label htmlFor="compare-manuscript-title" className="text-sm font-semibold text-slate-800">
              Title <span className="text-rose-500">*</span>
            </label>
            <span
              className={`text-xs ${titleTooLong ? 'font-semibold text-rose-600' : 'text-slate-400'}`}
            >
              {title.length}/{maxTitle} ký tự
            </span>
          </div>
          <input
            id="compare-manuscript-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={running}
            placeholder="Ví dụ: Facet-Aware Scientific Paper Recommendation via Grounded Concept Extraction"
            className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/15 focus:outline-none disabled:bg-slate-50"
          />
        </div>

        {/* Abstract */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label htmlFor="compare-manuscript-abstract" className="text-sm font-semibold text-slate-800">
              Abstract <span className="text-rose-500">*</span>
            </label>
            <span
              className={`text-xs ${abstractTooLong ? 'font-semibold text-rose-600' : 'text-slate-400'}`}
            >
              {abstract.length}/{maxAbstract} ký tự
            </span>
          </div>
          <textarea
            id="compare-manuscript-abstract"
            rows={6}
            value={abstract}
            onChange={(e) => setAbstract(e.target.value)}
            disabled={running}
            placeholder="Dán hoặc nhập toàn bộ abstract của manuscript vào đây..."
            className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm leading-relaxed text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/15 focus:outline-none disabled:bg-slate-50"
          />
        </div>

        {/* Controls: Choose 2-5 models & mode */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
          <div className="space-y-1.5">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Chọn 2–5 Extractor ({selectedModels.length} đã chọn)
            </div>
            {models.length === 0 ? (
              <div className="text-xs text-slate-400">Chưa có danh sách model từ backend.</div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {models.map((m) => {
                  const checked = selectedModels.includes(m.model_key);
                  const isBlocked = mode === 'live' && !m.supported;
                  return (
                    <button
                      key={m.model_key}
                      type="button"
                      disabled={running || isBlocked}
                      onClick={() => toggleModel(m.model_key)}
                      title={isBlocked ? 'Model chưa tải về máy để chạy trực tiếp (hãy chọn Xem kết quả mẫu)' : undefined}
                      className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                        checked
                          ? 'border-blue-600 bg-blue-50 text-blue-800 font-semibold'
                          : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                      } ${isBlocked ? 'opacity-40 cursor-not-allowed' : ''}`}
                    >
                      {m.model_key}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-xs">
              <button
                type="button"
                disabled={running}
                onClick={() => setMode('precomputed')}
                className={`rounded-md px-3 py-1.5 font-medium ${
                  mode === 'precomputed' ? 'bg-white text-blue-700 shadow-xs' : 'text-slate-600'
                }`}
              >
                Xem kết quả mẫu
              </button>
              <button
                type="button"
                disabled={running}
                onClick={() => setMode('live')}
                className={`rounded-md px-3 py-1.5 font-medium ${
                  mode === 'live' ? 'bg-white text-blue-700 shadow-xs' : 'text-slate-600'
                }`}
              >
                Chạy tuần tự
              </button>
            </div>

            <button
              type="button"
              disabled={running || models.length === 0}
              onClick={handleRunCompare}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2 text-sm font-semibold text-white shadow-xs hover:bg-blue-700 disabled:bg-slate-300"
            >
              {running ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Đang chạy tuần tự...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  So sánh ngay
                </>
              )}
            </button>
          </div>
        </div>

        {globalError && (
          <div className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-xs text-rose-800">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{globalError}</span>
          </div>
        )}
      </section>

      {/* Per-model status cards */}
      {Object.keys(results).length > 0 && (
        <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {selectedModels.map((mk) => {
            const entry = results[mk];
            if (!entry) return null;
            return (
              <div
                key={mk}
                className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-slate-900">{mk}</span>
                  {entry.state === 'done' ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  ) : entry.state === 'error' ? (
                    <AlertCircle className="h-4 w-4 text-rose-600" />
                  ) : (
                    <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                  )}
                </div>

                <div className="text-xs text-slate-600">{entry.status_label}</div>

                {entry.error && <div className="text-[11px] text-rose-600">{entry.error}</div>}

                {entry.analysis && (
                  <div className="space-y-1.5 pt-1 border-t border-slate-100 text-[11px] text-slate-500">
                    <div className="flex items-center justify-between">
                      <span>Nguồn:</span>
                      <span className="font-medium text-slate-700">
                        {entry.analysis.provenance.source === 'precomputed'
                          ? 'Mẫu có sẵn'
                          : entry.analysis.provenance.source === 'cache'
                            ? 'Cache'
                            : 'Trực tiếp'}
                      </span>
                    </div>
                    {entry.analysis.timings.model_load_ms != null && (
                      <div className="flex items-center justify-between">
                        <span>Nạp model:</span>
                        <span>{(entry.analysis.timings.model_load_ms / 1000).toFixed(2)}s</span>
                      </div>
                    )}
                    {entry.analysis.timings.extraction_ms != null && (
                      <div className="flex items-center justify-between">
                        <span className="inline-flex items-center gap-1">
                          <Clock className="h-3 w-3" /> Trích:
                        </span>
                        <span>{(entry.analysis.timings.extraction_ms / 1000).toFixed(2)}s</span>
                      </div>
                    )}
                    <Link
                      to={`/analyses/${encodeURIComponent(entry.analysis.analysis_id)}`}
                      className="inline-flex items-center gap-1 font-semibold text-blue-600 hover:underline pt-1"
                    >
                      Mở trang kết quả
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                  </div>
                )}
              </div>
            );
          })}
        </section>
      )}

      {/* Side-by-side Facet Comparison Matrix */}
      {activeColumns.length > 0 && (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-base font-bold text-slate-900">
              Bảng đối chiếu theo từng Facet
            </h2>
            <span className="text-xs text-slate-500">
              Lưu ý: Không tự tính F1 cho abstract mới khi chưa có nhãn chuẩn tham chiếu.
            </span>
          </div>

          {/* Mobile 2-model pair selector */}
          {activeColumns.length > 2 && (
            <div className="flex md:hidden items-center gap-2 rounded-xl border border-slate-200 bg-white p-3 text-xs">
              <span className="font-semibold text-slate-600">Đối chiếu 2 model:</span>
              <select
                value={mobilePair[0]}
                onChange={(e) => setMobilePair([e.target.value, mobilePair[1]])}
                className="flex-1 rounded border border-slate-300 px-2 py-1"
              >
                {activeColumns.map((mk) => (
                  <option key={mk} value={mk}>
                    {mk}
                  </option>
                ))}
              </select>
              <span>vs</span>
              <select
                value={mobilePair[1]}
                onChange={(e) => setMobilePair([mobilePair[0], e.target.value])}
                className="flex-1 rounded border border-slate-300 px-2 py-1"
              >
                {activeColumns.map((mk) => (
                  <option key={mk} value={mk}>
                    {mk}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="space-y-4">
            {FACET_ORDER.map((facetKey) => (
              <div
                key={facetKey}
                className="rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-xs"
              >
                <div className="border-b border-slate-200 bg-slate-50 px-4 py-2.5">
                  <FacetBadge facet={facetKey} />
                </div>

                {/* Desktop grid (all active columns) */}
                <div
                  className="hidden md:grid divide-x divide-slate-200"
                  style={{
                    gridTemplateColumns: `repeat(${activeColumns.length}, minmax(0, 1fr))`,
                  }}
                >
                  {activeColumns.map((mk) => {
                    const ana = results[mk].analysis!;
                    const facetOut = ana.facets[facetKey];
                    return (
                      <div key={mk} className="p-4 space-y-2.5">
                        <div className="text-xs font-bold text-slate-700 pb-1 border-b border-slate-100">
                          {mk}
                        </div>
                        {facetOut.status === 'empty' ? (
                          <p className="text-xs italic text-slate-400">
                            Không tìm thấy bằng chứng.
                          </p>
                        ) : facetOut.status === 'error' ? (
                          <p className="text-xs text-rose-600">
                            Lỗi: {facetOut.error_message || 'Không xác định'}
                          </p>
                        ) : (
                          <div className="space-y-2">
                            {facetOut.items.map((item, idx) => (
                              <div key={idx} className="space-y-1">
                                <div className="text-xs font-semibold text-slate-900">
                                  • {item.concept}
                                </div>
                                {item.evidences.map((ev, eIdx) => (
                                  <div
                                    key={eIdx}
                                    className="rounded bg-slate-50 px-2 py-1 text-[11px] italic text-slate-600"
                                  >
                                    "{ev.quote}"
                                  </div>
                                ))}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Mobile 2-column comparison */}
                <div className="grid grid-cols-2 divide-x divide-slate-200 md:hidden">
                  {mobilePair.map((mk, colIdx) => {
                    const ana = results[mk]?.analysis;
                    if (!ana) return <div key={colIdx} className="p-3" />;
                    const facetOut = ana.facets[facetKey];
                    return (
                      <div key={`${mk}-${colIdx}`} className="p-3 space-y-2">
                        <div className="text-xs font-bold text-slate-700 pb-1 border-b border-slate-100">
                          {mk}
                        </div>
                        {facetOut.status === 'empty' ? (
                          <p className="text-xs italic text-slate-400">Không có bằng chứng.</p>
                        ) : facetOut.status === 'error' ? (
                          <p className="text-xs text-rose-600">Lỗi</p>
                        ) : (
                          <div className="space-y-1.5">
                            {facetOut.items.map((item, idx) => (
                              <div key={idx} className="space-y-1">
                                <div className="text-xs font-semibold text-slate-900">
                                  • {item.concept}
                                </div>
                                {item.evidences.map((ev, eIdx) => (
                                  <div
                                    key={eIdx}
                                    className="rounded bg-slate-50 px-2 py-1 text-[11px] italic text-slate-600"
                                  >
                                    "{ev.quote}"
                                  </div>
                                ))}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
