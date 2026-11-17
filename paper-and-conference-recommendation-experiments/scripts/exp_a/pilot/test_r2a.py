"""R2a behavioral checks; real frozen validator, fake only expensive model calls."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
FROZEN = ROOT/'data/exp_a/.kaggle/base_improvement/release_20261022_v1/preflight_project'
sys.path.insert(0, str(FROZEN/'data/exp_a/.kaggle'))
spec = importlib.util.spec_from_file_location('r2a_test_shared', FROZEN/'data/exp_a/.kaggle/matrix.py')
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)


class RepairTests(unittest.TestCase):
    def setUp(self):
        path = ROOT/'data/exp_a/.kaggle/r2a/repair.py'
        self.assertTrue(path.is_file(), 'R2a repair module is not implemented')
        spec = importlib.util.spec_from_file_location('r2a_repair_test', path)
        self.mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.mod)
        self.paper = dict(paper_id='P000001', title='Document retrieval',
                          abstract='Existing retrieval is slow. We use hashing for document retrieval.')
        self.good = dict(paper_id='P000001', **{f: [] for f in shared.FACETS})
        self.good['problem'] = [dict(concept='Existing retrieval is slow', evidence_id='A0')]
        self.good['task'] = [dict(concept='document retrieval', evidence_id='A1')]
        self.good['method'] = [dict(concept='invented method', evidence_id='A1')]
        self.bad2 = copy.deepcopy(self.good)
        self.bad2['method'].append(dict(concept='another invention', evidence_id='A1'))

    def test_scoped_validator_accepts_current_positive_not_background_negation(self):
        paper = dict(paper_id='P000001', title='Adaptation', abstract=
            'Although self-training without reranking has been found not to improve in-domain accuracy, '
            'we show that it is effective for parser domain adaptation.')
        selection = dict(paper_id=paper['paper_id'], **{f: [] for f in shared.FACETS})
        selection['contribution'] = [dict(concept='self-training without reranking is effective for parser domain adaptation', evidence_id='A0')]
        old = shared.v3.assess_generation(json.dumps(selection),paper,'3.1',prompt_version='3.7')[2]
        self.assertTrue(any('negation' in e for e in old['validation_errors']))
        new = self.mod.assess(shared,json.dumps(selection),paper,scoped=True)[2]
        self.assertEqual(new['validation_errors'], [])
        self.assertEqual(shared.v3.assess_generation(json.dumps(selection),paper,'3.1',prompt_version='3.7')[2],old)

    def test_scope_still_rejects_omitted_actual_main_negation_and_quantity(self):
        paper = dict(paper_id='P000001', title='Accuracy', abstract=
            'Although earlier methods were slow, we show that our model does not improve accuracy by 12%.')
        for concept in ('our model does improve accuracy by 12%',):
            selection = dict(paper_id=paper['paper_id'], **{f: [] for f in shared.FACETS})
            selection['contribution'] = [dict(concept=concept,evidence_id='A0')]
            a = self.mod.assess(shared,json.dumps(selection),paper,scoped=True)[2]
            self.assertTrue(a['validation_errors'])
        paper['abstract']='Our model achieves 12% accuracy using hashing.'
        selection['contribution']=[dict(concept='Our model achieves accuracy using hashing',evidence_id='A0')]
        self.assertTrue(self.mod.assess(shared,json.dumps(selection),paper,scoped=True)[2]['validation_errors'])

    def test_patch_changes_only_flagged_item_and_preserves_input(self):
        before=copy.deepcopy(self.good)
        reply=dict(paper_id='P000001',edits=[dict(op='replace',facet='method',index=0,
            concept='hashing',evidence_id='A1',reason='Use the actual method in A1')])
        value,log=self.mod.apply_patch(shared,self.good,reply,self.paper,{('method',0)})
        self.assertEqual(self.good,before)
        self.assertEqual(value['problem'],before['problem'])
        self.assertEqual(value['task'],before['task'])
        self.assertEqual(value['method'],[dict(concept='hashing',evidence_id='A1')])
        self.assertEqual(len(log),1)

    def test_patch_is_atomic_rejects_out_of_scope_duplicates_and_wrong_paper(self):
        edit=dict(op='replace',facet='method',index=0,concept='hashing',evidence_id='A1',reason='source')
        cases=[dict(paper_id='P000001',edits=[edit,dict(edit,facet='problem')]),
               dict(paper_id='P000001',edits=[edit,edit]),dict(paper_id='P000002',edits=[edit]),
               dict(paper_id='P000001',edits=[dict(edit,index=True)])]
        for reply in cases:
            before=copy.deepcopy(self.good)
            with self.assertRaises(ValueError):self.mod.apply_patch(shared,self.good,reply,self.paper,{('method',0)})
            self.assertEqual(self.good,before)

    def test_deletions_use_snapshot_indices_and_require_auditable_source_reason(self):
        reply=dict(paper_id='P000001',edits=[dict(op='remove',facet='method',index=0,
            evidence_id='A1',reason='unsupported',explanation='A1 supports hashing, not this invented method'),
            dict(op='replace',facet='method',index=1,concept='hashing',evidence_id='A1',reason='source')])
        value,log=self.mod.apply_patch(shared,self.bad2,reply,self.paper,{('method',0),('method',1)})
        self.assertEqual(value['method'],[dict(concept='hashing',evidence_id='A1')])
        bad=copy.deepcopy(reply);bad['edits'][0]['reason']='silence lexical error'
        with self.assertRaises(ValueError):self.mod.apply_patch(shared,self.bad2,bad,self.paper,{('method',0),('method',1)})
        bad=copy.deepcopy(reply);bad['edits'][0]['evidence_id']='A99'
        with self.assertRaises(ValueError):self.mod.apply_patch(shared,self.bad2,bad,self.paper,{('method',0),('method',1)})

    def run_arm(self,arm,replies):
        path=ROOT/'data/exp_a/.kaggle/r2a/runner.py'
        self.assertTrue(path.is_file(),'R2a runner is not implemented')
        spec=importlib.util.spec_from_file_location('r2a_runner_test',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        cached=dict(raw_output=json.dumps(self.good),seed=45,stage='extract',attempt=1,
                    usage=dict(input_tokens=100,output_tokens=10),generation_seconds=7)
        before=copy.deepcopy(cached);calls=[]
        def generate(messages,seed):
            calls.append(copy.deepcopy(messages))
            return replies[len(calls)-1],dict(usage=dict(input_tokens=200,output_tokens=20),generation_seconds=2)
        config=dict(prompt_version='3.7',max_attempts=3,max_new_tokens=2048,seed=42,
                    do_sample=False,dataset_resource_filter=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'.test-tmp') as directory:
            record=module.annotate(shared,self.paper,'BASE',config,{},generate,arm,
                Path(directory)/'failure.json',cached=cached)
        self.assertEqual(cached,before)
        return record,calls

    def test_runner_patch_reuses_draft_and_protects_problem(self):
        reply=json.dumps(dict(paper_id='P000001',edits=[dict(op='replace',facet='method',index=0,
            concept='hashing',evidence_id='A1',reason='Actual method in source')]))
        record,calls=self.run_arm('R2a-P',[reply])
        self.assertEqual(len(calls),1)
        self.assertEqual(record['audit']['attempt_scores'][0]['raw_output'],json.dumps(self.good))
        self.assertEqual(record['facets']['problem'],['Existing retrieval is slow'])
        self.assertEqual(record['facets']['method'],['hashing'])
        self.assertFalse(record['fallback_used'])
        self.assertEqual(record['new_cost']['calls'],1)
        self.assertEqual(record['usage']['output_tokens'],30)
        self.assertEqual(record['generation_seconds'],9)
        self.assertEqual(record['protected_items_changed'],0)

    def test_runner_bad_patch_cannot_exceed_budget_or_erase_other_items(self):
        record,calls=self.run_arm('R2a-full',['not JSON','{"paper_id":"P000001","edits":[]}'])
        self.assertLessEqual(len(calls),2)
        self.assertTrue(record['fallback_used'])
        self.assertEqual(record['facets']['problem'],['Existing retrieval is slow'])
        self.assertEqual(record['audit']['attempts_used'],3)
        self.assertTrue(record['audit']['attempt_scores'][1]['patch_error'])

    def test_runner_valid_draft_needs_no_patch_and_does_not_claim_semantic_review(self):
        self.good['method']=[dict(concept='hashing',evidence_id='A1')]
        record,calls=self.run_arm('R2a-P',[])
        self.assertEqual(calls,[])
        self.assertEqual(record['new_cost']['calls'],0)
        self.assertFalse(record['audit']['self_review_completed'])
        self.assertTrue(record['audit']['validation_passed'])

    def test_replacement_cannot_expand_scope_by_making_protected_item_duplicate(self):
        self.good['method'].append(dict(concept='hashing',evidence_id='A1'))
        first=dict(paper_id='P000001',edits=[dict(op='replace',facet='method',index=0,
            concept='hashing',evidence_id='A1',reason='source')])
        second=dict(paper_id='P000001',edits=[dict(op='replace',facet='method',index=1,
            concept='document retrieval',evidence_id='A1',reason='source')])
        record,calls=self.run_arm('R2a-P',[json.dumps(first),json.dumps(second)])
        self.assertTrue(record['fallback_used'])
        self.assertEqual(record['facets']['method'],['invented method','hashing'])
        self.assertTrue(record['audit']['attempt_scores'][1]['patch_error'])


if __name__ == '__main__':unittest.main()
