export interface HistoryEntry {
  analysis_id: string;
  title: string;
  model_name: string;
  source: 'live' | 'cache' | 'precomputed';
  created_at: string;
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
    return next;
  } catch {
    return [];
  }
}

export function clearAnalysisHistory(): void {
  localStorage.removeItem('facetrec_history');
}
