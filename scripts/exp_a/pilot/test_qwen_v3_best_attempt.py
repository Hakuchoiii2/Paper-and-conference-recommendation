"""Regression checks for scored, audited v3 extraction; no model/GPU calls."""
import copy
import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from contextlib import closing, contextmanager
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'data/exp_a'))
import build_exp_a as base
import extraction_v3 as v3


def paper(paper_id='P000001'):
    return dict(paper_id=paper_id, title='Document retrieval',
                abstract='We use ranking for document retrieval.')


def response(p, **facets):
    return dict(paper_id=p['paper_id'], **{f: facets.get(f, []) for f in base.FACET_NAMES})


class ScoredV3Checks(unittest.TestCase):
    def annotate(self, p, candidates, directory):
        requests = []
        replies = iter(candidates)
        def generate(messages, seed):
            requests.append(copy.deepcopy(messages))
            candidate = next(replies)
            raw = candidate if isinstance(candidate, str) else json.dumps(candidate)
            return raw, dict(usage=dict(input_tokens=10, output_tokens=5), generation_seconds=1)
        try:
            value, meta = v3.annotate(p, 'Extract supported source phrases.',
                                     dict(seed=42, max_attempts=3, max_new_tokens=2048), {},
                                     generate, Path(directory) / 'last_failure.json')
        except base.AnnotationError as error:
            self.fail(f'Exhausted generated outputs must return an audited fallback: {error}')
        return value, meta, requests

    def test_invalid_draft_is_reviewed_with_all_label_errors(self):
        p = paper()
        invalid = response(p, problem=[dict(concept='invented limitation', evidence_id='A0')],
                           method=[dict(concept='invented technique', evidence_id='A0')])
        valid = response(p, method=[dict(concept='ranking', evidence_id='A0')])
        with tempfile.TemporaryDirectory() as directory:
            value, meta, requests = self.annotate(p, [invalid, valid, valid], directory)
        self.assertEqual([row['stage'] for row in meta['attempt_scores']], ['extract', 'review'])
        self.assertEqual(len(meta['attempt_scores'][0]['validation_errors']), 2)
        feedback = requests[1][-1]['content']
        for text in ['problem[0]', 'method[0]', 'invented limitation', 'invented technique', 'A0', p['abstract']]:
            self.assertIn(text, feedback)
        self.assertEqual(value['method'][0]['concept'], 'ranking')
        self.assertTrue(meta['validation_passed'])

    def test_exhaustion_saves_best_earlier_attempt_without_claiming_validation(self):
        p = paper()
        better = response(p, task=[dict(concept='document retrieval', evidence_id='T0')],
                          method=[dict(concept='ranking', evidence_id='A0')],
                          problem=[dict(concept='invented limitation', evidence_id='A0')])
        worse = response(p, method=[dict(concept='invented technique', evidence_id='A0')])
        with tempfile.TemporaryDirectory() as directory:
            value, meta, _ = self.annotate(p, [better, worse, worse], directory)
            audit = json.loads((Path(directory) / 'attempt_audits/P000001.json').read_text(encoding='utf-8'))
        self.assertEqual(meta['attempt'], 1)
        self.assertEqual(meta['attempts_used'], 3)
        self.assertEqual(value['method'][0]['concept'], 'ranking')
        self.assertTrue(meta['fallback_used'])
        self.assertFalse(meta['validation_passed'])
        self.assertTrue(meta['validation_errors'])
        self.assertGreater(meta['selected_score'], meta['attempt_scores'][1]['score'])
        self.assertEqual(audit['selected_attempt'], 1)
        self.assertEqual(len(audit['attempt_scores']), 3)
        self.assertEqual(base.validate_annotation(value, p, meta)['method'], ['ranking'])

    def test_valid_short_draft_keeps_v3_rules_when_reviews_fail(self):
        p = dict(paper(), abstract='We propose a robust and computationally efficient ranking algorithm.')
        draft = response(p, method=[dict(concept='robust ranking algorithm', evidence_id='A0')])
        invalid = response(p, method=[dict(concept='invented technique', evidence_id='A0')])
        with tempfile.TemporaryDirectory() as directory:
            value, meta, _ = self.annotate(p, [draft, invalid, invalid], directory)
        self.assertEqual(meta['attempt'], 1)
        self.assertEqual(meta['attempt_scores'][0]['validation_errors'], [])
        self.assertGreater(meta['attempt_scores'][0]['score'], meta['attempt_scores'][1]['score'])
        self.assertTrue(meta['fallback_used'])
        self.assertFalse(meta['validation_passed'])
        self.assertIn('self-review', ' '.join(meta['validation_errors']))
        self.assertEqual(base.validate_annotation(value, p, meta)['method'], ['robust ranking algorithm'])

    def test_malformed_outputs_keep_all_three_attempts_and_empty_audited_shape(self):
        p = paper()
        with tempfile.TemporaryDirectory() as directory:
            value, meta, _ = self.annotate(p, ['not JSON', '{', '{"paper_id":'], directory)
        self.assertEqual(value, response(p))
        self.assertEqual(meta['attempts_used'], 3)
        self.assertTrue(meta['fallback_used'])
        self.assertFalse(meta['validation_passed'])
        self.assertEqual([a['score'] for a in meta['attempt_scores']], [0, 0, 0])
        self.assertEqual(base.validate_annotation(value, p, meta)['method'], [])

    def test_audit_files_do_not_overwrite_other_papers(self):
        with tempfile.TemporaryDirectory() as directory:
            for pid in ['P000001', 'P000002']:
                p = paper(pid)
                invalid = response(p, method=[dict(concept='invented technique', evidence_id='A0')])
                self.annotate(p, [invalid] * 3, directory)
            paths = sorted((Path(directory) / 'attempt_audits').glob('*.json'))
            self.assertEqual([p.name for p in paths], ['P000001.json', 'P000002.json'])
            self.assertEqual([json.loads(p.read_text(encoding='utf-8'))['paper_id'] for p in paths],
                             ['P000001', 'P000002'])

    def test_saved_fallback_rejects_hidden_errors_and_changed_scores(self):
        p = paper()
        invalid = response(p, method=[dict(concept='invented technique', evidence_id='A0')])
        with tempfile.TemporaryDirectory() as directory:
            value, meta, _ = self.annotate(p, [invalid] * 3, directory)
        for field in ['errors', 'score', 'selected_value', 'validation_passed']:
            changed = copy.deepcopy(meta)
            candidate = copy.deepcopy(value)
            if field == 'errors':
                changed['validation_errors'] = []
                for row in changed['attempt_scores']:
                    row['validation_errors'] = []
            elif field == 'score':
                changed['attempt_scores'][0]['score'] += 1
            elif field == 'selected_value':
                candidate['method'][0]['concept'] = 'ranking'
            else:
                changed['validation_passed'] = True
            with self.subTest(field=field), self.assertRaises(ValueError):
                base.validate_annotation(candidate, p, changed)

    def test_finding_cannot_drop_trailing_limitation(self):
        p = dict(paper(), abstract='The union of these methods is promising, although only partially successful.')
        short = response(p, contribution=[dict(concept='union of these methods is promising', evidence_id='A0')])
        with self.assertRaisesRegex(ValueError, 'caveat|qualification'):
            v3.ground_response(short, p)
        full = response(p, contribution=[dict(concept='union of these methods is promising although only partially successful', evidence_id='A0')])
        self.assertEqual(v3.ground_response(full, p)['contribution'][0]['concept'], full['contribution'][0]['concept'])

    def test_split_source_word_is_diagnosed_without_rewriting_evidence(self):
        p = dict(paper(), abstract='Morpho logically well motivated structures are learned.')
        value = response(p, contribution=[dict(concept='morphologically well motivated structures are learned', evidence_id='A0')])
        with self.assertRaisesRegex(ValueError, 'split source word'):
            v3.ground_response(value, p)
        self.assertEqual(p['abstract'], 'Morpho logically well motivated structures are learned.')

    def test_download_boilerplate_is_flagged_even_when_empty_labels_are_valid(self):
        p = dict(paper(), abstract='Thank you for downloading this book. Our book servers save in multiple countries.')
        with tempfile.TemporaryDirectory() as directory:
            value, meta, _ = self.annotate(p, [response(p)] * 3, directory)
        self.assertEqual(value, response(p))
        self.assertEqual(meta.get('source_quality', {}).get('status'), 'suspected_non_research')
        self.assertTrue(meta['source_quality']['issues'])

    def test_generate_exports_fallbacks_and_resume_does_not_reextract_them(self):
        config = json.loads((ROOT / 'data/exp_a/config_v3_pilot50.json').read_text(encoding='utf-8'))
        config['paper_ids'] = config['paper_ids'][:2]
        papers = [p for p in base.read_jsonl(ROOT / config['corpus']) if p['paper_id'] in config['paper_ids']]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['corpus', 'prompt', 'guideline']:
                target = root / config[name]
                target.parent.mkdir(parents=True, exist_ok=True)
                if name == 'corpus':
                    base.write_jsonl(target, papers)
                else:
                    shutil.copyfile(ROOT / config[name], target)
            def extract(p, instruction):
                candidate = response(p, method=[dict(concept='invented technique', evidence_id='T0')])
                return v3.annotate(p, instruction, config, {},
                                   lambda messages, seed: (json.dumps(candidate), dict(usage={})),
                                   root / config['output_dir'] / 'last_failure.json')
            with patch.object(base, 'load_qwen', return_value=extract):
                manifest = base.generate(root, config)
            self.assertEqual(manifest['count'], 2)
            self.assertEqual(manifest['missing_ids'], [])
            self.assertEqual(set(manifest['fallback_annotations']), set(config['paper_ids']))
            self.assertEqual(base.check_outputs(root, config)['status'], 'complete')
            before = (root / config['output_dir'] / 'annotation_metadata.jsonl').read_bytes()
            with patch.object(base, 'load_qwen', side_effect=AssertionError('Fallback was re-extracted')):
                self.assertEqual(base.generate(root, config)['count'], 2)
            self.assertEqual((root / config['output_dir'] / 'annotation_metadata.jsonl').read_bytes(), before)


