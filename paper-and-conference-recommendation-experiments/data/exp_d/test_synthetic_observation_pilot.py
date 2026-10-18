"""Focused overlay contract tests; python -B -m unittest discover -s data/exp_d -p test_synthetic_observation_pilot.py."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ws = HERE / 'workspace' if (HERE / 'workspace').exists() else (HERE / 'workspace_baseline_20261016_v1' if (HERE / 'workspace_baseline_20261016_v1').exists() else HERE.parents[1])
sys.path[:0] = [str(ws / 'scripts'), str(ws)]
from experiment_io import FACETS
from data.experiment_common import behavior, session_grade, timestamp
from validate_experiments import check_d
from validate_all import validate_time

spec = importlib.util.spec_from_file_location('synthetic_pilot', HERE / 'run_synthetic_observation_pilot.py')
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.real = {pid: {f: {f + '_shared'} for f in FACETS} for pid in ('A', 'B', 'C', 'D')}
        self.real['C']['method'] = {'alternate_one'}
        self.real['D']['method'] = {'alternate_two'}
        self.cases = [dict(case_id='T1', user_id='U0001', query_paper_id='A', context_facet='problem',
                           candidate_ids=['B', 'C'], cutoff='2026-03-01T00:00:40Z')]
        self.truth = {'T1': dict(case_id='T1', focus_facet='method', query_mode='none',
            directions={f: 'similar' if f == 'problem' else 'different' if f == 'method' else 'ignore' for f in FACETS},
            facet_importance={f: .6 if f == 'problem' else .4 if f == 'method' else 0. for f in FACETS})}
        self.labels = [dict(case_id='T1', candidate_id='B', relevance=1),
                       dict(case_id='T1', candidate_id='C', relevance=2)]
        self.config = dict(sessions_per_user=1, candidates_per_case=2,
                           interaction_thresholds=[-.25, .05, .2, .4])
        self.api = dict(FACETS=FACETS, check_d=check_d, validate_time=validate_time,
                        behavior=behavior, session_grade=session_grade, timestamp=timestamp)
        self.overlay = pilot.make_observations(self.cases, self.truth, self.real, [], self.config,
                                               42, 0., 2, self.api)

    def validate(self, overlay=None, labels=None):
        pilot.validate_overlay(self.cases, self.truth, labels or self.labels, [], self.real,
            *(overlay or self.overlay), [dict(user_id='U0001')], self.config, 2, self.api)

    def test_deterministic_separate_and_valid(self):
        self.validate()
        self.assertEqual(self.overlay, pilot.make_observations(self.cases, self.truth, self.real,
            [], self.config, 42, 0., 2, self.api))
        facets, provenance, exposures, events = self.overlay
        self.assertEqual(len(facets), 4)
        self.assertEqual(len(events), 4)
        self.assertTrue(all(p['synthetic'] for p in provenance))
        self.assertTrue(all(not {'directions', 'focus_facet', 'relevance', 'same_focus'} & set(r)
                            for r in exposures + events))

    def test_wrong_nonfocus_match_rejected(self):
        overlay = copy.deepcopy(self.overlay)
        pid = overlay[2][0]['paper_ids'][0]
        overlay[0][pid]['task'] = set()
        with self.assertRaises(ValueError):
            self.validate(overlay)

    def test_future_feedback_rejected(self):
        overlay = copy.deepcopy(self.overlay)
        overlay[3][-1]['timestamp'] = self.cases[0]['cutoff']
        with self.assertRaises(ValueError):
            self.validate(overlay)

    def test_corrupt_labels_rejected(self):
        labels = copy.deepcopy(self.labels)
        labels[0]['relevance'] = 2
        with self.assertRaises(ValueError):
            self.validate(labels=labels)

    def test_noisy_feedback_is_intent_conditioned(self):
        facets, _, _, events = self.overlay
        for row in events:
            same = bool(facets[row['paper_id']]['method'] & self.real['A']['method'])
            self.assertEqual(row['interaction_type'], 'click' if same else 'like')


if __name__ == '__main__':
    unittest.main()
