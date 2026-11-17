"""Checks for the Qwen pilot; fake only the expensive model response."""
import copy
import importlib.util
import json
import random
import sys
import tempfile
import unittest
import shutil
import zipfile
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'data/exp_a'))
import build_exp_a as base


def selection(paper, **facets):
    return dict(paper_id=paper['paper_id'], **{f: facets.get(f, []) for f in base.FACET_NAMES})


class PipelineChecks(unittest.TestCase):
    def protocol(self):
        path = ROOT / 'data/exp_a/extraction_v3.py'
        self.assertTrue(path.is_file(), 'The new extraction protocol is missing')
        spec = importlib.util.spec_from_file_location('extraction_v3', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_short_grounded_phrase_does_not_need_seventy_percent_retention(self):
        v3 = self.protocol()
        paper = dict(paper_id='P000001', title='Retrieval',
                     abstract='We propose a robust and computationally efficient ranking algorithm.')
        value = selection(paper, method=[dict(concept='robust ranking algorithm', evidence_id='A0')])
        result = v3.ground_response(value, paper)
        self.assertEqual(result['method'][0]['concept'], 'robust ranking algorithm')
        self.assertEqual(result['method'][0]['evidence'], paper['abstract'])
        with self.assertRaises(ValueError):
            base.ground_response(value, paper)

    def test_shortening_cannot_drop_negation_or_internal_quantities(self):
        v3 = self.protocol()
        for sentence, concept in [
                ('The model does not improve accuracy.', 'does improve accuracy'),
                ('The model does not improve accuracy.', 'improve accuracy'),
                ('The model improves accuracy from 70 to 80 percent.', 'improves accuracy to 80 percent'),
                ('We use ranking.', 'invented ranking')]:
            paper = dict(paper_id='P000001', title='Evaluation', abstract=sentence)
            with self.subTest(concept=concept), self.assertRaises(ValueError):
                v3.ground_response(selection(paper, contribution=[dict(concept=concept, evidence_id='A0')]), paper)

    def test_exact_decimal_finding_is_preserved_and_changed_decimal_is_rejected(self):
        v3 = self.protocol()
        paper = dict(paper_id='P000001', title='Classification', abstract='Our model achieves 95.5% accuracy.')
        value = selection(paper, contribution=[dict(concept='achieves 95.5% accuracy', evidence_id='A0')])
        self.assertEqual(v3.ground_response(value, paper)['contribution'][0]['concept'], 'achieves 95.5% accuracy')
        for changed in ['achieves 95,5% accuracy', 'achieves 95', '5% accuracy', 'achieves 95.4% accuracy']:
            value['contribution'][0]['concept'] = changed
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                v3.ground_response(value, paper)

    def test_unnamed_dataset_is_rejected_without_requiring_other_facets(self):
        v3 = self.protocol()
        paper = dict(paper_id='P000001', title='Study', abstract='We use a dataset of 1000 tweets.')
        with self.assertRaisesRegex(ValueError, 'named resource'):
            v3.ground_response(selection(paper, dataset=[dict(concept='dataset of 1000 tweets', evidence_id='A0')]), paper)
        self.assertEqual(v3.ground_response(selection(paper), paper), selection(paper))

    def test_review_can_recover_contribution_and_save_both_evidence_audits(self):
        v3 = self.protocol()
        paper = dict(paper_id='P000001', title='Image classification',
                     abstract='We propose Adaptive Sampling for image classification.')
        draft = selection(paper, task=[dict(concept='image classification', evidence_id='T0')],
                          method=[dict(concept='Adaptive Sampling', evidence_id='A0')])
        reviewed = dict(draft, contribution=[dict(concept='Adaptive Sampling', evidence_id='A0')])
        responses = iter([draft, reviewed])
        requests = []
        def generate(messages, seed):
            requests.append(copy.deepcopy(messages))
            return json.dumps(next(responses)), dict(usage=dict(input_tokens=10, output_tokens=5))
        with tempfile.TemporaryDirectory() as directory:
            value, meta = v3.annotate(paper, 'Extract supported concepts.',
                                      dict(seed=42, max_attempts=3, max_new_tokens=2048), {}, generate,
                                      Path(directory) / 'failure.json')
        self.assertEqual(value['contribution'][0]['concept'], 'Adaptive Sampling')
        self.assertEqual(value['task'][0]['evidence'], paper['title'])
        self.assertEqual([r['stage'] for r in meta['attempt_scores']], ['extract', 'review'])
        self.assertTrue(meta['self_review_completed'])
        self.assertEqual(meta['usage'], dict(input_tokens=20, output_tokens=10))
        self.assertEqual(len(requests), 2)
        self.assertIn(paper['abstract'], requests[1][1]['content'])
        self.assertEqual(base.validate_annotation(value, paper, meta)['contribution'], ['Adaptive Sampling'])

    def test_invalid_review_is_not_published_as_a_valid_annotation(self):
        v3 = self.protocol()
        paper = dict(paper_id='P000001', title='Retrieval', abstract='We use ranking.')
        draft = selection(paper, method=[dict(concept='ranking', evidence_id='A0')])
        invalid = selection(paper, method=[dict(concept='fabricated technique', evidence_id='A0')])
        responses = iter([draft, invalid, invalid])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'failure.json'
            value, metadata = v3.annotate(paper, 'Extract.', dict(seed=42, max_attempts=3, max_new_tokens=1024), {},
                                          lambda messages, seed: (json.dumps(next(responses)), dict(usage={})), path)
            self.assertTrue(metadata['fallback_used'])
            self.assertFalse(metadata['validation_passed'])
            self.assertEqual(value['method'][0]['concept'], 'ranking')
            saved = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(len(saved['attempt_scores']), 3)
            self.assertEqual(saved['paper_id'], 'P000001')

    def test_pilot_sample_is_reproducible_and_excludes_development_ids(self):
        path = ROOT / 'data/exp_a/.kaggle/pilot/build.py'
        self.assertTrue(path.is_file(), 'Kaggle packager is missing')
        spec = importlib.util.spec_from_file_location('pilot_build', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        papers = [dict(paper_id=f'P{i:06d}') for i in range(1, 101)]
        excluded = {'P000001', 'P000002'}
        selected = module.select_pilot(papers, excluded, 50, 20261014)
        expected = sorted(random.Random(20261014).sample([r['paper_id'] for r in papers[2:]], 50))
        self.assertEqual(selected, expected)
        self.assertFalse(set(selected) & excluded)
        with self.assertRaises(ValueError):
            module.select_pilot(papers, excluded, 99, 42)

    def test_failed_v3_paper_stays_missing_and_resume_preserves_completed_paper(self):
        v3 = self.protocol()
        config = json.loads((ROOT / 'data/exp_a/config_v3_pilot50.json').read_text(encoding='utf-8'))
        config['paper_ids'] = config['paper_ids'][:2]
        first, second = config['paper_ids']
        def valid(paper, instruction):
            answer = selection(paper)
            return v3.annotate(paper, instruction, config, {},
                               lambda messages, seed: (json.dumps(answer), dict(usage={})),
                               root / 'failure.json')
        def partly_failing(paper, instruction):
            if paper['paper_id'] == second:
                raise base.AnnotationError('invalid review')
            return valid(paper, instruction)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['corpus', 'prompt', 'guideline']:
                dest = root / config[name]
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / config[name], dest)
            with patch.object(base, 'load_qwen', return_value=partly_failing):
                manifest = base.generate(root, config)
            self.assertEqual(manifest['count'], 1)
            self.assertEqual(manifest['missing_ids'], [second])
            self.assertIn(second, manifest['failed_annotations'])
            saved = base.read_jsonl(root / config['output_dir'] / 'annotation_metadata.jsonl')[0]
            def resume_only_missing(paper, instruction):
                self.assertEqual(paper['paper_id'], second)
                return valid(paper, instruction)
            with patch.object(base, 'load_qwen', return_value=resume_only_missing):
                complete = base.generate(root, config)
            self.assertEqual(complete['count'], 2)
            self.assertEqual(complete['status'], 'complete')
            self.assertEqual(base.read_jsonl(root / config['output_dir'] / 'annotation_metadata.jsonl')[0], saved)
            base.check_outputs(root, config)
            for name in ['facets_silver.jsonl', 'annotation_metadata.jsonl', 'manifest.json']:
                (root / config['output_dir'] / name).unlink()
            spec = importlib.util.spec_from_file_location('pilot_build', ROOT / 'data/exp_a/.kaggle/pilot/build.py')
            packager = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(packager)
            self.assertTrue(callable(getattr(packager, 'resume_files', None)), 'Checkpoint-only resume is missing')
            with patch.object(base, 'load_qwen', side_effect=AssertionError('Recovery must not run inference')):
                self.assertEqual(len(packager.resume_files(root, config)), 3)
            self.assertEqual(base.check_outputs(root, config)['count'], 2)
            self.assertEqual(base.read_jsonl(root / config['output_dir'] / 'annotation_metadata.jsonl')[0], saved)

    def test_kaggle_archive_has_exact_pilot_ids_without_reference_or_credentials(self):
        path = ROOT / 'data/exp_a/.kaggle/pilot/build.py'
        spec = importlib.util.spec_from_file_location('pilot_build', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        manifest = module.build()
        with zipfile.ZipFile(ROOT / 'data/exp_a/.kaggle/pilot/build/input-dataset/input_bundle.zip.bin') as archive:
            names = archive.namelist()
            self.assertFalse(any('ground_truth' in n or 'credentials' in n or 'baseline_silver' in n for n in names))
            config = json.loads(archive.read('data/exp_a/config_v3_pilot50.json'))
            self.assertEqual(config['paper_ids'], manifest['sample']['paper_ids'])
            self.assertEqual(len(config['paper_ids']), 50)
            self.assertFalse(config['do_sample'])
            self.assertEqual(config['extraction_protocol'], 'two_pass_v3')


if __name__ == '__main__':
    unittest.main()
