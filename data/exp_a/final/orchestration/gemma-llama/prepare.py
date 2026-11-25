"""Archive Qwen results and build an immutable input bundle; never submit a kernel."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
FINAL = HERE.parents[1]
REPO = FINAL.parents[2]


def raw(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)+'\n').encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Frozen trainer patch anchor differs: '+old)
    return source.replace(old, new)


def qwen_files():
    directory = FINAL/'results/Qwen8B'
    return {p.relative_to(directory).as_posix(): p.read_bytes()
            for p in directory.rglob('*') if p.is_file()}


def build(destination):
    destination = Path(destination)
    spec = importlib.util.spec_from_file_location('shared_final_package', FINAL/'package.py')
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    files, original = shared.source_files()
    files['frozen_runtime.py'] = files['runtime.py']
    files['runtime.py'] = (HERE/'model_runtime.py').read_bytes()
    files['compat.py'] = (HERE/'compat.py').read_bytes()
    trainer = files['train.py'].decode('utf-8')
    trainer = replace_once(trainer, 'token=False, trust_remote_code=False', 'token=True, trust_remote_code=False')
    trainer = replace_once(trainer,
        "    attention = install_attention(root) if config['model'] == BASE_MODEL else 'sdpa'",
        "    from compat import attention_for\n    attention = attention_for(config['model'], lambda: install_attention(root))")
    files['train.py'] = trainer.encode('utf-8')
    files['settings.template.json'] = raw(original)
    payload = {'common/'+name: data for name,data in files.items()}
    payload['batch.py'] = (HERE/'batch.py').read_bytes()
    payload['config.json'] = (FINAL/'configs/models.json').read_bytes()
    payload.update({'Qwen8B/'+name:data for name,data in qwen_files().items()})
    payload['bundle_manifest.json'] = raw(dict(files={name:sha(data) for name,data in payload.items()}))
    folder = destination/'input-dataset'
    folder.mkdir(parents=True, exist_ok=True)
    bundle = folder/'llama_gemma_bundle.zip.bin'
    # A deterministic archive makes rebuilds reviewable and safe to resume.
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(payload.items()):
            info = zipfile.ZipInfo(name, (2026,10,30,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    fingerprint = sha(bundle.read_bytes())
    config = json.loads(payload['config.json'])
    kernel = destination/'kernel'
    kernel.mkdir(parents=True, exist_ok=True)
    code = (HERE/'bootstrap.py').read_text(encoding='utf-8').replace('__BUNDLE_SHA256__', fingerprint)
    (kernel/'run_llama_gemma.py').write_text(code, encoding='utf-8')
    dataset_id = 'htnkhi/exp-a-llama-gemma-gold400-inputs'
    (folder/'dataset-metadata.json').write_bytes(raw(dict(id=dataset_id, title='Exp A Llama Gemma Gold400 Inputs',
        is_private=True, licenses=[dict(name='other')])))
    (kernel/'kernel-metadata.json').write_bytes(raw(dict(id='htnkhi/exp-a-llama-gemma-gold400',
        title='Exp A Llama Gemma Gold400', code_file='run_llama_gemma.py', language='python',
        kernel_type='script', is_private=True, enable_gpu=True, enable_internet=True,
        machine_shape='NvidiaTeslaT4', dataset_sources=[dataset_id], kernel_sources=[],
        model_sources=[], competition_sources=[])))
    result = dict(bundle_sha256=fingerprint, models=[m['key'] for m in config['models']],
                  source_bundle_sha256=sha((FINAL/'source_bundle.zip.bin').read_bytes()), files=len(payload))
    (destination/'build_manifest.json').write_bytes(raw(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'release_20261030_v1')
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2))
