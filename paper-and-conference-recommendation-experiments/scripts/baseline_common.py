"""Small, deterministic CPU baselines; no model downloads or training labels."""
import collections
import math
import random
import re

from build_corpus import normalize
from experiment_io import FACETS
from validate_all import require, validate_time

BEHAVIOR_WEIGHTS = dict(dislike=-1, view=0, click=1, save=2, like=3)
BEHAVIOR_GRADES = dict(dislike=0, view=0, click=1, save=2, like=3)


def unit_vector(vector):
    length = math.sqrt(sum(value * value for value in vector.values()))
    return {key: value / length for key, value in vector.items() if value} if length else {}


def dot(left, right):
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(key, 0) for key, value in left.items())


def tfidf(documents):
    counts = {key: collections.Counter(re.findall(r'\b\w\w+\b', normalize(text)))
              for key, text in sorted(documents.items())}
    frequency = collections.Counter(term for row in counts.values() for term in row)
    idf = {term: math.log((1 + len(counts)) / (1 + count)) + 1
           for term, count in frequency.items()}
    return {key: unit_vector({term: count * idf[term] for term, count in row.items()})
            for key, row in counts.items()}


def text_vectors(papers):
    return tfidf({pid: row['title'] + ' ' + row['abstract'] for pid, row in papers.items()})


def facet_vectors(facets):
    return tfidf({(pid, facet): ' '.join(sorted(row[facet]))
                  for pid, row in facets.items() for facet in FACETS})


def concept_vectors(facets):
    return {pid: unit_vector({(facet, concept): 1 for facet in FACETS for concept in sorted(row[facet])})
            for pid, row in sorted(facets.items())}


def ranked(case, model, scores):
    require(set(scores) == set(case['candidate_ids']), 'Scorer must cover exactly the candidate set')
    require(all(math.isfinite(value) for value in scores.values()), 'Non-finite prediction score')
    return dict(case_id=case['case_id'], model=model,
                ranking=[dict(paper_id=pid, score=scores[pid])
                         for pid in sorted(scores, key=lambda pid: (-scores[pid], pid))])


def random_scores(case, seed):
    rng = random.Random(f"{seed}:{case['case_id']}")
    return {pid: rng.random() for pid in sorted(case['candidate_ids'])}


def history_profiles(history, vectors, cutoff=None, half_life_days=None, recent_start=None):
    profiles = collections.defaultdict(collections.Counter)
    cutoff = validate_time(cutoff) if cutoff else None
    recent_start = validate_time(recent_start) if recent_start else None
    for event in history:
        time = validate_time(event['timestamp'])
        require(cutoff is None or time < cutoff, 'Future event reached profile builder')
        if recent_start is not None and time < recent_start:
            continue
        weight = BEHAVIOR_WEIGHTS[event['interaction_type']]
        if half_life_days is not None:
            require(cutoff is not None and math.isfinite(half_life_days) and half_life_days > 0,
                    'Decay requires a cutoff and positive finite half-life')
            weight *= 2 ** (-(cutoff - time).total_seconds() / (86400 * half_life_days))
        for key, value in vectors[event['paper_id']].items():
            profiles[event['user_id']][key] += weight * value
    return {user: unit_vector(profile) for user, profile in profiles.items()}


def popularity(history):
    counts = collections.Counter()
    for event in history:
        counts[event['paper_id']] += max(0, BEHAVIOR_WEIGHTS[event['interaction_type']])
    return counts


def ranking_metrics(ranking, labels, ks):
    require(len(ranking) == len(set(ranking)) and set(ranking) == set(labels),
            'Ranking must contain every judged candidate exactly once')
    require(all(type(value) in (int, float) and math.isfinite(value) and value >= 0
                for value in labels.values()), 'Invalid relevance grade')
    grades = [labels[pid] for pid in ranking]
    positives = sum(value > 0 for value in grades)
    result = {}
    for k in ks:
        require(type(k) is int and k > 0, 'k must be a positive integer')
        top = grades[:k]
        ideal = sorted(grades, reverse=True)[:k]
        dcg = sum((2 ** value - 1) / math.log2(i + 2) for i, value in enumerate(top))
        idcg = sum((2 ** value - 1) / math.log2(i + 2) for i, value in enumerate(ideal))
        result[f'ndcg@{k}'] = dcg / idcg if idcg else None
        result[f'recall@{k}'] = sum(value > 0 for value in top) / positives if positives else None
        result[f'precision@{k}'] = sum(value > 0 for value in top) / len(top)
        result[f'mrr@{k}'] = next((1 / (i + 1) for i, value in enumerate(top) if value > 0),
                                  0.0) if positives else None
    return result


