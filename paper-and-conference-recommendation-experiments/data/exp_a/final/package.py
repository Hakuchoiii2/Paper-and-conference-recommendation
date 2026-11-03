"""Shared, accepted data/policy payload for both experiment orchestrators."""
import hashlib
import json
from pathlib import Path
import zipfile

FINAL = Path(__file__).resolve().parent


def raw(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False).encode())


def source_files():
    """Verify the historical seal, then read active shared files from final/."""
    with zipfile.ZipFile(FINAL/'source_bundle.zip.bin') as archive:
        files = {name:archive.read(name) for name in archive.namelist()}
    sealed = json.loads(files.pop('settings.json'))
    for name, expected in sealed['files'].items():
        if sha(files[name]) != expected:
            raise ValueError('Frozen source checksum differs: '+name)
    settings = json.loads((FINAL/'reference/settings.json').read_text(encoding='utf-8'))
    for name in tuple(files):
        if name == 'splits.json' or name.startswith(('model_inputs/', 'training_data/', 'evaluation_only/')):
            files[name] = (FINAL/'reference'/name).read_bytes()
    for path in (FINAL/'runtime').rglob('*.py'):
        files[path.relative_to(FINAL/'runtime').as_posix()] = path.read_bytes()
    files['runtime.py'] = (FINAL/'orchestration/Qwen8B/runtime.py').read_bytes()
    for name in tuple(files):
        if name.startswith('data/exp_a/prompts/'):
            files[name] = (FINAL/'prompts'/Path(name).name).read_bytes()
    instruction = '\n\n'.join(files[settings['generation'][key]].decode('utf-8') for key in ('guideline','prompt'))
    if sha(instruction.encode()) != settings['instruction_sha256']:
        raise ValueError('Shared instruction differs from accepted SFT; regenerate data before changing prompts')
    if json.loads(files['splits.json']) != settings['splits']:
        raise ValueError('Shared split differs from accepted settings')
    settings['files'] = {name:sha(data) for name,data in files.items()}
    settings.pop('signature', None)
    settings['signature'] = digest(settings)
    return files, settings
