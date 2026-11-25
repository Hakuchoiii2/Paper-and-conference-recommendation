"""V2-only source-review, token, packaging and pre-training boundary."""
import hashlib
import importlib.util
import json
import re
import zipfile
from pathlib import PurePosixPath
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FACETS = ('problem', 'task', 'method', 'dataset', 'contribution')


def sha256(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def actor(value):
    return re.sub(r'^(?:author|reviewer)[_: -]+', '', value.strip().casefold())


SCHEMA = load_module('exp_a_v2_training_schema', HERE.parent / 'label_revision_v2/schema.py')


def validate_decision(paper, target, proof, hashes, *, allow_unreviewed=False):
    """Validate one independent acceptance; semantic judgments remain AI reviews."""
    pid = paper['paper_id']
    require(set(paper) == {'paper_id', 'title', 'abstract', 'split'}, pid + ': wrong source fields')
    require(paper['split'] in ('train', 'dev'), pid + ': test or unknown split')
    SCHEMA.ground_response(target, paper)
    require(proof.get('paper_id') == pid, pid + ': wrong decision paper_id')
    require(proof.get('source_sha256') == digest({k: paper[k] for k in ('paper_id', 'title', 'abstract')}),
            pid + ': source hash mismatch')
    require(proof.get('annotation_sha256') == digest(target), pid + ': annotation hash mismatch')
    for key in ('policy_sha256', 'prompt_sha256', 'schema_sha256'):
        require(proof.get(key) == hashes[key], pid + ': ' + key + ' mismatch')
    if allow_unreviewed and proof.get('status') == 'source_authored_unreviewed':
        require(isinstance(proof.get('author_id'), str) and proof['author_id'].strip()
                and proof.get('reviewer_id') is None and 'facet_checks' not in proof
                and proof.get('label_source') == 'ai_reference'
                and proof.get('human_review_status') == 'pending'
                and proof.get('unresolved_issues') == [], pid + ': invalid unreviewed provenance')
        require(isinstance(proof.get('source_notes'), list)
                and all(isinstance(note, str) and note.strip() for note in proof['source_notes']),
                pid + ': invalid source notes')
        return dict(proof)
    author, reviewer = proof.get('author_id'), proof.get('reviewer_id')
    require(isinstance(author, str) and author.strip() and isinstance(reviewer, str) and reviewer.strip()
            and actor(author) != actor(reviewer), pid + ': independent author/reviewer required')
    require(proof.get('status') == 'accepted' and proof.get('label_source') == 'ai_reference'
            and proof.get('human_review_status') == 'pending', pid + ': acceptance/provenance missing')
    require(proof.get('unresolved_issues') == [], pid + ': unresolved review issues')
    require(isinstance(proof.get('source_notes'), list)
            and all(isinstance(note, str) and note.strip() for note in proof['source_notes']),
            pid + ': invalid source notes')
    checks = proof.get('facet_checks')
    require(isinstance(checks, dict) and set(checks) == set(FACETS), pid + ': missing facet checks')
    for facet, check in checks.items():
        require(isinstance(check, dict) and all(check.get(key) == 'pass'
                for key in ('evidence', 'role', 'qualifiers', 'coverage'))
                and isinstance(check.get('note'), str) and check['note'].strip(),
                pid + ': incomplete ' + facet + ' review')
    return dict(proof)

TRAINER = load_module('exp_a_v2_unchanged_trainer', HERE.parent / 'train.py')
MODEL = 'Qwen/Qwen3-8B'
REVISION = 'b968826d9c46dd6066d109eabc6255188de91218'
DATASET = 'htnkhi/exp-a-qwen-qlora-v2-inputs'
KERNEL = 'htnkhi/exp-a-qwen-qlora-v2'
OUTPUT = 'adapters/qwen3-8b-facets-qlora-v2'
CHECKPOINTS = 'train_state_v2'
HASH_KEYS = ('policy_sha256', 'prompt_sha256', 'schema_sha256')
BATCH_FILES = ('sources.jsonl', 'draft_annotations.jsonl', 'draft_audit.jsonl', 'draft_seal.json',
               'reviewed_annotations.jsonl', 'decisions.jsonl', 'review_seal.json')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def safe_file(directory, name):
    require(isinstance(name, str) and name and '\\' not in name and ':' not in name
            and not name.startswith('/') and all(p not in ('.', '..', '') for p in name.split('/')),
            'Unsafe relative file path: ' + str(name))
    root = Path(directory).resolve()
    path = root / PurePosixPath(name)
    require(path.resolve().is_relative_to(root), 'Escaping file path: ' + name)
    require(path.is_file(), 'Missing file: ' + name)
    for part in (path, *path.parents):
        if part == root:
            break
        require(not part.is_symlink() and not (getattr(part.stat(), 'st_file_attributes', 0) & 1024),
                'Reparse/symlink file path: ' + name)
    return path


def verify_files(directory, files):
    require(isinstance(files, dict) and bool(files), 'Missing file hashes')
    for name, expected in files.items():
        require(isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected),
                'Invalid SHA-256: ' + name)
        require(sha256(safe_file(directory, name)) == expected, 'File hash mismatch: ' + name)


def keyed(path):
    result = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        require(isinstance(row, dict) and isinstance(row.get('paper_id'), str) and row['paper_id'],
                'Missing paper_id: ' + str(path))
        require(row['paper_id'] not in result, 'Duplicate paper_id: ' + row['paper_id'])
        result[row['paper_id']] = row
    require(bool(result), 'Empty records: ' + str(path))
    return result


def validate_splits(split_ids):
    require(isinstance(split_ids, dict) and set(split_ids) == {'train', 'dev', 'test'}, 'Wrong frozen splits')
    seen = set()
    for split, count in (('train', 467), ('dev', 100), ('test', 100)):
        ids = split_ids[split]
        require(isinstance(ids, list) and len(ids) == count and all(isinstance(pid, str) and pid for pid in ids),
                'Wrong original ' + split + ' split size')
        require(len(set(ids)) == count and not seen.intersection(ids), 'Duplicate/overlapping frozen split IDs')
        seen.update(ids)