class DatasetFilterChecks(unittest.TestCase):
    @contextmanager
    def saved_fixture(self):
        config = json.loads((ROOT / 'data/exp_a/config_v3_pilot50.json').read_text(encoding='utf-8'))
        config.update(prompt_version='3.3', prompt='data/exp_a/prompts/extraction_v3_3.md')
        p = copy.deepcopy(base.read_jsonl(ROOT / config['corpus'])[0])
        p['abstract'] = 'We evaluate on a Dutch test collection.'
        config.update(paper_ids=[p['paper_id']], dataset_resource_filter=True)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('corpus', 'prompt', 'guideline'):
                target = root / config[name]
                target.parent.mkdir(parents=True, exist_ok=True)
                if name == 'corpus':
                    base.write_jsonl(target, [p])
                else:
                    shutil.copyfile(ROOT / config[name], target)
            candidate = response(p, dataset=[dict(concept='Dutch test collection', evidence_id='A0')])
            def extract(paper, instruction):
                return v3.annotate(paper, instruction, config, {},
                                   lambda messages, seed: (json.dumps(candidate), dict(usage={})),
                                   root / config['output_dir'] / 'last_failure.json')
            with patch.object(base, 'load_qwen', return_value=extract):
                base.generate(root, config)
            yield root, config, p

    def annotate(self, p, candidate, enabled=True):
        config = dict(seed=42, max_attempts=3, max_new_tokens=2048, prompt_version='3.1',
                      dataset_resource_filter=enabled)
        with tempfile.TemporaryDirectory() as directory:
            return v3.annotate(p, '', config, {},
                               lambda messages, seed: (json.dumps(candidate), dict(usage={})),
                               Path(directory) / 'last_failure.json')

    def test_filter_removes_generic_dataset_preserving_raw_attempt_and_named_resource(self):
        p = dict(paper(), abstract='We evaluate on a Dutch test collection and on MNIST.')
        candidate = response(p, dataset=[dict(concept='Dutch test collection', evidence_id='A0'),
                                         dict(concept='MNIST', evidence_id='A0')])
        value, meta = self.annotate(p, candidate)
        baseline, old = self.annotate(p, candidate, enabled=False)
        self.assertEqual([item['concept'] for item in value['dataset']], ['MNIST'])
        self.assertEqual([item['concept'] for item in baseline['dataset']], ['Dutch test collection', 'MNIST'])
        self.assertEqual(meta['attempt_scores'], old['attempt_scores'])
        self.assertEqual(meta['selected_score'], old['selected_score'])
        self.assertEqual(meta['attempt'], old['attempt'])
        self.assertEqual(meta['postprocessing']['removed'][0]['concept'], 'Dutch test collection')
        self.assertNotIn('postprocessing', old)
        self.assertTrue(meta['validation_passed'])
        self.assertEqual(base.validate_annotation(value, p, meta)['dataset'], ['MNIST'])

    def test_filter_does_not_drop_lexical_errors_or_hide_fallback(self):
        p = dict(paper(), abstract='We evaluate on MNIST.')
        candidate = response(p, dataset=[dict(concept='MNIST corpus', evidence_id='A0')])
        value, meta = self.annotate(p, candidate)
        self.assertEqual(value['dataset'][0]['concept'], 'MNIST corpus')
        self.assertIn('postprocessing', meta)
        self.assertEqual(meta['postprocessing']['removed'], [])
        self.assertTrue(meta['fallback_used'])
        self.assertFalse(meta['validation_passed'])
        base.validate_annotation(value, p, meta)

    def test_filter_audit_cannot_be_tampered_or_switched_off_after_removal(self):
        p = dict(paper(), abstract='We evaluate on a Dutch test collection.')
        value, meta = self.annotate(p, response(p, dataset=[dict(concept='Dutch test collection', evidence_id='A0')]))
        self.assertEqual(value['dataset'], [])
        for change in ('audit', 'flag'):
            with self.subTest(change=change):
                altered = copy.deepcopy(meta)
                if change == 'audit':
                    altered['postprocessing']['removed'] = []
                else:
                    altered['request_parameters']['dataset_resource_filter'] = False
                with self.assertRaises(ValueError):
                    base.validate_annotation(value, p, altered)

    def test_reviewed_v3_records_are_not_reextracted_for_an_engine_upgrade(self):
        with self.saved_fixture() as (root, config, p):
            checkpoint = root / config['output_dir'] / '.exp_a_checkpoint.sqlite3'
            with closing(sqlite3.connect(checkpoint)) as db:
                record = json.loads(db.execute('SELECT payload FROM annotations').fetchone()[0])
                record['metadata']['extraction_policy_version'] = '3.2'
                db.execute('UPDATE annotations SET payload=?', (json.dumps(record),))
                db.commit()
            with patch.object(base, 'load_qwen', side_effect=AssertionError('Reviewed v3 record was re-extracted')):
                self.assertEqual(base.generate(root, config)['count'], 1)

    def test_resume_rejects_disabled_filter_in_checkpoint_and_jsonl(self):
        for recovery in ('checkpoint', 'jsonl', 'checkpoint_protocol', 'jsonl_protocol'):
            with self.subTest(recovery=recovery), self.saved_fixture() as (root, config, p):
                checkpoint = root / config['output_dir'] / '.exp_a_checkpoint.sqlite3'
                with closing(sqlite3.connect(checkpoint)) as db:
                    record = json.loads(db.execute('SELECT payload FROM annotations').fetchone()[0])
                    meta = record['metadata']
                    raw = next(a['raw_output'] for a in meta['attempt_scores'] if a['attempt'] == meta['attempt'])
                    restored, _, _ = v3.assess_generation(raw, p, '3.1')
                    meta['evidence'] = restored
                    meta.pop('postprocessing')
                    meta['request_parameters'].pop('dataset_resource_filter')
                    if recovery.endswith('_protocol'):
                        meta.pop('extraction_protocol')
                    record['facets'] = base.validate_annotation(restored, p, meta)
                    db.execute('UPDATE annotations SET payload=?', (json.dumps(record),))
                    db.commit()
                    if recovery.startswith('jsonl'):
                        papers, provenance, _ = base.inputs(root, config)
                        base.export(root, config, papers, provenance, db)
                        db.execute('DELETE FROM annotations')
                        db.commit()
                expected = 'annotation protocol' if recovery.endswith('_protocol') else 'dataset filter'
                with self.assertRaisesRegex(ValueError, expected):
                    base.generate(root, config)


