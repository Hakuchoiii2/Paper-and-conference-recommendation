# R2a pilot50 — 24/10/2026

## Results checked 25/10/2026

Kaggle status: COMPLETE; all three arms logged 50/50 records. [Results review](../../docs/2026-10-25-r2a-results-review.md) includes the comparison, source checks and next steps. Downloaded summaries, evaluations, records and log are under `review_20261025/`. Launch-time status below is historical.

Micro F1: R2 historical 56.5046%, R2a-V 56.6929%, R2a-P/full 55.4124%. Fallback: 18/18/15/14 respectively. P/full preserve protected items before the common dataset filter; lower fallback does not establish better semantic quality. AI reference and unchanged scorer limitations still apply.

User-approved private Kaggle run: https://www.kaggle.com/code/htnkhi/exp-a-r2a-v-p-full-pilot50

Implementation plan and execution ledger: [R2a Kaggle plan](../../docs/2026-10-24-r2a-kaggle.md). Experiment-specific design and plan documents belong under `data/exp_a/docs/`.

| Arm | Scoped extraction validator | Indexed repair |
|---|---|---|
| R2a-V | Yes: only leading-Although contrast scope | No: original R2 full review |
| R2a-P | No: original policy3.1 | Yes: original invalid item identities only |
| R2a-full | Yes | Yes |

No added coverage pass, retraining, adapter, scorer/reference change or R4. Uses exactly the original pilot50 frozen sources, AI reference, 8B NF4 model revision, raw R0 first drafts and greedy seed schedule. Max3 logical calls ×2048 output tokens/paper, including inherited draft, so max2 new calls. P/full may need no new calls when the draft passes the selected validator; this is validator validity, not semantic certification.

Patch edits are atomic replacements/removals/unresolved decisions. No additions; original identities survive index shifts. Protected items cannot become editable in later calls. Replacements cannot introduce duplicate concepts. Removals require a supplied source ID and a reason/explanation, which remain unverified model assertions for source audit.

The historical named-dataset postfilter remains common to all arms. It can remove labels outside the patch scope, so `protected_items_changed` for P/full is measured BEFORE this filter and its removals are separately counted in `common_dataset_filter_removed`. V is unrestricted review; its analogous counter is descriptive, not an identity guarantee.

## Evidence and outputs

- `release_20261024_v1/preflight.json`: input/model/code configuration and local verification.
- `release_20261024_v1/cloud_snapshot_verified.json`: fresh download; bundle and50 R0 bytes match.
- `release_20261024_v1/launch_report.json`: verified cloud code/private metadata and last observed status. RUNNING alone does not prove model workers started.
- `regression_tests_final.log`:82 pilot checks passed, including9 new R2a checks.
- `validator_replay.json`:134 original attempts; only P001181 changes validator outcome, in3 attempts.

On Kaggle, outputs are under `/kaggle/working/exp_a_r2a/results/`: signed records per arm, raw patch replies/applied annotations, operation reasons, original/scoped common gate outcomes, costs, per-facet evaluation, `experiment_summary.json` and `experiment_table.md`. The table includes cached R0 and historical R2 controls alongside the3 new arms. Micro F1 is agreement with the frozen AI reference and a known-imperfect scorer, not validated semantic accuracy.

## Commands from project root

```powershell
.\.venv-qwen\Scripts\python.exe -X utf8 -B scripts/exp_a/pilot/test_r2a.py
.\.venv-qwen\Scripts\python.exe -X utf8 -B data/exp_a/.kaggle/r2a/build.py
kaggle kernels status htnkhi/exp-a-r2a-v-p-full-pilot50
kaggle kernels output htnkhi/exp-a-r2a-v-p-full-pilot50 -p data/exp_a/.kaggle/r2a/downloads -o
```

Preflight/rebuild does not push or run a kernel. Cloud launch requires `kaggle kernels push -p .../release_20261024_v1/kernel --accelerator NvidiaTeslaT4`. Do not overwrite the pinned release/code while the run is active; use another version for changes.
