import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Clock, ExternalLink, History, Trash2, X } from 'lucide-react';
import {
  clearAnalysisHistory,
  getAnalysisHistory,
  removeAnalysisHistoryItem,
  type HistoryEntry,
} from '../utils/history';

interface HistoryDrawerProps {
  open: boolean;
  onClose: () => void;
}

type ConfirmDeleteState =
  | { type: 'all' }
  | { type: 'single'; entry: HistoryEntry }
  | null;

export function HistoryDrawer({ open, onClose }: HistoryDrawerProps) {
  const navigate = useNavigate();
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [confirmDelete, setConfirmDelete] = useState<ConfirmDeleteState>(null);

  useEffect(() => {
    if (open) {
      setHistory(getAnalysisHistory());
      setConfirmDelete(null);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (confirmDelete) {
          setConfirmDelete(null);
        } else {
          onClose();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, confirmDelete, onClose]);

  if (!open) return null;

  const handleConfirmDelete = () => {
    if (!confirmDelete) return;
    if (confirmDelete.type === 'all') {
      clearAnalysisHistory();
      setHistory([]);
    } else {
      const updated = removeAnalysisHistoryItem(confirmDelete.entry.analysis_id);
      setHistory(updated);
    }
    setConfirmDelete(null);
  };

  const handleSelect = (analysisId: string) => {
    onClose();
    navigate(`/analyses/${encodeURIComponent(analysisId)}`);
  };

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-xs transition-opacity"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-md bg-white shadow-2xl flex flex-col h-full animate-in slide-in-from-right duration-200"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div className="flex items-center gap-2">
            <History className="h-5 w-5 text-blue-600" />
            <h2 className="text-base font-bold text-slate-900">
              Lịch sử phân tích ({history.length})
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            aria-label="Đóng"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          {history.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-center text-slate-400 text-xs space-y-2">
              <Clock className="h-8 w-8 text-slate-300 stroke-1" />
              <p>Chưa có lịch sử phân tích manuscript nào trong phiên này.</p>
            </div>
          ) : (
            history.map((item) => (
              <div
                key={item.analysis_id}
                onClick={() => handleSelect(item.analysis_id)}
                className="group cursor-pointer rounded-xl border border-slate-200 p-3.5 hover:border-blue-400 hover:bg-blue-50/40 transition shadow-2xs space-y-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-xs font-semibold text-slate-900 group-hover:text-blue-700 line-clamp-2 leading-snug">
                    {item.title}
                  </h3>
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setConfirmDelete({ type: 'single', entry: item });
                      }}
                      title="Xóa mục này"
                      aria-label="Xóa mục lịch sử này"
                      className="rounded-md p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600 transition"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                    <ExternalLink className="h-3.5 w-3.5 text-slate-400 group-hover:text-blue-600" />
                  </div>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-1 text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                  <span className="font-medium text-slate-600">
                    {item.model_name || 'Qwen3-4B'}
                  </span>
                  <span>
                    {new Date(item.created_at).toLocaleTimeString('vi-VN', {
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    })}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        {history.length > 0 && (
          <div className="border-t border-slate-200 p-4 bg-slate-50 flex items-center justify-between">
            <span className="text-[11px] text-slate-500">
              Lưu tối đa 30 lần phân tích gần nhất
            </span>
            <button
              type="button"
              onClick={() => setConfirmDelete({ type: 'all' })}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-rose-600 hover:text-rose-800"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Xóa tất cả
            </button>
          </div>
        )}

        {/* Confirmation Dialog */}
        {confirmDelete && (
          <div
            onClick={() => setConfirmDelete(null)}
            className="absolute inset-0 z-10 flex items-center justify-center bg-slate-900/45 p-5 backdrop-blur-[1px]"
          >
            <div
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-5 shadow-xl space-y-4"
            >
              <div className="flex items-start gap-3">
                <div className="rounded-full bg-rose-50 p-2 text-rose-600 shrink-0">
                  <AlertTriangle className="h-5 w-5" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-sm font-bold text-slate-900">
                    {confirmDelete.type === 'all'
                      ? 'Xóa toàn bộ lịch sử?'
                      : 'Xóa mục lịch sử này?'}
                  </h3>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {confirmDelete.type === 'all'
                      ? `Bạn có chắc chắn muốn xóa tất cả ${history.length} mục lịch sử phân tích không? Hành động này không thể hoàn tác.`
                      : `Bạn có chắc chắn muốn xóa "${confirmDelete.entry.title}" khỏi lịch sử không?`}
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setConfirmDelete(null)}
                  className="rounded-lg border border-slate-300 bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={handleConfirmDelete}
                  className="rounded-lg bg-rose-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-rose-700"
                >
                  {confirmDelete.type === 'all' ? 'Xóa tất cả' : 'Xóa'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
