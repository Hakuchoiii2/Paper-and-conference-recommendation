"""Extraction policy regressions; model responses are supplied without GPU inference."""
import copy
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'data/exp_a'))
import build_exp_a as a


class RetryPolicyCheck(unittest.TestCase):
    def test_regular_verb_forms_are_supported_but_synonyms_are_not(self):
        cases = (
            ('represent word meaning in context', 'representing word meaning in context', True),
            ('extract instances', 'extracting instances', True),
            ('use ranking', 'using ranking', True),
            ('run experiments', 'running experiments', True),
            ('study models', 'studies models', True),
            ('predicting labels', 'predicted labels', True),
            ('fill documents', 'filling documents', True),
            ('file documents', 'filing documents', True),
            ('hop', 'hopping', True),
            ('hope', 'hoping', True),
            ('rate', 'rated', True),
            ('filing documents', 'filling documents', False),
            ('hopping', 'hoping', False),
            ('hopping', 'hoped', False),
            ('rat', 'rated', False),
            ('analyse models', 'evaluate models', False),
            ('policy', 'police', False),
            ('the', 'thing', False),
        )
        for concept, evidence, accepted in cases:
            with self.subTest(concept=concept, evidence=evidence):
                paper = dict(paper_id='P000015', title='Research', abstract=evidence)
                value = dict(paper_id=paper['paper_id'], **{f: [] for f in a.FACET_NAMES})
                value['task'] = [dict(concept=concept, evidence_id='A0')]
                if accepted:
                    try:
                        grounded = a.ground_response(value, paper)
                    except ValueError as error:
                        self.fail(f'Equivalent verb form was rejected: {error}')
                    self.assertEqual(grounded['task'][0]['concept'], concept)
                    self.assertEqual(grounded['task'][0]['evidence'], evidence)
                else:
                    with self.assertRaises(ValueError):
                        a.ground_response(value, paper)

    def test_parenthetical_examples_are_optional_but_other_parentheses_are_not(self):
        cases = (
            ('extract instances of noun categories and relations',
             "We consider extracting instances of noun categories (e.g., 'athlete', 'team') "
             "and relations (e.g., 'playsForTeam(athlete, team)').", True),
            ('alpha gamma', 'alpha (e.g., beta(delta(epsilon))) gamma.', True),
            ('alpha gamma', 'alpha (for example, beta) gamma.', True),
            ('alpha gamma', 'alpha (beta) gamma.', False),
            ('alpha gamma', 'alpha (SVM) gamma.', False),
            ('alpha gamma', 'alpha (not beta) gamma.', False),
            ('alpha gamma', 'alpha (e.g., beta gamma.', False),
            ('beta', 'alpha (e.g., beta) gamma.', True),
            ('alpha omega', 'alpha beta gamma delta omega (e.g., ignored).', False),
        )
        for concept, evidence, accepted in cases:
            with self.subTest(concept=concept, evidence=evidence):
                coverage = a.source_phrase_coverage(concept, evidence)
                if accepted:
                    self.assertGreaterEqual(coverage, 0.7)
                else:
                    self.assertLess(coverage, 0.7)

    def test_example_abbreviations_remain_in_one_selectable_sentence(self):
        for example in ('e.g. beta', 'e.g., beta', 'e. g. beta', 'E.G. beta'):
            with self.subTest(example=example):
                evidence = f'alpha ({example}) gamma.'
                paper = dict(paper_id='P000017', title='Research',
                             abstract=evidence + ' We report results.')
                value = dict(paper_id=paper['paper_id'], **{f: [] for f in a.FACET_NAMES})
                value['task'] = [dict(concept='alpha gamma', evidence_id='A0')]
                try:
                    grounded = a.ground_response(value, paper)
                except ValueError as error:
                    self.fail(f'The example sentence could not be selected: {error}')
                self.assertEqual(grounded['task'][0]['evidence'], evidence)
                self.assertEqual(a.evidence_options(paper)['A1']['evidence'], 'We report results.')

    def test_known_policy_21_upgrade_requires_all_other_provenance_to_match(self):
        current = dict(generator_version='2.2', generator_sha256='new-build',
                       config={'model': 'Qwen/test'}, input_hashes={'corpus': 'original'}, schema={})
        previous = dict(current, generator_version='2.1',
                        generator_sha256='49419379061eb134e3d4de9772dd7c34ce4e688502a34952a7df5e4b572a206b')
        self.assertTrue(a.compatible_provenance(previous, current))
        self.assertFalse(a.compatible_provenance(dict(previous, input_hashes={'corpus': 'changed'}), current))
        self.assertFalse(a.compatible_provenance(dict(previous, generator_sha256='unknown-build'), current))

    def test_shortening_retains_seventy_percent_of_the_smallest_source_span(self):
        paper = dict(paper_id='P000001', title='Retrieval',
                     abstract='alpha beta gamma delta epsilon zeta eta theta iota kappa.')
        for concept, accepted in (
                ('gamma delta', True),
                ('alpha gamma delta zeta eta iota kappa', True),  # 7/10
                ('alpha gamma zeta eta iota kappa', False),      # 6/10
                ('kappa alpha', False),
                ('alpha invented kappa', False)):
            with self.subTest(concept=concept):
                value = dict(paper_id=paper['paper_id'], **{f: [] for f in a.FACET_NAMES})
                value['method'] = [dict(concept=concept, evidence_id='A0')]
                if accepted:
                    try:
                        self.assertEqual(a.ground_response(value, paper)['method'][0]['concept'], concept)
                    except ValueError as error:
                        self.fail(f'Acceptable shortening was rejected: {error}')
                else:
                    with self.assertRaises(ValueError):
                        a.ground_response(value, paper)
        # A repeated leading word must not force an unnecessarily long source span.
        paper['abstract'] = 'alpha unused unused alpha beta gamma delta.'
        value['method'] = [dict(concept='alpha gamma delta', evidence_id='A0')]
        try:
            self.assertEqual(a.ground_response(value, paper)['method'][0]['concept'], 'alpha gamma delta')
        except ValueError as error:
            self.fail(f'The shortest supporting span was rejected: {error}')

    def test_sparse_review_and_invalid_output_share_the_three_attempt_budget(self):
        self.assertTrue(callable(getattr(a, 'annotate', None)), 'Retry policy needs a testable annotation boundary')
        paper = dict(paper_id='P000003', title='Retrieval', abstract='We use ranking for retrieval.')
        config = dict(max_attempts=3, max_new_tokens=2048, seed=42,
                      temperature=0.7, top_p=0.8, top_k=20)
        empty = dict(paper_id=paper['paper_id'], **{f: [] for f in a.FACET_NAMES})
        sparse = dict(empty, method=[dict(concept='ranking', evidence_id='A0')],
                      task=[dict(concept='retrieval', evidence_id='T0')])
        dense = dict(sparse, contribution=[dict(concept='ranking', evidence_id='A0')])
        bad = dict(sparse, method=[dict(concept='invented technique', evidence_id='A0')])
        cases = (
            ('two_empty', [dense], 1, False),
            ('three_empty', [sparse, sparse], 2, True),
            ('five_empty', [empty, empty], 2, True),
            ('review_finds_labels', [empty, dense], 2, True),
            ('invalid_then_review', [bad, sparse, dense], 3, True),
            ('three_invalid', [bad, bad, bad], None, False),
            ('sparse_without_review_budget', [bad, bad, sparse], None, False),
        )
        with tempfile.TemporaryDirectory() as directory:
            for name, responses, attempt, reviewed in cases:
                with self.subTest(case=name):
                    replies = iter(responses)
                    feedback = []
                    def generate_text(messages, seed):
                        feedback.append(copy.deepcopy(messages))
                        return json.dumps(next(replies)), dict(usage={}, generation_seconds=0)
                    failure_path = Path(directory) / (name + '.json')
                    if attempt is None:
                        with self.assertRaises(a.AnnotationError):
                            a.annotate(paper, 'Extract supported concepts.', config, {}, generate_text, failure_path)
                        self.assertEqual(json.loads(failure_path.read_text())['paper_id'], 'P000003')
                    else:
                        value, metadata = a.annotate(paper, 'Extract supported concepts.', config, {}, generate_text, failure_path)
                        self.assertEqual(metadata['attempt'], attempt)
                        self.assertEqual(metadata['sparse_reviewed'], reviewed)
                        self.assertEqual(value, a.ground_response(responses[-1], paper))
                        self.assertFalse(failure_path.exists())
                    self.assertEqual(len(feedback), len(responses))
                    if reviewed:
                        self.assertTrue(any('T0' in msg['content'] and 'empty' in msg['content']
                                            for messages in feedback[1:] for msg in messages if msg['role'] == 'user'))

    def test_known_checkpoint_upgrade_preserves_dense_records_and_reviews_sparse_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            papers = [dict(paper_id=f'P00000{i}', source='csfcube', source_id=str(i), title='Retrieval',
                           abstract='We use ranking for retrieval.', year=None,
                           domain='information_technology', scope_evidence=['CS']) for i in (1, 2)]
            a.write_jsonl(root / 'papers.jsonl', papers)
            for name in ('prompt.md', 'guide.md'):
                (root / name).write_text('Extract.', encoding='utf-8')
            config = dict(corpus='papers.jsonl', output_dir='out', model='Qwen/test', revision='test-only',
                          device='cpu', cache_dir='models', prompt='prompt.md', guideline='guide.md',
                          prompt_version='1.5', guideline_version='1.0', max_new_tokens=2048,
                          max_attempts=3, temperature=0.7, top_p=0.8, top_k=20, seed=42)
            def answer(paper, instruction):
                value = dict(paper_id=paper['paper_id'], **{f: [] for f in a.FACET_NAMES})
                for facet in ('task', 'method', 'contribution'):
                    value[facet] = [dict(concept='ranking', evidence=paper['abstract'], source='abstract')]
                return value, dict(usage={}, sparse_reviewed=True)
            with patch.object(a, 'load_qwen', return_value=answer):
                a.generate(root, config)
            checkpoint = root / 'out/.exp_a_checkpoint.sqlite3'
            with closing(sqlite3.connect(checkpoint)) as db, db:
                signature = json.loads(db.execute('SELECT signature FROM run').fetchone()[0])
                signature.update(generator_version='2.0', generator_sha256='28ea4be0f55bffcaea5a74579d5b58bb9d14395a936b9f9f1225db21d9c521ab')
                db.execute('UPDATE run SET signature=?', (json.dumps(signature, sort_keys=True),))
                record = json.loads(db.execute('SELECT payload FROM annotations WHERE paper_id="P000002"').fetchone()[0])
                record['metadata'].pop('extraction_policy_version', None)
                record['metadata'].pop('sparse_reviewed', None)
                for facet in a.FACET_NAMES:
                    record['facets'][facet] = []
                    record['metadata']['evidence'][facet] = []
                db.execute('UPDATE annotations SET payload=? WHERE paper_id="P000002"', (json.dumps(record),))
            reviewed_ids = []
            def review(paper, instruction):
                reviewed_ids.append(paper['paper_id'])
                return answer(paper, instruction)
            with patch.object(a, 'load_qwen', return_value=review):
                manifest = a.generate(root, config)
                a.generate(root, config)
            self.assertEqual(reviewed_ids, ['P000002'])
            self.assertEqual(manifest['count'], 2)
            self.assertEqual(a.check_outputs(root, config)['count'], 2)
            # A new-paper cap must not hide a later legacy record needing review.
            with closing(sqlite3.connect(checkpoint)) as db, db:
                db.execute('DELETE FROM annotations WHERE paper_id="P000001"')
                db.execute('UPDATE annotations SET payload=? WHERE paper_id="P000002"', (json.dumps(record),))
            reviewed_ids.clear()
            with patch.object(a, 'load_qwen', return_value=review):
                manifest = a.generate(root, config, limit=1)
            self.assertEqual(reviewed_ids, ['P000001', 'P000002'])
            self.assertEqual(manifest['count'], 2)
            self.assertEqual(a.read_jsonl(root / 'out/facets_silver.jsonl')[1]['method'], ['ranking'])
            # A valid sparse response already reviewed by 2.1 needs no second review on upgrade.
            with closing(sqlite3.connect(checkpoint)) as db, db:
                signature = json.loads(db.execute('SELECT signature FROM run').fetchone()[0])
                signature.update(generator_version='2.1',
                                 generator_sha256='49419379061eb134e3d4de9772dd7c34ce4e688502a34952a7df5e4b572a206b')
                db.execute('UPDATE run SET signature=?', (json.dumps(signature, sort_keys=True),))
                record['metadata'].update(extraction_policy_version='2.1', sparse_reviewed=True)
                db.execute('UPDATE annotations SET payload=? WHERE paper_id="P000002"', (json.dumps(record),))
            reviewed_ids.clear()
            with patch.object(a, 'load_qwen', return_value=review):
                a.generate(root, config)
            self.assertEqual(reviewed_ids, [])


if __name__ == '__main__':
    unittest.main()
