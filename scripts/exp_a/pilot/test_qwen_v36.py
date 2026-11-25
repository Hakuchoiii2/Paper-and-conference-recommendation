"""Scoped review, tied fallback, and raw/effective audit replay."""
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


class ScopedReviewChecks(unittest.TestCase):
    def setUp(self):
        self.paper = dict(paper_id='P000001', title='Document retrieval', abstract=
            'We introduce hashing for document retrieval. We evaluate using the Orion Treebank and Vega corpus.')
        self.empty = dict(paper_id='P000001', **{f: [] for f in base.FACET_NAMES})
        self.draft = dict(self.empty, method=[dict(concept='hashing', evidence_id='A0')],
            task=[dict(concept='document retrieval', evidence_id='A0')],
            contribution=[dict(concept='hashing', evidence_id='A0')])

    def extract(self, replies, version='3.6', paper=None):
        paper = paper or self.paper
        requests, candidates = [], iter(replies)
        def generate(messages, seed):
            requests.append(copy.deepcopy(messages))
            reply = next(candidates)
            return reply if isinstance(reply, str) else json.dumps(reply), dict(usage={})
        with tempfile.TemporaryDirectory() as directory:
            try:
                value, meta = v3.annotate(paper, '', dict(prompt_version=version,
                    max_attempts=len(replies), max_new_tokens=2048, seed=42,
                    dataset_resource_filter=True), {}, generate, Path(directory)/'last_failure.json')
            except ValueError as error:
                self.fail(f'Scoped review must run and keep an auditable output: {error}')
        meta['prompt_version'] = version
        base.validate_annotation(value, paper, meta)
        return value, meta, requests

    def test_dataset_review_preserves_other_valid_facets_and_original_model_response(self):
        review = dict(self.empty, dataset=[dict(concept='Orion Treebank', evidence_id='A1'),
                                           dict(concept='Vega corpus', evidence_id='A1')])
        value, meta, _ = self.extract([self.draft, review])
        self.assertTrue(meta['validation_passed'])
        for facet in ('task', 'method', 'contribution'):
            self.assertEqual([r['concept'] for r in value[facet]], [r['concept'] for r in self.draft[facet]])
        self.assertEqual([r['concept'] for r in value['dataset']], ['Orion Treebank', 'Vega corpus'])
        attempt = meta['attempt_scores'][1]
        self.assertEqual(json.loads(attempt['raw_output'])['method'], [])
        self.assertEqual(json.loads(attempt['applied_output'])['method'], self.draft['method'])
        tampered = copy.deepcopy(meta)
        tampered['attempt_scores'][1]['applied_output'] = attempt['raw_output']
        with self.assertRaisesRegex(ValueError, 'review application'):
            base.validate_annotation(value, self.paper, tampered)

    def test_invalid_facet_is_repairable_without_dropping_valid_task(self):
        draft = dict(self.draft, method=[dict(concept='hashing models', evidence_id='A0')])
        review = dict(self.empty, method=self.draft['method'])
        value, meta, _ = self.extract([draft, review])
        self.assertTrue(meta['validation_passed'])
        self.assertEqual([r['concept'] for r in value['method']], ['hashing'])
        self.assertEqual([r['concept'] for r in value['task']], ['document retrieval'])
        self.assertIn('method', meta['attempt_scores'][1]['review_facets'])

    def test_malformed_full_response_cannot_be_hidden_by_preserving_old_facets(self):
        broken = dict(self.empty)
        del broken['task']
        value, meta, _ = self.extract([self.draft, broken, self.draft])
        self.assertTrue(meta['validation_passed'])
        self.assertEqual(meta['attempts_used'], 3)
        self.assertFalse(meta['attempt_scores'][1]['schema_valid'])
        self.assertEqual(set(meta['attempt_scores'][2]['review_facets']), set(base.FACET_NAMES))

    def test_ties_prefer_latest_review_and_stagnant_feedback_changes_only_for_new_version(self):
        invalid = dict(self.draft, method=[dict(concept='hashing models', evidence_id='A0')])
        for version, selected in (('3.5', 1), ('3.6', 3)):
            with self.subTest(version=version):
                _, meta, requests = self.extract([invalid, invalid, invalid], version=version)
                self.assertTrue(meta['fallback_used'])
                self.assertEqual(meta['attempt'], selected)
                if version == '3.6':
                    self.assertNotEqual(requests[1], requests[2])
                else:
                    self.assertEqual(requests[1], requests[2])

    def test_actual_syntax_question_reviews_replace_the_false_negative_draft(self):
        papers = {r['paper_id']: r for r in base.read_jsonl(ROOT/'data/processed/papers.jsonl')}
        metadata = {r['paper_id']: r for r in base.read_jsonl(
            ROOT/'data/exp_a/generated_v3_5_pilot50/annotation_metadata.jsonl')}
        paper = papers['P003673']
        replies = [a['raw_output'] for a in metadata[paper['paper_id']]['attempt_scores']]
        value, meta, _ = self.extract(replies, paper=paper)
        self.assertEqual(meta['attempt'], 3)
        self.assertTrue(value['problem'][0]['concept'].startswith('whether '))
        self.assertNotIn('does not learn', value['problem'][0]['concept'])
        self.assertTrue(any('whether' in e for e in meta['attempt_scores'][0]['validation_errors']))

    def test_previous_prompt35_provenance_is_reusable_but_not_for_prompt36(self):
        fingerprint = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        current = dict(config=dict(extraction_protocol='two_pass_v3', prompt_version='3.5', seed=42),
            input_hashes={}, generator_version=base.GENERATOR_VERSION,
            generator_sha256=fingerprint(Path(base.__file__)), protocol_sha256=fingerprint(Path(v3.__file__)))
        saved = dict(current, generator_version='3.6',
            generator_sha256='1a8c94cb6013c24c13c26963004a6e125c19881dd1a587e474a758f3487f24a5',
            protocol_sha256='27806f24e1503603af796f5c62c462d233d4be1f2c5511df77895293693781d4')
        self.assertTrue(base.compatible_provenance(saved, current))
        self.assertFalse(base.compatible_provenance(saved,
            dict(current, config=dict(current['config'], prompt_version='3.6'))))
        self.assertFalse(base.compatible_provenance(dict(saved, protocol_sha256='unknown'), current))


if __name__ == '__main__':
    unittest.main()
