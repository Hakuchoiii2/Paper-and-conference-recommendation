"""Exploratory ordinal likelihood, with fixed nuisance-strength marginalization.

Only public session evidence enters inference. This is a project adaptation,
not a reproduction or a claim of research novelty. No generator parameters.
"""
import math

from data_io import FACETS, time
from baseline_common import parse_search
from methods import empty, paired_evidence

DEFAULTS = dict(strengths=[.25, .75, 1.5], query_reliability=.8,
                minimum_pairs=2, posterior_minimum=.25, posterior_gap=.10)


def log_difference_probability(value, sign, strength):
    """Five ordered actions: triangular neutral difference, exponentially tilted.

    Equal-spacing of action ranks is an explicit modeling assumption. Ties have
    nonzero mass. strength=0 is the neutral distribution for an unrelated facet.
    """
    if value not in range(-4, 5):
        raise ValueError('Expected a difference of five ordinal action ranks')
    normalizer = sum((5-abs(d))*math.exp(strength*sign*d) for d in range(-4, 5))
    return math.log(5-abs(value)) + strength*sign*value - math.log(normalizer)


def ordinal_intent(evidence, facets, vocabulary, config=None):
    config = DEFAULTS if config is None else config
    case = evidence.case
    anchor = facets[case['query_paper_id']]
    directions, confidence = empty(case)
    hypotheses = [(f, d) for f in FACETS if f != case['context_facet'] and anchor[f]
                  for d in ('similar', 'different')]
    if not hypotheses:
        return dict(directions=directions, direction_confidence=confidence, posterior=[], abstained=True)
    query_h = None
    for query in sorted(evidence.queries, key=lambda q:(time(q['timestamp']), q['query_id'])):
        explicit = []
        for f, values in parse_search(query['text'], facets, vocabulary).items():
            if f == case['context_facet']:
                continue
            if anchor[f] & values['exclude']:
                explicit.append((f, 'different'))
            elif anchor[f] & values['include']:
                explicit.append((f, 'similar'))
        if len(explicit) == 1 and explicit[0] in hypotheses:
            query_h = explicit[0]
    # Retain observed ties; an unidentified contrast is not fabricated as a tie.
    contrasts = [(f, value) for pair in paired_evidence(evidence, facets)
                 for f, value in pair['differences'].items() if f != case['context_facet']]
    weights = []
    for h in hypotheses:
        logs = []
        for strength in config['strengths']:
            value = 0.0
            for f, difference in contrasts:
                same_facet = f == h[0]
                sign = 1 if h[1] == 'different' else -1
                value += log_difference_probability(difference, sign, strength if same_facet else 0)
            if query_h is not None:
                q = config['query_reliability']
                value += math.log(q if h == query_h else (1-q)/(len(hypotheses)-1))
            logs.append(value)
        peak = max(logs)
        weights.append(peak + math.log(sum(math.exp(v-peak) for v in logs)/len(logs)))
    peak = max(weights)
    probabilities = [math.exp(v-peak) for v in weights]
    total = sum(probabilities)
    posterior = sorted((dict(focus=f, direction=d, probability=p/total)
                        for (f, d), p in zip(hypotheses, probabilities)),
                       key=lambda r:(-r['probability'], r['focus'], r['direction']))
    first = posterior[0]
    gap = first['probability'] - posterior[1]['probability']
    usable = sum(f == first['focus'] for f, _ in contrasts)
    accept = (first['probability'] >= config['posterior_minimum'] and gap >= config['posterior_gap']
              and (query_h is not None or usable >= config['minimum_pairs']))
    if accept:
        directions[first['focus']], confidence[first['focus']] = first['direction'], first['probability']
    return dict(directions=directions, direction_confidence=confidence, posterior=posterior,
                posterior_gap=gap, query_hypothesis=list(query_h) if query_h else None,
                observed_contrasts=len(contrasts), abstained=not accept)
