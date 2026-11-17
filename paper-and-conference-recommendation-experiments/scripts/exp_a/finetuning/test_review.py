"""Require independent source review before new teacher labels enter training."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class TeacherReviewChecks(unittest.TestCase):
    def module(self):
        spec = importlib.util.spec_from_file_location('qlora_review', ROOT/'data/exp_a/finetuning/review.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def fixture(self, root, reviewer='/root/reviewer',paper_id='P000001'):
        paper = dict(paper_id=paper_id, title='Retrieval study',
                     abstract='We introduce hashing for document retrieval.')
        response = dict(paper_id=paper['paper_id'], problem=[], task=[dict(concept='document retrieval', evidence_id='A0')],
                        method=[dict(concept='hashing', evidence_id='A0')], dataset=[],
                        contribution=[dict(concept='hashing', evidence_id='A0')])
        payload = json.dumps(paper, ensure_ascii=False)+'\n'
        (root/'source_candidates.jsonl').write_text(payload, encoding='utf-8')
        (root/'selection.json').write_text(json.dumps(dict(count=1, paper_ids=[paper['paper_id']],
            source_sha256=hashlib.sha256(payload.encode()).hexdigest())), encoding='utf-8')
        batch = root/'batch_1'
        (batch/'drafts').mkdir(parents=True)
        (batch/'reviewed').mkdir()
        (batch/'sources.jsonl').write_text(payload, encoding='utf-8')
        (batch/'drafts/part_01.jsonl').write_text(json.dumps(response)+'\n', encoding='utf-8')
        review = dict(paper_id=paper['paper_id'],response=response,draft_agent='/root/sft_data_audit',
            review_agent=reviewer, review_status='reviewed',reviewer_type='ai',human_review_status='pending',
            source_status='usable',review_notes=['Source coverage, roles and exact evidence checked.'])
        (batch/'reviewed/part_01.jsonl').write_text(json.dumps(review)+'\n', encoding='utf-8')
        return paper, response

    def test_reviewed_response_reconstructs_complete_reference_and_provenance(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paper, response = self.fixture(root)
            manifest = module.aggregate(root, root/'pool')
            proof = json.loads((root/'pool/review_evidence.jsonl').read_text(encoding='utf-8'))
            reference = json.loads((root/'pool/review_annotations.jsonl').read_text(encoding='utf-8'))
            self.assertEqual(manifest['count'],1)
            self.assertEqual(reference['facets']['method'],['hashing'])
            self.assertEqual(proof['evidence']['method'][0]['evidence'],paper['abstract'])
            self.assertEqual(proof['evidence']['method'][0]['evidence_id'],'A0')
            self.assertEqual(proof['source_sha256'],hashlib.sha256(json.dumps(paper,ensure_ascii=False,sort_keys=True).encode()).hexdigest())
            self.assertEqual(proof['review_agent'],'/root/reviewer')

    def test_self_review_is_rejected(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root,reviewer='/root/sft_data_audit')
            with self.assertRaisesRegex(ValueError,'independent'):
                module.aggregate(root,root/'pool')

    def test_missing_review_cannot_be_claimed_complete(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root/'batch_1/reviewed/part_01.jsonl').unlink()
            with self.assertRaisesRegex(ValueError,'review coverage'):
                module.aggregate(root,root/'pool')

    def test_invalid_paper_is_recorded_as_a_whole_paper_rejection(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root/'batch_1/reviewed/part_01.jsonl'
            review=json.loads(path.read_text(encoding='utf-8'))
            review['response']['method'].append(dict(concept='invented neural model',evidence_id='A0'))
            path.write_text(json.dumps(review)+'\n',encoding='utf-8')
            manifest=module.aggregate(root,root/'pool')
            self.assertEqual(manifest['count'],0)
            self.assertEqual([r['paper_id'] for r in manifest['rejected_papers']],['P000001'])
            self.assertEqual((root/'pool/review_annotations.jsonl').read_text(encoding='utf-8'),'')

    def test_incomplete_source_cannot_enter_the_training_pool(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.fixture(root)
            path=root/'batch_1/reviewed/part_01.jsonl'
            review=json.loads(path.read_text(encoding='utf-8'))
            review.update(source_status='incomplete',review_notes=['Abstract ends in a cut-off clause.'])
            path.write_text(json.dumps(review)+'\n',encoding='utf-8')
            manifest=module.aggregate(root,root/'pool')
            self.assertEqual(manifest['count'],0)
            self.assertIn('incomplete',manifest['rejected_papers'][0]['reason'])

    def test_review_aggregation_enters_real_data_preparation_without_dropping_concepts(self):
        from scripts.exp_a.finetuning.test_prepare import fixture, preparation
        module=self.module()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            papers,_,_=fixture(root,count=10)
            teacher=root/'teacher'
            teacher.mkdir()
            paper,response=self.fixture(teacher,paper_id='P999999')
            preparation.base.write_jsonl(root/'data/processed/papers.jsonl',papers+[paper])
            module.aggregate(teacher,teacher/'pool')
            result=preparation.prepare(root,root/'prepared',extra_source_dir=teacher/'pool')
            self.assertEqual(result['eligible_papers'],11)
            self.assertEqual(result['rejected_papers'],[])
            rows=sum((preparation.base.read_jsonl(root/'prepared'/name)
                for name in ('train.jsonl','dev.jsonl','test_references.jsonl')),[])
            row=next(row for row in rows if row['paper_id']=='P999999')
            if 'messages' in row:
                self.assertEqual(json.loads(row['messages'][-1]['content']),response)
            else:
                self.assertEqual(row['facets']['method'],['hashing'])


if __name__=='__main__':
    unittest.main()
