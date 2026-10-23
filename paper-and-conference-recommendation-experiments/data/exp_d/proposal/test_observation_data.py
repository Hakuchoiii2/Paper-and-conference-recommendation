"""Meaningful data-contract tests; no model or experiment runner is imported."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from prepare_source import FACETS, HERE, load_bundle, read_json, read_rows, sha, write_json, write_rows
from build_observation_data import assemble, build
from validate_observation_data import validate_dataset


def fixture(root):
    facets = {'P000001':{f:{f+' anchor'} for f in FACETS}}
    for i, focus in enumerate(FACETS[1:]):
        for side in range(2):
            pid = f'P{2+i*2+side:06d}'
            row = {f:set(v) for f,v in facets['P000001'].items()}
            row['problem'] = {'problem '+pid}
            if side:
                row[focus] = {focus+' alternate'}
            facets[pid] = row
    for i in range(50):
        pid = f'P{20+i:06d}'
        facets[pid] = {f:{f+' outside '+pid} for f in FACETS}
    papers = [dict(paper_id=p, title='Fixture '+p, abstract=(' '+p)*60,
                   year=2020, source='fixture', source_id=p, domain='information_technology',
                   scope_evidence=['unit test only, never production data']) for p in facets]
    write_rows(root / 'papers.jsonl', papers)
    write_rows(root / 'facets.jsonl', [dict(paper_id=p, **{f:sorted(v) for f,v in r.items()}) for p,r in facets.items()])
    histories = {'users.jsonl':[dict(user_id='U0001')],
                 'interactions_train.jsonl':[dict(user_id='U0001', paper_id='P000001', interaction_type='save',
                                                timestamp='2026-01-01T00:00:00Z',session_id='C1',exposure_id='C1X')],
                 'search_events.jsonl':[], 'exposures.jsonl':[]}
    for name, values in histories.items():
        write_rows(root / 'history' / name, values)
    files = {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file()}
    write_json(root / 'manifest.json', dict(protocol='d_source_v1', status='verified', fixture_only=True, files=files))
    config = read_json(HERE / 'observation_config.json')
    config.update(problem_designs=[dict(anchor='P000001',context='task')],
                  max_real_designs_per_focus=1, feedback_seeds=[42], noise_levels=[.2,.5])
    return config


def rehash_output(root):
    m = read_json(root / 'manifest.json')
    m['files'] = {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    write_json(root / 'manifest.json', m)


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp_parent = HERE / '.test-tmp'
        tmp_parent.mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(dir=tmp_parent)
        cls.root = Path(cls.temp.name).resolve()
        assert cls.root.is_relative_to(HERE)
        cls.source = cls.root / 'source'
        cls.config = fixture(cls.source)
        cls.config_path = cls.root / 'config.json'
        write_json(cls.config_path, cls.config)
        cls.dataset = cls.root / 'dataset'
        build(cls.source, cls.config_path, cls.dataset)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def corrupted(self, name):
        import shutil
        destination = self.root / name
        shutil.copytree(self.dataset, destination)
        return destination

    def test_full_contract_and_all_five_facets(self):
        result = validate_dataset(self.dataset)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['designs'], 5)
        self.assertEqual(result['sessions'], 30)
        self.assertEqual(result['synthetic_candidates'], 1)
        self.assertEqual(result['synthetic_observations'], 40)

    def test_reproducible_bytes(self):
        other = self.root / 'repeat'
        build(self.source, self.config_path, other)
        first, second = read_json(self.dataset/'manifest.json'),read_json(other/'manifest.json')
        self.assertEqual(first, second)

    def test_no_overwrite(self):
        with self.assertRaisesRegex(ValueError, 'already exists'):
            build(self.source, self.config_path, self.dataset)

    def test_dry_run_writes_nothing(self):
        output = self.root/'dry'
        build(self.source, self.config_path, output, dry_run=True)
        self.assertFalse(output.exists())

    def test_labels_recomputed_not_prediction_based(self):
        output = self.corrupted('wrong_label')
        path = output/'ground_truth/intent_labels.jsonl'
        rows = read_rows(path)
        rows[0]['relevance'] = (rows[0]['relevance']+1)%3
        write_rows(path, rows)
        rehash_output(output)
        with self.assertRaisesRegex(ValueError, 'Label disagrees'):
            validate_dataset(output)

    def test_no_hidden_fields_in_public_case(self):
        output = self.corrupted('leak')
        path = output/'generated/sessions.jsonl'
        rows = read_rows(path)
        rows[0]['focus_facet'] = 'problem'
        write_rows(path, rows)
        rehash_output(output)
        with self.assertRaisesRegex(ValueError, 'Hidden field'):
            validate_dataset(output)

    def test_no_fabricated_concepts(self):
        output = self.corrupted('fake')
        path = output/'catalog/facets.jsonl'
        rows = read_rows(path)
        next(r for r in rows if r['source_kind']=='synthetic')['problem']=['invented concept']
        write_rows(path, rows)
        rehash_output(output)
        with self.assertRaisesRegex(ValueError, 'Invented concept'):
            validate_dataset(output)

    def test_no_future_feedback(self):
        output = self.corrupted('future')
        path = output/'conditions/seed_42_noise_0.2/generated/interactions_train.jsonl'
        rows = read_rows(path)
        rows[0]['timestamp'] = '2027-01-01T00:00:00Z'
        write_rows(path, rows)
        rehash_output(output)
        with self.assertRaisesRegex(ValueError, 'Future/cross-case'):
            validate_dataset(output)

    def test_paired_pool_cannot_change(self):
        output = self.corrupted('pool')
        path = output/'generated/sessions.jsonl'
        rows = read_rows(path)
        rows[0]['candidate_ids'].reverse()
        write_rows(path, rows)
        rehash_output(output)
        with self.assertRaisesRegex(ValueError, 'Paired pool'):
            validate_dataset(output)

    def test_candidate_cannot_be_observation(self):
        output = self.corrupted('role')
        path = output/'ground_truth/designs.jsonl'
        rows = read_rows(path)
        rows[0]['observation_pairs'][0][0] = rows[0]['candidate_ids'][0]
        write_rows(path, rows)
        rehash_output(output)
        with self.assertRaisesRegex(ValueError, 'role overlap'):
            validate_dataset(output)

    def test_missing_facet_not_different(self):
        from build_observation_data import grade
        anchor = {f:{f+' a'} for f in FACETS}
        candidate = copy.deepcopy(anchor)
        candidate['problem'] = set()
        self.assertEqual(grade(anchor,candidate,'task','problem','different'),0)

    def test_noise_is_not_an_experiment_model(self):
        source = load_bundle(self.source)
        data = assemble(source,self.config)
        a,b = data['conditions']['seed_42_noise_0.2'],data['conditions']['seed_42_noise_0.5']
        self.assertEqual(a['exposures'],b['exposures'])
        self.assertNotEqual(a['interactions'],b['interactions'])
        self.assertEqual([r['gaussian_draw'] for r in a['reaction_truth']], [r['gaussian_draw'] for r in b['reaction_truth']])

    def test_outside_D_output_rejected(self):
        with self.assertRaisesRegex(ValueError, 'inside D'):
            build(self.source,self.config_path,HERE.parent/'not_allowed')

    def test_no_hidden_C_profiles_exported(self):
        self.assertEqual({p.name for p in (self.dataset/'history').iterdir()},
                         {'users.jsonl','interactions_train.jsonl','search_events.jsonl','exposures.jsonl'})

    def test_existing_real_sides_are_not_replaced(self):
        source = load_bundle(self.source)
        source['facets']['P000002']['problem'] = set(source['facets']['P000001']['problem'])
        data = assemble(source,self.config)
        design = next(d for d in data['designs'] if d['focus']=='problem')
        self.assertIsNone(design['synthetic_fill_side'])
        self.assertEqual(design['candidate_source_group'],'real_only')
        self.assertEqual(data['report']['synthetic_candidate_records'],0)

    def test_fill_missing_different_side(self):
        source = load_bundle(self.source)
        source['facets']['P000001']['dataset'] = {'special dataset'}
        source['facets']['P000002']['dataset'] = {'special dataset'}
        source['facets']['P000002']['problem'] = set(source['facets']['P000001']['problem'])
        config = copy.deepcopy(self.config)
        config['problem_designs'] = [dict(anchor='P000001',context='dataset')]
        data = assemble(source,config)
        design = next(d for d in data['designs'] if d['focus']=='problem')
        self.assertEqual(design['synthetic_fill_side'],'different')
        self.assertEqual(design['same_candidate_ids'],['P000002'])
        self.assertIn(design['different_candidate_ids'][0],data['synthetic'])

    def test_upstream_source_corruption_is_rejected(self):
        import shutil
        other = self.root/'tampered_source'
        shutil.copytree(self.source,other)
        path = other/'facets.jsonl'
        path.write_text(path.read_text(encoding='utf-8')+'\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Source bundle changed'):
            load_bundle(other)


if __name__ == '__main__':
    unittest.main()
