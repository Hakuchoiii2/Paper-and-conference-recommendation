"""The published adapter must retain every sealed file after adding usage docs."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]


class CollectionChecks(unittest.TestCase):
    def test_publication_docs_preserve_all_sealed_adapter_checksums(self):
        spec = importlib.util.spec_from_file_location('qlora_collect_test', ROOT/'data/exp_a/finetuning/collect.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)/'download'
            build = Path(temporary)/'build'
            destination = Path(temporary)/'dataset'
            source = root/module.experiment.ADAPTER
            source.mkdir(parents=True)
            build.mkdir()
            (root/'results').mkdir()
            original_readme = '# Original PEFT model card\n'
            (source/'README.md').write_text(original_readme,encoding='utf-8')
            (source/'adapter_model.safetensors').write_bytes(b'fixture weights')
            settings = dict(model=dict(model='Qwen/Qwen3-8B',revision='pinned'),
                experiment_signature='fixture',adapter_dataset='owner/adapter')
            manifest = dict(status='complete',base_model='Qwen/Qwen3-8B',base_revision='pinned',
                experiment_signature='fixture',files={name:module.shared.base.sha256(source/name)
                    for name in ('README.md','adapter_model.safetensors')})
            module.shared.base.write_json(source/'adapter_manifest.json',manifest)
            module.shared.base.write_json(build/'build_manifest.json',dict(settings=settings))
            table = [dict(arm='original',tp=1,fp=0,fn=0)]
            module.shared.base.write_json(root/'results/experiment_summary.json',dict(table=table))
            with patch.object(module,'verify_download',return_value=manifest), \
                 patch.object(module.experiment,'evaluate',return_value=table):
                result = module.collect(root,build,destination)
            self.assertEqual(result['status'],'verified_and_staged')
            module.experiment.verify_adapter(destination,settings)
            self.assertEqual((destination/'README.md').read_text(encoding='utf-8'),original_readme)


if __name__ == '__main__':
    unittest.main()
