"""CPU checks for the Qwen14B-only training release."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))


class PlacementTests(unittest.TestCase):
    def test_every_layer_is_placed_and_large_matrices_are_separated(self):
        path = HERE/'dual_gpu.py'
        self.assertTrue(path.is_file(), 'Qwen14B dual-GPU placement is missing')
        spec = importlib.util.spec_from_file_location('qwen14b_dual_gpu', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        placement = module.device_map()
        self.assertEqual(placement['model.embed_tokens'], 0)
        self.assertEqual(placement['lm_head'], 1)
        self.assertEqual([placement[f'model.layers.{i}'] for i in range(40)], [0]*20+[1]*20)
        self.assertEqual(set(placement.values()), {0, 1})


class ReleaseTests(unittest.TestCase):
    def test_release_uses_two_gpus_and_smoke_gates_full_training(self):
        path = HERE/'prepare_dual_gpu.py'
        self.assertTrue(path.is_file(), 'Dual-GPU release builder is missing')
        spec = importlib.util.spec_from_file_location('qwen14b_builder', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        import tempfile
        scratch = HERE/'.test-tmp'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            self.assertTrue(Path(tmp).resolve().is_relative_to(scratch.resolve()))
            files, code = module.build(Path(tmp))
            import hashlib
            import json
            manifest = json.loads((Path(tmp)/'build_manifest.json').read_text())
            self.assertEqual(hashlib.sha256((Path(tmp)/'kernel/run_qwen14b.py').read_bytes()).hexdigest(), manifest['code_sha256'])
            compile(code, 'bootstrap', 'exec')
            for name, data in files.items():
                if name.endswith('.py'):
                    compile(data, name, 'exec')
            runtime = files['runtime.py'].decode()
            self.assertLess(runtime.index("'--smoke'"), runtime.index("'--smoke-reload'"))
            self.assertLess(runtime.index("'--smoke-reload'"), runtime.index("'--train', gpu='0,1'"))
            self.assertIn("from dual_gpu import", files['train.py'].decode())
            self.assertNotIn("device_map={'': 0}", files['train.py'].decode())
            self.assertIn("'dual_gpu.py', 'smoke.py'", code)
            # Bootstrap's tokenizer preflight loads train.py by file path, before runtime sys.path setup.
            import subprocess
            trainer_path = Path(tmp)/'preflight_train.py'
            trainer_path.write_bytes(files['train.py'])
            process = subprocess.run([sys.executable, '-I', '-c',
                'import importlib.util,sys; s=importlib.util.spec_from_file_location("preflight",sys.argv[1]); '
                'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); assert callable(m.encode_example)',
                str(trainer_path)], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            import json
            root = Path(tmp)/'Qwen14B'
            state, adapter = root/'smoke_state', root/'smoke_adapter'
            state.mkdir(parents=True)
            adapter.mkdir()
            (state/'run_manifest.json').write_text(json.dumps(dict(status='running', signature='test')))
            (adapter/'partial.bin').write_bytes(b'partial')
            namespace = dict(__name__='runtime_recovery_test')
            exec(files['runtime.py'], namespace)
            trainer = dict(__name__='trainer_recovery_test')
            exec(files['train.py'], trainer)
            namespace['recover_run_directory'](root, trainer['check_run_directory'], state, 'test', adapter)
            self.assertTrue((root/'smoke_state.interrupted-1/run_manifest.json').is_file())
            self.assertTrue((root/'smoke_adapter.interrupted-1/partial.bin').is_file())


class LossTests(unittest.TestCase):
    def test_completion_loss_matches_full_causal_loss_and_gradient(self):
        import torch
        from transformers import Qwen3Config, Qwen3ForCausalLM
        from dual_gpu import completion_loss
        torch.manual_seed(42)
        model = Qwen3ForCausalLM(Qwen3Config(vocab_size=32, hidden_size=16,
            intermediate_size=32, num_hidden_layers=2, num_attention_heads=2,
            num_key_value_heads=1, head_dim=8, attention_dropout=0.0)).eval()
        ids = torch.tensor([[1, 2, 3, 4, 5], [6, 7, 8, 0, 0]])
        labels = torch.tensor([[-100, -100, 3, 4, 5], [-100, 7, 8, -100, -100]])
        inputs = dict(input_ids=ids, attention_mask=(ids != 0).long(), labels=labels)
        reference = model(**inputs, use_cache=False).loss
        reference.backward()
        gradient = model.lm_head.weight.grad.clone()
        model.zero_grad()
        result = completion_loss(model, inputs)
        self.assertTrue(torch.allclose(result, reference, atol=1e-6))
        result.backward()
        self.assertTrue(torch.allclose(model.lm_head.weight.grad, gradient, atol=1e-6))
        count = (labels[:, 1:] != -100).sum()
        self.assertTrue(torch.allclose(completion_loss(model, inputs, num_items_in_batch=count), reference, atol=1e-6))
        with self.assertRaisesRegex(ValueError, 'no supervised'):
            completion_loss(model, dict(inputs, labels=torch.full_like(labels, -100)))

    def test_smoke_covers_longest_context_and_longest_completion(self):
        from dual_gpu import smoke_examples
        rows = [dict(input_ids=list(range(10)), labels=[-100]*9+[1]),
                dict(input_ids=list(range(5)), labels=[-100, 1, 2, 3, 4])]
        sampled = smoke_examples(rows, 8)
        self.assertEqual(len(sampled), 8)
        self.assertIs(sampled[0], rows[0])
        self.assertIs(sampled[1], rows[1])

    def test_labels_and_normalization_can_start_on_cpu_with_gpu_logits(self):
        import torch
        if not torch.cuda.is_available():
            self.skipTest('CUDA unavailable')
        from transformers import Qwen3Config, Qwen3ForCausalLM
        from dual_gpu import completion_loss
        model = Qwen3ForCausalLM(Qwen3Config(vocab_size=32, hidden_size=16,
            intermediate_size=32, num_hidden_layers=2, num_attention_heads=2,
            num_key_value_heads=1, head_dim=8)).cuda().eval()
        ids = torch.tensor([[1, 2, 3, 4]], device='cuda:0')
        labels = torch.tensor([[-100, -100, 3, 4]])
        expected = model(input_ids=ids, labels=labels.cuda(), use_cache=False).loss
        actual = completion_loss(model, dict(input_ids=ids, labels=labels),
                                 num_items_in_batch=(labels[:, 1:] != -100).sum())
        self.assertTrue(torch.allclose(actual, expected, atol=1e-6))
        actual.backward()
        self.assertTrue(torch.isfinite(model.lm_head.weight.grad).all())


if __name__ == '__main__':
    unittest.main(verbosity=2)
