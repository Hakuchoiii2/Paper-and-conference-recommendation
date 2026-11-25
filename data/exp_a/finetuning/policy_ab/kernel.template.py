"""Private, inference-only policy comparison using the published sealed adapter."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

PROJECT = Path('/kaggle/working/policy_ab')
BUNDLE_SHA256 = '__BUNDLE_SHA256__'


def main():
    bundles = list(Path('/kaggle/input').rglob('policy_ab_bundle.zip.bin'))
    if len(bundles) != 1 or hashlib.sha256(bundles[0].read_bytes()).hexdigest() != BUNDLE_SHA256:
        raise RuntimeError('Missing/changed policy A/B bundle')
    PROJECT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(bundles[0]) as archive:
        if any(PROJECT.resolve() not in (PROJECT / name).resolve().parents for name in archive.namelist()):
            raise RuntimeError('Unsafe bundle path')
        archive.extractall(PROJECT)
    settings = json.loads((PROJECT / 'settings.json').read_text(encoding='utf-8'))
    candidates = [p.parent for p in Path('/kaggle/input').rglob('adapter_manifest.json')
                  if hashlib.sha256(p.read_bytes()).hexdigest() == settings['adapter_manifest_sha256']]
    if len(candidates) != 1:
        raise RuntimeError('Missing/ambiguous sealed v1 adapter')
    os.environ.update(HF_HOME='/tmp/exp_a_huggingface', TOKENIZERS_PARALLELISM='false',
                      PYTHONDONTWRITEBYTECODE='1', USE_TF='0')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', 'transformers==4.57.6',
        'accelerate==1.15.0', 'bitsandbytes==0.50.2', 'peft==0.18.1'], check=True)
    sys.path.insert(0, str(PROJECT / 'data/exp_a/finetuning/policy_ab'))
    import runner
    runner.run(PROJECT, settings, candidates[0])


if __name__ == '__main__':
    main()
