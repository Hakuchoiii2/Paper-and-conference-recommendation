"""E: rolling temporal evaluation on the same C identities, with a separate stream."""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT_ROOT))
sys.path.insert(0,str(PROJECT_ROOT / 'scripts'))
import collections
from data.experiment_common import (FACETS,facet_index,new_profile,normalized_weights,profile_events,
                                    timestamp,validate_simulator)
from validate_all import require,validate_time

def interpolate(old, new, coefficient):
    return {f:{c:(1-coefficient)*old[f].get(c,0) + coefficient*new[f].get(c,0)
               for c in sorted(old[f].keys() | new[f].keys())} for f in FACETS}

def build_e(facets, users, config, rng):
    validate_simulator(config)
    count = config['events_per_user_per_period']
    require(type(count) is int and count >= 2,'Invalid events_per_user_per_period')
    boundaries = [validate_time(t) for t in config['period_boundaries']]
    require(len(boundaries) == 5 and all(a < b for a,b in zip(boundaries,boundaries[1:])),
            'E needs four ordered periods')
    coefficients = config['drift_coefficients']
    require(coefficients == [0,.5,1,1],'Unsupported drift schedule')
    require(type(config['stable_fraction']) in (int,float) and 0 <= config['stable_fraction'] <= 1,
            'Invalid stable_fraction')
    ids = [u['user_id'] for u in users]
    rng.shuffle(ids)
    stable = set(ids[:int(len(ids)*config['stable_fraction'])])
    groups = {u:'stable' if u in stable else 'drift' for u in sorted(ids)}
    profiles, history, future, queries, exposures, cases, test_queries, test_exposures = [],[],[],[],[],[],[],[]
    index = facet_index(facets)
    for user in sorted(ids):
        old, old_weights = new_profile(facets,config,rng)
        new, new_weights = new_profile(facets,config,rng)
        for period,(start,end) in enumerate(zip(boundaries,boundaries[1:]),1):
            coefficient = 0 if user in stable else coefficients[period-1]
            profile = interpolate(old,new,coefficient)
            weights = normalized_weights({f:(1-coefficient)*old_weights[f] + coefficient*new_weights[f] for f in FACETS})
            profiles.append(dict(user_id=user,period=period,start_timestamp=timestamp(start),end_timestamp=timestamp(end),
                                 latent_preferences=profile,facet_importance=weights))
            step = (end-start) / (count+1)
            require(step.total_seconds() > 3,'Period too short for ordered search/exposure/events')
            times = [start + step*i for i in range(1,count+1)]
            events, searches, shown = profile_events(facets,index,user,profile,weights,times,config,rng,f'E{user}P{period}')
            if period <= 3:
                history.extend(events); queries.extend(searches); exposures.extend(shown)
            if period >= 2:
                future.extend(events); test_queries.extend(searches); test_exposures.extend(shown)
                cases.append(dict(case_id=f'E{user}P{period}',user_id=user,period=period,cutoff=timestamp(start),
                                  candidate_ids=[r['paper_id'] for r in events]))
    report = dict(shortfall=0,actual_users=len(ids),actual_events=len(ids)*4*count,
                  behavior_counts=dict(collections.Counter(r['interaction_type'] for r in history)),
                  group_counts=dict(collections.Counter(groups.values())))
    return ({'interactions_train.jsonl':history,'search_events.jsonl':queries,'exposures.jsonl':exposures,'cases.jsonl':cases},
            {'temporal_profiles.jsonl':profiles,'interactions_test.jsonl':future,
             'search_events_test.jsonl':test_queries,'exposures_test.jsonl':test_exposures,
             'period_metadata.json':dict(groups=groups,boundaries=config['period_boundaries'],drift_coefficients=coefficients)},
            report)

if __name__ == '__main__':
    from data.build_experiments import run
    run('e')
