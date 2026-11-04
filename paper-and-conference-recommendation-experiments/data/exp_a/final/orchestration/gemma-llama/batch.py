"""Run and seal Llama before starting Gemma; no concurrent model training."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ORDER = ('Llama8B', 'Gemma9B')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    temporary.replace(path)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            result.update(block)
    return result.hexdigest()


def output_hashes(root):
    files = [root/'settings.json']
    for name in ('adapter', 'results'):
        files.extend(p for p in (root/name).rglob('*') if p.is_file())
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(files)}


def verify_complete(root):
    marker = read(root/'complete.json')
    if marker['signature'] != read(root/'settings.json')['signature']:
        raise ValueError('Completed model signature differs')
    if not marker.get('files'):
        raise ValueError('Completed model has no output checksums')
    for name, expected in marker['files'].items():
        path = (root/name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or sha(path) != expected:
            raise ValueError('Completed output checksum differs: '+name)


def execute_model(root):
    env = dict(os.environ, WORLD_SIZE='1', TOKENIZERS_PARALLELISM='false')
    # The coordinator sees both GPUs; runtime.py isolates training/worker subprocesses.
    subprocess.run([sys.executable, '-B', str(root/'runtime.py')], cwd=root, env=env, check=True)


def publish_model(root):
    hashes = output_hashes(root)
    marker = dict(signature=read(root/'settings.json')['signature'], files=hashes)
    destination = root.parent/(root.name+'_completed.zip')
    temporary = destination.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in hashes:
            archive.write(root/name, root.name+'/'+name)
        archive.writestr(root.name+'/complete.json', json.dumps(marker, indent=2, ensure_ascii=False)+'\n')
    temporary.replace(destination)
    write(root/'complete.json', marker)
    verify_complete(root)
    print(f'SAVED {root.name}: {destination.name}', flush=True)


def run_models(root, *, execute=execute_model, publish=publish_model):
    root = Path(root)
    for name in ORDER:
        model_root = root/name
        if (model_root/'complete.json').is_file():
            verify_complete(model_root)
            if not (root/(name+'_completed.zip')).is_file():
                publish(model_root)
            print('RESTORED '+name, flush=True)
            continue
        write(root/'batch_status.json', dict(status='running', model=name))
        execute(model_root)
        summary = read(model_root/'results/experiment_summary.json')
        if summary.get('status') != 'complete' or summary.get('signature') != read(model_root/'settings.json')['signature']:
            raise ValueError('Model did not finish with the expected signature: '+name)
        publish(model_root)
    write(root/'batch_status.json', dict(status='complete', models=list(ORDER)))


if __name__ == '__main__':
    run_models(Path(__file__).resolve().parent)
