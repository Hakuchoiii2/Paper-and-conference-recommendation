"""Human gold scoring uses literal expected errors, never Qwen as its own judge."""
import json
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'scripts'))
from build_corpus import read_jsonl, write_jsonl
from download_sources import sha256
import test_exp_a_handoff as handoff
try:
    from exp_a import evaluate_exp_a as evaluator
except ImportError:
    evaluator = None


class EvaluationChecks(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(evaluator, 'Human-gold evaluation is not implemented')
        fixture = handoff.HandoffChecks()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.seed()
        self.root = fixture.root
        handoff.merger.merge(self.root, fixture.parts)
        self.queue = 'data/exp_a/ground_truth/gold_review'
        handoff.selector.select(self.root, output=self.queue, count=3)
        self.gold = self.queue + '/review_annotations.jsonl'
        self.output = 'data/exp_a/evaluation/test_gold'

    def review(self):
        rows = [dict(paper_id=pid, reviewer='human test reviewer', review_status='reviewed', facets={
                    'problem':['problem'], 'task':['task'], 'method':['method'],
                    'dataset':['dataset'], 'contribution':['extra' if pid == 'P000002' else 'contribution']})
                for pid in ('P000002', 'P000004', 'P000003')]
        write_jsonl(self.root / self.gold, rows)
        return rows

    def score(self, **kwargs):
        return evaluator.evaluate(self.root, gold=self.gold, output=self.output, expected_count=3, **kwargs)

    def test_counts_per_facet_and_micro_metrics_have_literal_expected_values(self):
        self.review()
        report = self.score()
        self.assertEqual(report['micro']['tp'], 14)
        self.assertEqual(report['micro']['fp'], 1)
        self.assertEqual(report['micro']['fn'], 1)
        self.assertAlmostEqual(report['micro']['precision'], 14/15)
        self.assertAlmostEqual(report['micro']['recall'], 14/15)
        self.assertAlmostEqual(report['micro']['f1'], 14/15)
        self.assertEqual(report['by_facet']['dataset']['fn'], 1)
        self.assertEqual(report['by_facet']['contribution']['fp'], 1)
        self.assertEqual(report['by_facet']['dataset']['precision'], 1)
        self.assertAlmostEqual(report['by_facet']['dataset']['recall'], 2/3)
        self.assertAlmostEqual(report['by_facet']['contribution']['precision'], 3/4)
        self.assertEqual(report['by_facet']['contribution']['recall'], 1)
        self.assertEqual(report['exact_papers'], 1)
        self.assertEqual(report['corpus_audit']['fallback_papers'], 1)
        self.assertEqual(report['cohort']['selection_policy'],
                         'nonempty_facets_desc_supported_concepts_desc_paper_id_asc_v1')
        detail = {row['paper_id']:row for row in read_jsonl(self.root / self.output / 'per_paper.jsonl')}
        self.assertEqual(detail['P000002']['comparison']['contribution']['extra'], ['contribution'])
        self.assertEqual(detail['P000003']['comparison']['dataset']['missing'], ['dataset'])
        before = {name:(self.root/self.output/name).read_bytes() for name in
                  ('summary.json','per_paper.jsonl','report.md','manifest.json')}
        self.score()
        self.assertEqual(before, {name:(self.root/self.output/name).read_bytes() for name in before})
        manifest = json.loads((self.root/self.output/'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['gold_sha256'],sha256(self.root/self.gold))

    def test_pending_or_unattributed_gold_cannot_be_scored(self):
        with self.assertRaisesRegex(ValueError, 'review|pending'):
            self.score()
        self.assertFalse((self.root/self.output).exists())
        rows = self.review()
        rows[0]['reviewer'] = None
        write_jsonl(self.root/self.gold, rows)
        with self.assertRaisesRegex(ValueError, 'reviewer'):
            self.score()

    def test_missing_duplicate_or_foreign_gold_ids_are_rejected(self):
        original = self.review()
        for rows in (original[:-1], original+[original[0]],
                     [dict(original[0],paper_id='P999999')]+original[1:]):
            with self.subTest(ids=[row['paper_id'] for row in rows]):
                write_jsonl(self.root/self.gold,rows)
                with self.assertRaisesRegex(ValueError, 'count|ID|duplicate|cohort|paper'):
                    self.score()
        self.assertFalse((self.root/self.output).exists())

    def test_normalization_keeps_meaningful_punctuation_and_no_automatic_synonyms(self):
        self.assertEqual(evaluator.label_key('  MATRIX   Factorization '),'matrix factorization')
        self.assertNotEqual(evaluator.label_key('C++'),evaluator.label_key('C'))
        self.assertNotEqual(evaluator.label_key('matrix factorization'),evaluator.label_key('MF'))
        empty = evaluator.metrics(0,0,0)
        self.assertIsNone(empty['precision'])
        self.assertIsNone(empty['recall'])
        self.assertIsNone(empty['f1'])
        self.assertEqual(evaluator.metrics(0,0,2)['f1'],0)

    def test_invalid_gold_lists_and_duplicate_normalized_concepts_are_rejected(self):
        for value in ('problem', ['problem',' PROBLEM '], [''], [True]):
            rows = self.review()
            rows[0]['facets']['problem'] = value
            write_jsonl(self.root/self.gold,rows)
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'concept|list|duplicate|facet'):
                    self.score()

    def test_cross_facet_candidates_are_visible_for_human_error_analysis(self):
        rows = self.review()
        rows[0]['facets']['method'] = ['contribution']
        rows[0]['facets']['contribution'] = ['method','extra']
        write_jsonl(self.root/self.gold,rows)
        self.score()
        first = read_jsonl(self.root/self.output/'per_paper.jsonl')[0]
        self.assertEqual(first['comparison']['method']['possible_cross_facet'], {'method':['contribution']})

    def test_corrupted_silver_and_unsafe_output_stop_before_writing(self):
        self.review()
        with self.assertRaisesRegex(ValueError,'evaluation|overwrite'):
            evaluator.evaluate(self.root,gold=self.gold,output=self.queue,expected_count=3)
        path = self.root/'data/exp_a/generated/facets_silver.jsonl'
        path.write_text('{}\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'checksum'):
            self.score()
        self.assertFalse((self.root/self.output).exists())

    def test_evaluation_cannot_overwrite_a_custom_silver_source(self):
        self.review()
        source = 'data/exp_a/evaluation/custom_silver'
        handoff.merger.merge(self.root, ['data/exp_a/generated/part_1','data/exp_a/generated/part_2'], source)
        before = {name:(self.root/source/name).read_bytes() for name in
                  ('manifest.json','facets_silver.jsonl','annotation_metadata.jsonl')}
        gold_before = (self.root/self.gold).read_bytes()
        for output in (source, source+'/child', 'data/exp_a/evaluation'):
            with self.subTest(output=output):
                with self.assertRaisesRegex(ValueError,'source|overlap'):
                    evaluator.evaluate(self.root,source=source,gold=self.gold,output=output,expected_count=3)
                self.assertEqual(before,{name:(self.root/source/name).read_bytes() for name in before})
                self.assertEqual(gold_before,(self.root/self.gold).read_bytes())
        result = evaluator.evaluate(self.root,source=source,gold=self.gold,output=self.output,expected_count=3)
        self.assertEqual(result['gold_count'],3)


if __name__ == '__main__':
    unittest.main()
