import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]


def module(name):
    path = HERE / (name + '.py')
    spec = importlib.util.spec_from_file_location('compare_test_' + name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class ChatTests(unittest.TestCase):
    def test_gemma_folds_system_into_first_user_without_changing_followup(self):
        m = module('compat')
        messages = [dict(role='system', content='Policy'), dict(role='user', content='Source'),
                    dict(role='assistant', content='Draft'), dict(role='user', content='Review')]
        formatted = m.format_messages(messages, 'google/gemma-2-9b-it')
        self.assertEqual(formatted, [dict(role='user', content='Policy\n\nSource'),
                                    dict(role='assistant', content='Draft'), dict(role='user', content='Review')])
        self.assertEqual(messages[0]['role'], 'system')
        self.assertEqual(m.format_messages(messages, 'meta-llama/Llama-3.1-8B-Instruct'), messages)

    def test_completion_supervises_end_of_turn_and_masks_prompt(self):
        m = module('compat')
        # Offline tokenizer boundary double: Gemma's turn marker is not its EOS.
        class Tokenizer:
            name_or_path = 'google/gemma-2-9b-it'
            eos_token_id = 1
            unk_token_id = 0
            vocab_calls = 0
            def get_vocab(self):
                self.vocab_calls += 1
                return {'<end_of_turn>': 9}
            def apply_chat_template(self, messages, **kwargs):
                assert messages[0]['role'] == 'user'
                return 'PROMPT' if kwargs['add_generation_prompt'] else 'PROMPT{}<end_of_turn>\n'
            def __call__(self, text, **kwargs):
                return {'input_ids': [4, 5] if text == 'PROMPT' else [7, 8, 9, 10]}
            def decode(self, ids, **kwargs):
                return '\n' if ids == [10] else '{}'
        row = dict(paper_id='P000001', messages=[dict(role='system', content='Policy'),
                   dict(role='user', content='Source'), dict(role='assistant', content='{}')])
        tokenizer = Tokenizer()
        encoded = m.encode_example(tokenizer, row, 5)
        self.assertEqual(tokenizer.vocab_calls, 1, 'Vocabulary must be fetched once per example')
        self.assertEqual(encoded['input_ids'], [4, 5, 7, 8, 9])
        self.assertEqual(encoded['labels'], [-100, -100, 7, 8, 9])
        with self.assertRaisesRegex(ValueError, 'truncation'):
            m.encode_example(Tokenizer(), row, 4)


class ProgressTests(unittest.TestCase):
    def test_preflight_reports_start_intermediate_and_final_counts(self):
        from unittest.mock import Mock, patch
        boot = module('bootstrap')
        compat = Mock()
        compat.encode_example.return_value = dict(input_ids=[1, 2, 3], labels=[-100, 2, 3])
        rows = [dict(paper_id=f'P{i}') for i in range(26)]
        with patch.object(boot, 'log') as output:
            lengths = boot.encode_split(compat, object(), rows, 'Llama8B', 'train')
        self.assertEqual(lengths, dict(count=26, max_sequence=3, max_completion=2))
        self.assertEqual(compat.encode_example.call_count, 26)
        messages = [call.args[0] for call in output.call_args_list]
        for progress in ('0/26', '1/26', '25/26', '26/26'):
            self.assertTrue(any(progress in message for message in messages), messages)

    def test_progress_keeps_completion_budget_validation(self):
        from unittest.mock import Mock, patch
        boot = module('bootstrap')
        compat = Mock()
        compat.encode_example.return_value = dict(input_ids=[1]*2049, labels=[1]*2049)
        with patch.object(boot, 'log'), self.assertRaisesRegex(ValueError, 'generation budget'):
            boot.encode_split(compat, object(), [dict(paper_id='P1')], 'Llama8B', 'train')


class BatchTests(unittest.TestCase):
    def test_models_finish_and_publish_before_next_model_and_skip_verified_completed(self):
        m = module('batch')
        events = []
        with tempfile.TemporaryDirectory(dir=REPO/'.test-tmp') as tmp:
            root = Path(tmp)
            for name in ('Llama8B', 'Gemma9B'):
                (root/name).mkdir()
                (root/name/'settings.json').write_text(json.dumps({'signature': name}), encoding='utf-8')
            def execute(path):
                events.append(('run', path.name))
                (path/'results').mkdir(exist_ok=True)
                (path/'results/experiment_summary.json').write_text(json.dumps({'status': 'complete', 'signature': path.name}), encoding='utf-8')
            def publish(path):
                events.append(('save', path.name))
                m.publish_model(path)
            m.run_models(root, execute=execute, publish=publish)
            self.assertEqual(events, [('run', 'Llama8B'), ('save', 'Llama8B'), ('run', 'Gemma9B'), ('save', 'Gemma9B')])
            events.clear()
            m.run_models(root, execute=execute, publish=publish)
            self.assertEqual(events, [])
            (root/'Llama8B_completed.zip').unlink()
            m.run_models(root, execute=execute, publish=publish)
            self.assertEqual(events, [('save', 'Llama8B')])
            (root/'Llama8B/results/experiment_summary.json').write_text('{}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                m.run_models(root, execute=execute, publish=publish)

    def test_failure_stops_before_next_model_and_keeps_first_model_files(self):
        m = module('batch')
        with tempfile.TemporaryDirectory(dir=REPO/'.test-tmp') as tmp:
            root = Path(tmp)
            for name in ('Llama8B', 'Gemma9B'):
                (root/name).mkdir()
                (root/name/'settings.json').write_text(json.dumps({'signature': name}), encoding='utf-8')
            events = []
            def fail(path):
                events.append(path.name)
                (path/'checkpoint.txt').write_text('saved', encoding='utf-8')
                raise RuntimeError('worker failed')
            with self.assertRaisesRegex(RuntimeError, 'worker failed'):
                m.run_models(root, execute=fail, publish=lambda _: self.fail('Published failure'))
            self.assertEqual(events, ['Llama8B'])
            self.assertTrue((root/'Llama8B/checkpoint.txt').exists())

    def test_zip_failure_does_not_mark_model_complete(self):
        from unittest.mock import patch
        m = module('batch')
        with tempfile.TemporaryDirectory(dir=REPO/'.test-tmp') as tmp:
            root = Path(tmp)/'Llama8B'
            root.mkdir()
            m.write(root/'settings.json', dict(signature='run'))
            m.write(root/'results/experiment_summary.json', dict(status='complete', signature='run'))
            with patch.object(m.zipfile, 'ZipFile', side_effect=OSError('disk failure')):
                with self.assertRaisesRegex(OSError, 'disk failure'):
                    m.publish_model(root)
            self.assertFalse((root/'complete.json').exists())


class RecoveryTests(unittest.TestCase):
    def test_partial_first_checkpoint_is_preserved_and_training_can_restart(self):
        run = module('model_runtime')
        helper = run.load('recovery_trainer', REPO/'data/exp_a/final/runtime/train.py')
        with tempfile.TemporaryDirectory(dir=REPO/'.test-tmp') as tmp:
            root = Path(tmp)
            state = root/'train_state'
            state.mkdir()
            (state/'run_manifest.json').write_text(json.dumps(dict(signature={'model':'same'}, status='running')), encoding='utf-8')
            (state/'checkpoint-35').mkdir()
            (state/'checkpoint-35/adapter_model.safetensors').write_bytes(b'partial')
            run.recover_run_directory(root, helper.check_run_directory, state, {'model':'same'}, root/'provisional_adapter')
            self.assertFalse(state.exists())
            self.assertEqual((root/'train_state.interrupted-1/checkpoint-35/adapter_model.safetensors').read_bytes(), b'partial')

    def test_partial_export_resumes_verified_checkpoint_and_wrong_signature_never_moves(self):
        run = module('model_runtime')
        helper = run.load('recovery_trainer', REPO/'data/exp_a/final/runtime/train.py')
        with tempfile.TemporaryDirectory(dir=REPO/'.test-tmp') as tmp:
            root = Path(tmp)
            state = root/'train_state'
            checkpoint = state/'checkpoint-105'
            checkpoint.mkdir(parents=True)
            signature = {'model':'same'}
            helper.write_json(state/'run_manifest.json', dict(signature=signature, status='running'))
            for name in helper.RESUME_FILES:
                (checkpoint/name).write_bytes(b'checkpoint')
            helper.write_json(checkpoint/'checkpoint_manifest.json', dict(signature=signature, files=helper.file_hashes(checkpoint)))
            adapter = root/'provisional_adapter'
            adapter.mkdir()
            (adapter/'adapter_config.json').write_text('{}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'signature'):
                run.recover_run_directory(root, helper.check_run_directory, state, {'model':'different'}, adapter, checkpoint)
            self.assertTrue(adapter.exists())
            run.recover_run_directory(root, helper.check_run_directory, state, signature, adapter, checkpoint)
            self.assertTrue(checkpoint.exists())
            self.assertFalse(adapter.exists())
            self.assertTrue((root/'provisional_adapter.interrupted-1/adapter_config.json').exists())


class BundleTests(unittest.TestCase):
    def test_inline_token_is_exported_for_training_workers_without_secret_lookup(self):
        from unittest.mock import patch
        boot = module('bootstrap')
        boot.HF_TOKEN = 'test-placeholder-not-a-real-token'
        with patch.dict(boot.os.environ, {'HF_TOKEN':'environment-placeholder'}):
            self.assertEqual(boot.hf_token(), 'test-placeholder-not-a-real-token')
            self.assertEqual(boot.os.environ['HF_TOKEN'], 'test-placeholder-not-a-real-token')

    def test_real_three_pass_workers_partition_papers_and_resume_without_labels(self):
        import re
        import zipfile
        prepare = module('prepare')
        boot = module('bootstrap')
        run = module('model_runtime')
        with tempfile.TemporaryDirectory(dir=REPO/'.test-tmp') as tmp:
            root = Path(tmp)
            build = prepare.build(root/'build')
            boot.extract(root/'build/input-dataset/llama_gemma_bundle.zip.bin', root/'run', build['bundle_sha256'])
            project = boot.prepare_model(root/'run', dict(key='Llama8B', model='meta-llama/Llama-3.1-8B-Instruct', revision='a'*40))
            old, compat = run.frozen(project)
            settings = old.read(project/'settings.json')
            papers = old.rows(project/'model_inputs/test.jsonl')[:2]
            settings['splits']['test'] = [p['paper_id'] for p in papers]
            (project/'model_inputs/test.jsonl').write_text(''.join(json.dumps(p)+'\n' for p in papers), encoding='utf-8')
            (project/'evaluation_only').rename(project/'hidden_references')
            adapter = project/'adapter'
            adapter.mkdir()
            (adapter/'adapter_model.safetensors').write_bytes(b'fake weights never loaded')
            calls = []
            def factory(config, install_attention):
                def decode(messages, seed):
                    text = '\n'.join(m['content'] for m in messages)
                    pid = re.search(r'"paper_id"\s*:\s*"(P\d+)"', text).group(1)
                    calls.append(pid)
                    facets = ('task','method') if 'ADDITIONS ONLY' in text else ('problem','task','method','dataset','contribution')
                    answer = dict(paper_id=pid, **{f:[] for f in facets})
                    return json.dumps(answer), dict(usage=dict(input_tokens=10, output_tokens=10), generation_seconds=.1, reached_token_limit=False)
                return decode, dict(model=config['model'])
            compat.load_generator = factory
            for index in (0,1):
                old.worker(project, settings, 'test', 'QLoRA-V-recall', adapter, index)
            work = project/'results/test/QLoRA-V-recall/records'
            self.assertEqual({p.stem for p in work.glob('*.json')}, {p['paper_id'] for p in papers})
            self.assertEqual(len(calls), 6)
            compat.load_generator = lambda *_: self.fail('Resume loaded a decoder')
            for index in (0,1):
                old.worker(project, settings, 'test', 'QLoRA-V-recall', adapter, index)

    def test_bundle_uses_frozen_split_and_preserves_current_qwen_results(self):
        m = module('prepare')
        with tempfile.TemporaryDirectory(dir=REPO/'.test-tmp') as tmp:
            output = Path(tmp)
            build = m.build(output)
            import zipfile
            with zipfile.ZipFile(output/'input-dataset/llama_gemma_bundle.zip.bin') as archive:
                settings = json.loads(archive.read('common/settings.template.json'))
                self.assertEqual({k:len(v) for k,v in settings['splits'].items()}, {'train':280, 'valid':60, 'test':60})
                self.assertNotIn('common/training_data/test.jsonl', archive.namelist())
                self.assertEqual(archive.read('Qwen8B/results/experiment_summary.json'),
                                 (REPO/'data/exp_a/final/results/Qwen8B/results/experiment_summary.json').read_bytes())
                manifest = json.loads(archive.read('bundle_manifest.json'))
                self.assertEqual(set(archive.namelist()), set(manifest['files'])|{'bundle_manifest.json'})
                self.assertEqual(build['models'], ['Llama8B', 'Gemma9B'])

    def test_extract_resumes_without_overwrite_and_rejects_tampering(self):
        m = module('prepare')
        boot = module('bootstrap')
        with tempfile.TemporaryDirectory(dir=REPO/'.test-tmp') as tmp:
            root = Path(tmp)
            build = m.build(root/'build')
            bundle = root/'build/input-dataset/llama_gemma_bundle.zip.bin'
            destination = root/'run'
            boot.extract(bundle, destination, build['bundle_sha256'])
            (destination/'Llama8B').mkdir()
            (destination/'Llama8B/progress.txt').write_text('checkpoint', encoding='utf-8')
            boot.extract(bundle, destination, build['bundle_sha256'])
            self.assertEqual((destination/'Llama8B/progress.txt').read_text(), 'checkpoint')
            (destination/'common/compat.py').write_text('tampered', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Changed'):
                boot.extract(bundle, destination, build['bundle_sha256'])

    def test_prepare_model_pins_revision_and_rejects_changed_resume(self):
        m = module('prepare')
        boot = module('bootstrap')
        with tempfile.TemporaryDirectory(dir=REPO/'.test-tmp') as tmp:
            root = Path(tmp)
            build = m.build(root/'build')
            destination = root/'run'
            boot.extract(root/'build/input-dataset/llama_gemma_bundle.zip.bin', destination, build['bundle_sha256'])
            item = dict(key='Gemma9B', model='google/gemma-2-9b-it', revision='a'*40)
            model = boot.prepare_model(destination, item)
            settings = json.loads((model/'settings.json').read_text(encoding='utf-8'))
            self.assertEqual(settings['training']['revision'], 'a'*40)
            self.assertEqual(settings['generation']['revision'], 'a'*40)
            self.assertEqual(settings['training']['epochs'], 3)
            run = module('model_runtime')
            old, _ = run.frozen(model)
            old.verify(model)
            boot.prepare_model(destination, item)
            with self.assertRaisesRegex(ValueError, 'identity'):
                boot.prepare_model(destination, dict(item, revision='b'*40))

    def test_selected_logit_loss_matches_native_llama_and_gemma_loss(self):
        import torch
        from transformers import LlamaConfig, LlamaForCausalLM, Gemma2Config, Gemma2ForCausalLM
        run = module('model_runtime')
        trainer = run.load('comparison_loss_test', REPO/'data/exp_a/final/runtime/train.py')
        for config_type, model_type in ((LlamaConfig, LlamaForCausalLM), (Gemma2Config, Gemma2ForCausalLM)):
            config = config_type(vocab_size=32, hidden_size=16, intermediate_size=32,
                num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=1,
                head_dim=8, max_position_embeddings=64, pad_token_id=0)
            config._attn_implementation = 'eager'
            model = model_type(config).eval()
            inputs = dict(input_ids=torch.tensor([[2,3,4,5,6]]),
                          labels=torch.tensor([[-100,-100,4,5,6]]), attention_mask=torch.ones(1,5,dtype=torch.long))
            expected = model(**inputs).loss
            actual = trainer.completion_loss(model, inputs)
            self.assertTrue(torch.allclose(actual, expected, atol=1e-6), config_type.__name__)


if __name__ == '__main__':
    unittest.main()