class V32PolicyChecks(unittest.TestCase):
    def annotate(self, p, candidates):
        replies = iter(candidates)
        config = dict(seed=42, max_attempts=3, max_new_tokens=2048, prompt_version='3.2')
        with tempfile.TemporaryDirectory() as directory:
            return v3.annotate(p, '', config, {},
                               lambda messages, seed: (json.dumps(next(replies)), dict(usage={})),
                               Path(directory) / 'last_failure.json')

    def test_valid_sparse_annotations_do_not_score_lower_for_empty_facets(self):
        p = dict(paper(), abstract='Limited annotations hinder retrieval. We use ranking for document retrieval. We introduce Ranker. We evaluate on MNIST.')
        sparse = response(p, task=[dict(concept='document retrieval', evidence_id='A1')],
                          method=[dict(concept='ranking', evidence_id='A1')],
                          contribution=[dict(concept='Ranker', evidence_id='A2')])
        dense = dict(sparse, problem=[dict(concept='Limited annotations hinder retrieval', evidence_id='A0')],
                     dataset=[dict(concept='MNIST', evidence_id='A3')])
        _, a = self.annotate(p, [sparse] * 3)
        _, b = self.annotate(p, [dense] * 3)
        self.assertTrue(a['validation_passed'])
        self.assertTrue(b['validation_passed'])
        self.assertEqual(a['selected_score'], b['selected_score'])

    def test_fallback_prefers_review_detail_over_draft_copy_density(self):
        p = dict(paper(), abstract='Two language design methods based on principles derived from the denotational approach to programming language semantics are described. Several useful extensions and generalizations of Pascal emerge by applying these principles, including a solution to the array parameter problem, and a modularization facility.')
        draft = response(p, problem=[dict(concept='invented limitation', evidence_id='A0')],
                         method=[dict(concept='denotational approach to programming language semantics', evidence_id='A0')],
                         contribution=[dict(concept='useful extensions and generalizations of Pascal', evidence_id='A1')])
        review = copy.deepcopy(draft)
        review['contribution'][0]['concept'] += ' including a solution to the array parameter problem and a modularization facility'
        value, meta = self.annotate(p, [draft, review, review])
        self.assertTrue(meta['fallback_used'])
        self.assertEqual(meta['attempt'], 3)
        self.assertIn('modularization facility', value['contribution'][0]['concept'])
        base.validate_annotation(value, p, meta)

    def test_generic_collections_and_language_names_require_review(self):
        cases = [('100 discussion topics spanning over 10 Twitter events', 'We use 100 discussion topics spanning over 10 Twitter events.'),
                 ('Dutch test collection', 'We evaluate on a Dutch test collection.'),
                 ('annotated Arabic corpus', 'An annotated Arabic corpus is used.'),
                 ('Assamese', 'We run experiments on low-resource languages in Assamese, Bengali and Tamil.'),
                 ('English', 'We run experiments in English.'),
                 ('Python', 'We implement the method in Python.'),
                 ('Arabic', 'We present a technique for extracting keyphrases of Arabic documents.'),
                 ('Arabic', 'During analysis, an annotated Arabic corpus is used to extract lexical features.'),
                 ('alignment test cases', 'We compare results on sets of alignment test cases.')]
        for concept, source in cases:
            with self.subTest(concept=concept):
                p = dict(paper(), abstract=source)
                candidate = response(p, dataset=[dict(concept=concept, evidence_id='A0')])
                _, meta = self.annotate(p, [candidate] * 3)
                self.assertFalse(meta['validation_passed'])
                self.assertTrue(any('named resource' in e for e in meta['validation_errors']))
        p = dict(paper(), abstract='We evaluate the model on MNIST.')
        candidate = response(p, dataset=[dict(concept='MNIST', evidence_id='A0')])
        _, meta = self.annotate(p, [candidate] * 3)
        self.assertTrue(meta['validation_passed'])

    def test_named_benchmark_remains_valid_when_the_sentence_mentions_languages(self):
        p = dict(paper(), abstract='We evaluate WMT15 across four languages.')
        candidate = response(p, dataset=[dict(concept='WMT15', evidence_id='A0')])
        _, meta = self.annotate(p, [candidate] * 3)
        self.assertTrue(meta['validation_passed'])

    def test_explicit_resource_naming_disambiguates_a_language_like_name(self):
        p = dict(paper(), abstract='We evaluate a dataset named English.')
        candidate = response(p, dataset=[dict(concept='English', evidence_id='A0')])
        _, meta = self.annotate(p, [candidate] * 3)
        self.assertTrue(meta['validation_passed'])

    def test_background_negation_does_not_reject_the_contrasting_finding(self):
        p = dict(paper(), abstract='Although self-training without reranking has been found not to improve in-domain accuracy for parsers trained on the WSJ Penn Treebank, we show that it is surprisingly effective for parser domain adaptation.')
        candidate = response(p, contribution=[dict(concept='self-training without reranking is surprisingly effective for parser domain adaptation', evidence_id='A0')])
        value, meta = self.annotate(p, [candidate] * 3)
        self.assertTrue(meta['validation_passed'])
        base.validate_annotation(value, p, meta)

    def test_claim_negation_cannot_be_dropped(self):
        p = dict(paper(), abstract='Our model does not improve accuracy.')
        candidate = response(p, contribution=[dict(concept='model improves accuracy', evidence_id='A0')])
        _, meta = self.annotate(p, [candidate] * 3)
        self.assertFalse(meta['validation_passed'])
        self.assertTrue(any('negation' in e for e in meta['validation_errors']))

    def test_finding_must_retain_its_leading_condition(self):
        p = dict(paper(), abstract='In the case of Tamil, when significantly more test data than training data is available, we integrated semi-supervised training and speaker adaptation, and achieved significant improvements in STT and KWS.')
        short = response(p, contribution=[dict(concept='achieved significant improvements in STT and KWS', evidence_id='A0')])
        _, meta = self.annotate(p, [short] * 3)
        self.assertFalse(meta['validation_passed'])
        self.assertTrue(any('condition' in e for e in meta['validation_errors']))
        full = response(p, contribution=[dict(concept='In the case of Tamil when significantly more test data than training data is available achieved significant improvements in STT and KWS', evidence_id='A0')])
        _, meta = self.annotate(p, [full] * 3)
        self.assertTrue(meta['validation_passed'])

    def test_under_and_when_conditions_do_not_depend_on_the_next_subject(self):
        for source, short, full in [
                ('Under limited training data, our model improves accuracy.', 'model improves accuracy', 'Under limited training data model improves accuracy'),
                ('When training data is limited, performance improves.', 'performance improves', 'When training data is limited performance improves')]:
            with self.subTest(source=source):
                p = dict(paper(), abstract=source)
                candidate = response(p, contribution=[dict(concept=short, evidence_id='A0')])
                _, meta = self.annotate(p, [candidate] * 3)
                self.assertFalse(meta['validation_passed'])
                candidate['contribution'][0]['concept'] = full
                _, meta = self.annotate(p, [candidate] * 3)
                self.assertTrue(meta['validation_passed'])

    def test_method_negation_and_negative_class_names_are_not_missing_findings(self):
        for source, facet, concept in [
                ('We do not use labels during training.', 'method', 'do not use labels during training'),
                ('We discuss the benchmark contest, which consisted in dense labeling of aerial images into building / not building classes, covering five cities not present in the training set.', 'task', 'dense labeling of aerial images into building / not building classes')]:
            with self.subTest(source=source):
                p = dict(paper(), abstract=source)
                candidate = response(p, **{facet: [dict(concept=concept, evidence_id='A0')]})
                _, meta = self.annotate(p, [candidate] * 3)
                self.assertTrue(meta['validation_passed'])

    def test_an_explicit_negative_experimental_finding_cannot_be_omitted(self):
        p = dict(paper(), abstract='We use morphs. However, in our experiments we did not obtain higher BLEU scores than the word-based approach. Our morphs reduce untranslated words.')
        short = response(p, method=[dict(concept='morphs', evidence_id='A0')],
                         contribution=[dict(concept='morphs reduce untranslated words', evidence_id='A2')])
        _, meta = self.annotate(p, [short] * 3)
        self.assertFalse(meta['validation_passed'])
        self.assertTrue(any('negative finding' in e and 'A1' in e for e in meta['validation_errors']))
        full = copy.deepcopy(short)
        full['contribution'].append(dict(concept='did not obtain higher BLEU scores than the word-based approach', evidence_id='A1'))
        value, meta = self.annotate(p, [full] * 3)
        self.assertTrue(meta['validation_passed'])
        base.validate_annotation(value, p, meta)

    def test_problem_cannot_turn_whether_into_an_assertion(self):
        p = dict(paper(), abstract='We investigate whether the encoder learns source syntax.')
        short = response(p, problem=[dict(concept='encoder learns source syntax', evidence_id='A0')])
        _, meta = self.annotate(p, [short] * 3)
        self.assertFalse(meta['validation_passed'])
        full = response(p, problem=[dict(concept='whether the encoder learns source syntax', evidence_id='A0')])
        _, meta = self.annotate(p, [full] * 3)
        self.assertTrue(meta['validation_passed'])

    def test_source_truncation_is_flagged_without_editing_the_abstract(self):
        p = dict(paper(), abstract='We use ranking. The hearer will come to')
        candidate = response(p, method=[dict(concept='ranking', evidence_id='A0')])
        _, meta = self.annotate(p, [candidate] * 3)
        self.assertTrue(any('truncat' in x.lower() for x in meta['source_quality']['issues']))
        self.assertEqual(p['abstract'], 'We use ranking. The hearer will come to')

    def test_saved_policy_cannot_be_downgraded_to_bypass_v32_checks(self):
        p = dict(paper(), abstract='Limited annotations hinder retrieval. We use ranking for document retrieval. We introduce Ranker. We evaluate on MNIST.')
        candidate = response(p, problem=[dict(concept='Limited annotations hinder retrieval', evidence_id='A0')],
                             task=[dict(concept='document retrieval', evidence_id='A1')],
                             method=[dict(concept='ranking', evidence_id='A1')],
                             dataset=[dict(concept='MNIST', evidence_id='A3')],
                             contribution=[dict(concept='Ranker', evidence_id='A2')])
        value, meta = self.annotate(p, [candidate] * 3)
        meta['prompt_version'] = '3.2'
        meta['request_parameters']['extraction_policy_version'] = '3.1'
        with self.assertRaisesRegex(ValueError, 'policy'):
            base.validate_annotation(value, p, meta)


