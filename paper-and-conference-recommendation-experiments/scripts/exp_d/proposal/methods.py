"""Eight public estimators; original baseline inference remains untouched."""
import math

from data_io import FACETS, time
from baseline_common import BEHAVIOR_WEIGHTS, direction_estimate, parse_search, search_vocabulary

MODELS = ('fixed_similar', 'profile_similar', 'query_only', 'direction_behavior',
          'direction_search', 'vote', 'bayes_h', 'ordinal_intent')
DEFAULTS = dict(minimum_pairs=2, delta_margin=.25, vote_fraction=.75,
                reaction_reliability=.8, query_reliability=.8,
                posterior_minimum=.25, posterior_gap=.10)


def empty(case):
    directions = dict.fromkeys(FACETS, 'unknown')
    confidence = dict.fromkeys(FACETS, 0.0)
    directions[case['context_facet']], confidence[case['context_facet']] = 'similar', 1.0
    return directions, confidence


def paired_evidence(evidence, facets):
    """Same overlap/missingness matching and final-action subtraction as DELTA."""
    case = evidence.case
    anchor = facets[case['query_paper_id']]
    reactions = {(r['exposure_id'], r['paper_id']):BEHAVIOR_WEIGHTS[r['interaction_type']]
                 for r in evidence.reactions}
    pairs = []
    for exposure in evidence.exposures:
        if len(exposure['paper_ids']) != 2:
            continue
        a, b = exposure['paper_ids']
        key_a, key_b = (exposure['exposure_id'], a), (exposure['exposure_id'], b)
        if key_a not in reactions or key_b not in reactions:
            continue
        differences = {}
        for f in FACETS:
            if not anchor[f] or not facets[a][f] or not facets[b][f]:
                continue
            same_a, same_b = bool(anchor[f] & facets[a][f]), bool(anchor[f] & facets[b][f])
            comparable = all((None if not anchor[g] or not facets[a][g] else bool(anchor[g] & facets[a][g]))
                             == (None if not anchor[g] or not facets[b][g] else bool(anchor[g] & facets[b][g]))
                             for g in FACETS if g != f)
            if same_a != same_b and comparable:
                same, different = (a, b) if same_a else (b, a)
                differences[f] = reactions[exposure['exposure_id'], different] - reactions[exposure['exposure_id'], same]
        pairs.append(dict(exposure_id=exposure['exposure_id'], differences=differences))
    return pairs


def query_overrides(evidence, facets, vocabulary, directions, confidence):
    anchor = facets[evidence.case['query_paper_id']]
    for query in sorted(evidence.queries, key=lambda q:(time(q['timestamp']), q['query_id'])):
        for f, values in parse_search(query['text'], facets, vocabulary).items():
            if anchor[f] & values['exclude']:
                directions[f], confidence[f] = 'different', 1.0
            elif anchor[f] & values['include']:
                directions[f], confidence[f] = 'similar', .8


def vote(evidence, facets, config, vocabulary):
    directions, confidence = empty(evidence.case)
    pairs = paired_evidence(evidence, facets)
    counts = {}
    for f in FACETS:
        values = [p['differences'][f] for p in pairs if p['differences'].get(f, 0) != 0]
        n_diff, n_same = sum(v > 0 for v in values), sum(v < 0 for v in values)
        counts[f] = dict(different=n_diff, similar=n_same)
        if len(values) >= config['minimum_pairs']:
            fraction = max(n_diff, n_same) / len(values)
            if fraction >= config['vote_fraction']:
                directions[f] = 'different' if n_diff > n_same else 'similar'
                confidence[f] = fraction
    query_overrides(evidence, facets, vocabulary, directions, confidence)
    return dict(directions=directions, direction_confidence=confidence, votes=counts)


def bayes_h(evidence, facets, config, vocabulary):
    case = evidence.case
    directions, confidence = empty(case)
    hypotheses = [(f, d) for f in FACETS if f != case['context_facet'] and facets[case['query_paper_id']][f]
                  for d in ('similar', 'different')]
    if not hypotheses:
        return dict(directions=directions, direction_confidence=confidence, posterior=[], abstained=True)
    query_hypothesis = None
    anchor = facets[case['query_paper_id']]
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
            query_hypothesis = explicit[0]
    pairs = paired_evidence(evidence, facets)
    usable = sum(any(value != 0 and f != case['context_facet'] for f, value in p['differences'].items()) for p in pairs)
    log_weights = []
    for hypothesis in hypotheses:
        f, direction = hypothesis
        log_weight = -math.log(len(hypotheses))
        if query_hypothesis is not None:
            likelihood = (config['query_reliability'] if hypothesis == query_hypothesis
                          else (1 - config['query_reliability']) / (len(hypotheses) - 1))
            log_weight += math.log(likelihood)
        for pair in pairs:
            value = pair['differences'].get(f, 0)
            if value == 0:
                likelihood = .5
            else:
                supported = 'different' if value > 0 else 'similar'
                likelihood = config['reaction_reliability'] if supported == direction else 1-config['reaction_reliability']
            log_weight += math.log(likelihood)
        log_weights.append(log_weight)
    peak = max(log_weights)
    probabilities = [math.exp(value-peak) for value in log_weights]
    total = sum(probabilities)
    posterior = sorted((dict(focus=f, direction=d, probability=value/total)
                        for (f, d), value in zip(hypotheses, probabilities)),
                       key=lambda r:(-r['probability'], r['focus'], r['direction']))
    first = posterior[0]
    gap = first['probability'] - (posterior[1]['probability'] if len(posterior) > 1 else 0)
    accept = (first['probability'] >= config['posterior_minimum'] and gap >= config['posterior_gap']
              and (query_hypothesis is not None or usable >= config['minimum_pairs']))
    if accept:
        directions[first['focus']], confidence[first['focus']] = first['direction'], first['probability']
    return dict(directions=directions, direction_confidence=confidence, posterior=posterior,
                posterior_gap=gap, query_hypothesis=list(query_hypothesis) if query_hypothesis else None,
                non_tied_pairs=usable, abstained=not accept)


def predict_all(evidence, facets, config=None, vocabulary=None, ordinal_config=None):
    config = dict(DEFAULTS if config is None else config)
    vocabulary = vocabulary if vocabulary is not None else search_vocabulary(facets)
    similar = dict.fromkeys(FACETS, 'similar')
    result = {name:dict(directions=dict(similar), direction_confidence=dict.fromkeys(FACETS, 1.0))
              for name in ('fixed_similar', 'profile_similar')}
    for model, reactions, queries, exposures, use_search in (
        ('direction_behavior', evidence.reactions, (), evidence.exposures, False),
        ('direction_search', evidence.reactions, evidence.queries, evidence.exposures, True),
        ('query_only', (), evidence.queries, (), True)):
        d, c = direction_estimate(evidence.case, reactions, queries, exposures, facets,
                                 margin=config['delta_margin'], minimum_pairs=config['minimum_pairs'], use_search=use_search)
        result[model] = dict(directions=d, direction_confidence=c)
    result['vote'] = vote(evidence, facets, config, vocabulary)
    result['bayes_h'] = bayes_h(evidence, facets, config, vocabulary)
    # Local import avoids a cycle: Ordinal-Intent shares public pair matching.
    from ordinal_intent import ordinal_intent
    result['ordinal_intent'] = ordinal_intent(evidence, facets, vocabulary, ordinal_config)
    return {name:result[name] for name in MODELS}
