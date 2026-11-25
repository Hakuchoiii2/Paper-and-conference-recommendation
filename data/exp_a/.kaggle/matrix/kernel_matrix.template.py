"""One private Kaggle kernel: paired facet extraction and frozen semantic scoring."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

BUNDLE_SHA256 = '__BUNDLE_SHA256__'
PROJECT = Path('/kaggle/working/exp_a_matrix')


def main():
    bundles = list(Path('/kaggle/input').rglob('matrix_bundle.zip.bin'))
    if len(bundles) != 1 or hashlib.sha256(bundles[0].read_bytes()).hexdigest() != BUNDLE_SHA256:
        raise RuntimeError('Missing, ambiguous or changed experiment bundle')
    PROJECT.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(bundles[0]) as archive:
        for member in archive.infolist():
            if PROJECT.resolve() not in (PROJECT/member.filename).resolve().parents or member.filename.startswith('/'):
                raise RuntimeError('Unsafe bundle path')
        archive.extractall(PROJECT)
    settings = json.loads((PROJECT/'matrix_settings.json').read_text(encoding='utf-8'))
    for name,expected in settings['files'].items():
        if hashlib.sha256((PROJECT/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'Changed input: {name}')
    os.environ.update(HF_HOME='/tmp/exp_a_huggingface',TOKENIZERS_PARALLELISM='false',
        PYTHONDONTWRITEBYTECODE='1',USE_TF='0')
    subprocess.run([sys.executable,'-m','pip','install','--quiet','transformers==4.57.6',
        'accelerate==1.15.0','bitsandbytes==0.50.2'],check=True)
    sys.path.insert(0,str(PROJECT/'data/exp_a/.kaggle/matrix'))
    import matrix
    started = time.monotonic()
    # Prepare the pinned evaluator without sending reference labels to an extraction worker.
    from huggingface_hub import hf_hub_download
    directory = PROJECT/matrix.evaluator.MODEL_DIRECTORY
    download = json.loads((directory/'download_manifest.json').read_text(encoding='utf-8'))
    for name,info in download['files'].items():
        path = directory/name
        if not path.is_file():
            path = Path(hf_hub_download(matrix.evaluator.MODEL_ID,filename=name,
                revision=matrix.evaluator.MODEL_REVISION,local_dir=str(directory),token=False))
        if hashlib.sha256(path.read_bytes()).hexdigest() != info['sha256']:
            raise RuntimeError(f'Embedding model checksum differs: {name}')
    matrix.run(PROJECT)
    summary = json.loads((PROJECT/'results/experiment_summary.json').read_text(encoding='utf-8'))
    summary['wall_seconds'] = round(time.monotonic()-started,2)
    (Path('/kaggle/working')/'experiment_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()
