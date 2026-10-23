import copy
import unittest

from data_io import FACETS
from focus_masked import active_directions
from baseline_common import facet_vectors, intent_scores


class FocusMaskTests(unittest.TestCase):
    def test_only_unique_inferred_focus_activates_mask(self):
        original = dict.fromkeys(FACETS, 'unknown')
        original.update(task='similar', problem='different')
        frozen = copy.deepcopy(original)
        masked = active_directions('task', original)
        self.assertEqual(original, frozen)
        self.assertEqual(masked['problem'], 'different')
        self.assertEqual(masked['task'], 'similar')
        self.assertTrue(all(masked[f]=='ignore' for f in FACETS if f not in ('task','problem')))

    def test_unknown_focus_keeps_original_fallback(self):
        directions = dict.fromkeys(FACETS, 'unknown')
        directions['task'] = 'similar'
        self.assertEqual(active_directions('task', directions), directions)

    def test_multiple_possible_focuses_do_not_get_arbitrarily_selected(self):
        directions = dict.fromkeys(FACETS, 'similar')
        self.assertEqual(active_directions('task', directions), directions)

    def test_similar_control_uses_exactly_same_inferred_focus_and_mask(self):
        directions = dict.fromkeys(FACETS, 'unknown')
        directions.update(task='similar', problem='different')
        active = active_directions('task', directions)
        control = active_directions('task', directions, force_similar=True)
        self.assertEqual({f for f in active if active[f]=='ignore'}, {f for f in control if control[f]=='ignore'})
        self.assertEqual(control['problem'], 'similar')

    def test_mask_uses_unchanged_scorer_and_does_not_change_C_weights(self):
        facets = {p:{f:{f+' same'} for f in FACETS} for p in ('A','S','D')}
        facets['D']['problem'] = {'other problem'}
        facets['D']['contribution'] = set()
        case = dict(query_paper_id='A', context_facet='task', candidate_ids=['S','D'])
        weights = dict.fromkeys(FACETS, .2)
        frozen = dict(weights)
        estimates = dict.fromkeys(FACETS, 'unknown')
        estimates.update(task='similar', problem='different')
        vectors = facet_vectors(facets)
        base = intent_scores(case, weights, estimates, vectors)
        masked = intent_scores(case, weights, active_directions('task', estimates), vectors)
        self.assertEqual(base['D'], -1)
        self.assertGreater(masked['D'], masked['S'])
        self.assertEqual(weights, frozen)


if __name__ == '__main__':
    unittest.main()