def validate_confirmation_support(review_dir, accepted, files, hashes, queue):
    """Bind both sealed author drafts and final rechecks to the accepted 12-source candidate."""
    directory = Path(review_dir) / 'confirmation12'
    required = {'sources.jsonl', 'selection.json', 'adjudicated_annotations.jsonl', 'adjudication.json'} | {
        f'author_{author}_{kind}.{suffix}' for author in ('a', 'b')
        for kind, suffix in (('annotations', 'jsonl'), ('audit', 'jsonl'), ('seal', 'json'),
                             ('cross_review', 'json'), ('final_recheck', 'json'))}
    support = accepted.get('files')
    require(isinstance(support, dict) and set(support) == required, 'Missing/unapproved confirmation support files')
    verify_files(directory, support)
    require(all(files.get('confirmation12/' + name) == value for name, value in support.items()),
            'Confirmation support differs from review manifest')
    candidate = support['adjudicated_annotations.jsonl']
    require(accepted.get('annotations_sha256') == candidate, 'Accepted confirmation candidate checksum differs')
    ids = accepted['paper_ids']
    sources, annotations = keyed(directory / 'sources.jsonl'), keyed(directory / 'adjudicated_annotations.jsonl')
    require(set(sources) == set(annotations) == set(ids), 'Confirmation source/candidate IDs differ')
    for pid, paper in sources.items():
        require(all(paper.get(key) == value for key, value in dict(queue[pid]['source'], split=queue[pid]['split']).items()),
                pid + ': confirmation source differs from frozen queue')
        SCHEMA.ground_response(annotations[pid], paper)
    selection = read(directory / 'selection.json')
    require(selection.get('paper_ids') == ids and selection.get('source_sha256') == support['sources.jsonl']
            and all(selection.get(key) == hashes[key] for key in HASH_KEYS), 'Confirmation selection differs')
    mapping = accepted.get('independent_actor_mapping', {value: value for value in accepted['independent_author_ids']})
    require(isinstance(mapping, dict) and set(mapping) == set(accepted['independent_author_ids'])
            and set(mapping.values()) == {'author_a', 'author_b'}, 'Confirmation stable actor mapping differs')
    for author, other in (('a', 'b'), ('b', 'a')):
        prefix = 'author_' + author
        for kind in ('annotations', 'audit'):
            rows = keyed(directory / (prefix + '_' + kind + '.jsonl'))
            require(set(rows) == set(ids), 'Confirmation draft/audit IDs differ')
            if kind == 'annotations':
                for pid, value in rows.items():
                    SCHEMA.ground_response(value, sources[pid])
        seal = read(directory / (prefix + '_seal.json'))
        require(seal.get('reviewer_identity') == prefix and seal.get('paper_ids') == ids,
                'Confirmation draft actor/cohort differs')
        bindings = dict(sources=support['sources.jsonl'], selection=support['selection.json'],
            annotations=support[prefix + '_annotations.jsonl'], audit=support[prefix + '_audit.jsonl'],
            policy=hashes['policy_sha256'], prompt=hashes['prompt_sha256'], schema=hashes['schema_sha256'])
        if author == 'a':
            require(isinstance(seal.get('sha256'), dict)
                    and all(seal['sha256'].get(key) == value for key, value in bindings.items()),
                    'Confirmation A draft seal differs')
        else:
            fields = dict(sources='sources_sha256', selection='selection_sha256', annotations='annotations_sha256',
                audit='audit_sha256', policy='policy_sha256', prompt='prompt_sha256', schema='schema_sha256')
            require(all(seal.get(fields[key]) == value for key, value in bindings.items()), 'Confirmation B draft seal differs')
        cross = read(directory / (prefix + '_cross_review.json'))
        require(cross.get('reviewer_identity') == prefix
                and cross.get('reviewed_author', cross.get('review_subject')) == 'author_' + other,
                'Confirmation cross-review identity differs')
        cross_bindings = dict(sources=support['sources.jsonl'], policy=hashes['policy_sha256'],
            **{f'author_{actor}_{kind}': support[f'author_{actor}_{kind}.{suffix}']
               for actor in ('a', 'b') for kind, suffix in (('annotations', 'jsonl'), ('audit', 'jsonl'), ('seal', 'json'))})
        require(isinstance(cross.get('input_sha256'), dict)
                and all(cross['input_sha256'].get(key) == value for key, value in cross_bindings.items()),
                'Confirmation cross-review does not bind sealed drafts')
        final = read(directory / (prefix + '_final_recheck.json'))
        final_bindings = dict(sources=support['sources.jsonl'], selection=support['selection.json'],
            adjudication=support['adjudication.json'], policy=hashes['policy_sha256'], prompt=hashes['prompt_sha256'],
            schema_contract=hashes['schema_sha256'],
            **{f'author_{actor}_{kind}': support[f'author_{actor}_{kind}.json']
               for actor in ('a', 'b') for kind in ('cross_review', 'seal')})
        final_bindings['candidate' if author == 'a' else 'candidate_annotations'] = candidate
        require(final.get('reviewer_identity') == prefix and final.get('status') == 'accepted_integrated_revisions'
                and final.get('remaining_material_issues') == [] and isinstance(final.get('input_sha256'), dict)
                and all(final['input_sha256'].get(key) == value for key, value in final_bindings.items())
                and (author == 'a' or final.get('candidate_sha256') == candidate),
                'Confirmation final recheck is unaccepted or bound to a different candidate')
    return {'confirmation12/' + name for name in support}


