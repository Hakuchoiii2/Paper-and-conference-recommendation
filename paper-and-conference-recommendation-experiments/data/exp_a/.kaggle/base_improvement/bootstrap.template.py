"""New code only; reuse already-hosted private pilot inputs and R0 outputs."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import zipfile

SETTINGS_B64 = '__SETTINGS_B64__'
RUNNER_B64 = '__RUNNER_B64__'
PROJECT = Path('/kaggle/working/base_v1_r1_r2')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract_original(bundle, destination, settings):
    if sha(bundle) != settings['source_bundle_sha256']:
        raise ValueError('Original input bundle checksum differs')
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('Destination must be empty')
    root=destination.resolve();seen=set()
    with zipfile.ZipFile(bundle) as archive:
        for entry in archive.infolist():
            name=entry.filename;mode=entry.external_attr>>16
            if (not name or name.startswith('/') or '\\' in name or ':' in name
                    or any(p in ('','.','..') for p in name.split('/')) or name in seen
                    or entry.is_dir() or stat.S_ISLNK(mode)
                    or stat.S_IFMT(mode) not in (0,stat.S_IFREG)
                    or root not in (root/PurePosixPath(name)).resolve().parents):
                raise ValueError('Unsafe original archive member')
            seen.add(name)
        expected=dict(settings['old_files'],**{'matrix_settings.json':settings['old_settings_sha256']})
        if seen != set(expected):
            raise ValueError('Original archive inventory differs')
        for name,h in expected.items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=h:
                raise ValueError('Original archive content differs: '+name)
        destination.mkdir(parents=True,exist_ok=True)
        archive.extractall(destination)


def main():
    settings=json.loads(base64.b64decode(SETTINGS_B64))
    inputs=Path('/kaggle/input')
    candidates=[p for p in inputs.rglob('matrix_bundle.zip.bin')
                if sha(p)==settings['source_bundle_sha256']]
    if not candidates:
        raise ValueError('Attach the existing private matrix input dataset')
    extract_original(candidates[0],PROJECT,settings)
    print("PILOT50 INPUT BUNDLE VERIFIED",flush=True)
    runner=base64.b64decode(RUNNER_B64)
    if hashlib.sha256(runner).hexdigest()!=settings['runner_sha256']:
        raise ValueError('New runner checksum differs')
    (PROJECT/'improvement.py').write_bytes(runner)
    (PROJECT/'improvement_settings.json').write_text(json.dumps(settings,indent=2)+'\n',encoding='utf-8')
    candidates=[p for p in inputs.rglob('records') if all((p/(pid+'.json')).is_file() and sha(p/(pid+'.json'))==h
                for pid,h in settings['r0_record_sha256'].items())]
    if not candidates:
        raise ValueError('Attach the frozen input snapshot with the 50 verified 8B R0 records')
    destination=PROJECT/'results/R0/records';destination.mkdir(parents=True)
    for pid in settings['paper_ids']:
        shutil.copyfile(candidates[0]/(pid+'.json'),destination/(pid+'.json'))
    print("R0 RECORDS VERIFIED: 50/50; installing pinned dependencies",flush=True)
    os.environ.update(HF_HOME='/tmp/exp_a_huggingface',TOKENIZERS_PARALLELISM='false',
        PYTHONDONTWRITEBYTECODE='1',USE_TF='0')
    subprocess.run([sys.executable,'-m','pip','install','--quiet','transformers==4.57.6',
        'accelerate==1.15.0','bitsandbytes==0.50.2'],check=True)
    spec=importlib.util.spec_from_file_location('improvement',PROJECT/'improvement.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.verify(PROJECT,settings)
    shared=module.load_shared(PROJECT)
    from huggingface_hub import hf_hub_download
    directory=PROJECT/shared.evaluator.MODEL_DIRECTORY
    download=json.loads((directory/'download_manifest.json').read_text(encoding='utf-8'))
    for name,info in download['files'].items():
        path=directory/name
        if not path.is_file():
            path=Path(hf_hub_download(shared.evaluator.MODEL_ID,filename=name,
                revision=shared.evaluator.MODEL_REVISION,local_dir=str(directory),token=False))
        if sha(path)!=info['sha256']:
            raise ValueError('Embedding checksum differs')
    print("BOOTSTRAP COMPLETE; launching R1/R2 workers",flush=True)
    module.run(PROJECT,settings)


if __name__=='__main__':
    main()
