"""Exercise experiment isolation, evidence validation and paired scoring without an LLM."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'data/exp_a/.kaggle/matrix'))


class MatrixChecks(unittest.TestCase):
    def module(self):
        path = ROOT / 'data/exp_a/.kaggle/matrix/matrix.py'
        self.assertTrue(path.is_file(), 'The paired experiment runner is missing')
        spec = importlib.util.spec_from_file_location('exp_a_matrix', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_independent_facet_calls_replace_only_targets_and_keep_source_conditions(self):
        m = self.module()
        paper = dict(paper_id='P000002', title='Ranking', abstract=(
            'We introduce RankNet. When training data is limited, RankNet does not improve accuracy.'))
        baseline = dict(paper_id='P000002', problem=['existing limitation'], task=['ranking'],
                        method=['OLD_DRAFT_SECRET'], dataset=['OldData'], contribution=['OLD_DRAFT_SECRET'])
        replies = [dict(paper_id='P000002', items=[dict(evidence_id='A0', span='RankNet', concept='RankNet', kind='method')]),
                   dict(paper_id='P000002', items=[dict(evidence_id='A1',
                        span='When training data is limited, RankNet does not improve accuracy',
                        concept='When training data is limited, RankNet does not improve accuracy', kind='finding')])]
        requests = []
        def generate(messages, seed):
            requests.append(messages)
            return json.dumps(replies[len(requests)-1]), dict(usage={'input_tokens': 10, 'output_tokens': 5}, generation_seconds=1)
        result = m.split_paper(paper, baseline, generate, seed=42)
        self.assertEqual(result['facets']['method'], ['RankNet'])
        self.assertEqual(result['facets']['contribution'], ['When training data is limited, RankNet does not improve accuracy'])
        self.assertEqual([result['facets'][f] for f in ('problem','task','dataset')],
                         [['existing limitation'], ['ranking'], ['OldData']])
        self.assertNotIn('OLD_DRAFT_SECRET', json.dumps(requests))
        self.assertEqual(len(requests), 2)
        self.assertFalse(result['fallback_used'])
        self.assertEqual(result['usage']['output_tokens'], 10)

    def test_invented_span_is_repaired_and_other_facet_receives_fresh_context(self):
        m = self.module()
        paper = dict(paper_id='P000002', title='Ranking', abstract='We use RankNet.')
        baseline = dict(paper_id='P000002', **{f: [] for f in m.FACETS})
        bad = dict(paper_id='P000002', items=[dict(evidence_id='A0', span='RankNet invented', concept='RankNet', kind='method')])
        good = dict(paper_id='P000002', items=[dict(evidence_id='A0', span='RankNet', concept='RankNet', kind='method')])
        replies = [bad, good, dict(paper_id='P000002', items=[])]
        requests = []
        def generate(messages, seed):
            requests.append(messages)
            return json.dumps(replies[len(requests)-1]), dict(usage={}, generation_seconds=0)
        result = m.split_paper(paper, baseline, generate, seed=42)
        self.assertEqual(result['facets']['method'], ['RankNet'])
        self.assertEqual(len(requests[1]), 4)
        self.assertEqual(len(requests[2]), 2)
        self.assertTrue(result['audit']['method']['attempts'][0]['errors'])
        self.assertFalse(result['fallback_used'])

    def test_failed_repairs_remain_flagged_and_cannot_publish_invented_items(self):
        m = self.module()
        paper = dict(paper_id='P000002', title='Ranking', abstract='We use RankNet.')
        baseline = dict(paper_id='P000002', **{f: [] for f in m.FACETS})
        def generate(messages, seed):
            return json.dumps(dict(paper_id='P000002', items=[dict(evidence_id=[], span='fiction', concept='fiction', kind='method')])), dict(usage={})
        result = m.split_paper(paper, baseline, generate, seed=42)
        self.assertEqual(result['facets']['method'], [])
        self.assertEqual(result['facets']['contribution'], [])
        self.assertTrue(result['fallback_used'])
        self.assertEqual(sum(len(a['attempts']) for a in result['audit'].values()), 4)

    def test_scoring_uses_one_to_one_guarded_matches_and_counts_missing_labels(self):
        m = self.module()
        paper = dict(paper_id='P000002', title='Ranking', abstract='The model does not improve accuracy.')
        predicted = dict(paper_id='P000002', **{f: [] for f in m.FACETS})
        predicted.update(method=['RankNet','extra method'], contribution=['model improves accuracy'])
        truth = dict(paper_id='P000002', facets={f: [] for f in m.FACETS})
        truth['facets'].update(method=['RankNet','other method'], contribution=['model does not improve accuracy'])
        vectors = {v: [1.0,0.0] for v in ('model improves accuracy','model does not improve accuracy')}
        vectors.update({'extra method':[1.0,0.0], 'other method':[0.0,1.0]})
        report = m.score_rows([paper], [dict(facets=predicted)], [truth], vectors)
        self.assertEqual([report['micro'][k] for k in ('tp','fp','fn')], [1,2,2])
        self.assertAlmostEqual(report['micro']['f1'], 1/3)
        self.assertEqual(report['details'][0]['comparison']['contribution']['missing'], ['model does not improve accuracy'])
        with self.assertRaisesRegex(ValueError, 'IDs'):
            m.score_rows([paper], [], [truth], vectors)

    def test_checkpoint_cannot_resume_with_changed_source_or_experiment(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'result.json'
            m.save_record(path, {'paper_id':'P000002','facets':{'method':[]}}, 'source-and-config-hash')
            self.assertEqual(m.load_record(path, 'source-and-config-hash')['paper_id'], 'P000002')
            with self.assertRaisesRegex(ValueError, 'signature'):
                m.load_record(path, 'different-source-or-config')

    def test_findings_cannot_lose_leading_condition_or_distant_and_contracted_negation(self):
        m = self.module()
        for source,short in [
            ('When training data is limited, RankNet improves accuracy.', 'RankNet improves accuracy'),
            ("RankNet doesn't improve accuracy.", 'improve accuracy'),
            ("RankNet doesn't improve accuracy.", 'RankNet improve accuracy'),
            ("RankNet isn't improving accuracy.", 'RankNet improving accuracy'),
            ('RankNet is not currently able to improve accuracy.', 'improve accuracy')]:
            paper = dict(paper_id='P000002',title='Ranking',abstract=source)
            raw = json.dumps(dict(paper_id='P000002',items=[dict(evidence_id='A0',span=short,concept=short,kind='finding')]))
            with self.subTest(source=source):
                items,errors = m.parse_items(raw,paper,'contribution')
                self.assertEqual(items,[])
                self.assertTrue(errors)
                raw = json.dumps(dict(paper_id='P000002',items=[dict(evidence_id='A0',span=source,concept=source,kind='finding')]))
                self.assertEqual(m.parse_items(raw,paper,'contribution')[1],[])
                raw = json.dumps(dict(paper_id='P000002',items=[dict(evidence_id='A0',span=source,concept=short,kind='finding')]))
                self.assertTrue(m.parse_items(raw,paper,'contribution')[1])
        source = 'The baseline does not improve accuracy, but RankNet improves accuracy.'
        paper = dict(paper_id='P000002',title='Ranking',abstract=source)
        raw = json.dumps(dict(paper_id='P000002',items=[dict(evidence_id='A0',span='RankNet improves accuracy',concept='RankNet improves accuracy',kind='finding')]))
        self.assertEqual(m.parse_items(raw,paper,'contribution')[1],[])

    def test_bundle_contains_same_source_ids_and_isolates_reference_from_model_inputs(self):
        path = ROOT / 'data/exp_a/.kaggle/matrix/build_matrix.py'
        self.assertTrue(path.is_file(), 'The matrix bundle builder is missing')
        spec = importlib.util.spec_from_file_location('build_matrix', path)
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        import zipfile
        with tempfile.TemporaryDirectory() as directory:
            manifest = builder.build(Path(directory))
            with zipfile.ZipFile(Path(directory)/'input-dataset/matrix_bundle.zip.bin') as archive:
                names = archive.namelist()
                papers = [json.loads(v) for v in archive.read('model_inputs/papers.jsonl').decode().splitlines()]
                reference = [json.loads(v) for v in archive.read('evaluation_only/review_annotations.jsonl').decode().splitlines()]
                self.assertEqual(len(papers), 50)
                self.assertEqual({p['paper_id'] for p in papers}, {p['paper_id'] for p in reference})
                self.assertFalse(any('reference' in n or 'review_annotations' in n for n in names if n.startswith('model_inputs/')))
                self.assertTrue(all('facets' not in p for p in papers))
                self.assertEqual(manifest['baseline_expected_counts'], {'tp':200,'fp':135,'fn':202})
                metadata = json.loads((Path(directory)/'kernel/kernel-metadata.json').read_text())
                self.assertTrue(metadata['is_private'])

    def test_attention_preserves_causal_and_padding_masks_with_grouped_kv(self):
        m = self.module()
        self.assertTrue(hasattr(m,'install_attention'), 'T4 attention fix is missing')
        import torch
        from transformers import Qwen3Config, Qwen3ForCausalLM
        torch.manual_seed(1)
        model = Qwen3ForCausalLM(Qwen3Config(vocab_size=32,hidden_size=32,intermediate_size=64,
            num_hidden_layers=1,num_attention_heads=4,num_key_value_heads=2,head_dim=8)).eval()
        ids = torch.tensor([[0,1,4,5],[1,6,7,8]])
        mask = torch.tensor([[0,1,1,1],[1,1,1,1]])
        with torch.inference_mode():
            expected = model(ids,attention_mask=mask).logits
            model.set_attn_implementation(m.install_attention())
            actual = model(ids,attention_mask=mask).logits
            torch.testing.assert_close(actual,expected,atol=2e-6,rtol=2e-5)
            prefix = model(ids[:,:-1],attention_mask=mask[:,:-1],use_cache=True)
            last = model(ids[:,-1:],attention_mask=mask,past_key_values=prefix.past_key_values).logits
            torch.testing.assert_close(last,actual[:,-1:],atol=2e-6,rtol=2e-5)

    def test_completed_worker_replays_checkpoints_without_loading_model(self):
        m = self.module()
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            settings=dict(generation=dict(prompt='prompt.md',guideline='guide.md'),models={'4b':{}},generation_signature='same-run')
            m.base.write_json(root/'matrix_settings.json',settings)
            paper=dict(paper_id='P000002',title='Ranking',abstract='We use ranking.')
            m.base.write_jsonl(root/'model_inputs/papers.jsonl',[paper])
            m.base.write_jsonl(root/'model_inputs/baseline_records.jsonl',[dict(paper_id='P000002')])
            for name in ('prompt.md','guide.md'):
                (root/name).write_text('Extract.',encoding='utf-8')
            m.save_record(root/'results/4b_source_first/records/P000002.json',dict(paper_id='P000002'),'same-run')
            with patch.object(m,'load_generator',side_effect=AssertionError('Completed worker must not load/download a model')):
                m.worker(root,'4b',0)

    def test_recovery_rejects_changed_embedded_split_prompt(self):
        import build_matrix as builder
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory, patch.object(builder.matrix,'METHOD',builder.matrix.METHOD+'\nChanged extraction instructions.'):
            with self.assertRaisesRegex(ValueError,'source-first policy'):
                builder.build(Path(directory))

    def test_fused_attention_avoids_unsupported_native_gqa_path(self):
        m = self.module()
        self.assertTrue(hasattr(m,'memory_efficient_attention'), 'T4 attention fix is missing')
        import torch
        if not torch.cuda.is_available():
            self.skipTest('CUDA unavailable')
        from types import SimpleNamespace
        import warnings
        from torch.nn.attention import sdpa_kernel,SDPBackend
        from transformers.integrations.sdpa_attention import sdpa_attention_forward
        module = SimpleNamespace(num_key_value_groups=4,is_causal=True)
        q = torch.randn(1,8,64,32,device='cuda',dtype=torch.float16)
        k = torch.randn(1,2,64,32,device='cuda',dtype=torch.float16)
        v = torch.randn_like(k)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with sdpa_kernel(SDPBackend.EFFICIENT_ATTENTION), self.assertRaises(RuntimeError):
                sdpa_attention_forward(module,q,k,v,None)
        with sdpa_kernel(SDPBackend.MATH):
            expected = torch.nn.functional.scaled_dot_product_attention(q,k.repeat_interleave(4,1),v.repeat_interleave(4,1),is_causal=True)
        actual,_ = m.memory_efficient_attention(module,q,k,v,None)
        torch.testing.assert_close(actual.transpose(1,2),expected,atol=2e-3,rtol=2e-3)


if __name__ == '__main__':
    unittest.main()
