# Exp A: open-weight extraction candidates

Researched 2026-10-30 against first-party model cards. This is a candidate list for title/abstract -> five-facet JSON, not a claim of measured task quality or Kaggle T4 feasibility. No GPU experiments were run for this note.

## Recommended comparison

Use these five weights, with existing gold400 QLoRA as a sixth configuration of Qwen3-8B. Keep pretrained instruction weights versus task-tuned weights explicit in result tables.

| Exact repository ID | Role and caveat | Official source |
|---|---|---|
| `Qwen/Qwen3-8B` | Existing 8B anchor. Disable thinking explicitly with `enable_thinking=False` in its own chat template; thinking is enabled by default. | [Qwen card](https://huggingface.co/Qwen/Qwen3-8B) |
| `Qwen/Qwen3.5-9B` | Current within-family update, 9B language model with vision encoder and hybrid DeltaNet/attention layout. Post-trained despite no Instruct suffix. Requires its supported recent Transformers/backend and processor; disable thinking. Do not assume the Qwen3 causal-LM loader/LoRA targets transfer. | [Qwen3.5 card](https://huggingface.co/Qwen/Qwen3.5-9B) |
| `meta-llama/Llama-3.1-8B-Instruct` | 8B independent-family anchor. Use its tokenizer/chat template and model generation config, not Qwen control tokens. Check gated weight access and Llama license before Kaggle download. Card documents Transformers >=4.43.0. | [Meta card](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) |
| `mistralai/Ministral-3-8B-Instruct-2512-BF16` | Newer Mistral family: 8.4B LM + 0.4B vision encoder, instruction-tuned, JSON output support. Prefer this official full-precision source for an NF4 pilot. The unsuffixed repository is FP8, a different loading path. | [Official BF16 card](https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512-BF16) |
| `google/gemma-4-E4B-it` | Current Google comparison: 4.5B effective, 8B including embeddings. Closer parameter-storage tier to 8B anchors, explicitly not equal compute. Requires supported Gemma4 loader/processor, own template, and response parsing; conditional on a T4 pilot. | [Google card](https://huggingface.co/google/gemma-4-E4B-it) |

## Loading and comparison traps

- Ministral: official instructions use `Mistral3ForConditionalGeneration` and `MistralCommonBackend`; card requires `mistral-common >=1.8.6`. If using unsuffixed FP8 weights, its official recipe dequantizes with `FineGrainedFP8Config(dequantize=True)` before any separately validated NF4 conversion. Avoid an unmeasured FP8 -> BF16 -> NF4 startup memory peak by piloting the official BF16 source instead. This still does not prove successful 4-bit loading. [Mistral instructions](https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512#transformers)
- Gemma4: the official example uses `AutoProcessor`, `AutoModelForMultimodalLM`, `enable_thinking=False`, decoding with special tokens retained, then `processor.parse_response(...)`. Non-E2B/E4B variants can retain an empty thought channel even when thinking is disabled. Parse the final answer before strict JSON validation; preserve the raw completion for audit. [Google instructions](https://huggingface.co/google/gemma-4-12B-it)
- Use each model's chat template; when rendering to text then separately tokenizing, do not duplicate special tokens. Decode generated tokens after the input length. Model-specific formatting is needed even when the semantic extraction instruction is held constant. [Transformers templates](https://huggingface.co/docs/transformers/chat_templating)
- NF4 quantizes eligible linear layers; embeddings, activations, KV cache and runtime buffers remain relevant. Record actual peak allocated/reserved GPU memory, prompt/output tokens, seconds per record, JSON/schema validity and truncation. Pin resolved model revisions and package versions. Successful quantized inference does not prove QLoRA training feasibility. [Transformers bitsandbytes](https://huggingface.co/docs/transformers/quantization/bitsandbytes)

## Fallbacks and smaller ablations

- `google/gemma-4-12B-it`: optional stronger Google upper-size comparison (11.95B), only if the T4 pilot and budget permit. It exceeds the 8-9B comparison band. The core E4B candidate uses per-layer embeddings and is **4.5B effective but 8B including embeddings**, not a conventional 4B dense checkpoint; report both quantities. [Google 12B card](https://huggingface.co/google/gemma-4-12B-it), [Google E4B card](https://huggingface.co/google/gemma-4-E4B-it)
- `google/gemma-2-9b-it`: older Google size-matched alternative with simpler text-only architecture, useful for a reproducible 8-9B-only table. Its legacy template supports user/model roles; put instructions in the first user message rather than injecting a system role. [Gemma2 card](https://huggingface.co/google/gemma-2-9b-it), [legacy Google formatting](https://ai.google.dev/gemma/docs/core/prompt-structure)
- `Qwen/Qwen3-4B-Instruct-2507`: 4B cost/size ablation, non-thinking only; no need for `enable_thinking=False`. Card requires Transformers >=4.51.0. Same family, so it adds size evidence rather than family diversity. [Qwen card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)
- `google/gemma-3-4b-it`: older 4B multimodal Google fallback, uses Gemma3 conditional-generation/processor path rather than assuming Qwen's loader. [Google card](https://huggingface.co/google/gemma-3-4b-it)
- `mistralai/Mistral-7B-Instruct-v0.3`: older 7B text-only reproducibility fallback. Uses v3 tokenizer and 32768 vocabulary; do not reuse v0.1/v0.2 tokenizer assets. [Mistral card](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3)

Selection rationale is an experimental-design recommendation, not a manufacturer benchmark claim: retain one established anchor, one current within-family update, and independent Meta/Mistral/Google families. Run a small fixed schema-validity and memory pilot before committing the full held-out evaluation. Keep any fallback substitution explicit.

