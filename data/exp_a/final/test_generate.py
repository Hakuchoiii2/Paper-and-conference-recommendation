import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


class FinalPipelineTests(unittest.TestCase):
    def module(self):
        self.assertTrue((HERE/'generate.py').is_file(), 'Official generation entrypoint is missing')
        spec = importlib.util.spec_from_file_location('official_generation_test', HERE/'generate.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_real_three_pass_pipeline_exports_and_resumes_without_new_calls(self):
        m = self.module()
        config = m.read(REPO/'data/exp_a/final/config.json')
        source = REPO/'data/exp_a/final/reference'
        paper = m.read_rows(source/'model_inputs/train.jsonl')[0]
        answer = m.read_rows(source/'training_data/train.jsonl')[0]['messages'][-1]['content']
        calls = []
        def factory(shared, generation):
            self.assertEqual(Path(generation['adapter_path']), REPO/config['adapter'])
            def decoder(messages, seed):
                calls.append((messages, seed))
                reply = answer if len(calls) < 3 else json.dumps(dict(paper_id=paper['paper_id'], task=[], method=[]))
                return reply, dict(usage=dict(input_tokens=10, output_tokens=10), generation_seconds=0.1, reached_token_limit=False)
            return decoder, dict(adapter_enabled=True)
        with tempfile.TemporaryDirectory(dir=REPO/'.test-tmp') as directory:
            out = Path(directory)
            result = m.generate([paper], out, config, REPO, factory=factory)
            self.assertEqual(result['status'], 'complete')
            self.assertEqual(len(calls), 3)
            record = m.read(out/'records'/f'{paper["paper_id"]}.json')['record']
            expected = json.loads(answer)
            self.assertEqual(record['facets'], dict(paper_id=paper['paper_id'], **{f:[x['concept'] for x in expected[f]] for f in m.FACETS}))
            self.assertTrue(record['adapter_enabled'])
            metadata = m.read_rows(out/'annotation_metadata.jsonl')[0]
            self.assertEqual(metadata['review_status'], 'unreviewed')
            self.assertEqual(metadata['tier'], 'silver')
            self.assertEqual(m.read_rows(out/'facets_silver.jsonl'), [record['facets']])
            m.generate([paper], out, config, REPO, factory=lambda *_: self.fail('Resume loaded a model'))
            changed = dict(paper, abstract=paper['abstract']+' Changed source.')
            with self.assertRaisesRegex(ValueError, 'signature|identity'):
                m.generate([changed], out, config, REPO, factory=factory)
            exports = {n:(out/n).read_bytes() for n in ('facets_silver.jsonl','annotation_metadata.jsonl','manifest.json')}
            path = out/'records'/f'{paper["paper_id"]}.json'
            envelope = m.read(path)
            envelope['record']['source_sha256'] = 'tampered'
            path.write_text(json.dumps(envelope), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                m.generate([paper], out, config, REPO, factory=factory)
            self.assertEqual(exports, {n:(out/n).read_bytes() for n in exports})

    def test_rejects_bad_ids_and_duplicate_inputs_before_model_loading(self):
        m = self.module()
        with tempfile.TemporaryDirectory(dir=REPO/'.test-tmp') as directory:
            path = Path(directory)/'papers.jsonl'
            for rows in ([dict(paper_id='../escape', title='Title', abstract='Text')],
                         [dict(paper_id='P000001', title='Title', abstract='Text')]*2):
                path.write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')
                with self.assertRaises(ValueError):
                    m.read_papers(path)

    def test_integrity_rejects_changed_and_escaping_paths(self):
        m = self.module()
        with tempfile.TemporaryDirectory(dir=REPO/'.test-tmp') as directory:
            root = Path(directory)
            path = root/'weights'; path.write_bytes(b'valid')
            m.verify_files(root, {'weights': m.sha(path)})
            with self.assertRaises(ValueError):
                m.verify_files(root, {'../weights': m.sha(path)})
            with self.assertRaises(ValueError):
                m.verify_files(root, {'weights': '0'*64})


if __name__ == '__main__':
    unittest.main()