def validate_reviews(review_dir, queue, split_ids, hashes, *, prior_ids=()):
    """Require the complete frozen cohort, independent decisions and sealed batch lineage."""
    review_dir = Path(review_dir)
    validate_splits(split_ids)
    expected = {pid: split for split in ('train', 'dev') for pid in split_ids[split]}
    require(set(queue) == set(expected), 'Review queue missing/reassigned/test IDs')
    for pid, row in queue.items():
        require(row.get('split') == expected[pid] and isinstance(row.get('source'), dict)
                and set(row['source']) == {'paper_id', 'title', 'abstract'}
                and row['source']['paper_id'] == pid, pid + ': queue source/split mismatch')
    manifest = read(review_dir / 'review_manifest.json')
    require(manifest.get('version') in ('exp_a_v2_source_review_1', 'exp_a_v2_source_review_2')
            and manifest.get('label_source') == 'ai_reference'
            and manifest.get('human_review_status') == 'pending', 'Wrong source-review manifest/provenance')
    for key in HASH_KEYS:
        require(manifest.get(key) == hashes[key], 'Review manifest ' + key + ' differs')
    files = manifest.get('files')
    verify_files(review_dir, files)
    required = {'source_papers.jsonl', 'annotations.jsonl', 'decisions.jsonl', 'confirmation12/acceptance.json'}
    require(required.issubset(files), 'Review manifest missing required evidence files')
    require(manifest.get('policy_confirmation_file') == 'confirmation12/acceptance.json'
            and manifest.get('policy_confirmation_sha256') == files['confirmation12/acceptance.json'],
            'Missing policy-confirmation hash')
    accepted = read(safe_file(review_dir, manifest['policy_confirmation_file']))
    ids, authors = accepted.get('paper_ids'), accepted.get('independent_author_ids')
    require(accepted.get('status') == 'accepted' and type(accepted.get('unresolved_material_issues')) is int
            and accepted['unresolved_material_issues'] == 0, 'Policy confirmation is not accepted')
    require(isinstance(ids, list) and len(ids) == len(set(ids)) == 12 and set(ids).issubset(expected)
            and not set(ids).intersection(prior_ids)
            and sum(expected[pid] == 'train' for pid in ids) == 6, 'Policy confirmation needs 12 fresh 6/6 train/dev IDs')
    require(isinstance(authors, list) and len(authors) == 2
            and all(isinstance(a, str) and a.strip() for a in authors)
            and len({actor(a) for a in authors}) == 2, 'Policy confirmation needs two independent authors')
    require(all(accepted.get(key) == hashes[key] for key in HASH_KEYS), 'Policy confirmation contract differs')
    allowed_files = required | validate_confirmation_support(review_dir, accepted, files, hashes, queue)
    lean = manifest['version'] == 'exp_a_v2_source_review_2'
    if lean:
        require('review_scope_v2.json' in files, 'Missing authorized sampled-review scope')
        scope = read(safe_file(review_dir, 'review_scope_v2.json'))
        require(scope.get('version') == 'exp_a_v2_review_scope_2'
                and scope.get('mode') == 'source_first_draft_all_automated_validation_all_independent_review_sample_and_difficult_cases'
                and scope.get('required_full_independent_review') is False
                and scope.get('required_source_first_annotation') is True
                and scope.get('label_source') == 'ai_reference'
                and scope.get('human_review_status') == 'pending', 'Wrong sampled-review scope')
        allowed_files.add('review_scope_v2.json')
        allowed_files.update(name for name in files if re.fullmatch(r'selected_reviews/[a-z_]+(?:annotations|decisions)\.jsonl|selected_reviews/[a-z_]+seal\.json', name))
    papers, targets, decisions = (keyed(safe_file(review_dir, name))
                                 for name in ('source_papers.jsonl', 'annotations.jsonl', 'decisions.jsonl'))
    require(set(papers) == set(targets) == set(decisions) == set(expected), 'Missing/extra/test review paper IDs')
    records = {}
    for pid in expected:
        paper = papers[pid]
        require(paper == dict(queue[pid]['source'], split=expected[pid]), pid + ': source differs from frozen queue')
        proof = validate_decision(paper, targets[pid], decisions[pid], hashes, allow_unreviewed=lean)
        records[pid] = dict(paper=paper, target=targets[pid], provenance=proof)
    sealed_ids = set()
    seals = sorted(name for name in files if re.fullmatch(r'batches/[^/]+/seal\.json', name))
    require(bool(seals), 'Missing sealed batch evidence')
    for name in seals:
        seal = read(safe_file(review_dir, name))
        batch = name.rsplit('/', 1)[0]
        require(seal.get('batch_id') == batch.split('/')[-1], 'Wrong sealed batch_id')
        batch_ids = seal.get('paper_ids')
        require(isinstance(batch_ids, list) and batch_ids and len(set(batch_ids)) == len(batch_ids)
                and set(batch_ids).issubset(expected) and not sealed_ids.intersection(batch_ids),
                'Duplicate/missing/test batch IDs')
        if lean and seal.get('review_status') in ('source_authored_unreviewed', 'sampled_review'):
            expected_files = {batch + '/' + file for file in
                ('sources.jsonl', 'draft_annotations.jsonl', 'draft_audit.jsonl', 'draft_seal.json', 'decisions.jsonl')}
            mixed = seal['review_status'] == 'sampled_review'
            if mixed:
                expected_files.update({batch + '/reviewed_annotations.jsonl', batch + '/review_seal.json'})
            allowed_files.update(expected_files | {name})
            require(isinstance(seal.get('files'), dict) and set(seal['files']) == expected_files
                    and all(files.get(file) == value for file, value in seal['files'].items()),
                    'Unreviewed batch proof differs')
            verify_files(review_dir, seal['files'])
            draft = read(safe_file(review_dir, batch + '/draft_seal.json'))
            author = seal.get('author_id')
            require(isinstance(author, str) and author.strip() and seal.get('reviewer_id') is None
                    and draft.get('author_id') == author and draft.get('paper_ids') == batch_ids
                    and all(draft.get(key) == hashes[key] for key in HASH_KEYS),
                    'Unreviewed batch actor/cohort/contract differs')
            require(all(draft.get(key) == files[batch + '/' + file] for key, file in
                (('source_sha256', 'sources.jsonl'), ('annotations_sha256', 'draft_annotations.jsonl'),
                 ('audit_sha256', 'draft_audit.jsonl'))), 'Unreviewed draft seal differs')
            if mixed:
                review = read(safe_file(review_dir, batch + '/review_seal.json'))
                require(review.get('paper_ids') == batch_ids
                        and review.get('draft_seal_sha256') == files[batch + '/draft_seal.json']
                        and review.get('reviewed_annotations_sha256') == files[batch + '/reviewed_annotations.jsonl']
                        and review.get('decisions_sha256') == files[batch + '/decisions.jsonl']
                        and review.get('source_sha256') == files[batch + '/sources.jsonl']
                        and all(review.get(key) == hashes[key] for key in HASH_KEYS)
                        and review.get('unresolved_material_issues') == 0, 'Sampled batch review lineage differs')
                final_rows = keyed(safe_file(review_dir, batch + '/reviewed_annotations.jsonl'))
                require(set(final_rows) == set(batch_ids), 'Sampled annotation IDs differ')
            rows = {file: keyed(safe_file(review_dir, batch + '/' + file)) for file in
                    ('sources.jsonl', 'draft_annotations.jsonl', 'draft_audit.jsonl', 'decisions.jsonl')}
            require(all(set(values) == set(batch_ids) for values in rows.values()), 'Unreviewed batch IDs differ')
            for pid in batch_ids:
                require(rows['sources.jsonl'][pid] == papers[pid]
                        and rows['decisions.jsonl'][pid] == decisions[pid]
                        and decisions[pid]['author_id'] == author,
                        pid + ': aggregate differs from sealed source draft')
                SCHEMA.ground_response(rows['draft_annotations.jsonl'][pid], papers[pid])
                if mixed:
                    require(final_rows[pid] == targets[pid], pid + ': sampled final target differs')
                if decisions[pid]['status'] == 'source_authored_unreviewed':
                    require(rows['draft_annotations.jsonl'][pid] == targets[pid]
                            and decisions[pid]['reviewer_id'] is None,
                            pid + ': unreviewed target changed or reviewer invented')
                else:
                    require(mixed and decisions[pid]['status'] == 'accepted',
                            pid + ': independent decision needs sampled-review seal')
            sealed_ids.update(batch_ids)
            continue
        expected_files = {batch + '/' + file for file in BATCH_FILES}
        allowed_files.update(expected_files | {name})
        require(isinstance(seal.get('files'), dict) and set(seal['files']) == expected_files
                and all(files.get(file) == value for file, value in seal['files'].items()),
                'Batch seal file proof differs from review manifest')
        verify_files(review_dir, seal['files'])
        draft, reviewed = (read(safe_file(review_dir, batch + '/' + file))
                           for file in ('draft_seal.json', 'review_seal.json'))
        author, reviewer = seal.get('author_id'), seal.get('reviewer_id')
        require(isinstance(author, str) and isinstance(reviewer, str) and author.strip() and reviewer.strip()
                and actor(author) != actor(reviewer), 'Independent batch author/reviewer required')
        require(draft.get('author_id') == author and reviewed.get('reviewer_id') == reviewer
                and draft.get('paper_ids') == batch_ids == reviewed.get('paper_ids')
                and all(draft.get(key) == reviewed.get(key) == hashes[key] for key in HASH_KEYS),
                'Batch actor/cohort/contract lineage differs')
        require(type(reviewed.get('unresolved_material_issues')) is int and reviewed['unresolved_material_issues'] == 0,
                'Batch has unresolved material issues')
        pairs = ((draft, 'source_sha256', 'sources.jsonl'), (draft, 'annotations_sha256', 'draft_annotations.jsonl'),
                 (draft, 'audit_sha256', 'draft_audit.jsonl'), (reviewed, 'draft_seal_sha256', 'draft_seal.json'),
                 (reviewed, 'source_sha256', 'sources.jsonl'),
                 (reviewed, 'reviewed_annotations_sha256', 'reviewed_annotations.jsonl'),
                 (reviewed, 'decisions_sha256', 'decisions.jsonl'))
        require(all(value.get(key) == files[batch + '/' + file] for value, key, file in pairs), 'Broken draft/review seal hashes')
        batch_rows = {file: keyed(safe_file(review_dir, batch + '/' + file))
                      for file in ('sources.jsonl', 'draft_annotations.jsonl', 'draft_audit.jsonl',
                                   'reviewed_annotations.jsonl', 'decisions.jsonl')}
        require(all(set(rows) == set(batch_ids) for rows in batch_rows.values()), 'Batch record IDs differ')
        for pid in batch_ids:
            require(batch_rows['sources.jsonl'][pid] == papers[pid]
                    and batch_rows['reviewed_annotations.jsonl'][pid] == targets[pid]
                    and batch_rows['decisions.jsonl'][pid] == decisions[pid], pid + ': aggregate differs from sealed batch')
            SCHEMA.ground_response(batch_rows['draft_annotations.jsonl'][pid], papers[pid])
            require(decisions[pid]['author_id'] == author and decisions[pid]['reviewer_id'] == reviewer,
                    pid + ': decision actor differs from sealed batch')
        sealed_ids.update(batch_ids)
    if lean:
        reviewed = [pid for pid in expected if decisions[pid]['status'] == 'accepted']
        require(len(reviewed) >= 60 and {expected[pid] for pid in reviewed} == {'train', 'dev'},
                'Need existing independent sample of at least 60 train/dev papers')
        require(manifest.get('independent_review_paper_ids') == sorted(reviewed),
                'Independent review coverage claim differs from actual decisions')
        difficult = manifest.get('difficult_paper_ids')
        require(isinstance(difficult, list) and len(difficult) == len(set(difficult))
                and set(difficult).issubset(reviewed), 'Difficult source cases need independent resolution')
    require(sealed_ids == set(expected), 'Sealed batches do not cover all 567 papers')
    require(set(files) == allowed_files, 'Unapproved source-review evidence file; only train/dev release proof is allowed')
    return records, manifest


