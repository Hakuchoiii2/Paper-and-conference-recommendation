# Global data contract

Versions: **corpus/A 1.0**, **B–E and evaluation 2.0**. Owner: Khai.
The current A–E protocol is [EXPERIMENT_PROTOCOL.md](docs/EXPERIMENT_PROTOCOL.md).
C now means preference inference (formerly D); D means automatic session direction (formerly C).
Changing field meaning requires a version bump; v1 mock artifacts must be rebuilt in new destinations.

## Encoding, identity and corpus

UTF-8 JSONL (one object per line); JSON for config/manifests. Canonical corpus:
`data/processed/papers.jsonl` is the only paper catalog for all experiments,
including mock runs. Keep its IDs/title/abstract unchanged; no sample catalog or
separate mock paper namespace. A extracts source-grounded silver facets into `data/exp_a/generated/facets_silver.jsonl`.
B–E mock means synthetic queries/intents/rule labels/users/behavior on real
corpus IDs and A facets. Do not fabricate paper facet annotations.
Mock experiment manifests use dataset_kind=mock and identify the real input
corpus path/hash; the corpus manifest remains dataset_kind=real. Record label
coverage and reject unknown IDs; missing annotation is not an empty facet list.
`paper_id`: `^P[0-9]{6}$`; `user_id`: `^U[0-9]{4}$`;
B query IDs: Q0001; D case/session IDs: D00001. Search/exposure IDs include their session namespace.
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
annotation; absent annotation is never substituted with empty lists. Missing facet evidence is distinct from absence of any annotation.
Native rhetorical sentence labels are retained, never relabeled as these facets.

Silver: `data/exp_a/generated/facets_silver.jsonl`, automated labels.
Gold: `data/exp_a/generated/facets_gold.jsonl`, human-reviewed subset of corpus.
`annotation_metadata.jsonl`: paper_id, tier, dataset_kind, annotator_type,
guideline_version, prompt_version, review_status; one entry per paper/tier.
A also records local model/revision/runtime, seed/attempt and token counts and evidence objects
(concept, exact quotation, source title/abstract) for every nonempty facet.
The silver manifest must report complete corpus coverage before B–E handoff;
partial outputs explicitly list missing IDs. Quotation presence is a structural
check; semantic correctness still requires human review.
Mock expected labels and Codex scope reviews do not count as real gold.

## Intent, relevance and behavior (B–E 2.0)

B queries contain query_id, query_paper_id and candidate_ids; no target_facet input.
Fixed importance is config-owned. Relevance is a continuous weighted sum of concept grades 0/1/2.
Native CSFCube 0–3 judgments and SciFact evidence labels retain their native meaning.

C owns users.jsonl and hidden latent_user_profiles.jsonl (concept preferences + normalized facet_importance).
D/E use C identity and manifest. D also reads C history/search; E simulates a separate temporal stream.
Profile truth is generated before behavior, never reconstructed from events.

Search: query_id, user_id, session_id, text, parent_query_id, timestamp.
Exposure: exposure_id, user_id, session_id, query_id (nullable), ordered paper_ids, timestamp.
Interaction: user_id, paper_id, interaction_type, timestamp, session_id, exposure_id.
Search precedes exposure; exposure precedes its feedback. Parent queries stay within user/session and precede the child.
Interaction types: view/click/save/like/dislike. Use timezone-aware ISO-8601, preferably UTC.
Latent preferences are finite [-1,1]; facet_importance is nonnegative and sums to one.

C cases: case_id, user_id, candidate_ids, cutoff.
D sessions: case_id, user_id, query_paper_id, context_facet, candidate_ids, cutoff.
D hidden intent: case_id, focus_facet, directions, facet_importance, query_mode.
Directions have five keys and true states similar/different/ignore. Predicted unknown is abstention, not true ignore.
D context is a controlled retrieval condition; hidden focus/direction is never a public scorer feature.
C/E future events and D intent labels are evaluation-only. Only evaluator-owned oracle_intent gets true intent/importance.
Missing facet evidence never earns a "different" reward.

E cases additionally contain period. Its hidden profiles add period/start_timestamp/end_timestamp.
E evaluates periods 2/3/4 using previous-period prefixes. History storage covers periods 1–3;
evaluation storage covers periods 2–4, with identical duplicated observations for rolling reuse.
Raw storage partition is not sufficient: filter every history/query/exposure at each case cutoff before scoring.

## Reproducibility and splits

Seed 42; sort records/concepts before sampling. Versioned manifests include config, generator/input hashes,
file checksums, counts and actual complete/partial status. B groups anchors 70/15/15.
C uses chronological history/holdout; D uses the session prefix; E uses rolling period boundaries.
Public scorers share cases/candidates/visible prefixes; never tune on test outcomes.
Unobserved or unjudged items are not automatically negative.
Outputs under results/ are separate from dataset truth, with evaluation version 2.0.
Legacy outputs and unrelated files are preserved: use new output/truth destinations rather than silently relabeling.
See the protocol for exact utility, query generation/parsing, feedback weights and metric definitions.

## Scope and acceptance

IT admission uses versioned `configs/scope.json` and the per-record scope audit.
These are automated/Codex-reviewed scope decisions, not human-reviewed facet gold.
Human overrides require an include flag, reviewer and explicit evidence/reason.
Rebuild after changes, preserve ID mappings, review target gaps, then freeze.
Current acceptance: main-corpus validation plus runnable corruption tests.
A–E generators and validators exist. Full acceptance additionally requires the real-corpus outputs and independent human review.

The local Qwen prompt v1.5 uses extractive concept phrases: normalized label
words must occur in the selected evidence sentence. This avoids generic
facet-definition labels; paraphrases are rejected in this extraction mode.
Sentence-ID presence and source phrase checks do not replace semantic review.

Local A policy 2.3 saves the highest-scored attempt when validation still fails:
metadata records fallback_used, validation_errors and all attempt scores/raw outputs;
manifest.fallback_annotations audits these records. A missing ID means no saved
record, distinct from an audited fallback that may contain empty facets.
Runtime/GPU failures still stop. Full downstream handoff requires complete coverage;
B–E generation excludes every fallback or quality-flagged record.

The 400-paper selection creates a pending human review queue under
data/exp_a/ground_truth/gold_review, never automatic facets_gold.jsonl.
Ranking favors nonempty facets, then supported concepts, then paper ID; exclude
P000001 prompt development, fallbacks/errors and all-empty annotations.
Its completeness bias must accompany evaluations. Human labels are produced
independently before comparing the separately stored silver reference.
