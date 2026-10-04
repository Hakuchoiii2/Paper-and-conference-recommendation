"""Extract source-grounded silver facets with local Qwen3; resume per accepted paper."""
import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
import re
from contextlib import closing, contextmanager
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

from build_corpus import normalize, read_jsonl, write_jsonl
from download_sources import ROOT, sha256, write_json
from validate_all import require, validate_facets, validate_papers

FACET_NAMES = ('problem', 'task', 'method', 'dataset', 'contribution')
GENERATOR_VERSION = '2.1'
LEGACY_GENERATOR_SHA256 = '28ea4be0f55bffcaea5a74579d5b58bb9d14395a936b9f9f1225db21d9c521ab'
MIN_CONCEPT_RETENTION = 0.7
SPARSE_REVIEW_THRESHOLD = 3
EVIDENCE_SCHEMA = dict(type='object', additionalProperties=False,
                       required=['concept', 'evidence_id'], properties={
                           'concept': {'type': 'string'}, 'evidence_id': {'type': 'string'}})
SCHEMA = dict(type='object', additionalProperties=False,
              required=['paper_id', *FACET_NAMES], properties={
                  'paper_id': {'type': 'string'},
                  **{f: {'type': 'array', 'items': EVIDENCE_SCHEMA} for f in FACET_NAMES}})


class AnnotationError(RuntimeError):
    """One paper exhausted its output-validation retries; other papers can proceed."""


@contextmanager
def single_run(directory):
    # OS lock releases even after a crash; a second launch cannot generate duplicate annotations.
    with (directory / '.exp_a_checkpoint.sqlite3.lock').open('a+b') as lock:
        try:
            if os.name == 'nt':
                import msvcrt
                if lock.seek(0, 2) == 0:
                    lock.write(b'0')
                    lock.flush()
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError('Experiment A is already running in this output directory') from None
        yield


def paper_bounds(config, total):
    bounds = config.get('paper_range', [1, None])
    require(isinstance(bounds, list) and len(bounds) == 2,
            'paper_range must be [start, end]; end may be null for the last paper')
    start, end = bounds
    require(type(start) is int and (end is None or type(end) is int),
            'paper_range positions must be integers; end may be null')
    end = total if end is None else end
    require(1 <= start <= end <= total, f'paper_range must satisfy 1 <= start <= end <= {total}')
    return start, end


def inputs(root, config):
    require(isinstance(config['model'], str) and config['model'].strip(), 'model must be nonempty')
    for key in ('max_new_tokens', 'max_attempts', 'top_k'):
        require(type(config[key]) is int and config[key] > 0, f'{key} must be positive')
    require(config['device'] in ('cuda', 'cpu'), 'device must be cuda or cpu')
    require(type(config.get('load_in_4bit', False)) is bool, 'load_in_4bit must be boolean')
    require(not config.get('load_in_4bit') or config['device'] == 'cuda', '4-bit mode requires CUDA')
    require(0 < config['temperature'] <= 2 and 0 < config['top_p'] <= 1, 'invalid sampling parameters')
    require(type(config['seed']) is int and config['seed'] >= 0, 'seed must be nonnegative integer')
    require(isinstance(config['revision'], str) and config['revision'], 'model revision is required')
    paths = {name: root / config[name] for name in ('corpus', 'prompt', 'guideline')}
    papers = sorted(read_jsonl(paths['corpus']), key=lambda row: row['paper_id'])
    validate_papers(papers)
    paper_bounds(config, len(papers))
    stable_config = {k: v for k, v in config.items() if k not in ('max_new_tokens', 'max_attempts')}
    provenance = dict(config=stable_config, generator_version=GENERATOR_VERSION,
                      generator_sha256=sha256(Path(__file__)), schema=SCHEMA,
                      input_hashes={name: sha256(path) for name, path in paths.items()})
    instruction = paths['guideline'].read_text(encoding='utf-8') + '\n\n' + paths['prompt'].read_text(encoding='utf-8')
    return papers, provenance, instruction


def compatible_provenance(previous, current):
    # Only this known validation-policy upgrade may reuse accepted annotations.
    legacy = dict(current, generator_version='2.0', generator_sha256=LEGACY_GENERATOR_SHA256)
    return previous == current or previous == legacy


def source_phrase_coverage(concept, evidence):
    tokens, words = normalize(concept).split(), normalize(evidence).split()
    if not tokens:
        return 0
    best = 0
    for start, word in enumerate(words):
        if word != tokens[0]:
            continue
        end = start
        try:
            for token in tokens[1:]:
                end = words.index(token, end + 1)
        except ValueError:
            continue
        best = max(best, len(tokens) / (end - start + 1))
    return best


