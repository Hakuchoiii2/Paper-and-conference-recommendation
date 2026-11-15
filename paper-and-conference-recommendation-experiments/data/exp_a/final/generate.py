"""Official Qwen3-8B + gold400 QLoRA + three-call V-recall generation."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[3]
FACETS = ('problem', 'task', 'method', 'dataset', 'contribution')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def read_rows(path):
    return [json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines() if s.strip()]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def verify_files(root, files):
    root = Path(root).resolve()
    for name, expected in files.items():
        path = (root/name).resolve()
        require(path.is_relative_to(root) and path.is_file() and sha(path) == expected, 'File checksum differs: '+name)


def verify(repo=REPO):
    manifest = read(repo/'data/exp_a/final/manifest.json')
    verify_files(repo, manifest['files'])
    config = read(repo/'data/exp_a/final/config.json')
    adapter = repo/config['adapter']
    metadata = read(adapter/'training_metadata.json')
    verify_files(adapter, metadata['files'])
    require(metadata['best_checkpoint'] == config['selected_checkpoint'], 'Wrong selected adapter')
    require(metadata['base_model'] == config['base_model'] and metadata['base_revision'] == config['revision'], 'Wrong base model')
    print(f"Verified {len(manifest['files'])} official files; {config['selected_checkpoint']}", flush=True)
    return config


def read_papers(path):
    result, seen = [], set()
    for row in read_rows(path):
        pid = row.get('paper_id')
        require(isinstance(pid, str) and re.fullmatch(r'P\d{6}', pid), 'Invalid paper_id')
        require(pid not in seen, 'Duplicate paper_id: '+pid)
        require(all(isinstance(row.get(k), str) and row[k].strip() for k in ('title', 'abstract')), 'Empty source: '+pid)
        seen.add(pid)
        result.append({k:row[k] for k in ('paper_id','title','abstract')})
    require(bool(result), 'Empty corpus')
    return result


def load_pipeline(root):
    spec = importlib.util.spec_from_file_location('official_frozen_policy', root/'gold_policy.py')
    policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy)
    return policy, policy.load_shared(root)


def export(shared, output, papers, records, signature, config):
    shared.base.write_jsonl(output/'facets_silver.jsonl', [r['facets'] for r in records])
    metadata = []
    catalog = {p['paper_id']:p for p in papers}
    for r in records:
        p = catalog[r['paper_id']]
        options = shared.base.evidence_options(p)
        selection = r['audit']['evidence_selection']
        evidence = dict(paper_id=r['paper_id'], **{f:[dict(concept=x['concept'], **options[x['evidence_id']]) for x in selection[f]] for f in FACETS})
        metadata.append(dict(r['audit'], paper_id=r['paper_id'], tier='silver', dataset_kind='real',
            annotator_type='qwen_local', review_status='unreviewed', training_performed=True,
            checkpoint=config['selected_checkpoint'], evidence=evidence, provenance_signature=signature))
    shared.base.write_jsonl(output/'annotation_metadata.jsonl', metadata)
    done = {r['paper_id'] for r in records}
    manifest = dict(contract_version='1.0', dataset_kind='real', tier='silver',
        status='complete' if len(done) == len(papers) else 'partial', count=len(done), corpus_count=len(papers),
        missing_ids=[p['paper_id'] for p in papers if p['paper_id'] not in done],
        provenance=dict(signature=signature, architecture=config['version'], release_signature=config['release_signature'],
                        model=config['base_model'], revision=config['revision'], selected_checkpoint=config['selected_checkpoint']),
        coverage={f:sum(bool(r['facets'][f]) for r in records) for f in FACETS},
        fallback_annotations={r['paper_id']:r['audit']['validation_errors'] for r in records if r['fallback_used']},
        total_input_tokens=sum(r['usage']['input_tokens'] for r in records),
        total_output_tokens=sum(r['usage']['output_tokens'] for r in records),
        files={n:sha(output/n) for n in ('facets_silver.jsonl','annotation_metadata.jsonl')})
    shared.base.write_json(output/'manifest.json', manifest)
    return manifest


def generate(papers, output, config, repo=REPO, *, factory=None):
    """Reuse signed records; only the decoder is replaceable in CPU integration tests."""
    output = Path(output).resolve()
    policy, shared = load_pipeline(repo/config['runtime'])
    adapter = (repo/config['adapter']).resolve()
    generation = dict(config['generation'], adapter_path=str(adapter))
    instruction = '\n\n'.join((repo/config[k]).read_text(encoding='utf-8') for k in ('guideline','prompt'))
    require(hashlib.sha256(instruction.encode()).hexdigest() == config['instruction_sha256'], 'Instruction checksum differs')
    adapter_hash = sha(adapter/'adapter_model.safetensors')
    signature = digest(dict(config=config, papers=papers, adapter_sha256=adapter_hash))
    if output.exists() and any(output.iterdir()):
        require((output/'run.json').is_file() and read(output/'run.json')['signature'] == signature, 'Run signature differs; use a new output directory')
    output.mkdir(parents=True, exist_ok=True)
    records = []
    with shared.base.single_run(output):
        cached = {}
        for paper in papers:
            path = output/'records'/f'{paper["paper_id"]}.json'
            if path.exists():
                record = shared.load_record(path, signature)
                require(record['paper_id'] == paper['paper_id'] and record['source_sha256'] == digest(paper), 'Source identity differs')
                cached[paper['paper_id']] = record
        shared.base.write_json(output/'run.json', dict(signature=signature, architecture=config['version']))
        decoder, runtime = None, None
        for paper in papers:
            path = output/'records'/f'{paper["paper_id"]}.json'
            if paper['paper_id'] in cached:
                record = cached[paper['paper_id']]
            else:
                if decoder is None:
                    decoder, runtime = (factory or (lambda s,c:s.load_generator(c)))(shared, generation)
                    runtime.update(adapter_enabled=True, adapter_sha256=adapter_hash)
                record = policy.annotate_fresh(shared, paper, instruction, generation, runtime, decoder, output, signature=signature)
                record.update(training_performed=True, arm='gold400-QLoRA-V-recall', adapter_enabled=True, adapter_sha256=adapter_hash)
                shared.save_record(path, record, signature)
            records.append(record)
            result = export(shared, output, papers, records, signature, config)
            print(f'{len(records)}/{len(papers)}: {paper["paper_id"]}; fallback={record["fallback_used"]}', flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify frozen files and adapter without loading a GPU model')
    parser.add_argument('--input', type=Path, help='JSONL papers; default: canonical corpus')
    parser.add_argument('--output', type=Path, help='New or compatible resumable output directory')
    parser.add_argument('--limit', type=int, help='Generate the first N papers into a separate output directory')
    args = parser.parse_args()
    config = verify()
    if args.check:
        return
    source = args.input or REPO/config['source_corpus']
    papers = read_papers(source)
    if args.limit is not None:
        require(args.limit > 0, '--limit must be positive')
        require(args.output is not None, 'Use --output for a limited run')
        papers = papers[:args.limit]
    output = (args.output or REPO/config['output']).resolve()
    protected = [REPO/config['runtime'], REPO/config['adapter'], REPO/'data/exp_a/final/reference', REPO/'data/exp_a/final/prompts']
    require(not any(output.is_relative_to(p.resolve()) or p.resolve().is_relative_to(output) for p in protected), 'Output overlaps frozen official files')
    os.environ.setdefault('USE_TF','0')
    os.environ.setdefault('TOKENIZERS_PARALLELISM','false')
    generate(papers, output, config)


if __name__ == '__main__':
    main()
