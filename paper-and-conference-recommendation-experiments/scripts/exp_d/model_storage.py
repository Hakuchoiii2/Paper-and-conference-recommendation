"""Configure D model storage BEFORE importing Hugging Face / torch libraries."""
import os
from pathlib import Path


def configure():
    root = Path(__file__).resolve().parents[2] / 'data/exp_d/model'
    paths = dict(HF_HOME=root / 'hf_home', HF_HUB_CACHE=root / 'hf_home/hub',
                 HF_XET_CACHE=root / 'hf_home/xet', HF_ASSETS_CACHE=root / 'hf_home/assets',
                 SENTENCE_TRANSFORMERS_HOME=root / 'sentence_transformers',
                 TORCH_HOME=root / 'torch', XDG_CACHE_HOME=root / 'cache',
                 TORCHINDUCTOR_CACHE_DIR=root / 'torch_inductor',
                 TEMP=root / 'tmp', TMP=root / 'tmp', TMPDIR=root / 'tmp')
    for key, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(path)
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
    # No authenticated download or executable repository code is needed.
    import tempfile
    tempfile.tempdir = str(root / 'tmp')
    return root
