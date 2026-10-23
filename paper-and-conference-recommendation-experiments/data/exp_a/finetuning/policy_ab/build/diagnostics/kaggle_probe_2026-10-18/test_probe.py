"""Checks for the bounded Kaggle diagnostic, without loading 8B weights."""
import importlib.util
import json
from pathlib import Path
import unittest
import zipfile

HERE = Path(__file__).resolve().parent


class ProbeTests(unittest.TestCase):
    def setUp(self):
        path = HERE / 'probe.py'
        self.assertTrue(path.is_file(), 'Kaggle diagnostic runner is missing')
        spec = importlib.util.spec_from_file_location('probe_under_test', path)
        self.probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.probe)

    def test_duplicate_item_stops_inside_an_unfinished_array(self):
        item = {'concept': 'ORBIT', 'evidence_ids': ['A0']}
        raw = '{"paper_id":"P000001","contribution":[' + ','.join(json.dumps(item) for _ in range(2)) + ','
        self.assertEqual(self.probe.duplicate_item(raw), {'facet': 'contribution', 'count': 2})

    def test_identical_items_in_different_facets_are_allowed(self):
        item = {'concept': 'ORBIT', 'evidence_ids': ['A0']}
        raw = json.dumps({'paper_id': 'P000001', 'method': [item], 'contribution': [item]})
        self.assertIsNone(self.probe.duplicate_item(raw))

    def test_escaped_json_inside_a_concept_does_not_create_fake_items(self):
        item = {'concept': 'literal "contribution":[{"concept":"ORBIT"}]', 'evidence_ids': ['A0']}
        raw = json.dumps({'paper_id': 'P000001', 'contribution': [item]})
        self.assertIsNone(self.probe.duplicate_item(raw))

    def test_incomplete_and_invalid_prefixes_do_not_raise(self):
        for raw in ('', '{', '{"contribution":[{"concept":"unfinished', 'not JSON'):
            self.assertIsNone(self.probe.duplicate_item(raw))

    def test_guard_detects_actual_cloud_loop_and_allows_normal_cloud_draft(self):
        records = HERE.parent / 'timeout_v1/policy_ab/results/new_v2_2/records'
        for pid in ('P000962', 'P001892'):
            record = json.loads((records / (pid + '.json')).read_text(encoding='utf-8'))['record']
            self.assertEqual(self.probe.duplicate_item(record['audit']['attempts'][0]['raw_output'])['facet'], 'contribution')
        normal = json.loads((records / 'P000151.json').read_text(encoding='utf-8'))['record']
        self.assertIsNone(self.probe.duplicate_item(normal['audit']['attempts'][0]['raw_output']))

    def test_actual_generate_obeys_per_call_time_guard(self):
        import torch
        from transformers import Qwen3Config, Qwen3ForCausalLM, StoppingCriteriaList
        model = Qwen3ForCausalLM(Qwen3Config(vocab_size=32, hidden_size=16,
            intermediate_size=32, num_hidden_layers=1, num_attention_heads=2,
            num_key_value_heads=1, head_dim=8, eos_token_id=None, pad_token_id=0)).eval()
        guard = self.probe.BudgetStop(None, 2, seconds=0)
        with torch.inference_mode():
            result = model.generate(torch.tensor([[1, 2]]), max_new_tokens=8,
                do_sample=False, stopping_criteria=StoppingCriteriaList([guard]))
        self.assertEqual(result.shape[-1], 3)
        self.assertEqual(guard.reason, 'time_budget')

    def test_first_messages_match_frozen_cloud_input_token_counts(self):
        from transformers import AutoTokenizer
        root = HERE.parents[6]
        runner = self.probe.get_runner(root)
        tokenizer = AutoTokenizer.from_pretrained(root / 'data/exp_a/finetuning/adapter-dataset', local_files_only=True)
        build = root / 'data/exp_a/finetuning/policy_ab/build'
        papers = {p['paper_id']: p for p in map(json.loads, (build / 'source_papers.jsonl').read_text(encoding='utf-8').splitlines())}
        with zipfile.ZipFile(build / 'input-dataset/policy_ab_bundle.zip.bin') as archive:
            for policy in self.probe.POLICIES:
                instruction = archive.read('instruction_old.txt' if policy == 'old_v3_7' else 'instruction_new.txt').decode('utf-8').replace('\r\n', '\n')
                for pid in self.probe.PAPERS:
                    messages = self.probe.first_messages(runner, papers[pid], instruction, policy)
                    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
                    record = json.loads((HERE.parent / f'timeout_v1/policy_ab/results/{policy}/records/{pid}.json').read_text(encoding='utf-8'))['record']
                    attempts = record['audit'].get('attempts', record['audit'].get('attempt_scores'))
                    self.assertEqual(len(tokenizer(text)['input_ids']), attempts[0]['usage']['input_tokens'])

    def test_original_runner_can_assess_probe_outputs(self):
        root = HERE.parents[6]
        runner = self.probe.get_runner(root)
        papers = {p['paper_id']: p for p in map(json.loads, (root / 'data/exp_a/finetuning/policy_ab/build/source_papers.jsonl').read_text(encoding='utf-8').splitlines())}
        record = json.loads((HERE.parent / 'timeout_v1/policy_ab/results/old_v3_7/records/P000962.json').read_text(encoding='utf-8'))['record']
        _, _, assessment, _ = runner.shared.v3.assess_attempt(record['audit']['attempt_scores'][0]['raw_output'], papers['P000962'], '3.1', prompt_version='3.7', dataset_resource_filter=True)
        self.assertTrue(assessment['schema_valid'])


if __name__ == '__main__':
    unittest.main()
