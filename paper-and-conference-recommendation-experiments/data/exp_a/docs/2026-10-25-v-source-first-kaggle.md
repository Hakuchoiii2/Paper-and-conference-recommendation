# V vs Source-first: design, implementation plan and ledger

User approved implementing and pushing V and source-first to Kaggle. Execute inline with writing-plans, executing-plans and TDD. No additional training or adapter.

Design: same frozen pilot50, Qwen3-8B NF4 revision, greedy decoding, scoped validator, named-dataset filter and unchanged scorer/reference. V reuses the exact cached first draft and runs at most 2 new reviews; Source-first runs inventory -> annotation -> optional validator repair. Both have a ceiling of 3 logical calls x2048 output tokens, with inherited cost reported separately. Actual input tokens/latency differ. The existing development cohort is not held-out validation.

Inventory selects verbatim source spans, candidate facet roles, prior/current/uncertain origin and context sentence IDs. Multiple roles are valid. Annotation still sees ALL source sentences so inventory omissions are not hard exclusion gates. Invalid inventory gets one retry then one annotation call; valid inventory permits annotation + one repair if invalid. Unresolved planning errors and annotation fallback are separate and combined into pipeline fallback. Neither certifies semantics. Single-sentence final evidence schema is unchanged, so cross-sentence caveat links remain an audited representation limitation.

Files: dedicated data/exp_a/.kaggle/source_first/{units.py,runner.py,build.py,bootstrap.template.py,README.md,release_20261025_v1/}; tests scripts/exp_a/pilot/test_source_first.py. Preserve prior releases and unrelated changes; no git checkout rewrite or unrelated commit.

Review focus: fabricated spans and unknown IDs; dual-role artifacts and negative findings; inventory failure/truncation; 3-call budget; all-source access without reference leakage; checkpoint and source/code/prompt hashes; baseline scoring drift.

- [x] Write failing tests for inventory identity, exact spans, role/origin/context constraints, valid negative findings and multi-role units.
- [x] Implement units.validate_inventory and bounded units.annotate; test clean two-call path, retry path, invalid planning fallback, one repair, failed-repair recovery and unchanged input.
- [x] Build frozen code-only release, verify 50 source/raw-draft hashes, test packaged runtime and existing R2a regression.
- [x] Review, fix material findings, rebuild; push private two-T4 kernel htnkhi/exp-a-v-source-first-pilot50 using existing private frozen-input dataset.
- [x] Pull cloud code/metadata, compare bytes and report actual status. RUNNING alone is not proof model workers started. No result claim before output exists.

## Execution ledger

Completed implementation inline. Tests first failed for missing module, then passed after implementation. 92 pilot tests pass; 10 source-first behavioral tests also pass against the packaged runtime. Preflight verified 50 frozen drafts, sources, inventory packets and all code hashes. Fresh read-only review found one P2 reporting defect: V trace omits token-limit flags. Fixed via per-attempt token usage, with a regression test observed failing then passing; metric is calls_at_output_token_cap, not a claim all cap hits are truncation. No remaining launch blockers.

Pushed one private kernel version 1. Kaggle normalized the final slug from the title to htnkhi/exp-a-v-vs-source-first-pilot50. Cloud pull code is byte-identical to the generated release; private/GPU/dataset metadata verified. Status RUNNING; worker startup and result scores pending. Frozen embedded settings keep requested slug as provenance; actual id saved in launch report and local kernel metadata. No old R2a kernel modified. No training, adapter or reference/scorer edits.
