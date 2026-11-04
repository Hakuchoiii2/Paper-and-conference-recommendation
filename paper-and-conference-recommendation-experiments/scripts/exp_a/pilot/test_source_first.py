"""Real frozen validator; only model generation is replaced in these tests."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'data/exp_a/.kaggle/source_first'
FROZEN=ROOT/'data/exp_a/.kaggle/r2a/release_20261024_v1/preflight_project'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class SourceTests(unittest.TestCase):
    def setUp(self):
        self.mod=load('source_units_test',HERE/'units.py')
        self.shared=load('source_shared_test',FROZEN/'data/exp_a/.kaggle/matrix.py')
        self.paper=dict(paper_id='P000001',title='Hash retrieval',abstract='Existing retrieval is slow. We use hashing for document retrieval.')
        self.plan=dict(paper_id='P000001',units=[dict(evidence_id='A1',span='hashing',roles=['method'],origin='current',context_ids=[])])
        self.good=dict(paper_id='P000001',**{f:[] for f in self.shared.FACETS})
        self.good['method']=[dict(concept='hashing',evidence_id='A1')]
    def test_inventory_validation(self):
        self.assertEqual(len(self.mod.validate_inventory(self.plan,self.paper,self.shared)),1)
        for key,value in [('span','invented'),('evidence_id','A99'),('roles',[]),('roles',['review']),('origin','novel'),('context_ids',['A99'])]:
            bad=copy.deepcopy(self.plan);bad['units'][0][key]=value
            with self.assertRaises(ValueError):self.mod.validate_inventory(bad,self.paper,self.shared)
        bad=copy.deepcopy(self.plan);bad['paper_id']='P9'
        with self.assertRaises(ValueError):self.mod.validate_inventory(bad,self.paper,self.shared)
    def test_multiple_roles_and_negative_finding(self):
        paper=dict(paper_id='P000001',title='ORBIT',abstract='We introduce ORBIT. It does not improve accuracy over hashing.')
        plan=dict(paper_id='P000001',units=[dict(evidence_id='A0',span='ORBIT',roles=['method','contribution'],origin='current',context_ids=['A1']),dict(evidence_id='A1',span='It does not improve accuracy over hashing',roles=['contribution'],origin='current',context_ids=['A0'])])
        self.assertEqual(len(self.mod.validate_inventory(plan,paper,self.shared)),2)
    def run_replies(self,replies):
        calls=[];before=copy.deepcopy(self.paper)
        def generate(messages,seed):
            calls.append(copy.deepcopy(messages));self.assertLessEqual(len(calls),3)
            return json.dumps(replies[len(calls)-1]),dict(usage=dict(input_tokens=10,output_tokens=20),generation_seconds=1,reached_token_limit=False)
        config=dict(seed=42,max_attempts=3,max_new_tokens=2048,do_sample=False,dataset_resource_filter=True)
        r=self.mod.annotate(self.shared,self.paper,'source-only instruction',config,{},generate)
        self.assertEqual(self.paper,before)
        for messages in calls:self.assertNotIn('review_annotations',json.dumps(messages))
        return r,calls
    def test_clean_two_calls_full_source(self):
        r,calls=self.run_replies([self.plan,self.good])
        self.assertEqual(len(calls),2);self.assertFalse(r['fallback_used'])
        self.assertEqual(r['facets']['method'],['hashing'])
        self.assertIn('Existing retrieval is slow',calls[1][1]['content'])
    def test_plan_retry_consumes_budget(self):
        r,calls=self.run_replies([{},self.plan,self.good])
        self.assertEqual(len(calls),3);self.assertTrue(r['inventory_valid']);self.assertFalse(r['fallback_used'])
        self.assertEqual([t['stage'] for t in r['call_trace']],['inventory','inventory_retry','extract'])
    def test_plan_failure_visible(self):
        r,calls=self.run_replies([{}, {}, self.good])
        self.assertTrue(r['fallback_used']);self.assertFalse(r['inventory_valid']);self.assertFalse(r['annotation_fallback'])
    def test_one_annotation_repair(self):
        bad=copy.deepcopy(self.good);bad['method'][0]['concept']='invented'
        r,calls=self.run_replies([self.plan,bad,self.good])
        self.assertEqual(len(calls),3);self.assertFalse(r['fallback_used'])
        self.assertEqual(r['facets']['method'],['hashing']);self.assertEqual(r['call_trace'][-1]['stage'],'repair')
    def test_invalid_last_reply_retains_grounded_items(self):
        bad=copy.deepcopy(self.good);bad['method'].append(dict(concept='invented',evidence_id='A1'))
        r,calls=self.run_replies([self.plan,bad,{}])
        self.assertTrue(r['annotation_fallback']);self.assertIn('hashing',r['facets']['method'])
    def test_truncated_plans_use_two_calls_and_remain_visible(self):
        calls=[]
        def generate(messages,seed):
            calls.append(messages)
            raw=self.plan if len(calls)<3 else self.good
            return json.dumps(raw),dict(usage=dict(input_tokens=10,output_tokens=2048),generation_seconds=1,reached_token_limit=len(calls)<3)
        config=dict(seed=42,max_attempts=3,max_new_tokens=2048,do_sample=False,dataset_resource_filter=True)
        r=self.mod.annotate(self.shared,self.paper,'source-only',config,{},generate)
        self.assertEqual(len(calls),3);self.assertFalse(r['inventory_valid']);self.assertTrue(r['fallback_used'])
        self.assertFalse(r['annotation_fallback']);self.assertEqual(r['source_inventory'],[])
        self.assertIn('Existing retrieval is slow',calls[2][1]['content'])
    def test_cost_counts_all_calls_with_contiguous_seed_schedule(self):
        r,calls=self.run_replies([{},self.plan,self.good])
        self.assertEqual(r['new_cost']['calls'],3)
        self.assertEqual(r['new_cost']['output_tokens'],60)
        self.assertEqual(r['usage']['input_tokens'],30)
        self.assertEqual([t['seed'] for t in r['call_trace']],[45,46,47])
    def test_v_token_cap_accounting_uses_audit_not_sparse_call_trace(self):
        runner=load('source_reporting_test',HERE/'runner.py')
        row=dict(call_trace=[dict(inherited=True)],audit=dict(attempt_scores=[dict(usage=dict(output_tokens=2048)),dict(usage=dict(output_tokens=100))]))
        self.assertEqual(runner.calls_at_output_token_cap([row],'R2a-V',2048),1)
        source=dict(call_trace=[dict(usage=dict(output_tokens=2048)),dict(usage=dict(output_tokens=20))])
        self.assertEqual(runner.calls_at_output_token_cap([source],'Source-first',2048),1)
if __name__=='__main__':unittest.main()
