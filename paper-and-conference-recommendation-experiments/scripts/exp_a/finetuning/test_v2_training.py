"""V2 release gates: accepted sources, exact tokenizer contract, private train-only bundle."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import io
import os
import subprocess
import sys
import zipfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / 'data/exp_a/finetuning/v2/training.py'
FACETS = ('problem', 'task', 'method', 'dataset', 'contribution')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def source(pid='P1', split='train'):
    return dict(paper_id=pid, title='Orbit retrieval', abstract='Orbit retrieves documents. Retrieval improves accuracy.', split=split)


def annotation(pid='P1'):
    return dict(paper_id=pid, problem=[], task=[], method=[
        dict(concept='Orbit retrieves documents Retrieval improves accuracy', evidence_ids=['A0', 'A1'])],
        dataset=[], contribution=[])


def decision(paper, target, hashes):
    return dict(paper_id=paper['paper_id'], source_sha256=digest({k: paper[k] for k in ('paper_id', 'title', 'abstract')}),
        annotation_sha256=digest(target), **hashes, author_id='author_a', reviewer_id='reviewer_b',
        status='accepted', label_source='ai_reference', human_review_status='pending',
        facet_checks={f: dict(evidence='pass', role='pass', qualifiers='pass', coverage='pass',
                              note='Verified against all supplied source sentences.') for f in FACETS},
        unresolved_issues=[], source_notes=[])


class BoundaryTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = None
        if MODULE.is_file():
            spec = importlib.util.spec_from_file_location('v2_training_under_test', MODULE)
            cls.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.module)

    def setUp(self):
        self.assertIsNotNone(self.module, 'The v2 training boundary is not implemented')
        self.paper = source()
        self.target = annotation()
        self.hashes = {key: 'a' * 64 for key in ('policy_sha256', 'prompt_sha256', 'schema_sha256')}
        self.proof = decision(self.paper, self.target, self.hashes)

class ReviewDecisionTests(BoundaryTestCase):
    def test_accepted_multi_evidence_keeps_independent_review_provenance(self):
        proof = self.module.validate_decision(self.paper, self.target, self.proof, self.hashes)
        self.assertEqual(proof['label_source'], 'ai_reference')
        self.assertEqual(proof['human_review_status'], 'pending')
        self.assertEqual(proof['author_id'], 'author_a')
        self.assertEqual(proof['reviewer_id'], 'reviewer_b')
        self.assertEqual(self.target['method'][0]['evidence_ids'], ['A0', 'A1'])

    def test_rejects_self_review_missing_facet_and_resealed_wrong_source(self):
        for mutate in (
            lambda p: p.update(reviewer_id='author_a'),
            lambda p: p.update(reviewer_id='reviewer_a'),
            lambda p: p.update(reviewer_id='AUTHOR_A'),
            lambda p: p['facet_checks'].pop('dataset'),
            lambda p: p['facet_checks']['method'].update(coverage='pending'),
            lambda p: p.update(unresolved_issues=['unsupported qualifier']),
            lambda p: p.update(source_sha256='0' * 64),
            lambda p: p.update(annotation_sha256='0' * 64),
            lambda p: p.update(label_source='student_prediction'),
        ):
            with self.subTest(mutate=mutate):
                proof = copy.deepcopy(self.proof)
                mutate(proof)
                with self.assertRaises(ValueError):
                    self.module.validate_decision(self.paper, self.target, proof, self.hashes)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + '\n', encoding='utf-8')


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(root, *, policy_note=''):
    """Controlled 567-source fixture; never claim these are real project labels."""
    finetuning = root / 'data/exp_a/finetuning'
    v2 = finetuning / 'v2'
    review = v2 / 'review'
    policy = finetuning / 'label_revision_v2'
    for name in ('policy_v2_2.md', 'prompt_v2_2.md', 'response_schema.json'):
        destination = policy / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / 'data/exp_a/finetuning/label_revision_v2' / name).read_bytes())
        if name == 'policy_v2_2.md' and policy_note:
            with destination.open('a', encoding='utf-8') as stream:
                stream.write('\n' + policy_note + '\n')
    hashes = {key: file_sha(policy / name) for key, name in (
        ('policy_sha256', 'policy_v2_2.md'), ('prompt_sha256', 'prompt_v2_2.md'),
        ('schema_sha256', 'response_schema.json'))}
    ids = dict(train=[f'FIX{i:04}' for i in range(467)],
               dev=[f'FIX{i:04}' for i in range(467, 567)],
               test=[f'FIX{i:04}' for i in range(567, 667)])
    frozen = finetuning / 'data/manifest.json'
    write_json(frozen, dict(counts=dict(train=467, dev=100, test=100), split_ids=ids))
    protected = {'data/exp_a/finetuning/data/manifest.json': file_sha(frozen)}
    for index in range(37):
        path = root / f'protected/{index}.txt'
        path.parent.mkdir(exist_ok=True)
        path.write_text(f'protected fixture {index}', encoding='utf-8')
        protected[str(path.relative_to(root)).replace('\\', '/')] = file_sha(path)
    write_json(policy / 'pilot40/protected_v1_sha256.json', protected)
    write_rows(policy / 'pilot40/adjudicated_annotations.jsonl',
               [dict(paper_id=pid) for pid in ids['train'][-40:]])
    papers = [source(pid, split) for split in ('train', 'dev') for pid in ids[split]]
    queue = [dict(paper_id=p['paper_id'], split=p['split'], source={k: p[k] for k in ('paper_id', 'title', 'abstract')})
             for p in papers]
    write_rows(v2 / 'build/train_dev_review_queue.jsonl', queue)
    write_json(v2 / 'build/readiness.json', dict(review_queue_sha256=file_sha(v2 / 'build/train_dev_review_queue.jsonl'),
        frozen_split_sha256=file_sha(frozen), **hashes))
    targets = [annotation(p['paper_id']) for p in papers]
    decisions = [decision(p, a, hashes) for p, a in zip(papers, targets)]
    write_rows(review / 'source_papers.jsonl', papers)
    write_rows(review / 'annotations.jsonl', targets)
    write_rows(review / 'decisions.jsonl', decisions)
    confirmation_ids = ids['train'][:6] + ids['dev'][:6]
    confirmation = review / 'confirmation12'
    subset = [p for p in papers if p['paper_id'] in confirmation_ids]
    subset_targets = [annotation(p['paper_id']) for p in subset]
    write_rows(confirmation / 'sources.jsonl', subset)
    write_rows(confirmation / 'adjudicated_annotations.jsonl', subset_targets)
    write_json(confirmation / 'adjudication.json', dict(status='accepted', note='Controlled fixture only.'))
    write_json(confirmation / 'selection.json', dict(paper_ids=confirmation_ids, **hashes,
        source_sha256=file_sha(confirmation / 'sources.jsonl')))
    for name in ('a', 'b'):
        write_rows(confirmation / f'author_{name}_annotations.jsonl', subset_targets)
        write_rows(confirmation / f'author_{name}_audit.jsonl',
                   [dict(paper_id=p['paper_id'], note='Controlled independent source review fixture.') for p in subset])
    proof_hash = lambda name: file_sha(confirmation / name)
    write_json(confirmation / 'author_a_seal.json', dict(reviewer_identity='author_a', paper_ids=confirmation_ids,
        sha256=dict(sources=proof_hash('sources.jsonl'), selection=proof_hash('selection.json'),
            policy=hashes['policy_sha256'], prompt=hashes['prompt_sha256'], schema=hashes['schema_sha256'],
            annotations=proof_hash('author_a_annotations.jsonl'), audit=proof_hash('author_a_audit.jsonl'))))
    write_json(confirmation / 'author_b_seal.json', dict(reviewer_identity='author_b', paper_ids=confirmation_ids,
        **hashes, sources_sha256=proof_hash('sources.jsonl'), selection_sha256=proof_hash('selection.json'),
        annotations_sha256=proof_hash('author_b_annotations.jsonl'), audit_sha256=proof_hash('author_b_audit.jsonl')))
    for name, other in (('a', 'b'), ('b', 'a')):
        inputs = dict(sources=proof_hash('sources.jsonl'), policy=hashes['policy_sha256'],
            **{f'author_{author}_{kind}': proof_hash(f'author_{author}_{kind}.{suffix}')
               for author in ('a', 'b') for kind, suffix in (('annotations', 'jsonl'), ('audit', 'jsonl'), ('seal', 'json'))})
        write_json(confirmation / f'author_{name}_cross_review.json',
            dict(reviewer_identity=f'author_{name}', reviewed_author=f'author_{other}', input_sha256=inputs))
    candidate_sha = proof_hash('adjudicated_annotations.jsonl')
    for name in ('a', 'b'):
        inputs = dict(sources=proof_hash('sources.jsonl'), selection=proof_hash('selection.json'),
            adjudication=proof_hash('adjudication.json'), policy=hashes['policy_sha256'], prompt=hashes['prompt_sha256'],
            schema_contract=hashes['schema_sha256'],
            **{f'author_{author}_{kind}': proof_hash(f'author_{author}_{kind}.json')
               for author in ('a', 'b') for kind in ('cross_review', 'seal')})
        inputs['candidate' if name == 'a' else 'candidate_annotations'] = candidate_sha
        final = dict(reviewer_identity=f'author_{name}', status='accepted_integrated_revisions',
            remaining_material_issues=[], input_sha256=inputs)
        if name == 'b':
            final['candidate_sha256'] = candidate_sha
        write_json(confirmation / f'author_{name}_final_recheck.json', final)
    write_json(confirmation / 'acceptance.json', dict(status='accepted', **hashes, annotations_sha256=candidate_sha,
        paper_ids=confirmation_ids, independent_author_ids=['author_a', 'author_b'],
        independent_actor_mapping=dict(author_a='author_a', author_b='author_b'), unresolved_material_issues=0,
        files={p.name: file_sha(p) for p in confirmation.iterdir() if p.is_file()}))
    batch = review / 'batches/fixture'
    write_rows(batch / 'sources.jsonl', papers)
    write_rows(batch / 'draft_annotations.jsonl', targets)
    write_rows(batch / 'draft_audit.jsonl', [dict(paper_id=p['paper_id'], note='Controlled fixture only') for p in papers])
    write_rows(batch / 'reviewed_annotations.jsonl', targets)
    write_rows(batch / 'decisions.jsonl', decisions)
    draft = dict(author_id='author_a', paper_ids=[p['paper_id'] for p in papers], **hashes,
        source_sha256=file_sha(batch / 'sources.jsonl'), annotations_sha256=file_sha(batch / 'draft_annotations.jsonl'),
        audit_sha256=file_sha(batch / 'draft_audit.jsonl'))
    write_json(batch / 'draft_seal.json', draft)
    write_json(batch / 'review_seal.json', dict(reviewer_id='reviewer_b', paper_ids=draft['paper_ids'], **hashes,
        draft_seal_sha256=file_sha(batch / 'draft_seal.json'), source_sha256=file_sha(batch / 'sources.jsonl'),
        reviewed_annotations_sha256=file_sha(batch / 'reviewed_annotations.jsonl'),
        decisions_sha256=file_sha(batch / 'decisions.jsonl'), unresolved_material_issues=0))
    batch_names = ('sources.jsonl', 'draft_annotations.jsonl', 'draft_audit.jsonl', 'draft_seal.json',
                   'reviewed_annotations.jsonl', 'decisions.jsonl', 'review_seal.json')
    write_json(batch / 'seal.json', dict(batch_id='fixture', author_id='author_a', reviewer_id='reviewer_b',
        paper_ids=draft['paper_ids'], files={f'batches/fixture/{name}': file_sha(batch / name) for name in batch_names}))
    files = {p.relative_to(review).as_posix(): file_sha(p) for p in review.rglob('*') if p.is_file()}
    write_json(review / 'review_manifest.json', dict(version='exp_a_v2_source_review_1', **hashes,
        label_source='ai_reference', human_review_status='pending', files=files,
        policy_confirmation_file='confirmation12/acceptance.json',
        policy_confirmation_sha256=file_sha(review / 'confirmation12/acceptance.json')))
    return review, ids


class PreparationTests(BoundaryTestCase):
    def test_preparation_keeps_exact_frozen_splits_and_real_token_prefix_eos(self):
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained('Qwen/Qwen3-8B',
            revision='b968826d9c46dd6066d109eabc6255188de91218',
            cache_dir=str(ROOT / 'models/huggingface'), local_files_only=True, token=False, trust_remote_code=False)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review, ids = fixture(root, policy_note='REVIEW_ONLY_POLICY_MARKER')
            output = root / 'data/exp_a/finetuning/v2/training_data'
            manifest = self.module.prepare(review, output, tokenizer=tokenizer, root=root)
            self.assertEqual(manifest['counts'], dict(train=467, dev=100))
            self.assertEqual(manifest['split_ids'], ids)
            self.assertTrue(manifest['token_limits']['verified'])
            self.assertEqual(manifest['protected_v1_verified'], 38)
            prompt = (root / 'data/exp_a/finetuning/label_revision_v2/prompt_v2_2.md').read_text(encoding='utf-8')
            self.assertEqual((output / 'instruction.txt').read_text(encoding='utf-8'), prompt)
            self.assertEqual(manifest['instruction_sha256'], hashlib.sha256(prompt.encode('utf-8')).hexdigest())
            rows = [json.loads(line) for line in (output / 'train.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual([r['paper_id'] for r in rows], ids['train'])
            self.assertEqual(json.loads(rows[0]['messages'][-1]['content'])['method'][0]['evidence_ids'], ['A0', 'A1'])
            inference = self.module.messages(source(ids['train'][0]), (output / 'instruction.txt').read_text(encoding='utf-8'))
            self.assertEqual(rows[0]['messages'][:2], inference)
            self.assertEqual(manifest['rendered_system_sha256'], hashlib.sha256(inference[0]['content'].encode('utf-8')).hexdigest())
            self.assertNotIn('# Quy tắc nhãn năm facet', inference[0]['content'])
            self.assertNotIn('REVIEW_ONLY_POLICY_MARKER', inference[0]['content'])
            self.assertEqual(manifest['policy_sha256'], file_sha(root / 'data/exp_a/finetuning/label_revision_v2/policy_v2_2.md'))
            encoded = self.module.TRAINER.encode_example(tokenizer, rows[0], 4096)
            supervised = [token for token in encoded['labels'] if token != -100]
            self.assertEqual(tokenizer.decode(supervised), rows[0]['messages'][-1]['content'] + '<|im_end|>')
            self.assertEqual(encoded['input_ids'][-1], tokenizer.eos_token_id)
            self.assertFalse((output / 'test_papers.jsonl').exists())
            self.assertFalse((output / 'test_references.jsonl').exists())

    def test_review_gate_rejects_missing_duplicate_reassigned_and_unsealed_inputs(self):
        def change_row(review, file, mutate):
            rows = [json.loads(line) for line in (review / file).read_text(encoding='utf-8').splitlines()]
            mutate(rows)
            write_rows(review / file, rows)
        mutations = (
            lambda r: write_rows(r / 'unrelated_test_papers.jsonl', [source('FIX0567', 'test')]),
            lambda r: change_row(r, 'source_papers.jsonl', lambda rows: rows[0].update(title='Changed source')),
            lambda r: change_row(r, 'source_papers.jsonl', lambda rows: rows[0].update(split='dev')),
            lambda r: change_row(r, 'annotations.jsonl', lambda rows: rows.pop()),
            lambda r: change_row(r, 'annotations.jsonl', lambda rows: rows.append(rows[0])),
            lambda r: write_json(r / 'confirmation12/acceptance.json',
                                dict(self.module.read(r / 'confirmation12/acceptance.json'), status='pending')),
            lambda r: write_json(r / 'batches/fixture/review_seal.json',
                                dict(self.module.read(r / 'batches/fixture/review_seal.json'), unresolved_material_issues=1)),
            lambda r: write_json(r / 'batches/fixture/seal.json',
                                dict(self.module.read(r / 'batches/fixture/seal.json'), paper_ids=['FIX0567'])),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as directory:
                review, ids = fixture(Path(directory))
                mutate(review)
                # Re-sign the outer manifest: inner lineage and frozen-source checks must still reject.
                manifest = self.module.read(review / 'review_manifest.json')
                manifest['files'] = {p.relative_to(review).as_posix(): file_sha(p)
                                     for p in review.rglob('*') if p.is_file() and p.name != 'review_manifest.json'}
                manifest['policy_confirmation_sha256'] = manifest['files']['confirmation12/acceptance.json']
                write_json(review / 'review_manifest.json', manifest)
                queue = self.module.keyed(review.parent / 'build/train_dev_review_queue.jsonl')
                with self.assertRaises(ValueError):
                    self.module.validate_reviews(review, queue, ids, {key: manifest[key] for key in self.module.HASH_KEYS})

    def test_real_tokenizer_rejects_sequence_and_assistant_overflow_without_truncation(self):
        tokenizer = self.module.load_tokenizer()
        base = [dict(role='system', content='Return JSON.'), dict(role='user', content='Source')]
        row = dict(paper_id='overlong', provenance={'fixture': True}, messages=base + [
            dict(role='assistant', content=json.dumps({'value': ' x' * 2200}))])
        with self.assertRaisesRegex(ValueError, '2048'):
            self.module.token_lengths(tokenizer, row)
        row['messages'][1]['content'] = ' source' * 5000
        row['messages'][-1]['content'] = '{}'
        with self.assertRaisesRegex(ValueError, '4096.*truncation forbidden'):
            self.module.token_lengths(tokenizer, row)

    def test_deterministic_private_bundle_runtime_gates_and_training_only_kernel(self):
        self.assertTrue(callable(getattr(self.module, 'build', None)), 'V2 private training packaging is not implemented')
        self.assertTrue(callable(getattr(self.module, 'verify_build', None)), 'V2 build metadata gate is not implemented')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review, ids = fixture(root)
            v2 = root / 'data/exp_a/finetuning/v2'
            data = v2 / 'training_data'
            tokenizer = self.module.load_tokenizer()
            self.module.prepare(review, data, tokenizer=tokenizer, root=root)
            first = self.module.build(data, v2 / 'training_build_a', root=root)
            second = self.module.build(data, v2 / 'training_build_b', root=root)
            self.assertEqual(first['bundle_sha256'], second['bundle_sha256'])
            self.assertEqual(first['dataset'], 'htnkhi/exp-a-qwen-qlora-v2-inputs')
            dataset = v2 / 'training_build_a/input-dataset'
            kernel = v2 / 'training_build_a/kernel'
            self.assertIs(json.loads((dataset / 'dataset-metadata.json').read_text())['is_private'], True)
            self.assertIs(json.loads((kernel / 'kernel-metadata.json').read_text())['is_private'], True)
            self.module.verify_build(v2 / 'training_build_a')
            metadata_path = kernel / 'kernel-metadata.json'
            original_metadata = metadata_path.read_bytes()
            metadata = json.loads(original_metadata)
            metadata['is_private'] = False
            write_json(metadata_path, metadata)
            with self.assertRaises(ValueError):
                self.module.verify_build(v2 / 'training_build_a')
            metadata_path.write_bytes(original_metadata)
            bundle = dataset / 'v2_training_bundle.zip.bin'
            with zipfile.ZipFile(bundle) as archive:
                names = archive.namelist()
                self.assertEqual(len(names), len(set(names)))
                self.assertFalse(any('test_papers' in n or 'test_references' in n or
                                     n.endswith(('.safetensors', '.bin', '.pt', '.pth')) for n in names))
            spec = importlib.util.spec_from_file_location('v2_built_training_kernel', kernel / 'run_training.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            unpacked = root / 'runtime'
            module.extract_bundle(bundle, unpacked, first['bundle_sha256'])

            smoke = """import importlib.util,json,pathlib,sys
