# QLoRA v1: verified paired results

Private Kaggle kernel version 1 completed. Local re-scoring reproduced all cloud TP/FP/FN counts on the same 100 held-out papers. Reference: GPT/Codex AI labels; human review pending. Semantic threshold remains 0.85.

467 train / 100 dev / 100 test; pilot50 excluded. Qwen3-8B NF4, LoRA r16/alpha32; three training epochs, 177 steps. Saved checkpoint 118 (epoch 2), selected by lowest dev loss 0.092656.

| Metric | Original | QLoRA | Change (percentage points) |
|---|---:|---:|---:|
| Micro F1 | 47.44 | 59.28 | +11.83 |
| Macro F1 | 46.99 | 61.00 | +14.02 |
| Problem F1 | 37.45 | 53.04 | +15.60 |
| Task F1 | 48.06 | 62.14 | +14.08 |
| Method F1 | 54.17 | 64.66 | +10.50 |
| Dataset F1 | 51.02 | 73.17 | +22.15 |
| Contribution F1 | 44.24 | 52.00 | +7.76 |

TP/FP/FN: 399/420/464 → 500/324/363. Validation fallback: 69/100 → 9/100.

## Remaining measured errors

Contribution: 119 FP + 121 FN = 240; method: 93 FP + 107 FN = 200. Together they account for 64.05% of the 687 remaining FP+FN events. Problem has 108, task 117, dataset 22.

Observed causes include omitted contribution findings, overly short or merged concepts, inconsistent split granularity, wrong evidence IDs and background methods assigned to the current paper. Seven of nine remaining validation cases concern source wording/evidence alignment; one concerns quantity preservation and one a duplicate concept.

## Generalization across annotation sources

| Reference group | Test papers | Original micro F1 | QLoRA micro F1 |
|---|---:|---:|---:|
| additional_ai_reference | 45 | 53.25 | 56.67 |
| existing_ai_reference | 55 | 42.54 | 61.52 |

All facets improve overall, but improvement is much smaller on the 45 newly sourced papers (+3.42 points) than on the 55 existing-reference papers (+18.98). This is an exploratory subgroup comparison, not evidence of a specific causal mechanism.

## Source-based review examples

- **P000566**: The model omits distinct FoX/NWChem/Avogadro modifications and dictionary entries, often retaining only generic artifact names. The source states each development explicitly. Short method names Avogadro/CML/NWChem are also scored as unmatched against expanded descriptions, so the measured error mixes missing information with alias/granularity sensitivity.
- **P001494**: The source title explicitly names the FRENK Datasets; the model outputs FRENK Datasets while the reference uses FRENK. This appears to identify the same resource yet scores as an unmatched pair. Contributions also differ between the named dataset and generic dataset description; source review is needed before treating every FP/FN as a factual model error.
- **P003080**: The sequence to sequence models are described as a background limitation, but the model includes them under method. It omits Wikipedia/Wizard of Wikipedia under dataset. It splits the retrieval/reading/conditioning method differently from the reference, causing additional FP/FN. Its long contribution claim about knowledgeable discussions is source-supported but absent from the reference, a candidate reference omission.
- **P004079**: The SMT method selects A3, a sentence about out-of-vocabulary words in NMTs. Validation correctly flags that SMT is not in its selected evidence sentence.

Next priority: review annotation consistency and source roles for contribution/method, retain full finding qualifiers, and add difficult newly sourced examples for the next development cycle. The present results establish a useful adapter, but do not establish a corpus-wide quality ceiling.

Full counts, nine residual validation cases, source-group metrics and limitations: `error_analysis_v1.json`. Cloud report snapshots: `cloud_scores_v1.json`. Collection proof: `collection_manifest.json`.

Private reusable adapter target: https://www.kaggle.com/datasets/htnkhi/exp-a-qwen3-8b-facets-qlora-v1 . Publication status is recorded in `push_report.json`.
