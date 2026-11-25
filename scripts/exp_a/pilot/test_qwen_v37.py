"""Review additions, source coverage hints, and historical audit isolation."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'data/exp_a'))
import build_exp_a as base
import extraction_v3 as v3


class CoverageReviewChecks(unittest.TestCase):
    def setUp(self):
        self.paper = dict(paper_id='P000001', title='Document retrieval', abstract=
            'We introduce hashing for document retrieval. We use cosine similarity. '
            'Our model does not improve accuracy on noisy inputs.')
        self.empty = dict(paper_id='P000001', **{f: [] for f in base.FACET_NAMES})
        self.draft = dict(self.empty, task=[dict(concept='document retrieval', evidence_id='A0')],
            method=[dict(concept='hashing', evidence_id='A0')],
            contribution=[dict(concept='hashing', evidence_id='A0')])

    def extract(self, replies, paper=None):
        paper = paper or self.paper
        candidates = iter(replies)
        with tempfile.TemporaryDirectory() as directory:
            value, meta = v3.annotate(paper, '', dict(prompt_version='3.7', max_attempts=len(replies),
                max_new_tokens=2048, seed=42, dataset_resource_filter=True), {},
                lambda messages, seed: (json.dumps(next(candidates)), dict(usage={})),
                Path(directory) / 'last_failure.json')
        meta['prompt_version'] = '3.7'
        base.validate_annotation(value, paper, meta)
        return value, meta

    def test_actual_review_restores_methods_and_finding_condition(self):
        papers = {r['paper_id']: r for r in base.read_jsonl(ROOT/'data/processed/papers.jsonl')}
        notes = {r['paper_id']: r for r in base.read_jsonl(
            ROOT/'data/exp_a/generated_v3_6_pilot50/annotation_metadata.jsonl')}
        replies = [json.loads(a['raw_output']) for a in notes['P002586']['attempt_scores']]
        value, meta = self.extract(replies, papers['P002586'])
        self.assertEqual([r['concept'] for r in value['method']], ['semi-supervised training', 'speaker adaptation'])
        self.assertEqual(len(value['contribution']), 1)
        self.assertIn('Tamil', value['contribution'][0]['concept'])
        self.assertIn('when significantly more test data than training data is available', value['contribution'][0]['concept'])
        self.assertTrue(meta['validation_passed'])

    def test_additions_do_not_delete_valid_draft_items(self):
        review = dict(self.empty, method=[dict(concept='cosine similarity', evidence_id='A1')],
            contribution=[dict(concept='model does not improve accuracy on noisy inputs', evidence_id='A2')])
        value, meta = self.extract([self.draft, review])
        self.assertEqual({r['concept'] for r in value['method']}, {'hashing', 'cosine similarity'})
        self.assertEqual({r['concept'] for r in value['contribution']},
                         {'hashing', 'model does not improve accuracy on noisy inputs'})
        self.assertEqual([r['concept'] for r in value['task']], ['document retrieval'])
        self.assertTrue(meta['validation_passed'])
        altered = copy.deepcopy(meta)
        altered['attempt_scores'][1]['applied_output'] = altered['attempt_scores'][1]['raw_output']
        with self.assertRaisesRegex(ValueError, 'review application'):
            base.validate_annotation(value, self.paper, altered)

    def test_shorter_review_cannot_drop_existing_finding_condition(self):
        paper = dict(self.paper, abstract='For French, our model improves accuracy.')
        draft = dict(self.empty, contribution=[dict(concept='For French, our model improves accuracy', evidence_id='A0')])
        review = dict(self.empty, contribution=[dict(concept='our model improves accuracy', evidence_id='A0')])
        value, _ = self.extract([draft, review], paper)
        self.assertEqual([r['concept'] for r in value['contribution']], ['For French, our model improves accuracy'])

    def test_expansion_with_inserted_source_words_replaces_unqualified_finding(self):
        paper = dict(self.paper, abstract='For Tamil, our model consistently improves accuracy.')
        draft = dict(self.empty, contribution=[dict(concept='model improves accuracy', evidence_id='A0')])
        review = dict(self.empty, contribution=[dict(concept='For Tamil, our model consistently improves accuracy', evidence_id='A0')])
        value, _ = self.extract([draft, review], paper)
        self.assertEqual([r['concept'] for r in value['contribution']],
                         ['For Tamil, our model consistently improves accuracy'])

    def test_invalid_draft_item_can_be_repaired_without_preserving_it(self):
        draft = dict(self.draft, method=[dict(concept='invented algorithm', evidence_id='A0')])
        value, meta = self.extract([draft, self.draft])
        self.assertEqual([r['concept'] for r in value['method']], ['hashing'])
        self.assertTrue(meta['validation_passed'])

    def test_unsupported_review_addition_stays_flagged(self):
        review = dict(self.draft, method=[dict(concept='invented algorithm', evidence_id='A0')])
        _, meta = self.extract([self.draft, review])
        self.assertTrue(meta['fallback_used'])
        self.assertTrue(meta['attempt_scores'][1]['validation_errors'])

    def test_preserving_condition_does_not_hide_unrelated_review_duplicates(self):
        paper = dict(self.paper, abstract='For French, our model improves accuracy. We introduce hashing.')
        draft = dict(self.empty, contribution=[dict(concept='For French, our model improves accuracy', evidence_id='A0')])
        review = dict(self.empty, contribution=[dict(concept='our model improves accuracy', evidence_id='A0'),
            dict(concept='hashing', evidence_id='A1'), dict(concept='hashing', evidence_id='A1')])
        _, meta = self.extract([draft, review], paper)
        self.assertTrue(meta['fallback_used'])
        self.assertTrue(any('duplicate' in e for e in meta['attempt_scores'][1]['validation_errors']))

    def test_malformed_full_json_cannot_hide_behind_preservation(self):
        broken = dict(self.draft)
        del broken['method']
        value, meta = self.extract([self.draft, broken, self.draft])
        self.assertFalse(meta['attempt_scores'][1]['schema_valid'])
        self.assertEqual(meta['attempts_used'], 3)
        self.assertEqual([r['concept'] for r in value['method']], ['hashing'])

    def test_inventory_recovers_after_nonlist_facet_without_crashing(self):
        broken = dict(self.draft, method='hashing')
        value, meta = self.extract([broken, broken, self.draft])
        self.assertEqual(meta['attempts_used'], 3)
        self.assertFalse(meta['attempt_scores'][0]['schema_valid'])
        self.assertTrue(meta['validation_passed'])
        self.assertEqual([r['concept'] for r in value['method']], ['hashing'])

    def test_duplicate_with_bad_evidence_id_can_be_repaired_without_crashing(self):
        for evidence_id in ('A99', []):
            with self.subTest(evidence_id=evidence_id):
                broken = dict(self.draft, method=self.draft['method'] +
                    [dict(concept='hashing', evidence_id=evidence_id)])
                value, meta = self.extract([broken, self.draft])
                self.assertTrue(meta['validation_passed'])
                self.assertEqual([r['concept'] for r in value['method']], ['hashing'])

    def test_source_inventory_highlights_uncited_methods_artifacts_and_negative_findings(self):
        draft = dict(self.empty, task=self.draft['task'])
        candidates = v3.coverage_candidates(self.paper, draft)
        self.assertIn('A0', candidates['contribution'])
        self.assertIn('A2', candidates['contribution'])
        self.assertIn('A1', candidates['method'])
        covered = dict(self.draft, method=self.draft['method'] + [dict(concept='cosine similarity', evidence_id='A1')])
        self.assertNotIn('A1', v3.coverage_candidates(self.paper, covered)['method'])

    def test_nonresearch_empty_output_is_still_valid(self):
        paper = dict(self.paper, title='Download book', abstract='Thank you for downloading this book from our digital library.')
        value, meta = self.extract([self.empty, self.empty], paper)
        self.assertTrue(meta['validation_passed'])
        self.assertTrue(all(value[f] == [] for f in base.FACET_NAMES))

    def test_known_prompt36_provenance_migrates_only_with_same_prompt(self):
        fingerprint = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        current = dict(config=dict(extraction_protocol='two_pass_v3', prompt_version='3.6'), input_hashes={},
            generator_version=base.GENERATOR_VERSION, generator_sha256=fingerprint(Path(base.__file__)),
            protocol_sha256=fingerprint(Path(v3.__file__)))
        previous = dict(current, generator_version='3.7',
            generator_sha256='12c7ea9bed1e1224a2908c6116a3a76c9c5d8998929876a6f79605abe42825cd',
            protocol_sha256='29fb3eb7518ca5740f8652615a3a7e7142bbf4c1f1bbed243c841ab7d1640f3e')
        self.assertTrue(base.compatible_provenance(previous, current))
        self.assertFalse(base.compatible_provenance(previous, dict(current, config=dict(current['config'], prompt_version='3.7'))))
        self.assertFalse(base.compatible_provenance(dict(previous, protocol_sha256='unknown'), current))


if __name__ == '__main__':
    unittest.main()
