import { FACET_META } from '../constants/facets';
import type { EvidenceSpan, FacetKey } from '../types/api';

export interface ActiveEvidenceHighlight {
  facet: FacetKey;
  evidence: EvidenceSpan;
}

interface HighlightedTextProps {
  text: string;
  field: 'title' | 'abstract';
  activeHighlight: ActiveEvidenceHighlight | null;
}

export function HighlightedText({ text, field, activeHighlight }: HighlightedTextProps) {
  if (!activeHighlight || activeHighlight.evidence.source_field !== field) {
    return <span>{text}</span>;
  }

  const { evidence, facet } = activeHighlight;
  const meta = FACET_META[facet];

  let start = -1;
  let end = -1;

  // Use verified offsets first, verify slice matches quote
  if (
    evidence.verified &&
    typeof evidence.start_offset === 'number' &&
    typeof evidence.end_offset === 'number' &&
    evidence.start_offset >= 0 &&
    evidence.end_offset <= text.length &&
    text.slice(evidence.start_offset, evidence.end_offset) === evidence.quote
  ) {
    start = evidence.start_offset;
    end = evidence.end_offset;
  } else if (evidence.quote) {
    // Only highlight if exact substring appears in text (never guess fuzzy offsets)
    const idx = text.indexOf(evidence.quote);
    if (idx !== -1) {
      start = idx;
      end = idx + evidence.quote.length;
    }
  }

  if (start === -1 || end <= start) {
    return <span>{text}</span>;
  }

  const before = text.slice(0, start);
  const match = text.slice(start, end);
  const after = text.slice(end);

  return (
    <span>
      {before}
      <mark className={`rounded px-1 py-0.5 font-medium transition-colors ${meta.highlightClass}`}>
        {match}
      </mark>
      {after}
    </span>
  );
}
