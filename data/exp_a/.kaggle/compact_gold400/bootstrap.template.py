"""Private accepted-gold400 bootstrap; labels remain evaluation-only."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path,PurePosixPath
import stat
import subprocess
import sys
import zipfile
SETTINGS_B64='__SETTINGS_B64__'
BUNDLE_SHA256='__BUNDLE_SHA256__'
INPUT_SETTINGS_B64='__INPUT_SETTINGS_B64__'
OVERLAY_B64='__OVERLAY_B64__'
PROJECT=Path('/kaggle/working/exp_a_compact_gold400')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def unpack(bundle,root,settings):
    expected=set(settings['files'])|{'settings.json'}
    with zipfile.ZipFile(bundle) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or set(names)!=expected:raise ValueError('Bundle file inventory differs')
        for info in z.infolist():
            part=PurePosixPath(info.filename)
            if part.is_absolute() or '..' in part.parts or '\\' in info.filename or stat.S_ISLNK(info.external_attr>>16):raise ValueError('Unsafe bundle path')
            raw=z.read(info)
            if info.filename=='settings.json':
                if json.loads(raw)!=settings:raise ValueError('Bundle settings differ')
            elif hashlib.sha256(raw).hexdigest()!=settings['files'][info.filename]:raise ValueError('Bundle member checksum differs')
        if (root/'settings.json').exists() and json.loads((root/'settings.json').read_text())!=settings:raise ValueError('Existing project has different settings')
        for name in names:
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(name))
def prepare(bundle,root,settings,input_settings,overlay):
    allowed={'runner.py','data/exp_a/prompts/extraction_compact_v1.md','baseline/experiment_summary.json'}
    if set(overlay)!=allowed:raise ValueError('Unexpected code overlay inventory')
    for name,encoded in overlay.items():
        if hashlib.sha256(base64.b64decode(encoded)).hexdigest()!=settings['files'][name]:raise ValueError('Overlay checksum differs')
    if (root/'settings.json').exists():
        if json.loads((root/'settings.json').read_text(encoding='utf-8'))!=settings:raise ValueError('Existing project settings differ')
        return
    unpack(bundle,root,input_settings)
    for name,encoded in overlay.items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(base64.b64decode(encoded))
    (root/'settings.json').write_text(json.dumps(settings,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for name,checksum in settings['files'].items():
        if sha(root/name)!=checksum:raise ValueError('Prepared file checksum differs')

def main():
    settings=json.loads(base64.b64decode(SETTINGS_B64))
    candidates=[p for p in Path('/kaggle/input').rglob('gold400_bundle.zip.bin') if sha(p)==BUNDLE_SHA256]
    if len(candidates)!=1:raise ValueError('Frozen human-gold400 input bundle missing/ambiguous')
    prepare(candidates[0],PROJECT,settings,json.loads(base64.b64decode(INPUT_SETTINGS_B64)),json.loads(base64.b64decode(OVERLAY_B64)))
    print('INPUTS VERIFIED: all400 sources and accepted gold locked; generation uses source only',flush=True)
    os.environ.update(HF_HOME='/tmp/exp_a_gold400_hf',TOKENIZERS_PARALLELISM='false',PYTHONDONTWRITEBYTECODE='1',USE_TF='0')
    subprocess.run([sys.executable,'-m','pip','install','--quiet','transformers==4.57.6','accelerate==1.15.0','bitsandbytes==0.50.2'],check=True)
    s=importlib.util.spec_from_file_location('compact_gold400_runner',PROJECT/'runner.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    shared,_,_,_=m.verify(PROJECT,settings)
    from huggingface_hub import hf_hub_download
    directory=PROJECT/shared.evaluator.MODEL_DIRECTORY
    download=json.loads((directory/'download_manifest.json').read_text(encoding='utf-8'))
    for name,info in download['files'].items():
        path=directory/name
        if not path.is_file():path=Path(hf_hub_download(shared.evaluator.MODEL_ID,filename=name,revision=shared.evaluator.MODEL_REVISION,local_dir=str(directory),token=False))
        if sha(path)!=info['sha256']:raise ValueError('Embedding model checksum differs')
    print('BOOTSTRAP COMPLETE: Compact-patch, 2 shards x200, up to3 calls per paper, no training',flush=True)
    m.run(PROJECT,settings)
if __name__=='__main__':main()
