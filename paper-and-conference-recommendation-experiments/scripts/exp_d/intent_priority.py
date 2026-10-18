"""Training-free D rerankers. Public interface accepts no hidden intent or labels."""
from baseline_common import intent_scores, ranked


def observed_focus(context, directions, confidence):
    """Use a unique strongest observed non-context direction; abstain on ties."""
    eligible = [(confidence.get(f, 0.0), f) for f, d in directions.items()
                if f != context and d in ('similar', 'different') and confidence.get(f, 0) > 0]
    if not eligible:
        return None
    best = max(value for value, _ in eligible)
    winners = [f for value, f in eligible if value == best]
    return winners[0] if len(winners) == 1 else None


def rerank(case, facets, vectors, baseline, policy):
    """Transform one public direction baseline prediction, without fitting parameters.

    priority: predicted-intent tiers, then the unchanged baseline score within tiers.
    active: retain C weights only on context and the predicted focus; renormalize.
    Missing evidence or tied focus confidence returns the exact baseline ranking.
    """
    if policy not in ('priority', 'active'):
        raise ValueError('Unknown reranking policy')
    base_model, separator, arm = baseline['model'].partition('__')
    if base_model not in ('direction_behavior', 'direction_search'):
        raise ValueError('Only public direction predictions can be reranked')
    model = 'intent_' + policy + '_' + base_model.removeprefix('direction_')
    if separator:
        model += '__' + arm
    directions = dict(baseline['directions'])
    confidence = dict(baseline['direction_confidence'])
    weights = dict(baseline['facet_importance'])
    context = case['context_facet']
    focus = observed_focus(context, directions, confidence)
    original_scores = {r['paper_id']: r['score'] for r in baseline['ranking']}
    if set(original_scores) != set(case['candidate_ids']):
        raise ValueError('Baseline pool differs from session candidates')
    scores = original_scores
    fallback = focus is None
    if focus is not None and policy == 'active':
        total = weights.get(context, 0) + weights.get(focus, 0)
        if total <= 0:
            fallback = True
        else:
            weights = {f: weights[f] / total if f in (context, focus) else 0.0 for f in weights}
            scores = intent_scores(case, weights, directions, vectors)
    elif focus is not None:
        anchor = facets[case['query_paper_id']]
        low, high = min(original_scores.values()), max(original_scores.values())
        scores = {}
        for pid in case['candidate_ids']:
            candidate = facets[pid]
            complete = all(anchor[f] and candidate[f] for f in (context, focus))
            related = complete and bool(anchor[context] & candidate[context])
            overlap = bool(anchor[focus] & candidate[focus])
            satisfies = related and overlap == (directions[focus] == 'similar')
            tier = 2 if satisfies else 1 if related else 0
            # Bounded secondary key preserves baseline order without crossing tiers.
            tie = (original_scores[pid] - low) / (high - low) if high > low else 0.0
            scores[pid] = 2.0 * tier + tie
    row = ranked(case, model, scores)
    row.update(directions=directions, direction_confidence=confidence,
               facet_importance=weights, predicted_focus=focus,
               rerank_policy=policy, fallback_to_baseline=fallback,
               training='none')
    return row
