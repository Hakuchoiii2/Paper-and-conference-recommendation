"""D (formerly C): infer session directions from searches and matched exposures."""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT_ROOT))
sys.path.insert(0,str(PROJECT_ROOT / 'scripts'))
import collections
import datetime as dt
from data.experiment_common import (FACETS,behavior,candidate_sample,facet_index,overlapping,
                                    sampled,session_grade,timestamp,validate_sampling)
from validate_all import require,validate_time

def build_d(facets, users, config, rng):
    validate_sampling(dict(config,num_cases=len(users)*config['sessions_per_user']),
                      'num_cases','candidates_per_case')
    require(type(config['observation_pairs']) is int and config['observation_pairs'] >= 0,'Invalid observation_pairs')
    require(type(config['sessions_per_user']) is int and config['sessions_per_user'] > 0,'Invalid sessions_per_user')
    require(type(config['noise_std']) in (int,float) and 0 <= config['noise_std'] <= 1,'Invalid noise_std')
    index = facet_index(facets)
    anchors = sorted(pid for pid,row in facets.items() if sum(bool(row[f]) for f in FACETS) >= 2)
    require(anchors,'D needs at least two facets on an anchor')
    sessions, intents, labels, events, queries, exposures = [], [], [], [], [], []
    skipped = collections.Counter()
    # Enumerate feasible session designs once, before balancing focus selection.
    # Feasibility uses the existing pools/labels, not relaxed concept matching.
    eligible_by_pair = {(context,focus): {pid for pid,row in facets.items()
                         if row[context] and row[focus]}
                        for context in FACETS for focus in FACETS if context != focus}
    designs = {direction: collections.defaultdict(list) for direction in ('similar','different')}
    positive_capacity = {}
    for anchor in anchors:
        available = [f for f in FACETS if facets[anchor][f]]
        overlaps = {f: overlapping(index,f,facets[anchor][f]) for f in available}
        for context in available:
            for focus in available:
                if focus == context:
                    continue
                eligible = eligible_by_pair[context,focus] - {anchor}
                related = overlaps[context] & eligible
                same = overlaps[focus] & eligible
                for direction in designs:
                    positive = related & same if direction == 'similar' else related - same
                    if positive and len(eligible) > len(positive) and len(eligible) >= config['candidates_per_case']:
                        design = (anchor,context,focus)
                        designs[direction][focus].append(design)
                        positive_capacity[direction,design] = min(len(positive),config['candidates_per_case'] - 1,
                            max(1,round(config['candidates_per_case'] * config['positive_fraction'])))
                    else:
                        skipped['infeasible_design'] += 1
    focus_counts, context_counts, design_counts = collections.Counter(), collections.Counter(), collections.Counter()
    start = validate_time(config['start_timestamp'])
    for user_row in users:
        user = user_row['user_id']
        used_anchors = set()
        made = 0
        for _ in range(config['sessions_per_user']):
            direction = 'similar' if len(sessions) % 2 == 0 else 'different'
            available_designs = {f:[d for d in rows if d[0] not in used_anchors]
                                 for f,rows in designs[direction].items()}
            available_focus = [f for f in FACETS if available_designs.get(f)]
            if not available_focus:
                skipped['no_unused_feasible_anchor'] += 1
                break
            minimum = min(focus_counts[direction,f] for f in available_focus)
            focus = rng.choice([f for f in available_focus if focus_counts[direction,f] == minimum])
            choices = available_designs[focus]
            # Fill the configured positive quota where the original corpus permits it.
            # Do not relabel negatives or sacrifice focus balance to inflate this count.
            capacity = max(positive_capacity[direction,d] for d in choices)
            choices = [d for d in choices if positive_capacity[direction,d] == capacity]
            usage = min(design_counts[direction,d] for d in choices)
            choices = [d for d in choices if design_counts[direction,d] == usage]
            minimum_context = min(context_counts[d[1]] for d in choices)
            anchor,context,focus = rng.choice([d for d in choices if context_counts[d[1]] == minimum_context])
            eligible = eligible_by_pair[context,focus] - {anchor}
            same_problem = overlapping(index,context,facets[anchor][context]) & eligible
            same_focus = overlapping(index,focus,facets[anchor][focus]) & eligible
            positive = same_problem & same_focus if direction == 'similar' else same_problem - same_focus
            negative = eligible - positive
            candidates = candidate_sample(positive,negative,same_problem - positive,
                                          config['candidates_per_case'],config,rng)
            if candidates is None:
                skipped['insufficient_candidate_pool'] += 1
                continue
            sid = f'D{len(sessions)+1:05}'
            time = start + dt.timedelta(days=made)
            mode = ('clear','ambiguous','none')[len(sessions) % 3]
            previous = None
            if mode != 'none':
                concept_context = rng.choice(sorted(facets[anchor][context]))
                texts = [f'{context}: ' + rng.choice((concept_context, f'{concept_context} papers'))]
                if mode == 'clear':
                    concept = rng.choice(sorted(facets[anchor][focus]))
                    templates = ('alternatives to {}','without {}','excluding {}','instead of {}','not using {}') \
                                if direction == 'different' else ('more papers using {}','{} papers','{}')
                    texts.append(f'{context}: {concept_context}; {focus}: ' + rng.choice(templates).format(concept))
                for qi,text in enumerate(texts):
                    qid = f'{sid}Q{qi}'
                    queries.append(dict(query_id=qid,user_id=user,session_id=sid,text=text,
                                        parent_query_id=previous,timestamp=timestamp(time + dt.timedelta(seconds=qi))))
                    previous = qid
            # Match the other facets' overlap states; mere method variety is not direction evidence.
            groups = collections.defaultdict(lambda: {True:[],False:[]})
            for pid in sorted(same_problem - set(candidates)):
                signature = tuple(None if not facets[anchor][f] or not facets[pid][f]
                                  else bool(facets[anchor][f] & facets[pid][f])
                                  for f in FACETS if f != focus)
                groups[signature][pid in same_focus].append(pid)
            pairs = []
            for signature in sorted(groups,key=str):
                left,right = groups[signature][True],groups[signature][False]
                rng.shuffle(left); rng.shuffle(right)
                pairs.extend(zip(left,right))
            rng.shuffle(pairs)
            for ei,pair in enumerate(pairs[:config['observation_pairs']]):
                shown = list(pair)
                rng.shuffle(shown)
                xtime = time + dt.timedelta(seconds=10 + ei*5)
                xid = f'{sid}X{ei}'
                exposures.append(dict(exposure_id=xid,user_id=user,session_id=sid,query_id=previous,
                                      paper_ids=shown,timestamp=timestamp(xtime)))
                for pi,pid in enumerate(shown):
                    grade = session_grade(facets[anchor],facets[pid],focus,direction,context)
                    utility = (.7 if grade == 2 else .05) + rng.gauss(0,config['noise_std'])
                    events.append(dict(user_id=user,paper_id=pid,interaction_type=behavior(utility,config),
                                       timestamp=timestamp(xtime + dt.timedelta(seconds=pi+1)),
                                       session_id=sid,exposure_id=xid))
            cutoff = timestamp(time + dt.timedelta(seconds=20 + config['observation_pairs']*5))
            sessions.append(dict(case_id=sid,user_id=user,query_paper_id=anchor,context_facet=context,candidate_ids=candidates,cutoff=cutoff))
            directions = {f:'ignore' for f in FACETS}
            directions[context],directions[focus] = 'similar',direction
            weights = dict.fromkeys(FACETS,0.0)
            weights[context],weights[focus] = .6,.4
            intents.append(dict(case_id=sid,focus_facet=focus,directions=directions,
                                facet_importance=weights,query_mode=mode))
            labels.extend(dict(case_id=sid,candidate_id=pid,relevance=session_grade(
                facets[anchor],facets[pid],focus,direction,context)) for pid in candidates)
            made += 1
            used_anchors.add(anchor)
            focus_counts[direction,focus] += 1
            context_counts[context] += 1
            design_counts[direction,(anchor,context,focus)] += 1
    report = dict(shortfall=len(users)*config['sessions_per_user'] - len(sessions),
                  actual_cases=len(sessions),actual_pairs=len(labels),skipped=dict(skipped),
                  focus_counts={direction:{f:focus_counts[direction,f] for f in FACETS}
                                for direction in designs},
                  context_counts=dict(context_counts),
                  feasible_design_counts={direction:{f:len(rows) for f,rows in by_focus.items()}
                                          for direction,by_focus in designs.items()},
                  positive_pool_policy='maximize_configured_quota_within_balanced_focus',
                  maximum_positive_capacity={direction:{f:max(positive_capacity[direction,d] for d in rows)
                                                       for f,rows in by_focus.items()}
                                             for direction,by_focus in designs.items()},
                  unique_anchors=len({row['query_paper_id'] for row in sessions}),
                  mean_intent_candidates=sum(row['relevance'] == 2 for row in labels)/len(sessions) if sessions else 0,
                  behavior_counts=dict(collections.Counter(r['interaction_type'] for r in events)))
    return ({'sessions.jsonl':sessions,'interactions_train.jsonl':events,
             'search_events.jsonl':queries,'exposures.jsonl':exposures},
            {'session_intents.jsonl':intents,'intent_labels.jsonl':labels},report)

if __name__ == '__main__':
    from data.build_experiments import run
    run('d')
