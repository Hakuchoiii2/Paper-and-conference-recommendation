"""Collection must reject incomplete, corrupted or mispaired cloud measurements."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT/'data/exp_a/finetuning/v2'


class V2CollectionTests(unittest.TestCase):
    def test_checks_signatures_pairing_and_actual_validator_before_reporting(self):
        self.assertTrue((HERE/'collect.py').is_file(), 'v2 collection is not implemented')
        spec = importlib.util.spec_from_file_location('v2_collect_test', HERE/'collect.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with zipfile.ZipFile(ROOT/'data/exp_a/finetuning/policy_ab/build/input-dataset/policy_ab_bundle.zip.bin') as archive:
                frozen = json.loads(archive.read('settings.json'))
                instruction = archive.read('instruction_new.txt').decode().replace('\r\n','\n')
            papers = module.sources()
            probe = dict(version='exp_a_v2_decoding_probe_1', papers=list(module.PAPERS),
                decoders=['greedy','sampling'], limits=dict(max_new_tokens=1024,seconds_per_call=90),
                source_signature=frozen['signature'], training_performed=False,
                sampling=dict(temperature=0.7,top_p=0.8,top_k=20),
                files={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in module.code_paths().items()})
            probe['signature'] = module.digest(probe)
            (directory/'probe_settings.json').write_text(json.dumps(probe),encoding='utf-8')
            paths = []
            for arm in ('base','adapter'):
                for decoder in ('greedy','sampling'):
                    for pid in module.PAPERS:
                        raw=json.dumps(dict(paper_id=pid,**{f:[] for f in module.runner.shared.FACETS}))
                        messages=module.legacy.first_messages(module.runner,papers[pid],instruction,'new_v2_2')
                        record=dict(arm=arm,decoder=decoder,policy='new_v2_2',paper_id=pid,status='measured',
                            seed=frozen['generation']['seed']+int(pid[1:])*frozen['generation']['max_attempts'],stage='draft',
                            probe_signature=probe['signature'],source_signature=frozen['signature'],
                            messages_sha256=module.digest(messages),instruction_sha256=frozen['files']['instruction_new.txt'],
                            adapter_manifest_sha256=frozen['adapter_manifest_sha256'],
                            runtime=dict(model=frozen['model']['model'],revision=frozen['model']['revision'],
                                transformers='4.57.6',torch='2.11.0+cu128',gpu='Tesla T4',
                                quantization='nf4_double_fp16',enable_thinking=False,use_cache=True,adapter_enabled=arm=='adapter'),
                            raw_output=raw,raw_output_untrimmed=raw,schema_valid=True,validation_errors=[],
                            stop_reason='json_complete',bounded_stop=False,generation_seconds=1.0,
                            usage=dict(input_tokens=100,output_tokens=50))
                        path=directory/f'results/{arm}/{decoder}/{pid}.json'
                        path.parent.mkdir(parents=True,exist_ok=True)
                        path.write_text(json.dumps(dict(record=record,record_sha256=module.digest(record))),encoding='utf-8')
                        paths.append(path)
            (directory/'run_summary.json').write_text(json.dumps(dict(status='complete',signature=probe['signature'],
                saved_calls=12,expected_calls=12,worker_exit_codes=[0,0])),encoding='utf-8')
            report = module.collect(directory)
            self.assertEqual(report['verified_records'],12)
            self.assertEqual(len(report['groups']),4)
            self.assertEqual(report['groups'][0]['mean_seconds'],1.0)
            path=paths[-1]; pristine=path.read_bytes()
            for field, value, message in (('seed', -1, 'seed'), ('stage', 'review', 'stage')):
                envelope=json.loads(pristine); envelope['record'][field]=value
                envelope['record_sha256']=module.digest(envelope['record'])
                path.write_text(json.dumps(envelope),encoding='utf-8')
                with self.assertRaisesRegex(ValueError,message):
                    module.collect(directory)
            for field,value in (('enable_thinking',True),('use_cache',False),('quantization','none')):
                envelope=json.loads(pristine); envelope['record']['runtime'][field]=value
                envelope['record_sha256']=module.digest(envelope['record'])
                path.write_text(json.dumps(envelope),encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'Runtime'):
                    module.collect(directory)
            envelope=json.loads(pristine); envelope['record']['usage']['output_tokens']=2048
            envelope['record_sha256']=module.digest(envelope['record'])
            path.write_text(json.dumps(envelope),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'token'):
                module.collect(directory)
            path.write_bytes(pristine)
            envelope=json.loads(pristine)
            envelope['record']['messages_sha256']='0'*64
            envelope['record_sha256']=module.digest(envelope['record'])
            path.write_text(json.dumps(envelope),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'messages'):
                module.collect(directory)
            path.write_bytes(pristine)
            envelope=json.loads(pristine); envelope['record']['raw_output']='tampered'
            path.write_text(json.dumps(envelope),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'checksum'):
                module.collect(directory)
            path.unlink()
            with self.assertRaisesRegex(ValueError,'12'):
                module.collect(directory)


if __name__ == '__main__':
    unittest.main()
