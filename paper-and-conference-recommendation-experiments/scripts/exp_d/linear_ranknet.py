"""Linear D adaptation of Burges et al. (2005), equations 1--3.

Pairwise logistic cross entropy is inherited; observable features, L2, train-only
standardization, session weighting and L-BFGS are choices for this experiment.
Public features/predict accept no relevance, hidden intent, or provenance.
"""
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from baseline_common import dot, ranked
from experiment_io import FACETS

TERMS = ('cosine', 'overlap', 'anchor_missing', 'candidate_missing', 'context',
         'C_weight', 'pred_similar', 'pred_different', 'pred_unknown', 'confidence',
         'context_cosine', 'context_overlap', 'C_cosine', 'C_overlap',
         'signed_conf_cosine', 'signed_conf_overlap',
         'context_overlap_signed_conf_cosine', 'context_overlap_signed_conf_overlap')
FEATURE_NAMES = [f'{f}:{t}' for f in FACETS for t in TERMS]


def features(case, facets, vectors, base):
    """90 observable features; IDs select records and never enter the vector.

    signed_conf = +confidence for predicted similar, -confidence for different,
    zero for unknown. Interactions enable a linear score to respond to intent.
    No hand-coded truth-based gate or proposal score is included.
    """
    a = case['query_paper_id']
    context = case['context_facet']
    result = []
    for pid in case['candidate_ids']:
        related = float(bool(facets[a][context] & facets[pid][context]))
        row = []
        for f in FACETS:
            sim = max(0., min(1., dot(vectors[a, f], vectors[pid, f])))
            overlap = float(bool(facets[a][f] & facets[pid][f]))
            ctx = float(f == context)
            w = base['facet_importance'][f]
            d = base['directions'][f]
            conf = base['direction_confidence'][f]
            sign = conf * (1 if d == 'similar' else -1 if d == 'different' else 0)
            row.extend((sim, overlap, float(not facets[a][f]), float(not facets[pid][f]),
                        ctx, w, float(d == 'similar'), float(d == 'different'),
                        float(d == 'unknown'), conf, ctx*sim, ctx*overlap,
                        w*sim, w*overlap, sign*sim, sign*overlap,
                        related*sign*sim, related*sign*overlap))
        result.append(row)
    return np.asarray(result, dtype=np.float64)


def loss_gradient(theta, differences, pair_weights, l2):
    margin = differences @ theta
    loss = float(pair_weights @ np.logaddexp(0., -margin) + .5*l2*(theta @ theta))
    grad = differences.T @ (-pair_weights * expit(-margin)) + l2*theta
    return loss, grad


def fit(train, l2):
    """train is [(features, relevance_targets)] only from registered train anchors.

    Use each unordered unequal-grade pair once, orient higher-grade first, omit
    ties. Equal total weight per episode/observation condition. All candidates
    enter train-only scaling. No validation/test labels enter this function.
    """
    all_x = np.concatenate([x for x, _ in train])
    mean, scale = all_x.mean(axis=0), all_x.std(axis=0)
    scale[scale < 1e-12] = 1.
    diffs, weights = [], []
    for x, y in train:
        z = (x-mean)/scale
        i, j = np.where(np.asarray(y)[:, None] > np.asarray(y)[None, :])
        if len(i):
            diffs.append(z[i]-z[j])
            weights.extend([1./(len(train)*len(i))]*len(i))
    if not diffs:
        raise ValueError('No unequal-grade training pairs')
    differences, pair_weights = np.concatenate(diffs), np.asarray(weights)
    result = minimize(loss_gradient, np.zeros(all_x.shape[1]),
                      args=(differences, pair_weights, l2), jac=True, method='L-BFGS-B',
                      options=dict(maxiter=400, ftol=1e-12, gtol=1e-7))
    if not result.success:
        raise ValueError('Optimizer did not converge: '+str(result.message))
    return dict(feature_names=FEATURE_NAMES, mean=mean.tolist(), scale=scale.tolist(),
                theta=result.x.tolist(), l2=l2, loss=float(result.fun),
                iterations=int(result.nit), convergence=str(result.message),
                train_instances=len(train), unequal_pairs=len(pair_weights))


def predict(case, base, x, model):
    scores = ((x-np.asarray(model['mean']))/np.asarray(model['scale'])) @ np.asarray(model['theta'])
    channel = base['model'].removeprefix('direction_')
    row = ranked(case, 'linear_ranknet_'+channel, dict(zip(case['candidate_ids'], scores.tolist())))
    row.update(directions=dict(base['directions']),
               direction_confidence=dict(base['direction_confidence']),
               facet_importance=dict(base['facet_importance']),
               training='pairwise relevance labels on registered train anchors only')
    return row