def aggregate(details):
    buckets = collections.defaultdict(list)
    for row in details:
        buckets[row['model'], 'overall'].append(row)
        for group in set(row.get('groups',[row['group']])):
            if group != 'overall':
                buckets[row['model'], group].append(row)
    summary = []
    for (model, group), rows in sorted(buckets.items()):
        values = dict(model=model, group=group, cases=len(rows),
                      positive_cases=sum(row['positive_candidates'] > 0 for row in rows))
        defined = {}
        for metric in sorted({key for row in details for key in row['metrics']}):
            scores = [row['metrics'].get(metric) for row in rows if row['metrics'].get(metric) is not None]
            values[metric] = sum(scores) / len(scores) if scores else None
            defined[metric] = len(scores)
        pairs = [pair for row in rows for pair in row.get('direction_pairs',[])]
        if pairs:
            f1s = []
            for label in ('similar','different'):
                tp = sum(t == label and p == label for t,p in pairs)
                fp = sum(t != label and p == label for t,p in pairs)
                fn = sum(t == label and p != label for t,p in pairs)
                f1s.append(2*tp / (2*tp+fp+fn) if 2*tp+fp+fn else 0)
            values['direction_macro_f1'] = sum(f1s)/len(f1s)
            defined['direction_macro_f1'] = len(rows)
        values['defined_cases'] = defined
        summary.append(values)
    return summary


def search_vocabulary(facets):
    return {f:set().union(*(row[f] for row in facets.values())) for f in FACETS}


def parse_search(text, facets, vocabulary=None):
    """Lexical mock-query parser; excluded terms never become positive profile concepts."""
    # shortcut: mock queries use known concept phrases; add semantic parsing for natural search logs.
    vocabulary = vocabulary or search_vocabulary(facets)
    result = {f:dict(include=set(),exclude=set()) for f in FACETS}
    for segment in normalize(text).split(';'):
        prefix,separator,tail = segment.partition(':')
        fs = [prefix.strip()] if separator and prefix.strip() in FACETS else FACETS
        content = tail if separator and prefix.strip() in FACETS else segment
        for f in fs:
            direct = content.strip()
            negative_direct = direct.startswith('alternatives to ')
            for prefix_text in ('alternatives to ','more papers using '):
                if direct.startswith(prefix_text):
                    direct = direct[len(prefix_text):]
                    break
            if direct.endswith(' papers'):
                direct = direct[:-7]
            if direct in vocabulary[f]:
                result[f]['exclude' if negative_direct else 'include'].add(direct)
                continue
            occupied = set()
            for concept in sorted(vocabulary[f],key=lambda c:(-len(c),c)):
                pattern = r'(?<!\w)' + re.escape(concept) + r'(?!\w)'
                for match in re.finditer(pattern,content):
                    span = set(range(match.start(),match.end()))
                    if span & occupied:
                        continue
                    occupied.update(span)
                    before = content[:match.start()]
                    negative = re.search(r'(?:without|excluding|alternatives? to|instead of|not using)\s*$',before)
                    result[f]['exclude' if negative else 'include'].add(concept)
    return result

def facet_profiles(history, searches, facets, cutoff, half_life_days=None, recent_start=None):
    raw = collections.defaultdict(lambda:{f:collections.Counter() for f in FACETS})
    vocabulary = search_vocabulary(facets)
    cutoff = validate_time(cutoff)
    recent_start = validate_time(recent_start) if recent_start else None
    def temporal_weight(row):
        time = validate_time(row['timestamp'])
        require(time < cutoff,'Future event reached profile builder')
        if recent_start and time < recent_start:
            return 0
        return 2 ** (-(cutoff-time).total_seconds()/(86400*half_life_days)) if half_life_days else 1
    for event in history:
        weight = temporal_weight(event) * BEHAVIOR_WEIGHTS[event['interaction_type']]
        for f in FACETS:
            values = facets[event['paper_id']][f]
            for concept in sorted(values):
                raw[event['user_id']][f][concept] += weight / len(values)
    for query in searches:
        weight = temporal_weight(query)
        for f,values in parse_search(query['text'],facets,vocabulary).items():
            for key,sign in (('include',1),('exclude',-1)):
                for concept in sorted(values[key]):
                    raw[query['user_id']][f][concept] += sign * weight
    profiles = {}
    for user,values in raw.items():
        mass = {f:sum(abs(v) for v in values[f].values()) for f in FACETS}
        total = sum(mass.values())
        profiles[user] = dict(vectors={f:unit_vector(values[f]) for f in FACETS},
                              facet_importance={f:mass[f]/total if total else 1/len(FACETS) for f in FACETS})
    return profiles

