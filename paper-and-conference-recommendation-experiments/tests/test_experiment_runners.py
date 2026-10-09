"""CPU ranking regressions, leakage boundaries and end-to-end result artifacts."""
import importlib
import json
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'scripts'))
sys.path.insert(0, str(PROJECT / 'tests'))
import baseline_common as baseline
import experiment_runner as runner
import test_experiment_pipeline as fixtures
from build_corpus import read_jsonl
from download_sources import write_json


class RankingChecks(unittest.TestCase):
    def test_metrics_match_hand_calculation_and_handle_short_pools(self):
        grades = dict(a=2, b=1, c=0)
        perfect = baseline.ranking_metrics(['a', 'b', 'c'], grades, [1, 10])
        self.assertEqual(perfect['ndcg@10'], 1)
        self.assertEqual(perfect['recall@1'], 0.5)
        self.assertAlmostEqual(perfect['precision@10'], 2 / 3)
        swapped = baseline.ranking_metrics(['b', 'a', 'c'], grades, [2])
        expected = (1 + 3 / math.log2(3)) / (3 + 1 / math.log2(3))
        self.assertAlmostEqual(swapped['ndcg@2'], expected)
        self.assertEqual(baseline.ranking_metrics(['c', 'b', 'a'], grades, [2])['mrr@2'], 0.5)
        with self.assertRaises(ValueError):
            baseline.ranking_metrics(['a', 'a', 'b'], grades, [2])

    def test_no_positive_metrics_remain_undefined_with_denominators(self):
        metrics = baseline.ranking_metrics(['a'], dict(a=0), [5])
        self.assertIsNone(metrics['ndcg@5'])
        self.assertIsNone(metrics['recall@5'])
        self.assertIsNone(metrics['mrr@5'])
        self.assertEqual(metrics['precision@5'], 0)
        row = dict(model='m', group='holdout', positive_candidates=0, metrics=metrics)
        summary = baseline.aggregate([row])[0]
        self.assertEqual(summary['positive_cases'], 0)
        self.assertEqual(summary['defined_cases']['ndcg@5'], 0)

    def test_tfidf_smoothing_and_cosine_have_known_values(self):
        vectors = baseline.tfidf(dict(a='alpha alpha beta', b='beta', c=''))
        alpha = 2 * (math.log(4 / 2) + 1)
        beta = math.log(4 / 3) + 1
        self.assertAlmostEqual(vectors['a']['alpha'], alpha / math.sqrt(alpha**2 + beta**2))
        self.assertAlmostEqual(baseline.dot(vectors['a'], vectors['a']), 1)
        self.assertEqual(vectors['c'], {})

    def test_ties_and_random_predictions_are_independent_of_input_order(self):
        case = dict(case_id='Q0001', candidate_ids=['b', 'a'])
        ranked = baseline.ranked(case, 'tie', dict(b=0, a=0))
        self.assertEqual([row['paper_id'] for row in ranked['ranking']], ['a', 'b'])
        self.assertEqual(baseline.random_scores(case, 42),
                         baseline.random_scores(dict(case, candidate_ids=['a', 'b']), 42))
        with self.assertRaises(ValueError):
            baseline.ranked(case, 'bad', dict(a=float('nan'), b=0))

    def test_decay_and_recent_history_follow_new_interest_and_reject_future(self):
        vectors = dict(old={'old': 1}, new={'new': 1})
        history = [dict(user_id='U0001', paper_id='old', interaction_type='like', timestamp='2026-01-01T00:00:00Z'),
                   dict(user_id='U0001', paper_id='new', interaction_type='like', timestamp='2026-03-31T00:00:00Z')]
        options = dict(cutoff='2026-04-01T00:00:00Z')
        static = baseline.history_profiles(history, vectors, **options)['U0001']
        decay = baseline.history_profiles(history, vectors, half_life_days=30, **options)['U0001']
        recent = baseline.history_profiles(history, vectors, recent_start='2026-03-01T00:00:00Z', **options)['U0001']
        self.assertEqual(static['old'], static['new'])
        self.assertGreater(decay['new'], decay['old'])
        self.assertEqual(recent, {'new': 1})
        with self.assertRaisesRegex(ValueError, 'Future'):
            baseline.history_profiles(history, vectors, cutoff='2026-03-31T00:00:00Z')

    def test_directions_use_matched_feedback_and_search_negation(self):
        fs = fixtures.test_facets()
        q,a,b = 'P000001','P000005','P000017'
        fs[a] = {f:set(v) for f,v in fs[q].items()}
        fs[b] = dict(fs[a],method={'m1'})
        case = dict(case_id='D00001',query_paper_id=q,context_facet='problem')
        shown,events = [],[]
        for i in range(2):
            xid = f'X{i}'
            shown.append(dict(exposure_id=xid,session_id='D00001',paper_ids=[a,b]))
            for pid,kind in ((a,'click'),(b,'like')):
                events.append(dict(exposure_id=xid,session_id='D00001',paper_id=pid,interaction_type=kind))
        directions,_ = baseline.direction_estimate(case,events,[],shown,fs)
        self.assertEqual(directions['method'],'different')
        unknown,_ = baseline.direction_estimate(case,[],[],[],fs)
        self.assertEqual(unknown['method'],'unknown')
        query = dict(session_id='D00001',query_id='Q1',text='method: alternatives to m0',
                     timestamp='2026-01-01T00:00:00Z')
        parsed = baseline.parse_search(query['text'],fs)
        self.assertEqual(parsed['method']['exclude'],{'m0'})
        self.assertFalse(parsed['method']['include'])
        searched,_ = baseline.direction_estimate(case,[],[query],[],fs)
        self.assertEqual(searched['method'],'different')
        mismatched = dict(fs[b],task={'other'})
        fs[b] = mismatched
        directions,_ = baseline.direction_estimate(case,events,[],shown,fs)
        self.assertEqual(directions['method'],'unknown')

    def test_missing_method_is_not_rewarded_as_different_and_unknown_uses_context(self):
        fs = dict(q=dict(problem={'p'},task=set(),method={'old'},dataset=set(),contribution=set()),
                  p=dict(problem={'p'},task=set(),method=set(),dataset=set(),contribution=set()))
        case = dict(query_paper_id='q',candidate_ids=['p'])
        weights = dict.fromkeys(baseline.FACETS,0.0)
        weights.update(problem=.5,method=.5)
        self.assertEqual(baseline.intent_scores(case,weights,dict(method='different'),baseline.facet_vectors(fs))['p'],-1)
        fs['p']['method'] = {'new'}
        vectors = baseline.facet_vectors(fs)
        unknown = baseline.intent_scores(case,weights,dict(method='unknown'),vectors)
        similar = baseline.intent_scores(case,weights,dict(method='similar'),vectors)
        self.assertEqual(unknown,similar)

    def test_importance_mae_and_pooled_direction_f1(self):
        case = dict(case_id='D1',candidate_ids=['a','b'])
        weights = dict.fromkeys(baseline.FACETS,0.0)
        weights.update(problem=.6,method=.4)
        row = baseline.ranked(case,'m',dict(a=2,b=1))
        row.update(facet_importance=weights,directions=dict.fromkeys(baseline.FACETS,'unknown'))
        row['directions']['problem'] = 'similar'
        hidden = dict(facet_importance=weights,directions=dict.fromkeys(baseline.FACETS,'ignore'))
        hidden['directions'].update(problem='similar',method='different')
        details = runner.evaluate_predictions([row],[case],{'D1':dict(a=2,b=1)},{'D1':'none'},[5],{'D1':hidden})
        self.assertEqual(details[0]['metrics']['importance_mae'],0)
        self.assertEqual(details[0]['metrics']['direction_coverage'],.5)
        summary = baseline.aggregate(details)[0]
        self.assertEqual(summary['direction_macro_f1'],.5)


