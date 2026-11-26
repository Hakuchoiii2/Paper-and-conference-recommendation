import type { FacetKey } from '../types/api';

export interface FacetMeta {
  key: FacetKey;
  labelVi: string;
  labelEn: string;
  shortDesc: string;
  badgeClass: string;
  borderClass: string;
  highlightClass: string;
  dotClass: string;
}

export const FACET_ORDER: FacetKey[] = [
  'problem',
  'task',
  'method',
  'dataset',
  'contribution',
];

export const FACET_META: Record<FacetKey, FacetMeta> = {
  problem: {
    key: 'problem',
    labelVi: 'Vấn đề (Problem)',
    labelEn: 'Problem',
    shortDesc: 'Vấn đề nghiên cứu được giải quyết',
    badgeClass: 'bg-rose-50 text-rose-700 border-rose-200',
    borderClass: 'border-l-rose-500',
    highlightClass: 'bg-rose-200/80 text-rose-950 ring-1 ring-rose-400',
    dotClass: 'bg-rose-500',
  },
  task: {
    key: 'task',
    labelVi: 'Nhiệm vụ (Task)',
    labelEn: 'Task',
    shortDesc: 'Nhiệm vụ cụ thể của bài báo',
    badgeClass: 'bg-amber-50 text-amber-800 border-amber-200',
    borderClass: 'border-l-amber-500',
    highlightClass: 'bg-amber-200/80 text-amber-950 ring-1 ring-amber-400',
    dotClass: 'bg-amber-500',
  },
  method: {
    key: 'method',
    labelVi: 'Phương pháp (Method)',
    labelEn: 'Method',
    shortDesc: 'Phương pháp, mô hình hoặc kỹ thuật đề xuất',
    badgeClass: 'bg-blue-50 text-blue-700 border-blue-200',
    borderClass: 'border-l-blue-600',
    highlightClass: 'bg-blue-200/80 text-blue-950 ring-1 ring-blue-400',
    dotClass: 'bg-blue-600',
  },
  dataset: {
    key: 'dataset',
    labelVi: 'Dữ liệu (Dataset)',
    labelEn: 'Dataset',
    shortDesc: 'Bộ dữ liệu, ngữ liệu hoặc benchmark sử dụng',
    badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    borderClass: 'border-l-emerald-500',
    highlightClass: 'bg-emerald-200/80 text-emerald-950 ring-1 ring-emerald-400',
    dotClass: 'bg-emerald-500',
  },
  contribution: {
    key: 'contribution',
    labelVi: 'Đóng góp (Contribution)',
    labelEn: 'Contribution',
    shortDesc: 'Đóng góp chính được bài báo trình bày',
    badgeClass: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    borderClass: 'border-l-indigo-600',
    highlightClass: 'bg-indigo-200/80 text-indigo-950 ring-1 ring-indigo-400',
    dotClass: 'bg-indigo-600',
  },
};
