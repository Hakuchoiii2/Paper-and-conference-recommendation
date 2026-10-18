"""Behavioral checks for the new training-free public reranking interface."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'scripts'))
from baseline_common import facet_vectors
from experiment_io import FACETS

spec = importlib.util.spec_from_file_location('intent_priority_test', PROJECT / 'scripts/exp_d/intent_priority.py')
method = importlib.util.module_from_spec(spec)
spec.loader.exec_module(method)


class RerankingTests(unittest.TestCase):
    def setUp(self):
        self.facets = {pid: {f: {f + ' shared'} for f in FACETS} for pid in ('A', 'S', 'D', 'X')}
        self.facets['D']['method'] = {'alternate method'}
        self.facets['D']['dataset'] = set()  # Inactive missingness must not hide valid focus evidence.
        self.facets['X']['problem'] = {'unrelated'}
        self.case = dict(case_id='CASE', query_paper_id='A', context_facet='problem', candidate_ids=['S', 'D', 'X'])
        directions = dict.fromkeys(FACETS, 'unknown')
        directions.update(problem='similar', method='different')
        self.base = dict(case_id='CASE', model='direction_behavior__synthetic_observations',
                         directions=directions, direction_confidence=dict(problem=1., method=.5),
                         facet_importance=dict.fromkeys(FACETS, .2),
                         ranking=[dict(paper_id=pid, score=score) for pid, score in [('S', .9), ('X', .8), ('D', -1.)]])
        self.vectors = facet_vectors(self.facets)

    def run_policy(self, policy):
        return method.rerank(self.case, self.facets, self.vectors, self.base, policy)

    def test_priority_transfers_direction_to_new_candidates(self):
        before = copy.deepcopy(self.base)
        result = self.run_policy('priority')
        self.assertEqual([r['paper_id'] for r in result['ranking']], ['D', 'S', 'X'])
        self.assertEqual(result['directions'], before['directions'])
        self.assertEqual(self.base, before)
        self.assertEqual(result['predicted_focus'], 'method')

    def test_unknown_or_tied_focus_falls_back_exactly(self):
        self.base['directions']['method'] = 'unknown'
        for policy in ('priority', 'active'):
            self.assertEqual(self.run_policy(policy)['ranking'], self.base['ranking'])
        self.base['directions'].update(method='different', task='similar')
        self.base['direction_confidence']['task'] = .5
        self.assertTrue(self.run_policy('priority')['fallback_to_baseline'])

    def test_missing_focus_is_not_rewarded_as_different(self):
        self.facets['D']['method'] = set()
        result = self.run_policy('priority')
        self.assertEqual(result['ranking'][0]['paper_id'], 'S')

    def test_active_preserves_relative_C_weights_and_ignores_inactive_missingness(self):
        self.base['facet_importance'].update(problem=.3, method=.1)
        # Preserve a valid original weight simplex.
        self.base['facet_importance']['task'] = .2
        result = self.run_policy('active')
        self.assertAlmostEqual(sum(result['facet_importance'].values()), 1.)
        self.assertAlmostEqual(result['facet_importance']['problem'], .75)
        self.assertAlmostEqual(result['facet_importance']['method'], .25)
        self.assertEqual(result['facet_importance']['dataset'], 0.)
        self.assertGreater(next(r['score'] for r in result['ranking'] if r['paper_id'] == 'D'), -1.)

    def test_public_contract_rejects_oracle_and_pool_mismatch(self):
        self.base['model'] = 'oracle_intent'
        with self.assertRaises(ValueError):
            self.run_policy('priority')
        self.base['model'] = 'direction_search'
        self.case['candidate_ids'].append('Z')
        with self.assertRaises(ValueError):
            self.run_policy('priority')


if __name__ == '__main__':
    unittest.main()
