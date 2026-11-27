import { FACET_META } from '../constants/facets';
import type { FacetKey } from '../types/api';

interface FacetBadgeProps {
  facet: FacetKey;
  compact?: boolean;
}

export function FacetBadge({ facet, compact = false }: FacetBadgeProps) {
  const meta = FACET_META[facet];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium ${meta.badgeClass}`}
      title={meta.shortDesc}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${meta.dotClass}`} />
      {compact ? meta.labelEn : meta.labelVi}
    </span>
  );
}
