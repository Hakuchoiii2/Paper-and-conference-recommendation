import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, BookMarked, Trash2, UserCheck, X } from 'lucide-react';
import { useSystem } from '../context/SystemContext';
import type { ExploreProfileItem, ExploreProfileResponse } from '../types/api';
import { clearAnalysisHistory, removeAnalysisHistoryItem } from '../utils/history';
import {
  getExploreUserId,
  notifyProfileUpdated,
  PROFILE_UPDATED_EVENT,
} from '../utils/userSession';

function cleanVenue(venue?: string | null): string | null {
  if (!venue) return null;
  const v = venue.trim();
  if (!v || v.toUpperCase() === 'CSFCUBE') return null;
  return v;
}

function getSavedItemKind(item: ExploreProfileItem): {
  label: string;
  className: string;
  isExplore: boolean;
} {
  const src = (item.source || '').toLowerCase();
  const isKbAnalysis = Boolean(item.analysis_id?.startsWith('ana_kb_'));

  if (src === 'manuscript' || src === 'precomputed' || (src === 'live' && !isKbAnalysis)) {
    return {
      label: 'Manuscript',
      className: 'border-indigo-200 bg-indigo-50 text-indigo-700',
      isExplore: false,
    };
  }
  if (src === 'explore_openalex' || src === 'openalex') {
    return {
      label: 'Bài báo tra cứu (OpenAlex)',
      className: 'border-sky-200 bg-sky-50 text-sky-700',
      isExplore: true,
    };
  }
  return {
    label: 'Bài báo tra cứu',
    className: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    isExplore: true,
  };
}

interface ProfileDrawerProps {
  open: boolean;
  onClose: () => void;
}

type ConfirmDeleteState =
  | { type: 'all' }
  | { type: 'single'; item: ExploreProfileItem }
  | null;

export function ProfileDrawer({ open, onClose }: ProfileDrawerProps) {
  const navigate = useNavigate();
  const { apiClient: api } = useSystem();
  const [profile, setProfile] = useState<ExploreProfileResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<ConfirmDeleteState>(null);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const data = await api.exploreGetProfile(getExploreUserId());
      setProfile(data);
    } catch {
      // ignore if offline
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      loadProfile();
      setConfirmDelete(null);
    }
  }, [open]);

  useEffect(() => {
    const handler = () => {
      if (open) loadProfile();
    };
    window.addEventListener(PROFILE_UPDATED_EVENT, handler);
    return () => window.removeEventListener(PROFILE_UPDATED_EVENT, handler);
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

  const items = profile?.items || [];

  const handleConfirmDelete = async () => {
    if (!confirmDelete) return;
    setBusy(true);
    try {
      const updated =
        confirmDelete.type === 'all'
          ? await api.exploreDeleteProfile(getExploreUserId())
          : await api.exploreDeleteProfile(getExploreUserId(), confirmDelete.item.paper_id);
      if (confirmDelete.type === 'all') {
        clearAnalysisHistory();
      } else if (confirmDelete.item.analysis_id) {
        removeAnalysisHistoryItem(confirmDelete.item.analysis_id);
      }
      setProfile(updated);
      notifyProfileUpdated(updated.paper_count);
      setConfirmDelete(null);
    } finally {
      setBusy(false);
    }
  };

  const handleSelect = (item: ExploreProfileItem) => {
    onClose();
    if (item.analysis_id) {
      const kind = getSavedItemKind(item);
      navigate(
        `/analyses/${encodeURIComponent(item.analysis_id)}${kind.isExplore ? '?from=explore' : ''}`
      );
      return;
    }
    navigate(`/explore/papers/${encodeURIComponent(item.paper_id)}`, {
      state: {
        paper: {
          paper_id: item.paper_id,
          title: item.title,
          year: item.year,
          venue: item.venue,
          source: item.source,
        },
      },
    });
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
            <UserCheck className="h-5 w-5 text-blue-600" />
            <h2 className="text-base font-bold text-slate-900">
              Hồ sơ & Lịch sử ({items.length})
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
          {loading && !profile ? (
            <div className="flex items-center justify-center h-48 text-xs text-slate-400">
              Đang tải hồ sơ đọc...
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-center text-slate-400 text-xs space-y-2">
              <BookMarked className="h-8 w-8 text-slate-300 stroke-1" />
              <p>Chưa có bài báo nào trong hồ sơ đọc.</p>
              <p className="text-[11px] text-slate-400 max-w-xs">
                Tìm kiếm bài báo ở trang Tra cứu rồi bấm Phân tích để xây dựng hồ sơ gợi ý cá nhân.
              </p>
            </div>
          ) : (
            items.map((item) => {
              const venueLabel = cleanVenue(item.venue);
              const extraMeta = [item.year, venueLabel].filter(Boolean).join(' • ');
              const kind = getSavedItemKind(item);
              return (
                <div
                  key={item.paper_id}
                  onClick={() => handleSelect(item)}
                  className="group cursor-pointer rounded-xl border border-slate-200 p-3.5 hover:border-blue-400 hover:bg-blue-50/40 transition shadow-2xs space-y-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-xs font-semibold text-slate-900 group-hover:text-blue-700 line-clamp-2 leading-snug">
                      {item.title}
                    </h3>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setConfirmDelete({ type: 'single', item });
                      }}
                      title="Xóa bài này khỏi hồ sơ"
                      aria-label="Xóa bài này khỏi hồ sơ"
                      className="shrink-0 rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600 transition"
                    >
                      <Trash2 className="h-4.5 w-4.5" />
                    </button>
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-1.5 text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span
                        className={`inline-flex shrink-0 items-center rounded-md border px-1.5 py-0.5 text-[10px] font-semibold ${kind.className}`}
                      >
                        {kind.label}
                      </span>
                      {extraMeta && (
                        <span className="font-medium text-slate-600 truncate max-w-[140px]">
                          {extraMeta}
                        </span>
                      )}
                    </div>
                    <span className="shrink-0">
                      {new Date(item.created_at).toLocaleTimeString('vi-VN', {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        {items.length > 0 && (
          <div className="border-t border-slate-200 p-4 bg-slate-50 flex items-center justify-between">
            <span className="text-[11px] text-slate-500">
              Tạo vector trung bình gợi ý trên trang Tra cứu
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
                      ? 'Xóa toàn bộ hồ sơ đọc?'
                      : 'Xóa bài báo khỏi hồ sơ?'}
                  </h3>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {confirmDelete.type === 'all'
                      ? `Bạn có chắc chắn muốn xóa tất cả ${items.length} bài báo khỏi hồ sơ đọc không? Vector trung bình gợi ý sẽ được đặt lại về ban đầu.`
                      : `Bạn có chắc chắn muốn xóa "${confirmDelete.item.title}" khỏi hồ sơ đọc không?`}
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => setConfirmDelete(null)}
                  className="rounded-lg border border-slate-300 bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={handleConfirmDelete}
                  className="rounded-lg bg-rose-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-60"
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
