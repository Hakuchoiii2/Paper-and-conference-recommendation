# Llama/Gemma: progress logging fix

This local release adds elapsed-time logs around setup, Hugging Face access, tokenizer loading, evaluator downloads and batch launch. Tokenizer preflight reports the first example, every 25 examples and the final count. The stop-token vocabulary is fetched once per example instead of once per answer token. Child processes inherit unbuffered output.

## Apply on Kaggle

1. Stop the old run in Kaggle. Updating local files cannot change an already running process.
2. Upload `input-dataset/llama_gemma_bundle.zip.bin` as a new version of the existing private dataset `htnkhi/exp-a-llama-gemma-gold400-inputs`. Keep the dataset private.
3. In the notebook editor, update the input dataset to that new version and replace the script with `kernel/run_llama_gemma.py` from this release. The script pins the new bundle checksum, so both updates are required.
4. Set HF_TOKEN in the private editor as before, or enable the existing HF_TOKEN secret. The local script has no token. Select T4 x2, enable Internet, then Save & Run All.

The old release is preserved. This release has not been uploaded or submitted by its build command. CPU tests cannot establish the duration of a full Kaggle GPU run.
