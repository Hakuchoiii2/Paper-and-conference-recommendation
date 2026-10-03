"""Local extraction contract checks, with no model download in unit tests."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'data/exp_a'))
import build_exp_a as a

class ExtractionCheck(unittest.TestCase):
    def test_paper_range_selects_inclusive_sorted_ids_and_resumes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            papers=[dict(paper_id=f'P00000{i}',source='csfcube',source_id=str(i),
                         title='Retrieval',abstract='Ranking.',year=None,
                         domain='information_technology',scope_evidence=['CS']) for i in (4,2,1,3)]
            a.write_jsonl(root/'papers.jsonl',papers)
            for name in ('prompt.md','guide.md'):
                (root/name).write_text('Extract.',encoding='utf-8')
            config=dict(corpus='papers.jsonl',output_dir='out',paper_range=[2,3],
                        model='Qwen/Qwen3-1.7B',revision='test-only',device='cuda',
                        cache_dir='models',prompt='prompt.md',guideline='guide.md',
                        prompt_version='1.2',guideline_version='1.0',max_new_tokens=1024,
                        max_attempts=3,temperature=0.7,top_p=0.8,top_k=20,seed=42)
            def answer(paper,instruction):
                value=dict(paper_id=paper['paper_id'],**{f:[] for f in a.FACET_NAMES})
                return value,dict(model=config['model'],usage={})
            with patch.object(a,'load_qwen',return_value=answer):
                a.generate(root,config,limit=1)
                self.assertEqual([p['paper_id'] for p in a.read_jsonl(root/'out/facets_silver.jsonl')],
                                 ['P000002'])
                manifest=a.generate(root,config)
                self.assertEqual([p['paper_id'] for p in a.read_jsonl(root/'out/facets_silver.jsonl')],
                                 ['P000002','P000003'])
                self.assertEqual(a.generate(root,config)['count'],2)
                self.assertEqual(manifest['corpus_count'],4)
                self.assertEqual(manifest['status'],'partial')
                self.assertEqual(manifest['missing_ids'],['P000001','P000004'])
                a.check_outputs(root,config,allow_partial=True)
                with self.assertRaisesRegex(ValueError,'not ready for B'):
                    a.check_outputs(root,config)
                with self.assertRaisesRegex(ValueError,'provenance'):
                    a.generate(root,dict(config,paper_range=[1,4]))
                for bounds,expected in (([4,None],['P000004']),([3,3],['P000003']),
                                        ([1,None],['P000001','P000002','P000003','P000004'])):
                    selected=dict(config,paper_range=bounds,output_dir=f'part_{bounds[0]}')
                    a.generate(root,selected)
                    self.assertEqual([p['paper_id'] for p in a.read_jsonl(root/selected['output_dir']/'facets_silver.jsonl')],
                                     expected)
            for bounds in ([0,2],[3,2],[1,5],[5,None],[True,2],[1,2.5],[1,False],
                           [1],[1,2,3],'1-2',None):
                with self.subTest(paper_range=bounds), self.assertRaisesRegex(ValueError,'paper_range'):
                    a.generate(root,dict(config,paper_range=bounds,output_dir='invalid'))
            self.assertFalse((root/'invalid').exists())

    def test_sentence_ids_resolve_to_exact_source_without_fabrication(self):
        paper=dict(paper_id='P000001',title='Retrieval',abstract='We use "ranking". No named dataset.')
        value=dict(paper_id=paper['paper_id'],**{f:[] for f in a.FACET_NAMES})
        value['method']=[dict(concept='ranking',evidence_id='A0')]
        resolved=a.ground_response(value,paper)
        self.assertEqual(resolved['method'][0],dict(concept='ranking',evidence='We use "ranking".',source='abstract'))
        a.validate_response(resolved,paper)
        bad=dict(resolved,method=[dict(concept='algorithm/technique used',evidence=paper['abstract'],source='abstract')])
        with self.assertRaisesRegex(ValueError,'source phrase'):
            a.validate_response(bad,paper)
        value['method'][0]['evidence_id']='A999'
        with self.assertRaisesRegex(ValueError,'evidence_id'):
            a.ground_response(value,paper)

    def test_windows_launcher_preserves_script_path_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix='qwen path ') as directory:
            root=Path(directory)
            executable=root/'.venv-qwen/Scripts/python.exe'
            executable.parent.mkdir(parents=True)
            executable.touch()
            with patch.object(a,'ROOT',root), patch('subprocess.call',return_value=0) as launch:
                with self.assertRaises(SystemExit) as exit_status:
                    a.main()
                self.assertEqual(exit_status.exception.code,0)
                self.assertEqual(launch.call_args.args[0][0],str(executable))
                self.assertEqual(launch.call_args.args[0][3],str(Path(a.__file__).resolve()))

    def test_local_pipeline_resume_failure_and_grounding(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            papers=[dict(paper_id=f'P00000{i}',source='csfcube',source_id=str(i),
                         title='Retrieval',abstract='We use ranking for retrieval.',year=None,
                         domain='information_technology',scope_evidence=['CS']) for i in (1,2)]
            a.write_jsonl(root/'papers.jsonl',papers)
            for name in ('prompt.md','guide.md'):
                (root/name).write_text('Extract supported concepts.',encoding='utf-8')
            config=dict(corpus='papers.jsonl',output_dir='out',model='Qwen/Qwen3-1.7B',
                        revision='test-only',device='cuda',cache_dir='models',prompt='prompt.md',
                        guideline='guide.md',prompt_version='1.2',guideline_version='1.0',
                        max_new_tokens=1024,max_attempts=3,temperature=0.7,top_p=0.8,top_k=20,seed=42)
            with self.assertRaisesRegex(ValueError,'4-bit mode requires CUDA'):
                a.inputs(root,dict(config,device='cpu',load_in_4bit=True))
            def answer(paper,instruction):
                value=dict(paper_id=paper['paper_id'],**{f:[] for f in a.FACET_NAMES})
                value['method']=[dict(concept='ranking',evidence='use ranking',source='abstract')]
                return value,dict(model=config['model'],usage={},model_revision=config['revision'])
            with patch.object(a,'load_qwen',return_value=answer) as loader:
                self.assertEqual(a.generate(root,config,limit=1)['status'],'partial')
                config['max_new_tokens']=2048
                self.assertEqual(a.generate(root,config)['status'],'complete')
                self.assertEqual(loader.call_count,2)
                self.assertEqual(a.generate(root,config)['count'],2)
                self.assertEqual(loader.call_count,2)
            self.assertEqual(a.check_outputs(root,config)['count'],2)
            self.assertFalse((root/'out/facets_gold.jsonl').exists())
            with a.single_run(root/'out'):
                with self.assertRaisesRegex(RuntimeError,'already running'):
                    a.generate(root,config)
            bad,_=answer(papers[0],'')
            bad['method'][0]['evidence']='invented quotation'
            with self.assertRaisesRegex(ValueError,'evidence'):
                a.validate_response(bad,papers[0])
            bad['paper_id']='P999999'
            with self.assertRaisesRegex(ValueError,'paper_id'):
                a.validate_response(bad,papers[0])
            (root/'prompt.md').write_text('Changed.',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'provenance'):
                a.generate(root,config)

    def test_failure_keeps_partial_and_json_parser_rejects_prose(self):
        self.assertEqual(a.parse_generation('```json\n{"paper_id":"P000001"}\n```'),{'paper_id':'P000001'})
        with self.assertRaises(ValueError):
            a.parse_generation('Here is the answer: {"paper_id":"P000001"}')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            config=dict(corpus='papers.jsonl',output_dir='out',model='Qwen/Qwen3-1.7B',
                        revision='test-only',device='cuda',cache_dir='models',prompt='prompt.md',
                        guideline='guide.md',prompt_version='1.2',guideline_version='1.0',
                        max_new_tokens=1024,max_attempts=3,temperature=0.7,top_p=0.8,top_k=20,seed=42)
            papers=[dict(paper_id=f'P00000{i}',source='csfcube',source_id=str(i),title='Retrieval',
                         abstract='Ranking.',year=None,domain='information_technology',scope_evidence=['CS']) for i in (1,2)]
            a.write_jsonl(root/'papers.jsonl',papers)
            for name in ('prompt.md','guide.md'):
                (root/name).write_text('Extract.',encoding='utf-8')
            value=dict(paper_id='P000001',**{f:[] for f in a.FACET_NAMES})
            from unittest.mock import Mock
            extractor=Mock(side_effect=[(value,{'usage':{},'model':config['model']}),RuntimeError('local generation failed')])
            with patch.object(a,'load_qwen',return_value=extractor):
                with self.assertRaisesRegex(RuntimeError,'local generation failed'):
                    a.generate(root,config)
            manifest=a.check_outputs(root,config,allow_partial=True)
            self.assertEqual(manifest['count'],1)
            self.assertEqual(manifest['missing_ids'],['P000002'])

            # A paper-specific model rejection does not prevent later real papers from running.
            config['output_dir']='batch'
            second=dict(value,paper_id='P000002')
            extractor=Mock(side_effect=[a.AnnotationError('bad JSON'),(second,{'usage':{},'model':config['model']})])
            with patch.object(a,'load_qwen',return_value=extractor):
                manifest=a.generate(root,config)
            self.assertEqual(manifest['count'],1)
            self.assertEqual(manifest['missing_ids'],['P000001'])
            self.assertEqual(manifest['failed_annotations'],{'P000001':'bad JSON'})
            a.check_outputs(root,config,allow_partial=True)
            with patch.object(a,'load_qwen',return_value=lambda p,i:(value,{'usage':{},'model':config['model']})):
                manifest=a.generate(root,config)
            self.assertEqual(manifest['status'],'complete')
            self.assertEqual(manifest['failed_annotations'],{})
            a.check_outputs(root,config)

            config['output_dir']='all_rejected'
            with patch.object(a,'load_qwen',return_value=Mock(side_effect=a.AnnotationError('bad JSON'))):
                self.assertEqual(a.generate(root,config)['count'],0)
            # A zero-annotation reset cannot carry failures from a removed corpus ID.
            a.write_jsonl(root/'papers.jsonl',[papers[1]])
            with patch.object(a,'load_qwen',return_value=lambda p,i:(second,{'usage':{},'model':config['model']})):
                manifest=a.generate(root,config)
            self.assertEqual(manifest['failed_annotations'],{})
            a.check_outputs(root,config)

if __name__=='__main__':
    unittest.main()
