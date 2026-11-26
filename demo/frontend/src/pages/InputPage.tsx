import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  BookMarked,
  CheckCircle2,
  Cpu,
  Eraser,
  FileText,
  Layers,
  Loader2,
  Play,
  Search,
  ServerOff,
  Settings2,
  X,
} from 'lucide-react';
import { useSystem } from '../context/SystemContext';
import { saveAnalysisHistory } from '../utils/history';
import type {
  AnalysisMode,
  ConferenceRankingMethod,
  ExampleSummary,
  PaperRankingMethod,
} from '../types/api';

export function InputPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    apiClient,
    models,
    runtime,
    triggerLoadModel,
    setDrawerOpen,
  } = useSystem();

  const navState =
    (location.state as {
      title?: string;
      abstract?: string;
      fromAnalysisId?: string;
      embedding?: 'tfidf' | 'bert-base';
      mode?: AnalysisMode;
    } | null) || null;

  const [title, setTitle] = useState(navState?.title || '');
  const [abstract, setAbstract] = useState(navState?.abstract || '');
  const [examples, setExamples] = useState<ExampleSummary[]>([]);
  const [exampleSearch, setExampleSearch] = useState<string>('');
  const [selectedExampleId, setSelectedExampleId] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [selectedEmbedding, setSelectedEmbedding] = useState<'tfidf' | 'bert-base'>(() => {
    if (navState?.embedding) return navState.embedding;
    const saved = localStorage.getItem('facetrec_embedding');
    return saved === 'bert-base' || saved === 'tfidf' ? saved : 'tfidf';
  });
  const [runMode, setRunMode] = useState<AnalysisMode>(() => {
    if (navState?.mode) return navState.mode;
    const saved = localStorage.getItem('facetrec_run_mode');
    return saved === 'live' || saved === 'precomputed' ? saved : 'live';
  });
  const [paperMethod, setPaperMethod] = useState<PaperRankingMethod>(() => {
    const saved = localStorage.getItem('facetrec_paper_method');
    return saved === 'whole_text' || saved === 'equal_facets' || saved === 'weighted_facets'
      ? saved
      : 'whole_text';
  });
  const [confMethod, setConfMethod] = useState<ConferenceRankingMethod>(() => {
    const saved = localStorage.getItem('facetrec_conf_method');
    return saved === 'whole_text_knn' || saved === 'flat_facet_knn' || saved === 'gated_knn'
      ? saved
      : 'whole_text_knn';
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Lưu lựa chọn embedding, phương pháp và chế độ thực thi vào localStorage
  useEffect(() => {
    localStorage.setItem('facetrec_embedding', selectedEmbedding);
  }, [selectedEmbedding]);

  useEffect(() => {
    localStorage.setItem('facetrec_run_mode', runMode);
  }, [runMode]);

  useEffect(() => {
    localStorage.setItem('facetrec_paper_method', paperMethod);
  }, [paperMethod]);

  useEffect(() => {
    localStorage.setItem('facetrec_conf_method', confMethod);
  }, [confMethod]);

  // Tự động đóng thông báo sau 4.5 giây
  useEffect(() => {
    if (!toastMessage) return;
    const timer = setTimeout(() => {
      setToastMessage(null);
    }, 4500);
    return () => clearTimeout(timer);
  }, [toastMessage]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
  };

  const handleModelChange = async (targetModelKey: string) => {
    const targetModel = models.find((m) => m.model_key === targetModelKey);
    if (!targetModel) return;

    // Chỉ chặn khi chạy "Trực tiếp" trên máy; "Mẫu có sẵn" không cần tải model về GPU
    if (runMode === 'live' && !targetModel.supported) {
      showToast(
        targetModel.unavailable_reason ||
          `⚠️ Model ${targetModel.display_name} chưa được tải về máy để chạy trực tiếp. Vui lòng chuyển sang "Mẫu có sẵn" để xem kết quả tính trước của model này.`
      );
      setSelectedModel(runtime?.loaded_model_key || 'Qwen3-4B');
      return;
    }

    setSelectedModel(targetModelKey);
    if (runMode === 'live' && targetModelKey !== runtime?.loaded_model_key && runtime?.connected) {
      const isResident = typeof runtime?.resident_models?.[targetModelKey] === 'number';
      if (isResident) {
        // Model đã nạp thường trú trong VRAM -> chuyển nhanh 0 giây
        try {
          await triggerLoadModel(targetModelKey);
        } catch (err) {
          showToast(err instanceof Error ? err.message : 'Không chuyển được model');
        }
      } else {
        // Model chưa nạp vào VRAM -> KHÔNG tự ý tải/nạp làm đứng trang, hướng dẫn mở Hệ thống
        showToast(
          `⚠️ Model ${targetModel.display_name} chưa được nạp vào GPU. Hãy mở nút "Hệ thống" ở góc trên phải để nạp model này, hoặc đổi sang model đã sẵn sàng (0s) khác.`
        );
      }
    }
  };

  const handleModeChange = (newMode: AnalysisMode) => {
    if (newMode === 'live') {
      const current = models.find((m) => m.model_key === selectedModel);
      if (current && !current.supported) {
        showToast(
          `⚠️ ${current.unavailable_reason || `Model ${current.display_name} chưa khả dụng trên máy này.`} Đã chuyển về ${runtime?.loaded_model_key || 'Qwen3-4B'} để chạy trực tiếp.`
        );
        setSelectedModel(runtime?.loaded_model_key || 'Qwen3-4B');
      }
    }
    setRunMode(newMode);
  };

  useEffect(() => {
    if (!runtime?.connected) {
      setExamples([]);
      return;
    }
    apiClient
      .getExamples()
      .then(setExamples)
      .catch(() => setExamples([]));
  }, [apiClient, runtime?.connected]);

  useEffect(() => {
    if (!selectedModel && runtime?.loaded_model_key) {
      setSelectedModel(runtime.loaded_model_key);
    } else if (models.length > 0 && !selectedModel) {
      const firstSupported = models.find((m) => m.supported);
      if (firstSupported) setSelectedModel(firstSupported.model_key);
    }
  }, [models, runtime?.loaded_model_key, selectedModel]);

  const handleSelectExample = async (exampleId: string) => {
    setSelectedExampleId(exampleId);
    setError(null);
    if (!exampleId) return;
    try {
      const detail = await apiClient.getExample(exampleId);
      setTitle(detail.title);
      setAbstract(detail.abstract);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không tải được bài mẫu.');
    }
  };

  const handleClear = () => {
    setTitle('');
    setAbstract('');
    setSelectedExampleId('');
    setExampleSearch('');
    setError(null);
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

  const needsFacets = !(paperMethod === 'whole_text' && confMethod === 'whole_text_knn');
  const isSelectedModelReady =
    !needsFacets ||
    runMode === 'precomputed' ||
    (Boolean(selectedModel) && runtime?.loaded_model_key === selectedModel);
  const needsModelLoad =
    needsFacets && runMode === 'live' && Boolean(selectedModel) && !isSelectedModelReady;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!runtime?.connected) {
      setError('Chưa kết nối được với Backend API. Vui lòng kiểm tra cấu hình trong Hệ thống.');
      return;
    }
    if (!title.trim() || !abstract.trim()) {
      setError('Vui lòng nhập đầy đủ cả Title và Abstract của manuscript.');
      return;
    }
    if (needsFacets && !selectedModel) {
      setError('Vui lòng chọn một extractor.');
      return;
    }
    if (titleTooLong || abstractTooLong) {
      setError('Nội dung vượt quá giới hạn ký tự khuyến nghị. Vui lòng rút gọn trước khi gửi.');
      return;
    }
    if (needsModelLoad) {
      setError(
        `Model "${selectedModel}" chưa được nạp vào GPU. Vui lòng mở nút "Hệ thống" ở góc trên phải để chuyển đổi & nạp model này, hoặc chọn một model đã sẵn sàng khác.`
      );
      return;
    }

    setSubmitting(true);
    try {
      const idempotencyKey = `ana_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      const res = await apiClient.createAnalysis({
        title: title.trim(),
        abstract: abstract.trim(),
        model_key: selectedModel || 'Qwen3-4B',
        mode: runMode,
        embedding_model: selectedEmbedding,
        paper_ranking_method: paperMethod,
        conference_ranking_method: confMethod,
        idempotency_key: idempotencyKey,
      });

      const modelDisplayName =
        models.find((m) => m.model_key === selectedModel)?.display_name || selectedModel;
      saveAnalysisHistory({
        analysis_id: res.analysis_id,
        title: title.trim(),
        model_name: modelDisplayName,
        source: runMode,
        created_at: new Date().toISOString(),
      });
      navigate(
        `/analyses/${encodeURIComponent(res.analysis_id)}?job_id=${encodeURIComponent(res.job_id)}`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tạo tác vụ phân tích.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Toast Notification tự động tắt */}
      {toastMessage && (
        <div className="fixed top-6 right-6 z-50 flex max-w-md items-start gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 shadow-xl transition-all">
          <AlertTriangle className="h-5 w-5 flex-shrink-0 text-amber-600 mt-0.5" />
          <div className="flex-1 text-xs font-medium text-amber-900 leading-relaxed">
            {toastMessage}
          </div>
          <button
            type="button"
            onClick={() => setToastMessage(null)}
            className="text-amber-500 hover:text-amber-800 p-0.5"
            aria-label="Đóng thông báo"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Hero heading */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl space-y-1.5">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Tìm bài báo và hội nghị phù hợp với manuscript
            </h1>
            <p className="text-sm text-slate-600">
              Nhập Title và Abstract để trích xuất năm facet khoa học có dẫn chứng nguồn, xếp hạng bài báo liên quan và gợi ý hội nghị phù hợp.
            </p>
          </div>

          {navState?.fromAnalysisId && (
            <button
              type="button"
              onClick={() => navigate(`/analyses/${encodeURIComponent(navState.fromAnalysisId!)}`)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 transition"
            >
              <ArrowLeft className="h-4 w-4 text-slate-500" />
              Quay lại kết quả phân tích
            </button>
          )}
        </div>
      </div>

      {/* Backend connection alert when offline */}
      {runtime && !runtime.connected && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <div className="flex items-center gap-2.5">
            <ServerOff className="h-4.5 w-4.5 shrink-0 text-amber-600" />
            <span>
              Chưa kết nối được tới Backend API. Khởi chạy FastAPI hoặc cấu hình địa chỉ máy chủ trong bảng <strong>Hệ thống</strong>.
            </span>
          </div>
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-semibold text-amber-900 hover:bg-amber-100"
          >
            <Settings2 className="h-3.5 w-3.5" />
            Cấu hình Hệ thống
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main Form */}
        <form
          onSubmit={handleSubmit}
          className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-5"
        >
          {/* Example selector + Search + Clear */}
          <div className="space-y-2.5 pb-3 border-b border-slate-100">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Chọn bài mẫu từ Corpus ({examples.length} bài sẵn có)
              </span>
              <button
                type="button"
                onClick={handleClear}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
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
                  placeholder="Lọc bài mẫu (VD: NLP, neural, ACL...)"
                  className="w-full rounded-lg border border-slate-300 bg-white pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none"
                />
              </div>

              {/* Dropdown danh sách bài mẫu đã lọc */}
              <div className="md:col-span-3">
                <select
                  id="example-select"
                  value={selectedExampleId}
                  onChange={(e) => handleSelectExample(e.target.value)}
                  disabled={filteredExamples.length === 0}
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
              <label htmlFor="manuscript-title" className="text-sm font-semibold text-slate-800">
                Title <span className="text-rose-500">*</span>
              </label>
              <span
                className={`text-xs ${titleTooLong ? 'font-semibold text-rose-600' : 'text-slate-400'}`}
              >
                {title.length}/{maxTitle} ký tự
              </span>
            </div>
            <input
              id="manuscript-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ví dụ: Facet-Aware Scientific Paper Recommendation via Grounded Concept Extraction"
              className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/15 focus:outline-none"
            />
          </div>

          {/* Abstract */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label htmlFor="manuscript-abstract" className="text-sm font-semibold text-slate-800">
                Abstract <span className="text-rose-500">*</span>
              </label>
              <span
                className={`text-xs ${abstractTooLong ? 'font-semibold text-rose-600' : 'text-slate-400'}`}
              >
                {abstract.length}/{maxAbstract} ký tự
              </span>
            </div>
            <textarea
              id="manuscript-abstract"
              rows={8}
              value={abstract}
              onChange={(e) => setAbstract(e.target.value)}
              placeholder="Dán hoặc nhập toàn bộ abstract của manuscript vào đây..."
              className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm leading-relaxed text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/15 focus:outline-none"
            />
          </div>

          {/* Extractor & Embedding & Mode & Ranking Methods - Căn chỉnh đồng đều chuẩn SaaS */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 space-y-4">
            <div className="grid grid-cols-1 gap-3.5 md:grid-cols-3">
              {/* Cột 1: Extractor */}
              <div className="flex flex-col justify-between space-y-1.5">
                <label
                  htmlFor="extractor-select"
                  className="h-5 flex items-center text-xs font-bold uppercase tracking-wider text-slate-600 truncate"
                >
                  1. Extractor (LLM)
                </label>

                <select
                  id="extractor-select"
                  value={selectedModel}
                  onChange={(e) => handleModelChange(e.target.value)}
                  disabled={models.length === 0 || (!needsFacets && runMode === 'live')}
                  className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-800 shadow-2xs focus:border-blue-500 focus:outline-none disabled:bg-slate-100 disabled:text-slate-400"
                >
                  {models.length === 0 ? (
                    <option value="">Chưa có model</option>
                  ) : (
                    models.map((m) => {
                      const isRes =
                        runtime?.loaded_model_key === m.model_key ||
                        typeof runtime?.resident_models?.[m.model_key] === 'number';
                      const suffix =
                        runMode !== 'live'
                          ? ''
                          : !m.supported
                            ? ' - Không khả dụng trên máy này'
                            : isRes
                              ? ' • Sẵn sàng (0s)'
                              : ' • Chưa nạp';
                      return (
                        <option key={m.model_key} value={m.model_key}>
                          {m.display_name} ({m.parameter_size}){suffix}
                        </option>
                      );
                    })
                  )}
                </select>

                <div className="h-5 flex items-center justify-between text-[11px]">
                  {!runtime?.connected ? (
                    <span className="text-slate-400">Chưa kết nối backend</span>
                  ) : !needsFacets && runMode === 'live' ? (
                    <span className="text-slate-500 truncate">Toàn văn — bỏ qua trích LLM</span>
                  ) : isSelectedModelReady ? (
                    <span className="inline-flex items-center gap-1 text-emerald-700 font-medium">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Sẵn sàng
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-amber-700">
                      <Cpu className="h-3.5 w-3.5" /> Chưa nạp vào GPU
                    </span>
                  )}
                  {needsModelLoad && runtime?.connected && (
                    <button
                      type="button"
                      onClick={() => setDrawerOpen(true)}
                      className="font-semibold text-blue-600 hover:underline"
                    >
                      Mở Hệ thống
                    </button>
                  )}
                </div>
              </div>

              {/* Cột 2: Embedding */}
              <div className="flex flex-col justify-between space-y-1.5">
                <label
                  htmlFor="embedding-select"
                  className="h-5 flex items-center text-xs font-bold uppercase tracking-wider text-slate-600 truncate"
                >
                  2. Embedding (Scorer)
                </label>

                <select
                  id="embedding-select"
                  value={selectedEmbedding}
                  onChange={(e) => setSelectedEmbedding(e.target.value as 'tfidf' | 'bert-base')}
                  className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-800 shadow-2xs focus:border-blue-500 focus:outline-none"
                >
                  <option value="tfidf">TF-IDF (Mặc định - Nhanh)</option>
                  <option value="bert-base">BERT-base-uncased (768d)</option>
                </select>

                <div className="h-5 flex items-center text-[11px] text-slate-500 truncate">
                  {selectedEmbedding === 'bert-base'
                    ? 'Dense vector 768 chiều (google-bert/bert-base-uncased)'
                    : 'So khớp từ vựng nhanh tức thì'}
                </div>
              </div>

              {/* Cột 3: Chế độ thực thi */}
              <div className="flex flex-col justify-between space-y-1.5">
                <span className="h-5 flex items-center text-xs font-bold uppercase tracking-wider text-slate-600 truncate">
                  3. Chế độ thực thi
                </span>

                <div className="flex h-10 w-full items-center rounded-lg border border-slate-200 bg-slate-200/60 p-1">
                  <button
                    type="button"
                    onClick={() => handleModeChange('live')}
                    className={`h-full flex-1 rounded-md text-xs font-semibold transition ${
                      runMode === 'live'
                        ? 'bg-white text-blue-700 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Trực tiếp
                  </button>
                  <button
                    type="button"
                    onClick={() => handleModeChange('precomputed')}
                    className={`h-full flex-1 rounded-md text-xs font-semibold transition ${
                      runMode === 'precomputed'
                        ? 'bg-white text-blue-700 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Mẫu có sẵn
                  </button>
                </div>

                <div className="h-5 flex items-center text-[11px] text-slate-500 truncate">
                  {runMode === 'precomputed'
                    ? 'Dùng kết quả LLM thật đã tính trước'
                    : 'Chạy trích xuất & xếp hạng mới'}
                </div>
              </div>
            </div>

            {/* Hàng 2: Chọn Phương pháp gợi ý cho Bài báo & Hội nghị */}
            <div className="grid grid-cols-1 gap-3.5 border-t border-slate-200/80 pt-3.5 md:grid-cols-2">
              {/* Cột 4: Phương pháp gợi ý Bài báo */}
              <div className="flex flex-col justify-between space-y-1.5">
                <label
                  htmlFor="paper-method-select"
                  className="h-5 flex items-center text-xs font-bold uppercase tracking-wider text-slate-600 truncate"
                >
                  4. Phương pháp gợi ý Bài báo
                </label>

                <select
                  id="paper-method-select"
                  value={paperMethod}
                  onChange={(e) => setPaperMethod(e.target.value as PaperRankingMethod)}
                  className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-800 shadow-2xs focus:border-blue-500 focus:outline-none"
                >
                  <option value="whole_text">Toàn văn (Full-Text — Mặc định)</option>
                  <option value="equal_facets">5-Facet Trọng số đều (Equal 0.2 × 5)</option>
                  <option value="weighted_facets">5-Facet Có trọng số (Weighted)</option>
                </select>

                <div className="h-5 flex items-center text-[11px] text-slate-500 truncate">
                  {paperMethod === 'whole_text'
                    ? 'So sánh trực tiếp toàn văn Title + Abstract'
                    : paperMethod === 'equal_facets'
                      ? 'Trích 5 facet, chia đều trọng số 0.2 mỗi facet'
                      : 'Ưu tiên Problem 0.4, Task/Method 0.2, Dataset/Contrib 0.1'}
                </div>
              </div>

              {/* Cột 5: Phương pháp gợi ý Hội nghị */}
              <div className="flex flex-col justify-between space-y-1.5">
                <label
                  htmlFor="conf-method-select"
                  className="h-5 flex items-center text-xs font-bold uppercase tracking-wider text-slate-600 truncate"
                >
                  5. Phương pháp gợi ý Hội nghị
                </label>

                <select
                  id="conf-method-select"
                  value={confMethod}
                  onChange={(e) => setConfMethod(e.target.value as ConferenceRankingMethod)}
                  className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-800 shadow-2xs focus:border-blue-500 focus:outline-none"
                >
                  <option value="whole_text_knn">Toàn văn k-NN (Full-Text — Mặc định)</option>
                  <option value="flat_facet_knn">5-Facet Trọng số đều k-NN (Flat 5-Facet)</option>
                  <option value="gated_knn">Gated 5-Facet k-NN (Cổng Problem)</option>
                </select>

                <div className="h-5 flex items-center text-[11px] text-slate-500 truncate">
                  {confMethod === 'whole_text_knn'
                    ? 'Top-10 láng giềng toàn văn từ 602 bài Train bỏ phiếu'
                    : confMethod === 'flat_facet_knn'
                      ? 'Trích 5 facet chia đều trọng số, Top-10 bỏ phiếu'
                      : 'Cổng Problem (τ=0.45) × 4 facet giải pháp, Top-10 bỏ phiếu'}
                </div>
              </div>
            </div>
          </div>

          {error && (
            <div className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              <AlertCircle className="h-4.5 w-4.5 shrink-0 mt-0.5 text-rose-600" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex items-center justify-end pt-1">
            <button
              type="submit"
              disabled={submitting || !title.trim() || !abstract.trim()}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300 transition"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Đang khởi tạo...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Phân tích manuscript
                </>
              )}
            </button>
          </div>
        </form>

        {/* Right sidebar: Output overview */}
        <aside className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs space-y-4">
            <h2 className="text-sm font-semibold text-slate-900">Đầu ra của hệ thống</h2>
            <ul className="space-y-3.5 text-sm text-slate-600">
              <li className="flex items-start gap-3">
                <div className="rounded-lg bg-blue-50 p-2 text-blue-600">
                  <Layers className="h-4 w-4" />
                </div>
                <div>
                  <div className="font-medium text-slate-800">Năm facet có bằng chứng</div>
                  <p className="text-xs text-slate-500">
                    Trích xuất <em>problem, task, method, dataset, contribution</em> kèm câu trích dẫn nguyên văn từ title/abstract.
                  </p>
                </div>
              </li>
              <li className="flex items-start gap-3">
                <div className="rounded-lg bg-indigo-50 p-2 text-indigo-600">
                  <FileText className="h-4 w-4" />
                </div>
                <div>
                  <div className="font-medium text-slate-800">Bài báo liên quan (Top-k)</div>
                  <p className="text-xs text-slate-500">
                    Xếp hạng các bài báo trong corpus kèm điểm tương đồng và giải thích đối chiếu theo từng facet.
                  </p>
                </div>
              </li>
              <li className="flex items-start gap-3">
                <div className="rounded-lg bg-emerald-50 p-2 text-emerald-600">
                  <BookMarked className="h-4 w-4" />
                </div>
                <div>
                  <div className="font-medium text-slate-800">Hội nghị phù hợp</div>
                  <p className="text-xs text-slate-500">
                    Đánh giá mức phù hợp nội dung với hồ sơ bài lịch sử của hội nghị và liệt kê các bài minh họa tiêu biểu.
                  </p>
                </div>
              </li>
            </ul>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-600 space-y-1.5">
            <div className="font-semibold text-slate-800">Lưu ý thực nghiệm</div>
            <p>
              Mỗi lần sửa nội dung manuscript và chạy lại sẽ tạo một <code>analysis_id</code> mới, không ghi đè kết quả cũ.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