def profile_score(profile, candidate, facets):
    return sum(profile['facet_importance'][f] * dot(profile['vectors'][f],
                unit_vector({c:1 for c in facets[candidate][f]})) for f in FACETS)

def search_text_profiles(papers, history, searches, cutoff, recent_start=None, half_life_days=None):
    documents = {pid:r['title'] + ' ' + r['abstract'] for pid,r in papers.items()}
    documents.update({q['query_id']:q['text'] for q in searches})
    vectors = tfidf(documents)
    query_events = [dict(user_id=q['user_id'],paper_id=q['query_id'],interaction_type='click',
                         timestamp=q['timestamp']) for q in searches]
    profiles = history_profiles(history + query_events,vectors,cutoff=cutoff,
                                recent_start=recent_start,half_life_days=half_life_days)
    return profiles,vectors


def direction_estimate(case, history, queries, exposures, facets, margin=.25, minimum_pairs=2, use_search=True):
    # Confidence is a heuristic evidence score, not a calibrated probability.
    anchor = facets[case['query_paper_id']]
    vocabulary = search_vocabulary(facets)
    output = dict.fromkeys(FACETS,'unknown')
    confidence = dict.fromkeys(FACETS,0.0)
    context = case.get('context_facet','problem')
    output[context],confidence[context] = 'similar',1.0
    reactions = {(r['exposure_id'],r['paper_id']):BEHAVIOR_WEIGHTS[r['interaction_type']]
                 for r in history if r['session_id'] == case['case_id']}
    contrasts = {f:[] for f in FACETS}
    for x in exposures:
        if x['session_id'] != case['case_id'] or len(x['paper_ids']) != 2:
            continue
        a,b = x['paper_ids']
        if (x['exposure_id'],a) not in reactions or (x['exposure_id'],b) not in reactions:
            continue
        for f in FACETS:
            if not anchor[f] or not facets[a][f] or not facets[b][f]:
                continue
            same_a,same_b = bool(anchor[f] & facets[a][f]),bool(anchor[f] & facets[b][f])
            comparable = all((None if not anchor[g] or not facets[a][g] else bool(anchor[g] & facets[a][g]))
                             == (None if not anchor[g] or not facets[b][g] else bool(anchor[g] & facets[b][g]))
                             for g in FACETS if g != f)
            if same_a != same_b and comparable:
                same,different = (a,b) if same_a else (b,a)
                contrasts[f].append(reactions[x['exposure_id'],different] - reactions[x['exposure_id'],same])
    for f,values in contrasts.items():
        if len(values) >= minimum_pairs:
            delta = sum(values)/(len(values)+2)
            if abs(delta) >= margin:
                output[f] = 'different' if delta > 0 else 'similar'
                confidence[f] = min(1,abs(delta)/3)
    if use_search:
        session_queries = sorted((q for q in queries if q['session_id'] == case['case_id']),
                                 key=lambda q:(validate_time(q['timestamp']),q['query_id']))
        for q in session_queries:
            for f,values in parse_search(q['text'],facets,vocabulary).items():
                if anchor[f] & values['exclude']:
                    output[f],confidence[f] = 'different',1.0
                elif anchor[f] & values['include']:
                    output[f],confidence[f] = 'similar',.8
                # A different concept alone is weak evidence; keep the behavioral estimate.
    return output,confidence

def intent_scores(case, weights, directions, vectors):
    anchor = case['query_paper_id']
    context = case.get('context_facet','problem')
    scores = {}
    for pid in case['candidate_ids']:
        if not vectors[anchor,context] or not vectors[pid,context]:
            scores[pid] = -1.0
            continue
        relevance = dot(vectors[anchor,context],vectors[pid,context])
        if relevance <= 0:
            scores[pid] = -1.0
            continue
        numerator,denominator = 0.0,0.0
        missing = False
        for f in FACETS:
            direction = directions.get(f,'unknown')
            if direction == 'ignore' or not weights.get(f,0):
                continue
            if not vectors[anchor,f]:
                continue
            if not vectors[pid,f]:
                missing = True
                break
            similarity = max(0,min(1,dot(vectors[anchor,f],vectors[pid,f])))
            numerator += weights[f] * (1-similarity if direction == 'different' else similarity)
            denominator += weights[f]
        scores[pid] = -1.0 if missing else numerator/denominator if denominator else relevance
    return scores
