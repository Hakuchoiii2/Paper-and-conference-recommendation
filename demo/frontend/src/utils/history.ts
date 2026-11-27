import type {
  AnalysisDetail,
  ConferenceRankingResponse,
  PaperRankingResponse,
} from '../types/api';

export interface HistoryEntry {
  analysis_id: string;
  title: string;
  model_name: string;
  source: 'live' | 'cache' | 'precomputed';
  created_at: string;
}

export interface AnalysisSnapshot {
  analysis: AnalysisDetail;
  paperRanking?: PaperRankingResponse | null;
  confRanking?: ConferenceRankingResponse | null;
  saved_at: string;
}

const SNAPSHOT_KEY = 'facetrec_analysis_snapshots';
const MAX_SNAPSHOTS = 12;

export function saveAnalysisSnapshot(snapshot: AnalysisSnapshot): void {
  try {
    const raw = localStorage.getItem(SNAPSHOT_KEY);
    const map: Record<string, AnalysisSnapshot> = raw ? JSON.parse(raw) : {};
    map[snapshot.analysis.analysis_id] = snapshot;
    const keys = Object.keys(map);
    if (keys.length > MAX_SNAPSHOTS) {
      keys
        .sort((a, b) => (map[b].saved_at || '').localeCompare(map[a].saved_at || ''))
        .slice(MAX_SNAPSHOTS)
        .forEach((oldKey) => {
          delete map[oldKey];
        });
    }
    localStorage.setItem(SNAPSHOT_KEY, JSON.stringify(map));
  } catch {
    // ignore quota errors
  }
}

export function getAnalysisSnapshot(analysisId: string): AnalysisSnapshot | null {
  try {
    const raw = localStorage.getItem(SNAPSHOT_KEY);
    if (!raw) return null;
    const map: Record<string, AnalysisSnapshot> = JSON.parse(raw);
    return map[analysisId] || null;
  } catch {
    return null;
  }
}

export function saveAnalysisHistory(entry: HistoryEntry): void {
  try {
    const raw = localStorage.getItem('facetrec_history');
    let list: HistoryEntry[] = raw ? JSON.parse(raw) : [];
    list = list.filter((item) => item.analysis_id !== entry.analysis_id);
    list.unshift(entry);
    if (list.length > 30) list = list.slice(0, 30);
    localStorage.setItem('facetrec_history', JSON.stringify(list));
  } catch {
    // ignore storage issues
  }
}

export function getAnalysisHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem('facetrec_history');
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function removeAnalysisHistoryItem(analysisId: string): HistoryEntry[] {
  try {
    const raw = localStorage.getItem('facetrec_history');
    const list: HistoryEntry[] = raw ? JSON.parse(raw) : [];
    const next = list.filter((item) => item.analysis_id !== analysisId);
    localStorage.setItem('facetrec_history', JSON.stringify(next));
    // Also clean snapshot
    const snapRaw = localStorage.getItem(SNAPSHOT_KEY);
    if (snapRaw) {
      const map: Record<string, AnalysisSnapshot> = JSON.parse(snapRaw);
      delete map[analysisId];
      localStorage.setItem(SNAPSHOT_KEY, JSON.stringify(map));
    }
    return next;
  } catch {
    return [];
  }
}

export function clearAnalysisHistory(): void {
  localStorage.removeItem('facetrec_history');
  localStorage.removeItem(SNAPSHOT_KEY);
}
