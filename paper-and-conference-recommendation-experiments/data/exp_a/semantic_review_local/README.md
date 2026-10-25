# Local semantic-review spike

User-authorized exploratory test on existing R2a-full outputs. All files are separate from extraction code and records. This script only writes reviewer warnings; it never applies patches or exports revised annotations.

Model: cached Qwen3-4B-Instruct-2507, revision `cdbee75f17c01a7cc42f958dc650907174af0554`, local NF4 double quantization, FP16 compute, RTX 4060 Laptop 8 GB. Offline model/tokenizer loading, greedy decoding, 2048-token cap per paper, one call per paper, no retry. Not the Kaggle Qwen3-8B model.

Sample: four known cases plus four seeded random papers from the same pilot50 cohort, eight papers and 74 existing items. This is a development probe, not a held-out semantic benchmark. Reference, evaluation scores, fallback and known-case status are excluded from model packets. Empty facet lists/missing-label coverage are outside this item-level test.

Before inference, `source_first_notes.json` records Codex's provisional source-based item judgments. These are not independent human annotations. The generation never receives this file. Outputs are validated for exact item IDs, supported operation-free schema and verbatim quotes. Invalid replies remain rejected; raw replies are preserved. Diagnostic ID prefix removal in the analysis does not change acceptance or annotations.

`spike.py self-check` checks warning validation. `prepare` refuses to overwrite the existing run directory; `run` refuses to overwrite prior model results. For a new experiment, explicitly version the run directory before preparing. Preserve v1 prompt and results when changing the design.

See [result report](../docs/2026-10-25-local-semantic-review-spike.md), [summary](run_20261025_v1/summary.json), [raw outputs and input packets](run_20261025_v1/), and [post-run rationale judgments](run_20261025_v1/rationale_adjudication.json).
