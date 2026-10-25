"""Private pilot50 experiment. New code only; unchanged dedicated frozen inputs."""
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

SETTINGS_B64='__SETTINGS_B64__'
ASSETS_B64='__ASSETS_B64__'
PROJECT=Path('/kaggle/working/exp_a_r2a')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


__EXTRACT_ORIGINAL__


def main():
    settings=json.loads(base64.b64decode(SETTINGS_B64))
    inputs=Path('/kaggle/input')
    bundles=[p for p in inputs.rglob('matrix_bundle.zip.bin') if sha(p)==settings['source_bundle_sha256']]
    if not bundles:raise ValueError('Required immutable original pilot bundle absent')
    extract_original(bundles[0],PROJECT,settings)
    for name,data in json.loads(base64.b64decode(ASSETS_B64)).items():
        raw=base64.b64decode(data)
        if name not in ('runner.py','repair.py','legacy.py') or hashlib.sha256(raw).hexdigest()!=settings['code_sha256'][name]:
            raise ValueError('Invalid new code asset')
        (PROJECT/name).write_bytes(raw)
    (PROJECT/'improvement_settings.json').write_text(json.dumps(settings,indent=2)+'\n',encoding='utf-8')
    candidates=[p for p in inputs.rglob('records') if all((p/(pid+'.json')).is_file() and
                sha(p/(pid+'.json'))==h for pid,h in settings['r0_record_sha256'].items())]
    if not candidates:raise ValueError('Required 50 immutable cached R0 records absent')
    destination=PROJECT/'results/R0/records';destination.mkdir(parents=True)
    for pid in settings['paper_ids']:shutil.copyfile(candidates[0]/(pid+'.json'),destination/(pid+'.json'))
    print('FROZEN INPUTS VERIFIED: original bundle + 50/50 R0 records',flush=True)
    os.environ.update(HF_HOME='/tmp/exp_a_r2a_hf',TOKENIZERS_PARALLELISM='false',PYTHONDONTWRITEBYTECODE='1',USE_TF='0')
    subprocess.run([sys.executable,'-m','pip','install','--quiet','transformers==4.57.6','accelerate==1.15.0','bitsandbytes==0.50.2'],check=True)
    spec=importlib.util.spec_from_file_location('r2a_runner',PROJECT/'runner.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.verify(PROJECT,settings)
    shared=module.load_shared(PROJECT)
    from huggingface_hub import hf_hub_download
    directory=PROJECT/shared.evaluator.MODEL_DIRECTORY
    download=json.loads((directory/'download_manifest.json').read_text(encoding='utf-8'))
    for name,info in download['files'].items():
        path=directory/name
        if not path.is_file():path=Path(hf_hub_download(shared.evaluator.MODEL_ID,filename=name,
            revision=shared.evaluator.MODEL_REVISION,local_dir=str(directory),token=False))
        if sha(path)!=info['sha256']:raise ValueError('Embedding checksum differs')
    print('BOOTSTRAP COMPLETE: GPU0 R2a-V; GPU1 R2a-P then R2a-full',flush=True)
    module.run(PROJECT,settings)


if __name__=='__main__':main()