def validate_response(value, paper):
    require(isinstance(value, dict) and value.get('paper_id') == paper['paper_id'],
            f"{paper['paper_id']}: wrong paper_id")
    require(set(value) == {'paper_id', *FACET_NAMES}, 'wrong facet keys')
    facets = {'paper_id': paper['paper_id']}
    for facet in FACET_NAMES:
        items = value[facet]
        require(isinstance(items, list), f'{facet}: expected list')
        concepts = []
        for item in items:
            require(isinstance(item, dict) and set(item) == {'concept', 'evidence', 'source'},
                    f'{facet}: wrong evidence keys')
            require(all(isinstance(item[k], str) and item[k].strip() for k in item),
                    f'{facet}: empty concept/evidence/source')
            concept, evidence, source = item['concept'], item['evidence'], item['source']
            require(concept == concept.strip(), f'{facet}: untrimmed concept')
            require(source in ('title', 'abstract') and evidence in paper[source],
                    f"{paper['paper_id']}: {facet} evidence is absent from source text")
            require(source_phrase_coverage(concept, evidence) >= MIN_CONCEPT_RETENTION,
                    f'{facet}: concept must retain at least 70% of its source phrase in the same word order; '
                    f'invalid concept={json.dumps(concept)}; selected evidence={json.dumps(evidence)}. '
                    'Use a less abbreviated phrase from this evidence or choose the correct evidence_id; do not add new words.')
            require(concept.casefold() not in {c.casefold() for c in concepts}, f'{facet}: duplicate concept')
            concepts.append(concept)
        facets[facet] = concepts
    validate_facets([facets], {paper['paper_id']})
    return facets


