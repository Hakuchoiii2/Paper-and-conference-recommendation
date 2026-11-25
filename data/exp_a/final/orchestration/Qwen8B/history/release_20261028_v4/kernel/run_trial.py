"""Private Kaggle bootstrap for the gold400 training/validation/test trial."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import zipfile

BUNDLE_SHA256 = 'b2216c95e9ac50bdc0e8bc722a176d78b00b9526d7579fa2c87d9a5f03c80eaa'
PROJECT = Path('/kaggle/working/exp_a_v_recall_gold400_qlora')


def extract(bundle, root):
    if hashlib.sha256(bundle.read_bytes()).hexdigest() != BUNDLE_SHA256:
        raise ValueError('Bundle hash differs')
    if root.exists() and any(root.iterdir()):
        raise ValueError('Refusing to overwrite an existing run')
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate bundle member')
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if path.is_absolute() or any(p in ('', '.', '..') for p in info.filename.split('/')) or '\\' in info.filename or ':' in info.filename or stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError('Unsafe bundle member')
        settings = json.loads(archive.read('settings.json'))
        if set(names) != set(settings['files']) | {'settings.json'}:
            raise ValueError('Unexpected bundle inventory')
        for name, expected in settings['files'].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError('Changed bundle file: ' + name)
        archive.extractall(root)


def main():
    candidates = list(Path('/kaggle/input').rglob('gold400_qlora_bundle.zip.bin'))
    if len(candidates) != 1:
        raise ValueError('Missing or ambiguous trial bundle')
    extract(candidates[0], PROJECT)
    os.environ.update(HF_HOME='/tmp/exp_a_huggingface', TOKENIZERS_PARALLELISM='false',
                      PYTHONDONTWRITEBYTECODE='1', USE_TF='0', WORLD_SIZE='1')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', 'transformers==4.57.6',
                    'accelerate==1.15.0', 'bitsandbytes==0.50.2', 'peft==0.18.1'], check=True)
    manifests = list((PROJECT / 'data/exp_a/evaluation/embedding_probe/.model_cache').glob('*/download_manifest.json'))
    if len(manifests) != 1:
        raise ValueError('Missing pinned embedding manifest')
    from huggingface_hub import hf_hub_download
    manifest = json.loads(manifests[0].read_text(encoding='utf-8'))
    for name, info in manifest['files'].items():
        path = manifests[0].parent / name
        if not path.is_file():
            path = Path(hf_hub_download(manifest['model'], filename=name, revision=manifest['revision'], local_dir=str(manifests[0].parent), token=False))
        if hashlib.sha256(path.read_bytes()).hexdigest() != info['sha256']:
            raise ValueError('Embedding hash differs: ' + name)
    print('INPUTS VERIFIED: gold400, train280/valid60/test60, seed42; final checkpoint chosen by validation F1; no F2.', flush=True)
    subprocess.run([sys.executable, '-B', str(PROJECT / 'runtime.py')], cwd=PROJECT, check=True)


if __name__ == '__main__':
    main()
