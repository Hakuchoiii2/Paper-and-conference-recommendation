import importlib.util
import hashlib
import json
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parent


class Gold400Tests(unittest.TestCase):
    def module(self):
        self.assertTrue((HERE / 'prepare.py').exists(), 'gold400 preparation is missing')
        spec = importlib.util.spec_from_file_location('gold400_prepare_test', HERE / 'prepare.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_split_is_deterministic_complete_and_disjoint(self):
        m = self.module()
        papers = [dict(paper_id=f'P{i:06}', title=f'Title {i}', abstract=f'Abstract {i}') for i in range(400)]
        a = m.split_papers(papers)
        self.assertEqual(a, m.split_papers(list(reversed(papers))))
        self.assertEqual([len(a[s]) for s in ('train', 'valid', 'test')], [280, 60, 60])
        self.assertEqual(len(set(sum(a.values(), []))), 400)
        papers[1]['abstract'] = papers[0]['abstract']
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            m.split_papers(papers)

    def test_target_preserves_gold_and_rejects_wrong_evidence(self):
        m = self.module()
        facets = ('problem', 'task', 'method', 'dataset', 'contribution')
        gold = dict(paper_id='P000001', facets={f: [] for f in facets})
        gold['facets']['method'] = ['a method']
        proof = dict(paper_id='P000001', evidence={f: [] for f in facets})
        proof['evidence']['method'] = [dict(concept='a method', evidence_id='A0', evidence='We use a method.')]
        target = m.target(gold, proof, {'A0': dict(evidence='We use a method.')})
        self.assertEqual(target['method'], [dict(concept='a method', evidence_id='A0')])
        proof['evidence']['method'][0]['evidence'] = 'A different sentence.'
        with self.assertRaisesRegex(ValueError, 'Evidence'):
            m.target(gold, proof, {'A0': dict(evidence='We use a method.')})

    def test_checkpoint_selection_uses_only_valid_f1_recall_and_earliest(self):
        spec = importlib.util.spec_from_file_location('gold400_runtime_test', HERE / 'runtime.py')
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        def result(step, f1, recall, split='valid'):
            return dict(split=split, arm=f'checkpoint-{step}', micro=dict(f1=f1, recall=recall))
        candidates = [result(35, .4, .5), result(70, .45, .49), result(105, .45, .49)]
        self.assertEqual(m.choose_checkpoint(candidates)['arm'], 'checkpoint-70')
        candidates[2]['micro']['recall'] = .51
        self.assertEqual(m.choose_checkpoint(candidates)['arm'], 'checkpoint-105')
        with self.assertRaisesRegex(ValueError, 'validation only'):
            m.choose_checkpoint([result(35, .9, .9, split='test')])

    def test_bootstrap_rejects_path_traversal_and_tampering(self):
        spec = importlib.util.spec_from_file_location('gold400_bootstrap_test', HERE / 'bootstrap.py')
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory(dir=HERE) as temporary:
            root = Path(temporary)
            bundle = root / 'bundle.zip'
            with zipfile.ZipFile(bundle, 'w') as z:
                z.writestr('../escape', 'untrusted')
            m.BUNDLE_SHA256 = hashlib.sha256(bundle.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                m.extract(bundle, root / 'extracted')
            with zipfile.ZipFile(bundle, 'w') as z:
                z.writestr('settings.json', json.dumps(dict(files={'runtime.py': '0' * 64})))
                z.writestr('runtime.py', 'tampered')
            m.BUNDLE_SHA256 = hashlib.sha256(bundle.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, 'Changed bundle'):
                m.extract(bundle, root / 'extracted')

    def test_release_hashes_and_test_isolation(self):
        m = self.module()
        spec = importlib.util.spec_from_file_location('gold400_runtime_verify_test', HERE / 'runtime.py')
        runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runtime)
        project = m.RELEASE / 'project'
        self.assertTrue(project.exists(), 'Build release before final package verification')
        settings = runtime.verify(project)
        test_ids = set(settings['splits']['test'])
        for split in ('train', 'valid'):
            data = runtime.rows(project / f'training_data/{split}.jsonl')
            self.assertFalse(test_ids & {r['paper_id'] for r in data})
        for name in ('runtime.py', 'gold_policy.py', 'train.py'):
            compile((project / name).read_text(encoding='utf-8'), name, 'exec')
        self.assertEqual((project / 'runtime.py').read_bytes(), (HERE / 'runtime.py').read_bytes())
        self.assertEqual(settings['metrics'], ['precision', 'recall', 'f1', 'macro_f1'])

    def test_packaged_full_pipeline_preserves_cola_paraphrases_and_symbols(self):
        m = self.module()
        spec = importlib.util.spec_from_file_location('gold400_full_policy_test', m.RELEASE / 'project/gold_policy.py')
        policy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(policy)
        shared = policy.load_shared(m.RELEASE / 'project')
        paper = dict(paper_id='P999008', title='bAbI and bAbI+', abstract='We use the Corpus of Linguistic Acceptability (CoLA).')
        selected = dict(paper_id=paper['paper_id'], **{f: [] for f in shared.FACETS})
        selected['dataset'] = [dict(concept='Corpus of Linguistic Acceptability', evidence_id='A0'),
                               *[dict(concept=x, evidence_id='T0') for x in ('bAbI+', 'bAbI')]]
        calls = []
        def generate(messages, seed):
            calls.append(messages)
            reply = selected if len(calls) < 3 else dict(paper_id=paper['paper_id'], task=[], method=[])
            return json.dumps(reply), dict(usage=dict(input_tokens=10, output_tokens=20), generation_seconds=1, reached_token_limit=False)
        config = dict(seed=42, max_attempts=3, max_new_tokens=2048, do_sample=False, prompt_version='3.7', dataset_resource_filter=True)
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            record = policy.annotate_fresh(shared, paper, 'Source-supported paraphrases are allowed.', config, {}, generate, Path(directory), signature='test')
        self.assertEqual(record['facets']['dataset'], ['Corpus of Linguistic Acceptability', 'bAbI+', 'bAbI'])
        self.assertEqual(record['audit']['validation_errors'], [])
        self.assertEqual(record['audit']['validator_policy'], 'source_attributed_paraphrase_v1')
        self.assertEqual(len(calls), 3)

    def test_packaged_gold400_roundtrip_preserves_all_reviewed_labels(self):
        m = self.module()
        policy = m.load('gold400_roundtrip_policy_test', m.RELEASE / 'project/gold_policy.py')
        shared = policy.load_shared(m.RELEASE / 'project')
        origin = m.ROOT / 'data/exp_a/ground_truth/gold_review'
        papers = {r['paper_id']: r for r in m.rows(origin/'review_papers.jsonl')}
        gold = {r['paper_id']: r for r in m.rows(origin/'human_gold.jsonl')}
        config = dict(seed=42, max_attempts=3, max_new_tokens=2048, do_sample=False, prompt_version='3.7', dataset_resource_filter=True)
        with tempfile.TemporaryDirectory(dir=HERE) as directory, redirect_stdout(io.StringIO()):
            for proof in m.rows(origin/'gpt_review_evidence.jsonl'):
                pid = proof['paper_id']
                selected = dict(paper_id=pid, **{f: [{k: item[k] for k in ('concept', 'evidence_id')} for item in proof['evidence'][f]] for f in shared.FACETS})
                calls = []
                def generate(messages, seed):
                    calls.append(messages)
                    answer = selected if len(calls) < 3 else dict(paper_id=pid, task=[], method=[])
                    return json.dumps(answer), dict(usage=dict(input_tokens=10, output_tokens=20), generation_seconds=1, reached_token_limit=False)
                result = policy.annotate_fresh(shared, papers[pid], 'Faithful source-supported paraphrases.', config, {}, generate, Path(directory)/pid, signature='test')
                self.assertEqual({f: result['facets'][f] for f in shared.FACETS}, gold[pid]['facets'], pid)
                self.assertEqual(result['audit']['validation_errors'], [], pid)
                self.assertEqual(len(calls), 3, pid)


if __name__ == '__main__':
    unittest.main()