def messages(paper, instruction):
    source = dict(paper_id=paper['paper_id'], evidence_options={
        key: value['evidence'] for key, value in SCHEMA.base.evidence_options(paper).items()})
    return [dict(role='system', content=instruction + '\nReturn JSON only. Schema: '
                 + json.dumps(SCHEMA.SCHEMA, separators=(',', ':'))),
            dict(role='user', content=json.dumps(source, ensure_ascii=False))]


def load_tokenizer(cache_dir=None, *, local_files_only=True):
    from transformers import AutoTokenizer
    cache = cache_dir or (ROOT / 'models/huggingface' if (ROOT / 'models/huggingface').is_dir()
                          else '/tmp/exp_a_huggingface')
    source = MODEL
    if local_files_only:
        from huggingface_hub import snapshot_download
        source = snapshot_download(MODEL, revision=REVISION, cache_dir=str(cache),
            local_files_only=True, token=False)
        require(Path(source).is_dir() and Path(source).name == REVISION, 'Missing exact pinned tokenizer snapshot')
    return AutoTokenizer.from_pretrained(source, revision=REVISION, cache_dir=str(cache),
        local_files_only=local_files_only, token=False, trust_remote_code=False)


def tokenizer_contract(tokenizer):
    return dict(model=MODEL, revision=REVISION, vocabulary_sha256=digest(tokenizer.get_vocab()),
        chat_template_sha256=hashlib.sha256(tokenizer.chat_template.encode('utf-8')).hexdigest(),
        eos_token_id=tokenizer.eos_token_id)


