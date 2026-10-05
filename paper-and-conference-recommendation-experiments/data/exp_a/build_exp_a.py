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
GENERATOR_VERSION = '2.3'
LEGACY_GENERATORS = (
    ('2.0', '28ea4be0f55bffcaea5a74579d5b58bb9d14395a936b9f9f1225db21d9c521ab'),
    ('2.1', '49419379061eb134e3d4de9772dd7c34ce4e688502a34952a7df5e4b572a206b'),
    ('2.2', 'a9aafd069b8c1ec12ae0079e05a2272c854839c889da621964c27c61b66b3e68'),
    ('2.3', 'd4337f76920a5ebf503217b4ef0aff307aa798c151453b287ad7f14838e14c88'),
    ('2.3', '48ff88ceca3c0e259675a34e684a6ad871bfe0f3e24afc599f7d1fff81d48d72'),
)
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
    """Legacy paper validation failure; an audited empty fallback can be saved."""


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
    # Only known compatible generator upgrades may reuse accepted annotations.
    return previous == current or any(
        previous == dict(current, generator_version=version, generator_sha256=fingerprint)
        for version, fingerprint in LEGACY_GENERATORS)


def regular_verb_form(base, ending):
    if ending == 'ing' and base.endswith('ie'):
        return base[:-2] + 'ying'
    if ending == 'ing' and base == 'singe':
        return base + ending
    if base.endswith('e') and not base.endswith(('ee', 'ye')):
        return base + 'd' if ending == 'ed' else base[:-1] + 'ing'
    if ending == 'ed' and re.search(r'[^aeiou]y$', base):
        return base[:-1] + 'ied'
    # A single-vowel CVC base doubles its last consonant: hop -> hopping,
    # whereas a silent-e base drops e: hope -> hoping.
    if re.fullmatch(r'[^aeiou]*[aeiou][bdglmnprt]', base):
        return base + base[-1] + ending
    return base + ending


def word_forms(word):
    forms = {word}
    short_forms = {'using': 'use', 'used': 'use', 'uses': 'use',
                   'dying': 'die', 'lying': 'lie', 'tying': 'tie'}
    if word in short_forms:
        forms.add(short_forms[word])
    if not word.isalpha():
        return forms
    for ending in ('ing', 'ed'):
        if word.endswith(ending) and len(word) >= len(ending) + 3:
            stem = word[:-len(ending)]
            candidates = {stem, stem + 'e'}
            if stem.endswith('i'):
                candidates.add(stem[:-1] + 'y')
            if re.search(r'([b-df-hj-np-tv-z])\1$', stem):
                candidates.add(stem[:-1])
            forms.update(base for base in candidates if regular_verb_form(base, ending) == word)
    if word.endswith('ies') and len(word) > 4:
        forms.add(word[:-3] + 'y')
    elif word.endswith('s') and not word.endswith(('ss', 'us', 'is')) and len(word) > 3:
        forms.add(word[:-1])
        if word.endswith(('ches', 'shes', 'sses', 'xes', 'zes', 'oes')):
            forms.add(word[:-2])
    return forms


def without_parenthetical_examples(evidence):
    parts, depth, cursor = [], 0, 0
    for position, char in enumerate(evidence):
        if char == '(':
            if depth == 0:
                start = position
            depth += 1
        elif char == ')' and depth:
            depth -= 1
            if depth == 0 and re.match(r'\s*(?:e\s*\.\s*g\s*\.|for\s+example\b|for\s+instance\b|such\s+as\b)',
                                      evidence[start+1:position], re.IGNORECASE):
                parts.extend((evidence[cursor:start], ' '))
                cursor = position + 1
    return ''.join(parts) + evidence[cursor:]


