"""Boundary, baseline equivalence and statistical-unit checks, not score tuning."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

from data_io import (DATA_ROOT, FACETS, PROJECT, Evidence, evidence_for, load_public, new_output,
                     read_json, shared_representation, write_json)
from methods import DEFAULTS, MODELS, bayes_h, paired_evidence, predict_all
from baseline_common import search_vocabulary
from run_benchmark import legacy_parity, predict_condition
from evaluate import METRICS, load_truth, paired_comparisons, score_predictions, summarize
from test_observation_data import fixture
from build_observation_data import build


def controlled(values, query=None):
    facets = {p:{f:{f+' anchor'} for f in FACETS} for p in ('A','S','D')}
    facets['D']['problem'] = {'other problem'}
    case = dict(case_id='T', user_id='U', query_paper_id='A', context_facet='task', cutoff='2026-03-01T00:02:00Z')
    reactions, exposures = [], []
    action_pair = {0:('view','view'), 1:('view','click'), 3:('view','like'), -4:('like','dislike')}
    for i, value in enumerate(values):
        exposure_id = 'X'+str(i)
        exposures.append(dict(exposure_id=exposure_id, session_id='T', user_id='U', paper_ids=['S','D'],
                              timestamp='2026-03-01T00:01:00Z'))
        for pid, action in zip(('S','D'), action_pair[value]):
            reactions.append(dict(session_id='T', user_id='U', exposure_id=exposure_id, paper_id=pid,
                                  interaction_type=action, timestamp='2026-03-01T00:01:01Z'))
    queries = (() if query is None else (dict(session_id='T', user_id='U', query_id='Q', text=query,
                                            timestamp='2026-03-01T00:01:02Z'),))
    return Evidence(case, tuple(reactions), tuple(queries), tuple(exposures)), facets


class InferenceTests(unittest.TestCase):
    def test_no_evidence_abstains(self):
        evidence, facets = controlled([])
        result = bayes_h(evidence, facets, DEFAULTS, search_vocabulary(facets))
        self.assertTrue(result['abstained'])
        self.assertEqual(len(result['posterior']), 8)
        self.assertAlmostEqual(sum(r['probability'] for r in result['posterior']), 1)
        self.assertEqual(result['directions']['problem'], 'unknown')

    def test_bayes_enumeration_matches_exact_likelihood(self):
        evidence, facets = controlled([3]*4)
        result = bayes_h(evidence, facets, DEFAULTS, search_vocabulary(facets))
        expected = .8**4/(.8**4+.2**4+6*.5**4)
        self.assertEqual(result['directions']['problem'], 'different')
        self.assertAlmostEqual(result['posterior'][0]['probability'], expected)

    def test_soft_query_can_be_overcome_by_opposing_reactions(self):
        evidence, facets = controlled([3]*4, 'problem: more papers using problem anchor')
        result = predict_all(evidence, facets)
        self.assertEqual(result['direction_search']['directions']['problem'], 'similar')
        self.assertEqual(result['vote']['directions']['problem'], 'similar')
        self.assertEqual(result['bayes_h']['directions']['problem'], 'different')

    def test_vote_is_not_delta_magnitude(self):
        evidence, facets = controlled([1,1,1,-4])
        result = predict_all(evidence, facets)
        self.assertEqual(result['vote']['directions']['problem'], 'different')
        self.assertEqual(result['direction_behavior']['directions']['problem'], 'unknown')

    def test_tied_actions_are_not_directional_evidence(self):
        evidence, facets = controlled([0]*4)
        result = predict_all(evidence, facets)
        for model in ('vote','bayes_h','direction_behavior'):
            self.assertEqual(result[model]['directions']['problem'], 'unknown')

    def test_confounding_pair_is_not_matched(self):
        evidence, facets = controlled([3]*4)
        facets['D']['method'] = {'another method'}
        self.assertTrue(all(not r['differences'] for r in paired_evidence(evidence, facets)))
        self.assertEqual(predict_all(evidence, facets)['bayes_h']['directions']['problem'], 'unknown')

    def test_context_is_not_a_focus_hypothesis(self):
        evidence, facets = controlled([3]*4)
        result = predict_all(evidence, facets)['bayes_h']
        self.assertTrue(all(r['focus'] != 'task' for r in result['posterior']))

    def test_future_and_other_user_logs_do_not_change_prediction(self):
        evidence, facets = controlled([3]*4)
        case = dict(evidence.case, candidate_ids=['SECRET_POOL'])
        condition = dict(exposures=list(evidence.exposures), reactions=list(evidence.reactions))
        future = dict(evidence.reactions[-1], interaction_type='dislike', timestamp='2026-03-02T00:00:00Z')
        wrong_user = dict(evidence.reactions[-1], user_id='OTHER', interaction_type='dislike')
        clean = evidence_for(case, condition, list(evidence.queries))
        condition['reactions'] += [future, wrong_user]
        dirty = evidence_for(case, condition, list(evidence.queries))
        self.assertNotIn('candidate_ids', dirty.case)
        self.assertEqual(predict_all(clean, facets), predict_all(dirty, facets))

    def test_candidate_pool_membership_is_not_estimator_input(self):
        evidence, facets = controlled([3]*4)
        condition = dict(exposures=list(evidence.exposures), reactions=list(evidence.reactions))
        a = evidence_for(dict(evidence.case, candidate_ids=['C1']), condition, [])
        b = evidence_for(dict(evidence.case, candidate_ids=['C2','C3']), condition, [])
        self.assertEqual(predict_all(a, facets), predict_all(b, facets))


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp_parent = DATA_ROOT / '.test-tmp'
        tmp_parent.mkdir(exist_ok=True)
        cls.tmp = tempfile.TemporaryDirectory(prefix='benchmark_', dir=tmp_parent)
        cls.root = Path(cls.tmp.name).resolve()
        assert cls.root.is_relative_to(DATA_ROOT)
        source = cls.root / 'source'
        config = fixture(source)
        config_path = cls.root / 'config.json'
        write_json(config_path, config)
        cls.dataset = cls.root / 'dataset'
        build(source, config_path, cls.dataset)
        cls.public = load_public(cls.dataset)
        cls.profiles, cls.vectors, cls.cutoff = shared_representation(cls.public)
        cls.predictions = [r for condition in cls.public['conditions']
                           for r in predict_condition(cls.public, condition, cls.profiles, cls.vectors, DEFAULTS)]

    @classmethod
    def tearDownClass(cls):
        assert cls.root.is_relative_to(DATA_ROOT)
        cls.tmp.cleanup()

    def test_all_four_baselines_equal_original_runner_for_every_fixture_case(self):
        path = PROJECT / 'scripts/exp_d/run_exp_d.py'
        spec = importlib.util.spec_from_file_location('legacy_fixture_test', path)
        legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy)
        for condition, logs in self.public['conditions'].items():
            rows = legacy.predict({}, self.public['facets'], self.public['cases'], logs['reactions'],
                dict(profile_history=self.public['history'], profile_searches=self.public['history_queries'],
                     cutoff=self.cutoff, exposures=logs['exposures'], searches=self.public['queries'],
                     direction_margin=.25, min_direction_pairs=2))
            actual = {(r['case_id'],r['model']):r for r in self.predictions if r['condition'] == condition}
            for expected in rows:
                for field, value in expected.items():
                    row = actual[expected['case_id'],expected['model']]
                    self.assertEqual(row['legacy_ranking'] if field=='ranking' else row[field], value)

    def test_all_nonuniform_methods_share_exact_profile_weights(self):
        for row in self.predictions:
            case = next(c for c in self.public['cases'] if c['case_id'] == row['case_id'])
            if row['model'] != 'fixed_similar':
                self.assertEqual(row['facet_importance'], self.profiles[case['user_id']]['facet_importance'])

    def test_ground_truth_changes_cannot_change_public_predictions(self):
        path = self.dataset / 'ground_truth/session_intents.jsonl'
        original = path.read_bytes()
        try:
            path.write_text('{"hidden":"poisoned labels must never reach public loader"}\n', encoding='utf-8')
            changed = load_public(self.dataset)
            condition = next(iter(changed['conditions']))
            predictions = predict_condition(changed, condition, self.profiles, self.vectors, DEFAULTS)
            self.assertEqual(predictions, [r for r in self.predictions if r['condition'] == condition])
        finally:
            path.write_bytes(original)

    def test_evaluator_complete_matrix_and_unknown_metrics(self):
        rows = score_predictions(self.predictions, self.public['cases'], load_truth(self.dataset), self.public['condition_metadata'])
        self.assertEqual(len(rows), len(self.public['cases'])*len(self.public['conditions'])*len(MODELS))
        for row in rows:
            if row['predicted_direction'] == 'unknown':
                self.assertEqual(row['metrics']['direction_accuracy'], 0)
                self.assertEqual(row['metrics']['coverage'], 0)
        summary, _ = summarize(rows)
        baseline = next(r for r in summary if r['group']=='overall' and r['model']=='profile_similar')
        self.assertEqual(baseline['direction_accuracy'], .5)
        self.assertEqual(baseline['joint_accuracy'], 0)

    def test_output_overwrite_and_outside_scope_rejected(self):
        with self.assertRaises(ValueError):
            new_output(PROJECT / 'results/not_allowed')
        with self.assertRaises(ValueError):
            new_output(DATA_ROOT / 'results')
        with self.assertRaises(ValueError):
            new_output(DATA_ROOT / 'datasets/observation_v1')


class StatisticsTests(unittest.TestCase):
    def test_repeated_rows_do_not_create_extra_independent_units(self):
        rows = []
        for cluster, value, count in (('A',1.,100),('B',0.,1)):
            for i in range(count):
                rows.append(dict(model='profile_similar', cluster=cluster, design_id=cluster, anchor=cluster,
                    case_id=cluster+str(i), noise=.2, query_mode='none', focus='problem', candidate_source='real_only',
                    true_direction='similar', metrics={m:value for m in METRICS}))
        summary, _ = summarize(rows)
        overall = next(r for r in summary if r['group']=='overall')
        self.assertEqual(overall['direction_accuracy'], .5)
        self.assertEqual(overall['clusters'], 2)

    def test_paired_bootstrap_uses_cluster_differences(self):
        values = {(model,'overall',cluster):{m:i/10 for m in METRICS}
                  for i,model in enumerate(MODELS) for cluster in ('A','B','C')}
        comparisons = paired_comparisons(values, 20)
        row = next(r for r in comparisons if r['comparison']=='bayes_vs_delta' and r['metric']=='ndcg10')
        self.assertAlmostEqual(row['delta'], .2)
        self.assertAlmostEqual(row['ci_low'], .2)
        self.assertAlmostEqual(row['ci_high'], .2)
        self.assertEqual(row['clusters'], 3)


if __name__ == '__main__':
    unittest.main()
