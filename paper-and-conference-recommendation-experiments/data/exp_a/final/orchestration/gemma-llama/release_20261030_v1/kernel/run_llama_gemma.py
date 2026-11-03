"""Kaggle: authenticated preflight, then Llama8B -> Gemma9B; two inference GPUs."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import zipfile

BUNDLE_SHA256 = '6259ddb570c4c208d0aeb2e8a17d5ac984701f391f65f08964145bd6a710b510'
PROJECT = Path('/kaggle/working/exp_a_compare')

# Optional: fill this only in your private Kaggle editor, then Save & Run All.
HF_TOKEN = ""


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temporary.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def extract(bundle, root, expected):
    if sha(bundle) != expected:
        raise ValueError('Bundle checksum differs')
    root = Path(root).resolve()
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate bundle members')
        for info in archive.infolist():
            name = info.filename
            if PurePosixPath(name).is_absolute() or any(p in ('', '.', '..') for p in name.split('/')) or '\\' in name or ':' in name or stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError('Unsafe bundle path')
            if not (root/name).resolve().is_relative_to(root):
                raise ValueError('Escaping bundle path')
        manifest = json.loads(archive.read('bundle_manifest.json'))
        if set(names) != set(manifest['files'])|{'bundle_manifest.json'}:
            raise ValueError('Bundle inventory differs')
        for name, expected_hash in manifest['files'].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected_hash:
                raise ValueError('Changed bundle input: '+name)
        # Check every existing input before writing any missing one. Outputs are untouched.
        for name in names:
            path = root/name
            if path.exists() and sha(path) != hashlib.sha256(archive.read(name)).hexdigest():
                raise ValueError('Changed existing input: '+name)
        for name in names:
            path = root/name
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(name))


def prepare_model(root, item):
    if item['key'] not in ('Llama8B', 'Gemma9B') or not re.fullmatch('[0-9a-f]{40}', item['revision']):
        raise ValueError('Expected supported model key and pinned revision SHA')
    common = root/'common'
    destination = root/item['key']
    settings = read(common/'settings.template.json')
    settings.update(version='exp_a_model_comparison_v1', model_key=item['key'])
    for section in ('training', 'generation'):
        settings[section].update(model=item['model'], revision=item['revision'])
    settings['generation']['cache_dir'] = '/tmp/exp_a_huggingface'
    inputs = set(settings['files'])|{'compat.py', 'frozen_runtime.py'}
    settings['files'] = {name:sha(common/name) for name in sorted(inputs)}
    settings.pop('signature', None)
    settings['signature'] = digest(settings)
    if (destination/'settings.json').is_file() and read(destination/'settings.json') != settings:
        raise ValueError('Resume model identity/settings differ')
    for source in common.rglob('*'):
        if not source.is_file() or source.name == 'settings.template.json' or '__pycache__' in source.parts:
            continue
        target = destination/source.relative_to(common)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if sha(target) != sha(source):
                raise ValueError('Changed model input: '+str(target.relative_to(destination)))
        elif source.name == 'model.safetensors':
            # The pinned evaluator weights are shared on disk, not duplicated per model.
            try:
                os.link(source, target)
            except OSError:
                shutil.copyfile(source, target)
        else:
            shutil.copyfile(source, target)
    write(destination/'settings.json', settings)
    return destination


def hf_token():
    token = HF_TOKEN.strip() or os.environ.get('HF_TOKEN')
    if not token:
        try:
            from kaggle_secrets import UserSecretsClient
            token = UserSecretsClient().get_secret('HF_TOKEN')
        except Exception:
            raise RuntimeError('Fill HF_TOKEN at the top of this private kernel, or enable Kaggle secret HF_TOKEN; the account must have access to Llama3.1 and Gemma2.') from None
    if not token:
        raise RuntimeError('HF_TOKEN is empty')
    os.environ['HF_TOKEN'] = token
    return token


def preflight(root, token):
    from huggingface_hub import HfApi, hf_hub_url, get_hf_file_metadata
    from transformers import AutoTokenizer
    config = read(root/'config.json')
    lock = root/'model_revisions.json'
    if lock.is_file():
        resolved = read(lock)
        if resolved['config_sha256'] != sha(root/'config.json'):
            raise ValueError('Revision lock belongs to different config')
        models = resolved['models']
    else:
        models = []
        for item in config['models']:
            info = HfApi().model_info(item['model'], revision=item['revision'] or 'main', token=token)
            models.append(dict(item, revision=info.sha))
        write(lock, dict(config_sha256=sha(root/'config.json'), models=models))
    if [m['key'] for m in models] != ['Llama8B', 'Gemma9B']:
        raise ValueError('Changed model order')
    for item, requested in zip(models, config['models']):
        if item['model'] != requested['model'] or (requested['revision'] and item['revision'] != requested['revision']):
            raise ValueError('Model revision lock identity differs')
        # HEAD one actual shard so gated access is tested, without downloading weights.
        info = HfApi().model_info(item['model'], revision=item['revision'], token=token)
        weights = next((s.rfilename for s in info.siblings if s.rfilename.endswith('.safetensors')), None)
        if weights is None:
            raise ValueError('No safetensors weights: '+item['model'])
        get_hf_file_metadata(hf_hub_url(item['model'], weights, revision=item['revision']), token=token)
        model_root = prepare_model(root, item)
        spec = importlib.util.spec_from_file_location('preflight_compat', model_root/'compat.py')
        compat = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(compat)
        tokenizer = AutoTokenizer.from_pretrained(item['model'], revision=item['revision'], token=token,
            cache_dir='/tmp/exp_a_huggingface', trust_remote_code=False)
        lengths = {}
        for split in ('train', 'valid'):
            examples = [json.loads(line) for line in (model_root/f'training_data/{split}.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
            encoded = [compat.encode_example(tokenizer, row, 4096) for row in examples]
            maximum = max(sum(v != -100 for v in row['labels']) for row in encoded)
            if maximum > 2048:
                raise ValueError(f'{item["key"]}: supervised answer exceeds generation budget2048; inspect before training')
            lengths[split] = dict(count=len(encoded), max_sequence=max(len(row['input_ids']) for row in encoded), max_completion=maximum)
        write(model_root/'tokenizer_preflight.json', dict(model=item, lengths=lengths,
              tokenizer_class=type(tokenizer).__name__, chat_template_sha256=digest(tokenizer.chat_template)))
        print(f'PREFLIGHT {item["key"]}: {item["revision"]}; tokenizer and gated access OK', flush=True)


def embedding(root):
    from huggingface_hub import hf_hub_download
    manifests = list((root/'common/data/exp_a/evaluation/embedding_probe/.model_cache').glob('*/download_manifest.json'))
    if len(manifests) != 1:
        raise ValueError('Missing pinned evaluator manifest')
    manifest = read(manifests[0])
    for name, expected in manifest['files'].items():
        path = manifests[0].parent/name
        if not path.is_file():
            hf_hub_download(manifest['model'], filename=name, revision=manifest['revision'],
                            local_dir=str(manifests[0].parent), token=False)
        if sha(path) != expected['sha256']:
            raise ValueError('Evaluator checksum differs: '+name)


def main():
    candidates = list(Path('/kaggle/input').rglob('llama_gemma_bundle.zip.bin'))
    if len(candidates) != 1:
        raise ValueError('Attach exactly one Llama/Gemma input bundle')
    extract(candidates[0], PROJECT, BUNDLE_SHA256)
    os.environ.update(HF_HOME='/tmp/exp_a_huggingface', TOKENIZERS_PARALLELISM='false',
        PYTHONDONTWRITEBYTECODE='1', USE_TF='0', WORLD_SIZE='1')
    token = hf_token()
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', 'transformers==4.57.6',
        'accelerate==1.15.0', 'bitsandbytes==0.50.2', 'peft==0.18.1', 'sentencepiece==0.2.1'], check=True)
    import torch
    if torch.cuda.device_count() != 2:
        raise RuntimeError('Select GPU T4 x2; exactly two CUDA GPUs are required')
    preflight(PROJECT, token)
    embedding(PROJECT)
    # Add shared evaluator weights to each project after the access/tokenizer checks.
    for item in read(PROJECT/'model_revisions.json')['models']:
        prepare_model(PROJECT, item)
    subprocess.run([sys.executable, '-B', str(PROJECT/'batch.py')], cwd=PROJECT, check=True)


if __name__ == '__main__':
    main()
