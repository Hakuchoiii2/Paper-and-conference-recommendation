"""Behavioral checks for the isolated R1/R2 experiment; no model downloads."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
import hashlib
import base64
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'data/exp_a/.kaggle/matrix'))
import matrix as shared


class ImprovementTests(unittest.TestCase):
    def setUp(self):
        path = ROOT/'data/exp_a/.kaggle/base_improvement/improvement.py'
        self.assertTrue(path.is_file(), 'R1/R2 experiment is not implemented')
        spec = importlib.util.spec_from_file_location('improvement_test', path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.paper = dict(paper_id='P000001', title='Document retrieval',
                          abstract='We use hashing for document retrieval.')
        self.config = dict(prompt_version='3.7', max_attempts=3, max_new_tokens=2048,
                           seed=42, do_sample=False, dataset_resource_filter=True)
        self.good = dict(paper_id='P000001', **{f: [] for f in shared.FACETS})
        self.good['task'] = [dict(concept='document retrieval', evidence_id='A0')]
        self.good['method'] = [dict(concept='hashing', evidence_id='A0')]
        self.bad = copy.deepcopy(self.good)
        self.bad['method'][0]['concept'] = 'invented technique'
        self.cached = dict(attempt=1, stage='extract', seed=45,
                           raw_output=json.dumps(self.bad), usage=dict(input_tokens=100,output_tokens=10),
                           generation_seconds=7.0)

    def run_arm(self, arm, replies, cached=None):
        calls = []
        def generate(messages, seed):
            calls.append(copy.deepcopy(messages))
            return json.dumps(replies[len(calls)-1]), dict(
                usage=dict(input_tokens=200, output_tokens=20), generation_seconds=2.0)
        with tempfile.TemporaryDirectory(dir=ROOT/'.test-tmp') as directory:
            record = self.module.annotate(shared, self.paper, 'BASE INSTRUCTION', self.config,
                dict(model='test'), generate, arm, Path(directory)/'last_failure.json', cached=cached)
        return record, calls

    def test_r1_changes_instruction_only(self):
        record, calls = self.run_arm('R1', [self.good, self.good])
        self.assertEqual(len(calls), 2)
        self.assertIn('BASE INSTRUCTION', calls[0][0]['content'])
        self.assertIn(self.module.EXAMPLES.strip(), calls[0][0]['content'])
        self.assertNotIn('TARGETED REPAIR PACKET', calls[1][-1]['content'])
        self.assertEqual(record['new_cost']['calls'], 2)
        self.assertFalse(record['fallback_used'])

    def test_r2_reuses_exact_draft_and_repairs_with_source_feedback(self):
        frozen = copy.deepcopy(self.cached)
        record, calls = self.run_arm('R2', [self.good], cached=self.cached)
        self.assertEqual(self.cached, frozen)
        self.assertEqual(len(calls), 1)
        self.assertNotIn(self.module.EXAMPLES.strip(), calls[0][0]['content'])
        self.assertIn('TARGETED REPAIR PACKET', calls[0][-1]['content'])
        self.assertIn('invented technique', calls[0][-1]['content'])
        self.assertIn('We use hashing for document retrieval.', calls[0][-1]['content'])
        self.assertEqual(record['audit']['attempt_scores'][0]['raw_output'], self.cached['raw_output'])
        self.assertEqual(record['audit']['attempts_used'], 2)
        self.assertEqual(record['new_cost']['calls'], 1)
        self.assertEqual(record['usage']['output_tokens'], 30)
        self.assertEqual(record['new_cost']['output_tokens'], 20)
        self.assertEqual(record['generation_seconds'], 9.0)
        self.assertFalse(record['fallback_used'])
        self.assertTrue(record['repair_transitions']['invalid_to_valid'])

    def test_r2_cannot_exceed_two_new_calls_when_draft_is_cached(self):
        record, calls = self.run_arm('R2', [self.bad, self.bad], cached=self.cached)
        self.assertEqual(len(calls), 2)
        self.assertEqual(record['audit']['attempts_used'], 3)
        self.assertEqual(record['new_cost']['calls'], 2)
        self.assertTrue(record['fallback_used'])

    def test_wrong_cached_seed_and_unapproved_arm_are_rejected(self):
        wrong = dict(self.cached, seed=999)
        with self.assertRaisesRegex(ValueError, 'seed'):
            self.run_arm('R2', [self.good], cached=wrong)
        with self.assertRaisesRegex(ValueError, 'arm'):
            self.run_arm('R4', [self.good, self.good])

    def test_settings_tampering_stops_before_any_input_is_opened(self):
        with self.assertRaisesRegex(ValueError, 'signature'):
            self.module.verify(Path('not-an-input-directory'),dict(signature='tampered'))

    def test_bootstrap_accepts_hash_verified_records_after_dataset_unzip(self):
        path=ROOT/'data/exp_a/.kaggle/base_improvement/bootstrap.template.py'
        spec=importlib.util.spec_from_file_location('bootstrap_mount_test',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        release=ROOT/'data/exp_a/.kaggle/base_improvement/release_20261022_v1'
        settings=json.loads((release/'settings.json').read_text(encoding='utf-8'))
        module.SETTINGS_B64=base64.b64encode(json.dumps(settings).encode()).decode()
        module.RUNNER_B64=base64.b64encode((ROOT/'data/exp_a/.kaggle/base_improvement/improvement.py').read_bytes()).decode()
        with tempfile.TemporaryDirectory(dir=ROOT/'.test-tmp') as directory:
            mount=Path(directory)/'mount';mount.mkdir()
            import shutil
            shutil.copyfile(ROOT/'data/exp_a/.kaggle/matrix/build_matrix/input-dataset/matrix_bundle.zip.bin',mount/'matrix_bundle.zip.bin')
            shutil.copytree(release/'preflight_project/results/R0/records',mount/'records')
            module.PROJECT=Path(directory)/'project'
            real_path=Path
            def mounted_path(value):
                return mount if str(value)=='/kaggle/input' else real_path(value)
            with patch.object(module,'Path',side_effect=mounted_path), patch.object(module.subprocess,'run',side_effect=RuntimeError('dependency-install-boundary')):
                with self.assertRaisesRegex(RuntimeError,'dependency-install-boundary'):
                    module.main()
            self.assertEqual(len(list((module.PROJECT/'results/R0/records').glob('*.json'))),50)

    def test_bootstrap_refuses_changed_bundle_and_unsafe_paths(self):
        path=ROOT/'data/exp_a/.kaggle/base_improvement/bootstrap.template.py'
        self.assertTrue(path.is_file(),'Safe bootstrap is not implemented')
        spec=importlib.util.spec_from_file_location('improvement_bootstrap_test',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(dir=ROOT/'.test-tmp') as directory:
            root=Path(directory);bundle=root/'bundle.zip'
            with zipfile.ZipFile(bundle,'w') as archive:
                archive.writestr('../outside.txt',b'unsafe')
            settings=dict(source_bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),
                          old_files={},old_settings_sha256='unused')
            with self.assertRaisesRegex(ValueError,'Unsafe'):
                module.extract_original(bundle,root/'project',settings)
            with self.assertRaisesRegex(ValueError,'checksum'):
                module.extract_original(bundle,root/'project',dict(settings,source_bundle_sha256='changed'))
            self.assertFalse((root/'outside.txt').exists())


if __name__ == '__main__':
    unittest.main()
