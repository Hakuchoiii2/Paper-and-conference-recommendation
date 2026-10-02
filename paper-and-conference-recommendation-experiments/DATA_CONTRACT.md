# Global data contract

Version: **1.0**. Owner: **Khai**. Status: proposed defaults, pending owner's
review before shared annotation and dataset freeze. Changes of field meaning
require a version bump. This file is the source of truth for A–E.

## Encoding, identity and corpus

UTF-8 JSONL (one object per line); JSON for config/manifests. Canonical corpus:
`data/processed/papers.jsonl`. Real and mock catalogs must never be merged.
The delivered fixture is a real subset of that corpus and shares its IDs.
`paper_id`: `^P[0-9]{6}$`; `user_id`: `^U[0-9]{4}$`;
`query_id`: `^Q[0-9]{4}$`; `intent_id`: `^I[0-9]{4}$`.
Source IDs are strings and never replaced by canonical IDs in raw files.

Paper fields: paper_id, source (`csfcube` or `scifact`), source_id, title, abstract,
year (integer 1000–2100 or null), domain (`information_technology`), scope_evidence
(nonempty string list). Text normalization collapses whitespace and joins source
abstract sentences with a space; raw wording/segmentation remain in raw files.
Out-of-range/non-numeric source years become null, never guessed.

`id_map.jsonl`: source, source_id, paper_id, identifiers, content_sha256, active, primary.
Unique key `(source, source_id)`; multiple keys may refer to one canonical paper.
Existing IDs remain reserved if filtering excludes a record (`active=false`).
Exactly one active alias is marked primary per paper; its text stays fixed when new aliases are added. Shared S2ORC
IDs/DOIs/etc merge records; normalized identical titles merge only when abstracts
also normalize identically. Ambiguous titles remain separate pending review.
Source text changes or conflicting issued IDs stop the build for review.

## Facets and annotations

Exactly five keys: `problem`, `task`, `method`, `dataset`, `contribution`.
Each value is a list of normalized concept strings. Multiple values allowed;
missing evidence = `[]`, never null or a bare string. No facets file exists before
annotation. Missing facet evidence is distinct from absence of any annotation.
Native rhetorical sentence labels are retained, never relabeled as these facets.

Silver: `data/exp_a/generated/facets_silver.jsonl`, automated labels.
Gold: `data/exp_a/generated/facets_gold.jsonl`, human-reviewed subset of corpus.
`annotation_metadata.jsonl`: paper_id, tier, dataset_kind, annotator_type,
guideline_version, prompt_version, review_status; one entry per paper/tier.
Mock expected labels and Codex scope reviews do not count as real gold.

## Intent, relevance and behavior (planned interfaces)

Directions: `similar`, `different`, `ignore`; constraints include all five keys.
Missing constrained facet makes a candidate ineligible, not automatically different.
Internal B relevance: 0 irrelevant, 1 partial, 2 high. Native CSFCube relevance is
0–3 and has no approved conversion yet; retain native scale and provenance.
SciFact SUPPORT/CONTRADICT labels are claim evidence, not paper recommendations.
Observable inputs must not contain relevance/satisfaction labels or hidden truth.

Interaction types: click, view, save, like, dislike. All timestamps are ISO-8601
with timezone, preferably UTC (`2026-01-10T10:00:00Z`). Latent weights must be
finite numbers in [-1,1], stored only in `ground_truth/`. D and E share user IDs;
E has a separate event stream with consecutive periods `[start,end)`.
Each user's latest history event must precede earliest holdout event strictly.

## Reproducibility and splits

Default seed: 42. Sort source records before sampling. Manifests include contract
version, dataset kind, generator version/hash, input hashes, seed and actual counts.
No build timestamp is included in deterministic content. Keep native query/claim
split files in raw; they do not assign a global corpus paper split. No new split
is created in this ingestion phase. Future B/C splits must group query anchors;
D/E splits are temporal. Never optimize on held-out gold or future interactions.
Loaders use explicit paths for observable data and separate evaluation truth.

## Scope and acceptance

IT admission uses versioned `configs/scope.json` and the per-record scope audit.
These are automated/Codex-reviewed scope decisions, not human-reviewed facet gold.
Human overrides require an include flag, reviewer and explicit evidence/reason.
Rebuild after changes, preserve ID mappings, review target gaps, then freeze.
Current acceptance: corpus/fixture validation plus runnable corruption tests.
Full experiment acceptance is unavailable until A–E datasets and validators exist.