class V33PolicyChecks(unittest.TestCase):
    def extract(self, version):
        p = dict(paper(), abstract='Limited labels hinder image retrieval. We use random projection and nearest-neighbor search for image retrieval. We introduce ORBIT. Our model does not improve accuracy on noisy inputs. We evaluate on a Dutch test collection and MNIST.')
        candidate = response(p,
            problem=[dict(concept='Limited labels hinder image retrieval', evidence_id='A0')],
            task=[dict(concept='image retrieval', evidence_id='A1')],
            method=[dict(concept='random projection', evidence_id='A1'),
                    dict(concept='nearest-neighbor search', evidence_id='A1')],
            contribution=[dict(concept='ORBIT', evidence_id='A2'),
                          dict(concept='model does not improve accuracy on noisy inputs', evidence_id='A3')],
            dataset=[dict(concept='Dutch test collection', evidence_id='A4'),
                     dict(concept='MNIST', evidence_id='A4')])
        config = dict(seed=42, max_attempts=3, max_new_tokens=2048,
                      prompt_version=version, dataset_resource_filter=True)
        with tempfile.TemporaryDirectory() as directory:
            try:
                value, meta = v3.annotate(p, '', config, {},
                    lambda messages, seed: (json.dumps(candidate), dict(usage={})),
                    Path(directory) / 'last_failure.json')
            except ValueError as error:
                self.fail(f'Prompt {version} must run with its declared policy: {error}')
        meta['prompt_version'] = version
        return p, value, meta

    def test_new_prompt_keeps_baseline_scores_selection_and_dataset_filter(self):
        p, new, meta = self.extract('3.3')
        _, old, baseline = self.extract('3.1')
        self.assertEqual(new, old)
        self.assertEqual(meta['attempt_scores'], baseline['attempt_scores'])
        self.assertEqual(meta['attempt'], baseline['attempt'])
        self.assertEqual(meta['source_quality'], baseline['source_quality'])
        self.assertEqual(meta['request_parameters']['extraction_policy_version'], '3.1')
        self.assertEqual(base.validate_annotation(new, p, meta)['dataset'], ['MNIST'])

    def test_new_prompt_replay_rejects_a_different_validator_policy(self):
        p, value, meta = self.extract('3.3')
        meta['request_parameters']['extraction_policy_version'] = '3.2'
        with self.assertRaisesRegex(ValueError, 'policy'):
            base.validate_annotation(value, p, meta)

    def test_unknown_prompt_version_rejects_before_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'prompt'):
                v3.annotate(paper(), '', dict(prompt_version='unknown', max_attempts=3, max_new_tokens=2048, seed=42), {},
                            lambda messages, seed: self.fail('Unexpected model call'),
                            Path(directory) / 'last_failure.json')


if __name__ == '__main__':
    unittest.main()
