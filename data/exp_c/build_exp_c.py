"""C (formerly D): infer user concepts and facet importance from history/search."""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT_ROOT))
sys.path.insert(0,str(PROJECT_ROOT / 'scripts'))
import collections
import datetime as dt
from data.experiment_common import (facet_index,new_profile,profile_events,timestamp,validate_simulator)
from validate_all import require,validate_time

def build_c(facets, config, rng):
    validate_simulator(config)
    require(type(config['num_users']) is int and 0 < config['num_users'] <= 9999,'Invalid num_users')
    count, ntrain = config['events_per_user'],config['history_events_per_user']
    require(type(count) is int and type(ntrain) is int and 0 < ntrain < count,'Invalid C history/future quotas')
    require(type(config['event_step_seconds']) is int and config['event_step_seconds'] > 3,'Invalid event interval')
    start = validate_time(config['start_timestamp'])
    times = [start + dt.timedelta(seconds=i * config['event_step_seconds']) for i in range(count)]
    users, profiles, history, future, searches, exposures, cases = [], [], [], [], [], [], []
    future_searches, future_exposures = [], []
    index = facet_index(facets)
    cutoff = timestamp(times[ntrain] - dt.timedelta(seconds=3))
    for number in range(1,config['num_users']+1):
        user = f'U{number:04}'
        users.append(dict(user_id=user))
        profile, importance = new_profile(facets,config,rng)
        profiles.append(dict(user_id=user,latent_preferences=profile,facet_importance=importance))
        events, queries, shown = profile_events(facets,index,user,profile,importance,times,config,rng,f'C{user}')
        history.extend(events[:ntrain])
        future.extend(events[ntrain:])
        searches.extend(q for q in queries if q['timestamp'] < cutoff)
        future_searches.extend(q for q in queries if q['timestamp'] >= cutoff)
        exposures.extend(x for x in shown if x['timestamp'] < cutoff)
        future_exposures.extend(x for x in shown if x['timestamp'] >= cutoff)
        cases.append(dict(case_id=f'C{user}',user_id=user,candidate_ids=[e['paper_id'] for e in events[ntrain:]],
                          cutoff=cutoff))
    report = dict(shortfall=0,actual_users=len(users),actual_events=len(history)+len(future),
                  behavior_counts=dict(collections.Counter(r['interaction_type'] for r in history)))
    return (dict(zip(('users.jsonl','interactions_train.jsonl','search_events.jsonl','exposures.jsonl','cases.jsonl'),
                     (users,history,searches,exposures,cases))),
            dict(zip(('latent_user_profiles.jsonl','interactions_test.jsonl','search_events_test.jsonl','exposures_test.jsonl'),
                     (profiles,future,future_searches,future_exposures))),report)

if __name__ == '__main__':
    from data.build_experiments import run
    run('c')
