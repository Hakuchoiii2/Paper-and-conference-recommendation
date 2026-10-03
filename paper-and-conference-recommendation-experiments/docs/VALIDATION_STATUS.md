# Verification — local Qwen, 2026-10-03

- Local runtime: Python 3.11.16; PyTorch 2.6.0+cu124; Transformers 4.57.6;
  accelerate 1.15.0; bitsandbytes 0.50.2. CUDA is available on RTX 4060 Laptop 8 GB.
- Qwen/Qwen3-4B-Instruct-2507 revision cdbee75f17c01a7cc42f958dc650907174af0554
  loaded and inferred successfully using NF4 double 4-bit, float16 compute.
  Observed VRAM during the smoke run: approximately 3.8 GB.
- 14 unit checks passed; main corpus gate passed: 4,210 papers, 4,235 active
  source references, 9,390 audit records. Corpus text and IDs remain unchanged.
- Prompt 1.5, guideline 1.0: five real papers accepted in the pilot and the
  partial-output validator passed. P000001 is a prompt-development example;
  exclude it from held-out human gold.
- Structural/source checks cover exact evidence, source phrases, IDs, schema,
  resume, provenance, duplicate-run lock, partial export and Windows launcher.
  They do not measure semantic accuracy or extraction completeness. One of the
  first five papers received five empty lists; this is a model output that needs
  semantic review, not a missing paper filled by the code.
- The full run was started at 2026-10-03 12:00 Asia/Bangkok, resuming after the
  five pilot records. That run stopped after six accepted papers on a validation error in P000007. The batch runner now records per-paper validation rejections and continues with later papers; runtime/GPU failures still stop. Six previously accepted records are preserved in generated/pre_batch_snapshot and are reprocessed under the new generator hash. The batch flow passed a real rejection at P000007 and continued to later papers. Before the final zero-annotation reset fix, seven accepted records and logs were preserved in generated/pre_reset_fix_snapshot; SQLite integrity_check passed. The final full run was launched after the fix; generator, prompt and config remain frozen for this run. This is a launch snapshot, not a completion claim. Read the
  checkpoint for live counts; manifest/JSONL export on completion or handled stop.
  B–E may consume the full corpus only after complete A validation succeeds.
- No API key is used for inference; no human gold is generated. Failed API
  outputs and rejected local pilots remain in generated audit subdirectories.
  Annotator is qwen_local, tier silver, review_status unreviewed.