def token_lengths(tokenizer, row):
    encoded = TRAINER.encode_example(tokenizer, row, 4096)
    supervised = sum(token != -100 for token in encoded['labels'])
    require(0 < supervised <= 2048, row['paper_id'] + ': assistant exceeds 2048 tokens; truncation forbidden')
    prefix = tokenizer.apply_chat_template(row['messages'][:2], tokenize=True,
        add_generation_prompt=True, enable_thinking=False)
    complete = tokenizer.apply_chat_template(row['messages'], tokenize=True,
        add_generation_prompt=False, enable_thinking=False)
    require(complete[:len(prefix)] == prefix and encoded['input_ids'][:len(prefix)] == prefix,
            row['paper_id'] + ': tokenizer changes inference prefix')
    return dict(sequence=len(encoded['input_ids']), assistant=supervised)


def write_json(path, value):
    TRAINER.write_json(path, value)


def require_new_v2_directory(destination, root):
    path, v2 = Path(destination).resolve(), Path(root).resolve() / 'data/exp_a/finetuning/v2'
    require(path.is_relative_to(v2) and path != v2
            and path.relative_to(v2).parts[0] not in ('build', 'review', 'downloads', 'validation'),
            'Destination must be a new v2 training directory')
    require(not path.exists() or (path.is_dir() and not any(path.iterdir())), 'Refusing nonempty training destination')
    return path


def prepare(review_dir, destination, tokenizer=None, *, root=None):
    root = Path(root or ROOT).resolve()
    destination = require_new_v2_directory(destination, root)
    finetuning = root / 'data/exp_a/finetuning'
    policy = finetuning / 'label_revision_v2'
    protected = read(policy / 'pilot40/protected_v1_sha256.json')
    require(len(protected) == 38, 'Expected all 38 protected v1 artifacts')
    verify_files(root, protected)
    frozen_path = finetuning / 'data/manifest.json'
    frozen = read(frozen_path)
    validate_splits(frozen['split_ids'])
    queue_path = finetuning / 'v2/build/train_dev_review_queue.jsonl'
    readiness = read(finetuning / 'v2/build/readiness.json')
    require(sha256(queue_path) == readiness['review_queue_sha256']
            and sha256(frozen_path) == readiness['frozen_split_sha256'], 'Frozen queue/split checksum differs')
    hashes = {key: sha256(policy / file) for key, file in zip(HASH_KEYS,
        ('policy_v2_2.md', 'prompt_v2_2.md', 'response_schema.json'))}
    require(all(readiness.get(key) == hashes[key] for key in HASH_KEYS), 'Policy/prompt/schema differs from frozen queue')
    require(read(policy / 'response_schema.json') == SCHEMA.SCHEMA, 'Response schema differs from validator')
    prior = set(keyed(policy / 'pilot40/adjudicated_annotations.jsonl'))
    queue = keyed(queue_path)
    records, review_manifest = validate_reviews(review_dir, queue, frozen['split_ids'], hashes, prior_ids=prior)
    pinned = load_tokenizer()
    if tokenizer is None:
        tokenizer = pinned
    contract = tokenizer_contract(pinned)
    require(tokenizer_contract(tokenizer) == contract, 'Supplied tokenizer differs from pinned local tokenizer')
    instruction = (policy / 'prompt_v2_2.md').read_text(encoding='utf-8')
    payloads = {'instruction.txt': instruction.encode('utf-8'), 'review_queue.jsonl': queue_path.read_bytes(),
                'frozen_split.json': frozen_path.read_bytes(),
                'prior_review_ids.json': (json.dumps(sorted(prior)) + '\n').encode('utf-8')}
    for target, source_name in (('policy.md', 'policy_v2_2.md'), ('prompt.md', 'prompt_v2_2.md'),
                                ('response_schema.json', 'response_schema.json')):
        payloads[target] = (policy / source_name).read_bytes()
    lengths = {}
    for split in ('train', 'dev'):
        rows = []
        lengths[split] = []
        for pid in frozen['split_ids'][split]:
            record = records[pid]
            row = dict(paper_id=pid, messages=messages(record['paper'], instruction) + [
                dict(role='assistant', content=json.dumps(record['target'], ensure_ascii=False))],
                provenance=record['provenance'])
            row['token_lengths'] = token_lengths(tokenizer, row)
            lengths[split].append(row['token_lengths'])
            rows.append(row)
        payloads[split + '.jsonl'] = ''.join(json.dumps(row, ensure_ascii=False) + '\n'
                                             for row in rows).encode('utf-8')
    for name in (*review_manifest['files'], 'review_manifest.json'):
        payloads['review/' + name] = safe_file(review_dir, name).read_bytes()
    manifest = dict(version='exp_a_v2_training_data_1', counts=dict(train=467, dev=100),
        split_ids=frozen['split_ids'], **hashes, label_source='ai_reference', human_review_status='pending',
        protected_v1_verified=38, protected_v1_sha256=protected, frozen_split_sha256=sha256(frozen_path),
        review_queue_sha256=sha256(queue_path),
        review_coverage=dict(independent=sum(r['provenance']['status'] == 'accepted' for r in records.values()),
            source_authored_unreviewed=sum(r['provenance']['status'] == 'source_authored_unreviewed' for r in records.values())),
        review_manifest_sha256=sha256(Path(review_dir) / 'review_manifest.json'),
        instruction_sha256=hashlib.sha256(instruction.encode('utf-8')).hexdigest(),
        rendered_system_sha256=hashlib.sha256(messages(next(iter(records.values()))['paper'], instruction)[0]['content'].encode('utf-8')).hexdigest(),
        validator_sha256=sha256(HERE.parent / 'label_revision_v2/schema.py'),
        trainer_sha256=sha256(HERE.parent / 'train.py'), tokenizer=contract,
        token_limits=dict(max_sequence_tokens=4096, max_assistant_tokens=2048, verified=True,
            observed={split: dict(max_sequence=max(v['sequence'] for v in values),
                                  max_assistant=max(v['assistant'] for v in values)) for split, values in lengths.items()}),
        output_sha256={name: hashlib.sha256(payload).hexdigest() for name, payload in payloads.items()})
    destination.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    write_json(destination / 'manifest.json', manifest)
    return manifest

