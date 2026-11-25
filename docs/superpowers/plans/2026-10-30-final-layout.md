# Consolidate Exp A final layout

User authorized moving all active experiment code into data/exp_a/final, with separate Qwen8B and gemma-llama orchestrators and shared prompt/policy/config outside those two directories.

- [x] Add layout/build regression tests and observe the missing-layout failures.
- [x] Move existing code/releases; preserve historical artifacts under orchestration/Qwen8B/history and actual cloud provenance under Qwen8B/provenance.
- [x] Centralize shared payload assembly in final/package.py, reading final/runtime, prompts and reference; keep models.json outside orchestrator directories.
- [x] Update entrypoint/config/manifest, links, tests and package defaults; remove the vacated old directories.
- [x] Verify both bundles retain their exact previous SHA-256, run moved/current tests, and get independent review.

Validation: final entrypoint/layout5 + Qwen16 + Llama/Gemma12 + project38 =71 passing CPU tests. Qwen bundle remains41936f5b1b9d1e2bc9e60de4bd224ce2e55bbe8c1ae4f550a1509c95fd479ef9; Llama/Gemma bundle remains6259ddb570c4c208d0aeb2e8a17d5ac984701f391f65f08964145bd6a710b510. No GPU training or cloud submission. Review confirmed active paths and imports are local to final/.
