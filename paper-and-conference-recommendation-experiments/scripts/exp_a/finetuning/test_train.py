"""Offline tests: assistant-only labels, run integrity, and a tiny real LoRA update."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('finetuning_train', ROOT / 'data/exp_a/finetuning/train.py')
trainer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trainer)


def tokenizer_fixture():
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers
    from transformers import PreTrainedTokenizerFast
    alphabet = sorted(pre_tokenizers.ByteLevel.alphabet())
    vocabulary = {token: index for index, token in enumerate(['<|pad|>', '<|im_start|>', '<|im_end|>'] + alphabet)}
    backend = Tokenizer(models.BPE(vocab=vocabulary, merges=[]))
    backend.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    backend.decoder = decoders.ByteLevel()
    result = PreTrainedTokenizerFast(tokenizer_object=backend, pad_token='<|pad|>', eos_token='<|im_end|>',
                                    additional_special_tokens=['<|im_start|>'])
    # The Qwen3 non-thinking branch, exercised through the real Jinja tokenizer API.
    result.chat_template = """{% for message in messages %}{{ '<|im_start|>' + message.role + '\n' }}{% if message.role == 'assistant' and not enable_thinking %}{{ '<think>\n\n</think>\n\n' }}{% endif %}{{ message.content + '<|im_end|>\n' }}{% endfor %}{% if add_generation_prompt %}{{ '<|im_start|>assistant\n' }}{% if not enable_thinking %}{{ '<think>\n\n</think>\n\n' }}{% endif %}{% endif %}"""
    return result


def example(paper_id='P1', answer=None):
    return {'paper_id': paper_id, 'messages': [
        {'role': 'system', 'content': 'Return JSON only.'},
        {'role': 'user', 'content': 'Paper about methods.'},
        {'role': 'assistant', 'content': answer or json.dumps({'paper_id': paper_id, 'method': ['BERT']})}],
        'provenance': {'label_source': 'ai_generated_reference'}}


class CompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokenizer = tokenizer_fixture()

    def test_only_json_completion_and_eos_receive_labels(self):
        row = example()
        encoded = trainer.encode_example(self.tokenizer, row, 4096)
        supervised = [token for token in encoded['labels'] if token != -100]
        self.assertEqual(self.tokenizer.decode(supervised), row['messages'][-1]['content'] + '<|im_end|>')
        first = next(i for i, token in enumerate(encoded['labels']) if token != -100)
        prefix = self.tokenizer.decode(encoded['input_ids'][:first])
        self.assertTrue(prefix.endswith('<|im_start|>assistant\n<think>\n\n</think>\n\n'))
        self.assertIn('Return JSON only.', prefix)
        self.assertEqual(encoded['labels'][:first], [-100] * first)
        self.assertEqual(encoded['input_ids'][-1], self.tokenizer.eos_token_id)

    def test_overlong_examples_are_rejected_without_truncation(self):
        with self.assertRaisesRegex(ValueError, 'P1.*max_seq_length'):
            trainer.encode_example(self.tokenizer, example(), 20)

    def test_non_json_or_extra_assistant_turn_is_rejected(self):
        for row in (example(answer='not JSON'), example()):
            if row['messages'][-1]['content'] != 'not JSON':
                row['messages'].insert(1, {'role': 'assistant', 'content': '{}'})
            with self.subTest(row=row), self.assertRaises(ValueError):
                trainer.encode_example(self.tokenizer, row, 4096)

    def test_padding_is_masked_even_when_padding_and_eos_share_an_id(self):
        import torch
        a = {'input_ids': [10, 11, 2], 'attention_mask': [1, 1, 1], 'labels': [-100, 11, 2]}
        b = {'input_ids': [12, 2], 'attention_mask': [1, 1], 'labels': [-100, 2]}
        batch = trainer.CompletionCollator(2)([a, b])
        self.assertTrue(torch.equal(batch['input_ids'], torch.tensor([[10, 11, 2], [12, 2, 2]])))
        self.assertEqual(batch['labels'].tolist(), [[-100, 11, 2], [-100, 2, -100]])
        self.assertEqual(batch['attention_mask'].tolist(), [[1, 1, 1], [1, 1, 0]])

    def test_jsonl_duplicate_ids_and_train_dev_overlap_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            path = Path(directory) / 'train.jsonl'
            path.write_text('\n'.join(json.dumps(example()) for _ in range(2)), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Duplicate paper_id'):
                trainer.read_examples(path)
        with self.assertRaisesRegex(ValueError, 'overlap'):
            trainer.validate_split_ids([example()], [example()])


class RunIntegrityTests(unittest.TestCase):
    def test_actual_trainer_accumulates_completion_loss_and_restores_best_adapter(self):
        import math
        from transformers import Qwen3Config,Qwen3ForCausalLM,TrainingArguments
        from peft import LoraConfig,get_peft_model
        tokenizer=tokenizer_fixture()
        model=get_peft_model(Qwen3ForCausalLM(Qwen3Config(vocab_size=len(tokenizer),hidden_size=16,
            intermediate_size=32,num_hidden_layers=1,num_attention_heads=2,num_key_value_heads=1,
            head_dim=8,max_position_embeddings=1024,use_cache=False)),
            LoraConfig(r=2,lora_alpha=4,lora_dropout=0,target_modules='all-linear',task_type='CAUSAL_LM'))
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            args=TrainingArguments(output_dir=directory,use_cpu=True,per_device_train_batch_size=1,
                per_device_eval_batch_size=1,num_train_epochs=1,gradient_accumulation_steps=2,
                save_strategy='epoch',eval_strategy='epoch',load_best_model_at_end=True,
                metric_for_best_model='eval_loss',greater_is_better=False,report_to=[],disable_tqdm=True,
                optim='adamw_torch',learning_rate=1e-3,dataloader_pin_memory=False)
            runner=trainer.make_completion_trainer(model=model,args=args,
                train_dataset=[trainer.encode_example(tokenizer,example(pid),1024) for pid in ('P1','P2')],
                eval_dataset=[trainer.encode_example(tokenizer,example('P3'),1024)],
                data_collator=trainer.CompletionCollator(tokenizer.pad_token_id),processing_class=tokenizer)
            result=runner.train()
            self.assertEqual(runner.state.global_step,1)
            self.assertTrue(math.isfinite(result.training_loss))
            self.assertTrue(math.isfinite(runner.state.best_metric))
            self.assertTrue((Path(runner.state.best_model_checkpoint)/'adapter_model.safetensors').is_file())

    def test_selected_completion_logits_match_full_masked_loss_and_lora_gradients(self):
        import torch
        from transformers import Qwen3Config, Qwen3ForCausalLM
        from peft import LoraConfig, get_peft_model
        torch.manual_seed(7)
        model=Qwen3ForCausalLM(Qwen3Config(vocab_size=64,hidden_size=32,intermediate_size=64,
            num_hidden_layers=1,num_attention_heads=2,num_key_value_heads=1,head_dim=16,
            max_position_embeddings=64,tie_word_embeddings=False,use_cache=False))
        model=get_peft_model(model,LoraConfig(r=2,lora_alpha=4,lora_dropout=0,
            target_modules='all-linear',task_type='CAUSAL_LM'))
        with torch.no_grad():
            for name,parameter in model.named_parameters():
                if 'lora_B' in name:
                    parameter.normal_(0,.01)
        model.eval()
        ids=torch.randint(1,64,(2,12))
        labels=ids.clone()
        labels[0,:7]=-100
        labels[1,:5]=-100
        labels[1,10:]=-100
        mask=torch.ones_like(ids)
        mask[1,10:]=0
        batch=dict(input_ids=ids,attention_mask=mask,labels=labels)
        baseline=model(**batch).loss
        baseline.backward()
        gradients={name:p.grad.clone() for name,p in model.named_parameters() if 'lora_' in name}
        model.zero_grad(set_to_none=True)
        loss,outputs=trainer.completion_loss(model,batch,return_outputs=True)
        loss.backward()
        self.assertTrue(torch.allclose(loss,baseline,rtol=1e-6,atol=1e-7))
        self.assertLess(outputs.logits.shape[1],ids.shape[1])
        for name,parameter in model.named_parameters():
            if name in gradients:
                self.assertTrue(torch.allclose(parameter.grad,gradients[name],rtol=1e-5,atol=1e-7),name)
        normalized=trainer.completion_loss(model,batch,num_items_in_batch=2*(labels!=-100).sum())
        self.assertTrue(torch.allclose(normalized,baseline/2,rtol=1e-6,atol=1e-7))

    def test_incompatible_or_unmarked_nonempty_run_cannot_be_reused(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            state = Path(directory)
            (state / 'unrelated.txt').write_text('do not overwrite', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'unmarked'):
                trainer.check_run_directory(state, {'model': 'new'}, state / 'adapter')
            (state / 'unrelated.txt').unlink()
            trainer.write_json(state / 'run_manifest.json', {'signature': {'model': 'old'}, 'status': 'running'})
            with self.assertRaisesRegex(ValueError, 'signature differs'):
                trainer.check_run_directory(state, {'model': 'new'}, state / 'adapter')

    def test_checkpoint_resume_requires_matching_signature_and_intact_files(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            state = Path(directory)
            signature = {'model': 'tiny', 'train_sha256': 'abc'}
            checkpoint = state / 'checkpoint-1'
            checkpoint.mkdir()
            for name in trainer.RESUME_FILES:
                (checkpoint / name).write_text(name, encoding='utf-8')
            trainer.write_json(state / 'run_manifest.json', {'signature': signature, 'status': 'running'})
            trainer.write_json(checkpoint / 'checkpoint_manifest.json', {
                'signature': signature, 'files': trainer.file_hashes(checkpoint, exclude={'checkpoint_manifest.json'})})
            self.assertIsNone(trainer.check_run_directory(state, signature, state / 'adapter', resume=checkpoint))
            (checkpoint / 'adapter_model.safetensors').write_text('corrupted', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                trainer.check_run_directory(state, signature, state / 'adapter', resume=checkpoint)

    def test_completed_adapter_reuse_verifies_hashes_and_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            state, adapter = Path(directory) / 'state', Path(directory) / 'adapter'
            adapter.mkdir()
            signature = {'model': 'tiny'}
            metadata = {'status': 'complete', 'label_source': 'ai_generated_reference'}
            trainer.write_json(adapter / 'training_metadata.json', metadata)
            (adapter / 'adapter_model.safetensors').write_text('adapter', encoding='utf-8')
            trainer.write_json(state / 'run_manifest.json', {'signature': signature, 'status': 'complete',
                'files': trainer.file_hashes(adapter)})
            with self.assertRaisesRegex(ValueError, 'reuse_completed'):
                trainer.check_run_directory(state, signature, adapter)
            self.assertEqual(trainer.check_run_directory(state, signature, adapter, reuse_completed=True), metadata)
            (adapter / 'adapter_model.safetensors').write_text('corrupted', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                trainer.check_run_directory(state, signature, adapter, reuse_completed=True)


class AdapterSmokeTests(unittest.TestCase):
    def test_tiny_qwen3_adapter_updates_and_saves_without_base_weights(self):
        import torch
        from transformers import Qwen3Config, Qwen3ForCausalLM
        tokenizer = tokenizer_fixture()
        torch.manual_seed(42)
        base = Qwen3ForCausalLM(Qwen3Config(vocab_size=len(tokenizer), hidden_size=32,
            intermediate_size=64, num_hidden_layers=1, num_attention_heads=4, num_key_value_heads=2,
            head_dim=8, max_position_embeddings=512))
        model = trainer.prepare_adapter(base, {}, quantized=False)
        self.assertFalse(model.config.use_cache)
        self.assertTrue(model.is_gradient_checkpointing)
        trainable = {name: value for name, value in model.named_parameters() if value.requires_grad}
        self.assertTrue(trainable)
        self.assertTrue(all('lora_' in name for name in trainable))
        before = {name: value.detach().clone() for name, value in trainable.items()}
        batch = trainer.CompletionCollator(tokenizer.pad_token_id)([
            trainer.encode_example(tokenizer, example(), 512)])
        model.train()
        optimizer = torch.optim.AdamW(trainable.values(), lr=0.01)
        for _ in range(2):
            loss = model(**batch).loss
            self.assertTrue(torch.isfinite(loss))
            loss.backward()
            self.assertTrue(any(value.grad is not None and value.grad.abs().sum() > 0 for value in trainable.values()))
            optimizer.step()
            optimizer.zero_grad()
        self.assertTrue(any(not torch.equal(before[name], value) for name, value in trainable.items()))
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            model.save_pretrained(directory, safe_serialization=True)
            self.assertTrue((Path(directory) / 'adapter_model.safetensors').is_file())
            self.assertTrue((Path(directory) / 'adapter_config.json').is_file())
            self.assertFalse((Path(directory) / 'model.safetensors').exists())
            from safetensors.torch import load_file
            self.assertTrue(all('lora_' in name for name in load_file(str(Path(directory) / 'adapter_model.safetensors'))))


if __name__ == '__main__':
    unittest.main()
