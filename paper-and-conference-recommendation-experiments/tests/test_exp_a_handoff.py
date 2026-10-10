"""A merge and deterministic human-review selection; all fixtures are test-only."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'scripts'))
sys.path.insert(0, str(PROJECT / 'data/exp_a'))
import build_exp_a as a
try:
    import merge_exp_a as merger
    import select_gold_review as selector
except ImportError:
    merger = selector = None


class HandoffChecks(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(merger, 'A handoff and review-selection tools are not implemented')
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.papers = [dict(paper_id=f'P{i:06}', source='csfcube', source_id=str(i),
                            title='problem task method dataset contribution extra',
                            abstract='problem task method dataset contribution extra.', year=None,
                            domain='information_technology', scope_evidence=['test-only fixture'])
                       for i in range(1, 7)]
        a.write_jsonl(self.root / 'data/processed/papers.jsonl', self.papers)
        for name in ('prompt.md', 'guide.md'):
            (self.root / name).write_text('Test-only extraction.', encoding='utf-8')
        self.config = dict(corpus='data/processed/papers.jsonl', paper_range=[1, 6],
                           output_dir='data/exp_a/generated/part_1', model='Qwen/test-only',
                           revision='test-only', device='cpu', cache_dir='models',
                           prompt='prompt.md', guideline='guide.md', prompt_version='test',
                           guideline_version='test', max_new_tokens=1024, max_attempts=3,
                           temperature=0.7, top_p=0.8, top_k=20, seed=42)
        self.parts = ['data/exp_a/generated/part_1', 'data/exp_a/generated/part_2']
        self.output = 'data/exp_a/generated'

    def answer(self, paper, instruction):
        number = int(paper['paper_id'][1:])
        selected = list(a.FACET_NAMES)
        if number == 3:
            selected.remove('dataset')
        if number == 5:
            selected = []
        if number == 6:
            selected = ['task', 'method']
        evidence = dict(paper_id=paper['paper_id'], **{f: [] for f in a.FACET_NAMES})
        for facet in selected:
            evidence[facet] = [dict(concept=facet, evidence=paper['abstract'], source='abstract')]
        if number == 2:
            evidence['contribution'].append(dict(concept='extra', evidence=paper['abstract'], source='abstract'))
        metadata = dict(model='Qwen/test-only', model_revision='test-only', usage={})
        if number == 5:
            metadata.update(fallback_used=True, validation_errors=['test-only malformed generation'])
        return evidence, metadata

    def seed(self, second_start=4, seed=42):
        with patch.object(a, 'load_qwen', return_value=self.answer):
            a.generate(self.root, dict(self.config, paper_range=[1, 3], output_dir=self.parts[0]))
            a.generate(self.root, dict(self.config, paper_range=[second_start, 6],
                                       output_dir=self.parts[1], seed=seed))

    def test_merge_keeps_sorted_metadata_fallback_audit_and_all_ids(self):
        self.seed()
        manifest = merger.merge(self.root, list(reversed(self.parts)), self.output)
        self.assertEqual(manifest['status'], 'complete')
        self.assertEqual(manifest['count'], 6)
        self.assertEqual(manifest['missing_ids'], [])
        self.assertEqual(set(manifest['fallback_annotations']), {'P000005'})
        self.assertEqual([row['paper_id'] for row in a.read_jsonl(self.root / self.output / 'facets_silver.jsonl')],
                         ['P000001', 'P000002', 'P000003', 'P000004', 'P000005', 'P000006'])
        self.assertEqual(len(manifest['source_parts']), 2)
        before = (self.root / self.parts[0] / 'facets_silver.jsonl').read_bytes()
        merger.merge(self.root, self.parts, self.output)
        self.assertEqual(before, (self.root / self.parts[0] / 'facets_silver.jsonl').read_bytes())

    def test_incomplete_or_overlapping_parts_never_publish_handoff(self):
        self.seed(second_start=3)
        with self.assertRaisesRegex(ValueError, 'overlap|duplicate'):
            merger.merge(self.root, self.parts, self.output)
        with self.assertRaisesRegex(ValueError, 'missing|coverage|Only'):
            merger.merge(self.root, self.parts[:1], self.output)
        self.assertFalse((self.root / self.output / 'facets_silver.jsonl').exists())

    def test_different_sampling_provenance_is_rejected(self):
        self.seed(seed=43)
        with self.assertRaisesRegex(ValueError, 'provenance|config'):
            merger.merge(self.root, self.parts, self.output)

    def test_different_resolved_model_identity_is_rejected_before_writing(self):
        for field in ('model', 'model_revision'):
            with self.subTest(field=field):
                self.seed()
                directory = self.root / self.parts[1]
                rows = a.read_jsonl(directory / 'annotation_metadata.jsonl')
                original_identity = rows[0][field]
                rows[0][field] = 'different-resolved-checkpoint'
                a.write_jsonl(directory / 'annotation_metadata.jsonl', rows)
                manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
                manifest['files']['annotation_metadata.jsonl'] = a.sha256(directory / 'annotation_metadata.jsonl')
                a.write_json(directory / 'manifest.json', manifest)
                with self.assertRaisesRegex(ValueError, 'model|checkpoint|revision'):
                    merger.merge(self.root, self.parts, self.output)
                self.assertFalse((self.root / self.output / 'facets_silver.jsonl').exists())
                rows[0][field] = original_identity
                a.write_jsonl(directory / 'annotation_metadata.jsonl', rows)
                manifest['files']['annotation_metadata.jsonl'] = a.sha256(directory / 'annotation_metadata.jsonl')
                a.write_json(directory / 'manifest.json', manifest)

    def test_fallback_without_runtime_model_identity_remains_mergeable(self):
        self.seed()
        directory = self.root / self.parts[1]
        rows = a.read_jsonl(directory / 'annotation_metadata.jsonl')
        for row in rows:
            if row.get('fallback_used'):
                row.pop('model', None)
                row.pop('model_revision', None)
        a.write_jsonl(directory / 'annotation_metadata.jsonl', rows)
        manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
        manifest['files']['annotation_metadata.jsonl'] = a.sha256(directory / 'annotation_metadata.jsonl')
        a.write_json(directory / 'manifest.json', manifest)
        self.assertEqual(merger.merge(self.root, self.parts, self.output)['status'], 'complete')

    def test_changed_part_bytes_are_rejected_before_merge(self):
        self.seed()
        path = self.root / self.parts[0] / 'facets_silver.jsonl'
        path.write_text('{}\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            merger.merge(self.root, self.parts, self.output)
        self.assertFalse((self.root / self.output / 'facets_silver.jsonl').exists())

    def test_merge_output_cannot_overwrite_other_dataset_or_source_part(self):
        self.seed()
        for output in ('data/processed', self.parts[0], self.parts[0] + '/nested'):
            with self.subTest(output=output):
                with self.assertRaisesRegex(ValueError, 'experiment A|overwrite'):
                    merger.merge(self.root, self.parts, output)
        self.assertFalse((self.root / 'data/processed/facets_silver.jsonl').exists())

    def test_review_ranks_completeness_and_evidence_without_creating_gold(self):
        self.seed()
        merger.merge(self.root, self.parts, self.output)
        report = selector.select(self.root, self.output, 'data/exp_a/ground_truth/review', count=3)
        self.assertEqual(report['selected_ids'], ['P000002', 'P000004', 'P000003'])
        self.assertEqual(report['tier'], 'review_queue')
        self.assertEqual(report['excluded_ids']['P000001'], 'prompt_development_example')
        self.assertIn('P000005', report['excluded_ids'])
        queue = self.root / 'data/exp_a/ground_truth/review'
        papers = a.read_jsonl(queue / 'review_papers.jsonl')
        self.assertNotIn('silver_facets', papers[0])
        forms = a.read_jsonl(queue / 'review_annotations.jsonl')
        self.assertEqual(forms[0]['review_status'], 'pending')
        self.assertFalse((self.root / self.output / 'facets_gold.jsonl').exists())
        repeated = selector.select(self.root, self.output, 'unused', count=3, dry_run=True)
        self.assertEqual(report['selected_ids'], repeated['selected_ids'])
        self.assertFalse((self.root / 'unused').exists())

    def test_review_work_and_shortfall_are_never_overwritten(self):
        self.seed()
        merger.merge(self.root, self.parts, self.output)
        output = 'data/exp_a/ground_truth/review'
        selector.select(self.root, self.output, output, count=2)
        path = self.root / output / 'review_annotations.jsonl'
        path.write_text('human review in progress\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'exist|overwrite'):
            selector.select(self.root, self.output, output, count=2)
        self.assertEqual(path.read_text(encoding='utf-8'), 'human review in progress\n')
        with self.assertRaisesRegex(ValueError, 'eligible|shortfall'):
            selector.select(self.root, self.output, 'shortfall', count=400)
        self.assertFalse((self.root / 'shortfall').exists())

    def test_default_review_refuses_partial_a_but_explicit_preview_is_read_only(self):
        self.seed()
        with self.assertRaisesRegex(ValueError, 'partial|Only'):
            selector.select(self.root, self.parts[0], 'review', count=1)
        report = selector.select(self.root, self.parts[0], 'review', count=1,
                                 dry_run=True, allow_partial=True)
        self.assertEqual(report['selected_ids'], ['P000002'])
        self.assertFalse((self.root / 'review').exists())


if __name__ == '__main__':
    unittest.main()