root=pathlib.Path(sys.argv[1]).resolve()
path=root/'data/exp_a/finetuning/v2/training.py'
spec=importlib.util.spec_from_file_location('isolated_v2_training',path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert pathlib.Path(module.TRAINER.__file__).resolve()==root/'data/exp_a/finetuning/train.py'
attention=module.TRAINER.install_attention(root)
assert attention=='matrix_efficient_no_gqa'
print(json.dumps(dict(attention=attention,trainer=str(pathlib.Path(module.TRAINER.__file__).resolve()))))
"""
            environment = dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                               CUDA_VISIBLE_DEVICES='', USE_TF='0', PYTHONDONTWRITEBYTECODE='1')
            command = [sys.executable, '-X', 'utf8', '-I', '-B', '-c', smoke, str(unpacked)]
            isolated = subprocess.run(command, capture_output=True, text=True, env=environment, timeout=60)
            self.assertEqual(isolated.returncode, 0, isolated.stdout + isolated.stderr)
            self.assertEqual(json.loads(isolated.stdout.splitlines()[-1])['attention'], 'matrix_efficient_no_gqa')
            helper = unpacked / 'scripts/experiment_io.py'
            hidden = helper.with_suffix('.saved')
            helper.rename(hidden)
            try:
                missing = subprocess.run(command, capture_output=True, text=True, env=environment, timeout=60)
                self.assertNotEqual(missing.returncode, 0)
                self.assertIn('experiment_io', missing.stderr)
            finally:
                hidden.rename(helper)
            settings = json.loads((unpacked / 'v2_settings.json').read_text(encoding='utf-8'))
            self.module.verify_contract(unpacked, settings, tokenizer=tokenizer)
            for edit in (lambda s: s['training'].update(output_dir='adapters/qwen3-8b-facets-qlora-v1'),
                         lambda s: s.update(is_private=False),
                         lambda s: s['training'].update(epochs=1)):
                altered = copy.deepcopy(settings)
                edit(altered)
                altered['signature'] = digest({k: v for k, v in altered.items() if k != 'signature'})
                with self.assertRaises(ValueError):
                    self.module.verify_contract(unpacked, altered, tokenizer=tokenizer)
            # Only the expensive GPU train operation is replaced; all real release/runtime gates run.
            def train_cpu_stub(runtime_root, config):
                self.assertEqual(config['output_dir'], 'adapters/qwen3-8b-facets-qlora-v2')
                self.assertEqual(config['checkpoint_dir'], 'train_state_v2')
                self.assertNotIn('adapter_path', config)
                return dict(status='complete', counts=dict(train=467, dev=100))
            with patch.object(self.module.TRAINER, 'train', side_effect=train_cpu_stub):
                result = self.module.run_training(unpacked, settings, tokenizer=tokenizer)
            self.assertEqual(result['label_source'], 'ai_reference')
            self.assertEqual(result['human_review_status'], 'pending')
            self.assertTrue((unpacked / 'results/v2_training_provenance.json').is_file())
            self.assertFalse((unpacked / 'results/experiment_summary.json').exists())
            malicious = root / 'unsafe.zip'
            with zipfile.ZipFile(malicious, 'w') as archive:
                archive.writestr('../escaped.txt', 'unsafe')
            with self.assertRaises(ValueError):
                module.extract_bundle(malicious, root / 'unsafe_out', file_sha(malicious))
            self.assertFalse((root / 'escaped.txt').exists())
            # A new unmanifested evaluation file must block packaging, even with valid existing hashes.
            (data / 'test_papers.jsonl').write_text('{}\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                self.module.build(data, v2 / 'training_build_c', root=root)

    def test_confirmation_support_cannot_be_deleted_or_resealed_after_acceptance(self):
        mutations = (
            lambda c: (c / 'author_a_final_recheck.json').unlink(),
            lambda c: (c / 'author_b_seal.json').unlink(),
            lambda c: write_json(c / 'author_a_final_recheck.json',
                                dict(self.module.read(c / 'author_a_final_recheck.json'), status='pending')),
            lambda c: write_json(c / 'author_b_final_recheck.json',
                                dict(self.module.read(c / 'author_b_final_recheck.json'), candidate_sha256='0' * 64)),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as directory:
                review, ids = fixture(Path(directory))
                confirmation = review / 'confirmation12'
                mutate(confirmation)
                accepted = self.module.read(confirmation / 'acceptance.json')
                accepted['files'] = {p.name: file_sha(p) for p in confirmation.iterdir()
                                     if p.is_file() and p.name != 'acceptance.json'}
                write_json(confirmation / 'acceptance.json', accepted)
                manifest = self.module.read(review / 'review_manifest.json')
                manifest['files'] = {p.relative_to(review).as_posix(): file_sha(p)
                                     for p in review.rglob('*') if p.is_file() and p.name != 'review_manifest.json'}
                manifest['policy_confirmation_sha256'] = file_sha(confirmation / 'acceptance.json')
                write_json(review / 'review_manifest.json', manifest)
                queue = self.module.keyed(review.parent / 'build/train_dev_review_queue.jsonl')
                with self.assertRaises(ValueError):
                    self.module.validate_reviews(review, queue, ids, {key: manifest[key] for key in self.module.HASH_KEYS})

    def test_offline_tokenizer_load_uses_pinned_snapshot_without_offline_environment(self):
        script = """import importlib.util,json,pathlib,socket,sys
import huggingface_hub
def forbidden(*args,**kwargs):
    raise AssertionError('Offline tokenizer attempted metadata/network lookup')
huggingface_hub.model_info=forbidden
huggingface_hub.HfApi.model_info=forbidden
socket.create_connection=forbidden
socket.socket.connect=forbidden
path=pathlib.Path(sys.argv[1])
spec=importlib.util.spec_from_file_location('offline_v2_boundary',path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
tokenizer=module.load_tokenizer()
print(json.dumps(dict(snapshot=pathlib.Path(tokenizer.name_or_path).name,eos=tokenizer.eos_token_id,
                      vocabulary=len(tokenizer.get_vocab()))))
"""
        environment = dict(os.environ, CUDA_VISIBLE_DEVICES='', USE_TF='0', PYTHONDONTWRITEBYTECODE='1')
        environment.pop('HF_HUB_OFFLINE', None)
        environment.pop('TRANSFORMERS_OFFLINE', None)
        result = subprocess.run([sys.executable, '-X', 'utf8', '-I', '-B', '-c', script, str(MODULE)],
            capture_output=True, text=True, env=environment, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        observed = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(observed['snapshot'], 'b968826d9c46dd6066d109eabc6255188de91218')
        self.assertEqual(observed['eos'], 151645)
        self.assertEqual(observed['vocabulary'], 151669)




class SampledReviewTests(BoundaryTestCase):
    def test_unreviewed_provenance_is_explicit_and_never_self_accepted(self):
        proof = dict(self.proof, status='source_authored_unreviewed', reviewer_id=None)
        proof.pop('facet_checks')
        with self.assertRaises(ValueError):
            self.module.validate_decision(self.paper, self.target, proof, self.hashes)
        self.module.validate_decision(self.paper, self.target, proof, self.hashes, allow_unreviewed=True)
        for update in (dict(reviewer_id='author_a'), dict(status='accepted'),
                       dict(unresolved_issues=['unsupported claim'])):
            with self.assertRaises(ValueError):
                self.module.validate_decision(self.paper, self.target, dict(proof, **update),
                                              self.hashes, allow_unreviewed=True)

    def test_sampled_batch_lineage_and_review_coverage_cannot_be_inflated(self):
        m = self.module
        with tempfile.TemporaryDirectory() as directory:
            review, ids = fixture(Path(directory))
            manifest = m.read(review / 'review_manifest.json')
            hashes = {key: manifest[key] for key in m.HASH_KEYS}
            batch = review / 'batches/fixture'
            all_rows = {name: list(m.keyed(batch / name).values()) for name in
                ('sources.jsonl', 'draft_annotations.jsonl', 'draft_audit.jsonl',
                 'reviewed_annotations.jsonl', 'decisions.jsonl')}
            sampled_ids = set(ids['train'][:54] + ids['dev'][:6])
            independent = sorted(sampled_ids)
            for name, rows in all_rows.items():
                write_rows(batch / name, [row for row in rows if row['paper_id'] in sampled_ids])
            sampled = list(m.keyed(batch / 'sources.jsonl'))
            draft = dict(author_id='author_a', paper_ids=sampled, **hashes,
                source_sha256=file_sha(batch / 'sources.jsonl'),
                annotations_sha256=file_sha(batch / 'draft_annotations.jsonl'),
                audit_sha256=file_sha(batch / 'draft_audit.jsonl'))
            write_json(batch / 'draft_seal.json', draft)
            write_json(batch / 'review_seal.json', dict(reviewer_id='reviewer_b', paper_ids=sampled,
                **hashes, unresolved_material_issues=0, draft_seal_sha256=file_sha(batch / 'draft_seal.json'),
                source_sha256=file_sha(batch / 'sources.jsonl'),
                reviewed_annotations_sha256=file_sha(batch / 'reviewed_annotations.jsonl'),
                decisions_sha256=file_sha(batch / 'decisions.jsonl')))
            write_json(batch / 'seal.json', dict(batch_id='fixture', author_id='author_a',
                reviewer_id='reviewer_b', paper_ids=sampled,
                files={f'batches/fixture/{name}':file_sha(batch/name) for name in m.BATCH_FILES}))
            unreviewed = review / 'batches/unreviewed'
            pending_decisions = []
            for name in ('sources.jsonl', 'draft_annotations.jsonl', 'draft_audit.jsonl'):
                write_rows(unreviewed / name, [row for row in all_rows[name] if row['paper_id'] not in sampled_ids])
            for proof in all_rows['decisions.jsonl']:
                if proof['paper_id'] in sampled_ids:
                    continue
                proof = dict(proof, status='source_authored_unreviewed', reviewer_id=None)
                proof.pop('facet_checks')
                pending_decisions.append(proof)
            write_rows(unreviewed / 'decisions.jsonl', pending_decisions)
            pending_ids = list(m.keyed(unreviewed / 'sources.jsonl'))
            write_json(unreviewed / 'draft_seal.json', dict(author_id='author_a',paper_ids=pending_ids,
                **hashes, source_sha256=file_sha(unreviewed/'sources.jsonl'),
                annotations_sha256=file_sha(unreviewed/'draft_annotations.jsonl'),
                audit_sha256=file_sha(unreviewed/'draft_audit.jsonl')))
            names=('sources.jsonl','draft_annotations.jsonl','draft_audit.jsonl','draft_seal.json','decisions.jsonl')
            write_json(unreviewed/'seal.json',dict(batch_id='unreviewed',author_id='author_a',reviewer_id=None,
                review_status='source_authored_unreviewed',paper_ids=pending_ids,
                files={f'batches/unreviewed/{name}':file_sha(unreviewed/name) for name in names}))
            write_rows(review/'decisions.jsonl', [row for row in all_rows['decisions.jsonl']
                if row['paper_id'] in sampled_ids]+pending_decisions)
            scope=m.read(ROOT/'data/exp_a/finetuning/v2/review/review_scope_v2.json')
            write_json(review/'review_scope_v2.json',scope)
            manifest.update(version='exp_a_v2_source_review_2',independent_review_paper_ids=independent,
                            difficult_paper_ids=[])
            def reseal():
                manifest['files']={p.relative_to(review).as_posix():file_sha(p)
                    for p in review.rglob('*') if p.is_file() and p.name!='review_manifest.json'}
                write_json(review/'review_manifest.json',manifest)
            reseal()
            queue=m.keyed(Path(directory)/'data/exp_a/finetuning/v2/build/train_dev_review_queue.jsonl')
            records,_=m.validate_reviews(review,queue,ids,hashes)
            self.assertEqual(sum(v['provenance']['status']=='accepted' for v in records.values()),60)
            self.assertEqual(sum(v['provenance']['reviewer_id'] is None for v in records.values()),507)
            # A genuine selected review can coexist with untouched unreviewed drafts.
            mixed_decisions = list(m.keyed(unreviewed/'decisions.jsonl').values())
            chosen = mixed_decisions[0]['paper_id']
            chosen_paper = m.keyed(unreviewed/'sources.jsonl')[chosen]
            chosen_target = m.keyed(unreviewed/'draft_annotations.jsonl')[chosen]
            mixed_decisions[0] = decision(chosen_paper, chosen_target, hashes)
            write_rows(unreviewed/'decisions.jsonl',mixed_decisions)
            write_rows(unreviewed/'reviewed_annotations.jsonl',list(m.keyed(unreviewed/'draft_annotations.jsonl').values()))
            write_json(unreviewed/'review_seal.json',dict(paper_ids=pending_ids,**hashes,
                draft_seal_sha256=file_sha(unreviewed/'draft_seal.json'),
                source_sha256=file_sha(unreviewed/'sources.jsonl'),
                reviewed_annotations_sha256=file_sha(unreviewed/'reviewed_annotations.jsonl'),
                decisions_sha256=file_sha(unreviewed/'decisions.jsonl'),unresolved_material_issues=0))
            mixed_seal=m.read(unreviewed/'seal.json');mixed_seal['review_status']='sampled_review'
            for name in ('decisions.jsonl','reviewed_annotations.jsonl','review_seal.json'):
                mixed_seal['files']['batches/unreviewed/'+name]=file_sha(unreviewed/name)
            write_json(unreviewed/'seal.json',mixed_seal)
            write_rows(review/'decisions.jsonl',[row for row in all_rows['decisions.jsonl']
                if row['paper_id'] in sampled_ids]+mixed_decisions)
            independent=sorted(independent+[chosen])
            manifest['independent_review_paper_ids']=independent
            reseal()
            records,_=m.validate_reviews(review,queue,ids,hashes)
            self.assertEqual(sum(v['provenance']['status']=='accepted' for v in records.values()),61)
            manifest['independent_review_paper_ids']=sorted(ids['train']+ids['dev'])
            reseal()
            with self.assertRaisesRegex(ValueError,'coverage claim'):
                m.validate_reviews(review,queue,ids,hashes)
            manifest['independent_review_paper_ids']=independent
            manifest['difficult_paper_ids']=[pending_ids[1]]
            reseal()
            with self.assertRaisesRegex(ValueError,'Difficult source'):
                m.validate_reviews(review,queue,ids,hashes)
            manifest['difficult_paper_ids']=[]
            bad=m.read(unreviewed/'seal.json');bad['author_id']='another_actor'
            write_json(unreviewed/'seal.json',bad);reseal()
            with self.assertRaisesRegex(ValueError,'actor/cohort'):
                m.validate_reviews(review,queue,ids,hashes)


if __name__ == '__main__':
    unittest.main()
