"""Shared sampling and simulation rules for dataset generators B–E."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

import collections
import datetime as dt
import math
import random

from experiment_io import FACETS, check_users
from validate_all import require, validate_time

def facet_relevance(query, candidate):
    if not query or not candidate:
        return None
    return 2 if query == candidate else 1 if query & candidate else 0


def intent_satisfaction(query, candidate, constraints):
    active = [facet for facet in FACETS if constraints[facet] != 'ignore']
    if any(not query[facet] or not candidate[facet] for facet in active):
        return None
    return all(bool(query[facet] & candidate[facet]) == (constraints[facet] == 'similar')
               for facet in active)


def facet_index(facets):
    index = {facet: collections.defaultdict(set) for facet in FACETS}
    for pid, row in sorted(facets.items()):
        for facet in FACETS:
            for concept in sorted(row[facet]):
                index[facet][concept].add(pid)
    return index


def overlapping(index, facet, concepts):
    result = set()
    for concept in sorted(concepts):
        result.update(index[facet].get(concept, ()))
    return result


def sampled(values, count, rng):
    return rng.sample(sorted(values), count)


def candidate_sample(positive, negative, hard, count, config, rng):
    if not positive or not negative or len(positive) + len(negative) < count:
        return None
    npositive = max(1, min(len(positive), count-1, round(count * config['positive_fraction'])))
    npositive = max(npositive, count - len(negative))
    nnegative = count - npositive
    nhard = min(len(hard), round(nnegative * config['hard_negative_fraction']))
    selected = sampled(positive, npositive, rng) + sampled(hard, nhard, rng)
    selected += sampled(negative - set(selected), nnegative-nhard, rng)
    rng.shuffle(selected)
    return selected


def grouped_splits(records, key, seed):
    anchors = sorted({row['query_paper_id'] for row in records})
    random.Random(seed).shuffle(anchors)
    ntrain, ndev = int(len(anchors) * 0.7), int(len(anchors) * 0.15)
    assignment = {anchor: 'train' if i < ntrain else 'dev' if i < ntrain+ndev else 'test'
                  for i, anchor in enumerate(anchors)}
    return {name: [row[key] for row in records if assignment[row['query_paper_id']] == name]
            for name in ('train', 'dev', 'test')}


def validate_sampling(config, count_key, candidate_key):
    require(type(config[count_key]) is int and 0 < config[count_key] <= 9999, f'Invalid {count_key}')
    require(type(config[candidate_key]) is int and config[candidate_key] >= 2, f'Invalid {candidate_key}')
    for key in ('positive_fraction', 'hard_negative_fraction'):
        require(type(config[key]) in (int, float) and math.isfinite(config[key])
                and 0 <= config[key] <= 1, f'Invalid {key}')
    require(config['label_rule_version'] == 'concept_overlap_v1', 'Unsupported label rule version')


def validate_simulator(config):
    require(config['rule_version'] == 'profile_first_v1', 'Unsupported simulator rule version')
    require(type(config['concepts_per_facet']) is int and config['concepts_per_facet'] >= 2,
            'concepts_per_facet must be at least two')
    for key, low, high in (('targeted_exposure_fraction', 0, 1), ('noise_std', 0, 1)):
        require(type(config[key]) in (int,float) and math.isfinite(config[key])
                and low <= config[key] <= high, f'Invalid {key}')
    thresholds = config['interaction_thresholds']
    require(len(thresholds) == 4 and all(type(v) in (int,float) and math.isfinite(v) for v in thresholds)
            and all(a < b for a,b in zip(thresholds, thresholds[1:])), 'Invalid behavior thresholds')
    for key, minimum, maximum in (('positive_weight_range',0,1), ('negative_weight_range',-1,0)):
        bounds = config[key]
        require(len(bounds) == 2 and all(type(v) in (int,float) and math.isfinite(v) for v in bounds)
                and minimum <= bounds[0] <= bounds[1] <= maximum, f'Invalid {key}')


def new_profile(facets, config, rng):
    eligible = sorted(pid for pid, row in facets.items() if any(row.values()))
    require(len(eligible) >= 2, 'Simulator needs at least two papers with evidence')
    positive, negative = (facets[pid] for pid in rng.sample(eligible, 2))
    profile = {}
    for facet in FACETS:
        preferred = sampled(positive[facet], min(len(positive[facet]), config['concepts_per_facet']-1), rng)
        avoided = sampled(negative[facet] - set(preferred), min(len(negative[facet] - set(preferred)),
                          config['concepts_per_facet']-len(preferred)), rng)
        profile[facet] = {concept: round(rng.uniform(*config['positive_weight_range']), 6) for concept in preferred}
        profile[facet].update({concept: round(rng.uniform(*config['negative_weight_range']), 6) for concept in avoided})
    return profile


def affinity(profile, paper):
    weights = [profile.get(facet, {}).get(concept, 0) for facet, concepts in sorted(paper.items())
               for concept in sorted(concepts)]
    return sum(weights) / len(weights) if weights else 0.0


def timestamp(value):
    return value.astimezone(dt.timezone.utc).isoformat().replace('+00:00', 'Z')


def profile_events(facets, index, user, profile, timestamps, config, rng):
    pool = sorted(pid for pid, row in facets.items() if any(row.values()))
    require(len(pool) >= len(timestamps), 'Not enough eligible papers for distinct exposure events')
    matching = set()
    for facet, weights in profile.items():
        matching.update(overlapping(index, facet, {concept for concept, weight in weights.items() if weight}))
    targeted = sorted(matching)
    rng.shuffle(pool)
    rng.shuffle(targeted)
    used, events = set(), []
    for time in timestamps:
        while targeted and targeted[-1] in used:
            targeted.pop()
        while pool and pool[-1] in used:
            pool.pop()
        choices = targeted if targeted and rng.random() < config['targeted_exposure_fraction'] else pool
        pid = choices.pop()
        used.add(pid)
        score = affinity(profile, facets[pid]) + rng.gauss(0, config['noise_std'])
        level = sum(score >= threshold for threshold in config['interaction_thresholds'])
        events.append(dict(user_id=user, paper_id=pid, interaction_type=('dislike','view','click','save','like')[level],
                           timestamp=timestamp(time)))
    return events
