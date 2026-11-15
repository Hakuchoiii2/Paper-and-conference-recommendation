# Ingestion report — 2026-10-02; workflow updated 2026-10-03

## Delivered scope

Official raw CSFCube v1.1 and SciFact downloads, a provisional IT corpus,
a runnable stdlib pipeline and A–E directory/docs. All experiments now read
`data/processed/papers.jsonl` directly; the separate smoke sample was removed.
Gold/silver annotation and A–E experimental datasets are **not generated**.
No conference recommendation judgments, models, commits or GitHub push.

| Source | Raw records | IT-admitted source records | Excluded |
|---|---:|---:|---:|
| CSFCube v1.1 | 4207 | 4207 | 0 |
| SciFact | 5183 | 28 | 5155 |

Canonical corpus: **4210 records**, after **25 duplicate source records**
were merged. Canonical records by source: {"csfcube": 4182, "scifact": 28}.
Cross-source identifier/title+abstract overlap: 0 canonical papers.
No input titles/abstracts were missing. CSFCube has two missing years and one
invalid year (801), normalized to null; SciFact has no publication year field.
Native source metadata remains unchanged in raw files.

## Limitations requiring review before freeze

- CSFCube is admitted using its documented CS sampling scope; not every title was
  independently classified by a person.
- SciFact filter admits explicit computing/software methods, including applied
  bioinformatics. Ordinary biomedical findings are excluded. Codex corrected
  several scope cases using abstract evidence; this is not human annotation.
- 15 SciFact records are flagged review_pending and remain excluded.
  Exact phrases may miss other IT papers; see the complete per-record scope audit.
- 5 same-title/different-abstract cases remain separate. Thus the canonical
  count is provisional and does not prove every entry is a distinct publication.
  Report includes IDs for manual resolution; do not merge on title alone.
- Minimum workload 3000 is exceeded numerically; working target 6000 is short by
  1790. No duplicates/synthetic papers were added to fill this gap.
- No five-facet labels or gold are available. Native CSFCube labels/splits and
  SciFact claim evidence/splits are preserved rather than reinterpreted.

## Review files

`data/processed/papers.jsonl` — canonical title/abstract catalog.
`data/processed/id_map.jsonl` — stable source aliases and provenance.
`data/processed/scope_audit.jsonl` — all 9390 raw input decisions.
`data/processed/corpus_report.json` — actual counts and ambiguous duplicate cases.
`configs/scope.json` — versioned filter and explicit Codex scope overrides.

## Validation protocol

Run the four commands in the root README in sequence. The corpus gate validates
raw/source and output checksums, references, schema types, counts, canonical content
and lack of labels in the corpus. Unit checks exercise scope discrimination,
provenance/dedup, stable IDs, invalid metadata, validation directly against the main corpus,
unknown references, invalid facets, timezone absence, temporal overlap and unsafe
archive paths. Full experiment validation is explicitly unavailable until those
stages are built. Raw/full generated outputs are ignored for future Git commits.