CODE_FILES = (
    'data/exp_a/finetuning/v2/training.py', 'data/exp_a/finetuning/train.py',
    'data/exp_a/finetuning/label_revision_v2/schema.py', 'data/exp_a/build_exp_a.py',
    'data/exp_a/.kaggle/matrix/matrix.py', 'data/exp_a/extraction_v3.py',
    'scripts/exp_a/evaluate_exp_a.py', 'scripts/experiment_io.py',
    'scripts/build_corpus.py', 'scripts/download_sources.py', 'scripts/validate_all.py')


def verify_prepared(data, tokenizer=None):
    """Rebuild every accepted target/prefix from sealed train/dev source records."""
    data = Path(data)
    manifest = read(data / 'manifest.json')
    require(manifest.get('version') == 'exp_a_v2_training_data_1'
            and manifest.get('counts') == dict(train=467, dev=100)
            and manifest.get('label_source') == 'ai_reference'
            and manifest.get('human_review_status') == 'pending', 'Wrong v2 prepared-data contract')
    validate_splits(manifest['split_ids'])
    limits = manifest.get('token_limits', {})
    require(limits.get('verified') is True and limits.get('max_sequence_tokens') == 4096
            and limits.get('max_assistant_tokens') == 2048, 'Pinned-tokenizer preflight required')
    require(manifest.get('protected_v1_verified') == 38 and len(manifest.get('protected_v1_sha256', {})) == 38,
            'Missing protected-v1 verification provenance')
    files = manifest.get('output_sha256')
    verify_files(data, files)
    required = {'train.jsonl', 'dev.jsonl', 'instruction.txt', 'policy.md', 'prompt.md',
                'response_schema.json', 'review_queue.jsonl', 'frozen_split.json', 'prior_review_ids.json',
                'review/review_manifest.json'}
    require(required.issubset(files) and all(name in required or name.startswith('review/') for name in files),
            'Unapproved training input file')
    actual = {p.relative_to(data).as_posix() for p in data.rglob('*') if p.is_file()}
    require(actual == set(files) | {'manifest.json'}, 'Unmanifested/extra training input file')
    hashes = {key: manifest[key] for key in HASH_KEYS}
    require(all(sha256(data / file) == hashes[key] for key, file in zip(HASH_KEYS,
            ('policy.md', 'prompt.md', 'response_schema.json'))), 'Prepared policy/prompt/schema differs')
    require(read(data / 'response_schema.json') == SCHEMA.SCHEMA, 'Prepared response schema differs from validator')
    require(manifest['validator_sha256'] == sha256(HERE.parent / 'label_revision_v2/schema.py')
            and manifest['trainer_sha256'] == sha256(HERE.parent / 'train.py'), 'Validator/trainer code differs')
    require(sha256(data / 'frozen_split.json') == manifest['frozen_split_sha256']
            and read(data / 'frozen_split.json')['split_ids'] == manifest['split_ids']
            and sha256(data / 'review_queue.jsonl') == manifest['review_queue_sha256']
            and sha256(data / 'review/review_manifest.json') == manifest['review_manifest_sha256'],
            'Prepared source-review/split authority differs')
    prior = read(data / 'prior_review_ids.json')
    require(isinstance(prior, list) and all(isinstance(pid, str) for pid in prior), 'Invalid prior review IDs')
    records, _ = validate_reviews(data / 'review', keyed(data / 'review_queue.jsonl'),
        manifest['split_ids'], hashes, prior_ids=prior)
    actual_coverage = dict(independent=sum(r['provenance']['status'] == 'accepted' for r in records.values()),
        source_authored_unreviewed=sum(r['provenance']['status'] == 'source_authored_unreviewed' for r in records.values()))
    require(manifest.get('review_coverage') == actual_coverage, 'Prepared review coverage differs')
    instruction = (data / 'instruction.txt').read_text(encoding='utf-8')
    require(instruction == (data / 'prompt.md').read_text(encoding='utf-8')
            and manifest.get('instruction_sha256') == hashlib.sha256(instruction.encode('utf-8')).hexdigest()
            and manifest.get('rendered_system_sha256') == hashlib.sha256(
                messages(next(iter(records.values()))['paper'], instruction)[0]['content'].encode('utf-8')).hexdigest(),
            'Instruction/rendered system differs from accepted model prompt')
    tokenizer = tokenizer or load_tokenizer()
    require(tokenizer_contract(tokenizer) == manifest['tokenizer'], 'Pinned tokenizer contract differs')
    for split in ('train', 'dev'):
        rows = keyed(data / (split + '.jsonl'))
        require(list(rows) == manifest['split_ids'][split], 'Prepared split/order differs: ' + split)
        observed = []
        for pid, row in rows.items():
            record = records[pid]
            expected = messages(record['paper'], instruction) + [
                dict(role='assistant', content=json.dumps(record['target'], ensure_ascii=False))]
            require(set(row) == {'paper_id', 'messages', 'provenance', 'token_lengths'}
                    and row['messages'] == expected and row['provenance'] == record['provenance'],
                    pid + ': prepared message/label/provenance differs from accepted source review')
            lengths = token_lengths(tokenizer, row)
            require(row['token_lengths'] == lengths, pid + ': prepared token counts differ')
            observed.append(lengths)
        require(limits['observed'][split] == dict(max_sequence=max(v['sequence'] for v in observed),
                max_assistant=max(v['assistant'] for v in observed)), 'Prepared token maxima differ')
    return manifest


