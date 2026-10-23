"""Exercise the policy A/B runner without loading model weights or networking."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / 'data/exp_a/finetuning/policy_ab/runner.py'


class PolicyABTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.is_file(), 'Policy A/B runner is missing')
        spec = importlib.util.spec_from_file_location('policy_ab_under_test', MODULE)
        self.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runner)
        self.paper = dict(paper_id='P000001', title='ORBIT retrieval', abstract=
            'We introduce ORBIT. It improves recall by 12% on noisy queries.')
        self.value = dict(paper_id='P000001', problem=[], task=[], method=[], dataset=[],
            contribution=[dict(concept='ORBIT improves recall by 12% on noisy queries',
                               evidence_ids=['A0', 'A1'])])

    def test_new_policy_requires_review_and_retains_both_exact_quotes(self):
        calls = []
        def generate(messages, seed):
            calls.append((messages, seed))
            return json.dumps(self.value), dict(usage=dict(input_tokens=10, output_tokens=20), generation_seconds=1)
        record = self.runner.annotate_new(self.paper, 'Use source only.', dict(seed=42, max_attempts=3), generate)
        self.assertEqual(len(calls), 2)
        self.assertEqual([c[1] for c in calls], [45, 46])
        self.assertEqual(record['usage'], dict(input_tokens=20, output_tokens=40))
        self.assertFalse(record['fallback_used'])
        self.assertEqual(record['selection'], self.value)
        self.assertEqual([e['evidence'] for e in record['evidence']['contribution'][0]['evidence']],
            ['We introduce ORBIT.', 'It improves recall by 12% on noisy queries.'])

    def test_invalid_review_is_repaired_without_hiding_format_failure(self):
        invalid = copy.deepcopy(self.value)
        invalid['contribution'][0]['evidence_id'] = invalid['contribution'][0].pop('evidence_ids')[0]
        outputs = iter([self.value, invalid, self.value])
        def generate(messages, seed):
            return json.dumps(next(outputs)), {}
        record = self.runner.annotate_new(self.paper, 'Use source only.', dict(seed=42, max_attempts=3), generate)
        self.assertFalse(record['fallback_used'])
        self.assertEqual(len(record['audit']['attempts']), 3)
        self.assertTrue(record['audit']['attempts'][1]['validation_errors'])
        self.assertFalse(record['audit']['attempts'][1]['schema_valid'])

    def test_failed_grounding_keeps_supported_items_and_raw_failed_claim(self):
        invalid = copy.deepcopy(self.value)
        invalid['contribution'].append(dict(concept='ORBIT improves recall by 99%', evidence_ids=['A0', 'A1']))
        def generate(messages, seed):
            return json.dumps(invalid), {}
        record = self.runner.annotate_new(self.paper, 'Use source only.', dict(seed=42, max_attempts=3), generate)
        self.assertTrue(record['fallback_used'])
        self.assertEqual(record['selection'], self.value)
        self.assertIn('99%', record['audit']['attempts'][0]['raw_output'])
        self.assertTrue(record['audit']['attempts'][0]['schema_valid'])
        self.assertEqual(len(record['audit']['attempts']), 3)

    def test_wrong_paper_and_extra_fields_cannot_pass_validation(self):
        for mutation in ('wrong_id', 'extra_field', 'duplicate'):
            value = copy.deepcopy(self.value)
            if mutation == 'wrong_id':
                value['paper_id'] = 'P000002'
            elif mutation == 'extra_field':
                value['confidence'] = 1
            else:
                value['contribution'] *= 2
            with self.subTest(mutation=mutation):
                result = self.runner.assess_new(json.dumps(value), self.paper)
                self.assertTrue(result['validation_errors'])

    def test_fallback_prefers_supported_draft_over_unreadable_reviews(self):
        invalid = copy.deepcopy(self.value)
        invalid['contribution'] += [dict(concept='ORBIT improves recall by 99%', evidence_ids=['A0', 'A1']),
                                   dict(concept='ORBIT improves recall by 80%', evidence_ids=['A0', 'A1'])]
        outputs = iter([json.dumps(invalid), 'unreadable review', 'unreadable review'])
        record = self.runner.annotate_new(self.paper, 'Use source only.', dict(seed=42, max_attempts=3),
                                         lambda messages, seed: (next(outputs), {}))
        self.assertTrue(record['fallback_used'])
        self.assertEqual(record['selection'], self.value)
        self.assertEqual(record['audit']['selected_attempt'], 1)

    def test_resume_rejects_wrong_arm_paper_or_adapter(self):
        self.assertTrue(hasattr(self.runner, 'load_checkpoint'), 'Arm/paper checkpoint verification is missing')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = dict(signature='test-signature', adapter_manifest_sha256='adapter-hash',
                            files={'instruction_new.txt': 'prompt-hash'})
            original = dict(paper_id='P000001', arm='new_v2_2', adapter_manifest_sha256='adapter-hash',
                            instruction_sha256='prompt-hash')
            path = root / 'results/new_v2_2/records/P000001.json'
            self.runner.shared.save_record(path, original, 'test-signature')
            self.assertEqual(self.runner.load_checkpoint(root, settings, 'new_v2_2', 'P000001'), original)
            for key, value in [('arm', 'old_v3_7'), ('paper_id', 'P000002'),
                               ('adapter_manifest_sha256', 'different'), ('instruction_sha256', 'different')]:
                changed = dict(original, **{key: value})
                self.runner.shared.save_record(path, changed, 'test-signature')
                with self.subTest(key=key), self.assertRaises(ValueError):
                    self.runner.load_checkpoint(root, settings, 'new_v2_2', 'P000001')

    def test_bundle_uses_fresh_balanced_sources_without_reference_labels(self):
        module = MODULE.with_name('build.py')
        self.assertTrue(module.is_file(), 'Policy A/B bundler is missing')
        spec = importlib.util.spec_from_file_location('policy_ab_build_under_test', module)
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as temporary:
            result = builder.build(Path(temporary))
            self.assertEqual(result['counts'], dict(train=20, dev=20))
            self.assertEqual(result['leakage'], dict(test=0, pilot50=0, policy_pilot40=0))
            with zipfile.ZipFile(Path(temporary) / 'input-dataset/policy_ab_bundle.zip.bin') as archive:
                self.assertFalse(any('reference' in name or 'train.jsonl' in name or 'test_' in name
                                     for name in archive.namelist()))
                papers = [json.loads(line) for line in archive.read('model_inputs/papers.jsonl').decode().splitlines()]
                self.assertEqual(len(papers), 40)
                self.assertTrue(all(set(p) == {'paper_id', 'title', 'abstract', 'source'} for p in papers))
                settings = json.loads(archive.read('settings.json'))
                self.assertEqual(settings['model']['model'], 'Qwen/Qwen3-8B')
                self.assertEqual(settings['generation']['max_new_tokens'], 2048)
            metadata = json.loads((Path(temporary) / 'kernel/kernel-metadata.json').read_text())
            self.assertTrue(metadata['is_private'])


if __name__ == '__main__':
    unittest.main()
