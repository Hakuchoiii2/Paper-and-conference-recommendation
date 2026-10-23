"""Private v2 training only: validate the pinned bundle, then delegate QLoRA."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import zipfile

BUNDLE_SHA256 = '__BUNDLE_SHA256__'
PROJECT = Path('/kaggle/working/exp_a_qlora_v2')


def extract_bundle(bundle, destination, expected_sha256):
    bundle, destination = Path(bundle), Path(destination)
    if hashlib.sha256(bundle.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError('V2 training bundle SHA-256 differs')
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError('V2 extraction directory must be empty')
    root = destination.resolve()
    with zipfile.ZipFile(bundle) as archive:
        names = set()
        for member in archive.infolist():
            name = member.filename
            parts = name.split('/')
            mode = member.external_attr >> 16
            target = (root / PurePosixPath(name)).resolve()
            if (not name or name.startswith('/') or '\\' in name or ':' in name
                    or any(part in ('', '.', '..') for part in parts)
                    or not target.is_relative_to(root) or name in names
                    or member.is_dir() or stat.S_ISLNK(mode)
                    or (stat.S_IFMT(mode) not in (0, stat.S_IFREG))):
                raise ValueError('Unsafe or duplicate v2 bundle member: ' + name)
            names.add(name)
        if 'v2_settings.json' not in names:
            raise ValueError('Missing v2 settings')
        settings = json.loads(archive.read('v2_settings.json'))
        if names != set(settings.get('files', {})) | {'v2_settings.json'}:
            raise ValueError('V2 bundle file inventory differs')
        for name, expected in settings['files'].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError('Changed v2 input: ' + name)
        destination.mkdir(parents=True, exist_ok=True)
        archive.extractall(destination)


def main():
    bundles = list(Path('/kaggle/input').rglob('v2_training_bundle.zip.bin'))
    if len(bundles) != 1:
        raise ValueError('Missing or ambiguous v2 training bundle')
    extract_bundle(bundles[0], PROJECT, BUNDLE_SHA256)
    settings = json.loads((PROJECT / 'v2_settings.json').read_text(encoding='utf-8'))
    os.environ.update(HF_HOME='/tmp/exp_a_huggingface', TOKENIZERS_PARALLELISM='false',
        PYTHONDONTWRITEBYTECODE='1', USE_TF='0', CUDA_VISIBLE_DEVICES='0', WORLD_SIZE='1')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', 'transformers==4.57.6',
        'accelerate==1.15.0', 'bitsandbytes==0.50.2', 'peft==0.18.1'], check=True)
    sys.path.insert(0, str(PROJECT / 'data/exp_a/finetuning/v2'))
    import training
    result = training.run_training(PROJECT, settings)
    print(json.dumps(dict(status=result['status'], counts=result['counts'],
        signature=settings['signature'], training_only=True, evaluation_performed=False)))


if __name__ == '__main__':
    main()