def source_phrase_coverage(concept, evidence):
    tokens = [word_forms(word) for word in normalize(concept).split()]
    if not tokens:
        return 0
    best = 0
    for text in {evidence, without_parenthetical_examples(evidence)}:
        words = [word_forms(word) for word in normalize(text).split()]
        for start, word in enumerate(words):
            if not word & tokens[0]:
                continue
            end = start
            try:
                for token in tokens[1:]:
                    end = next(i for i in range(end + 1, len(words)) if words[i] & token)
            except StopIteration:
                continue
            best = max(best, len(tokens) / (end - start + 1))
    return best


def validate_response(value, paper, allow_quality_errors=False):
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
            require(all(isinstance(item[k], str) for k in item) and concept_nonempty(item['concept']),
                    f'{facet}: empty concept/evidence/source')
            concept, evidence, source = item['concept'], item['evidence'], item['source']
            require(concept == concept.strip(), f'{facet}: untrimmed concept')
            unresolved = allow_quality_errors and source == 'unresolved' and evidence == ''
            require(unresolved or source in ('title', 'abstract') and bool(evidence.strip()) and evidence in paper[source],
                    f"{paper['paper_id']}: {facet} evidence is absent from source text")
            coverage = source_phrase_coverage(concept, evidence)
            require(allow_quality_errors or coverage >= MIN_CONCEPT_RETENTION,
                    f'{facet}: concept must retain at least 70% of its source phrase in the same word order; '
                    f'matched retention={coverage:.0%} after verb-form and example normalization; '
                    f'invalid concept={json.dumps(concept)}; selected evidence={json.dumps(evidence)}. '
                    'Use a less abbreviated phrase from this evidence or choose the correct evidence_id; '
                    'regular verb forms are allowed, but do not invent words or replace them with synonyms.')
            require(concept.casefold() not in {c.casefold() for c in concepts}, f'{facet}: duplicate concept')
            concepts.append(concept)
        facets[facet] = concepts
    validate_facets([facets], {paper['paper_id']})
    return facets


def concept_nonempty(concept):
    return isinstance(concept, str) and bool(concept.strip())


