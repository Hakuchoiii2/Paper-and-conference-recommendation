"""Protect experiment separation and the real extract/review contract."""
import importlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'data/exp_a/.kaggle/matrix'))


class PolicyMatrixChecks(unittest.TestCase):
    def module(self):
        path = ROOT / 'data/exp_a/.kaggle/matrix/policy_matrix.py'
        self.assertTrue(path.is_file(), 'Policy experiment runner is missing')
        return importlib.import_module('policy_matrix')

    def test_bundle_excludes_policy_papers_and_keeps_reference_out_of_generation(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as directory:
            result = m.build(Path(directory))
            with zipfile.ZipFile(Path(directory) / 'input-dataset/matrix_bundle.zip.bin') as archive:
                settings = json.loads(archive.read('policy_settings.json'))
                papers = [json.loads(x) for x in archive.read('model_inputs/papers.jsonl').splitlines()]
                refs = [json.loads(x) for x in archive.read('evaluation_only/review_annotations.jsonl').splitlines()]
                examples = json.loads(archive.read('data/exp_a/prompts/policy_examples_v1.json'))
                self.assertEqual(len(papers), 30)
                self.assertEqual(len(settings['audit_paper_ids']), 20)
                ids = {p['paper_id'] for p in papers}
                self.assertEqual(ids, {p['paper_id'] for p in refs})
                self.assertFalse(ids & set(settings['audit_paper_ids']))
                self.assertFalse(ids & {x['paper_id'] for x in examples})
                self.assertTrue(all(set(p) <= {'paper_id','title','abstract','source_flags'} for p in papers))
                self.assertFalse(any('review_annotations' in n for n in archive.namelist() if n.startswith('model_inputs/')))
                self.assertEqual(set(result['arms']), {'original','policy','policy_examples'})
                self.assertEqual(settings['generation']['max_attempts'], 3)
                self.assertEqual(settings['generation']['max_new_tokens'], 2048)
                for example in examples:
                    m.v3.validate_response(m.v3.ground_response(example['output'], example['source']), example['source'], policy='3.1')
                for name, expected in settings['files'].items():
                    import hashlib
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), expected)
                project = Path(directory)/'isolated_project'
                archive.extractall(project)
            probe = subprocess.run([sys.executable,'-X','utf8','-I','-B','-c',
                'import sys; sys.path.insert(0,sys.argv[1]); import policy_matrix; print("bundle import passed")',
                str(project/'data/exp_a/.kaggle/matrix')],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(probe.returncode,0,probe.stderr)

    def test_annotation_reviews_source_and_keeps_evidence_without_reference_labels(self):
        m = self.module()
        paper = dict(paper_id='P000002',title='Ranking',abstract='We introduce RankNet for ranking.')
        value = dict(paper_id='P000002', **{f: [] for f in m.FACETS})
        value.update(method=[dict(concept='RankNet',evidence_id='A0')],
                     contribution=[dict(concept='RankNet',evidence_id='A0')])
        requests = []
        def generate(messages, seed):
            requests.append(messages)
            return json.dumps(value), dict(usage=dict(input_tokens=10,output_tokens=5),generation_seconds=1)
        with tempfile.TemporaryDirectory() as directory:
            result = m.annotate_paper(paper,'Extract from this source.',dict(seed=42,max_attempts=3,
                max_new_tokens=2048,prompt_version='3.7',dataset_resource_filter=True),{},generate,Path(directory))
        self.assertEqual(len(requests), 2)
        self.assertEqual(result['facets']['method'], ['RankNet'])
        self.assertEqual(result['facets']['contribution'], ['RankNet'])
        self.assertFalse(result['fallback_used'])
        self.assertEqual(result['usage']['output_tokens'], 10)
        self.assertEqual(result['audit']['evidence_selection']['method'][0]['evidence_id'], 'A0')

    def test_split_rejects_an_example_from_the_scored_papers(self):
        m = self.module()
        with self.assertRaisesRegex(ValueError, 'overlap'):
            m.validate_split(['P000001','P000002'],['P000001'],['P000002'])


if __name__ == '__main__':
    unittest.main()
