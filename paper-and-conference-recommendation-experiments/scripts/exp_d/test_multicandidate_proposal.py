"""Protocol checks for the nested-pool intervention, including metric limitations."""
import copy
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT/'scripts'), str(PROJECT), str(PROJECT/'data/exp_d'),
               str(PROJECT/'scripts/exp_d')]
from experiment_io import FACETS
from data.experiment_common import session_grade, timestamp
from baseline_common import facet_vectors, ranked, ranking_metrics
from validate_experiments import check_d
from build_contrast_sessions import build
from build_multicandidate_sessions import expand
from proposal_ranker import predict
from run_multicandidate_proposal import verify_public_replay, verify_direction_arms


class MultiCandidateTests(unittest.TestCase):
    def setUp(self):
        self.ids = ['A', 'S'] + [f'D{i}' for i in range(7)] + [f'O{i}' for i in range(18)]
        self.facets = {pid: {f: {f+' shared'} for f in FACETS} for pid in self.ids}
        for pid in [f'D{i}' for i in range(7)]:
            self.facets[pid]['method'] = {'alternative '+pid}
        for pid in [f'O{i}' for i in range(18)]:
            self.facets[pid]['problem'] = {'outside'}
        self.design = dict(anchor='A', context='problem', focus='method', same=['S'],
                           different=[f'D{i}' for i in range(7)], outside=[f'O{i}' for i in range(18)])
        self.api = dict(FACETS=FACETS, session_grade=session_grade, timestamp=timestamp)
        self.users = [dict(user_id=f'U{i}') for i in range(3)]

    def original(self, different=7):
        design = copy.deepcopy(self.design)
        design['different'] = design['different'][:different]
        cases, truth, labels, queries, pairs = build([design], self.facets, self.users, self.api)
        return design, cases, truth, labels, queries, pairs

    def test_nested_pools_preserve_episodes_and_deterministic_labels(self):
        d, cases, truth, labels, queries, _ = self.original()
        before = copy.deepcopy((cases, truth, d, self.facets))
        result = expand(cases, truth, [d], self.facets, self.api)
        self.assertEqual(result, expand(cases, truth, [d], self.facets, self.api))
        self.assertEqual(before, (cases, truth, d, self.facets))
        expanded, new_labels, metadata = result
        self.assertTrue(all(c['candidate_ids'] == expanded[0]['candidate_ids'] for c in expanded))
        old_same_diff = set(cases[0]['candidate_ids']) & (set(d['same']) | set(d['different']))
        for original, new, m in zip(cases, expanded, metadata):
            self.assertEqual({k:v for k,v in original.items() if k!='candidate_ids'},
                             {k:v for k,v in new.items() if k!='candidate_ids'})
            self.assertEqual(len(set(new['candidate_ids'])), 20)
            self.assertTrue(old_same_diff <= set(new['candidate_ids']))
            self.assertEqual(len(m['added_ids']), 4)
            self.assertEqual((m['same_count'], m['different_count'], m['outside_count']), (1, 5, 14))
        by_case = {c['case_id']:c for c in expanded}
        for t in truth:
            grades = [r['relevance'] for r in new_labels if r['case_id']==t['case_id']]
            if t['directions']['method']=='different':
                self.assertEqual((grades.count(2), grades.count(1), grades.count(0)), (5, 1, 14))
            else:
                self.assertEqual((grades.count(2), grades.count(1), grades.count(0)), (1, 5, 14))
        check_d({'sessions.jsonl':expanded, 'search_events.jsonl':queries,
                 'exposures.jsonl':[], 'interactions_train.jsonl':[]},
                {'session_intents.jsonl':truth, 'intent_labels.jsonl':new_labels}, self.facets,
                dict(candidates_per_case=20, sessions_per_user=5),
                dict(shortfall=9, actual_cases=6, actual_pairs=120), self.users)

    def test_scarce_designs_retained_without_manufactured_candidates(self):
        for available, expected in ((1,1), (2,2), (7,5)):
            d, cases, truth, old_labels, _, _ = self.original(available)
            expanded, labels, metadata = expand(cases, truth, [d], self.facets, self.api)
            self.assertEqual(len(expanded), len(cases))
            self.assertTrue(all(m['different_count']==expected for m in metadata))
            self.assertTrue(all(set(c['candidate_ids']) <= set(self.facets) for c in expanded))
            if available==1:
                self.assertEqual(expanded, cases)
                self.assertEqual(labels, old_labels)

    def test_rejects_non_v1_pool_and_unpaired_input(self):
        d, cases, truth, _, _, _ = self.original()
        changed = copy.deepcopy(cases)
        changed[0]['candidate_ids'][0] = changed[0]['candidate_ids'][1]
        with self.assertRaises(ValueError):
            expand(changed, truth, [d], self.facets, self.api)
        changed = copy.deepcopy(cases)
        changed[1]['candidate_ids'] = list(reversed(changed[1]['candidate_ids']))
        with self.assertRaises(ValueError):
            expand(changed, truth, [d], self.facets, self.api)
        for cap in (0,6,True):
            with self.assertRaises(ValueError):
                expand(cases, truth, [d], self.facets, self.api, cap)

    def test_expanded_pool_does_not_remove_overlap_metric_ceiling(self):
        d, cases, truth, _, _, _ = self.original()
        cases, labels, _ = expand(cases, truth, [d], self.facets, self.api)
        case, intent = cases[1], truth[1]
        vectors = facet_vectors(self.facets)
        base = ranked(case, 'direction_behavior', {pid:0. for pid in case['candidate_ids']})
        directions = {f:'unknown' for f in FACETS}
        directions.update(problem='similar', method='different')
        base.update(directions=directions, direction_confidence=dict(problem=1., method=1.),
                    facet_importance=dict.fromkeys(FACETS, .2))
        arms = [predict(case, self.facets, vectors, base, arm) for arm in ('predicted','similar','flipped')]
        verify_direction_arms(arms, base)
        judged = {r['candidate_id']:r['relevance'] for r in labels if r['case_id']==case['case_id']}
        ranking = [r['paper_id'] for r in arms[0]['ranking']]
        self.assertEqual(ranking_metrics(ranking, judged, [10])['ndcg@10'], 1.)
        # All grade-2 orderings have the same judged gain: no within-grade preference labels.
        reversed_top = list(reversed(ranking[:5])) + ranking[5:]
        self.assertEqual(ranking_metrics(reversed_top, judged, [10])['ndcg@10'], 1.)
        always = [r['paper_id'] for r in arms[1]['ranking']]
        self.assertEqual(sum(judged[p]==2 for p in ranking[:5])/5, 1.)
        self.assertEqual(sum(judged[p]==2 for p in always[:5])/5, .8)
        base['directions']['method'] = 'unknown'
        fallback = [predict(case, self.facets, vectors, base, arm) for arm in ('predicted','similar','flipped')]
        verify_direction_arms(fallback, base)

    def test_replay_guard_detects_profile_or_retained_score_changes(self):
        d, cases, _, _, _, _ = self.original()
        records = []
        for model in ('fixed_similar', 'profile_similar', 'direction_behavior', 'direction_search'):
            row = ranked(cases[0], model, {pid:0. for pid in cases[0]['candidate_ids']})
            row.update(directions=dict.fromkeys(FACETS, 'similar'),
                       direction_confidence=dict.fromkeys(FACETS, 1.), facet_importance=dict.fromkeys(FACETS, .2))
            records.append(row)
        verify_public_replay(records, records, cases[:1])
        for field in ('facet_importance', 'directions', 'ranking'):
            corrupted = copy.deepcopy(records)
            if field=='facet_importance':
                corrupted[0][field]['method'] = .9
            elif field=='directions':
                corrupted[0][field]['method'] = 'different'
            else:
                corrupted[0][field][0]['score'] = .4
            with self.assertRaises(ValueError):
                verify_public_replay(corrupted, records, cases[:1])


if __name__ == '__main__':
    unittest.main()
