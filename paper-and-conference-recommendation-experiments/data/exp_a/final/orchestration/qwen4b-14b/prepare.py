"""Build a public-Qwen kernel using the existing accepted gold400 Kaggle dataset."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
FINAL = HERE.parents[1]
CONTROL = FINAL/'orchestration/gemma-llama'
DATASET = 'htnkhi/exp-a-llama-gemma-gold400-inputs'
BUNDLE_SHA256 = '6259ddb570c4c208d0aeb2e8a17d5ac984701f391f65f08964145bd6a710b510'


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Controller patch anchor differs: '+old)
    return text.replace(old, new)


def build(destination):
    destination = Path(destination)
    spec = importlib.util.spec_from_file_location('qwen_scales_shared_package', FINAL/'package.py')
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    accepted, _ = shared.source_files()
    bundle = CONTROL/'release_20261030_v1/input-dataset/llama_gemma_bundle.zip.bin'
    if hashlib.sha256(bundle.read_bytes()).hexdigest() != BUNDLE_SHA256:
        raise ValueError('Existing dataset bundle differs from uploaded version')
    with zipfile.ZipFile(bundle) as archive:
        for name,data in accepted.items():
            if name.startswith(('model_inputs/', 'training_data/', 'evaluation_only/')) or name == 'splits.json':
                if archive.read('common/'+name) != data:
                    raise ValueError('Existing dataset split/data differs: '+name)
    trainer = replace_once(accepted['train.py'].decode(),
        "    attention = install_attention(root) if config['model'] == BASE_MODEL else 'sdpa'",
        "    attention = install_attention(root)")
    matrix = replace_once(accepted['data/exp_a/.kaggle/matrix.py'].decode(),
        "    attention = install_attention() if config['model'] == 'Qwen/Qwen3-8B' else 'sdpa'",
        "    attention = install_attention()")
    batch = replace_once((CONTROL/'batch.py').read_text(encoding='utf-8'),
                         "ORDER = ('Llama8B', 'Gemma9B')", "ORDER = ('Qwen4B', 'Qwen14B')")
    files = {
        'runtime.py': (CONTROL/'model_runtime.py').read_bytes(),
        'frozen_runtime.py': accepted['runtime.py'],
        'compat.py': (HERE/'compat.py').read_bytes(),
        'train.py': trainer.encode(),
        'data/exp_a/.kaggle/matrix.py': matrix.encode(),
        'batch.py': batch.encode(),
        'config.json': (FINAL/'configs/qwen4b-14b.json').read_bytes(),
    }
    code = (CONTROL/'bootstrap.py').read_text(encoding='utf-8')
    code = code.replace('__BUNDLE_SHA256__', BUNDLE_SHA256).replace('/kaggle/working/exp_a_compare', '/kaggle/working/exp_a_qwen_scales')
    code = code.replace('("Llama8B", "Gemma9B")', '("Qwen4B", "Qwen14B")')
    code = code.replace("('Llama8B', 'Gemma9B')", "('Qwen4B', 'Qwen14B')")
    code = code.replace("['Llama8B', 'Gemma9B']", "['Qwen4B', 'Qwen14B']")
    start, end = code.index('def hf_token():'), code.index('def preflight(')
    code = code[:start]+code[end:]
    code = code.replace('# Optional: fill this only in your private Kaggle editor, then Save & Run All.\nHF_TOKEN = ""\n', '')
    code = replace_once(code, '    token = hf_token()', '    token = False')
    code = replace_once(code, '    extract(candidates[0], PROJECT, BUNDLE_SHA256)',
                        "    extract(candidates[0], PROJECT/'source', BUNDLE_SHA256)\n    prepare_common(PROJECT)")
    setup = '''def prepare_common(root):
    root = Path(root)
    common = root/'common'
    source = root/'source/common'
    files = {p.relative_to(source).as_posix():p.read_bytes()
             for p in source.rglob('*') if p.is_file()}
    files.update({name:data for name,data in RUNTIME_FILES.items() if name not in ('batch.py','config.json')})
    targets = {common/name:data for name,data in files.items()}
    targets.update({root/name:RUNTIME_FILES[name] for name in ('batch.py','config.json')})
    for path,data in targets.items():
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Changed Qwen run input: '+str(path.relative_to(root)))
    for path,data in targets.items():
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)


'''
    code = replace_once(code, 'def main():', 'RUNTIME_FILES = '+repr(files)+'\n\n\n'+setup+'def main():')
    code = code.replace('Llama8B -> Gemma9B', 'Qwen4B -> Qwen14B').replace('authenticated preflight', 'public preflight')
    code = code.replace('Llama/Gemma input bundle', 'existing gold400 input bundle').replace('tokenizer and gated access OK', 'public tokenizer/access OK')
    compile(code, 'run_qwen_scales.py', 'exec')
    kernel = destination/'kernel'
    kernel.mkdir(parents=True, exist_ok=True)
    (kernel/'run_qwen_scales.py').write_text(code, encoding='utf-8')
    metadata = dict(id='htnkhi/exp-a-qwen4b-14b-gold400', title='Exp A Qwen4B 14B Gold400',
        code_file='run_qwen_scales.py', language='python', kernel_type='script', is_private=True,
        enable_gpu=True, enable_internet=True, machine_shape='NvidiaTeslaT4',
        dataset_sources=[DATASET], kernel_sources=[], model_sources=[], competition_sources=[])
    (kernel/'kernel-metadata.json').write_bytes(shared.raw(metadata))
    report = dict(dataset=DATASET, reused_bundle_sha256=BUNDLE_SHA256,
        code_sha256=shared.sha(code.encode()), models=['Qwen4B','Qwen14B'], new_dataset_uploaded=False,
        runtime_files={name:shared.sha(data) for name,data in files.items()})
    (destination/'build_manifest.json').write_bytes(shared.raw(report))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'release_20261030_v1')
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2))
