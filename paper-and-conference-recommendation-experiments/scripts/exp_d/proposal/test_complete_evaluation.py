"""Original metric parity, oracle isolation, and full-run integration checks."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from data_io import DATA_ROOT, FACETS, read_json, read_rows, write_json
from evaluate import (ORACLE, legacy_summary, macro_f1, oracle_predictions,
                      score_predictions, summarize)
from methods import DEFAULTS, MODELS
from baseline_common import aggregate, intent_scores, ranked
from experiment_runner import evaluate_predictions
from run_benchmark import run
import test_benchmark as benchmark_tests


class CompleteEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        benchmark_tests.ContractTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        benchmark_tests.ContractTests.tearDownClass.__func__(cls)

    def test_original_metrics_match_original_evaluator_exactly(self):
        from evaluate import load_truth
        truth = load_truth(self.dataset)
        details = score_predictions(self.predictions,self.public['cases'],truth,self.public['condition_metadata'])
        labels = {}
        for r in truth['labels']:
            labels.setdefault(r['case_id'],{})[r['candidate_id']] = r['relevance']
        all_original = []
        for condition in self.public['conditions']:
            rows = evaluate_predictions([r for r in self.predictions if r['condition']==condition],
                self.public['cases'],labels,{r['case_id']:'test' for r in self.public['cases']},[5,10],truth['intents'])
            expected = {(r['case_id'],r['model']):r['metrics'] for r in rows}
            for r in details:
                if r['condition']==condition:
                    self.assertEqual(r['legacy_metrics'],expected[r['case_id'],r['model']])
            all_original.extend(rows)
        expected = {r['model']:r for r in aggregate(all_original) if r['group']=='overall'}
        actual = {r['model']:r for r in legacy_summary(details) if r['group']=='overall'}
        for model in MODELS:
            self.assertEqual(actual[model],expected[model])

    def test_oracle_uses_true_weights_and_directions_without_mutating_public(self):
        from evaluate import load_truth
        truth = load_truth(self.dataset)
        before = copy.deepcopy(self.predictions)
        oracles = oracle_predictions(self.public['cases'],self.public['conditions'],truth,self.vectors)
        self.assertEqual(self.predictions,before)
        cases = {r['case_id']:r for r in self.public['cases']}
        for row in oracles:
            intent = truth['intents'][row['case_id']]
            self.assertEqual(row['facet_importance'],intent['facet_importance'])
            self.assertEqual(row['directions'],intent['directions'])
            self.assertTrue(row['privileged_information'])
            expected = ranked(cases[row['case_id']],ORACLE,
                intent_scores(cases[row['case_id']],intent['facet_importance'],intent['directions'],self.vectors))
            self.assertEqual(row['ranking'],expected['ranking'])
        rows = score_predictions(self.predictions+oracles,self.public['cases'],truth,self.public['condition_metadata'],True)
        oracle = [r for r in rows if r['model']==ORACLE]
        self.assertTrue(all(r['metrics']['importance_mae']==0 for r in oracle))
        self.assertTrue(all(r['metrics']['direction_accuracy']==1 for r in oracle))
        with self.assertRaises(ValueError):
            score_predictions(self.predictions,self.public['cases'],truth,self.public['condition_metadata'],True)

    def test_compliance_ceiling_and_supplied_context_not_counted_as_focus(self):
        from evaluate import load_truth
        rows = score_predictions(self.predictions,self.public['cases'],load_truth(self.dataset),self.public['condition_metadata'])
        self.assertTrue(all(r['metrics']['intent_compliance@5']<=.2 for r in rows))
        self.assertTrue(all(r['metrics']['intent_compliance@10']<=.1 for r in rows))
        summary,_ = summarize(rows)
        baseline = next(r for r in summary if r['model']=='profile_similar' and r['group']=='overall')
        self.assertEqual(baseline['direction_accuracy'],.5)
        self.assertEqual(baseline['legacy_direction_accuracy'],.75)

    def test_complete_runner_needs_dataset_only_and_exports_full_report(self):
        results = DATA_ROOT/'results'
        results.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.complete_test_',dir=results) as parent:
            target = Path(parent)/'run'
            run(self.dataset,target,bootstrap_repetitions=20)
            manifest = read_json(target/'manifest.json')
            self.assertEqual(manifest['status'],'complete')
            n = len(self.public['cases'])*len(self.public['conditions'])
            self.assertEqual(manifest['prediction_rows'],n*len(MODELS))
            self.assertEqual(manifest['oracle_rows'],n)
            self.assertEqual(len(read_rows(target/'oracle_predictions.jsonl')),n)
            self.assertEqual(set(read_json(target/'conclusions.json')['best_public_on_pilot'].values()) & {ORACLE},set())
            text = (target/'report.md').read_text(encoding='utf-8')
            self.assertEqual(text.count('```mermaid'),2)
            self.assertIn('Compliance@5',text)
            self.assertIn('19 thật + 1 tổng hợp',text)
            self.assertTrue((target/'legacy_summary.csv').exists())
            with self.assertRaises(ValueError):
                run(self.dataset,target,bootstrap_repetitions=20)


class FocusF1Tests(unittest.TestCase):
    def test_unknown_is_missed_not_removed_from_f1(self):
        self.assertEqual(macro_f1([('similar','similar',1),('different','different',1)]),1)
        self.assertAlmostEqual(macro_f1([('similar','similar',1),('different','unknown',1)]),.5)
        self.assertEqual(macro_f1([('similar','unknown',1),('different','unknown',1)]),0)


if __name__ == '__main__':
    unittest.main()
