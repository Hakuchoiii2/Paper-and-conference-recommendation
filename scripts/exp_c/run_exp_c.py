"""C: preference inference; compare whole-text and facet profiles with search ablation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from baseline_common import (dot,facet_profiles,popularity,profile_score,ranked,search_text_profiles)
from experiment_runner import main

def predict(papers, facets, cases, history, options):
    queries = options['searches']
    text,vectors = search_text_profiles(papers,history,queries,options['cutoff'])
    facet = facet_profiles(history,queries,facets,options['cutoff'])
    no_search = facet_profiles(history,[],facets,options['cutoff'])
    popular = popularity(history)
    predictions = []
    for case in cases:
        user = case['user_id']
        predictions.append(ranked(case,'popularity',{p:popular[p] for p in case['candidate_ids']}))
        predictions.append(ranked(case,'text_history',{p:dot(text.get(user,{}),vectors[p]) for p in case['candidate_ids']}))
        for model,profiles in (('facet_no_search',no_search),('facet_history',facet)):
            profile = profiles.get(user)
            scores = {p:profile_score(profile,p,facets) if profile else 0 for p in case['candidate_ids']}
            row = ranked(case,model,scores)
            if profile:
                row['facet_importance'] = profile['facet_importance']
            predictions.append(row)
    return predictions

if __name__ == '__main__':
    main('c',predict)
