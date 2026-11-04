import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / 'data/exp_a/.kaggle/compact_gold400'
FROZEN = HERE.parent / 'v_recall_gold400/release_20261026_v1/preflight_project'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class CompactTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((HERE/'runner.py').exists(), 'compact runner is missing')
        self.runner = load('compact_test_runner', HERE/'runner.py')
        self.shared = load('compact_test_shared', FROZEN/'data/exp_a/.kaggle/matrix.py')
        self.paper = dict(paper_id='P000019', title='Document retrieval', abstract='We use hashing and nearest neighbor search for document retrieval.')
        self.draft = dict(paper_id=self.paper['paper_id'], **{f:[] for f in self.shared.FACETS})
        self.draft['task'] = [dict(concept='document retrieval', evidence_id='A0')]
        self.draft['method'] = [dict(concept='invented technique', evidence_id='A0')]
        self.config = dict(seed=42, max_attempts=3, max_new_tokens=2048, do_sample=False, dataset_resource_filter=True, prompt_version='3.7')

    def run_replies(self, replies, work=None):
        calls=[]
        def generate(messages, seed):
            calls.append((copy.deepcopy(messages), seed))
            item=replies[len(calls)-1]
            raw=item if isinstance(item,str) else json.dumps(item)
            return raw, dict(usage=dict(input_tokens=10,output_tokens=20),generation_seconds=1,reached_token_limit=False)
        if work is not None:
            return self.runner.annotate_fresh(self.shared,self.paper,'compact source instruction',self.config,{},generate,work,signature='test'),calls
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
            return self.runner.annotate_fresh(self.shared,self.paper,'compact source instruction',self.config,{},generate,Path(tmp),signature='test'),calls

    def patch(self, **updates):
        edit=dict(op='replace',facet='method',index=0,concept='hashing',evidence_id='A0',reason='source phrase')
        edit.update(updates)
        return dict(paper_id=self.paper['paper_id'],edits=[edit])

    def test_replaces_only_invalid_item_and_stops_when_valid(self):
        record,calls=self.run_replies([self.draft,self.patch()])
        self.assertEqual(len(calls),2)
        self.assertEqual([s for _,s in calls],[99,100])
        self.assertEqual(record['facets']['method'],['hashing'])
        self.assertEqual(record['facets']['task'],['document retrieval'])
        self.assertEqual(record['protected_items_changed'],0)
        self.assertEqual(record['new_cost']['calls'],2)
        self.assertEqual(record['usage']['output_tokens'],40)
        self.assertNotIn('human_gold',json.dumps(calls))
        packet=json.loads(calls[1][0][1]['content'])
        self.assertEqual([(x['facet'],x['index']) for x in packet['flagged_items']],[('method',0)])

    def test_valid_draft_needs_one_call_without_coverage(self):
        self.draft['method'][0]['concept']='hashing'
        record,calls=self.run_replies([self.draft])
        self.assertEqual(len(calls),1)
        self.assertFalse(record['fallback_used'])
        self.assertEqual(record['new_cost']['calls'],1)

    def test_patch_cannot_edit_protected_valid_item(self):
        bad=self.patch(facet='task',concept='hashing')
        record,calls=self.run_replies([self.draft,bad,self.patch()])
        self.assertEqual(record['facets']['task'],['document retrieval'])
        self.assertEqual(record['facets']['method'],['hashing'])
        self.assertTrue(record['audit']['attempt_scores'][1]['patch_error'])
        self.assertEqual(len(calls),3)

    def test_bad_patch_preserves_previous_candidate(self):
        record,calls=self.run_replies([self.draft,'bad json','bad json'])
        self.assertEqual(record['facets']['method'],['invented technique'])
        self.assertEqual(record['facets']['task'],['document retrieval'])
        self.assertTrue(record['fallback_used'])
        self.assertEqual(len(calls),3)

    def test_malformed_draft_recovers_then_gets_targeted_repair(self):
        record,calls=self.run_replies(['bad json',self.draft,self.patch()])
        self.assertEqual(record['facets']['method'],['hashing'])
        self.assertEqual(len(calls),3)
        self.assertEqual(record['audit']['attempt_scores'][1]['stage'],'schema_recovery')

    def test_draft_resume_preserves_logical_cost_and_checks_identity(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
            work=Path(tmp)
            first,_=self.run_replies([self.draft,self.patch()],work)
            second,calls=self.run_replies([],work)
            self.assertEqual(len(calls),0)
            self.assertEqual(first['facets'],second['facets'])
            self.assertEqual(second['new_cost']['calls'],2)
            self.assertEqual(second['resumed_calls'],2)
            self.paper['title']='changed source'
            with self.assertRaises(ValueError):self.run_replies([],work)

    def test_truncated_draft_never_counts_as_valid(self):
        valid=copy.deepcopy(self.draft);valid['method'][0]['concept']='hashing'
        calls=[]
        def generate(messages,seed):
            calls.append(seed)
            return json.dumps(valid),dict(usage=dict(input_tokens=1,output_tokens=2048 if len(calls)==1 else 20),generation_seconds=1,reached_token_limit=len(calls)==1)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
            record=self.runner.annotate_fresh(self.shared,self.paper,'instruction',self.config,{},generate,Path(tmp),signature='test')
        self.assertEqual(len(calls),2)
        self.assertFalse(record['fallback_used'])

    def test_truncated_patch_retries_patch_without_regenerating_protected_items(self):
        calls=[]
        def generate(messages,seed):
            calls.append(copy.deepcopy(messages))
            if len(calls)==1:reply=self.draft
            elif len(calls)==2:reply=self.patch()
            else:
                packet=json.loads(messages[1]['content'])
                self.assertIn('annotation',packet,'truncated patch must retry an indexed patch')
                self.assertEqual(packet['annotation']['task'],self.draft['task'])
                reply=self.patch()
            return json.dumps(reply),dict(usage=dict(input_tokens=10,output_tokens=2048 if len(calls)==2 else 20),generation_seconds=1,reached_token_limit=len(calls)==2)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
            record=self.runner.annotate_fresh(self.shared,self.paper,'instruction',self.config,{},generate,Path(tmp),signature='test')
        self.assertEqual(record['facets']['task'],['document retrieval'])
        self.assertEqual(record['facets']['method'],['hashing'])
        self.assertFalse(record['fallback_used'])

class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'tmp')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)/'project'

    def package(self):
        self.assertTrue((HERE/'build.py').exists(), 'compact builder is missing')
        builder=load('compact_builder_test',HERE/'build.py')
        from unittest.mock import patch
        release=Path(self.temp.name)/'release'
        with patch.object(builder,'RELEASE',release):builder.main()
        settings=json.loads((release/'settings.json').read_text(encoding='utf-8'))
        boot=load('compact_boot_test',HERE/'bootstrap.template.py')
        boot.unpack(release/'input-dataset/gold400_bundle.zip.bin',self.root,settings)
        runner=load('compact_packaged_runner_test',self.root/'runner.py')
        return runner,settings,release

    def test_packaged_cohort_frozen_helpers_and_compact_prompt(self):
        runner,settings,release=self.package()
        shared,papers,config,instruction=runner.verify(self.root,settings,evaluation=True)
        self.assertEqual(len(papers),400)
        self.assertEqual(len(runner.shard(papers,0)),200)
        self.assertFalse(set(p['paper_id'] for p in runner.shard(papers,0)) & set(p['paper_id'] for p in runner.shard(papers,1)))
        self.assertIn('contiguous',instruction)
        self.assertIn('independent',instruction)
        self.assertNotIn('During review, METHOD and CONTRIBUTION remain open',instruction)
        for name in ['repair.py','r2a_runner.py','legacy.py','scripts/exp_a/evaluate_exp_a.py','data/exp_a/.kaggle/matrix.py']:
            self.assertEqual((self.root/name).read_bytes(),(FROZEN/name).read_bytes())
        self.assertTrue(json.loads((release/'kernel/kernel-metadata.json').read_text())['is_private'])
        self.assertEqual(settings['gold_sha256'],runner.sha(FROZEN/'evaluation_only/human_gold.jsonl'))

    def test_cloud_bootstrap_reuses_old_bundle_with_code_only_overlay(self):
        import base64
        runner,settings,release=self.package()
        boot=load('compact_rendered_cloud_boot',release/'kernel/run_experiment.py')
        old=json.loads(base64.b64decode(boot.INPUT_SETTINGS_B64))
        overlay=json.loads(base64.b64decode(boot.OVERLAY_B64))
        self.assertEqual(set(overlay),{'runner.py','data/exp_a/prompts/extraction_compact_v1.md','baseline/experiment_summary.json'})
        self.assertEqual(settings['dataset'],old['dataset'])
        cloud=Path(self.temp.name)/'cloud'
        boot.prepare(FROZEN.parent/'input-dataset/gold400_bundle.zip.bin',cloud,settings,old,overlay)
        runner.verify(cloud,settings,evaluation=True)
        boot.prepare(FROZEN.parent/'input-dataset/gold400_bundle.zip.bin',cloud,settings,old,overlay)
        bad=dict(overlay,**{'../escape.txt':base64.b64encode(b'bad').decode()})
        with self.assertRaises(ValueError):boot.prepare(FROZEN.parent/'input-dataset/gold400_bundle.zip.bin',cloud,settings,old,bad)

    def test_gold_separation_and_missing_prediction_fail_closed(self):
        runner,settings,_=self.package()
        (self.root/'evaluation_only/human_gold.jsonl').write_text('unreadable gold',encoding='utf-8')
        runner.verify(self.root,settings)
        with self.assertRaises(ValueError):runner.verify(self.root,settings,evaluation=True)
        with self.assertRaises(FileNotFoundError):runner.evaluate(self.root,settings)
        self.assertFalse((self.root/'results/prediction_manifest.json').exists())
        (self.root/'model_inputs/papers.jsonl').write_text('changed',encoding='utf-8')
        with self.assertRaises(ValueError):runner.verify(self.root,settings)

    def test_offline_all400_scoring_and_actual_one_call_cost(self):
        from unittest.mock import patch
        runner,settings,_=self.package()
        shared,papers,_,_=runner.verify(self.root,settings)
        for paper in papers:
            pid=paper['paper_id'];selection=dict(paper_id=pid,**{f:[] for f in shared.FACETS})
            record=dict(paper_id=pid,arm=runner.ARM,source_sha256=runner.digest(paper),facets=selection,
                audit=dict(attempts_used=1,attempt_scores=[dict(applied_output=json.dumps(selection),validation_errors=['empty'])]),
                call_trace=[dict(inherited=False,usage=dict(output_tokens=1))],new_cost=dict(calls=1),protected_items_changed=0,
                fallback_used=True,usage=dict(input_tokens=1,output_tokens=1),generation_seconds=1)
            shared.save_record(self.root/f'results/{runner.ARM}/records/{pid}.json',record,settings['signature'])
        with patch.object(runner,'load_shared',return_value=shared),patch.object(shared.evaluator,'encode_labels',side_effect=lambda root,labels:({x:[0.] for x in labels},dict(test_only=True))):
            result=runner.evaluate(self.root,settings)
        self.assertEqual(result['paper_count'],400)
        self.assertEqual(result['excluded_papers'],0)
        self.assertEqual(result['fresh_calls'],400)
        self.assertEqual(result['inherited_calls'],0)
        self.assertEqual(len(result['table']),5)
        self.assertEqual(result['table'][-1]['fn'],3346)
        manifest=json.loads((self.root/'results/prediction_manifest.json').read_text())
        self.assertEqual(len(manifest['records']),400)
        path=self.root/f'results/{runner.ARM}/records/{papers[0]["paper_id"]}.json'
        raw=json.loads(path.read_text());raw['record']['facets']['method']=['tampered'];path.write_text(json.dumps(raw))
        with self.assertRaises(ValueError):runner.load_result(shared,self.root,settings,papers[0])

if __name__=='__main__':unittest.main()
