> **Tài liệu lịch sử, trước thiết kế 2.0 ngày 2026-10-09.** C/D và các quota/giới hạn ở dưới dùng nghĩa cũ; không dùng làm hướng dẫn hiện hành.
> Xem [protocol 2.0](EXPERIMENT_PROTOCOL.md) và [lệnh chạy mới](RUN_EXPERIMENTS.md). Yêu cầu hiện tại đã bao gồm code thực nghiệm.

# Experiment datasets implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Deliver validated A merge, deterministic 400-paper review selection and
B–E generators at README target sizes.

**Architecture:** Reuse A's validator and corpus utilities; shared I/O enforces
complete silver, hashes and paths. Each experiment owns its generator under `data/exp_*`; reusable rules and
the dataset CLI live under `data/`. Experiment execution/evaluation lives under
`scripts/exp_*`, with shared I/O and validation utilities in `scripts/`.

**Tech Stack:** Python 3.11+ standard library.

**Spec:** `docs/EXPERIMENT_DATASETS_SPEC.md`.

## Global Constraints

- Canonical corpus `data/processed/papers.jsonl`; preserve IDs/text and local A edits.
- Complete A before B–E, seed 42, mock labels/behavior, separate observable/truth.
- B 300×100, C 1,500, D 300×50, E 300×4×15, review queue 400.
- Preserve A parts and existing human review artifacts; no fabricated quota.

## Review Focus

- Forged or missing A coverage must fail before writing output.
- Different annotation provenance or overlapping A parts must stop merging.
- Gold selection must exclude prompt examples and fallbacks and report its bias.
- Missing constrained facets must remain ineligible, not become negatives.
- D/E latent weights, future events and drift groups must remain hidden.

### Task 1: A handoff and gold review selection

Files: `scripts/experiment_io.py`, `data/exp_a/merge_exp_a.py`,
`data/exp_a/select_gold_review.py`, `tests/test_exp_a_handoff.py`.
Interfaces: `load_silver(root, directory, complete=True)` returns corpus, facets,
metadata and manifest; `merge(root, parts, output, dry_run=False)`;
`select(root, source, output, count=400, dry_run=False, allow_partial=False)`.

- [x] Write failing behavior checks for completeness, overlap, provenance,
  deterministic ranking, exclusions and preservation of review work.
- [x] Implement tools without modifying the existing A generator.
- [x] Run new and existing A/corpus checks.

### Task 2: B/C generators

Files: `data/build_experiments.py`, `data/experiment_common.py`,
`data/exp_b/build_exp_b.py`, `data/exp_c/build_exp_c.py`, B/C configs,
intent templates and dataset tests.
Interfaces: `build_b(facets, config, rng)`, `build_c(facets, config, templates, rng)`
return observable/truth records and honest generation reports.

- [x] Write failing literal relevance/intent, missing-facet, quota, split and
  deterministic-rebuild checks.
- [x] Implement sampling with positives/negatives and per-type shortfall reports.
- [x] Run new checks and existing suite.

### Task 3: D/E generators

Files: `data/exp_d/build_exp_d.py`, `data/exp_e/build_exp_e.py`,
shared generator rules, D/E configs and dataset tests.
Interfaces: `build_d(facets, config, rng)`, `build_e(facets, users, config, rng)`;
E consumes D users, never D future events.

- [x] Write failing target-count, shared-user, temporal-boundary, stable/drift
  and hidden-truth checks.
- [x] Implement profile-first simulation and chronological splits.
- [x] Run new checks and existing suite.

### Task 4: Validation, CLI, documentation and review

Files: `scripts/validate_experiments.py`, `scripts/validate_all.py`, exp entry points,
READMEs and validation status. Each runner has dry-run and validate-only modes.

- [x] Write failing corruption/prerequisite checks and implement validators/CLI.
- [x] Verify target-sized test fixtures and byte-identical rebuilds.
- [x] Run real corpus/A checks and dry runs; report missing real A parts.
- [x] Update commands, actual status and human gold explanation.
- [x] Obtain one fresh review and resolve meaningful findings with tests.

## Progress and decisions

Baseline: 46 tests, corpus gate and partial A validator passed (842/4,210).
Work in the current checkout to retain local A edits and data. No Git mutations
or GPU annotation runs are required to implement the generators. Real-data
coverage is never relaxed to demonstrate target counts. Documentation stays in
the existing docs directory because creating the nested specs directory failed.


Completed implementation: A merge/review queue, B–E full-target configs and
generators, CLI, validators and documentation. Fresh full suite: 69 tests passed.
Target-sized fixtures and cross-process deterministic rebuilds passed. Real
corpus and partial A gates passed; all four B–E dry runs stopped at the missing
full A manifest before writing outputs. Merge preview stopped at missing part_2.
Part_1-only 400-paper preview is read-only and not the final review cohort.

One fresh code review completed. Resolved its two important findings with
regression tests: observable D/E behavior distributions now cover history only;
A merge rejects inconsistent recorded runtime model/checkpoint identities while
allowing absent fallback fields. Merge output is confined to experiment A.
Local documentation links and tracked diff whitespace checks passed.

The original local A generator/resume edits remain intact. Keep changes in the
current checkout, as planned; no commit, push, merge or GPU annotation batch.
Real B–E generation and independent human gold remain pending A parts 2–5.