def parse_generation(text):
    text = text.strip()
    fenced = re.fullmatch(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if fenced:
        text = fenced[1]
    try:
        value = json.loads(text)
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
        return value
    except (ValueError, RecursionError, UnicodeEncodeError):
        raise ValueError('Qwen output must contain one readable UTF-8 JSON object only') from None


def evidence_options(paper):
    abstract = paper['abstract']
    examples = [match.span() for match in re.finditer(r'\be\s*\.\s*g\s*\.', abstract, re.IGNORECASE)]
    sentences, cursor = [], 0
    for boundary in re.finditer(r'(?<=[.!?])\s+', abstract):
        if any(start <= boundary.start() <= end for start, end in examples):
            continue
        sentences.append(abstract[cursor:boundary.start()])
        cursor = boundary.end()
    sentences.append(abstract[cursor:])
    return {'T0': dict(source='title', evidence=paper['title']),
            **{f'A{i}': dict(source='abstract', evidence=sentence)
               for i, sentence in enumerate(sentences)}}


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


def assess_generation(raw, paper):
    """Recover a stable output shape, audit every issue, and score source support."""
    value = dict(paper_id=paper['paper_id'], **{facet: [] for facet in FACET_NAMES})
    try:
        selection = parse_generation(raw)
        require(isinstance(selection, dict), 'Qwen output must be a JSON object')
    except ValueError as error:
        return value, None, dict(score=0.0, schema_valid=False, parseable=False, validation_errors=[str(error)])
    shape_errors = []
    if selection.get('paper_id') != paper['paper_id']:
        shape_errors.append('wrong paper_id; output uses the supplied paper_id')
    if set(selection) != {'paper_id', *FACET_NAMES}:
        shape_errors.append('wrong facet keys; output uses all five facet lists')
    issues, total, valid, retention, supported_facets = [], 0, 0, 0.0, set()
    options = evidence_options(paper)
    for facet in FACET_NAMES:
        items = selection.get(facet)
        if not isinstance(items, list):
            shape_errors.append(f'{facet}: expected list')
            continue
        seen = set()
        for index, item in enumerate(items):
            total += 1
            where = f'{facet}[{index}]'
            if not isinstance(item, dict) or set(item) != {'concept', 'evidence_id'}:
                shape_errors.append(f'{where}: wrong concept/evidence_id keys')
            concept = item.get('concept') if isinstance(item, dict) else item
            if not concept_nonempty(concept):
                shape_errors.append(f'{where}: empty or non-string concept')
                continue
            if concept != concept.strip():
                shape_errors.append(f'{where}: untrimmed concept')
            concept = concept.strip()
            key = normalize(concept)
            if key in seen:
                issues.append(f'{where}: duplicate concept')
                # Duplicates count in the denominator but earn no support/retention.
                continue
            seen.add(key)
            evidence_id = item.get('evidence_id') if isinstance(item, dict) else None
            if not isinstance(evidence_id, str) or evidence_id not in options:
                shape_errors.append(f'{where}: unknown evidence_id')
                grounded = dict(concept=concept, evidence='', source='unresolved')
            else:
                grounded = dict(concept=concept, **options[evidence_id])
            value[facet].append(grounded)
            one = dict(paper_id=paper['paper_id'], **{name: [] for name in FACET_NAMES})
            one[facet] = [grounded]
            try:
                validate_response(one, paper)
            except ValueError as error:
                issues.append(f'{where}: {error}')
            else:
                valid += 1
                supported_facets.add(facet)
            retention += source_phrase_coverage(concept, grounded['evidence'])
    schema_valid = not shape_errors
    # ponytail: lexical support is a heuristic, not semantic confidence; keep human silver review.
    score = (60 * len(supported_facets) / len(FACET_NAMES)
             + (25 * valid / total + 5 * retention / total if total else 0)
             + 10 * schema_valid)
    return value, selection, dict(score=round(score, 4), schema_valid=schema_valid, parseable=True,
                                 validation_errors=shape_errors + issues)


def attempt_rank(attempt):
    return attempt['score'], attempt['parseable'], -len(attempt['validation_errors'])


def validate_annotation(value, paper, metadata):
    """Fallbacks relax quality checks only when the selected raw and audit agree."""
    fallback = metadata.get('fallback_used', False)
    require(type(fallback) is bool, 'fallback_used must be boolean')
    if not fallback:
        return validate_response(value, paper)
    errors = metadata.get('validation_errors')
    require(isinstance(errors, list) and errors and all(isinstance(error, str) for error in errors),
            'fallback must declare its validation errors')
    attempts = metadata.get('attempt_scores', [])
    require(isinstance(attempts, list), 'fallback attempt_scores must be a list')
    if attempts:
        require(metadata.get('attempts_used') == len(attempts), 'fallback attempts_used differs from audit')
        require([row.get('attempt') for row in attempts] == list(range(1, len(attempts)+1)),
                'fallback audit must contain every attempt in order')
        for row in attempts:
            _, _, assessment = assess_generation(row['raw_output'], paper)
            require(all(row.get(key) == assessment[key] for key in ('score', 'schema_valid', 'parseable')),
                    'fallback attempt score or structure differs from its raw output')
            require(all(issue in row['validation_errors'] for issue in assessment['validation_errors']),
                    'fallback attempt audit hides validation errors')
        selected = next((row for row in attempts if row['attempt'] == metadata['attempt']), None)
        require(selected is not None, 'fallback selected attempt is absent from audit')
        recovered, _, assessment = assess_generation(selected['raw_output'], paper)
        require(recovered == value, 'fallback evidence differs from its selected raw output')
        require(selected['score'] == assessment['score'], 'fallback score differs from its raw output')
        require(all(issue in errors for issue in assessment['validation_errors']),
                'fallback audit hides validation errors')
        require(errors == selected['validation_errors'], 'fallback errors differ from its selected attempt')
        require(metadata.get('selected_score') == selected['score'], 'fallback selected_score differs from audit')
        require(selected == max(attempts, key=attempt_rank),
                'fallback did not select the highest-scoring attempt')
    else:
        require(not any(value[facet] for facet in FACET_NAMES), 'nonempty fallback requires raw attempt audit')
    return validate_response(value, paper, allow_quality_errors=True)


def annotate(paper, instruction, config, runtime, generate_text, failure_path):
    source = dict(paper_id=paper['paper_id'],
                  evidence_options={key: row['evidence'] for key, row in evidence_options(paper).items()})
    policy = ('\nCurrent extraction policy overrides any stricter copying rule above: concepts may omit '
              'up to 30% of the words in their smallest matching source span. Keep retained words in their '
              'original order and preserve meaning. Regular verb forms such as representing/represent '
              'or extracting/extract are equivalent; arbitrary synonyms or invented words are not allowed. '
              'Parenthetical examples explicitly marked e.g., for example, for instance or such as may be omitted '
              'without affecting the retention ratio. Other parentheses, abbreviations and conditions still count. '
              'Short exact phrases are allowed. '
              'Consider both the title T0 and all abstract sentences for each facet.')
    messages = [dict(role='system', content=instruction + policy + '\nReturn JSON only. Schema: ' + json.dumps(SCHEMA)),
                dict(role='user', content=json.dumps(source, ensure_ascii=False))]
    sparse_reviewed = False
    attempts, best = [], None

    def finish(candidate, fallback):
        entry = candidate['audit']
        generation = dict(candidate['generation'])
        usage_keys = {key for row in attempts for key in row['usage']}
        generation['usage'] = {key: sum(row['usage'].get(key, 0) for row in attempts) for key in usage_keys}
        generation['generation_seconds'] = sum(row['generation_seconds'] for row in attempts)
        return candidate['value'], dict(
            **runtime, **generation, evidence_selection=candidate['selection'],
            attempt=entry['attempt'], seed=entry['seed'], sparse_reviewed=sparse_reviewed,
            attempts_used=len(attempts), selected_score=entry['score'], attempt_scores=attempts,
            fallback_used=fallback, validation_errors=entry['validation_errors'],
            request_parameters=dict(max_new_tokens=config['max_new_tokens'],
                                    max_attempts=config['max_attempts'], enable_thinking=False,
                                    min_concept_retention=MIN_CONCEPT_RETENTION,
                                    regular_verb_forms=True, ignore_parenthetical_examples=True,
                                    sparse_review_threshold=SPARSE_REVIEW_THRESHOLD,
                                    temperature=config['temperature'], top_p=config['top_p'], top_k=config['top_k']))

    for attempt in range(config['max_attempts']):
        seed = config['seed'] + int(paper['paper_id'][1:]) * config['max_attempts'] + attempt
        raw, generation = generate_text(messages, seed)
        # Preserve otherwise unencodable characters as literal escapes in the audit.
        raw = raw.encode('utf-8', errors='backslashreplace').decode('utf-8')
        value, selection, assessment = assess_generation(raw, paper)
        errors = assessment['validation_errors']
        empty_count = sum(not value[facet] for facet in FACET_NAMES)
        review = not errors and empty_count >= SPARSE_REVIEW_THRESHOLD and not sparse_reviewed
        if review:
            errors.append(f'{empty_count}/5 facets are empty; required sparse review has not completed')
        entry = dict(attempt=attempt+1, seed=seed, raw_output=raw, **assessment,
                     usage=generation.get('usage', {}), generation_seconds=generation.get('generation_seconds', 0))
        attempts.append(entry)
        candidate = dict(value=value, selection=selection, generation=generation, audit=entry)
        if best is None or attempt_rank(entry) > attempt_rank(best['audit']):
            best = candidate
        print(f"{paper['paper_id']}: attempt {attempt+1}/{config['max_attempts']} "
              f"score={entry['score']:.2f}/100; validation_errors={len(errors)}", flush=True)
        if not errors:
            return finish(candidate, False)
        if attempt + 1 < config['max_attempts']:
            if review:
                sparse_reviewed = True
                print(f"{paper['paper_id']}: review {attempt+2}/{config['max_attempts']} ({empty_count}/5 empty facets)", flush=True)
                feedback = (f'{empty_count}/5 facets are empty. Review EACH empty facet against both the title T0 '
                            'and every abstract sentence. Recover supported problem, task, method, dataset or '
                            'contribution phrases you missed. Do not invent information or fill facets merely '
                            'to avoid empty lists; keep [] when the paper supplies no support. Return the complete JSON.')
            else:
                print(f"{paper['paper_id']}: retry {attempt+2}/{config['max_attempts']} ({len(errors)} validation errors)", flush=True)
                feedback = ('Validation errors:\n' + '\n'.join(errors)
                            + '\nCorrect ALL errors using ONLY the original evidence_options. '
                            'Preserve supported concepts, choose valid evidence IDs, and use [] only when unsupported. '
                            'Return the complete JSON.')
            messages[2:] = [dict(role='assistant', content=raw), dict(role='user', content=feedback)]
    chosen = best['audit']
    write_json(failure_path, dict(paper_id=paper['paper_id'], error='\n'.join(chosen['validation_errors']),
                                 raw_output=chosen['raw_output'], selected_attempt=chosen['attempt'], attempt_scores=attempts))
    print(f"BEST AVAILABLE {paper['paper_id']}: attempt {chosen['attempt']}, "
          f"score={chosen['score']:.2f}/100; saved with validation errors", flush=True)
    return finish(best, True)


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
                    fallback_annotations={row['paper_id']: row['validation_errors'] for row in metadata
                                          if row.get('fallback_used', False)},
                    coverage={f: sum(bool(row[f]) for row in facets) for f in FACET_NAMES},
                    total_input_tokens=sum(row['usage'].get('input_tokens', 0) for row in metadata),
                    total_output_tokens=sum(row['usage'].get('output_tokens', 0) for row in metadata),
                    files={name: sha256(directory / name) for name in ('facets_silver.jsonl', 'annotation_metadata.jsonl')})
    # Write manifest last: interrupted exports fail checksum validation instead of silent passing.
    write_json(directory / 'manifest.json', manifest)
    return manifest