def training_settings(manifest):
    return dict(TRAINER.DEFAULTS, train_file='training_data/train.jsonl', dev_file='training_data/dev.jsonl',
        output_dir=OUTPUT, checkpoint_dir=CHECKPOINTS, split_manifest_file='training_data/manifest.json',
        prompt_sha256=manifest['prompt_sha256'], schema_sha256=manifest['schema_sha256'],
        cache_dir='/tmp/exp_a_huggingface', offline=False)


def verify_contract(root, settings, tokenizer=None):
    """Validate the exact release again before any trainer/GPU/output side effects."""
    root = Path(root).resolve()
    require(isinstance(settings, dict) and settings.get('version') == 'exp_a_qlora_v2'
            and settings.get('dataset') == DATASET and settings.get('kernel') == KERNEL
            and settings.get('is_private') is True and settings.get('label_source') == 'ai_reference'
            and settings.get('human_review_status') == 'pending', 'Wrong private v2 dataset/kernel contract')
    require(settings.get('signature') == digest({key: value for key, value in settings.items() if key != 'signature'}),
            'V2 settings signature differs')
    verify_files(root, settings.get('files'))
    data = root / 'training_data'
    manifest = read(data / 'manifest.json')
    require(sha256(data / 'manifest.json') == settings.get('data_manifest_sha256'), 'Training-data manifest differs')
    expected_files = set(CODE_FILES) | {'training_data/manifest.json'} | {
        'training_data/' + name for name in manifest['output_sha256']}
    require(set(settings['files']) == expected_files, 'Runtime bundle contains unapproved/missing inputs')
    config = settings.get('training')
    require(isinstance(config, dict), 'Missing training settings')
    expected = training_settings(manifest)
    optional = {'resume_from_checkpoint', 'reuse_completed'}
    require(set(expected).issubset(config) and set(config).issubset(set(expected) | optional),
            'Unapproved training setting')
    require(all(config[key] == value and type(config[key]) is type(value)
                for key, value in expected.items() if key not in ('cache_dir', 'offline')),
            'V2 training model/revision/hyperparameters/output contract differs')
    require(type(config['offline']) is bool and isinstance(config['cache_dir'], str) and config['cache_dir'],
            'Invalid tokenizer cache/offline setting')
    require('reuse_completed' not in config or type(config['reuse_completed']) is bool, 'Invalid reuse_completed')
    if config.get('resume_from_checkpoint') is not None:
        require(isinstance(config['resume_from_checkpoint'], str)
                and re.fullmatch(r'train_state_v2/checkpoint-[0-9]+', config['resume_from_checkpoint']),
                'Resume must use an explicit v2 checkpoint')
    for name in (OUTPUT, CHECKPOINTS, 'results/v2_training_provenance.json'):
        path = root / name
        require(path.resolve().is_relative_to(root), 'Output path escapes v2 runtime')
        for parent in (path, *path.parents):
            if parent == root:
                break
            if parent.exists():
                require(not parent.is_symlink() and not (getattr(parent.stat(), 'st_file_attributes', 0) & 1024),
                        'Output path is a reparse point')
    tokenizer = tokenizer or load_tokenizer(config['cache_dir'], local_files_only=config['offline'])
    return verify_prepared(data, tokenizer=tokenizer)


def run_training(root, settings, *, tokenizer=None):
    manifest = verify_contract(root, settings, tokenizer=tokenizer)
    result = TRAINER.train(Path(root).resolve(), dict(settings['training']))
    provenance = dict(result, label_source='ai_reference', human_review_status='pending',
        v2_signature=settings['signature'], review_manifest_sha256=manifest['review_manifest_sha256'],
        instruction_sha256=manifest['instruction_sha256'], rendered_system_sha256=manifest['rendered_system_sha256'],
        policy_sha256=manifest['policy_sha256'], prompt_sha256=manifest['prompt_sha256'],
        schema_sha256=manifest['schema_sha256'], tokenizer=manifest['tokenizer'],
        dataset=DATASET, kernel=KERNEL, review_coverage=manifest['review_coverage'], training_only=True, evaluation_performed=False)
    write_json(Path(root) / 'results/v2_training_provenance.json', provenance)
    return provenance


