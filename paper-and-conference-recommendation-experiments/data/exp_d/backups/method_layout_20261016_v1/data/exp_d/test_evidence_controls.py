import copy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'scripts/exp_d'),str(ROOT/'data/exp_d')]
from baseline_common import facet_vectors,intent_scores,ranked
from experiment_io import FACETS
from intent_priority import observed_focus,rerank
from evidence_controls import anchor_split,select_panel,shuffle_actions,direction_controls


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.facets={pid:{f:{f+' shared'} for f in FACETS} for pid in ('A','S','D')}
        self.facets['D']['method']={'alternative'}
        self.vectors=facet_vectors(self.facets)
        self.case=dict(case_id='C',query_paper_id='A',context_facet='problem',candidate_ids=['S','D'])
        d=dict.fromkeys(FACETS,'unknown');d.update(problem='similar',method='different')
        w=dict.fromkeys(FACETS,.2)
        self.base=ranked(self.case,'direction_behavior',intent_scores(self.case,w,d,self.vectors))
        self.base.update(directions=d,facet_importance=w,direction_confidence=dict(problem=1.,method=.8))
        self.api=dict(observed_focus=observed_focus,intent_scores=intent_scores,ranked=ranked,rerank=rerank)

    def controls(self,base=None):
        return direction_controls(self.case,self.facets,self.vectors,base or self.base,self.api)

    def test_strict_predicted_is_original_and_only_focus_direction_changes(self):
        controls=self.controls();original=copy.deepcopy(self.base)
        for r in controls:
            self.assertEqual(r['facet_importance'],original['facet_importance'])
            self.assertEqual(r['predicted_focus'],'method')
            self.assertEqual(r['directions']['problem'],'similar')
            for f in FACETS:
                if f!='method':self.assertEqual(r['directions'][f],original['directions'][f])
        self.assertEqual(controls[0]['ranking'],original['ranking'])
        self.assertEqual(self.base,original)

    def test_m0_tie_break_has_no_original_direction_score_leak(self):
        changed=copy.deepcopy(self.base)
        changed['ranking']=list(reversed(changed['ranking']))
        for r in changed['ranking']:r['score']=-r['score']
        first=[r['ranking'] for r in self.controls() if r['family']=='m0']
        second=[r['ranking'] for r in self.controls(changed) if r['family']=='m0']
        self.assertEqual(first,second)

    def test_unknown_focus_is_identical_fallback_in_all_arms(self):
        self.base['directions']['method']='unknown'
        for row in self.controls():
            self.assertTrue(row['fallback_to_baseline'])
            self.assertEqual(row['ranking'],self.base['ranking'])

    def test_shuffle_preserves_metadata_and_action_counts(self):
        events=[dict(session_id=s,paper_id=str(i),exposure_id='E',timestamp=i,interaction_type=a)
                for s in ('one','two') for i,a in enumerate(('like','view','save','dislike'))]
        old=copy.deepcopy(events);shuffled=shuffle_actions(events,3)
        self.assertEqual(shuffled,shuffle_actions(events,3));self.assertEqual(events,old)
        for a,b in zip(events,shuffled):
            self.assertEqual({k:v for k,v in a.items() if k!='interaction_type'},
                             {k:v for k,v in b.items() if k!='interaction_type'})
        for session in ('one','two'):
            self.assertEqual(sorted(r['interaction_type'] for r in events if r['session_id']==session),
                             sorted(r['interaction_type'] for r in shuffled if r['session_id']==session))

    def test_split_and_panel_use_only_public_case_fields(self):
        cases=[dict(case_id=f'{a}-{i}',query_paper_id=str(a)) for a in range(20) for i in range(5)]
        self.assertEqual(anchor_split(cases),anchor_split(list(reversed(cases))))
        panel=select_panel(cases)
        self.assertEqual(len(panel),60)
        self.assertEqual(panel,select_panel(list(reversed(cases))))
        split=anchor_split(cases)
        self.assertEqual(set(split.values()),{'development','validation','audit'})


if __name__=='__main__':unittest.main()
