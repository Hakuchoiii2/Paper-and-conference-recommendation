"""Deterministic mock scenarios on verified A concepts; no fabricated paper facets."""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

import collections
import datetime as dt
import math
import random
from experiment_io import FACETS
from validate_all import require, validate_time

def facet_relevance(query, candidate):
    if not query or not candidate:
        return None
    return 2 if query == candidate else 1 if query & candidate else 0

def facet_index(facets):
    index = {f: collections.defaultdict(set) for f in FACETS}
    for pid, row in sorted(facets.items()):
        for f in FACETS:
            for concept in sorted(row[f]):
                index[f][concept].add(pid)
    return index

def overlapping(index, facet, concepts):
    return set().union(*(index[facet].get(c, set()) for c in sorted(concepts))) if concepts else set()

def sampled(values, count, rng):
    return rng.sample(sorted(values), count)

def candidate_sample(positive, negative, hard, count, config, rng):
    if not positive or not negative or len(positive) + len(negative) < count:
        return None
    np = max(1, min(len(positive), count - 1, round(count * config['positive_fraction'])))
    np = max(np, count - len(negative))
    nn = count - np
    nh = min(len(hard), round(nn * config['hard_negative_fraction']))
    selected = sampled(positive, np, rng) + sampled(hard, nh, rng)
    selected += sampled(negative - set(selected), nn - nh, rng)
    rng.shuffle(selected)
    return selected

def grouped_splits(records, key, seed):
    anchors = sorted({r['query_paper_id'] for r in records})
    random.Random(seed).shuffle(anchors)
    a, b = int(len(anchors) * .7), int(len(anchors) * .85)
    sides = {q: 'train' if i < a else 'dev' if i < b else 'test' for i, q in enumerate(anchors)}
    return {s: [r[key] for r in records if sides[r['query_paper_id']] == s] for s in ('train','dev','test')}

def normalized_weights(values):
    require(set(values) == set(FACETS) and all(type(v) in (int,float) and math.isfinite(v) and v >= 0
                                             for v in values.values()) and sum(values.values()) > 0,
            'Invalid facet importance')
    total = sum(values.values())
    return {f: values[f] / total for f in FACETS}

def validate_sampling(config, count_key, candidate_key):
    require(type(config[count_key]) is int and 0 < config[count_key] <= 9999, f'Invalid {count_key}')
    require(type(config[candidate_key]) is int and config[candidate_key] >= 2, f'Invalid {candidate_key}')
    for key in ('positive_fraction','hard_negative_fraction'):
        require(type(config[key]) in (int,float) and math.isfinite(config[key]) and 0 <= config[key] <= 1,
                f'Invalid {key}')

def validate_simulator(config):
    require(config['rule_version'] == 'profile_search_v2', 'Unsupported simulator rule version')
    require(type(config['concepts_per_facet']) is int and config['concepts_per_facet'] >= 2,
            'concepts_per_facet must be at least two')
    for key in ('targeted_exposure_fraction','noise_std','search_fraction'):
        require(type(config[key]) in (int,float) and math.isfinite(config[key]) and 0 <= config[key] <= 1,
                f'Invalid {key}')
    require(type(config['exposure_size']) is int and config['exposure_size'] >= 2, 'Invalid exposure_size')
    thresholds = config['interaction_thresholds']
    require(len(thresholds) == 4 and all(type(v) in (int,float) and math.isfinite(v) for v in thresholds)
            and all(a < b for a,b in zip(thresholds,thresholds[1:])), 'Invalid behavior thresholds')
    for key, low, high in (('positive_weight_range',0,1),('negative_weight_range',-1,0)):
        v = config[key]
        require(len(v) == 2 and all(type(x) in (int,float) and math.isfinite(x) for x in v)
                and low <= v[0] <= v[1] <= high, f'Invalid {key}')

