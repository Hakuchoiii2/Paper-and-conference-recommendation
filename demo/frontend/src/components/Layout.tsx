import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  BookOpenCheck,
  Compass,
  FileSearch,
  GitCompare,
  Settings2,
  UserCheck,
} from 'lucide-react';
import { useSystem } from '../context/SystemContext';
import { SystemDrawer } from './SystemDrawer';
import { ProfileDrawer } from './ProfileDrawer';
import { getExploreUserId, PROFILE_UPDATED_EVENT } from '../utils/userSession';

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { apiClient: api, setDrawerOpen } = useSystem();
  const [profileOpen, setProfileOpen] = useState(false);
  const [profileCount, setProfileCount] = useState<number>(0);

  const searchParams = new URLSearchParams(location.search);
  const fromExplore =
    searchParams.get('from') === 'explore' ||
    (location.state as { from?: string } | null)?.from === 'explore';

  const isExplore =
    location.pathname === '/' ||
    location.pathname.startsWith('/explore') ||
    (location.pathname.startsWith('/analyses') && fromExplore);
  const isCompare = location.pathname.startsWith('/compare');
  const isAnalyze = !isExplore && !isCompare;

  useEffect(() => {
    api
      .exploreGetProfile(getExploreUserId())
      .then((res) => setProfileCount(res.paper_count))
      .catch(() => {});

    const onProfileChange = (e: Event) => {
      const detail = (e as CustomEvent<{ paperCount?: number }>).detail;
      if (typeof detail?.paperCount === 'number') {
        setProfileCount(detail.paperCount);
      } else {
        api
          .exploreGetProfile(getExploreUserId())
          .then((res) => setProfileCount(res.paper_count))
          .catch(() => {});
      }
    };
    window.addEventListener(PROFILE_UPDATED_EVENT, onProfileChange);
    return () => window.removeEventListener(PROFILE_UPDATED_EVENT, onProfileChange);
  }, [api]);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-30 border-b border-slate-200/90 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          {/* Left: Brand */}
          <Link to="/" className="flex shrink-0 items-center gap-2.5 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-sm">
              <BookOpenCheck className="h-5 w-5" />
            </div>
            <div className="leading-tight">
              <div className="text-sm font-bold tracking-tight text-slate-900 group-hover:text-blue-700 whitespace-nowrap">
                DS300 FacetRec
              </div>
              <div className="text-[11px] text-slate-500 hidden xl:block whitespace-nowrap">
                Gợi ý Bài báo & Hội nghị 5-Facet
              </div>
            </div>
          </Link>

          {/* Center: Main Navigation */}
          <nav className="flex items-center gap-1 rounded-xl bg-slate-100/80 p-1">
            <Link
              to="/"
              className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3.5 py-1.5 text-sm font-medium transition ${
                isExplore
                  ? 'bg-white text-blue-700 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Compass className="h-4 w-4 shrink-0" />
              <span>Tra cứu bài báo</span>
            </Link>
            <Link
              to="/analyze"
              className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3.5 py-1.5 text-sm font-medium transition ${
                isAnalyze
                  ? 'bg-white text-blue-700 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <FileSearch className="h-4 w-4 shrink-0" />
              <span>Phân tích manuscript</span>
            </Link>
            <Link
              to="/compare"
              className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3.5 py-1.5 text-sm font-medium transition ${
                isCompare
                  ? 'bg-white text-blue-700 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <GitCompare className="h-4 w-4 shrink-0" />
              <span>So sánh extractor</span>
            </Link>
          </nav>

          {/* Right: Action Buttons (Unified Profile + System) */}
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={() => setProfileOpen(true)}
              className="inline-flex h-9 items-center gap-1.5 whitespace-nowrap rounded-lg border border-blue-200 bg-blue-50/80 px-3 text-xs font-semibold text-blue-700 hover:bg-blue-100 transition"
              title="Hồ sơ đọc & Lịch sử phân tích"
            >
              <UserCheck className="h-4 w-4 shrink-0" />
              <span className="hidden sm:inline">Hồ sơ</span>
              <span className="inline-flex min-w-[20px] items-center justify-center rounded-full bg-blue-600 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
                {profileCount}
              </span>
            </button>

            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              className="inline-flex h-9 items-center gap-1.5 whitespace-nowrap rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 shadow-2xs hover:bg-slate-50 transition"
              title="Cấu hình Extractor & Embedding"
            >
              <Settings2 className="h-4 w-4 shrink-0 text-slate-500" />
              <span className="hidden md:inline">Hệ thống</span>
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">{children}</main>

      <SystemDrawer />
      <ProfileDrawer open={profileOpen} onClose={() => setProfileOpen(false)} />
    </div>
  );
}
