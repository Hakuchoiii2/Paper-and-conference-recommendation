"""Exercise both inference arms, reference isolation and the unchanged scorer without a GPU."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('v2_evaluation_test',ROOT/'data/exp_a/finetuning/v2/evaluation.py')
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'tmp')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.adapter = self.root/'adapter';self.adapter.mkdir()
        self.papers = [dict(paper_id=f'P{100000+i:06}',title='Orbit',abstract='Orbit retrieves documents.') for i in range(100)]
        refs = [dict(paper_id=p['paper_id'],facets={f:['Orbit'] if f == 'method' else [] for f in evaluation.shared.FACETS},
                     provenance='REFERENCE_ONLY_SECRET') for p in self.papers]
        payloads = {'model_inputs/test_papers.jsonl': ''.join(json.dumps(p)+'\n' for p in self.papers),
                    'evaluation_only/test_references.jsonl': ''.join(json.dumps(r)+'\n' for r in refs),
                    'instruction.txt': 'Frozen extraction policy'}
        for name,value in payloads.items():
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(value,encoding='utf-8')
        weights=self.adapter/'adapter_model.safetensors';weights.write_bytes(b'test-only fake adapter')
        metadata=dict(status='complete',best_checkpoint='checkpoint-118',base_model='test-model',base_revision='rev',
                      files={'adapter_model.safetensors':evaluation.sha256(weights)})
        evaluation.write_json(self.adapter/'training_metadata.json',metadata)
        self.settings=dict(version='exp_a_qlora_v2_test_1',generation=evaluation.GENERATION,
            model=dict(model='test-model',revision='rev'),test_ids=[p['paper_id'] for p in self.papers],
            train_dev_ids=['P000001'],adapter_metadata_sha256=evaluation.sha256(self.adapter/'training_metadata.json'),
            adapter_sha256=evaluation.sha256(weights),files={'instruction.txt':evaluation.sha256(self.root/'instruction.txt')},
            test_files={name:evaluation.sha256(self.root/name) for name in payloads if name!='instruction.txt'})
        self.sign()

    def sign(self):
        self.settings['signature']=evaluation.shared.digest({k:v for k,v in self.settings.items() if k!='signature'})

    def test_rejects_overlap_and_changed_payload(self):
        self.settings['train_dev_ids']=[self.papers[0]['paper_id']];self.sign()
        with self.assertRaisesRegex(ValueError,'overlaps'):
            evaluation.verify(self.root,self.settings)
        self.settings['train_dev_ids']=[];self.sign()
        (self.root/'instruction.txt').write_text('Changed',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'payload'):
            evaluation.verify(self.root,self.settings)

    def test_rejects_adapter_and_record_tampering(self):
        (self.adapter/'adapter_model.safetensors').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'adapter file'):
            evaluation.verify_adapter(self.adapter,self.settings)
        path=self.root/'results/base/records/P100000.json'
        evaluation.shared.save_record(path,{'paper_id':'wrong'},self.settings['signature'])
        with self.assertRaises((ValueError,KeyError)):
            evaluation.load_record(self.root,self.settings,'base','P100000')

    def test_two_arms_review_without_references_and_score_all_100(self):
        calls=[]
        def generate(messages,seed):
            self.assertNotIn('REFERENCE_ONLY_SECRET',json.dumps(messages))
            self.assertEqual(messages[0]['content'],'Frozen extraction policy\nReturn JSON only. Schema: '
                             +json.dumps(evaluation.runner.multi.SCHEMA,separators=(',',':')))
            source=json.loads(messages[1]['content']);pid=source['paper_id']
            calls.append((pid,len(messages),seed))
            value=dict(paper_id=pid,**{f:[] for f in evaluation.shared.FACETS})
            value['method']=[dict(concept='Orbit',evidence_ids=['A0'])]
            return json.dumps(value),dict(usage=dict(input_tokens=10,output_tokens=5),generation_seconds=0.1,
                                          stop_reason='json_complete',bounded_stop=False)
        with redirect_stdout(io.StringIO()):
            for arm in evaluation.ARMS:
                evaluation.worker(self.root,self.settings,self.adapter,arm,generate=generate,
                                  runtime=dict(adapter_enabled=arm=='qlora_v2'))
            result=evaluation.evaluate(self.root,self.settings,vectors={'Orbit':[1.,0.]},embedding={'test':True})
        self.assertEqual(len(calls),400)
        self.assertEqual(sum(size==4 for _,size,_ in calls),200)
        self.assertEqual([r['micro_f1'] for r in result['table']],[1.,1.])
        # An unsuccessful paper is kept in the cohort and contributes a false negative.
        row=evaluation.load_record(self.root,self.settings,'base','P100000')
        row['facets']['method']=[];row['fallback_used']=True
        evaluation.shared.save_record(self.root/'results/base/records/P100000.json',row,self.settings['signature'])
        with redirect_stdout(io.StringIO()):
            result=evaluation.evaluate(self.root,self.settings,vectors={'Orbit':[1.,0.]},embedding={'test':True})
        self.assertAlmostEqual(result['table'][0]['recall'],0.99)
        self.assertEqual(result['table'][0]['fallback_count'],1)
        self.assertEqual(result['paper_count'],100)


if __name__=='__main__':
    unittest.main()
