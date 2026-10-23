# QLoRA v1: Kaggle training, reusable adapter, paired evaluation

User-approved work: train Qwen3-8B with QLoRA on Kaggle, download the adapter and
publish it to a private Kaggle dataset for reuse, evaluate on 100 papers different
from pilot50, organize matrix/pilot code and remove obsolete pre-3.5 outputs/tests.
Latest steering fixes train/dev/test at 70/15/15 and requests additional corpus
papers extracted and reviewed with GPT to retain 100 test papers.

## Data contract

- Target667 complete validated papers:467train,100dev,100test (largest remainder).
- Existing400 references are AI-reviewed, not human gold. Five pending source
  cases excluded;364 complete targets pass current grounding with exact evidence
  ID remapping only. No individual labels dropped to make a paper pass.
- Additional papers come from the same4210-paper corpus, excluding all400 reviewed
  IDs, all50 pilot IDs, prompt example IDs and duplicate normalized titles.
- GPT via Codex performs source-grounded extraction and an independent review
  pass. Record AI provenance, source hashes, evidence IDs and review decisions;
  do not claim an external GPT API call or human annotation.
- Stratify by presence of each facet, multiple labels per facet, all-empty papers,
  source length and old/new annotation provenance. Check exact target counts and
  zero source/title/ID overlap across folds and zero overlap with pilot50.
- Reject complete papers with unsupported targets or excessive token length;
  collect more reviewed cases if necessary. No silent truncation or label deletion.
- References for test100 stay outside model_inputs and are read only by scoring.
  The100 are held out from this QLoRA run; existing AI-reference papers have prior
  project history, so this does not establish untouched human-test performance.

## Model and run contract

- Qwen/Qwen3-8B revision b968826d9c46dd6066d109eabc6255188de91218.
- Original3.7 guideline/prompt, same minimal concept+evidence_id schema, disabled
  thinking, greedy decoding, max_new_tokens2048, unchanged extract/review3.7.
- NF4 double quantization, FP16, one T4 training worker, LoRA all-linear r16,
  alpha32, dropout0.05, batch1, gradient accumulation8, max sequence4096,
  gradient checkpointing, seed42, three epochs and best checkpoint by dev loss.
- Completion-only loss: system/user/padding tokens ignored, assistant JSON and
  end token supervised. Qwen3 computes vocabulary logits only at positions that
  predict supervised completion tokens, preserving the full prompt context and
  exact masked causal loss while avoiding large prompt-logit allocations on T4.
  Verify loss and all LoRA gradients against full masked CE, and an actual tiny
  Trainer accumulation/eval/best-adapter restoration cycle.
- Train finishes before two separate evaluation workers load base and adapter
  models. Both generate fresh predictions on the same100 inputs with matching
  budgets/backends. Test references never enter generator messages.
- Semantic micro/macro and per-facet P/R/F1, source flags, cost and coverage are
  reported with the pinned embedding evaluator and threshold0.85.
- Save adapter only plus tokenizer/metadata/checksums. Base model stays separate.
  Publish adapter with exact base revision and prompt/schema/data provenance.

## Layout and delivery

Existing Kaggle matrix code moves to data/exp_a/.kaggle/matrix/ and pilot code to
data/exp_a/.kaggle/pilot/. Associated tests are grouped under scripts/exp_a/.
Shared extraction/evaluation stays shared. Live4210-paper generated baseline is
retained because experiments B–E and pilot building depend on it.

New code lives in data/exp_a/finetuning/, tests in scripts/exp_a/finetuning/.
Private destinations: htnkhi/exp-a-qwen-qlora-inputs (input dataset),
htnkhi/exp-a-qwen-qlora (kernel), htnkhi/exp-a-qwen3-8b-facets-qlora-v1 (adapter).
User is notified after the fine-tuning kernel is pushed. A thread follow-up checks
completion, downloads/validates outputs, publishes the adapter privately and
reports paired evaluation. An incomplete/failed run must not publish an adapter.

Execution uses the existing checkout: essential experiment files are untracked
and would be absent from a new worktree. No broad git commit/reset is authorized
or needed. Cleanup deletion paths are checked inside this project and listed in
data/exp_a/cleanup_manifest_2026-10-16.json.
