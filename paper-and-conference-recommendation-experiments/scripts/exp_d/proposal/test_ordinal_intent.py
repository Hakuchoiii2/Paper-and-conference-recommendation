import math
import unittest
from unittest.mock import patch

from data_io import Evidence, FACETS
from common_ranking import ranking_directions
from ordinal_intent import log_difference_probability, ordinal_intent


class OrdinalTests(unittest.TestCase):
    def test_probabilities_normalized_and_direction_symmetric(self):
        for strength in (0, .25, .75, 1.5):
            self.assertAlmostEqual(sum(math.exp(log_difference_probability(d, 1, strength))
                                       for d in range(-4, 5)), 1)
            for d in range(-4, 5):
                self.assertAlmostEqual(log_difference_probability(d, 1, strength),
                                       log_difference_probability(-d, -1, strength))

    def infer(self, values):
        case = dict(context_facet='task', query_paper_id='A')
        facets = {'A':{f:{f} for f in FACETS}}
        evidence = Evidence(case, (), (), ())
        pairs = [dict(differences={'problem':v}) for v in values]
        with patch('ordinal_intent.paired_evidence', return_value=pairs):
            return ordinal_intent(evidence, facets, {})

    def test_consistent_strong_evidence_and_reversal(self):
        self.assertEqual(self.infer([4, 4, 4, 4])['directions']['problem'], 'different')
        self.assertEqual(self.infer([-4, -4, -4, -4])['directions']['problem'], 'similar')

    def test_ties_and_empty_evidence_do_not_invent_direction(self):
        for values in ([], [0, 0, 0, 0], [4, -4, 4, -4]):
            self.assertTrue(self.infer(values)['abstained'])

    def test_magnitude_changes_posterior(self):
        strong = self.infer([4, 4, 4, 4])['posterior'][0]['probability']
        weak = self.infer([1, 1, 1, 1])['posterior'][0]['probability']
        self.assertGreater(strong, weak)

    def test_common_policy_preserves_raw_and_explicitly_falls_back(self):
        raw = dict.fromkeys(FACETS, 'unknown')
        raw.update(task='similar', problem='different')
        frozen = dict(raw)
        result, policy = ranking_directions('task', raw)
        self.assertEqual(raw, frozen)
        self.assertEqual(result['problem'], 'different')
        self.assertTrue(all(result[f]=='ignore' for f in FACETS if f not in ('task','problem')))
        self.assertEqual(policy, 'unique_inferred_focus')
        for raw in (dict.fromkeys(FACETS, 'unknown'), dict.fromkeys(FACETS, 'similar')):
            result, policy = ranking_directions('task', raw)
            self.assertEqual(result, dict.fromkeys(FACETS, 'similar'))
            self.assertEqual(policy, 'profile_similar_fallback')


if __name__ == '__main__':
    unittest.main()
