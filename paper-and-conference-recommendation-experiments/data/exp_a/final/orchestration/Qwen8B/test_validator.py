"""Exercise the actual V-recall assessment boundary without any model inference."""
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
FROZEN = ROOT / 'data/exp_a/final/runtime'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((FROZEN / 'gold_validator.py').exists(), 'Gold-compatible validator missing')
        self.validator = load('gold_compatible_validator_test', FROZEN / 'gold_validator.py')
        self.policy = load('gold_compatible_frozen_policy_test', FROZEN / 'gold_policy.py')
        self.shared = self.policy.load_shared(FROZEN)

    def assess(self, paper, selections):
        before = self.shared.base.normalize
        original = self.shared.v3.validate_response
        with self.validator.scope(self.shared):
            value, _, assessment = self.shared.v3.assess_generation(
                json.dumps(selections), paper, '3.1', prompt_version='3.7', dataset_resource_filter=True)
        self.assertIs(self.shared.base.normalize, before)
        self.assertIs(self.shared.v3.validate_response, original)
        return value, assessment

    def selection(self, pid, **facets):
        return dict(paper_id=pid, **{f: facets.get(f, []) for f in self.shared.FACETS})

    def test_paraphrase_reorder_context_and_named_corpus(self):
        paper = dict(paper_id='P999001', title='StarCraft II game maps',
            abstract='For the main game maps, we provide a dataset of game replay data from human expert players. We also use the Corpus of Linguistic Acceptability (CoLA).')
        selected = self.selection(paper['paper_id'],
            contribution=[dict(concept='human expert game replay dataset for main StarCraft II maps', evidence_id='A0')],
            dataset=[dict(concept='Corpus of Linguistic Acceptability', evidence_id='A1')])
        value, audit = self.assess(paper, selected)
        self.assertEqual(audit['validation_errors'], [])
        self.assertTrue(audit['validation_warnings'])
        self.assertEqual(value['dataset'][0]['concept'], 'Corpus of Linguistic Acceptability')

    def test_distinct_symbols_and_separately_stated_caveat_are_accepted(self):
        paper = dict(paper_id='P999002', title='bAbI and bAbI+',
            abstract='Categorization results are significantly above chance, but not sufficient for a fully-automated process.')
        selected = self.selection(paper['paper_id'],
            dataset=[dict(concept=x, evidence_id='T0') for x in ('bAbI+', 'bAbI')],
            contribution=[dict(concept=x, evidence_id='A0') for x in (
                'Categorization results are significantly above chance',
                'categorization results are not sufficient for a fully automated process')])
        _, audit = self.assess(paper, selected)
        self.assertEqual(audit['validation_errors'], [])

    def test_rejects_wrong_source_schema_duplicate_and_new_quantity(self):
        paper = dict(paper_id='P999003', title='Accuracy study', abstract='Our model achieves 78% accuracy.')
        for selected, expected in (
            (self.selection(paper['paper_id'], contribution=[dict(concept='78% accuracy', evidence_id='A99')]), 'unknown evidence_id'),
            (self.selection(paper['paper_id'], contribution=[dict(concept='95% accuracy', evidence_id='A0')]), 'quantity absent'),
            (self.selection(paper['paper_id'], method=[dict(concept='model', evidence_id='A0')]*2), 'duplicate concept')):
            _, audit = self.assess(paper, selected)
            self.assertTrue(any(expected in x for x in audit['validation_errors']), audit)

    def test_rejects_explicit_polarity_reversal(self):
        paper = dict(paper_id='P999004', title='Model comparison', abstract='Our model does not improve classification accuracy.')
        selected = self.selection(paper['paper_id'], contribution=[dict(concept='Our model improves classification accuracy', evidence_id='A0')])
        _, audit = self.assess(paper, selected)
        self.assertTrue(any('polarity' in x for x in audit['validation_errors']), audit)

    def test_equivalent_negative_paraphrases_are_not_reversals(self):
        paper = dict(paper_id='P999009', title='Model comparison', abstract='Our model improves classification accuracy with no supervision.')
        selected = self.selection(paper['paper_id'], contribution=[dict(concept='Our model improves classification accuracy without supervision', evidence_id='A0')])
        _, audit = self.assess(paper, selected)
        self.assertEqual(audit['validation_errors'], [])
        paper['abstract'] = 'Our model does not improve classification accuracy without supervision.'
        selected['contribution'][0]['concept'] = 'Our model improves classification accuracy without supervision'
        _, audit = self.assess(paper, selected)
        self.assertTrue(any('polarity' in x for x in audit['validation_errors']), audit)

    def test_multiplier_ranges_and_normalized_numbers(self):
        paper = dict(paper_id='P999005', title='Communication efficiency', abstract='We reduce communication by 10-100x using 1,048 examples.')
        selected = self.selection(paper['paper_id'], contribution=[dict(
            concept='10–100 times reduction in communication using 1048 examples', evidence_id='A0')])
        _, audit = self.assess(paper, selected)
        self.assertEqual(audit['validation_errors'], [])

    def test_scientific_notation_is_not_a_fabricated_quantity(self):
        paper = dict(paper_id='P999007', title='Model training', abstract='We use a learning rate of 0.0001.')
        selected = self.selection(paper['paper_id'], method=[dict(concept='learning rate of 1e-4', evidence_id='A0')])
        _, audit = self.assess(paper, selected)
        self.assertEqual(audit['validation_errors'], [])

    def test_question_paraphrase_and_reordering_have_no_lexical_score_penalty(self):
        paper = dict(paper_id='P999006', title='Search reliability',
            abstract='We investigate whether robust search generalizes to noisy inputs.')
        selected = self.selection(paper['paper_id'], problem=[dict(
            concept='uncertainty about generalization of robust search to noisy inputs', evidence_id='A0')])
        _, audit = self.assess(paper, selected)
        self.assertEqual(audit['validation_errors'], [])
        self.assertEqual(audit['score'], 100)
        self.assertFalse(audit['semantic_entailment_verified'])

    def test_complete_gold_is_checked_without_reference_lookup_by_validator(self):
        origin = ROOT / 'data/exp_a/ground_truth/gold_review'
        papers = {x['paper_id']: x for x in map(json.loads, (origin/'review_papers.jsonl').read_text(encoding='utf-8').splitlines())}
        proof = [json.loads(x) for x in (origin/'gpt_review_evidence.jsonl').read_text(encoding='utf-8').splitlines()]
        failures = []
        for row in proof:
            selected = self.selection(row['paper_id'], **{f: [{k: x[k] for k in ('concept', 'evidence_id')} for x in row['evidence'][f]] for f in self.shared.FACETS})
            _, audit = self.assess(papers[row['paper_id']], selected)
            if audit['validation_errors']:
                failures.append(dict(paper_id=row['paper_id'], errors=audit['validation_errors']))
        self.assertEqual(failures, [])


if __name__ == '__main__':
    unittest.main()
