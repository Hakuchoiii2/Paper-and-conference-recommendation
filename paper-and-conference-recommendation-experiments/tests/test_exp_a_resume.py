"""Resume from saved JSONL without repeating accepted model generations."""
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'data/exp_a'))
import build_exp_a as a


class JsonlResumeCheck(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.papers = [dict(paper_id=f'P{i:06}', source='csfcube', source_id=str(i),
                            title='Retrieval', abstract='We use ranking for retrieval.', year=None,
                            domain='information_technology', scope_evidence=['CS']) for i in (1, 2, 3)]
        a.write_jsonl(self.root / 'papers.jsonl', self.papers)
        for name in ('prompt.md', 'guide.md'):
            (self.root / name).write_text('Extract supported concepts.', encoding='utf-8')
        self.config = dict(corpus='papers.jsonl', output_dir='out', paper_range=[1, 3],
                           model='Qwen/test', revision='test-only', device='cpu',
                           cache_dir='models', prompt='prompt.md', guideline='guide.md',
                           prompt_version='test', guideline_version='test', max_new_tokens=1024,
                           max_attempts=3, temperature=0.7, top_p=0.8, top_k=20, seed=42)
        self.out = self.root / 'out'
        self.checkpoint = self.out / '.exp_a_checkpoint.sqlite3'

    def answer(self, paper, instruction):
        value = dict(paper_id=paper['paper_id'], **{facet: [] for facet in a.FACET_NAMES})
        value['method'] = [dict(concept='ranking', evidence='We use ranking for retrieval.', source='abstract')]
        return value, dict(model='Qwen/test', model_revision='test-only', usage={})

    def seed(self):
        with patch.object(a, 'load_qwen', return_value=self.answer):
            a.generate(self.root, self.config)

    def test_jsonl_only_resume_fills_middle_gap_and_preserves_saved_annotations(self):
        self.seed()
        with closing(sqlite3.connect(self.checkpoint)) as db, db:
            db.execute("DELETE FROM annotations WHERE paper_id = 'P000002'")
            a.export(self.root, self.config, self.papers, a.inputs(self.root, self.config)[1], db)
        saved = a.read_jsonl(self.out / 'annotation_metadata.jsonl')
        self.checkpoint.unlink()

        def missing_only(paper, instruction):
            self.assertEqual(paper['paper_id'], 'P000002', 'Accepted papers must not be generated again')
            return self.answer(paper, instruction)

        with patch.object(a, 'load_qwen', return_value=missing_only):
            manifest = a.generate(self.root, self.config, limit=1)
        self.assertEqual(manifest['missing_ids'], [])
        self.assertEqual([row['paper_id'] for row in a.read_jsonl(self.out / 'facets_silver.jsonl')],
                         ['P000001', 'P000002', 'P000003'])
        metadata = a.read_jsonl(self.out / 'annotation_metadata.jsonl')
        self.assertEqual([metadata[0], metadata[2]], saved)
        a.check_outputs(self.root, self.config)

    def test_missing_output_files_are_rebuilt_from_checkpoint_without_model_loading(self):
        self.seed()
        for name in ('facets_silver.jsonl', 'annotation_metadata.jsonl', 'manifest.json'):
            with self.subTest(missing_file=name):
                original = (self.out / name).read_bytes()
                (self.out / name).unlink()
                with patch.object(a, 'load_qwen', side_effect=AssertionError('No inference needed')):
                    a.generate(self.root, self.config)
                self.assertEqual((self.out / name).read_bytes(), original)
                a.check_outputs(self.root, self.config)

    def test_metadata_only_resume_rebuilds_silver_without_model_loading(self):
        self.seed()
        original = (self.out / 'facets_silver.jsonl').read_bytes()
        self.checkpoint.unlink()
        (self.out / 'facets_silver.jsonl').unlink()
        with patch.object(a, 'load_qwen', side_effect=AssertionError('Evidence already saved')):
            a.generate(self.root, self.config)
        self.assertEqual((self.out / 'facets_silver.jsonl').read_bytes(), original)
        a.check_outputs(self.root, self.config)

    def test_jsonl_recovery_rejects_changed_inputs_without_overwriting_saved_files(self):
        self.seed()
        self.checkpoint.unlink()
        original = (self.out / 'facets_silver.jsonl').read_bytes()
        (self.root / 'prompt.md').write_text('Changed prompt.', encoding='utf-8')
        with patch.object(a, 'load_qwen', side_effect=AssertionError('Reject before inference')):
            with self.assertRaisesRegex(ValueError, 'provenance'):
                a.generate(self.root, self.config)
        self.assertEqual((self.out / 'facets_silver.jsonl').read_bytes(), original)

    def test_jsonl_recovery_rejects_unverified_metadata_without_overwriting_silver(self):
        self.seed()
        self.checkpoint.unlink()
        original = (self.out / 'facets_silver.jsonl').read_bytes()
        with (self.out / 'annotation_metadata.jsonl').open('a', encoding='utf-8') as stream:
            stream.write('{}\n')
        with patch.object(a, 'load_qwen', side_effect=AssertionError('Reject before inference')):
            with self.assertRaisesRegex(ValueError, 'checksum'):
                a.generate(self.root, self.config)
        self.assertEqual((self.out / 'facets_silver.jsonl').read_bytes(), original)

    def test_jsonl_recovery_preserves_audited_fallbacks_without_model_loading(self):
        def fallback(paper, instruction):
            value = dict(paper_id=paper['paper_id'], **{facet: [] for facet in a.FACET_NAMES})
            value['method'] = [dict(concept='invented technique', evidence_id='A0')]
            raw = json.dumps(value)
            return a.annotate(paper, instruction, self.config, {},
                              lambda messages, seed: (raw, dict(usage={})), self.out / 'last_failure.json')

        with patch.object(a, 'load_qwen', return_value=fallback):
            a.generate(self.root, self.config)
        original = (self.out / 'annotation_metadata.jsonl').read_bytes()
        self.checkpoint.unlink()
        with patch.object(a, 'load_qwen', side_effect=AssertionError('Fallbacks already saved')):
            a.generate(self.root, self.config)
        self.assertEqual((self.out / 'annotation_metadata.jsonl').read_bytes(), original)
        self.assertEqual(set(a.check_outputs(self.root, self.config)['fallback_annotations']),
                         {'P000001', 'P000002', 'P000003'})

    def test_jsonl_recovery_requires_manifest_and_evidence_before_overwriting(self):
        for missing_file in ('manifest.json', 'annotation_metadata.jsonl'):
            with self.subTest(missing_file=missing_file):
                self.config['output_dir'] = missing_file + '_out'
                self.out = self.root / self.config['output_dir']
                self.checkpoint = self.out / '.exp_a_checkpoint.sqlite3'
                self.seed()
                original = (self.out / 'facets_silver.jsonl').read_bytes()
                self.checkpoint.unlink()
                (self.out / missing_file).unlink()
                with patch.object(a, 'load_qwen', side_effect=AssertionError('Reject before inference')):
                    with self.assertRaisesRegex(ValueError, 'JSONL recovery requires'):
                        a.generate(self.root, self.config)
                self.assertEqual((self.out / 'facets_silver.jsonl').read_bytes(), original)

    def test_existing_policy_23_outputs_remain_compatible(self):
        current = dict(generator_version='2.3', generator_sha256='updated-build',
                       config={'model': 'Qwen/test'}, input_hashes={'corpus': 'original'}, schema={})
        previous = dict(current,
                        generator_sha256='d4337f76920a5ebf503217b4ef0aff307aa798c151453b287ad7f14838e14c88')
        self.assertTrue(a.compatible_provenance(previous, current))
        self.assertFalse(a.compatible_provenance(dict(previous, input_hashes={'corpus': 'changed'}), current))


if __name__ == '__main__':
    unittest.main()
