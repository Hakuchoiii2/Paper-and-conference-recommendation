"""Dual-GPU scheduling and real export/merge; replace only GPU subprocess work."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'data/exp_a'))
import build_exp_a as base


class DualT4Checks(unittest.TestCase):
    def setUp(self):
        path = ROOT / 'data/exp_a/.kaggle/pilot/dual_t4.py'
        self.assertTrue(path.is_file(), 'Dual-T4 worker orchestration is missing')
        spec = importlib.util.spec_from_file_location('dual_t4', path)
        self.dual = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.dual)

    def test_odd_cohort_splits_without_losing_or_overlapping_positions(self):
        config = dict(paper_ids=['P000001','P000002','P000003','P000004','P000005'],
                      paper_range=[1, None], output_dir='data/exp_a/pilot', seed=42)
        first, second = self.dual.worker_configs(config)
        self.assertEqual(first['paper_range'], [1, 3])
        self.assertEqual(second['paper_range'], [4, 5])
        self.assertEqual(config['paper_range'], [1, None])
        self.assertEqual(first['paper_ids'], config['paper_ids'])
        self.assertNotEqual(first['output_dir'], second['output_dir'])
        self.assertEqual((first['seed'], second['seed']), (42, 42))

    def fixture(self, root):
        papers = [dict(paper_id=f'P{i:06}', source='csfcube', source_id=str(i),
                       title='Document retrieval', abstract='We use ranking for document retrieval.',
                       year=None, domain='information_technology', scope_evidence=['test-only fixture'])
                  for i in range(1, 7)]
        base.write_jsonl(root / 'data/processed/papers.jsonl', papers)
        (root / 'prompt.md').write_text('Test-only extraction.', encoding='utf-8')
        return dict(corpus='data/processed/papers.jsonl', paper_ids=[p['paper_id'] for p in papers],
            paper_range=[1, None], output_dir='data/exp_a/pilot', model='Qwen/test-only', revision='test-only',
            device='cuda', load_in_4bit=True, cache_dir='models', prompt='prompt.md', guideline='prompt.md',
            prompt_version='3.7', guideline_version='3.1', extraction_protocol='two_pass_v3', do_sample=False,
            max_new_tokens=1024, max_attempts=3, temperature=0.7, top_p=0.8, top_k=20, seed=42)

    def test_two_workers_start_before_wait_and_merge_verified_disjoint_outputs(self):
        events = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); config = self.fixture(root)
            def launch(command, *, env):
                gpu = env['CUDA_VISIBLE_DEVICES']; events.append('launch'+gpu)
                worker = json.loads(Path(command[command.index('--worker-config')+1]).read_text(encoding='utf-8'))
                def load(worker_root, worker_config):
                    def extract(paper, instruction):
                        import extraction_v3 as v3
                        selection = dict(paper_id=paper['paper_id'], **{f: [] for f in base.FACET_NAMES})
                        selection['method'] = [dict(concept='ranking', evidence_id='A0')]
                        return v3.annotate(paper, instruction, worker_config,
                            dict(model='Qwen/test-only', model_revision='test-only', physical_gpu_index=int(gpu)),
                            lambda messages, seed: (json.dumps(selection), dict(usage={})),
                            worker_root / worker_config['output_dir'] / 'last_failure.json')
                    return extract
                with patch.object(base, 'load_qwen', side_effect=load):
                    base.generate(root, worker)
                class Process:
                    def wait(self):
                        events.append('wait'+gpu)
                        return 0
                    def poll(self): return 0
                return Process()
            with patch.object(self.dual.subprocess, 'Popen', side_effect=launch):
                manifest = self.dual.run_workers(root, config, gpu_count=2)
            self.assertEqual(events, ['launch0','launch1','wait0','wait1'])
            self.assertEqual(manifest['count'], 6)
            self.assertEqual(manifest['status'], 'complete')
            notes = base.read_jsonl(root / config['output_dir'] / 'annotation_metadata.jsonl')
            self.assertEqual([n['paper_id'] for n in notes], config['paper_ids'])
            self.assertEqual([n['physical_gpu_index'] for n in notes], [0,0,0,1,1,1])
            self.assertTrue(all(n['request_parameters']['review_application'] == 'coverage_preserving_v3_7'
                                and 'applied_output' in n['attempt_scores'][-1] for n in notes))
            base.check_outputs(root, config)
            with patch.object(self.dual.subprocess, 'Popen', side_effect=AssertionError('Unexpected resume inference')):
                self.assertEqual(self.dual.run_workers(root, config, gpu_count=2), manifest)

    def test_one_gpu_fails_before_launching_or_publishing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); config = self.fixture(root)
            with patch.object(self.dual.subprocess, 'Popen', side_effect=AssertionError('Unexpected worker launch')):
                with self.assertRaisesRegex(ValueError, 'two|2'):
                    self.dual.run_workers(root, config, gpu_count=1)
            self.assertFalse((root / config['output_dir']).exists())

    def test_failed_worker_cannot_publish_a_complete_merged_output(self):
        class FailedProcess:
            def wait(self): return 1
            def poll(self): return 1
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); config = self.fixture(root)
            with patch.object(self.dual.subprocess, 'Popen', return_value=FailedProcess()):
                with self.assertRaisesRegex(RuntimeError, 'worker'):
                    self.dual.run_workers(root, config, gpu_count=2)
            self.assertFalse((root / config['output_dir'] / 'manifest.json').exists())


if __name__ == '__main__':
    unittest.main()
