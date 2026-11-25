"""D: infer session direction; every direction ablation uses the same C profile."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from baseline_common import direction_estimate,facet_profiles,facet_vectors,intent_scores,ranked
from experiment_io import FACETS
from experiment_runner import main

def predict(papers, facets, cases, history, options):
    profiles = facet_profiles(options['profile_history'],options['profile_searches'],facets,options['cutoff'])
    vectors = facet_vectors(facets)
    predictions = []
    for case in cases:
        weights = profiles[case['user_id']]['facet_importance']
        similar = dict.fromkeys(FACETS,'similar')
        behavior,behavior_confidence = direction_estimate(case,history,[],options['exposures'],facets,
                    margin=options['direction_margin'],minimum_pairs=options['min_direction_pairs'],use_search=False)
        searched,search_confidence = direction_estimate(case,history,options['searches'],options['exposures'],facets,
                    margin=options['direction_margin'],minimum_pairs=options['min_direction_pairs'])
        for model,w,directions,confidence in (
            ('fixed_similar',dict.fromkeys(FACETS,1/len(FACETS)),similar,dict.fromkeys(FACETS,1.0)),
            ('profile_similar',weights,similar,dict.fromkeys(FACETS,1.0)),
            ('direction_behavior',weights,behavior,behavior_confidence),
            ('direction_search',weights,searched,search_confidence)):
            row = ranked(case,model,intent_scores(case,w,directions,vectors))
            row.update(facet_importance=w,directions=directions,direction_confidence=confidence)
            predictions.append(row)
    return predictions

if __name__ == '__main__':
    main('d',predict)
