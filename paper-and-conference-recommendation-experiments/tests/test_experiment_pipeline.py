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
        for name in ('exp_b.json','exp_c.json','exp_d.json','exp_e.json'):
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

    def small_configs(self):
        changes = dict(b=dict(num_queries=20,candidates_per_query=10),
                       c=dict(num_users=4,events_per_user=10,history_events_per_user=6,search_fraction=1),
                       d=dict(sessions_per_user=3,candidates_per_case=10),
                       e=dict(events_per_user_per_period=4,search_fraction=1))
        for name,updates in changes.items():
            path = self.root / f'configs/exp_{name}.json'
            cfg = json.loads(path.read_text(encoding='utf-8'))
            cfg.update(updates)
            write_json(path,cfg)

    def test_files_validate_and_rebuild_identically_in_order(self):
        self.small_configs()
        for name in ('b','c','d','e'):
            manifest = self.build(name)
            self.assertEqual(manifest['status'],'complete')
            self.assertEqual(manifest['contract_version'],'2.0')
            validator.validate_experiment(self.root,name)
            before = {n:(self.root/n).read_bytes() for n in manifest['files']}
            self.assertEqual(manifest,self.build(name))
            self.assertEqual(before,{n:(self.root/n).read_bytes() for n in before})

    def test_d_and_e_require_c_handoff(self):
        self.small_configs()
        for name in ('d','e'):
            with self.assertRaises(FileNotFoundError):
                self.build(name)
        self.build('c')
        self.build('d')
        self.build('e')

    def test_label_and_observable_truth_corruption_rejected_with_new_hashes(self):
        self.small_configs()
        self.build('b')
        self.corrupt('b','ground_truth/retrieval_labels.jsonl',lambda rows:rows[0].update(relevance=9))
        with self.assertRaisesRegex(ValueError,'label'):
            validator.validate_experiment(self.root,'b')
        self.build('c'); self.build('d')
        self.corrupt('d','generated/sessions.jsonl',lambda rows:rows[0].update(directions={'method':'different'}))
        with self.assertRaisesRegex(ValueError,'schema'):
            validator.validate_experiment(self.root,'d')
        self.build('d')
        self.corrupt('d','ground_truth/intent_labels.jsonl',lambda rows:rows[0].update(relevance=9))
        with self.assertRaisesRegex(ValueError,'label'):
            validator.validate_experiment(self.root,'d')

    def test_search_cutoff_exposure_membership_and_query_parent_are_validated(self):
        self.small_configs(); self.build('c')
        self.corrupt('c','generated/search_events.jsonl',lambda rows:rows[0].update(timestamp='2027-01-01T00:00:00Z'))
        with self.assertRaisesRegex(ValueError,'order|time|history'):
            validator.validate_experiment(self.root,'c')
        self.build('c')
        self.corrupt('c','generated/interactions_train.jsonl',lambda rows:rows[0].update(paper_id='P999999'))
        with self.assertRaisesRegex(ValueError,'paper'):
            validator.validate_experiment(self.root,'c')
        self.build('c')
        self.corrupt('c','generated/search_events.jsonl',lambda rows:rows[1].update(parent_query_id='missing'))
        with self.assertRaisesRegex(ValueError,'parent'):
            validator.validate_experiment(self.root,'c')
        self.build('c')
        self.corrupt('c','generated/search_events.jsonl',lambda rows:rows[1].update(query_id=rows[0]['query_id']))
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            validator.validate_experiment(self.root,'c')

    def test_foreign_users_and_temporal_importance_corruption_rejected(self):
        self.small_configs(); self.build('c'); self.build('e')
        self.corrupt('e','generated/interactions_train.jsonl',lambda rows:rows[0].update(user_id='U9999'))
        with self.assertRaisesRegex(ValueError,'user'):
            validator.validate_experiment(self.root,'e')
        self.build('e')
        def mutate(rows):
            r = next(r for r in rows if r['period'] == 2)
            r['facet_importance']['problem'] += .05
            r['facet_importance']['method'] -= .05
        self.corrupt('e','ground_truth/temporal_profiles.jsonl',mutate)
        with self.assertRaisesRegex(ValueError,'importance'):
            validator.validate_experiment(self.root,'e')

    def test_missing_hash_and_legacy_outputs_are_preserved(self):
        self.small_configs(); self.build('b')
        path = self.root / 'data/exp_b/generated/manifest.json'
        manifest = json.loads(path.read_text(encoding='utf-8'))
        manifest['input_hashes'].pop('data/processed/papers.jsonl')
        write_json(path,manifest)
        with self.assertRaisesRegex(ValueError,'hash'):
            validator.validate_experiment(self.root,'b')
        self.build('b')
        manifest = json.loads(path.read_text(encoding='utf-8'))
        manifest['contract_version'] = '1.0'
        write_json(path,manifest)
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError,'Legacy'):
            self.build('b')
        self.assertEqual(before,path.read_bytes())

    def test_history_report_and_incomplete_a_are_rejected(self):
        self.small_configs(); self.build('c')
        directory = self.root / 'data/exp_c'
        report_path = directory / 'generated/generation_report.json'
        report = json.loads(report_path.read_text(encoding='utf-8'))
        report['behavior_counts']['click'] = -1
        write_json(report_path,report)
        manifest_path = directory / 'generated/manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['files'][report_path.relative_to(self.root).as_posix()] = sha256(report_path)
        write_json(manifest_path,manifest)
        with self.assertRaisesRegex(ValueError,'history'):
            validator.validate_experiment(self.root,'c')
        result = builder.generate(self.root,'b',dry_run=True)
        self.assertEqual(result['targets']['queries'],20)
        self.assertFalse((self.root / 'data/exp_b/generated').exists())
        a_path = self.root / 'data/exp_a/generated/manifest.json'
        value = json.loads(a_path.read_text(encoding='utf-8'))
        value['status'] = 'partial'
        write_json(a_path,value)
        with self.assertRaises(ValueError):
            self.build('b')

    def test_fresh_processes_ignore_python_hash_seed(self):
        self.small_configs(); self.build('c')
        child = ('import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); '
                 'from data.build_experiments import generate; generate(Path(sys.argv[2]),sys.argv[3])')
        for name in ('c','d','e'):
            manifest = self.build(name)
            before = {p:(self.root/p).read_bytes() for p in manifest['files']}
            result = subprocess.run([sys.executable,'-B','-X','utf8','-c',child,str(PROJECT),str(self.root),name],
                                    env=dict(os.environ,PYTHONHASHSEED='195'),capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(before,{p:(self.root/p).read_bytes() for p in before})

if __name__ == '__main__':
    unittest.main()
