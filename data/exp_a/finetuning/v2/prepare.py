"""Stage the decoding diagnostic and a source-only review queue; never launch training."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FINETUNING = HERE.parent
LEGACY = FINETUNING/'policy_ab/build/diagnostics/kaggle_probe_2026-10-18'


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build(destination=None):
    destination = Path(destination or HERE/'build')
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('Refusing to overwrite a nonempty v2 staging directory')
    protected = read(FINETUNING/'label_revision_v2/pilot40/protected_v1_sha256.json')
    for name, expected in protected.items():
        if sha256(ROOT/name) != expected:
            raise ValueError('Protected v1 file changed: ' + name)
    frozen = read(FINETUNING/'data/manifest.json')
    config = read(ROOT/'data/exp_a/config_v3_pilot50.json')
    corpus_path = ROOT/config['corpus']
    if sha256(corpus_path) != frozen['corpus_sha256']:
        raise ValueError('Corpus differs from the frozen v1 split')
    papers = {p['paper_id']: p for p in map(json.loads, corpus_path.read_text(encoding='utf-8').splitlines())}
    train, dev, test = (set(frozen['split_ids'][split]) for split in ('train', 'dev', 'test'))
    if train & dev or train & test or dev & test or (len(train),len(dev),len(test)) != (467,100,100):
        raise ValueError('Frozen split is invalid')
    pilot = FINETUNING/'label_revision_v2/pilot40'
    annotations = [json.loads(line) for line in (pilot/'adjudicated_annotations.jsonl').read_text(encoding='utf-8').splitlines()]
    if len({r['paper_id'] for r in annotations}) != 40 or not {r['paper_id'] for r in annotations} <= train | dev:
        raise ValueError('Candidate pilot overlaps test or differs from its expected cohort')
    # Import the existing evidence splitter, without opening v1 assistant targets.
    import importlib.util
    spec = importlib.util.spec_from_file_location('v2_prepare_schema', FINETUNING/'label_revision_v2/schema.py')
    schema = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(schema)
    for row in annotations:
        schema.ground_response(row, papers[row['paper_id']])
    files = {'generation.py': (HERE/'generation.py').read_bytes(),
             'probe.py': (HERE/'probe.py').read_bytes(), 'legacy_probe.py': (LEGACY/'probe.py').read_bytes()}
    for name, payload in files.items():
        compile(payload, name, 'exec')
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for name, payload in sorted(files.items()):
            entry = zipfile.ZipInfo(name, date_time=(2026,10,18,0,0,0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, payload)
    payload = stream.getvalue()
    encoded = base64.b64encode(payload).decode('ascii')
    code = """import base64, hashlib, io, os, pathlib, subprocess, sys, zipfile
payload = base64.b64decode('__PAYLOAD__')
assert hashlib.sha256(payload).hexdigest() == '__DIGEST__'
directory = pathlib.Path('/kaggle/working/exp_a_v2_probe_code')
directory.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(io.BytesIO(payload)) as archive:
    assert set(archive.namelist()) == {'probe.py','generation.py','legacy_probe.py'}
    archive.extractall(directory)
os.environ.update(PYTHONDONTWRITEBYTECODE='1', TOKENIZERS_PARALLELISM='false', USE_TF='0')
subprocess.run([sys.executable, '-B', str(directory/'probe.py')], check=True)
""".replace('__PAYLOAD__', encoded).replace('__DIGEST__', hashlib.sha256(payload).hexdigest())
    compile(code, 'run_probe.py', 'exec')
    metadata = read(LEGACY/'kernel/kernel-metadata.json')
    metadata.update(id='htnkhi/exp-a-v2-decoding-probe', title='Exp A V2 Decoding Probe')
    destination.mkdir(parents=True, exist_ok=True)
    (destination/'kernel').mkdir()
    (destination/'probe_code.zip').write_bytes(payload)
    (destination/'kernel/run_probe.py').write_text(code, encoding='utf-8')
    (destination/'kernel/kernel-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n', encoding='utf-8')
    with (destination/'train_dev_review_queue.jsonl').open('w', encoding='utf-8', newline='\n') as stream:
        for split, ids in (('train',train), ('dev',dev)):
            for pid in sorted(ids):
                paper = papers[pid]
                stream.write(json.dumps(dict(paper_id=pid, split=split,
                    source={k:paper[k] for k in ('paper_id','title','abstract')},
                    evidence_options={k:v['evidence'] for k,v in schema.base.evidence_options(paper).items()},
                    review_status='source_first_v2_2_review_required'), ensure_ascii=False)+'\n')
    manifest = dict(phase='inference_diagnostic_only', training_ready=False,
        required_train_dev_papers=len(train | dev), candidate_pilot_papers=len(annotations),
        candidate_policy_version='2.2', candidate_schema_version='2.1',
        v1_protected_files_verified=len(protected), protected_v1_sha256=protected,
        probe_code_sha256=sha256(destination/'probe_code.zip'), kernel=metadata['id'],
        kernel_code_sha256=sha256(destination/'kernel/run_probe.py'),
        source_bundle_sha256='38e77ec72990909c9dfe9dae3be4421af4e1c2313adb0d8904a6964399032b35',
        policy_sha256=sha256(FINETUNING/'label_revision_v2/policy_v2_2.md'),
        prompt_sha256=sha256(FINETUNING/'label_revision_v2/prompt_v2_2.md'),
        schema_sha256=sha256(FINETUNING/'label_revision_v2/response_schema.json'),
        frozen_split_sha256=sha256(FINETUNING/'data/manifest.json'),
        review_queue_sha256=sha256(destination/'train_dev_review_queue.jsonl'),
        blockers=['Fresh policy v2.2 confirmation sample is not yet independently accepted',
            '567 train/dev papers need source-grounded v2.2 review; 40 earlier pilot references are provisional',
            'Decoding probe results must be collected and checked before selecting inference settings',
            'User must receive the concrete v1-to-v2 comparison before a v2 training kernel is pushed'],
        limitations=['No v2 adapter trained', 'No new F1 measured',
            'AI references with human review pending', 'Three diagnostic papers are not a held-out benchmark'])
    (destination/'readiness.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path)
    args = parser.parse_args()
    result = build(args.destination)
    print(json.dumps({k:v for k,v in result.items() if k != 'protected_v1_sha256'},ensure_ascii=False,indent=2))
