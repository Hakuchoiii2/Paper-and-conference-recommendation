"""Preparation checks at the complete dataset boundary; no model downloads."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / 'data/exp_a/finetuning/prepare.py'
spec = importlib.util.spec_from_file_location('qlora_prepare_under_test', MODULE_PATH)
preparation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparation)


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')


def fixture(root, count=40):
    review = root / 'data/exp_a/ground_truth/gold_review'
    papers, references, evidence = [], [], []
    for index in range(count):
        pid = f'P{index + 1:06d}'
        paper = dict(paper_id=pid, title=f'Document retrieval study {index + 1}', abstract=
            'This study addresses costly retrieval. We use hashing and cosine similarity for document retrieval. '
            'We introduce the TREC corpus.')
        facets = dict(problem=[], task=['document retrieval'], method=[], dataset=[], contribution=[])
        if index % 5 == 0:
            facets['problem'] = ['costly retrieval']
        if index % 2 == 0:
            facets['method'] = ['hashing', 'cosine similarity'] if index % 4 == 0 else ['hashing']
        if index < 6:
            facets['dataset'] = ['TREC corpus']
        if index % 3 == 0:
            facets['contribution'] = ['TREC corpus']
        if index == count - 1:
            facets = {facet: [] for facet in preparation.base.FACET_NAMES}
        options = preparation.base.evidence_options(paper)
        ev = {}
        for facet, concepts in facets.items():
            ev[facet] = []
            for concept in concepts:
                eid, option = next((eid, option) for eid, option in options.items() if concept in option['evidence'])
                ev[facet].append(dict(concept=concept, evidence_id=eid, grounding_kind='source_phrase', **option))
        papers.append(paper)
        references.append(dict(paper_id=pid, facets=facets, reviewer_type='ai', review_status='reviewed',
                               human_review_status='pending'))
        evidence.append(dict(paper_id=pid, annotation_origin='fixture_ai_reference', evidence=ev,
            source_sha256=hashlib.sha256(json.dumps(paper, ensure_ascii=False, sort_keys=True).encode()).hexdigest()))
    write_jsonl(review / 'review_papers.jsonl', papers)
    write_jsonl(review / 'review_annotations.jsonl', references)
    write_jsonl(review / 'gpt_review_evidence.jsonl', evidence)
    (review / 'gpt_review_manifest.json').write_text('{"source_confirmation_pending_ids": []}', encoding='utf-8')
    write_jsonl(root / 'data/processed/papers.jsonl', papers)
    write_jsonl(root / 'data/exp_a/pilot50/ai_reference_v1/source_papers.jsonl', [])
    prompt = root / 'data/exp_a/prompts/prompt.md'
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text('Use source words and return all five facets.', encoding='utf-8')
    (prompt.parent / 'guideline.md').write_text('Only extract supported concepts.', encoding='utf-8')
    (root / 'data/exp_a/config_v3_pilot50.json').write_text(json.dumps(dict(
        corpus='data/processed/papers.jsonl', prompt='data/exp_a/prompts/prompt.md',
        guideline='data/exp_a/prompts/guideline.md')), encoding='utf-8')
    return papers, references, evidence


class PrepareChecks(unittest.TestCase):
    def test_exact_quotas_reproducible_and_rare_facets_reach_holdouts(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            root = Path(directory)
            fixture(root)
            first = preparation.prepare(root, root / 'one', seed=42)
            second = preparation.prepare(root, root / 'two', seed=42)
            self.assertEqual(first['counts'], dict(train=28, dev=6, test=6))
            self.assertEqual(first['split_ids'], second['split_ids'])
            self.assertEqual(len(set().union(*(set(ids) for ids in first['split_ids'].values()))), 40)
            for split in ('train', 'dev', 'test'):
                self.assertGreater(first['distributions'][split]['facet_presence']['dataset'], 0)
                self.assertGreater(first['distributions'][split]['facet_multiple']['method'], 0)
            train = preparation.base.read_jsonl(root / 'one/train.jsonl')
            self.assertEqual(len(train[0]['messages']), 3)
            self.assertEqual([message['role'] for message in train[0]['messages']], ['system', 'user', 'assistant'])
            self.assertEqual(train[0]['provenance']['human_review_status'], 'pending')
            self.assertEqual(train[0]['messages'][0]['content'],
                'Only extract supported concepts.\n\nUse source words and return all five facets.'
                + '\nReturn JSON only. Schema: ' + json.dumps(preparation.base.SCHEMA))
            test_papers = preparation.base.read_jsonl(root / 'one/test_papers.jsonl')
            self.assertEqual(set(test_papers[0]), {'paper_id', 'title', 'abstract'})
            self.assertTrue((root / 'one/instruction.txt').is_file())

    def test_bad_concept_rejects_whole_paper_and_exact_evidence_id_remaps(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            root = Path(directory)
            papers, references, evidence = fixture(root, count=10)
            review = root / 'data/exp_a/ground_truth/gold_review'
            references[0]['facets']['method'].append('invented algorithm')
            evidence[0]['evidence']['method'].append(dict(concept='invented algorithm', evidence_id='A1',
                source='abstract', evidence=preparation.base.evidence_options(papers[0])['A1']['evidence']))
            evidence[1]['evidence']['task'][0]['evidence_id'] = 'R2-task-1'
            write_jsonl(review / 'review_annotations.jsonl', references)
            write_jsonl(review / 'gpt_review_evidence.jsonl', evidence)
            result = preparation.prepare(root, root / 'out')
            all_ids = set().union(*(set(ids) for ids in result['split_ids'].values()))
            self.assertNotIn('P000001', all_ids)
            self.assertIn('P000002', all_ids)
            self.assertEqual(result['eligible_papers'], 9)
            rows = sum((preparation.base.read_jsonl(root / 'out' / name)
                for name in ('train.jsonl', 'dev.jsonl', 'test_references.jsonl')), [])
            row = next(row for row in rows if row['paper_id'] == 'P000002')
            self.assertEqual(row['provenance']['evidence_id_remapping'][0]['after'], 'A1')

    def test_pending_frozen_and_prompt_examples_are_excluded(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            root = Path(directory)
            papers, _, _ = fixture(root, count=10)
            write_jsonl(root / 'data/exp_a/pilot50/ai_reference_v1/source_papers.jsonl', [papers[0]])
            (root / 'data/exp_a/prompts/prompt.md').write_text('Example P000002.', encoding='utf-8')
            (root / 'data/exp_a/ground_truth/gold_review/gpt_review_manifest.json').write_text(
                '{"source_confirmation_pending_ids": ["P000003"]}', encoding='utf-8')
            result = preparation.prepare(root, root / 'out')
            self.assertEqual(result['eligible_papers'], 7)
            self.assertEqual({row['paper_id'] for row in result['rejected_papers']}, {'P000001', 'P000002', 'P000003'})

    def test_corrupt_source_hash_or_corpus_fails_closed(self):
        for corrupt_hash in (True, False):
            with self.subTest(corrupt_hash=corrupt_hash), tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
                root = Path(directory)
                papers, _, evidence = fixture(root, count=5)
                if corrupt_hash:
                    evidence[0]['source_sha256'] = 'incorrect'
                    write_jsonl(root / 'data/exp_a/ground_truth/gold_review/gpt_review_evidence.jsonl', evidence)
                else:
                    papers[0]['abstract'] = 'Changed source.'
                    write_jsonl(root / 'data/processed/papers.jsonl', papers)
                with self.assertRaisesRegex(ValueError, 'source hash mismatch|source differs'):
                    preparation.prepare(root, root / 'out')
                self.assertFalse((root / 'out').exists())

    def test_duplicate_titles_cannot_leak_across_splits(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            root = Path(directory)
            papers, _, evidence = fixture(root)
            for paper, proof in zip(papers, evidence):
                paper['title'] = 'Shared paper title'
                proof['source_sha256'] = hashlib.sha256(json.dumps(paper, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            write_jsonl(root / 'data/processed/papers.jsonl', papers)
            write_jsonl(root / 'data/exp_a/ground_truth/gold_review/review_papers.jsonl', papers)
            write_jsonl(root / 'data/exp_a/ground_truth/gold_review/gpt_review_evidence.jsonl', evidence)
            with self.assertRaisesRegex(ValueError, 'Cross-split title leakage'):
                preparation.prepare(root, root / 'out')
            self.assertFalse((root / 'out').exists())

    def test_token_limits_reject_complete_examples_without_truncation(self):
        class Tokenizer:
            def apply_chat_template(self, messages, tokenize, add_generation_prompt, enable_thinking):
                if enable_thinking:
                    raise AssertionError('Preparation must use the same non-thinking template as inference')
                prefix = list(range(20))
                if add_generation_prompt:
                    return prefix
                pid = json.loads(messages[-1]['content'])['paper_id']
                length = {'P000001': 4097, 'P000002': 2069}.get(pid, 50)
                return prefix + [99] * (length - len(prefix))

        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            root = Path(directory)
            fixture(root)
            result = preparation.prepare(root, root / 'out', tokenizer=Tokenizer())
            self.assertEqual(result['eligible_papers'], 38)
            self.assertTrue(result['token_limits']['verified'])
            self.assertEqual({row['paper_id'] for row in result['rejected_papers']}, {'P000001', 'P000002'})
            for row in preparation.base.read_jsonl(root / 'out/train.jsonl'):
                self.assertEqual(row['token_lengths'], dict(sequence=50, assistant=30))

    def test_additional_teacher_references_are_balanced_and_never_disguised_as_human(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            root = Path(directory)
            papers, references, evidence = fixture(root)
            review = root / 'data/exp_a/ground_truth/gold_review'
            write_jsonl(review / 'review_papers.jsonl', papers[:30])
            write_jsonl(review / 'review_annotations.jsonl', references[:30])
            write_jsonl(review / 'gpt_review_evidence.jsonl', evidence[:30])
            extra = root / 'teacher'
            write_jsonl(extra / 'source_papers.jsonl', papers[30:])
            write_jsonl(extra / 'review_annotations.jsonl', references[30:])
            write_jsonl(extra / 'review_evidence.jsonl', evidence[30:])
            result = preparation.prepare(root, root / 'out', extra_source_dir=extra)
            self.assertEqual(result['eligible_papers'], 40)
            for split in ('train', 'dev', 'test'):
                self.assertGreater(result['distributions'][split]['annotation_groups']['additional_ai_reference'], 0)
            self.assertEqual(result['annotation_kind'], 'ai_reference')
            self.assertEqual(result['human_review_status'], 'pending')


if __name__ == '__main__':
    unittest.main()
