"""B: shared TF-IDF encoder for whole text, equal facets and fixed weighted facets."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from baseline_common import dot,random_scores,ranked,tfidf
from experiment_io import FACETS
from experiment_runner import main

def predict(papers, facets, cases, history, options):
    docs = {(pid,'whole'):row['title'] + ' ' + row['abstract'] for pid,row in papers.items()}
    docs.update({(pid,f):' '.join(sorted(row[f])) for pid,row in facets.items() for f in FACETS})
    vectors = tfidf(docs)
    predictions = []
    for case in cases:
        q = case['query_paper_id']
        scores = dict(random=random_scores(case,options['seed']),
                      text_tfidf={p:dot(vectors[q,'whole'],vectors[p,'whole']) for p in case['candidate_ids']},
                      equal_facets={p:sum(dot(vectors[q,f],vectors[p,f]) for f in FACETS)/len(FACETS)
                                    for p in case['candidate_ids']},
                      weighted_facets={p:sum(options['fixed_weights'][f]*dot(vectors[q,f],vectors[p,f])
                                             for f in FACETS) for p in case['candidate_ids']})
        predictions.extend(ranked(case,model,values) for model,values in scores.items())
    return predictions

if __name__ == '__main__':
    main('b',predict)
