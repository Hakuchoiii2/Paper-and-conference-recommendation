"""Generate dataset D; paths are relative to the project root."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

import collections
import datetime as dt
from data.experiment_common import (facet_index, new_profile, profile_events, validate_simulator)
from validate_all import require, validate_time


def build_d(facets, config, rng):
    validate_simulator(config)
    require(type(config['num_users']) is int and 0 < config['num_users'] <= 9999, 'Invalid user count')
    require(type(config['events_per_user']) is int and type(config['history_events_per_user']) is int
            and 0 < config['history_events_per_user'] < config['events_per_user'], 'Invalid D history/future quotas')
    require(type(config['event_step_seconds']) is int and config['event_step_seconds'] > 0, 'Invalid event interval')
    start = validate_time(config['start_timestamp'])
    times = [start + dt.timedelta(seconds=i*config['event_step_seconds']) for i in range(config['events_per_user'])]
    index = facet_index(facets)
    users, profiles, history, future = [], [], [], []
    for number in range(1, config['num_users']+1):
        user = f'U{number:04}'
        users.append(dict(user_id=user))
        profile = new_profile(facets, config, rng)
        profiles.append(dict(user_id=user, latent_preferences=profile))
        events = profile_events(facets, index, user, profile, times, config, rng)
        history.extend(events[:config['history_events_per_user']])
        future.extend(events[config['history_events_per_user']:])
    report = dict(shortfall=0, actual_users=len(users), actual_events=len(history)+len(future),
                  behavior_counts=dict(collections.Counter(row['interaction_type'] for row in history)),
                  exposure_policy='without_replacement_mixture_uniform_and_profile_concept_overlap',
                  affinity_rule='mean_weight_over_paper_concepts_unseen_zero',
                  cutoff_policy='first_history_events_then_strictly_future_per_user')
    return ({'users.jsonl': users, 'interactions_train.jsonl': history},
            {'latent_user_profiles.jsonl': profiles, 'interactions_test.jsonl': future}, report)

if __name__ == '__main__':
    from data.build_experiments import run
    run('d')
