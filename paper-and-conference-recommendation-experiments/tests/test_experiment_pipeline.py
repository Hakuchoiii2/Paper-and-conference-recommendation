"""File-backed target-sized datasets and corruption gates; no real facets are fabricated."""
import contextlib
import collections
import io
import json
import sqlite3
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / 'scripts'))
sys.path.insert(0, str(PROJECT / 'data/exp_a'))
import build_exp_a as a
from data import build_experiments as builder
from download_sources import sha256, write_json
from test_experiment_datasets import test_facets
try:
    import validate_experiments as validator
except ImportError:
    validator = None


class PipelineChecks(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(validator, 'Experiment file validators and CLI are not implemented')
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in ('exp_b.json','exp_c.json','exp_d.json','exp_e.json','intent_templates.json'):
            write_json(self.root / 'configs' / name, json.loads((PROJECT / 'configs' / name).read_text(encoding='utf-8')))
        normalized = test_facets()
        papers, records = [], []
        for i, (pid, values) in enumerate(normalized.items(), 1):
            abstract = ' '.join(concept for facet in values.values() for concept in sorted(facet)) + '.'
            papers.append(dict(paper_id=pid, source='csfcube', source_id=str(i), title='Test-only paper',
                               abstract=abstract, year=None, domain='information_technology',
                               scope_evidence=['test-only fixture; never a real corpus']))
            facets = dict(paper_id=pid, **{facet: sorted(concepts) for facet, concepts in values.items()})
            evidence = dict(paper_id=pid, **{facet: [dict(concept=concept, evidence=abstract, source='abstract')
                                                   for concept in sorted(concepts)] for facet, concepts in values.items()})
            metadata = dict(paper_id=pid, tier='silver', dataset_kind='real', annotator_type='qwen_local',
                            review_status='unreviewed', prompt_version='test', guideline_version='test',
                            evidence=evidence, usage={})
            records.append(dict(facets=facets, metadata=metadata))
        a.write_jsonl(self.root / 'data/processed/papers.jsonl', papers)
        for name in ('prompt.md','guide.md'):
            (self.root / name).write_text('Explicitly test-only extraction.', encoding='utf-8')
        self.a_config = dict(corpus='data/processed/papers.jsonl', output_dir='data/exp_a/generated',
                             model='Qwen/test-only', revision='test-only', device='cpu',
                             cache_dir='models', prompt='prompt.md', guideline='guide.md',
                             prompt_version='test', guideline_version='test', max_new_tokens=1024,
                             max_attempts=3, temperature=0.7, top_p=0.8, top_k=20, seed=42)
        with sqlite3.connect(':memory:') as db:
            db.execute('CREATE TABLE annotations (paper_id TEXT PRIMARY KEY, payload TEXT)')
            db.execute('CREATE TABLE failures (paper_id TEXT PRIMARY KEY, error TEXT)')
            db.executemany('INSERT INTO annotations VALUES (?,?)',
                           [(row['facets']['paper_id'], json.dumps(row)) for row in records])
            a.export(self.root,self.a_config,papers,a.inputs(self.root,self.a_config)[1],db)

    def build(self, name):
        with contextlib.redirect_stdout(io.StringIO()):
            return builder.generate(self.root, name)

    def corrupt(self, experiment, filename, mutate):
        directory = self.root / f'data/exp_{experiment}'
        path = directory / filename
        rows = a.read_jsonl(path)
        mutate(rows)
        a.write_jsonl(path, rows)
        manifest_path = directory / 'generated/manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['files'][path.relative_to(self.root).as_posix()] = sha256(path)
        write_json(manifest_path, manifest)

    def test_target_files_validate_and_rebuild_with_identical_bytes(self):
        for name, expected in [('b', {'retrieval_queries.jsonl':300,'retrieval_labels.jsonl':30000}),
                               ('c', {'intents.jsonl':1500,'intent_labels.jsonl':30000}),
                               ('d', {'users.jsonl':300,'interactions_train.jsonl':9000,'interactions_test.jsonl':6000}),
                               ('e', {'temporal_profiles.jsonl':1200,'interactions_train.jsonl':13500,'interactions_test.jsonl':4500})]:
            with self.subTest(experiment=name):
                manifest = self.build(name)
                self.assertEqual(manifest['status'], 'complete')
                for filename, count in expected.items():
                    self.assertEqual(manifest['counts'][filename], count)
                validator.validate_experiment(self.root, name)
                before = {filename: (self.root / filename).read_bytes() for filename in manifest['files']}
                rebuilt = self.build(name)
                self.assertEqual(manifest, rebuilt)
                self.assertEqual(before, {filename: (self.root / filename).read_bytes() for filename in rebuilt['files']})

    def test_rule_labels_and_hidden_truth_corruptions_are_rejected_even_with_new_hashes(self):
        self.build('b')
        self.corrupt('b','ground_truth/retrieval_labels.jsonl', lambda rows: rows[0].update(relevance=9))
        with self.assertRaisesRegex(ValueError, 'relevance|label'):
            validator.validate_experiment(self.root,'b')
        self.build('b')
        self.corrupt('b','generated/retrieval_queries.jsonl', lambda rows: rows[0].update(relevance=2))
        with self.assertRaisesRegex(ValueError, 'field|observable|schema'):
            validator.validate_experiment(self.root,'b')
        self.build('c')
        self.corrupt('c','ground_truth/intent_labels.jsonl',
                     lambda rows: rows[0].update(satisfies_intent=not rows[0]['satisfies_intent']))
        with self.assertRaisesRegex(ValueError, 'intent|label'):
            validator.validate_experiment(self.root,'c')

    def test_future_overlap_and_foreign_e_users_are_rejected(self):
        self.build('d')
        self.corrupt('d','generated/interactions_train.jsonl', lambda rows: rows[0].update(timestamp='2027-01-01T00:00:00Z'))
        with self.assertRaisesRegex(ValueError, 'temporal|time|order'):
            validator.validate_experiment(self.root,'d')
        self.build('d')
        self.build('e')
        self.corrupt('e','generated/interactions_train.jsonl', lambda rows: rows[0].update(user_id='U9999'))
        with self.assertRaisesRegex(ValueError, 'user'):
            validator.validate_experiment(self.root,'e')

    def test_a_prerequisites_fail_before_output_creation_and_dry_run_writes_nothing(self):
        result = builder.generate(self.root,'b',dry_run=True)
        self.assertEqual(result['targets']['queries'], 300)
        self.assertFalse((self.root/'data/exp_b/generated').exists())
        a_directory = self.root/'data/exp_a/generated'
        rows = a.read_jsonl(a_directory/'facets_silver.jsonl')[:-1]
        notes = a.read_jsonl(a_directory/'annotation_metadata.jsonl')[:-1]
        a.write_jsonl(a_directory/'facets_silver.jsonl',rows)
        a.write_jsonl(a_directory/'annotation_metadata.jsonl',notes)
        manifest = json.loads((a_directory/'manifest.json').read_text(encoding='utf-8'))
        manifest.update(count=399,status='partial',missing_ids=['P000400'],coverage={f:399 for f in a.FACET_NAMES})
        manifest['files'] = {name:sha256(a_directory/name) for name in manifest['files']}
        write_json(a_directory/'manifest.json',manifest)
        with self.assertRaisesRegex(ValueError,'Only|partial'):
            self.build('b')
        self.assertFalse((self.root/'data/exp_b/generated').exists())

    def test_manifest_cannot_omit_an_input_or_output_checksum(self):
        self.build('b')
        path = self.root/'data/exp_b/generated/manifest.json'
        manifest = json.loads(path.read_text(encoding='utf-8'))
        manifest['input_hashes'].pop('data/processed/papers.jsonl')
        write_json(path,manifest)
        with self.assertRaisesRegex(ValueError,'input|hash'):
            validator.validate_experiment(self.root,'b')

    def test_observable_behavior_report_contains_history_only(self):
        for name in ('d', 'e'):
            self.build(name)
            directory = self.root / f'data/exp_{name}'
            report = json.loads((directory / 'generated/generation_report.json').read_text(encoding='utf-8'))
            history = a.read_jsonl(directory / 'generated/interactions_train.jsonl')
            future = a.read_jsonl(directory / 'ground_truth/interactions_test.jsonl')
            expected = dict(collections.Counter(row['interaction_type'] for row in history))
            self.assertEqual(report['behavior_counts'], expected)
            report['behavior_counts'] = dict(collections.Counter(row['interaction_type'] for row in history + future))
            write_json(directory / 'generated/generation_report.json', report)
            manifest = json.loads((directory / 'generated/manifest.json').read_text(encoding='utf-8'))
            manifest['files'][f'data/exp_{name}/generated/generation_report.json'] = sha256(directory / 'generated/generation_report.json')
            write_json(directory / 'generated/manifest.json', manifest)
            with self.assertRaisesRegex(ValueError, 'behavior|history'):
                validator.validate_experiment(self.root, name)

    def test_d_and_e_rebuilds_match_in_fresh_processes_with_different_hash_seed(self):
        child = ('import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); '
                 'from data.build_experiments import generate; generate(Path(sys.argv[2]),sys.argv[3])')
        for name in ('d','e'):
            manifest = self.build(name)
            before = {path:(self.root/path).read_bytes() for path in manifest['files']}
            environment = dict(os.environ, PYTHONHASHSEED='195')
            result = subprocess.run([sys.executable,'-B','-X','utf8','-c',child,
                                     str(PROJECT),str(self.root),name],
                                    env=environment,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(before,{path:(self.root/path).read_bytes() for path in before})


if __name__ == '__main__':
    unittest.main()
