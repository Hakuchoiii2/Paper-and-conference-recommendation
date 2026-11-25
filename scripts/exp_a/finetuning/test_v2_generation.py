"""Regressions for the two repetition patterns observed on Kaggle."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / 'data/exp_a/finetuning/v2/generation.py'
PROBE = ROOT / 'data/exp_a/finetuning/policy_ab/build/diagnostics/kaggle_probe_2026-10-18'


class TextTokenizer:
    eos_token_id = 0

    def decode(self, ids, **kwargs):
        return ''.join(chr(int(i)) for i in ids if int(i))


class V2GenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MODULE.is_file():
            cls.module = None
            return
        spec = importlib.util.spec_from_file_location('v2_generation_under_test', MODULE)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def setUp(self):
        self.assertIsNotNone(self.module, 'The bounded v2 generator is not implemented')

    def guard(self, text, seconds=90):
        import torch
        guard = self.module.GenerationGuard(TextTokenizer(), 1, seconds)
        stopped = guard(torch.tensor([[1] + [ord(c) for c in text]]), None)
        return guard, stopped

    def test_stops_at_first_document_with_escaped_quotes_and_braces(self):
        raw = json.dumps({'paper_id': 'P000001', 'method': [{'concept': 'a "quoted" } name'}]})
        guard, stopped = self.guard(raw)
        self.assertTrue(stopped)
        self.assertEqual(guard.reason, 'json_complete')
        self.assertEqual(self.module.json_prefix(raw + '\n' + raw), raw)

    def test_incomplete_and_non_object_outputs_do_not_count_as_complete(self):
        for raw in ('', '{', '{"method":[{"concept":"unfinished', '[]', 'not JSON'):
            guard, stopped = self.guard(raw)
            self.assertFalse(stopped)
            self.assertIsNone(guard.reason)

    def test_duplicate_concept_with_different_evidence_stops_unfinished_array(self):
        raw = '{"contribution":[{"concept":"ORBIT retrieval","evidence_ids":["A0"]},'
        raw += '{"concept":"orbit retrieval","evidence_ids":["A1"]},'
        guard, stopped = self.guard(raw)
        self.assertTrue(stopped)
        self.assertEqual(guard.reason, 'duplicate_concept')
        self.assertEqual(guard.duplicate['facet'], 'contribution')

    def test_cross_facet_reuse_and_json_inside_strings_are_allowed(self):
        item = {'concept': 'literal "contribution":[{"concept":"ORBIT"}]', 'evidence_ids': ['A0']}
        raw = json.dumps({'method': [item], 'contribution': [item]})[:-1]
        guard, stopped = self.guard(raw)
        self.assertFalse(stopped)
        self.assertIsNone(guard.duplicate)

    def test_time_limit_does_not_depend_on_parseable_output(self):
        guard, stopped = self.guard('not JSON', seconds=0)
        self.assertTrue(stopped)
        self.assertEqual(guard.reason, 'time_budget')

    def test_all_three_actual_cloud_failures_are_detected(self):
        for pid, expected in (('P000151', 'json_complete'), ('P000962', 'duplicate_concept'),
                              ('P001892', 'duplicate_concept')):
            path = PROBE / f'results_v1/policy_probe/results/adapter/new_v2_2/{pid}.json'
            raw = json.loads(path.read_text(encoding='utf-8'))['record']['raw_output']
            guard, stopped = self.guard(raw)
            self.assertTrue(stopped, pid)
            self.assertEqual(guard.reason, expected, pid)

    def test_sampling_options_reach_generate_and_raw_suffix_is_retained(self):
        import torch
        class Tokenizer(TextTokenizer):
            def apply_chat_template(self, messages, **kwargs):
                return 'source'
            def __call__(self, text, **kwargs):
                class Encoded(dict):
                    def to(self, device):
                        return self
                return Encoded(input_ids=torch.tensor([[1]]))
        class Model:
            device = 'cpu'
            config = type('Config', (), {'max_position_embeddings': 4096})()
            def generate(self, **kwargs):
                assert kwargs['do_sample'] is True
                assert (kwargs['temperature'], kwargs['top_p'], kwargs['top_k']) == (0.7, 0.8, 20)
                assert kwargs['use_cache'] is True
                return torch.tensor([[1] + [ord(c) for c in '{"ok":true}\n{"ok":true}']])
        generate = self.module.build_generator(Model(), Tokenizer(), {'do_sample': True})
        text, stats = generate([{'role': 'user', 'content': 'source'}], 42)
        self.assertEqual(text, '{"ok":true}')
        self.assertEqual(stats['raw_output_untrimmed'], '{"ok":true}\n{"ok":true}')
        self.assertGreater(stats['discarded_suffix_chars'], 0)
        self.assertEqual(stats['usage']['output_tokens'], 23)

    def test_invalid_generation_budgets_are_rejected_before_inference(self):
        for config in ({'max_new_tokens': 0}, {'seconds_per_call': -1}, {'do_sample': 'false'},
                       {'temperature': 0}, {'top_p': 2}, {'max_new_tokens': True}):
            with self.assertRaises(ValueError):
                self.module.build_generator(None, None, config)

    def test_real_transformers_generation_obeys_time_guard(self):
        import torch
        from transformers import Qwen3Config, Qwen3ForCausalLM, StoppingCriteriaList
        model = Qwen3ForCausalLM(Qwen3Config(vocab_size=32, hidden_size=16,
            intermediate_size=32, num_hidden_layers=1, num_attention_heads=2,
            num_key_value_heads=1, head_dim=8, eos_token_id=None, pad_token_id=0)).eval()
        guard = self.module.GenerationGuard(TextTokenizer(), 2, seconds=0)
        with torch.inference_mode():
            result = model.generate(torch.tensor([[1, 2]]), max_new_tokens=8,
                do_sample=False, stopping_criteria=StoppingCriteriaList([guard]))
        self.assertEqual(result.shape[-1], 3)
        self.assertEqual(guard.reason, 'time_budget')


if __name__ == '__main__':
    unittest.main()
