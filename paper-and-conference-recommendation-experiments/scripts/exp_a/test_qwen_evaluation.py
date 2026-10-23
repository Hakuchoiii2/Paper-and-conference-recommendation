"""Check Exp A counts and safety with fixed vectors; unit tests never load a model."""
import json
import math
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(PROJECT / 'scripts'))
from build_corpus import read_jsonl, write_jsonl
from download_sources import sha256
from exp_a.core import test_exp_a_handoff as handoff
from exp_a import evaluate_exp_a as evaluator


class EvaluationChecks(unittest.TestCase):
    def setUp(self):
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
        kwargs.setdefault('matching', 'exact')
        return evaluator.evaluate(self.root, gold=self.gold, output=self.output, expected_count=3, **kwargs)

    def test_embedding_assignment_is_one_to_one_and_maximizes_matches(self):
        self.assertEqual(evaluator.match_pairs([[0.95], [0.90]], 0.85), ((0, 0),))
        self.assertEqual(set(evaluator.match_pairs([[0.95,0.85], [0.90,0.1]],0.85)), {(0,1),(1,0)})
        self.assertEqual(evaluator.match_pairs([[0.849]],0.85), ())
        self.assertEqual(evaluator.match_pairs([[0.85]],0.85), ((0,0),))
        self.assertEqual(evaluator.match_pairs([[]],0.85), ())
        self.assertEqual(evaluator.match_pairs([],0.85), ())

    def test_resource_names_and_source_defined_aliases_match_without_erasing_identity(self):
        self.assertEqual(evaluator.canonical_label('Natural Questions benchmark dataset','dataset'),
                         evaluator.canonical_label('Natural Questions','dataset'))
        self.assertEqual(evaluator.canonical_label('ATIS corpus','dataset'),'atis')
        self.assertNotEqual(evaluator.canonical_label('C++ corpus','dataset'),
                            evaluator.canonical_label('C corpus','dataset'))
        source = 'We use Support Vector Machines (SVM).'
        self.assertEqual(evaluator.canonical_label('Support Vector Machines','method',source),'svm')
        self.assertEqual(evaluator.canonical_label('Support Vector Machines (SVM)','method',source),'svm')
        self.assertNotEqual(evaluator.canonical_label('Support Vector Machines','method'),'svm')
        self.assertNotEqual(evaluator.canonical_label('Vector Machines','method',source),'svm')

    def test_named_artifact_requires_an_explicit_source_definition(self):
        label = 'a novel end-to-end deep learning network called RespNet'
        source = 'A novel end-to-end deep learning network called RespNet is proposed.'
        pair = evaluator.pair_score(label,'RespNet','contribution',0.81,source)
        self.assertEqual(pair['match_type'],'canonical')
        self.assertEqual(pair['score'],1.0)
        self.assertEqual(pair['similarity'],0.81)
        self.assertNotEqual(evaluator.pair_score(label,'RespNet','contribution',0.81,'')['score'],1.0)
        self.assertNotEqual(evaluator.pair_score('a novel SVM called RespNet','RespNet',
                            'contribution',0.81,source)['score'],1.0)

    def test_evaluation_records_a_rejected_high_cosine_pair(self):
        rows = self.review()
        rows[0]['facets']['contribution'] = ['not contribution']
        write_jsonl(self.root/self.gold,rows)
        vectors = {'contribution':[1,0], 'extra':[-1,0], 'not contribution':[0.99,math.sqrt(1-0.99**2)]}
        runtime = dict(model='Qwen/Qwen3-Embedding-0.6B',revision='test',device='test',model_files={})
        with patch.object(evaluator,'encode_labels',return_value=(vectors,runtime)):
            report = self.score(matching='embedding')
        self.assertEqual(report['micro']['tp'],13)
        self.assertEqual(report['matching_diagnostics']['blocked_candidates'],{'negation_mismatch':1})
        first = read_jsonl(self.root/self.output/'per_paper.jsonl')[0]
        self.assertEqual(first['comparison']['contribution']['matched_pairs'],[])
        self.assertEqual(first['comparison']['contribution']['rejected_pairs'][0]['reason'],'negation_mismatch')

    def test_high_cosine_does_not_override_numbers_metrics_negation_or_task_operations(self):
        cases = [
            ('Encoder Network achieves correlation of ~0.84',
             'correlation of Encoder Network improved by ~13%','contribution','numeric_mismatch'),
            ('accuracy improves by 2%','accuracy improves by 3%','contribution','numeric_mismatch'),
            ('accuracy improves by 2%','accuracy improves','contribution','missing_quantity'),
            ('model improves accuracy','model does not improve accuracy','contribution','negation_mismatch'),
            ('model achieves accuracy of 0.84','model achieves correlation of 0.84','contribution','metric_mismatch'),
            ('model achieves accuracy of 13%','model accuracy improved by 13%','contribution','quantity_role_mismatch'),
            ('perform a rigorous measurement study characterizing counterspeech',
             'detect different types of counterspeech','task','different_task_operations'),
            ('WMT14 English-German','WMT17 English-German','dataset','numeric_mismatch')]
        for silver,gold,facet,reason in cases:
            with self.subTest(silver=silver,gold=gold):
                pair = evaluator.pair_score(silver,gold,facet,0.99,'')
                self.assertEqual(pair['blocked_reason'],reason)
                self.assertLess(pair['score'],0)
        self.assertIsNone(evaluator.pair_score('model improves accuracy by 1,000%',
                          'model improves accuracy by 1000%','contribution',0.99,'')['blocked_reason'])
        self.assertIsNone(evaluator.pair_score('model achieves F1-score of 0.71',
                          'model achieves F-score of 0.71','contribution',0.99,'')['blocked_reason'])

    def test_embedding_paraphrase_counts_once_and_keeps_exact_baseline(self):
        rows = self.review()
        rows[0]['facets']['method'] = ['technique','algorithm']
        write_jsonl(self.root/self.gold,rows)
        vectors = {'method':[1,0], 'technique':[0.9,math.sqrt(0.19)],
                   'algorithm':[0.95,math.sqrt(1-0.95**2)],
                   'contribution':[0,1], 'extra':[0,-1]}
        runtime = dict(model='Qwen/Qwen3-Embedding-0.6B', revision='test', device='test', model_files={})
        with patch.object(evaluator,'encode_labels',return_value=(vectors,runtime)):
            report = self.score(matching='embedding')
        self.assertEqual(report['evaluation_kind'],'embedding_agreement_with_human_gold')
        self.assertEqual((report['micro']['tp'],report['micro']['fp'],report['micro']['fn']),(14,1,2))
        self.assertEqual((report['lexical_baseline']['micro']['tp'],report['lexical_baseline']['micro']['fp'],
                          report['lexical_baseline']['micro']['fn']),(13,2,3))
        first = read_jsonl(self.root/self.output/'per_paper.jsonl')[0]
        method = first['comparison']['method']
        self.assertEqual(len(method['matched_pairs']),1)
        self.assertEqual(method['matched_pairs'][0]['gold'],'algorithm')
        self.assertAlmostEqual(method['matched_pairs'][0]['similarity'],0.95)
        self.assertEqual(method['missing'],['technique'])
        self.assertEqual(method['extra'],[])
        self.assertEqual(report['threshold'],0.85)
        self.assertIn('embedding',(self.root/self.output/'report.md').read_text(encoding='utf-8'))

    def test_embedding_does_not_match_labels_across_facets(self):
        rows = self.review()
        rows[0]['facets']['method'] = []
        rows[0]['facets']['task'] = ['method']
        write_jsonl(self.root/self.gold,rows)
        vectors = {'method':[1,0], 'task':[0,1], 'contribution':[1,0], 'extra':[-1,0]}
        runtime = dict(model='Qwen/Qwen3-Embedding-0.6B',revision='test',device='test',model_files={})
        with patch.object(evaluator,'encode_labels',return_value=(vectors,runtime)):
            report = self.score(matching='embedding')
        self.assertEqual(report['by_facet']['method']['fp'],1)
        self.assertEqual(report['by_facet']['task']['fp'],1)
        self.assertEqual(report['by_facet']['task']['fn'],1)

    def test_invalid_embedding_thresholds_are_rejected_before_model_loading(self):
        self.review()
        with patch.object(evaluator,'encode_labels',side_effect=AssertionError('Must reject threshold first')):
            for threshold in (0,-0.1,1.01,float('nan'),float('inf'),True):
                with self.subTest(threshold=threshold):
                    with self.assertRaisesRegex(ValueError,'threshold'):
                        self.score(matching='embedding',threshold=threshold)
            with self.assertRaisesRegex(ValueError,'matching'):
                self.score(matching='unknown')

    def test_exact_mode_does_not_load_an_embedding_model(self):
        self.review()
        with patch.object(evaluator,'encode_labels',side_effect=AssertionError('Exact mode must stay CPU-only')):
            self.assertEqual(self.score()['micro']['tp'],14)

    def test_embedding_output_cannot_overlap_the_model_cache(self):
        self.review()
        cache = evaluator.MODEL_DIRECTORY
        with patch.object(evaluator,'encode_labels',side_effect=AssertionError('Must reject output first')):
            for output in (cache,cache+'/child',str(Path(cache).parent)):
                with self.subTest(output=output):
                    with self.assertRaisesRegex(ValueError,'model cache'):
                        evaluator.evaluate(self.root,gold=self.gold,output=output,expected_count=3)

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

    def test_ai_reviewed_references_are_not_reported_as_human_gold(self):
        rows = self.review()
        for row in rows:
            row.pop('reviewer', None)
            row.update(reviewer_type='ai', human_review_status='pending')
        write_jsonl(self.root/self.gold, rows)
        report = self.score()
        self.assertEqual(report['evaluation_kind'], 'lexical_agreement_with_ai_reference')
        self.assertEqual(report['reference_kind'], 'ai')
        self.assertEqual(report['reference_counts'], {'ai': 3})
        self.assertIn('nhãn tham chiếu AI', (self.root/self.output/'report.md').read_text(encoding='utf-8'))
        rows[0].update(reviewer='human test reviewer', reviewer_type='human')
        write_jsonl(self.root/self.gold, rows)
        self.assertEqual(self.score()['reference_kind'], 'mixed')
        rows[0]['reviewer_type'] = 'unknown'
        write_jsonl(self.root/self.gold, rows)
        with self.assertRaisesRegex(ValueError, 'reviewer_type'):
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
        result = evaluator.evaluate(self.root,source=source,gold=self.gold,output=self.output,expected_count=3,matching='exact')
        self.assertEqual(result['gold_count'],3)


if __name__ == '__main__':
    unittest.main()