def parse_generation(text):
    text = text.strip()
    fenced = re.fullmatch(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if fenced:
        text = fenced[1]
    try:
        return json.loads(text)
    except ValueError:
        raise ValueError('Qwen output must contain one JSON object only') from None


def evidence_options(paper):
    return {'T0': dict(source='title', evidence=paper['title']),
            **{f'A{i}': dict(source='abstract', evidence=sentence)
               for i, sentence in enumerate(re.split(r'(?<=[.!?])\s+', paper['abstract']))}}


def ground_response(value, paper):
    require(isinstance(value, dict) and value.get('paper_id') == paper['paper_id'], 'wrong paper_id')
    require(set(value) == {'paper_id', *FACET_NAMES}, 'wrong facet keys')
    options = evidence_options(paper)
    grounded = {'paper_id': value['paper_id']}
    for facet in FACET_NAMES:
        require(isinstance(value[facet], list), f'{facet}: expected list')
        grounded[facet] = []
        for item in value[facet]:
            require(isinstance(item, dict) and set(item) == {'concept', 'evidence_id'}, 'wrong concept/evidence_id keys')
            require(isinstance(item['evidence_id'], str) and item['evidence_id'] in options,
                    f'{facet}: unknown evidence_id')
            grounded[facet].append(dict(concept=item['concept'], **options[item['evidence_id']]))
    validate_response(grounded, paper)
    return grounded


def annotate(paper, instruction, config, runtime, generate_text, failure_path):
    source = dict(paper_id=paper['paper_id'],
                  evidence_options={key: row['evidence'] for key, row in evidence_options(paper).items()})
    policy = ('\nCurrent extraction policy overrides any stricter copying rule above: concepts may omit '
              'up to 30% of the words in their smallest matching source span. Keep retained words in their '
              'original order, add no new words, and preserve meaning. Short exact phrases are allowed. '
              'Consider both the title T0 and all abstract sentences for each facet.')
    messages = [dict(role='system', content=instruction + policy + '\nReturn JSON only. Schema: ' + json.dumps(SCHEMA)),
                dict(role='user', content=json.dumps(source, ensure_ascii=False))]
    sparse_reviewed = False
    error = None
    for attempt in range(config['max_attempts']):
        seed = config['seed'] + int(paper['paper_id'][1:]) * config['max_attempts'] + attempt
        raw, generation = generate_text(messages, seed)
        try:
            selection = parse_generation(raw)
            value = ground_response(selection, paper)
            empty_count = sum(not value[facet] for facet in FACET_NAMES)
            if empty_count >= SPARSE_REVIEW_THRESHOLD and not sparse_reviewed:
                require(attempt + 1 < config['max_attempts'],
                        f'{empty_count}/5 facets are empty; no attempt remains for the required sparse review')
                sparse_reviewed = True
                print(f"{paper['paper_id']}: review {attempt+2}/{config['max_attempts']} ({empty_count}/5 empty facets)", flush=True)
                messages += [dict(role='assistant', content=raw), dict(role='user', content=
                             f'{empty_count}/5 facets are empty. Review EACH empty facet against both the title T0 '
                             'and every abstract sentence. Recover supported problem, task, method, dataset or '
                             'contribution phrases you missed. Do not invent information or fill facets merely '
                             'to avoid empty lists; keep [] when the paper supplies no support. Return the complete JSON.')]
                continue
            return value, dict(**runtime, **generation, evidence_selection=selection,
                               attempt=attempt+1, seed=seed, sparse_reviewed=sparse_reviewed,
                               request_parameters=dict(max_new_tokens=config['max_new_tokens'],
                                                       max_attempts=config['max_attempts'], enable_thinking=False,
                                                       min_concept_retention=MIN_CONCEPT_RETENTION,
                                                       sparse_review_threshold=SPARSE_REVIEW_THRESHOLD,
                                                       temperature=config['temperature'], top_p=config['top_p'], top_k=config['top_k']))
        except ValueError as failure:
            error = str(failure)
            if attempt + 1 < config['max_attempts']:
                print(f"{paper['paper_id']}: retry {attempt+2}/{config['max_attempts']} ({error})", flush=True)
                messages += [dict(role='assistant', content=raw), dict(role='user', content=
                             'Validation error: ' + error + '. Correct the JSON using ONLY the original evidence_options. '
                             'Choose a valid evidence_id; use [] when unsupported.')]
    write_json(failure_path, dict(paper_id=paper['paper_id'], error=error, raw_output=raw))
    raise AnnotationError(f'Qwen annotation failed validation after {config["max_attempts"]} attempts: {error}')


def load_qwen(root, config):
    # Imports are lazy: dry-run, validator and unit checks need no GPU/model.
    try:
        import torch
        import transformers
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    except ImportError:
        raise RuntimeError('Install Qwen dependencies in the dedicated environment; see exp_a/README.md') from None
    if config['device'] == 'cuda':
        require(torch.cuda.is_available(), 'CUDA unavailable. Use the dedicated CUDA environment or explicitly select cpu')
    options = dict(revision=config['revision'], cache_dir=str(root / config['cache_dir']),
                   token=False, trust_remote_code=False)
    print(f"Loading {config['model']} on {config['device']}...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(config['model'], **options)
    quantization = {}
    if config.get('load_in_4bit'):
        quantization['quantization_config'] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16)
    model = AutoModelForCausalLM.from_pretrained(
        config['model'], **options, **quantization, use_safetensors=True,
        torch_dtype=torch.float16 if config['device'] == 'cuda' else torch.float32,
        device_map=config['device'], attn_implementation='sdpa')
    model.eval()
    runtime = dict(model=config['model'], model_revision=model.config._commit_hash or config['revision'],
                   torch_version=torch.__version__, transformers_version=transformers.__version__,
                   quantization='nf4_double' if quantization else 'none',
                   device=config['device'], gpu_name=torch.cuda.get_device_name(0) if config['device'] == 'cuda' else None)

    def generate_text(messages, seed):
        torch.manual_seed(seed)
        if config['device'] == 'cuda':
            torch.cuda.manual_seed_all(seed)
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        encoded = tokenizer(text, return_tensors='pt').to(model.device)
        input_tokens = encoded['input_ids'].shape[-1]
        require(input_tokens + config['max_new_tokens'] <= model.config.max_position_embeddings,
                'Paper exceeds model context; input was not silently truncated')
        started = time.monotonic()
        with torch.inference_mode():
            generated = model.generate(**encoded, max_new_tokens=config['max_new_tokens'],
                                       do_sample=True, temperature=config['temperature'],
                                       top_p=config['top_p'], top_k=config['top_k'],
                                       pad_token_id=tokenizer.eos_token_id)
        output_ids = generated[0, input_tokens:]
        raw = tokenizer.decode(output_ids, skip_special_tokens=True).strip()
        return raw, dict(usage=dict(input_tokens=input_tokens, output_tokens=len(output_ids)),
                         generation_seconds=round(time.monotonic()-started, 3))

    def extract(paper, instruction):
        return annotate(paper, instruction, config, runtime, generate_text,
                        root / config['output_dir'] / 'last_failure.json')

    return extract


def export(root, config, papers, provenance, db):
    directory = root / config['output_dir']
    records = [json.loads(row[0]) for row in db.execute('SELECT payload FROM annotations ORDER BY paper_id')]
    facets = [row['facets'] for row in records]
    metadata = [row['metadata'] for row in records]
    write_jsonl(directory / 'facets_silver.jsonl', facets)
    write_jsonl(directory / 'annotation_metadata.jsonl', metadata)
    done = {row['paper_id'] for row in facets}
    missing = [row['paper_id'] for row in papers if row['paper_id'] not in done]
    failures = dict(db.execute('SELECT paper_id, error FROM failures ORDER BY paper_id'))
    manifest = dict(contract_version='1.0', dataset_kind='real', tier='silver',
                    status='partial' if missing else 'complete', count=len(facets), corpus_count=len(papers),
                    missing_ids=missing, failed_annotations=failures, provenance=provenance,
                    coverage={f: sum(bool(row[f]) for row in facets) for f in FACET_NAMES},
                    total_input_tokens=sum(row['usage'].get('input_tokens', 0) for row in metadata),
                    total_output_tokens=sum(row['usage'].get('output_tokens', 0) for row in metadata),
                    files={name: sha256(directory / name) for name in ('facets_silver.jsonl', 'annotation_metadata.jsonl')})
    # Write manifest last: interrupted exports fail checksum validation instead of silent passing.
    write_json(directory / 'manifest.json', manifest)
    return manifest


def generate(root, config, limit=None):
    require(limit is None or type(limit) is int and limit > 0, 'limit must be positive')
    papers, provenance, instruction = inputs(root, config)
    start, end = paper_bounds(config, len(papers))
    directory = root / config['output_dir']
    directory.mkdir(parents=True, exist_ok=True)
    with single_run(directory), closing(sqlite3.connect(directory / '.exp_a_checkpoint.sqlite3')) as db:
        db.execute('CREATE TABLE IF NOT EXISTS run (signature TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS annotations (paper_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS failures (paper_id TEXT PRIMARY KEY, error TEXT NOT NULL)')
        signature = json.dumps(provenance, sort_keys=True)
        previous = db.execute('SELECT signature FROM run').fetchone()
        if previous:
            if previous[0] != signature:
                compatible = compatible_provenance(json.loads(previous[0]), provenance)
                require(compatible or db.execute('SELECT COUNT(*) FROM annotations').fetchone()[0] == 0,
                        'Run provenance changed; restore inputs/config or use a NEW output_dir')
                db.execute('UPDATE run SET signature = ?', (signature,))
                if not compatible:
                    db.execute('DELETE FROM failures')
                db.commit()
        else:
            db.execute('INSERT INTO run VALUES (?)', (signature,))
            db.commit()
        done = {row[0] for row in db.execute('SELECT paper_id FROM annotations')}
        require(done <= {p['paper_id'] for p in papers}, 'checkpoint contains unknown papers')
        catalog = {p['paper_id']: p for p in papers}
        review_ids = set()
        for payload, in db.execute('SELECT payload FROM annotations'):
            record = json.loads(payload)
            paper = catalog[record['facets']['paper_id']]
            require(validate_response(record['metadata']['evidence'], paper) == record['facets'], 'checkpoint facets differ from evidence')
            if (record['metadata'].get('extraction_policy_version') != GENERATOR_VERSION
                    and sum(not record['facets'][facet] for facet in FACET_NAMES) >= SPARSE_REVIEW_THRESHOLD):
                review_ids.add(paper['paper_id'])
        added = 0
        current = None
        extractor = None
        try:
            for position, paper in enumerate(papers[start-1:end], start):
                current = paper['paper_id']
                if current in done and current not in review_ids:
                    continue
                if limit is not None and added >= limit and current not in done:
                    continue
                print(f"Extracting {current} ({position}/{len(papers)})", flush=True)
                if extractor is None:
                    extractor = load_qwen(root, config)
                try:
                    value, local = extractor(paper, instruction)
                except AnnotationError as failure:
                    if current in done:
                        print(f'REVIEW REJECTED {current}: {failure}; previous accepted result retained', flush=True)
                        continue
                    with db:
                        db.execute('INSERT OR REPLACE INTO failures VALUES (?, ?)', (current, str(failure)))
                    print(f'REJECTED {current}: {failure}; saved for retry, continuing', flush=True)
                    continue
                facets = validate_response(value, paper)
                metadata = dict(paper_id=current, tier='silver', dataset_kind='real', annotator_type='qwen_local',
                                review_status='unreviewed', guideline_version=config['guideline_version'],
                                 prompt_version=config['prompt_version'], extraction_policy_version=GENERATOR_VERSION,
                                 evidence=value, **local)
                with db:
                    db.execute('INSERT OR REPLACE INTO annotations VALUES (?, ?)',
                               (current, json.dumps(dict(facets=facets, metadata=metadata), ensure_ascii=False)))
                    db.execute('DELETE FROM failures WHERE paper_id = ?', (current,))
                added += current not in done
                done.add(current)
        except (ValueError, RuntimeError) as error:
            raise RuntimeError(f'{current}: {error}') from None
        finally:
            manifest = export(root, config, papers, provenance, db)
    return manifest


def check_outputs(root, config, allow_partial=False):
    papers, provenance, _ = inputs(root, config)
    directory = root / config['output_dir']
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    require(compatible_provenance(manifest['provenance'], provenance), 'Output provenance changed')
    require(manifest['dataset_kind'] == 'real' and manifest['tier'] == 'silver' and manifest['contract_version'] == '1.0', 'wrong manifest kind/tier/version')
    for name in ('facets_silver.jsonl', 'annotation_metadata.jsonl'):
        require(sha256(directory / name) == manifest['files'][name], f'{name}: checksum mismatch')
    facets = read_jsonl(directory / 'facets_silver.jsonl')
    metadata = read_jsonl(directory / 'annotation_metadata.jsonl')
    catalog = {paper['paper_id']: paper for paper in papers}
    validate_facets(facets, set(catalog))
    require([row['paper_id'] for row in facets] == [row['paper_id'] for row in metadata], 'metadata IDs differ')
    for row, annotation in zip(facets, metadata):
        require(annotation['tier'] == 'silver' and annotation['dataset_kind'] == 'real'
                and annotation['review_status'] == 'unreviewed' and annotation['annotator_type'] == 'qwen_local', 'wrong annotation provenance')
        require(annotation['prompt_version'] == config['prompt_version'] and annotation['guideline_version'] == config['guideline_version'], 'annotation versions differ')
        require(validate_response(annotation['evidence'], catalog[row['paper_id']]) == row, 'facet labels differ from evidence')
    missing = sorted(set(catalog) - {row['paper_id'] for row in facets})
    require(manifest['count'] == len(facets) and manifest['corpus_count'] == len(papers) and manifest['missing_ids'] == missing, 'wrong output counts/coverage')
    require(set(manifest['failed_annotations']) <= set(missing), 'failed papers must remain missing, never fake annotations')
    require(manifest['status'] == ('partial' if missing else 'complete'), 'wrong completion status')
    require(manifest['coverage'] == {f: sum(bool(row[f]) for row in facets) for f in FACET_NAMES}, 'wrong facet coverage')
    require(allow_partial or not missing, f'Only {len(facets)}/{len(papers)} papers annotated; partial output is not ready for B–E')
    return manifest


def main():
    dedicated = ROOT / '.venv-qwen' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if dedicated.is_file() and (Path(sys.executable).resolve() != dedicated.resolve() or not sys.flags.utf8_mode):
        raise SystemExit(subprocess.call([str(dedicated), '-X', 'utf8', str(Path(__file__).resolve()), *sys.argv[1:]]))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='data/exp_a/config.json')
    parser.add_argument('--limit', type=int, help='Maximum NEW papers in paper_range this invocation; default all remaining in range')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true', help='Check inputs, no inference or outputs')
    mode.add_argument('--validate-only', action='store_true', help='Validate published A outputs, no inference')
    parser.add_argument('--allow-partial', action='store_true', help='Permit partial outputs with --validate-only')
    args = parser.parse_args()
    try:
        config = json.loads((ROOT / args.config).read_text(encoding='utf-8'))
        if args.dry_run:
            papers, _, _ = inputs(ROOT, config)
            start, end = paper_bounds(config, len(papers))
            print(f"DRY RUN: {end-start+1}/{len(papers)} papers; paper_range=[{start}, {end}] "
                  f"({papers[start-1]['paper_id']}..{papers[end-1]['paper_id']}); "
                  f"output={config['output_dir']}; local model={config['model']}; "
                  f"device={config['device']}; no API key required; no inference")
            return
        if args.validate_only:
            manifest = check_outputs(ROOT, config, args.allow_partial)
        else:
            manifest = generate(ROOT, config, args.limit)
            check_outputs(ROOT, config, allow_partial=True)
        print(f"{manifest['status'].upper()}: {manifest['count']}/{manifest['corpus_count']} silver papers; output={config['output_dir']}")
    except KeyboardInterrupt:
        print('Stopped; accepted papers saved. Run the same command to resume.', file=sys.stderr)
        sys.exit(130)
    except (ValueError, RuntimeError, OSError, KeyError, sqlite3.Error) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
