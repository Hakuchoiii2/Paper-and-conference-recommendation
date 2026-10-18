"""Evidence-guided facet reranking: explicit constraints, C-profile tie key, abstention.

This is a rule-based proposal adapted to the overlap benchmark, not a learned semantic model.
No hidden labels, true focus or true weights are accepted by the public interface.
"""
from baseline_common import dot,ranked
from intent_priority import observed_focus


def predict(case,facets,vectors,base,arm='predicted'):
    if arm not in ('predicted','similar','flipped'):raise ValueError('Unknown arm')
    focus=observed_focus(case['context_facet'],base['directions'],base['direction_confidence'])
    directions=dict(base['directions']);weights=dict(base['facet_importance'])
    context=case['context_facet'];channel=base['model'].removeprefix('direction_')
    if channel not in ('behavior','search'):raise ValueError('Public direction baseline required')
    total=weights.get(context,0)+weights.get(focus,0) if focus else 0
    fallback=focus is None or total<=0
    if fallback:
        scores={r['paper_id']:r['score'] for r in base['ranking']}
    else:
        if arm=='similar':directions[focus]='similar'
        if arm=='flipped':directions[focus]='different' if directions[focus]=='similar' else 'similar'
        weights={f:w/total if f in (context,focus) else 0. for f,w in weights.items()}
        anchor=case['query_paper_id'];scores={}
        for pid in case['candidate_ids']:
            complete=all(facets[anchor][f] and facets[pid][f] for f in (context,focus))
            related=complete and bool(facets[anchor][context]&facets[pid][context])
            # Same gate and missingness in all three proposal direction arms.
            if not related:
                scores[pid]=-1.;continue
            matches=bool(facets[anchor][focus]&facets[pid][focus])==(directions[focus]=='similar')
            # Identical direction-independent secondary score in all arms, weighted by C.
            secondary=sum(weights[f]*max(0.,min(1.,dot(vectors[anchor,f],vectors[pid,f]))) for f in (context,focus))
            scores[pid]=2.*int(matches)+secondary
    row=ranked(case,f'proposal_{channel}_{arm}',scores)
    row.update(directions=directions,facet_importance=weights,direction_confidence=dict(base['direction_confidence']),
               predicted_focus=focus,fallback_to_baseline=fallback,training='none',
               policy='context-and-active-evidence gate, direction priority, direction-neutral C tie key')
    return row
