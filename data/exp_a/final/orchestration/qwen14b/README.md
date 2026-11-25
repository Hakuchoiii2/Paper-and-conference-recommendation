# Qwen14B Gold400 only

**Completed and downloaded 03/11/2026:** dual-T4 kernel version3 trained for 3 epochs/105 steps; selected `checkpoint-70`. Test60 precision **61.21%**, recall **66.33%**, micro-F1 **63.67%**, macro-F1 **65.62%**, fallback **0**. Results: `../../results/Qwen14B/`; selected adapter: `../../adapter/Qwen14B/`. Import verified 752 output checksums. See [final overview and adapter download instructions](../../README.md) and [five-model metrics](../../results/llm_experiment_metrics.csv).

The original release and its failure are retained below as history. The completed run uses `release_20261102_dual_gpu_v1/` and `/kaggle/working/exp_a_qwen14b_dual_gpu/`.

Standalone private Kaggle kernel `htnkhi/exp-a-qwen14b-gold400`. Derived from the frozen Qwen4B/14B release, with only Qwen14B enabled and revision pinned to the previous run. Uses a dedicated private copy of the verified original input bundle (`htnkhi/exp-a-qwen14b-gold400-inputs`), original training/evaluation policy and T4 x2 hardware. Qwen4B is not rerun.

The previous run failed during PEFT float32 preparation of Qwen14B. This isolated run retains that memory behavior; a fresh GPU session alone is not a verified OOM fix.

Output: `/kaggle/working/exp_a_qwen14b/Qwen14B_completed.zip` after successful completion.

## Dual T4 release — 02/11/2026

`release_20261102_dual_gpu_v1/` replaces single-GPU training in this kernel. Submitted as **kernel version 3**. Previous release files remain unchanged.

- One process sees both GPUs (`CUDA_VISIBLE_DEVICES=0,1`); embedding/layers0–19 on GPU0, layers20–39/norm/output head on GPU1. No DDP or model replication.
- Keep the original pinned Qwen3-14B revision, NF4 double quantization, FP16 compute, PEFT FP32 preparation, frozen base, LoRA rank16/alpha32/dropout0.05, split280/60/60, LR1e-4, accumulation8 and three full epochs.
- Before the full run, train one disposable optimizer step with eight examples covering the longest context and largest completion; check finite/nonzero gradients and actual LoRA updates on both GPUs. Reload that adapter in a fresh process, verify every tensor and compare evaluation losses. The smoke-only step uses no warmup so it performs a real update. The full run starts with fresh base/adapter/optimizer/seed and the original warmup settings.
- Runtime refuses full training if either smoke stage fails. The smoke adapter is **not** the final trained adapter. GPU memory is logged after base load, PEFT preparation, backward, optimizer and reload.
- Full inference/scoring keeps the original two-worker generation policy and checkpoint selection. Completion loss keeps the same masked causal objective, moving labels/normalizer to the logits device.
- New working directory: `/kaggle/working/exp_a_qwen14b_dual_gpu/`. Smoke report: `Qwen14B/results/dual_gpu_smoke.json`. Completed artifact: `Qwen14B_completed.zip`.

Build with `python -X utf8 prepare_dual_gpu.py`; test with the project Python environment using `test_dual_gpu.py`. Five local tests, the existing three Qwen-scales tests, actual bundle preparation/signature checks and independent code review passed before submission. The subsequent Kaggle run passed the smoke gate and completed full training/evaluation on two T4 cards; see the completion summary above.
