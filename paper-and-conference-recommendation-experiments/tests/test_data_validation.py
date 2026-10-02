"""Run: python tests/test_data_validation.py; standard library only."""
import json
import sys
import unittest
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
try:
    import build_corpus as corpus
except ImportError:
    corpus = None
try:
    import validate_all as validator
except ImportError:
    validator = None

class DataChecks(unittest.TestCase):
    def test_pipeline_exists(self):
        self.assertIsNotNone(corpus, 'Corpus builder has not been implemented')
        self.assertIsNotNone(validator, 'Validator has not been implemented')

    def test_scope_requires_computing_evidence(self):
        if corpus is None: self.skipTest('Waiting for implementation')
        policy = json.loads((Path(__file__).resolve().parents[1] / 'configs/scope.json').read_text())
        for title, abstract, expected in [
            ('A database management system', 'Efficient query processing.', True),
            ('Machine learning for diagnosis', 'A new machine learning classifier.', True),
            ('Cancer survival', 'A statistical model of cellular networks and imaging.', False),
            ('Neural networks in the brain', 'Biological neural networks control behavior.', False),
            ('Clinical prognosis', 'Machine learning is useful. We report patient survival.', False),
            ('Learning', 'We develop a deep learning method for image segmentation.', True),
            ('Software', 'We present a software package for data analysis.', True),
        ]:
            with self.subTest(title=title):
                self.assertEqual(corpus.classify('scifact', title, abstract, policy)[0], expected)
        self.assertTrue(corpus.classify('csfcube', 'A paper', 'Text', policy)[0])

    def test_merge_keeps_provenance_and_stable_ids(self):
        if corpus is None: self.skipTest('Waiting for implementation')
        rows = [
            dict(source='csfcube', source_id='a', title='Graph Learning!', abstract='Graph method.', year=2020, identifiers={'doi': '10/x'}, scope_evidence=['source scope']),
            dict(source='scifact', source_id='b', title='Graph learning', abstract='Graph method.', year=None, identifiers={}, scope_evidence=['graph neural network']),
            dict(source='csfcube', source_id='c', title='Other title', abstract='Graph method.', year=None, identifiers={'doi': '10/x'}, scope_evidence=['source scope']),
        ]
        papers, mapping, report = corpus.merge(rows, [])
        self.assertEqual(len(papers), 1)
        self.assertEqual({r['paper_id'] for r in mapping}, {'P000001'})
        self.assertEqual(len(mapping), 3)
        extra = dict(rows[0], source_id='d', title='A separate study', identifiers={})
        rebuilt, remap, _ = corpus.merge([extra] + rows, mapping)
        self.assertEqual({r['paper_id'] for r in remap if r['source_id'] in {'a','b','c'}}, {'P000001'})
        self.assertEqual(next(r['paper_id'] for r in remap if r['source_id']=='d'), 'P000002')
        self.assertEqual(len(rebuilt), 2)

    def test_conflicting_abstract_is_not_silently_merged(self):
        if corpus is None: self.skipTest('Waiting for implementation')
        rows = [dict(source='csfcube', source_id=str(n), title='Same title', abstract=a, year=None, identifiers={}, scope_evidence=['source scope']) for n,a in enumerate(['One distinct abstract.', 'Another distinct abstract.'])]
        papers, _, report = corpus.merge(rows, [])
        self.assertEqual(len(papers), 2)
        self.assertEqual(len(report['title_conflicts']), 1)

    def test_validator_catches_corruption(self):
        if validator is None: self.skipTest('Waiting for implementation')
        paper = dict(paper_id='P000001', source='csfcube', source_id='a', title='Title', abstract='Text', year=None, domain='information_technology', scope_evidence=['source scope'])
        validator.validate_papers([paper])
        for altered in [dict(paper, paper_id='P001'), dict(paper, abstract=''), dict(paper, year=True)]:
            with self.assertRaises(ValueError): validator.validate_papers([altered])
        with self.assertRaises(ValueError): validator.validate_refs([dict(paper_id='P999999')], {'P000001'}, 'sample')
        validator.validate_facets([dict(paper_id='P000001', problem=[], task=[], method=[], dataset=[], contribution=[])], {'P000001'})
        with self.assertRaises(ValueError): validator.validate_facets([dict(paper_id='P000001', background=[])], {'P000001'})
        with self.assertRaises(ValueError): validator.validate_time('2026-01-01T00:00:00')
        with self.assertRaises(ValueError): validator.validate_temporal([dict(user_id='U0001', timestamp='2026-01-03T00:00:00Z')], [dict(user_id='U0001', timestamp='2026-01-02T00:00:00Z')])

    def test_invalid_source_year_is_missing_not_a_fake_year(self):
        self.assertIsNone(corpus.adapt('csfcube', dict(paper_id='1', title='Paper', abstract=['Text'], metadata={'year':'801'}))['year'])

    def test_fixture_builder_writes_manifest_and_never_gold(self):
        import build_fixture
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'configs').mkdir()
            (root / 'configs/data.json').write_text(json.dumps(dict(seed=42, fixture_size=1, corpus='data/processed/papers.jsonl', contract_version='1.0')))
            corpus.write_jsonl(root / 'data/processed/papers.jsonl', [dict(paper_id='P000001', title='Actual title')])
            build_fixture.build(root)
            manifest = json.loads((root / 'data/fixtures/manifest.json').read_text())
            self.assertEqual(manifest['record_counts'], {'papers':1})
            self.assertEqual(manifest['dataset_kind'],'real')
            self.assertFalse((root / 'data/fixtures/facets.jsonl').exists())
            first = (root / 'data/fixtures/papers.jsonl').read_bytes()
            build_fixture.build(root)
            self.assertEqual(first, (root / 'data/fixtures/papers.jsonl').read_bytes())

    def test_downloader_rejects_path_traversal(self):
        from download_sources import safe_relative
        for unsafe in ['root/../../outside.json', '/absolute/file', 'root/C:/file', 'root/..\\escape']:
            with self.assertRaises(ValueError): safe_relative(unsafe)

    def test_primary_source_stays_stable_when_alias_is_added(self):
        original=dict(source='scifact',source_id='b',title='Original title',abstract='Original abstract.',year=None,identifiers={'doi':'10/shared'},scope_evidence=['software'])
        alias=dict(source='csfcube',source_id='a',title='Alias title',abstract='An alternate abstract.',year=2020,identifiers={'doi':'10/shared'},scope_evidence=['source scope'])
        first,mapping,_=corpus.merge([original],[])
        second,mapping,_=corpus.merge([alias,original],mapping)
        third,_,_=corpus.merge([alias,original],mapping)
        self.assertEqual(first,second)
        self.assertEqual(second,third)

    def test_override_requires_attributed_text_evidence(self):
        valid=dict(include=True,reviewer='Khai',reason='Introduces computing software.')
        self.assertEqual(corpus.check_override(valid,'scifact:1'),valid)
        for bad in [dict(include=True,reason='Reason'), dict(valid,reason=['Reason']), dict(valid,reviewer=' '), dict(valid,include=1)]:
            with self.assertRaises(ValueError): corpus.check_override(bad,'scifact:1')

if __name__ == '__main__': unittest.main()
