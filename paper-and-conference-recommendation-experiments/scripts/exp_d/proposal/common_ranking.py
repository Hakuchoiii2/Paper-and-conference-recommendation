"""One explicit facet-activation policy shared by every competing estimator."""
from data_io import FACETS


def ranking_directions(context, raw):
    active = [f for f in FACETS if f != context and raw.get(f) in ('similar', 'different')]
    if len(active) != 1:
        # A declared prior fallback; never reinterpret unknown as a prediction.
        return dict.fromkeys(FACETS, 'similar'), 'profile_similar_fallback'
    result = dict.fromkeys(FACETS, 'ignore')
    result[context] = 'similar'
    result[active[0]] = raw[active[0]]
    return result, 'unique_inferred_focus'
