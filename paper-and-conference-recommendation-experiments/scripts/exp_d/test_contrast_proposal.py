import copy
from pathlib import Path
import sys
import unittest

PROJECT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(PROJECT/'scripts'),str(PROJECT),str(PROJECT/'data/exp_d'),str(PROJECT/'scripts/exp_d')]
from baseline_common import facet_vectors,ranked
from experiment_io import FACETS
from data.experiment_common import session_grade,timestamp
from validate_experiments import check_d
from build_contrast_sessions import build
from proposal_ranker import predict


class ContrastTests(unittest.TestCase):
    def setUp(self):
        self.facets={pid:{f:{f+' shared'} for f in FACETS} for pid in ['A','S','D']+[f'O{i}' for i in range(18)]}
        self.facets['D']['method']={'alternative'}
        for i in range(18):self.facets[f'O{i}']['problem']={'outside'}
        self.design=dict(anchor='A',context='problem',focus='method',same=['S'],different=['D'],outside=[f'O{i}' for i in range(18)])
        self.users=[dict(user_id=f'U{i}') for i in range(3)]
        self.api=dict(FACETS=FACETS,session_grade=session_grade,timestamp=timestamp)

    def test_paired_pools_labels_users_cutoff_and_contract(self):
        cases,truth,labels,queries,pairs=build([self.design],self.facets,self.users,self.api)
        self.assertEqual(len(cases),6)
        self.assertTrue(all(len(set(c['candidate_ids']))==20 for c in cases))
        for left,right in zip(cases[::2],cases[1::2]):
            for key in ('candidate_ids','query_paper_id','context_facet','user_id','cutoff'):
                self.assertEqual(left[key],right[key])
            lt={r['candidate_id']:r['relevance'] for r in labels if r['case_id']==left['case_id']}
            rt={r['candidate_id']:r['relevance'] for r in labels if r['case_id']==right['case_id']}
            self.assertEqual((lt['S'],lt['D'],rt['S'],rt['D']),(2,1,1,2))
        config=dict(candidates_per_case=20,sessions_per_user=5)
        check_d({'sessions.jsonl':cases,'search_events.jsonl':queries,'exposures.jsonl':[],'interactions_train.jsonl':[]},
                {'session_intents.jsonl':truth,'intent_labels.jsonl':labels},self.facets,config,
                dict(shortfall=9,actual_cases=6,actual_pairs=120),self.users)

    def test_proposal_direction_control_is_only_effective_change(self):
        case=dict(case_id='C',query_paper_id='A',context_facet='problem',candidate_ids=['S','D'])
        base=ranked(case,'direction_search',{'S':.9,'D':.1})
        d=dict.fromkeys(FACETS,'unknown');d.update(problem='similar',method='different')
        base.update(directions=d,direction_confidence=dict(problem=1.,method=.8),facet_importance=dict.fromkeys(FACETS,.2))
        old=copy.deepcopy(base);vectors=facet_vectors(self.facets)
        pred=predict(case,self.facets,vectors,base);similar=predict(case,self.facets,vectors,base,'similar')
        self.assertEqual(pred['ranking'][0]['paper_id'],'D');self.assertEqual(similar['ranking'][0]['paper_id'],'S')
        self.assertEqual(pred['facet_importance'],similar['facet_importance'])
        self.assertEqual(pred['predicted_focus'],similar['predicted_focus'])
        self.assertEqual(base,old)
        base['directions']['method']='unknown'
        self.assertEqual(predict(case,self.facets,vectors,base)['ranking'],base['ranking'])


if __name__=='__main__':unittest.main()
