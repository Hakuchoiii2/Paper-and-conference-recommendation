# Qwen4B / Qwen14B sequential Kaggle run

User explicitly authorizes implementation and immediate private Kaggle submission. Run Qwen3-4B then Qwen3-14B like the existing fine-tuned comparison, using the same accepted gold400 split and public token-free model downloads. Preserve the user's Llama/Gemma cloud kernel with its manually entered token; do not pull or push its source.

- [x] Tests first for reuse of the existing dataset, no token requirement, accepted Qwen training prefix, sequential save/resume behavior.
- [x] Build a standalone code-only kernel with overlays for anonymous Qwen loads and memory-efficient attention; preserve original data as immutable source/.
- [x] Run focused/current tests, review generated code and verify input/data hashes.
- [x] Submit private T4x2 kernel against the existing dataset, verify cloud configuration and observe actual startup/trainer initialization.

Constraints: preserve3epochs/LR1e-4/seed42/LoRA16/effective batch8 and the original sequence/token budgets. Train on oneGPU, generate on two independent workers. Do not change budgets silently to fit14B. Save each model before the next starts and retain checkpoints on failure.

Verified:46 CPU tests passed (3scale,5final,38project), final checksum gate78 files passed, independent review found no confirmed code/privacy blocker. Private kernel version1 submitted at https://www.kaggle.com/code/htnkhi/exp-a-qwen4b-14b-gold400 with NvidiaTeslaT4. Both models passed public access/tokenizer preflight; exact revisions recorded in release deployment.json. Cloud log showed Qwen4B checkpoint shards loaded and Trainer initialized. Full training, evaluation and14B memory remain ongoing/unmeasured. The user's Llama/Gemma cloud source was not read or changed.
