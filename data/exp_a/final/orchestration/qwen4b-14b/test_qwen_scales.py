import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
FINAL = HERE.parents[1]
REPO = FINAL.parents[2]


def load(path, name='qwen_scales_test'):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScaleTests(unittest.TestCase):
    def test_reuses_existing_dataset_and_has_no_token_requirement(self):
        prepare = load(HERE/'prepare.py')
        with tempfile.TemporaryDirectory(dir=REPO/'.test-tmp') as tmp:
            destination = Path(tmp)
            prepare.build(destination)
            metadata = json.loads((destination/'kernel/kernel-metadata.json').read_text())
            self.assertEqual(metadata['dataset_sources'], ['htnkhi/exp-a-llama-gemma-gold400-inputs'])
            self.assertEqual(metadata['machine_shape'], 'NvidiaTeslaT4')
            self.assertTrue(metadata['enable_gpu'])
            self.assertTrue(metadata['is_private'])
            self.assertFalse((destination/'input-dataset').exists())
            boot = load(destination/'kernel/run_qwen_scales.py')
            self.assertFalse(hasattr(boot, 'hf_token'))

    def prepared(self, root):
        prepare = load(HERE/'prepare.py')
        prepare.build(root/'build')
        boot = load(root/'build/kernel/run_qwen_scales.py')
        boot.extract(FINAL/'orchestration/gemma-llama/release_20261030_v1/input-dataset/llama_gemma_bundle.zip.bin',
                     root/'run/source', boot.BUNDLE_SHA256)
        boot.prepare_common(root/'run')
        return boot, root/'run'

    def test_original_splits_and_public_qwen_training_prefix_are_preserved(self):
        with tempfile.TemporaryDirectory(dir=REPO/'.test-tmp') as tmp:
            boot, root = self.prepared(Path(tmp))
            project = boot.prepare_model(root, dict(key='Qwen4B', model='Qwen/Qwen3-4B', revision='a'*40))
            settings = json.loads((project/'settings.json').read_text())
            self.assertEqual({k:len(v) for k,v in settings['splits'].items()}, {'train':280,'valid':60,'test':60})
            self.assertEqual(settings['training']['epochs'], 3)
            self.assertEqual(settings['training']['learning_rate'], .0001)
            self.assertFalse((project/'training_data/test.jsonl').exists())
            # Exercise the actual pinned Qwen tokenizer, with its native non-thinking prefix.
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(str(REPO/'models/huggingface/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218'), local_files_only=True)
            sys.path.insert(0, str(project))
            try:
                compat = load(project/'compat.py', 'public_qwen_compat_test')
                row = json.loads((project/'training_data/train.jsonl').read_text().splitlines()[0])
                encoded = compat.encode_example(tokenizer, row, 4096)
                supervised = [v for v in encoded['labels'] if v != -100]
                self.assertEqual(tokenizer.decode(supervised), row['messages'][-1]['content']+'<|im_end|>')
                helper = load(project/'train.py', 'public_qwen_trainer_test')
                self.assertEqual(encoded, helper.encode_example(tokenizer, row, 4096))
            finally:
                sys.path.remove(str(project))

    def test_batch_finishes_4b_before_starting_14b(self):
        with tempfile.TemporaryDirectory(dir=REPO/'.test-tmp') as tmp:
            boot, root = self.prepared(Path(tmp))
            for key,model in (('Qwen4B','Qwen/Qwen3-4B'),('Qwen14B','Qwen/Qwen3-14B')):
                boot.prepare_model(root, dict(key=key, model=model, revision='a'*40))
            batch = load(root/'batch.py', 'qwen_batch_test')
            events = []
            def execute(project):
                events.append(('run', project.name))
                batch.write(project/'results/experiment_summary.json', dict(status='complete', signature=batch.read(project/'settings.json')['signature']))
            def publish(project):
                events.append(('save', project.name))
                batch.publish_model(project)
            batch.run_models(root, execute=execute, publish=publish)
            self.assertEqual(events, [('run','Qwen4B'),('save','Qwen4B'),('run','Qwen14B'),('save','Qwen14B')])
            events.clear()
            batch.run_models(root, execute=execute, publish=publish)
            self.assertEqual(events, [])


if __name__ == '__main__':
    unittest.main()
