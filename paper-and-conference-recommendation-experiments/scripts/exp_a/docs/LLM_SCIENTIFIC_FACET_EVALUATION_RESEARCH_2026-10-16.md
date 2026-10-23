# Evaluation of scientific facets extracted with LLMs

Research date: 2026-10-16. Scope: LLMs producing scientific-paper facets or structured information, with primary-source evaluation evidence. This note does not treat sentence classification or generic person/location NER as equivalent to our `problem/task/method/dataset/contribution` extraction.

## Main finding

There is no single interchangeable “facet extraction score.” Close systems evaluate broad facet segments by human inspection; scientific entity benchmarks use exact spans or exact entity-list strings; structured scientific summaries use exact/partial F1; other work supplements strict matching with expert semantic adjudication. Scores require their task, matching unit, reference source, and evaluation split to remain attached.

## 1. ScholarSum / Facet-aware Metric — closest explicit LLM facet extractor

**Source:** Wang et al., *New Paradigm for Evaluating Scholar Summaries: A Facet-aware Metric and A Meta-evaluation Benchmark*, arXiv:2402.14359v2, 2025 revision. [Primary HTML](https://arxiv.org/html/2402.14359v2), [PDF](https://arxiv.org/pdf/2402.14359v2).

- **Extraction:** GPT-4 extracts `background/method/result/conclusion` segments from abstracts into JSON; absent facets are empty. See §3.3, PDF p.9.
- **Published extraction result:** **90.3% correct**, human inspection, Figure 8 / §5.3, PDF p.17; prose rounds this to 90%.
- **Data:** the broader meta-evaluation benchmark samples 50 arXiv and 50 PubMed papers, producing 500 generated abstracts. Two PhD annotators score reference/generated summary alignment (§4.1–4.2).
- **Limits:** Figure 8 does not establish item-level precision, recall, or micro F1. The inspected extraction-audit description does not explicitly specify its sample count or denominator. Broad segments differ from our atomic lists. Do not assume all 500 generated abstracts were the Figure 8 extraction sample.
- The paper's FM scores and correlations evaluate **summary alignment / evaluator agreement**, not extraction F1.

## 2. SciER — scientific task/method/dataset spans with LLM prompting

**Source:** *SciER: An Entity and Relation Extraction Dataset for Datasets, Methods, and Tasks in Scientific Documents*, EMNLP 2024. [Primary HTML](https://arxiv.org/html/2410.21155v1), [ACL PDF](https://aclanthology.org/2024.emnlp-main.726.pdf).

- **Extraction:** dataset, method, and task entities, plus relations. LLM pipeline entity extraction is a meaningful comparator for three of our facets; it does not cover free-form problem/contribution claims.
- **Reference/split:** 106 human-annotated full papers: 80 train, 10 dev, 10 in-domain (ID) test, 6 out-of-domain (OOD) test; model inputs are sentence-level.
- **Metric:** strict NER F1 requires both entity span and type to match; see §4.4–4.5 and Table 3, PDF p.8.

| LLM pipeline | ID zero-shot | ID 30-shot | OOD zero-shot | OOD 30-shot |
|---|---:|---:|---:|---:|
| Llama3-70B-Instruct | 61.69 | 76.02 | 53.09 | 63.98 |
| Qwen2-72B-Instruct | 58.57 | 71.44 | 56.43 | 61.72 |

The large-model experiments run five times. These are entity-extraction results. Do not replace them with relation-extraction scores or the supervised HGERE score. These models are substantially larger than our 8B model.

## 3. SciRIFF — directly relevant small LLM extraction benchmark

**Source:** *SciRIFF* final EMNLP 2025 paper. [Primary PDF](https://aclanthology.org/2025.emnlp-main.310.pdf), Table 2, PDF p.6; task specification Appendix D, PDF pp.32–33.

- **Extraction:** the SciERC task maps a scientific abstract to JSON lists of six entity types, including method, task, material, metric, generic, and other scientific term. These are typed entity lists, not complete research contribution summaries.
- **Metric:** micro F1 over typed entity-list entries after lowercasing and trimming; entries are deduplicated per abstract. No offsets or embedding matching. Invalid JSON cases remain in the reported `all` score. Verified in the authors' [SciERC evaluator](https://raw.githubusercontent.com/allenai/SciRIFF/main/sciriff/eval/tasks/scierc_ner.py), [NER metric](https://github.com/allenai/SciRIFF/blob/main/sciriff/eval/metrics/ner_f1.py), and [normalization utility](https://github.com/allenai/SciRIFF/blob/main/sciriff/eval/metrics/util.py).

| Model | Original instruct checkpoint | SciRIFF fine-tuned |
|---|---:|---:|
| Llama3.1-8B-Instruct | 30.6 | 56.8 |
| Llama3.2-3B-Instruct | 20.8 | 58.2 |
| Qwen2.5-1.5B-Instruct | 20.8 | 52.0 |
| GPT-4o | 40.3 | — |
| GPT-5 | 44.0 | — |

This uses the existing human-annotated SciERC benchmark. Exact evaluation-example count was not verified for this note. The paper's average across heterogeneous tasks must not be called extraction F1. Fine-tuned and original-checkpoint columns must remain distinct. SciERC here is different from the newer SciER dataset above.

## 4. ORKG-R0 — structured scholarly contribution values

**Source:** Shamsabadi et al., *Large Language Models for Scientific Information Extraction: An Empirical Study for Virology*, Findings of EACL 2024. [Primary PDF](https://aclanthology.org/2024.findings-eacl.26.pdf).

- **Extraction:** title plus abstract → structured contribution values: disease, location, date, R0, confidence interval, method. FLAN-T5-Large 780M is task fine-tuned (§3–5).
- **Gold:** human annotation; printed test size 300 (135 answerable, 165 unanswerable), §5 / PDF p.6.
- **Metrics:** per-property and overall exact/partial precision, recall, F1. Paper's “overall” is not explicitly named micro or macro in the inspected metric paragraph. Partial matching is not established as embedding-based semantic equivalence.

| Selected best setting | Overall exact F1 | Overall partial F1 | Method partial F1 |
|---|---:|---:|---:|
| Text, s7 training / s8 inference, Table 2 | 44.80 | 55.89 | 47.79 |
| JSON, d3 training / s6 inference, Table 3 | 42.91 | 55.28 | 45.83 |

Tables 2–3 are on PDF p.7 / proceedings p.380. Different text-row exact scores can be higher: 44.80 is the exact score paired with the best-partial setting, not the maximum exact score of every experiment. Dataset counts are inconsistent: “1500” versus printed 1082/120/300 splits totaling 1502. Zero-shot Table 1 uses ROUGE, not extraction F1.

## 5. Structured materials extraction — strict versus expert semantic scoring

**Source:** Dagdelen et al., *Structured information extraction from scientific text with large language models*, Nature Communications 15, 1418 (2024). [Primary article](https://www.nature.com/articles/s41467-024-45563-x), [Author-hosted PDF](https://perssongroup.lbl.gov/papers/dagdelen_structured_information_extraction_2024.pdf).

General-JSON extracts material names, formulae, applications, structures, and descriptions from abstracts. Table 1 reports 634 abstracts, human-annotated; general-task automatic evaluation averages five random 90/10 splits. Models are task-fine-tuned GPT-3 davinci 175B and Llama-2 **70B** LoRA, not 7B.

Tables 2–3, PDF p.4, report these GPT-3 results:

| Field / formula-linked relation | Strict per-word relation F1 | Expert manual entity F1 |
|---|---:|---:|
| Name | 45.6 | 81.8 |
| Application | 53.7 | 83.2 |
| Structure / phase | 48.2 | 82.9 |
| Description | 35.4 | 70.4 |

The manual score accepts reasonable normalization/paraphrase, but still requires correct field and grouping under the correct material. It uses a random 10% test sample. The columns have different scoring units and evaluation aggregation; they are not a controlled “same metric + relaxed threshold” comparison. This is domain-specific structured IE, not our research-role ontology. Do not use its separate doping-task 82.1 F1 as a broad-facet result.

## A close facet system without a comparable extraction F1

**Scideator** extracts purpose, mechanism, and evaluation facets from title/abstract using GPT-4o by default. This is conceptually close to our application. Its Table 1 **89.66%** is downstream retrieval accuracy; Table 2 **0.79 macro F1** is downstream novelty classification. Neither establishes facet-extraction precision/recall. [Primary paper, §2/§4.2/Appendix F](https://arxiv.org/html/2409.14634v7).

## Implications for exp_A (interpretation and proposed measurement)

These are methodological recommendations, not changes implemented by this research note:

1. Retain a reproducible item-level score: per-facet precision/recall/F1, pooled micro F1, and macro F1 with the empty-facet convention documented. Name our current score **semantic agreement with AI reference**, because the reference is not human gold.
2. Add a human-adjudicated sample under a frozen annotation guide. Inspect both predicted items and source information to measure false additions **and omissions**. Judging only whether predictions are plausible gives a precision-like measure and cannot establish recall.
3. Report a strict string/span result alongside semantic item matching when suitable; keep numeric values, polarity, evidence, and facet role in the semantic acceptance rule. Inspect disputed matches such as acronym/full-name equivalence instead of simply lowering the cosine threshold.
4. If using an LLM judge, first test it against independent human pair judgments. Judge equivalence/coverage separately from source support and role correctness. An embedding-similarity cutoff by itself is not validated human semantic equivalence.
5. Reserve an untouched human test set; show uncertainty on a small sample. The published numbers above are context, not thresholds our current 30 reused dev papers must beat.

No experiment code, prompts, scoring implementation, or Kaggle kernel was changed for this research.
