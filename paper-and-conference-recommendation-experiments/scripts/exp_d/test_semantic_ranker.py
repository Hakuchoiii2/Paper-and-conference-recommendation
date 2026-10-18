"""Encoder ablations must preserve evidence, lexical context and missingness rules."""
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT / 'scripts'), str(PROJECT / 'scripts/exp_d')]
import numpy as np
from baseline_common import facet_vectors
from experiment_io import FACETS
from semantic_ranker import rerank


class SemanticTests(unittest.TestCase):
    def setUp(self):
        self.facets = {pid: {f: {f + ' shared'} for f in FACETS} for pid in ('A', 'B', 'X')}
        self.facets['X']['problem'] = {'outside'}
        self.vectors = facet_vectors(self.facets)
        self.embeddings = {(pid, f): np.array([1., 0.]) for pid in self.facets for f in FACETS}
        self.case = dict(case_id='S', query_paper_id='A', context_facet='problem', candidate_ids=['B', 'X'])
        directions = dict.fromkeys(FACETS, 'unknown')
        directions.update(problem='similar', method='different')
        self.base = dict(model='direction_search', case_id='S', directions=directions,
                         direction_confidence=dict(problem=1., method=.8),
                         facet_importance=dict.fromkeys(FACETS, .2),
                         ranking=[dict(paper_id='B', score=.8), dict(paper_id='X', score=-1.)])

    def run_mode(self, mode):
        return rerank(self.case, self.facets, self.vectors, self.embeddings, self.base, mode)

    def test_dense_similarity_cannot_bypass_lexical_context_gate(self):
        for mode in ('full', 'active', 'hybrid'):
            result = self.run_mode(mode)
            self.assertEqual(next(r['score'] for r in result['ranking'] if r['paper_id'] == 'X'), -1.)
            self.assertEqual(result['directions'], self.base['directions'])
            self.assertEqual(result['direction_confidence'], self.base['direction_confidence'])

    def test_unknown_focus_active_falls_back_but_full_still_encodes(self):
        self.base['directions']['method'] = 'unknown'
        for mode in ('active', 'hybrid'):
            result = self.run_mode(mode)
            self.assertTrue(result['fallback_to_baseline'])
            self.assertEqual(result['ranking'], self.base['ranking'])
        self.assertFalse(self.run_mode('full')['fallback_to_baseline'])

    def test_missing_active_facet_is_never_rewarded_as_different(self):
        self.facets['B']['method'] = set()
        self.vectors = facet_vectors(self.facets)
        for mode in ('full', 'active', 'hybrid'):
            result = self.run_mode(mode)
            self.assertEqual(next(r['score'] for r in result['ranking'] if r['paper_id'] == 'B'), -1.)

    def test_encoder_only_full_retains_weights_active_masks_them(self):
        self.assertEqual(self.run_mode('full')['facet_importance'], self.base['facet_importance'])
        active = self.run_mode('active')['facet_importance']
        self.assertEqual(active['problem'], .5)
        self.assertEqual(active['method'], .5)
        self.assertEqual(active['dataset'], 0.)
        self.assertEqual(self.run_mode('hybrid')['hybrid_dense_weight'], .5)


if __name__ == '__main__':
    unittest.main()
