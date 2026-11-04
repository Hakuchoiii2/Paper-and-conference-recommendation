"""Regression checks for the self-contained final experiment layout."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

FINAL = Path(__file__).resolve().parent
REPO = FINAL.parents[2]


def load(path):
    spec = importlib.util.spec_from_file_location('final_layout_'+path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LayoutTests(unittest.TestCase):
    def test_final_has_two_orchestrators_and_shared_runtime(self):
        for name in ('Qwen8B', 'gemma-llama'):
            self.assertTrue((FINAL/'orchestration'/name/'prepare.py').is_file(), name)
        shared = load(FINAL/'package.py')
        files, settings = shared.source_files()
        self.assertEqual(files['gold_policy.py'], (FINAL/'runtime/gold_policy.py').read_bytes())
        self.assertEqual(files['runtime.py'], (FINAL/'orchestration/Qwen8B/runtime.py').read_bytes())
        self.assertEqual(files[settings['generation']['prompt']], (FINAL/'prompts/extraction_gold_v1.md').read_bytes())
        self.assertEqual({k:len(v) for k,v in settings['splits'].items()}, {'train':280,'valid':60,'test':60})
        self.assertNotIn('training_data/test.jsonl', files)

    def test_both_builders_run_from_new_home_and_use_shared_inputs(self):
        qwen = load(FINAL/'orchestration/Qwen8B/prepare.py')
        compare = load(FINAL/'orchestration/gemma-llama/prepare.py')
        with tempfile.TemporaryDirectory(dir=REPO/'.test-tmp') as tmp:
            root = Path(tmp)
            qwen.build(root/'qwen')
            compare.build(root/'compare')
            runtime = load(FINAL/'orchestration/Qwen8B/runtime.py')
            runtime.verify(root/'qwen/project')
            self.assertTrue((root/'compare/kernel/run_llama_gemma.py').is_file())


if __name__ == '__main__':
    unittest.main()
