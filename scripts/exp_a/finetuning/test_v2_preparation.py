"""The v2 diagnostic must preserve v1 and keep training behind real data readiness."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / 'data/exp_a/finetuning/v2/prepare.py'


class V2PreparationTests(unittest.TestCase):
    def test_diagnostic_bundle_has_no_training_or_reference_payload_and_keeps_split(self):
        self.assertTrue(MODULE.is_file(), 'v2 preparation has not been implemented')
        spec = importlib.util.spec_from_file_location('v2_prepare_under_test', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'v2'
            manifest = module.build(output)
            self.assertEqual(manifest['phase'], 'inference_diagnostic_only')
            self.assertFalse(manifest['training_ready'])
            self.assertEqual(manifest['required_train_dev_papers'], 567)
            self.assertEqual(manifest['candidate_pilot_papers'], 40)
            self.assertEqual(manifest['v1_protected_files_verified'], 38)
            queue = [json.loads(line) for line in (output/'train_dev_review_queue.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(len(queue), 567)
            frozen = json.loads((ROOT/'data/exp_a/finetuning/data/manifest.json').read_text(encoding='utf-8'))
            self.assertFalse({p['paper_id'] for p in queue} & set(frozen['split_ids']['test']))
            self.assertEqual(set(queue[0]), {'paper_id', 'split', 'source', 'evidence_options', 'review_status'})
            metadata = json.loads((output/'kernel/kernel-metadata.json').read_text(encoding='utf-8'))
            self.assertEqual(metadata['id'], 'htnkhi/exp-a-v2-decoding-probe')
            self.assertTrue(metadata['is_private'])
            with zipfile.ZipFile(output/'probe_code.zip') as archive:
                self.assertEqual(set(archive.namelist()), {'generation.py', 'probe.py', 'legacy_probe.py'})
                for name in archive.namelist():
                    compile(archive.read(name), name, 'exec')
            self.assertEqual(hashlib.sha256((output/'probe_code.zip').read_bytes()).hexdigest(), manifest['probe_code_sha256'])
            self.assertFalse((output/'train.jsonl').exists())
            with self.assertRaisesRegex(ValueError, 'nonempty'):
                module.build(output)


if __name__ == '__main__':
    unittest.main()
