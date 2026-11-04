"""Real V validator and review path; replace only expensive model generation."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'data/exp_a/.kaggle/v_recall'
FROZEN=ROOT/'data/exp_a/.kaggle/r2a/release_20261024_v1/preflight_project'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class RecallTests(unittest.TestCase):
    def setUp(self):
        self.mod=load('recall_test',HERE/'recall.py')
        self.shared=load('recall_shared_test',FROZEN/'data/exp_a/.kaggle/matrix.py')
        self.paper=dict(paper_id='P000001',title='Document retrieval',abstract='We use hashing and nearest neighbor search for document retrieval.')
        self.draft=dict(paper_id='P000001',**{f:[] for f in self.shared.FACETS})
        self.draft['method']=[dict(concept='hashing',evidence_id='A0')]
        self.additions=dict(paper_id='P000001',task=[dict(concept='document retrieval',evidence_id='A0')],method=[dict(concept='nearest neighbor search',evidence_id='A0')])
        self.config=dict(seed=42,max_attempts=3,max_new_tokens=2048,do_sample=False,dataset_resource_filter=True,prompt_version='3.7')
        self.cached=dict(stage='extract',attempt=1,seed=45,raw_output=json.dumps(self.draft),usage=dict(input_tokens=100,output_tokens=50),generation_seconds=5)
    def run_reply(self,reply=None,truncated=False):
        if reply is None:reply=self.additions
        calls=[];before=copy.deepcopy((self.paper,self.cached,self.config))
        def generate(messages,seed):
            calls.append((copy.deepcopy(messages),seed))
            self.assertLessEqual(len(calls),2)
            raw=json.dumps(self.draft) if len(calls)==1 else (reply if isinstance(reply,str) else json.dumps(reply))
            return raw,dict(usage=dict(input_tokens=10,output_tokens=20),generation_seconds=1,reached_token_limit=truncated and len(calls)==2)
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            r=self.mod.annotate(self.shared,self.paper,'source instruction',self.config,{},generate,Path(tmp)/'last_failure.json',cached=self.cached)
        self.assertEqual((self.paper,self.cached,self.config),before)
        return r,calls
    def test_recovers_two_ideas_from_an_already_cited_sentence(self):
        r,calls=self.run_reply()
        self.assertEqual(r['facets']['method'],['hashing','nearest neighbor search'])
        self.assertEqual(r['facets']['task'],['document retrieval'])
        self.assertEqual(r['coverage']['accepted_count'],2)
        self.assertFalse(r['coverage_fallback']);self.assertEqual(len(calls),2)
        packet=json.loads(calls[-1][0][-1]['content'])
        self.assertIn('nearest neighbor search',packet['evidence_options']['A0'])
        self.assertEqual(packet['annotation']['method'],self.draft['method'])
    def test_rejects_unfounded_addition_but_retains_other_good_additions(self):
        bad=copy.deepcopy(self.additions);bad['method'].append(dict(concept='invented',evidence_id='A0'))
        r,_=self.run_reply(bad)
        self.assertEqual(r['facets']['method'],['hashing','nearest neighbor search'])
        self.assertTrue(r['coverage_fallback']);self.assertEqual(r['coverage']['accepted_count'],2)
        self.assertEqual(len(r['coverage']['rejected']),1)
    def test_unknown_source_id_is_rejected(self):
        bad=copy.deepcopy(self.additions);bad['method'][0]['evidence_id']='A99'
        r,_=self.run_reply(bad)
        self.assertEqual(r['facets']['method'],['hashing']);self.assertTrue(r['coverage_fallback'])
    def test_duplicate_and_non_target_changes_cannot_rewrite_the_draft(self):
        duplicate=copy.deepcopy(self.additions);duplicate['method'].append(self.draft['method'][0])
        r,_=self.run_reply(duplicate);self.assertEqual(r['facets']['method'],['hashing','nearest neighbor search'])
        bad=dict(self.additions,problem=[dict(concept='hashing',evidence_id='A0')])
        r,_=self.run_reply(bad);self.assertEqual(r['facets']['method'],['hashing'])
        self.assertEqual(r['facets']['problem'],[]);self.assertTrue(r['coverage_fallback'])
    def test_empty_additions_is_a_successful_no_op(self):
        r,_=self.run_reply(dict(paper_id='P000001',task=[],method=[]))
        self.assertEqual(r['facets']['method'],['hashing']);self.assertFalse(r['coverage_fallback'])
    def test_malformed_and_truncated_coverage_preserve_base(self):
        for raw,truncated in [('not json',False),(self.additions,True)]:
            r,_=self.run_reply(raw,truncated)
            self.assertEqual(r['facets']['method'],['hashing']);self.assertEqual(r['facets']['task'],[])
            self.assertTrue(r['coverage_fallback'])
    def test_seed_budget_cost_and_raw_draft_provenance(self):
        r,calls=self.run_reply()
        self.assertEqual([seed for _,seed in calls],[46,47])
        self.assertEqual(r['audit']['attempts_used'],3);self.assertEqual(r['new_cost']['calls'],2)
        self.assertEqual(r['usage']['output_tokens'],90);self.assertEqual(r['new_cost']['output_tokens'],40)
        self.assertEqual(r['audit']['attempt_scores'][0]['raw_output'],self.cached['raw_output'])
        self.assertTrue(r['call_trace'][0]['inherited'])
        self.assertEqual(r['coverage']['base_annotation']['method'],self.draft['method'])
        for messages,_ in calls:self.assertNotIn('review_annotations',json.dumps(messages))
    def test_first_review_messages_and_seed_match_original_v(self):
        r,calls=self.run_reply()
        original_calls=[]
        def generate(messages,seed):
            original_calls.append((copy.deepcopy(messages),seed))
            return json.dumps(self.draft),dict(usage=dict(input_tokens=10,output_tokens=20),generation_seconds=1)
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            self.mod.v.annotate(self.shared,self.paper,'source instruction',self.config,{},generate,'R2a-V',Path(tmp)/'last_failure.json',cached=self.cached)
        self.assertEqual(calls[0],original_calls[0])
    def test_f2_uses_recall_weighting_and_handles_empty_counts(self):
        runner=load('recall_runner_test',HERE/'runner.py')
        self.assertAlmostEqual(runner.f2(dict(tp=2,fp=1,fn=3)),10/23)
        self.assertEqual(runner.f2(dict(tp=0,fp=0,fn=0)),0)
    def test_rejects_changed_generation_budget(self):
        self.config['max_attempts']=4
        with self.assertRaises(ValueError):self.run_reply()
if __name__=='__main__':unittest.main()