def restore_jsonl(directory, config, papers, provenance, db):
    """Recover an empty/lost checkpoint from verified exported evidence."""
    if db.execute('SELECT COUNT(*) FROM annotations').fetchone()[0]:
        return
    silver_path = directory / 'facets_silver.jsonl'
    metadata_path = directory / 'annotation_metadata.jsonl'
    if not silver_path.exists() and not metadata_path.exists():
        return
    manifest_path = directory / 'manifest.json'
    require(manifest_path.is_file(), 'JSONL recovery requires manifest.json; restore it or the checkpoint')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for path in (silver_path, metadata_path):
        if path.exists():
            require(sha256(path) == manifest['files'].get(path.name), f'{path.name}: checksum mismatch')
    require(metadata_path.is_file(),
            'JSONL recovery requires annotation_metadata.jsonl; restore it or the checkpoint')
    metadata = read_jsonl(metadata_path)
    silver = read_jsonl(silver_path) if silver_path.exists() else None
    if not metadata and not silver:
        return
    require(compatible_provenance(manifest['provenance'], provenance), 'Output provenance changed')
    require(manifest['dataset_kind'] == 'real' and manifest['tier'] == 'silver'
            and manifest['contract_version'] == '1.0', 'wrong manifest kind/tier/version')
    catalog = {paper['paper_id']: paper for paper in papers}
    records = []
    for annotation in metadata:
        paper_id = annotation['paper_id']
        require(paper_id in catalog, 'JSONL contains unknown papers')
        require(annotation['tier'] == 'silver' and annotation['dataset_kind'] == 'real'
                and annotation['review_status'] == 'unreviewed' and annotation['annotator_type'] == 'qwen_local',
                'wrong annotation provenance')
        require(annotation['prompt_version'] == config['prompt_version']
                and annotation['guideline_version'] == config['guideline_version'], 'annotation versions differ')
        facets = validate_annotation(annotation['evidence'], catalog[paper_id], annotation)
        require(facets['paper_id'] == paper_id, 'metadata IDs differ')
        records.append(dict(facets=facets, metadata=annotation))
    facets = [record['facets'] for record in records]
    validate_facets(facets, set(catalog))
    require(silver is None or silver == facets, 'facet labels differ from evidence')
    missing = sorted(set(catalog) - {row['paper_id'] for row in facets})
    require(manifest['count'] == len(records) and manifest['corpus_count'] == len(papers)
            and manifest['missing_ids'] == missing, 'wrong output counts/coverage')
    with db:
        db.executemany('INSERT INTO annotations VALUES (?, ?)',
                       [(row['facets']['paper_id'], json.dumps(row, ensure_ascii=False)) for row in records])
        db.executemany('DELETE FROM failures WHERE paper_id = ?',
                       [(row['facets']['paper_id'],) for row in records])
    print(f'Restored {len(records)} accepted papers from JSONL', flush=True)


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
        restore_jsonl(directory, config, papers, provenance, db)
        done = {row[0] for row in db.execute('SELECT paper_id FROM annotations')}
        require(done <= {p['paper_id'] for p in papers}, 'checkpoint contains unknown papers')
        catalog = {p['paper_id']: p for p in papers}
        review_ids = set()
        for payload, in db.execute('SELECT payload FROM annotations'):
            record = json.loads(payload)
            paper = catalog[record['facets']['paper_id']]
            require(validate_annotation(record['metadata']['evidence'], paper, record['metadata']) == record['facets'],
                    'checkpoint facets differ from evidence')
            if (record['metadata'].get('extraction_policy_version') != GENERATOR_VERSION
                    and not record['metadata'].get('sparse_reviewed')
                    and sum(not record['facets'][facet] for facet in FACET_NAMES) >= SPARSE_REVIEW_THRESHOLD):
                review_ids.add(paper['paper_id'])
        selected_ids = {paper['paper_id'] for paper in papers[start-1:end]}
        print(f'Range [{start}, {end}]: {len(done & selected_ids)}/{len(selected_ids)} saved; '
              f'{len(selected_ids - done)} missing; {len(review_ids & selected_ids)} need policy review', flush=True)
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
                        print(f'REVIEW FAILED {current}: {failure}; previous accepted result retained', flush=True)
                        continue
                    value = dict(paper_id=current, **{facet: [] for facet in FACET_NAMES})
                    local = dict(usage={}, fallback_used=True, validation_errors=[str(failure)],
                                 attempt_scores=[], attempts_used=0, attempt=0, selected_score=0.0)
                if current in done and local.get('fallback_used', False):
                    print(f'REVIEW FALLBACK {current}: previous accepted result retained', flush=True)
                    continue
                facets = validate_annotation(value, paper, local)
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
        require(validate_annotation(annotation['evidence'], catalog[row['paper_id']], annotation) == row,
                'facet labels differ from evidence')
    missing = sorted(set(catalog) - {row['paper_id'] for row in facets})
    require(manifest['count'] == len(facets) and manifest['corpus_count'] == len(papers) and manifest['missing_ids'] == missing, 'wrong output counts/coverage')
    require(set(manifest['failed_annotations']) <= set(missing), 'failed papers must remain missing, never fake annotations')
    require(manifest.get('fallback_annotations', {}) == {
        row['paper_id']: row['validation_errors'] for row in metadata if row.get('fallback_used', False)},
        'fallback summary differs from annotation audit')
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