def build(data, destination, *, root=None):
    root = Path(root or ROOT).resolve()
    destination = require_new_v2_directory(destination, root)
    data = Path(data)
    manifest = verify_prepared(data)
    payloads = {'training_data/' + name: safe_file(data, name).read_bytes()
                for name in (*manifest['output_sha256'], 'manifest.json')}
    for name in CODE_FILES:
        payloads[name] = safe_file(ROOT, name).read_bytes()
        compile(payloads[name], name, 'exec')
    settings = dict(version='exp_a_qlora_v2', dataset=DATASET, kernel=KERNEL, is_private=True,
        training=training_settings(manifest), data_manifest_sha256=sha256(data / 'manifest.json'),
        label_source='ai_reference', human_review_status='pending',
        files={name: hashlib.sha256(value).hexdigest() for name, value in payloads.items()})
    settings['signature'] = digest(settings)
    payloads['v2_settings.json'] = (json.dumps(settings, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    dataset, kernel = destination / 'input-dataset', destination / 'kernel'
    dataset.mkdir(parents=True)
    kernel.mkdir()
    bundle = dataset / 'v2_training_bundle.zip.bin'
    with zipfile.ZipFile(bundle, 'w') as archive:
        for name, payload in sorted(payloads.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, payload)
    bundle_sha = sha256(bundle)
    code = (HERE / 'training_kernel.template.py').read_text(encoding='utf-8').replace('__BUNDLE_SHA256__', bundle_sha)
    compile(code, 'run_training.py', 'exec')
    (kernel / 'run_training.py').write_text(code, encoding='utf-8')
    dataset_metadata = dict(id=DATASET, title='Exp A Qwen QLoRA V2 Inputs', is_private=True, licenses=[dict(name='other')])
    kernel_metadata = dict(id=KERNEL, title='Exp A Qwen QLoRA V2', code_file='run_training.py',
        language='python', kernel_type='script', is_private=True, enable_gpu=True, enable_internet=True,
        machine_shape='NvidiaTeslaT4', dataset_sources=[DATASET], competition_sources=[], kernel_sources=[], model_sources=[])
    write_json(dataset / 'dataset-metadata.json', dataset_metadata)
    write_json(kernel / 'kernel-metadata.json', kernel_metadata)
    result = dict(version='exp_a_v2_training_build_1', dataset=DATASET, kernel=KERNEL, is_private=True,
        counts=manifest['counts'], bundle_sha256=bundle_sha, signature=settings['signature'],
        kernel_sha256=sha256(kernel / 'run_training.py'),
        dataset_metadata_sha256=sha256(dataset / 'dataset-metadata.json'),
        kernel_metadata_sha256=sha256(kernel / 'kernel-metadata.json'), settings=settings)
    write_json(destination / 'build_manifest.json', result)
    verify_build(destination)
    return result


def verify_build(destination):
    """Read-only upload gate for bundle, code and private dataset/kernel metadata."""
    destination = Path(destination)
    manifest = read(destination / 'build_manifest.json')
    require(manifest.get('version') == 'exp_a_v2_training_build_1' and manifest.get('dataset') == DATASET
            and manifest.get('kernel') == KERNEL and manifest.get('is_private') is True,
            'Wrong private v2 build identity')
    artifact_hashes = {
        'input-dataset/v2_training_bundle.zip.bin': manifest['bundle_sha256'],
        'input-dataset/dataset-metadata.json': manifest['dataset_metadata_sha256'],
        'kernel/run_training.py': manifest['kernel_sha256'],
        'kernel/kernel-metadata.json': manifest['kernel_metadata_sha256']}
    verify_files(destination, artifact_hashes)
    actual = {p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}
    require(actual == set(artifact_hashes) | {'build_manifest.json'}, 'Unexpected build artifact')
    dataset = read(destination / 'input-dataset/dataset-metadata.json')
    kernel = read(destination / 'kernel/kernel-metadata.json')
    require(dataset.get('id') == DATASET and dataset.get('is_private') is True
            and kernel.get('id') == KERNEL and kernel.get('is_private') is True
            and kernel.get('dataset_sources') == [DATASET] and kernel.get('code_file') == 'run_training.py'
            and kernel.get('enable_gpu') is True and kernel.get('competition_sources') == []
            and kernel.get('kernel_sources') == [] and kernel.get('model_sources') == [],
            'Build private metadata or input identity differs')
    expected_code = (HERE / 'training_kernel.template.py').read_text(encoding='utf-8').replace(
        '__BUNDLE_SHA256__', manifest['bundle_sha256'])
    require((destination / 'kernel/run_training.py').read_text(encoding='utf-8') == expected_code,
            'Training-only kernel differs from reviewed template')
    with zipfile.ZipFile(destination / 'input-dataset/v2_training_bundle.zip.bin') as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) and all(
            name and not name.startswith('/') and '\\' not in name and ':' not in name
            and all(part not in ('', '.', '..') for part in name.split('/')) for name in names),
            'Unsafe/duplicate bundle member')
        settings = json.loads(archive.read('v2_settings.json'))
        require(settings == manifest['settings'] and settings.get('signature') == manifest['signature']
                and settings['signature'] == digest({k: v for k, v in settings.items() if k != 'signature'})
                and settings.get('version') == 'exp_a_qlora_v2' and settings.get('dataset') == DATASET
                and settings.get('kernel') == KERNEL and settings.get('is_private') is True
                and settings.get('label_source') == 'ai_reference' and settings.get('human_review_status') == 'pending',
                'Bundle settings/signature/private identity differs')
        data = json.loads(archive.read('training_data/manifest.json'))
        expected_names = set(CODE_FILES) | {'training_data/manifest.json', 'v2_settings.json'} | {
            'training_data/' + name for name in data['output_sha256']}
        require(set(names) == expected_names and set(settings['files']) == expected_names - {'v2_settings.json'},
                'Bundle contains unapproved/missing data or runtime code')
        require(settings['training'] == training_settings(data), 'Bundle training settings differ')
        require(hashlib.sha256(archive.read('training_data/manifest.json')).hexdigest()
                == settings['data_manifest_sha256'], 'Bundle training manifest differs')
        require(all(hashlib.sha256(archive.read(name)).hexdigest() == expected
                    for name, expected in settings['files'].items()), 'Bundle member checksum differs')
        require(all(settings['files'][name] == sha256(safe_file(ROOT, name)) for name in CODE_FILES),
                'Bundled runtime differs from current reviewed code')
    return manifest
