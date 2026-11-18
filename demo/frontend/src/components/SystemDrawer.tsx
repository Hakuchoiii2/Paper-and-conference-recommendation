import { useEffect, useState } from 'react';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Cpu,
  RefreshCw,
  Server,
  X,
} from 'lucide-react';
import { useSystem } from '../context/SystemContext';

export function SystemDrawer() {
  const {
    apiMode,
    baseUrl,
    models,
    runtime,
    isLoadingRuntime,
    isSwitchingModel,
    switchModelMessage,
    drawerOpen,
    setDrawerOpen,
    setApiMode,
    setBaseUrl,
    refreshRuntime,
    triggerLoadModel,
  } = useSystem();

  const [selectedModel, setSelectedModel] = useState<string>(
    runtime?.intended_model_key || runtime?.loaded_model_key || 'Qwen3-8B'
  );
  const [urlInput, setUrlInput] = useState(baseUrl);
  const [showDetails, setShowDetails] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    setUrlInput(baseUrl);
  }, [baseUrl]);

  useEffect(() => {
    if (runtime?.intended_model_key) {
      setSelectedModel(runtime.intended_model_key);
    } else if (runtime?.loaded_model_key) {
      setSelectedModel(runtime.loaded_model_key);
    }
  }, [runtime?.intended_model_key, runtime?.loaded_model_key]);

  if (!drawerOpen) return null;

  const handleLoadModel = async () => {
    setLoadError(null);
    try {
      await triggerLoadModel(selectedModel);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleApplyUrl = () => {
    const trimmed = urlInput.trim() || '/api/v1';
    setBaseUrl(trimmed);
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/35 backdrop-blur-[1px]">
      <div className="flex h-full w-full max-w-md flex-col bg-white shadow-2xl border-l border-slate-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <Server className="h-5 w-5 text-blue-600" />
            <div>
              <h2 className="text-base font-semibold text-slate-900">Hệ thống & Model Runtime</h2>
              <p className="text-xs text-slate-500">Quản lý kết nối API và extractor đang nạp</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setDrawerOpen(false)}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Đóng bảng hệ thống"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {/* API Mode */}
          <section className="space-y-2.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500">
              Chế độ dữ liệu
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setApiMode('mock')}
                className={`rounded-lg border px-3 py-2 text-left text-sm transition ${
                  apiMode === 'mock'
                    ? 'border-blue-600 bg-blue-50 text-blue-800 font-medium'
                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                }`}
              >
                <div>Mẫu giả lập (Mock)</div>
                <div className="text-[11px] opacity-75">Không cần GPU/Backend</div>
              </button>
              <button
                type="button"
                onClick={() => setApiMode('http')}
                className={`rounded-lg border px-3 py-2 text-left text-sm transition ${
                  apiMode === 'http'
                    ? 'border-blue-600 bg-blue-50 text-blue-800 font-medium'
                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                }`}
              >
                <div>Backend thật (HTTP)</div>
                <div className="text-[11px] opacity-75">Local FastAPI / Kaggle</div>
              </button>
            </div>

            {apiMode === 'http' && (
              <div className="pt-2 space-y-1.5">
                <label className="block text-xs font-medium text-slate-700">
                  Địa chỉ API (chế độ phát triển)
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                    placeholder="/api/v1 hoặc http://localhost:8000/api/v1"
                    className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={handleApplyUrl}
                    className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
                  >
                    Áp dụng
                  </button>
                </div>
                <p className="text-[11px] text-slate-500">
                  Mặc định dùng đường dẫn tương đối <code>/api/v1</code> khi deploy cùng máy chủ.
                </p>
              </div>
            )}
          </section>

          {/* Runtime Status */}
          <section className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Trạng thái Runtime
              </span>
              <button
                type="button"
                onClick={refreshRuntime}
                disabled={isLoadingRuntime}
                className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700 disabled:opacity-50"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isLoadingRuntime ? 'animate-spin' : ''}`} />
                Làm mới
              </button>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Kết nối backend:</span>
                {runtime?.connected ? (
                  <span className="inline-flex items-center gap-1 font-medium text-emerald-700">
                    <CheckCircle2 className="h-4 w-4" /> Sẵn sàng
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 font-medium text-rose-600">
                    <AlertCircle className="h-4 w-4" /> Mất kết nối
                  </span>
                )}
              </div>

              <div className="flex items-center justify-between">
                <span className="text-slate-600">Model thực sự đang nạp:</span>
                <span className="font-semibold text-slate-900">
                  {runtime?.loaded_model_key || 'Chưa nạp'}
                </span>
              </div>

              {runtime?.intended_model_key &&
                runtime.intended_model_key !== runtime.loaded_model_key && (
                  <div className="flex items-center justify-between text-amber-700">
                    <span>Model dự kiến chọn:</span>
                    <span className="font-medium">{runtime.intended_model_key} (chưa nạp xong)</span>
                  </div>
                )}

              <div className="flex items-center justify-between">
                <span className="text-slate-600">Trạng thái worker:</span>
                <span className="inline-flex items-center gap-1.5 text-slate-800">
                  <Activity className="h-3.5 w-3.5 text-blue-600" />
                  {runtime?.worker_busy
                    ? runtime.current_task || 'Đang xử lý tác vụ'
                    : 'Đang rảnh'}
                </span>
              </div>
            </div>
          </section>

          {/* Model Selector */}
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500">
                Chọn & Nạp Extractor (1 model/lần)
              </label>
            </div>
            <p className="text-xs text-slate-500">
              Hệ thống chỉ giữ một extractor trong bộ nhớ để tối ưu VRAM. Chọn model rồi bấm Nạp model khi cần chạy trực tiếp.
            </p>

            <div className="space-y-2">
              {models.map((m) => {
                const isLoaded = runtime?.loaded_model_key === m.model_key;
                const isSelected = selectedModel === m.model_key;
                return (
                  <label
                    key={m.model_key}
                    className={`flex cursor-pointer items-center justify-between rounded-lg border p-3 transition ${
                      isSelected
                        ? 'border-blue-600 bg-blue-50/50'
                        : 'border-slate-200 hover:bg-slate-50'
                    } ${!m.supported ? 'opacity-60' : ''}`}
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="radio"
                        name="system_model"
                        value={m.model_key}
                        checked={isSelected}
                        onChange={() => setSelectedModel(m.model_key)}
                        className="text-blue-600 focus:ring-blue-500"
                      />
                      <div>
                        <div className="text-sm font-medium text-slate-900">{m.display_name}</div>
                        <div className="text-xs text-slate-500">
                          {m.family} • {m.parameter_size}
                          {!m.supported && m.unavailable_reason ? ` — ${m.unavailable_reason}` : ''}
                        </div>
                      </div>
                    </div>
                    {isLoaded && (
                      <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-[11px] font-medium text-emerald-800">
                        Đang nạp
                      </span>
                    )}
                  </label>
                );
              })}
            </div>

            {switchModelMessage && (
              <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-800">
                {switchModelMessage}
              </div>
            )}

            {loadError && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                {loadError}
              </div>
            )}

            <button
              type="button"
              onClick={handleLoadModel}
              disabled={
                isSwitchingModel ||
                !runtime?.connected ||
                runtime?.loaded_model_key === selectedModel
              }
              className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {isSwitchingModel
                ? 'Đang nạp model...'
                : runtime?.loaded_model_key === selectedModel
                  ? `${selectedModel} đã sẵn sàng`
                  : `Nạp model ${selectedModel}`}
            </button>
          </section>

          {/* Expandable resource details */}
          <section className="border-t border-slate-200 pt-3">
            <button
              type="button"
              onClick={() => setShowDetails(!showDetails)}
              className="flex w-full items-center justify-between text-xs font-medium text-slate-600 hover:text-slate-900"
            >
              <span className="inline-flex items-center gap-1.5">
                <Cpu className="h-3.5 w-3.5" />
                Thông tin tài nguyên & chẩn đoán
              </span>
              {showDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>

            {showDetails && (
              <div className="mt-3 rounded-lg bg-slate-100 p-3 text-xs text-slate-700 space-y-1.5">
                <div>
                  <span className="font-medium">Thiết bị:</span>{' '}
                  {runtime?.device_summary || 'Không có thông tin'}
                </div>
                <div>
                  <span className="font-medium">Ranking artifacts:</span>{' '}
                  {runtime?.ranking_ready ? 'Sẵn sàng' : 'Chưa sẵn sàng'}
                </div>
                <div>
                  <span className="font-medium">Giới hạn đầu vào:</span> Title ≤{' '}
                  {runtime?.limits.max_title_chars ?? 400} ký tự, Abstract ≤{' '}
                  {runtime?.limits.max_abstract_chars ?? 4000} ký tự
                </div>
                {runtime?.last_error && (
                  <div className="text-rose-700">
                    <span className="font-medium">Lỗi gần nhất:</span> {runtime.last_error}
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
