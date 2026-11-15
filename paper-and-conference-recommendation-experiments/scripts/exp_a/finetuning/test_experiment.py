"""Protect the adapter identity and reference-free prediction boundary."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class ExperimentChecks(unittest.TestCase):
    def module(self):
        path = ROOT/'data/exp_a/finetuning/experiment.py'
        self.assertTrue(path.exists(), 'QLoRA experiment runner missing')
        spec = importlib.util.spec_from_file_location('qlora_experiment', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_predictions_never_read_test_reference(self):
        m = self.module()
        paper = dict(paper_id='P000002',title='Ranking',abstract='We introduce RankNet for ranking.')
        response = dict(paper_id='P000002', **{f:[] for f in m.shared.FACETS})
        response['method'] = [dict(concept='RankNet',evidence_id='A0')]
        response['contribution'] = [dict(concept='RankNet',evidence_id='A0')]
        requests = []
        def generate(messages, seed):
            requests.append(messages)
            return json.dumps(response),dict(usage=dict(input_tokens=10,output_tokens=5),generation_seconds=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = dict(experiment_signature='fixture',test_ids=['P000002'],
                generation=dict(seed=42,max_attempts=3,max_new_tokens=2048,prompt_version='3.7',dataset_resource_filter=True))
            (root/'model_inputs').mkdir()
            m.shared.base.write_jsonl(root/'model_inputs/test_papers.jsonl',[paper])
            (root/'instruction.txt').write_text('Extract source concepts.',encoding='utf-8')
            (root/'evaluation_only').mkdir()
            (root/'evaluation_only/test_references.jsonl').write_text('INVALID REFERENCE MUST NOT BE READ',encoding='utf-8')
            m.predict(root,settings,'original',generate=generate,runtime={})
            record = m.shared.load_record(root/'results/original/records/P000002.json','fixture')
            self.assertEqual(record['facets']['method'],['RankNet'])
            self.assertEqual(record['facets']['contribution'],['RankNet'])
            self.assertEqual(len(requests),2)
            self.assertNotIn('INVALID REFERENCE',json.dumps(requests))

    def test_changed_adapter_file_is_rejected(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'adapter_model.safetensors').write_bytes(b'original')
            m.shared.base.write_json(root/'adapter_manifest.json',dict(status='complete',base_model='Qwen/Qwen3-8B',
                base_revision='pinned',experiment_signature='fixture',files={'adapter_model.safetensors':m.shared.base.sha256(root/'adapter_model.safetensors')}))
            settings=dict(experiment_signature='fixture',model=dict(model='Qwen/Qwen3-8B',revision='pinned'))
            m.verify_adapter(root,settings)
            (root/'adapter_model.safetensors').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'checksum'):
                m.verify_adapter(root,settings)

    def test_adapter_from_different_base_revision_is_rejected(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            m.shared.base.write_json(root/'adapter_manifest.json',dict(status='complete',base_model='Qwen/Qwen3-8B',
                base_revision='wrong',experiment_signature='fixture',files={}))
            with self.assertRaisesRegex(ValueError,'base model'):
                m.verify_adapter(root,dict(experiment_signature='fixture',model=dict(model='Qwen/Qwen3-8B',revision='pinned')))


if __name__ == '__main__':
    unittest.main()
