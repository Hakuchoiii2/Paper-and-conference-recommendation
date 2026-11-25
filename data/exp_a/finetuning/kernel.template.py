"""Private Kaggle QLoRA training and paired 100-paper evaluation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

BUNDLE_SHA256 = '__BUNDLE_SHA256__'
PROJECT = Path('/kaggle/working/exp_a_qlora')


def main():
    bundles=list(Path('/kaggle/input').rglob('qlora_bundle.zip.bin'))
    if len(bundles)!=1 or hashlib.sha256(bundles[0].read_bytes()).hexdigest()!=BUNDLE_SHA256:
        raise RuntimeError('Missing, ambiguous or changed QLoRA input bundle')
    PROJECT.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(bundles[0]) as archive:
        for member in archive.infolist():
            if PROJECT.resolve() not in (PROJECT/member.filename).resolve().parents or member.filename.startswith('/'):
                raise RuntimeError('Unsafe bundle path')
        archive.extractall(PROJECT)
    settings=json.loads((PROJECT/'qlora_settings.json').read_text(encoding='utf-8'))
    for name,expected in settings['files'].items():
        if hashlib.sha256((PROJECT/name).read_bytes()).hexdigest()!=expected:
            raise RuntimeError('Changed input: '+name)
    os.environ.update(HF_HOME='/tmp/exp_a_huggingface',TOKENIZERS_PARALLELISM='false',
        PYTHONDONTWRITEBYTECODE='1',USE_TF='0')
    subprocess.run([sys.executable,'-m','pip','install','--quiet','transformers==4.57.6',
        'accelerate==1.15.0','bitsandbytes==0.50.2','peft==0.18.1'],check=True)
    sys.path.insert(0,str(PROJECT/'data/exp_a/finetuning'))
    import experiment
    experiment.run(PROJECT,settings)
    summary=json.loads((PROJECT/'results/experiment_summary.json').read_text(encoding='utf-8'))
    (Path('/kaggle/working')/'experiment_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