def new_profile(facets, config, rng):
    eligible = sorted(pid for pid,row in facets.items() if any(row.values()))
    require(len(eligible) >= 2, 'Simulator needs at least two papers with evidence')
    positive, negative = (facets[pid] for pid in rng.sample(eligible,2))
    preferences = {}
    for f in FACETS:
        liked = sampled(positive[f], min(len(positive[f]),config['concepts_per_facet'] - 1), rng)
        avoided = sampled(negative[f] - set(liked), min(len(negative[f] - set(liked)),
                                                       config['concepts_per_facet'] - len(liked)), rng)
        preferences[f] = {c: round(rng.uniform(*config['positive_weight_range']),6) for c in liked}
        preferences[f].update({c: round(rng.uniform(*config['negative_weight_range']),6) for c in avoided})
    importance = normalized_weights({f: rng.uniform(.05,1) if preferences[f] else 0 for f in FACETS})
    return preferences, importance

def affinity(profile, paper, importance=None):
    importance = importance or dict.fromkeys(FACETS,1 / len(FACETS))
    return sum(importance[f] * (sum(profile.get(f,{}).get(c,0) for c in paper[f]) / len(paper[f])
                               if paper[f] else 0) for f in FACETS)

def behavior(score, config):
    return ('dislike','view','click','save','like')[sum(score >= t for t in config['interaction_thresholds'])]

def timestamp(value):
    return value.astimezone(dt.timezone.utc).isoformat().replace('+00:00','Z')

def profile_events(facets, index, user, profile, importance, times, config, rng, session):
    pool = sorted(pid for pid,row in facets.items() if any(row.values()))
    require(len(pool) >= max(len(times),config['exposure_size']), 'Not enough eligible papers')
    matching = set()
    for f, weights in profile.items():
        matching.update(overlapping(index,f,{c for c,v in weights.items() if v != 0}))
    used, events, searches, exposures = set(), [], [], []
    previous = None
    for i,time in enumerate(times):
        remaining = set(pool) - used
        target = remaining & matching
        pid = sampled(target if target and rng.random() < config['targeted_exposure_fraction']
                      else remaining,1,rng)[0]
        used.add(pid)
        query_id = None
        if rng.random() < config['search_fraction']:
            eligible = [f for f in FACETS if any(v > 0 for v in profile[f].values())]
            if eligible:
                f = rng.choices(eligible,weights=[importance[x] for x in eligible])[0]
                concept = sampled({c for c,v in profile[f].items() if v > 0},1,rng)[0]
                query_id = f'{session}Q{i:04}'
                searches.append(dict(query_id=query_id,user_id=user,session_id=session,
                                     text=f'{f}: {concept} papers',parent_query_id=previous,
                                     timestamp=timestamp(time - dt.timedelta(seconds=2))))
                previous = query_id
        displayed = [pid] + sampled(set(pool) - {pid},config['exposure_size'] - 1,rng)
        rng.shuffle(displayed)
        exposure = f'{session}X{i:04}'
        exposures.append(dict(exposure_id=exposure,user_id=user,session_id=session,query_id=query_id,
                              paper_ids=displayed,timestamp=timestamp(time - dt.timedelta(seconds=1))))
        score = affinity(profile,facets[pid],importance) + rng.gauss(0,config['noise_std'])
        events.append(dict(user_id=user,paper_id=pid,interaction_type=behavior(score,config),
                           timestamp=timestamp(time),session_id=session,exposure_id=exposure))
    return events, searches, exposures

def retrieval_grade(anchor, candidate, weights):
    return sum(weights[f] * (facet_relevance(anchor[f],candidate[f]) or 0) for f in FACETS)

def session_grade(anchor, candidate, focus, direction, context='problem'):
    if not candidate[context] or not candidate[focus] or not anchor[focus]:
        return 0
    relevant = bool(anchor[context] & candidate[context])
    matches = bool(anchor[focus] & candidate[focus]) == (direction == 'similar')
    return 2 if relevant and matches else 1 if relevant else 0
