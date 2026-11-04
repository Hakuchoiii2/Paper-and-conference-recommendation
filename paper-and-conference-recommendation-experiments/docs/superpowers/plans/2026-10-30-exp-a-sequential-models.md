# Exp A sequential Llama/Gemma run

Goal: archive the current Qwen8B results and prepare a Kaggle bundle that completes Llama8B before Gemma9B, with two generation workers per model.

The user's explicit implementation request supplies the design: reuse accepted gold400 split280/60/60, three QLoRA epochs, validation V-recall F1 checkpoint selection, one selected-adapter test, and per-model saved outputs. Work in this checkout because it contains the uncommitted final release required by this task; do not create a worktree that omits it.

- [x] Add regression tests for model chat formatting, completion-only labels, sequential ordering/failure/resume, and bundle integrity.
- [x] Add a comparison runner around the frozen runtime. Keep model results together under data/exp_a/final/results/Qwen8B, Llama8B and Gemma9B. Train one model on GPU0; split generation over GPUs0/1. Save each completed model before starting the next.
- [x] Package a private Kaggle input bundle and bootstrap with HF_TOKEN access preflight, pinned model revisions, resumable records/checkpoints and instructions. Do not submit or consume Kaggle quota in this task.
- [x] Verify the built bundle and Qwen checksums, run focused and project tests, review the change and report GPU validation limits.

Review focus: Gemma rejects system messages; Llama/Gemma assistant end markers differ from EOS; interruption must not mix model outputs or restart a completed model; gated access must fail before training; test references cannot enter generation inputs. Gemma2 must retain attention softcapping (eager attention), while Llama may use the existing memory-efficient attention implementation. Keep all pre-existing user edits untouched.

Validation: comparison12, project38, legacy training10 and final3 tests pass. Project/legacy tests require a workspace tempfile directory under this Windows sandbox; legacy tests also require offline HF mode and UTF-8 subprocess I/O. Independent review found and verified fixes for interrupted first-checkpoint writes, interrupted provisional-adapter exports and ZIP-before-completion ordering. Original final integrity check still verifies58 files/checkpoint105. No new model weights downloaded, GPU training or Kaggle submission performed; authenticated tokenizer/context/memory validation remains a runtime gate.