class RunnerChecks(unittest.TestCase):
    setUp = fixtures.PipelineChecks.setUp
    build = fixtures.PipelineChecks.build

    small_configs = fixtures.PipelineChecks.small_configs
    corrupt = fixtures.PipelineChecks.corrupt

    def test_each_runner_prefixes_hidden_truth_artifacts_and_reproducibility(self):
        self.small_configs()
        expected = dict(b={'random','text_tfidf','equal_facets','weighted_facets'},
                        c={'popularity','text_history','facet_no_search','facet_history'},
                        d={'fixed_similar','profile_similar','direction_behavior','direction_search','oracle_intent'},
                        e={'popularity','static','recent','decay'})
        for name in ('b','c','d','e'):
            self.build(name)
            predictor = importlib.import_module(f'exp_{name}.run_exp_{name}').predict
            def checked(papers,facets,cases,history,options):
                self.assertTrue(all(not set(case) & {'labels','directions','facet_importance','query_mode',
                                                     'latent_preferences','group'} for case in cases))
                if name != 'b':
                    cutoff = options['cutoff']
                    self.assertTrue(all(r['timestamp'] < cutoff for r in history))
                    self.assertTrue(all(r['timestamp'] < cutoff for r in options['searches']))
                    self.assertTrue(all(r['timestamp'] < cutoff for r in options['exposures']))
                    self.assertNotIn('truth',options)
                return predictor(papers,facets,cases,history,options)
            report = runner.run_experiment(self.root,name,checked)
            destination = self.root / f'results/exp_{name}/' / ('test' if name == 'b' else 'holdout')
            self.assertEqual({p.name for p in destination.iterdir()},runner.RESULT_FILES)
            self.assertEqual({r['model'] for r in report['summary']},expected[name])
            predictions = read_jsonl(destination / 'predictions.jsonl')
            self.assertEqual(len(predictions),report['cases']*len(expected[name]))
            if name == 'd':
                self.assertTrue(all(r.get('privileged_information') for r in predictions if r['model'] == 'oracle_intent'))
                self.assertTrue(all(not r.get('privileged_information') for r in predictions if r['model'] != 'oracle_intent'))
                self.assertIn('direction_macro_f1',report['summary'][0])
            if name == 'e':
                self.assertTrue({'period_2','period_3','period_4','stable','drift'}
                                <= {r['group'] for r in report['summary']})
            before = {p.name:p.read_bytes() for p in destination.iterdir()}
            with self.assertRaisesRegex(ValueError,'already exist'):
                runner.run_experiment(self.root,name,predictor)
            runner.run_experiment(self.root,name,predictor,overwrite=True)
            self.assertEqual(before,{p.name:p.read_bytes() for p in destination.iterdir()})

    def test_dry_run_does_not_score_or_write_and_results_cannot_overlap_data(self):
        self.small_configs()
        self.build('b')
        def unexpected(*args):
            self.fail('Dry run invoked scorer')
        report = runner.run_experiment(self.root, 'b', unexpected, dry_run=True)
        self.assertTrue(report['dry_run'])
        self.assertFalse((self.root / 'results').exists())
        for output in ('data/exp_a/generated', '../outside', 'results'):
            with self.assertRaises(ValueError):
                runner.run_experiment(self.root, 'b', unexpected, output=output)

    def test_failed_write_releases_lock_and_unrelated_files_are_preserved(self):
        self.small_configs()
        self.build('b')
        from exp_b.run_exp_b import predict
        destination = self.root / 'results/exp_b/test'
        with patch.object(runner, 'write_jsonl', side_effect=OSError('disk full')):
            with self.assertRaisesRegex(OSError, 'disk full'):
                runner.run_experiment(self.root, 'b', predict)
        self.assertFalse((destination / '.run.lock').exists())
        unrelated = destination / 'my_notes.txt'
        unrelated.write_text('keep', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'unrelated'):
            runner.run_experiment(self.root, 'b', predict, overwrite=True)
        self.assertEqual(unrelated.read_text(encoding='utf-8'), 'keep')

    def test_input_changes_during_loading_or_scoring_prevent_publication(self):
        self.small_configs()
        self.build('b')
        from exp_b.run_exp_b import predict
        source = self.root / 'data/exp_b/ground_truth/retrieval_labels.jsonl'
        original = source.read_bytes()
        load_cases = runner.evaluation_cases

        def change_while_loading(*args):
            values = load_cases(*args)
            source.write_bytes(original + b'\n')
            return values

        with patch.object(runner, 'evaluation_cases', side_effect=change_while_loading):
            with self.assertRaisesRegex(ValueError, 'changed while loading'):
                runner.run_experiment(self.root, 'b', predict)
        self.assertFalse((self.root / 'results').exists())
        source.write_bytes(original)

        def change_while_scoring(*args):
            values = predict(*args)
            source.write_bytes(original + b'\n')
            return values

        with self.assertRaisesRegex(ValueError, 'changed while scoring'):
            runner.run_experiment(self.root, 'b', change_while_scoring)
        self.assertFalse((self.root / 'results').exists())

    def test_incomplete_predictions_and_future_history_are_rejected(self):
        case = dict(case_id='U0001', user_id='U0001', candidate_ids=['a', 'b'])
        prediction = baseline.ranked(case, 'm', dict(a=1, b=0))
        with self.assertRaises(ValueError):
            runner.evaluate_predictions([prediction, prediction], [case], {'U0001': dict(a=1, b=0)},
                                        dict(U0001='holdout'), [5])
        self.small_configs()
        self.build('c')
        self.corrupt('c', 'generated/interactions_train.jsonl',
                     lambda rows: rows[0].update(timestamp='2027-01-01T00:00:00Z'))
        from exp_c.run_exp_c import predict
        with self.assertRaisesRegex(ValueError, 'time|temporal|order|history'):
            runner.run_experiment(self.root, 'c', predict)


if __name__ == '__main__':
    unittest.main()
