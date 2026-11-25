"""Package the accepted Qwen8B experiment from shared files in final/."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
FINAL = HERE.parents[1]
ROOT = FINAL.parents[2]
RELEASE = HERE/'history/release_20261028_v5'
KERNEL = 'htnkhi/exp-a-v-recall-gold400-qlora'
DATASET = 'htnkhi/exp-a-v-recall-gold400-qlora-inputs'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


# Retain original split/target validation helpers for historical regression tests.
legacy = load('qwen_original_preparation', HERE/'history/prepare_20261028.py')
split_papers = legacy.split_papers
target = legacy.target


def build(destination):
    destination = Path(destination)
    shared = load('qwen_shared_final_package', FINAL/'package.py')
    files, settings = shared.source_files()
    files['settings.json'] = shared.raw(settings)
    project = destination/'project'
    for name, data in files.items():
        path = project/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    folder = destination/'input-dataset'
    folder.mkdir(parents=True, exist_ok=True)
    bundle = folder/'gold400_qlora_bundle.zip.bin'
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026,10,28,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    fingerprint = hashlib.sha256(bundle.read_bytes()).hexdigest()
    (folder/'dataset-metadata.json').write_bytes(shared.raw(dict(id=DATASET,
        title='Exp A V Recall Gold400 QLoRA Inputs', is_private=True, licenses=[dict(name='other')])))
    kernel = destination/'kernel'
    kernel.mkdir(parents=True, exist_ok=True)
    code = (HERE/'bootstrap.py').read_text(encoding='utf-8').replace('__BUNDLE_SHA256__', fingerprint)
    (kernel/'run_trial.py').write_text(code, encoding='utf-8')
    (kernel/'kernel-metadata.json').write_bytes(shared.raw(dict(id=KERNEL,
        title='Exp A V Recall Gold400 QLoRA', code_file='run_trial.py', language='python',
        kernel_type='script', is_private=True, enable_gpu=True, enable_internet=True,
        machine_shape='NvidiaTeslaT4', dataset_sources=[DATASET], kernel_sources=[],
        competition_sources=[], model_sources=[])))
    result = dict(bundle_sha256=fingerprint, signature=settings['signature'],
                  counts={k:len(v) for k,v in settings['splits'].items()})
    (destination/'build_manifest.json').write_bytes(shared.raw(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'release_20261030_v1')
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2))
