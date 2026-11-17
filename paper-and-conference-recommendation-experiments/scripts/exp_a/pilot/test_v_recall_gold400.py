"""Real pinned V-recall; only generation and embedding inference are substituted."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'data/exp_a/.kaggle/v_recall_gold400'
PINNED=ROOT/'data/exp_a/.kaggle/v_recall/release_20261026_v1/preflight_project'
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class Gold400Tests(unittest.TestCase):
    def setUp(self):
        self.runner=load('gold400_runner_test',HERE/'runner.py')
        self.shared=load('gold400_shared_test',PINNED/'data/exp_a/.kaggle/matrix.py')
        self.paper=dict(paper_id='P000019',title='Document retrieval',abstract='We use hashing and nearest neighbor search for document retrieval.')
        self.draft=dict(paper_id=self.paper['paper_id'],**{f:[] for f in self.shared.FACETS})
        self.draft['method']=[dict(concept='hashing',evidence_id='A0')]
        self.coverage=dict(paper_id=self.paper['paper_id'],task=[dict(concept='document retrieval',evidence_id='A0')],method=[dict(concept='nearest neighbor search',evidence_id='A0')])
        self.config=dict(seed=42,max_attempts=3,max_new_tokens=2048,do_sample=False,dataset_resource_filter=True,prompt_version='3.7')
    def generate(self,replies):
        calls=[]
        def run(messages,seed):
            calls.append((copy.deepcopy(messages),seed));self.assertLessEqual(len(calls),3)
            reply=replies[len(calls)-1]
            return (reply if isinstance(reply,str) else json.dumps(reply)),dict(usage=dict(input_tokens=10,output_tokens=20),generation_seconds=1,reached_token_limit=False)
        return run,calls
    def test_fresh_draft_counts_three_new_calls_and_uses_only_source(self):
        generate,calls=self.generate([self.draft,self.draft,self.coverage])
        before=copy.deepcopy(self.paper)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
            r=self.runner.annotate_fresh(self.shared,self.paper,'source instruction',self.config,{},generate,Path(tmp),signature='test')
        self.assertEqual(self.paper,before);self.assertEqual(len(calls),3)
        self.assertEqual([seed for _,seed in calls],[99,100,101])
        self.assertEqual(r['new_cost']['calls'],3);self.assertEqual(r['new_cost']['output_tokens'],60)
        self.assertTrue(all(not t['inherited'] for t in r['call_trace']))
        self.assertEqual(r['facets']['method'],['hashing','nearest neighbor search'])
        self.assertEqual(r['facets']['task'],['document retrieval'])
        source=json.loads(calls[0][0][1]['content'])
        self.assertEqual(set(source),{'paper_id','evidence_options'})
        self.assertNotIn('human_gold',json.dumps(calls))
    def test_fresh_first_pass_messages_match_the_original_engine(self):
        generate,calls=self.generate([self.draft,self.draft,self.coverage])
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
            self.runner.annotate_fresh(self.shared,self.paper,'source instruction',self.config,{},generate,Path(tmp),signature='test')
        expected=[dict(role='system',content='source instruction\nReturn JSON only. Schema: '+json.dumps(self.shared.base.SCHEMA)),dict(role='user',content=json.dumps(dict(paper_id=self.paper['paper_id'],evidence_options={k:v['evidence'] for k,v in self.shared.base.evidence_options(self.paper).items()}),ensure_ascii=False))]
        self.assertEqual(calls[0][0],expected)
    def test_cached_fresh_draft_resumes_without_repeating_call_one(self):
        generate,calls=self.generate([self.draft,self.draft,self.coverage])
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
            tmp=Path(tmp)
            first=self.runner.annotate_fresh(self.shared,self.paper,'source instruction',self.config,{},generate,tmp,signature='test')
            again,other=self.generate([self.draft,self.coverage])
            second=self.runner.annotate_fresh(self.shared,self.paper,'source instruction',self.config,{},again,tmp,signature='test')
            self.assertEqual(len(other),2);self.assertEqual(first['facets'],second['facets'])
            self.assertEqual(second['new_cost']['calls'],3)
            with self.assertRaises(ValueError):self.runner.annotate_fresh(self.shared,self.paper,'changed instruction',self.config,{},again,tmp,signature='other')
    def test_malformed_fresh_draft_can_recover_on_review_without_extra_calls(self):
        generate,calls=self.generate(['bad json',self.draft,self.coverage])
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
            r=self.runner.annotate_fresh(self.shared,self.paper,'source instruction',self.config,{},generate,Path(tmp),signature='test')
        self.assertEqual(len(calls),3);self.assertIn('hashing',r['facets']['method'])
    def test_two_worker_shards_cover_all400_once(self):
        ids=[f'P{i:06d}' for i in range(1,401)]
        a=self.runner.shard(ids,0);b=self.runner.shard(ids,1)
        self.assertEqual(len(a),200);self.assertEqual(len(b),200)
        self.assertEqual(set(a)|set(b),set(ids));self.assertFalse(set(a)&set(b))
        with self.assertRaises(ValueError):self.runner.shard(ids,2)
    def test_bundle_unpack_rejects_unknown_or_traversing_files(self):
        import zipfile
        boot=load('gold400_bootstrap_test',HERE/'bootstrap.template.py')
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
            tmp=Path(tmp);bundle=tmp/'test.bin'
            with zipfile.ZipFile(bundle,'w') as z:z.writestr('../escape.txt','bad')
            with self.assertRaises(ValueError):boot.unpack(bundle,tmp/'project',dict(files={},signature='test'))
            self.assertFalse((tmp/'escape.txt').exists())
    def unpack_fixture(self,tmp):
        boot=load('gold400_fixture_boot',HERE/'bootstrap.template.py')
        settings=json.loads((HERE/'release_20261026_v1/settings.json').read_text())
        root=Path(tmp)/'project'
        boot.unpack(HERE/'release_20261026_v1/input-dataset/gold400_bundle.zip.bin',root,settings)
        return root,settings
    def test_workers_do_not_read_gold_and_evaluation_detects_tampering(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
            root,settings=self.unpack_fixture(tmp)
            (root/'evaluation_only/human_gold.jsonl').write_text('gold is unavailable',encoding='utf-8')
            _,papers,_,_=self.runner.verify(root,settings)
            self.assertEqual(len(papers),400)
            with self.assertRaises(ValueError):self.runner.verify(root,settings,evaluation=True)
    def test_missing_predictions_fail_before_gold_is_opened(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
            root,settings=self.unpack_fixture(tmp)
            (root/'evaluation_only/human_gold.jsonl').write_text('not readable JSON',encoding='utf-8')
            with self.assertRaises(FileNotFoundError):self.runner.evaluate(root,settings)
            self.assertFalse((root/'results/prediction_manifest.json').exists())
    def test_offline400_scoring_keeps_all_records_and_same_stage_counts(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
            root,settings=self.unpack_fixture(tmp)
            shared,papers,_,_=self.runner.verify(root,settings)
            for paper in papers:
                pid=paper['paper_id'];selection=dict(paper_id=pid,**{f:[] for f in shared.FACETS})
                selection['method']=[dict(concept=paper['title'],evidence_id='T0')]
                record=dict(paper_id=pid,arm='V-recall',source_sha256=self.runner.digest(paper),
                    audit=dict(attempts_used=3,attempt_scores=[dict(raw_output=json.dumps(selection))]),
                    call_trace=[dict(inherited=False,usage=dict(output_tokens=1)) for i in range(3)],
                    new_cost=dict(calls=3),facets=dict(paper_id=pid,**{f:[x['concept'] for x in selection[f]] for f in shared.FACETS}),
                    coverage=dict(base_annotation=selection,accepted=[],rejected=[],errors=[]),
                    base_review_audit=dict(fallback_used=False),fallback_used=False,annotation_fallback=False,coverage_fallback=False,
                    usage=dict(input_tokens=3,output_tokens=3),generation_seconds=3)
                shared.save_record(root/f'results/V-recall/records/{pid}.json',record,settings['signature'])
            with patch.object(self.runner,'load_shared',return_value=shared),patch.object(shared.evaluator,'encode_labels',side_effect=lambda root,labels:({x:[0.] for x in labels},dict(test_only='nonexact embedding matches disabled'))):
                result=self.runner.evaluate(root,settings)
            self.assertEqual(result['paper_count'],400);self.assertEqual(result['excluded_papers'],0)
            self.assertEqual(result['reference_kind'],'human_gold');self.assertEqual(result['fresh_calls'],1200)
            self.assertEqual(len({(r['tp'],r['fp'],r['fn']) for r in result['table']}),1)
            self.assertTrue((root/'results/prediction_manifest.json').exists())
            self.assertEqual(len(json.loads((root/'results/coverage_addition_audit.json').read_text())),400)
    def test_f2_is_recall_weighted(self):
        self.assertAlmostEqual(self.runner.f2(dict(tp=2,fp=1,fn=3)),10/23)
        self.assertEqual(self.runner.f2(dict(tp=0,fp=0,fn=0)),0)
if __name__=='__main__':unittest.main()
