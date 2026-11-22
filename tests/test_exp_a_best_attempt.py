"""Best-attempt fallback regressions without model loading or live outputs."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'data/exp_a'))
import build_exp_a as a


FACETS = ('problem', 'task', 'method', 'dataset', 'contribution')


def paper(paper_id='P000001'):
    return dict(paper_id=paper_id, source='csfcube', source_id=paper_id[1:],
                title='Document retrieval',
                abstract='We use ranking for document retrieval. We improve semantic matching.',
                year=None, domain='information_technology', scope_evidence=['CS'])


def response(paper_id='P000001', **facets):
    return dict(paper_id=paper_id, **{facet: facets.get(facet, []) for facet in FACETS})


def item(concept, evidence_id='A0'):
    return dict(concept=concept, evidence_id=evidence_id)


def config():
    return dict(corpus='papers.jsonl', output_dir='out', model='Qwen/test',
                revision='test-only', device='cpu', cache_dir='models',
                prompt='prompt.md', guideline='guide.md', prompt_version='test',
                guideline_version='test', max_new_tokens=2048, max_attempts=3,
                temperature=0.7, top_p=0.8, top_k=20, seed=42)


class BestAttemptCheck(unittest.TestCase):
    def annotate(self, candidates, selected_paper=None):
        raws = [candidate if isinstance(candidate, str) else json.dumps(candidate)
                for candidate in candidates]
        replies = iter(raws)

        def generate_text(messages, seed):
            return next(replies), dict(usage={'input_tokens': 10, 'output_tokens': 20},
                                      generation_seconds=0)

        with tempfile.TemporaryDirectory() as directory:
            value, metadata = a.annotate(selected_paper or paper(), 'Extract supported concepts.',
                                         config(), {}, generate_text,
                                         Path(directory) / 'last_failure.json')
        return value, metadata, raws

    def assert_audit(self, metadata, raws):
        self.assertEqual(metadata['attempts_used'], len(raws))
        self.assertEqual([attempt['attempt'] for attempt in metadata['attempt_scores']],
                         list(range(1, len(raws) + 1)))
        self.assertEqual([attempt['raw_output'] for attempt in metadata['attempt_scores']], raws)
        self.assertTrue(all(isinstance(attempt['score'], (int, float))
                            for attempt in metadata['attempt_scores']))

    def test_exhausted_retries_choose_earlier_best_and_keep_invalid_concept(self):
        best = response(task=[item('document retrieval', 'T0')], method=[item('ranking')],
                        contribution=[item('semantic matching', 'A1')],
                        problem=[item('invented concept')])
        worse = response(method=[item('invented technique')])
        value, metadata, raws = self.annotate([worse, best, worse])
        self.assertEqual(metadata['attempt'], 2)
        self.assertTrue(metadata['fallback_used'])
        self.assertEqual(value['method'][0]['concept'], 'ranking')
        self.assertEqual(value['problem'][0]['concept'], 'invented concept')
        self.assertEqual(value['problem'][0]['evidence'], 'We use ranking for document retrieval.')
        self.assertTrue(metadata['validation_errors'])
        self.assert_audit(metadata, raws)
        scores = [attempt['score'] for attempt in metadata['attempt_scores']]
        self.assertGreater(scores[1], scores[0])
        self.assertGreater(scores[1], scores[2])

    def test_grounded_nonempty_candidate_outscores_empty_review_candidates(self):
        best = response(task=[item('document retrieval', 'T0')], method=[item('ranking')],
                        contribution=[item('semantic matching', 'A1')],
                        problem=[item('invented concept')])
        value, metadata, raws = self.annotate([best, response(), response('P999999')])
        self.assertEqual(metadata['attempt'], 1)
        self.assertTrue(metadata['fallback_used'])
        self.assertEqual(value['contribution'][0]['concept'], 'semantic matching')
        self.assert_audit(metadata, raws)
        scores = [attempt['score'] for attempt in metadata['attempt_scores']]
        self.assertGreater(scores[0], scores[1])
        self.assertGreater(scores[0], scores[2])

    def test_wrong_paper_id_is_corrected_and_flagged_in_selected_fallback(self):
        wrong = response('P999999', task=[item('document retrieval', 'T0')],
                         method=[item('ranking')],
                         contribution=[item('semantic matching', 'A1')])
        value, metadata, raws = self.annotate([wrong, wrong, wrong])
        self.assertEqual(value['paper_id'], 'P000001')
        self.assertEqual(value['method'][0]['concept'], 'ranking')
        self.assertEqual(metadata['attempt'], 1)
        self.assertTrue(metadata['fallback_used'])
        self.assertIn('paper_id', ' '.join(metadata['validation_errors']))
        self.assert_audit(metadata, raws)

    def test_candidate_reports_all_errors_and_retains_unresolved_concept(self):
        bad = response('P999999', problem=[item('ranking'), item('ranking')],
                       task={}, method=[item('invented technique')],
                       dataset=[item('unresolved dataset', 'A999')],
                       contribution=[dict(concept='semantic matching', evidence_id='A1', extra=True)])
        value, metadata, raws = self.annotate([bad, bad, bad])
        self.assertEqual(value['dataset'],
                         [dict(concept='unresolved dataset', evidence='', source='unresolved')])
        errors = ' '.join(metadata['validation_errors']).lower()
        for fragment in ('paper_id', 'task', 'method', 'dataset', 'evidence_id', 'duplicate', 'contribution'):
            with self.subTest(issue=fragment):
                self.assertIn(fragment, errors)
        self.assertGreaterEqual(len(metadata['validation_errors']), 6)
        self.assertTrue(metadata['fallback_used'])
        self.assert_audit(metadata, raws)

    def test_duplicate_grounded_items_cannot_inflate_attempt_score(self):
        candidate = response(task=[item('document retrieval', 'T0')], method=[item('ranking')],
                             contribution=[item('invented contribution')])
        duplicated = copy.deepcopy(candidate)
        duplicated['method'] *= 10
        value, metadata, raws = self.annotate([candidate, duplicated, 'not JSON'])
        scores = [attempt['score'] for attempt in metadata['attempt_scores']]
        self.assertLessEqual(scores[1], scores[0])
        self.assertEqual(value['method'],
                         [dict(concept='ranking', evidence='We use ranking for document retrieval.', source='abstract')])
        self.assert_audit(metadata, raws)

    def test_retention_ranks_invalid_shortening_without_dropping_phrase(self):
        selected_paper = paper()
        selected_paper['abstract'] = 'alpha beta gamma delta epsilon zeta eta theta iota kappa.'
        better = response(method=[item('alpha gamma zeta eta iota kappa')])  # 6/10 words
        worse = response(method=[item('alpha zeta kappa')])  # 3/10 words
        value, metadata, raws = self.annotate([better, worse, worse], selected_paper)
        self.assertEqual(metadata['attempt'], 1)
        self.assertTrue(metadata['fallback_used'])
        self.assertEqual(value['method'][0]['concept'], 'alpha gamma zeta eta iota kappa')
        self.assertEqual(value['method'][0]['evidence'], selected_paper['abstract'])
        self.assertTrue(metadata['validation_errors'])
        self.assertGreater(metadata['attempt_scores'][0]['score'], metadata['attempt_scores'][1]['score'])
        self.assert_audit(metadata, raws)

    def test_five_supported_facets_outrank_many_exact_items_in_one_facet(self):
        selected_paper = paper()
        selected_paper['abstract'] = 'alpha beta gamma delta epsilon zeta eta theta iota kappa.'
        broader = response(**{facet: [item('alpha gamma delta zeta eta iota kappa')]
                              for facet in FACETS})  # 7/10 source words in each facet
        broader['contribution'].append(item('invented contribution'))
        exact_phrases = ('alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta',
                         'theta', 'iota', 'kappa', 'alpha beta', 'beta gamma', 'gamma delta',
                         'delta epsilon', 'epsilon zeta', 'zeta eta', 'eta theta',
                         'theta iota', 'iota kappa')
        narrower = response(method=[item(phrase) for phrase in exact_phrases],
                            task=[item('invented task')])
        value, metadata, raws = self.annotate([narrower, broader, narrower], selected_paper)
        self.assertEqual(metadata['attempt'], 2)
        self.assertTrue(all(value[facet] for facet in FACETS))
        self.assertGreater(metadata['attempt_scores'][1]['score'], metadata['attempt_scores'][0]['score'])
        self.assertTrue(metadata['fallback_used'])
        self.assert_audit(metadata, raws)

    def test_all_malformed_attempts_still_return_five_arrays_with_audit(self):
        value, metadata, raws = self.annotate(['not JSON', '{', '{"paper_id":'])
        self.assertEqual(value, dict(paper_id='P000001', **{facet: [] for facet in FACETS}))
        self.assertTrue(metadata['fallback_used'])
        self.assertTrue(metadata['validation_errors'])
        self.assertIn(metadata['attempt'], (1, 2, 3))
        self.assert_audit(metadata, raws)

    def test_zero_score_tie_preserves_parseable_unknown_labels(self):
        parsed = response(dataset=[item('unknown dataset', 'A999')])
        value, metadata, raws = self.annotate(['not JSON', parsed, '{'])
        self.assertEqual([row['score'] for row in metadata['attempt_scores']], [0, 0, 0])
        self.assertEqual(metadata['attempt'], 2)
        self.assertEqual(value['dataset'],
                         [dict(concept='unknown dataset', evidence='', source='unresolved')])
        self.assertTrue(metadata['fallback_used'])
        self.assertEqual(a.validate_annotation(value, paper(), metadata)['dataset'], ['unknown dataset'])
        self.assert_audit(metadata, raws)

    def test_fallback_audit_cannot_hide_selected_raw_quality_errors(self):
        candidate = response(method=[item('invented technique')],
                             dataset=[item('unknown dataset', 'A999')])
        value, metadata, _ = self.annotate([candidate, candidate, candidate])
        tampered = copy.deepcopy(metadata)
        tampered['validation_errors'] = [issue for issue in tampered['validation_errors']
                                         if 'method[' not in issue]
        self.assertTrue(tampered['validation_errors'])
        for attempt in tampered['attempt_scores']:
            attempt['validation_errors'] = [issue for issue in attempt['validation_errors']
                                            if 'method[' not in issue]
        with self.assertRaises(ValueError):
            a.validate_annotation(value, paper(), tampered)

    def test_known_policy_22_upgrade_requires_other_provenance_to_match(self):
        current = dict(generator_version='2.3', generator_sha256='current-build',
                       config={'model': 'Qwen/test'}, input_hashes={'corpus': 'original'}, schema={})
        previous = dict(current, generator_version='2.2',
                        generator_sha256='a9aafd069b8c1ec12ae0079e05a2272c854839c889da621964c27c61b66b3e68')
        self.assertTrue(a.compatible_provenance(previous, current))
        self.assertFalse(a.compatible_provenance(dict(previous, input_hashes={'corpus': 'changed'}), current))
        self.assertFalse(a.compatible_provenance(dict(previous, generator_sha256='unknown-build'), current))

    def test_valid_success_includes_attempt_scores_without_fallback(self):
        valid = response(task=[item('document retrieval', 'T0')], method=[item('ranking')],
                         contribution=[item('semantic matching', 'A1')])
        value, metadata, raws = self.annotate([valid])
        self.assertEqual(value['method'][0]['concept'], 'ranking')
        self.assertEqual(metadata['attempt'], 1)
        self.assertFalse(metadata['fallback_used'])
        self.assertEqual(metadata['validation_errors'], [])
        self.assert_audit(metadata, raws)

    def test_singe_verb_form_is_distinct_from_sing(self):
        selected_paper = paper()
        value = response(method=[item('singe')])
        selected_paper['abstract'] = 'We are singeing documents.'
        self.assertEqual(a.ground_response(value, selected_paper)['method'][0]['concept'], 'singe')
        selected_paper['abstract'] = 'We are singing documents.'
        with self.assertRaises(ValueError):
            a.ground_response(value, selected_paper)

    def test_malformed_encoding_or_nesting_cannot_stop_later_papers(self):
        for raw in (json.dumps(response(method=[item(chr(0xd800))])), '[' * 1100):
            with self.subTest(kind='surrogate' if raw.startswith('{') else 'nesting'):
                self.assert_malformed_batch_completes(raw)

    def test_nonstandard_json_numbers_cannot_leak_into_audit_metadata(self):
        for number in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(number=number), self.assertRaises(ValueError):
                a.parse_generation('{"extra": ' + number + '}')

    def assert_malformed_batch_completes(self, malformed_raw):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            papers = [paper('P000001'), paper('P000002')]
            (root / 'papers.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in papers), encoding='utf-8')
            for name in ('prompt.md', 'guide.md'):
                (root / name).write_text('Extract supported concepts.', encoding='utf-8')
            settings = config()
            visited = []

            def extract(selected_paper, instruction):
                visited.append(selected_paper['paper_id'])
                if selected_paper['paper_id'] == 'P000001':
                    candidates = [malformed_raw] * 3
                else:
                    candidates = [response('P000002', task=[item('document retrieval', 'T0')],
                                           method=[item('ranking')],
                                           contribution=[item('semantic matching', 'A1')])]
                value, metadata, _ = self.annotate(candidates, selected_paper)
                return value, metadata

            with patch.object(a, 'load_qwen', return_value=extract):
                manifest = a.generate(root, settings)
            self.assertEqual(manifest['status'], 'complete')
            self.assertEqual(manifest['count'], 2)
            self.assertEqual(visited, ['P000001', 'P000002'])
            self.assertEqual(a.check_outputs(root, settings)['count'], 2)
            facets = [json.loads(line) for line in (root / 'out/facets_silver.jsonl').read_text(encoding='utf-8').splitlines()]
            metadata = [json.loads(line) for line in (root / 'out/annotation_metadata.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(facets[0], dict(paper_id='P000001', **{facet: [] for facet in FACETS}))
            self.assertTrue(metadata[0]['fallback_used'])
            self.assertTrue(metadata[0]['validation_errors'])
            self.assert_audit(metadata[0], [malformed_raw] * 3)
            self.assertEqual(facets[1]['method'], ['ranking'])
            self.assertFalse(metadata[1]['fallback_used'])

    def test_generate_persists_every_fallback_and_resume_does_not_reextract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            papers = [paper('P000001'), paper('P000002')]
            (root / 'papers.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in papers), encoding='utf-8')
            for name in ('prompt.md', 'guide.md'):
                (root / name).write_text('Extract supported concepts.', encoding='utf-8')
            settings = config()
            raw_audits = {}

            def extract(selected_paper, instruction):
                if selected_paper['paper_id'] == 'P000001':
                    candidate = response('P000001', method=[item('invented technique')],
                                         dataset=[item('unknown dataset', 'A999')])
                    replies = [candidate, candidate, candidate]
                else:
                    replies = ['not JSON', '{', '{"paper_id":']
                value, metadata, raws = self.annotate(replies, selected_paper)
                raw_audits[selected_paper['paper_id']] = raws
                return value, metadata

            with patch.object(a, 'load_qwen', return_value=extract):
                manifest = a.generate(root, settings)
            self.assertEqual(manifest['status'], 'complete')
            self.assertEqual(manifest['count'], 2)
            self.assertEqual(manifest['missing_ids'], [])
            self.assertEqual(manifest['failed_annotations'], {})
            self.assertEqual(a.check_outputs(root, settings)['count'], 2)
            out = root / 'out'
            facets = [json.loads(line) for line in (out / 'facets_silver.jsonl').read_text(encoding='utf-8').splitlines()]
            metadata = [json.loads(line) for line in (out / 'annotation_metadata.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(facets[0]['method'], ['invented technique'])
            self.assertEqual(facets[0]['dataset'], ['unknown dataset'])
            self.assertEqual(facets[1], dict(paper_id='P000002', **{facet: [] for facet in FACETS}))
            for annotation in metadata:
                self.assertTrue(annotation['fallback_used'])
                self.assertTrue(annotation['validation_errors'])
                self.assert_audit(annotation, raw_audits[annotation['paper_id']])
            before_resume = (out / 'annotation_metadata.jsonl').read_bytes()
            with patch.object(a, 'load_qwen', side_effect=AssertionError('Completed fallback was re-extracted')):
                self.assertEqual(a.generate(root, settings)['count'], 2)
            self.assertEqual((out / 'annotation_metadata.jsonl').read_bytes(), before_resume)
            self.assertEqual(a.check_outputs(root, settings)['count'], 2)

            # Removing the fallback declaration must restore strict grounding validation.
            metadata[0]['fallback_used'] = False
            (out / 'annotation_metadata.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in metadata), encoding='utf-8')
            manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
            manifest['files']['annotation_metadata.jsonl'] = hashlib.sha256((out / 'annotation_metadata.jsonl').read_bytes()).hexdigest()
            (out / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaises(ValueError):
                a.check_outputs(root, settings)


if __name__ == '__main__':
    unittest.main()
