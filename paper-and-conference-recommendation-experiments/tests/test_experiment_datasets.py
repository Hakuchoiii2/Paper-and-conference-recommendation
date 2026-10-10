"""Mock protocol 2.0: profile-before-behavior, real concept reuse and heldout session papers."""
import datetime as dt
import random
import sys
import unittest
from pathlib import Path
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
sys.path.insert(0,str(PROJECT / 'scripts'))
from data.exp_b.build_exp_b import build_b
from data.exp_c.build_exp_c import build_c
from data.exp_d.build_exp_d import build_d
from data.exp_e.build_exp_e import build_e
from data.experiment_common import FACETS,facet_index,profile_events,session_grade
import json

def test_facets():
    return {f'P{i+1:06}':dict(problem={f'p{i%4}'},task={f't{i%5}'},method={f'm{(i//4)%4}'},
                             dataset={f'd{i%3}'},contribution={f'c{i%7}'}) for i in range(400)}

def config(name):
    return json.loads((PROJECT / f'configs/exp_{name}.json').read_text(encoding='utf-8'))

class DatasetChecks(unittest.TestCase):
    def test_zero_weight_future_concepts_do_not_target_current_exposures(self):
        facets = {pid:{f:({concept} if f == 'problem' else set()) for f in FACETS}
                  for pid,concept in [('old-paper','old'),('future-paper','future')]}
        profile = {f:({'old':1,'future':0} if f == 'problem' else {}) for f in FACETS}
        importance = {f:int(f == 'problem') for f in FACETS}
        cfg = dict(config('c'),targeted_exposure_fraction=1,search_fraction=0,noise_std=0,
                   exposure_size=2)
        for seed in range(10):
            events,_,_ = profile_events(facets,facet_index(facets),'U1',profile,importance,
                                       [dt.datetime(2026,1,1,tzinfo=dt.timezone.utc)],cfg,
                                       random.Random(seed),'S1')
            self.assertEqual(events[0]['paper_id'],'old-paper')

    def test_b_has_fixed_multi_facet_labels_and_anchor_disjoint_splits(self):
        observed,truth,report = build_b(test_facets(),config('b'),random.Random(42))
        self.assertEqual(len(observed['retrieval_queries.jsonl']),300)
        self.assertEqual(len(truth['retrieval_labels.jsonl']),30000)
        self.assertEqual(report['shortfall'],0)
        anchors = {}
        for q in observed['retrieval_queries.jsonl']:
            self.assertNotIn(q['query_paper_id'],q['candidate_ids'])
            self.assertNotIn('target_facet',q)
            side = next(s for s,ids in observed['splits.json'].items() if q['query_id'] in ids)
            self.assertEqual(anchors.setdefault(q['query_paper_id'],side),side)
        self.assertEqual((observed,truth,report),build_b(test_facets(),config('b'),random.Random(42)))

    def test_c_owns_users_and_has_search_exposure_and_hidden_importance(self):
        cfg = dict(config('c'),num_users=4,events_per_user=10,history_events_per_user=6,search_fraction=1)
        observed,truth,report = build_c(test_facets(),cfg,random.Random(42))
        self.assertEqual(len(observed['interactions_train.jsonl']),24)
        self.assertEqual(len(truth['interactions_test.jsonl']),16)
        self.assertEqual(len(observed['search_events.jsonl']),24)
        for row in truth['latent_user_profiles.jsonl']:
            self.assertAlmostEqual(sum(row['facet_importance'].values()),1)
        for case in observed['cases.jsonl']:
            self.assertTrue(all(r['timestamp'] < case['cutoff'] for r in observed['search_events.jsonl']
                                if r['user_id'] == case['user_id']))
        self.assertTrue(all(set(u) == {'user_id'} for u in observed['users.jsonl']))
        self.assertEqual((observed,truth,report),build_c(test_facets(),cfg,random.Random(42)))

    def test_d_hides_direction_and_keeps_observation_papers_out_of_holdout(self):
        users = [dict(user_id=f'U{i+1:04}') for i in range(4)]
        cfg = dict(config('d'),sessions_per_user=3,candidates_per_case=10)
        observed,truth,report = build_d(test_facets(),users,cfg,random.Random(42))
        self.assertEqual(report['shortfall'],0)
        self.assertEqual(len(observed['sessions.jsonl']),12)
        self.assertIn('problem',{r['focus_facet'] for r in truth['session_intents.jsonl']})
        self.assertEqual({r['query_mode'] for r in truth['session_intents.jsonl']},{'clear','ambiguous','none'})
        self.assertEqual({r['directions'][r['focus_facet']] for r in truth['session_intents.jsonl']},
                         {'similar','different'})
        cases = {r['case_id']:r for r in observed['sessions.jsonl']}
        for case in cases.values():
            self.assertFalse(set(case) & {'directions','facet_importance','query_mode','focus_facet'})
        for x in observed['exposures.jsonl']:
            self.assertFalse(set(x['paper_ids']) & set(cases[x['session_id']]['candidate_ids']))
        self.assertEqual((observed,truth,report),build_d(test_facets(),users,cfg,random.Random(42)))

    def test_e_rolling_cutoffs_and_stable_profiles(self):
        users = [dict(user_id=f'U{i+1:04}') for i in range(4)]
        cfg = dict(config('e'),events_per_user_per_period=4,search_fraction=1)
        observed,truth,report = build_e(test_facets(),users,cfg,random.Random(42))
        self.assertEqual(len(observed['cases.jsonl']),12)
        self.assertEqual(len(observed['interactions_train.jsonl']),48)
        self.assertEqual(len(truth['interactions_test.jsonl']),48)
        self.assertEqual(report['actual_events'],64)
        profiles = {(r['user_id'],r['period']):r for r in truth['temporal_profiles.jsonl']}
        for user,group in truth['period_metadata.json']['groups'].items():
            if group == 'stable':
                self.assertEqual(profiles[user,1]['latent_preferences'],profiles[user,4]['latent_preferences'])
            else:
                self.assertNotEqual(profiles[user,1]['latent_preferences'],profiles[user,3]['latent_preferences'])
        self.assertEqual({r['period'] for r in observed['cases.jsonl']},{2,3,4})

    def test_missing_facet_never_becomes_a_different_match(self):
        q = {f:{f} for f in FACETS}
        p = dict(q,method=set())
        self.assertEqual(session_grade(q,p,'method','different'),0)

if __name__ == '__main__':
    unittest.main()
