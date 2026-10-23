"""Exploratory active-facet prediction; no labels, scores, pool or parameters."""


def active_directions(context, estimated_directions, force_similar=False):
    """Mask only when public estimator outputs identify a unique active focus.

    Unknown means insufficient evidence. Ignore means predicted out of scope.
    The distinction changes effective active weights in the unchanged scorer.
    """
    active = [f for f, direction in estimated_directions.items()
              if f != context and direction in ('similar', 'different')]
    result = dict(estimated_directions)
    if len(active) != 1:
        return result
    focus = active[0]
    for facet in result:
        if facet not in (context, focus):
            result[facet] = 'ignore'
    if force_similar:
        result[focus] = 'similar'
    return result
