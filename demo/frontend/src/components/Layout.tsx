import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BookOpenCheck, GitCompare, Settings2 } from 'lucide-react';
import { useSystem } from '../context/SystemContext';
import { SystemDrawer } from './SystemDrawer';

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { apiMode, runtime, setDrawerOpen } = useSystem();

  const isCompare = location.pathname.startsWith('/compare');

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-2.5 group">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-sm">
                <BookOpenCheck className="h-4.5 w-4.5" />
              </div>
              <div>
                <div className="text-sm font-bold tracking-tight text-slate-900 group-hover:text-blue-700">
                  DS300 FacetRec
                </div>
                <div className="text-[11px] text-slate-500 hidden sm:block">
                  Gợi ý Bài báo & Hội nghị theo 5 Facet
                </div>
              </div>
            </Link>

            <nav className="flex items-center gap-1 sm:gap-2">
              <Link
                to="/"
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                  !isCompare
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                Phân tích manuscript
              </Link>
              <Link
                to="/compare"
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                  isCompare
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                <GitCompare className="h-4 w-4" />
                So sánh extractor
              </Link>
            </nav>
          </div>

          <div className="flex items-center gap-2.5">
            {apiMode === 'mock' ? (
              <span className="hidden sm:inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800">
                Chế độ mẫu (Mock)
              </span>
            ) : (
              <span
                className={`hidden sm:inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${
                  runtime?.connected
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                    : 'border-rose-200 bg-rose-50 text-rose-700'
                }`}
              >
                {runtime?.connected ? 'API Đã kết nối' : 'API Mất kết nối'}
              </span>
            )}

            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-xs hover:bg-slate-50"
            >
              <Settings2 className="h-4 w-4 text-slate-500" />
              <span>Hệ thống</span>
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">{children}</main>

      <SystemDrawer />
    </div>
  );
}
