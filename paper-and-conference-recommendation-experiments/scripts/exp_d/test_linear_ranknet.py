"""Leakage contract, pairwise numerical gradient, and global anchor grouping."""
import sys
from pathlib import Path
import unittest
import numpy as np

PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'data/exp_d/workspace_baseline_20261016_v1/scripts'))
from experiment_io import FACETS
from baseline_common import facet_vectors
from linear_ranknet import features, fit, loss_gradient
from run_completion import split_anchors


class LinearRankNetTests(unittest.TestCase):
    def test_gradient(self):
        rng=np.random.default_rng(7)
        x=rng.normal(size=(9,4));w=np.ones(9)/9;t=rng.normal(size=4)
        _,analytic=loss_gradient(t,x,w,.01)
        numerical=[]
        for i in range(4):
            shift=np.eye(4)[i]*1e-6
            numerical.append((loss_gradient(t+shift,x,w,.01)[0]-loss_gradient(t-shift,x,w,.01)[0])/2e-6)
        np.testing.assert_allclose(analytic,numerical,rtol=1e-6,atol=1e-8)

    def test_pair_order_and_offset(self):
        x=np.array([[0.,1.],[1.,0.],[2.,0.]])
        a=fit([(x,[0,1,2])],.01)
        b=fit([(x[::-1]+5,[2,1,0])],.01)
        np.testing.assert_allclose(a['theta'],b['theta'],atol=1e-6)
        scores=((x-a['mean'])/a['scale'])@a['theta']
        self.assertTrue(scores[2]>scores[1]>scores[0])

    def test_features_ignore_hidden_fields(self):
        facets={p:{f:{p} for f in FACETS} for p in ('a','b')}
        case=dict(query_paper_id='a',context_facet=FACETS[0],candidate_ids=['b'])
        base=dict(facet_importance=dict.fromkeys(FACETS,.2),
                  directions=dict.fromkeys(FACETS,'unknown'),direction_confidence=dict.fromkeys(FACETS,0.))
        vectors=facet_vectors(facets)
        expected=features(case,facets,vectors,base)
        poisoned=dict(case,true_focus='secret',directions={'hidden':'different'},relevance=2,provenance={'x':1})
        np.testing.assert_array_equal(expected,features(poisoned,facets,vectors,dict(base,true_weights={'hidden':1})))
        self.assertEqual(expected.shape,(1,90))

    def test_global_anchor_groups(self):
        canonical=[dict(query_paper_id=f'a{i}') for i in range(30)]
        auxiliary=[dict(query_paper_id=f'a{i}') for i in range(8) for _ in range(6)]
        first=split_anchors(canonical,auxiliary)
        self.assertEqual(first,split_anchors(canonical[::-1],auxiliary[::-1]))
        self.assertEqual({s:sum(first[f'a{i}']==s for i in range(8)) for s in ('train','validation','test')},
                         dict(train=5,validation=1,test=2))


if __name__=='__main__':
    unittest.main()
