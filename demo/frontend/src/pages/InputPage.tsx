import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  BookMarked,
  CheckCircle2,
  Cpu,
  Eraser,
  FileText,
  Layers,
  Loader2,
  Play,
  ServerOff,
  Settings2,
} from 'lucide-react';
import { useSystem } from '../context/SystemContext';
import type { AnalysisMode, ExampleSummary } from '../types/api';

export function InputPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    apiClient,
    models,
    runtime,
    triggerLoadModel,
    isSwitchingModel,
    setDrawerOpen,
  } = useSystem();

  const navState = (location.state as { title?: string; abstract?: string } | null) || null;

  const [title, setTitle] = useState(navState?.title || '');
  const [abstract, setAbstract] = useState(navState?.abstract || '');
  const [examples, setExamples] = useState<ExampleSummary[]>([]);
  const [selectedExampleId, setSelectedExampleId] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [runMode, setRunMode] = useState<AnalysisMode>('live');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    if (runtime?.loaded_model_key) {
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
      if (detail.default_model_key) {
        setSelectedModel(detail.default_model_key);
      }
      if (Object.keys(detail.precomputed_analyses || {}).length > 0) {
        setRunMode('precomputed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không tải được bài mẫu.');
    }
  };

  const handleClear = () => {
    setTitle('');
    setAbstract('');
    setSelectedExampleId('');
    setError(null);
  };

  const maxTitle = runtime?.limits.max_title_chars ?? 400;
  const maxAbstract = runtime?.limits.max_abstract_chars ?? 4000;
  const titleTooLong = title.length > maxTitle;
  const abstractTooLong = abstract.length > maxAbstract;

  const isSelectedModelReady =
    Boolean(selectedModel) && runtime?.loaded_model_key === selectedModel;
  const needsModelLoad = runMode === 'live' && Boolean(selectedModel) && !isSelectedModelReady;

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
    if (!selectedModel) {
      setError('Vui lòng chọn một extractor.');
      return;
    }
    if (titleTooLong || abstractTooLong) {
      setError('Nội dung vượt quá giới hạn ký tự khuyến nghị. Vui lòng rút gọn trước khi gửi.');
      return;
    }
    if (needsModelLoad) {
      setError(
        `Chế độ Trực tiếp yêu cầu model "${selectedModel}" đã được nạp. Vui lòng bấm "Nạp model" bên dưới hoặc chuyển sang "Mẫu có sẵn".`
      );
      return;
    }

    setSubmitting(true);
    try {
      const idempotencyKey = `ana_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      const res = await apiClient.createAnalysis({
        title: title.trim(),
        abstract: abstract.trim(),
        model_key: selectedModel,
        mode: runMode,
        idempotency_key: idempotencyKey,
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
          {/* Example selector + clear */}
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2 flex-1 min-w-[240px]">
              <label
                htmlFor="example-select"
                className="text-xs font-semibold text-slate-600 whitespace-nowrap"
              >
                Bài mẫu:
              </label>
              <select
                id="example-select"
                value={selectedExampleId}
                onChange={(e) => handleSelectExample(e.target.value)}
                disabled={examples.length === 0}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 focus:border-blue-500 focus:outline-none disabled:bg-slate-50 disabled:text-slate-400"
              >
                <option value="">
                  {examples.length > 0
                    ? '-- Chọn bài mẫu để điền nhanh --'
                    : '-- Chưa có bài mẫu từ backend --'}
                </option>
                {examples.map((ex) => (
                  <option key={ex.example_id} value={ex.example_id}>
                    {ex.short_label}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={handleClear}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              <Eraser className="h-3.5 w-3.5" />
              Xóa nội dung
            </button>
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

          {/* Extractor & Mode */}
          <div className="grid grid-cols-1 gap-4 rounded-xl border border-slate-200 bg-slate-50/70 p-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label
                htmlFor="extractor-select"
                className="block text-xs font-semibold uppercase tracking-wider text-slate-500"
              >
                Chọn Extractor
              </label>
              <select
                id="extractor-select"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                disabled={models.length === 0}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-800 focus:border-blue-500 focus:outline-none disabled:bg-slate-100 disabled:text-slate-400"
              >
                {models.length === 0 ? (
                  <option value="">Chưa có danh sách model</option>
                ) : (
                  models.map((m) => (
                    <option key={m.model_key} value={m.model_key} disabled={!m.supported}>
                      {m.display_name} ({m.parameter_size})
                    </option>
                  ))
                )}
              </select>

              <div className="flex items-center justify-between pt-1 text-xs">
                {!runtime?.connected ? (
                  <span className="text-slate-400">Chưa kết nối backend</span>
                ) : isSelectedModelReady ? (
                  <span className="inline-flex items-center gap-1 text-emerald-700 font-medium">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Model đang sẵn sàng
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-amber-700">
                    <Cpu className="h-3.5 w-3.5" /> Chưa nạp (hiện tại:{' '}
                    {runtime?.loaded_model_key || 'trống'})
                  </span>
                )}
                {needsModelLoad && runtime?.connected && (
                  <button
                    type="button"
                    disabled={isSwitchingModel}
                    onClick={() => triggerLoadModel(selectedModel)}
                    className="font-semibold text-blue-600 hover:underline disabled:opacity-50"
                  >
                    {isSwitchingModel ? 'Đang nạp...' : 'Nạp model'}
                  </button>
                )}
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="block text-xs font-semibold uppercase tracking-wider text-slate-500">
                Chế độ thực thi
              </span>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setRunMode('live')}
                  className={`rounded-lg border px-2.5 py-2 text-xs font-medium transition ${
                    runMode === 'live'
                      ? 'border-blue-600 bg-blue-50 text-blue-800'
                      : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  Chạy trực tiếp
                </button>
                <button
                  type="button"
                  onClick={() => setRunMode('precomputed')}
                  className={`rounded-lg border px-2.5 py-2 text-xs font-medium transition ${
                    runMode === 'precomputed'
                      ? 'border-blue-600 bg-blue-50 text-blue-800'
                      : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  Mẫu có sẵn
                </button>
              </div>
              <p className="text-[11px] text-slate-500 pt-0.5">
                {runMode === 'precomputed'
                  ? 'Chỉ trả kết quả khớp chính xác bài mẫu đã tính trước.'
                  : 'Chạy pipeline extraction và ranking cho nội dung bất kỳ.'}
              </p>
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
