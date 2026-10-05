"""Generate dataset E; paths are relative to the project root."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

import collections
import datetime as dt
import math
from data.experiment_common import (FACETS, check_users, facet_index, new_profile, profile_events,
                                    timestamp, validate_simulator)
from validate_all import require, validate_time


def interpolate(old, new, coefficient):
    return {facet: {concept: round((1-coefficient)*old[facet].get(concept,0) + coefficient*new[facet].get(concept,0), 6)
                    for concept in sorted(old[facet].keys() | new[facet].keys())} for facet in FACETS}


def build_e(facets, users, config, rng):
    validate_simulator(config)
    check_users(users)
    require(type(config['events_per_user_per_period']) is int and config['events_per_user_per_period'] >= 2,
            'E requires at least two events per user/period')
    require(config['history_periods'] == [1,2,3] and config['holdout_period'] == 4, 'E must split periods 1–3 / 4')
    require(type(config['stable_fraction']) in (int,float) and math.isfinite(config['stable_fraction'])
            and 0 <= config['stable_fraction'] <= 1, 'Invalid stable fraction')
    coefficients = config['drift_coefficients']
    require(len(coefficients) == 4 and all(type(c) in (int,float) and math.isfinite(c) and 0 <= c <= 1
                                          for c in coefficients) and coefficients[0] == 0
            and coefficients[2:] == [1,1], 'Invalid drift coefficients')
    boundaries = [validate_time(time) for time in config['period_boundaries']]
    require(len(boundaries) == 5 and all(a < b for a,b in zip(boundaries, boundaries[1:])),
            'E requires four consecutive nonempty periods')
    index = facet_index(facets)
    user_ids = sorted(row['user_id'] for row in users)
    shuffled = user_ids.copy()
    rng.shuffle(shuffled)
    stable = set(shuffled[:int(len(users)*config['stable_fraction'])])
    groups = {user: 'stable' if user in stable else 'drift' for user in user_ids}
    profiles, history, future = [], [], []
    for user in user_ids:
        old, new = new_profile(facets, config, rng), new_profile(facets, config, rng)
        for period, (start,end) in enumerate(zip(boundaries, boundaries[1:]), 1):
            seconds = int((end-start).total_seconds())
            count = config['events_per_user_per_period']
            require(seconds > count, 'Period too short for strictly ordered events')
            times = [start + dt.timedelta(seconds=seconds*i//(count+1)) for i in range(1,count+1)]
            profile = old if user in stable else interpolate(old,new,coefficients[period-1])
            profiles.append(dict(user_id=user, period=period, start_timestamp=timestamp(start),
                                 end_timestamp=timestamp(end), latent_preferences=profile))
            events = profile_events(facets,index,user,profile,times,config,rng)
            (history if period in config['history_periods'] else future).extend(events)
    report = dict(shortfall=0, actual_users=len(users), actual_events=len(history)+len(future),
                  group_counts={'stable':len(stable),'drift':len(users)-len(stable)},
                  behavior_counts=dict(collections.Counter(row['interaction_type'] for row in history)),
                  exposure_policy='without_replacement_per_period_mixture_uniform_and_profile_concept_overlap',
                  affinity_rule='mean_weight_over_paper_concepts_unseen_zero')
    return ({'interactions_train.jsonl': history}, {'temporal_profiles.jsonl': profiles,
            'interactions_test.jsonl': future, 'period_metadata.json': dict(groups=groups,
            boundaries=[timestamp(value) for value in boundaries], drift_coefficients=coefficients)}, report)

if __name__ == '__main__':
    from data.build_experiments import run
    run('e')
