"""Protect evidence attribution at the v2 annotation boundary, without model loads."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / 'data/exp_a/finetuning/label_revision_v2/schema.py'


class MultiSentenceEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.is_file(), 'Multi-sentence annotation schema is not implemented')
        spec = importlib.util.spec_from_file_location('revision_schema_under_test', MODULE)
        self.schema = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.schema)
        self.paper = dict(paper_id='P000001', title='ORBIT retrieval', abstract=
            'We introduce ORBIT. It improves recall by 12% on noisy queries.')
        self.response = dict(paper_id='P000001', problem=[], task=[], method=[], dataset=[],
            contribution=[dict(concept='ORBIT improves recall by 12% on noisy queries',
                               evidence_ids=['A0', 'A1'])])

    def test_resolves_subject_without_losing_either_exact_quote(self):
        grounded = self.schema.ground_response(self.response, self.paper)
        item = grounded['contribution'][0]
        self.assertEqual(item['concept'], 'ORBIT improves recall by 12% on noisy queries')
        self.assertEqual(item['evidence'], [
            dict(evidence_id='A0', source='abstract', evidence='We introduce ORBIT.'),
            dict(evidence_id='A1', source='abstract', evidence='It improves recall by 12% on noisy queries.')])

    def test_accepts_single_sentence_as_a_list(self):
        self.response['contribution'] = [dict(concept='ORBIT', evidence_ids=['A0'])]
        self.assertEqual(len(self.schema.ground_response(self.response, self.paper)['contribution'][0]['evidence']), 1)

    def test_rejects_missing_unknown_duplicated_or_reversed_evidence(self):
        for ids in ([], 'A0', ['A999'], ['A0', 'A0'], ['A1', 'A0'], [None], [{'id': 'A0'}]):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                bad = copy.deepcopy(self.response)
                bad['contribution'][0]['evidence_ids'] = ids
                self.schema.ground_response(bad, self.paper)

    def test_rejects_a_subject_not_supported_by_selected_sentences(self):
        self.response['contribution'][0]['evidence_ids'] = ['A1']
        with self.assertRaises(ValueError):
            self.schema.ground_response(self.response, self.paper)

    def test_rejects_invented_numbers(self):
        self.response['contribution'][0]['concept'] = 'ORBIT improves recall by 99% on noisy queries'
        with self.assertRaises(ValueError):
            self.schema.ground_response(self.response, self.paper)

    def test_rejects_legacy_item_shape_in_v2(self):
        self.response['contribution'] = [dict(concept='ORBIT', evidence_id='A0')]
        with self.assertRaises(ValueError):
            self.schema.ground_response(self.response, self.paper)

    def test_rejects_wrong_paper_or_incomplete_facets(self):
        for change in ('paper_id', 'task'):
            with self.subTest(change=change), self.assertRaises(ValueError):
                bad = copy.deepcopy(self.response)
                if change == 'paper_id':
                    bad[change] = 'P000002'
                else:
                    del bad[change]
                self.schema.ground_response(bad, self.paper)

    def test_rejects_duplicate_concepts_and_empty_text(self):
        for concept in ('ORBIT improves recall by 12% on noisy queries', ''):
            with self.subTest(concept=concept), self.assertRaises(ValueError):
                bad = copy.deepcopy(self.response)
                bad['contribution'].append(dict(concept=concept, evidence_ids=['A0', 'A1']))
                self.schema.ground_response(bad, self.paper)


if __name__ == '__main__':
    unittest.main()
