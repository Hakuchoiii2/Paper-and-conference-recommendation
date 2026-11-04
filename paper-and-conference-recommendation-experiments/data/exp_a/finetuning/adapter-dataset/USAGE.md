# Scientific facet QLoRA adapter v1

Base: `Qwen/Qwen3-8B`, revision `b968826d9c46dd6066d109eabc6255188de91218`.

Adapter weights only. Load the pinned base with the experiment NF4 configuration, then set `adapter_path` to this dataset directory in the shared matrix loader. Use Transformers4.57.6 and PEFT0.18.1. Do not merge into an unrelated base revision.

467 train /100 dev /100 test; pilot50 excluded. GPT/Codex AI reference labels; human review pending. Lowest development loss selects the saved adapter. See training_metadata.json and adapter_manifest.json for provenance and checksums.
