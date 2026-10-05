"""Target-sized generator checks using explicitly test-only facet fixtures."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from data import build_experiments as builder
except ImportError:
    builder = None

FACETS = ('problem', 'task', 'method', 'dataset', 'contribution')


def test_facets():
    return {f'P{i+1:06}': dict(problem={f'p{i%4}'}, task={f't{i%5}'},
                             method={f'm{(i//4)%4}'}, dataset={f'd{i%3}'},
                             contribution={f'c{i%7}'}) for i in range(400)}


def templates():
    definitions = [('same_problem', 200, {'problem': 'similar'}),
                   ('same_problem_different_method', 200, {'problem': 'similar', 'method': 'different'}),
                   ('same_method_different_problem', 200, {'method': 'similar', 'problem': 'different'}),
                   ('similar_task', 200, {'task': 'similar'}),
                   ('different_dataset', 200, {'dataset': 'different'}),
                   ('same_problem_same_method', 200, {'problem': 'similar', 'method': 'similar'}),
                   ('similar_contribution', 150, {'contribution': 'similar'}),
                   ('mixed_intent', 150, {'problem': 'similar', 'task': 'similar', 'method': 'different'})]
    return dict(version='concept_overlap_v1', templates=[dict(intent_type=name, quota=quota,
                constraints={facet: active.get(facet, 'ignore') for facet in FACETS})
                for name, quota, active in definitions])


def simulator_config():
    return dict(seed=42, rule_version='profile_first_v1', concepts_per_facet=2,
                targeted_exposure_fraction=0.8, noise_std=0.15,
                interaction_thresholds=[-0.25, 0.05, 0.2, 0.4],
                positive_weight_range=[0.5, 1.0], negative_weight_range=[-1.0, -0.5])


class DatasetChecks(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(builder, 'B–E dataset generators are not implemented')

    def test_literal_relevance_and_intents_keep_missing_facets_ineligible(self):
        for query, candidate, expected in [({'a'}, {'a'}, 2), ({'a','b'}, {'b','c'}, 1),
                                            ({'a'}, {'z'}, 0), (set(), {'a'}, None)]:
            self.assertEqual(builder.facet_relevance(query, candidate), expected)
        directions = dict.fromkeys(FACETS, 'ignore')
        directions.update(problem='similar', method='different')
        query = dict.fromkeys(FACETS, {'unused'})
        query.update(problem={'retrieval'}, method={'graph'})
        candidate = dict(query, method={'matrix'})
        self.assertTrue(builder.intent_satisfaction(query, candidate, directions))
        self.assertFalse(builder.intent_satisfaction(query, query, directions))
        self.assertIsNone(builder.intent_satisfaction(query, dict(candidate, method=set()), directions))

    def test_b_target_counts_labels_and_anchor_grouped_splits(self):
        config = dict(seed=42, num_queries=300, candidates_per_query=100,
                      positive_fraction=0.2, hard_negative_fraction=0.5,
                      label_rule_version='concept_overlap_v1', target_facets=list(FACETS))
        observed, truth, report = builder.build_b(test_facets(), config, random.Random(42))
        queries = observed['retrieval_queries.jsonl']
        self.assertEqual(len(queries), 300)
        self.assertEqual(len(truth['retrieval_labels.jsonl']), 30000)
        self.assertEqual(report['shortfall'], 0)
        self.assertEqual({facet: sum(q['target_facet'] == facet for q in queries) for facet in FACETS},
                         dict.fromkeys(FACETS, 60))
        split = observed['splits.json']
        by_anchor = {}
        for query in queries:
            self.assertEqual(len(set(query['candidate_ids'])), 100)
            self.assertNotIn(query['query_paper_id'], query['candidate_ids'])
            self.assertNotIn('relevance', query)
            anchor = query['query_paper_id']
            side = next(name for name, ids in split.items() if query['query_id'] in ids)
            self.assertEqual(by_anchor.setdefault(anchor, side), side)
        repeated = builder.build_b(test_facets(), config, random.Random(42))
        self.assertEqual((observed, truth, report), repeated)

    def test_b_shortage_is_reported_instead_of_fabricating_positives(self):
        facets = test_facets()
        for pid, row in facets.items():
            row['problem'] = {pid}
        config = dict(seed=42, num_queries=5, candidates_per_query=10,
                      positive_fraction=0.2, hard_negative_fraction=0.5,
                      label_rule_version='concept_overlap_v1', target_facets=['problem'])
        observed, truth, report = builder.build_b(facets, config, random.Random(42))
        self.assertEqual(observed['retrieval_queries.jsonl'], [])
        self.assertEqual(truth['retrieval_labels.jsonl'], [])
        self.assertEqual(report['shortfall'], 5)

    def test_c_target_counts_positive_negative_and_grouped_splits(self):
        config = dict(seed=42, num_cases=1500, candidates_per_case=20, positive_fraction=0.5,
                      hard_negative_fraction=0.5, label_rule_version='concept_overlap_v1')
        observed, truth, report = builder.build_c(test_facets(), config, templates(), random.Random(42))
        self.assertEqual(len(observed['intents.jsonl']), 1500)
        self.assertEqual(len(truth['intent_labels.jsonl']), 30000)
        self.assertEqual(report['shortfall'], 0)
        self.assertEqual(report['actual_by_type'], {row['intent_type']: row['quota'] for row in templates()['templates']})
        labels = {}
        for row in truth['intent_labels.jsonl']:
            labels.setdefault(row['intent_id'], set()).add(row['satisfies_intent'])
        self.assertTrue(all(values == {True, False} for values in labels.values()))
        anchors = {}
        for case in observed['intents.jsonl']:
            side = next(name for name, ids in observed['splits.json'].items() if case['intent_id'] in ids)
            self.assertEqual(anchors.setdefault(case['query_paper_id'], side), side)
        self.assertEqual((observed, truth, report), builder.build_c(test_facets(), config, templates(), random.Random(42)))

    def test_d_profile_affinity_and_target_temporal_split(self):
        preferences = {'method': {'graph': 1.0, 'matrix': -1.0}}
        self.assertEqual(builder.affinity(preferences, {'method': {'graph'}}), 1.0)
        self.assertEqual(builder.affinity(preferences, {'method': {'matrix'}}), -1.0)
        self.assertEqual(builder.affinity(preferences, {'method': {'unobserved'}}), 0.0)
        config = dict(simulator_config(), num_users=300, events_per_user=50,
                      history_events_per_user=30, start_timestamp='2026-01-01T00:00:00Z', event_step_seconds=86400)
        observed, truth, report = builder.build_d(test_facets(), config, random.Random(42))
        self.assertEqual(len(observed['users.jsonl']), 300)
        self.assertEqual(len(observed['interactions_train.jsonl']), 9000)
        self.assertEqual(len(truth['interactions_test.jsonl']), 6000)
        self.assertEqual(len(truth['latent_user_profiles.jsonl']), 300)
        self.assertEqual(report['shortfall'], 0)
        self.assertTrue(all(set(user) == {'user_id'} for user in observed['users.jsonl']))
        history, future = {}, {}
        for values, result in ((observed['interactions_train.jsonl'], history),
                               (truth['interactions_test.jsonl'], future)):
            for row in values:
                result.setdefault(row['user_id'], []).append(row)
                self.assertEqual(set(row), {'user_id','paper_id','interaction_type','timestamp'})
        for user in history:
            self.assertEqual(len(history[user]), 30)
            self.assertEqual(len(future[user]), 20)
            self.assertLess(history[user][-1]['timestamp'], future[user][0]['timestamp'])
            self.assertEqual(len({row['paper_id'] for row in history[user] + future[user]}), 50)

    def test_e_uses_shared_users_and_creates_stable_and_drift_profiles(self):
        users = [dict(user_id=f'U{i+1:04}') for i in range(300)]
        config = dict(simulator_config(), events_per_user_per_period=15, stable_fraction=0.5,
                      drift_coefficients=[0,0.5,1,1], history_periods=[1,2,3], holdout_period=4,
                      period_boundaries=['2026-01-01T00:00:00Z','2026-02-01T00:00:00Z',
                                         '2026-03-01T00:00:00Z','2026-04-01T00:00:00Z','2026-05-01T00:00:00Z'])
        observed, truth, report = builder.build_e(test_facets(), users, config, random.Random(42))
        self.assertEqual(len(observed['interactions_train.jsonl']), 13500)
        self.assertEqual(len(truth['interactions_test.jsonl']), 4500)
        self.assertEqual(len(truth['temporal_profiles.jsonl']), 1200)
        self.assertNotIn('users.jsonl', observed)
        self.assertEqual(report['group_counts'], {'stable':150, 'drift':150})
        profiles = {}
        for row in truth['temporal_profiles.jsonl']:
            profiles.setdefault(row['user_id'], []).append(row['latent_preferences'])
        for user, group in truth['period_metadata.json']['groups'].items():
            if group == 'stable':
                self.assertEqual(profiles[user][0], profiles[user][3])
            else:
                self.assertNotEqual(profiles[user][0], profiles[user][2])
                self.assertEqual(profiles[user][2], profiles[user][3])
        self.assertTrue(all(row['timestamp'] < '2026-04-01T00:00:00Z' for row in observed['interactions_train.jsonl']))
        self.assertTrue(all('2026-04-01T00:00:00Z' <= row['timestamp'] < '2026-05-01T00:00:00Z'
                            for row in truth['interactions_test.jsonl']))


if __name__ == '__main__':
    unittest.main()
