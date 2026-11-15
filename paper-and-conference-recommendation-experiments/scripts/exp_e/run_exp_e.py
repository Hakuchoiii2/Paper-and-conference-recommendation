"""E: static, recent and time-decayed profiles; same search evidence and ranker."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from baseline_common import facet_profiles,popularity,profile_score,ranked
from experiment_runner import main

def predict(papers, facets, cases, history, options):
    popular = popularity(history)
    profiles = {model:facet_profiles(history,options['searches'],facets,options['cutoff'],**extra)
                for model,extra in (
                    ('static',{}),('recent',dict(recent_start=options['recent_start'])),
                    ('decay',dict(half_life_days=options['half_life_days'])))}
    predictions = []
    for case in cases:
        predictions.append(ranked(case,'popularity',{p:popular[p] for p in case['candidate_ids']}))
        for model,values in profiles.items():
            profile = values.get(case['user_id'])
            row = ranked(case,model,{p:profile_score(profile,p,facets) if profile else 0 for p in case['candidate_ids']})
            if profile:
                row['facet_importance'] = profile['facet_importance']
            predictions.append(row)
    return predictions

if __name__ == '__main__':
    main('e',predict)
