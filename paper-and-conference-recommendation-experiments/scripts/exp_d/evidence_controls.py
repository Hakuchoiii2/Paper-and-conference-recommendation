"""Public direction interventions and reproducible, within-session feedback controls."""
import copy
import hashlib
import random
from collections import defaultdict


def anchor_split(cases):
    anchors = sorted({c['query_paper_id'] for c in cases},
                     key=lambda a: hashlib.sha256(('D-evidence-v1:' + a).encode()).hexdigest())
    a, b = round(len(anchors) * .6), round(len(anchors) * .8)
    mapping = {pid: split for split, ids in [('development', anchors[:a]),
               ('validation', anchors[a:b]), ('audit', anchors[b:])] for pid in ids}
    return mapping


def select_panel(cases):
    by_anchor = defaultdict(list)
    for case in cases:
        by_anchor[case['query_paper_id']].append(case)
    selected = []
    for anchor in sorted(by_anchor):
        selected += sorted(by_anchor[anchor], key=lambda c: hashlib.sha256(
            ('D-panel-v1:' + c['case_id']).encode()).hexdigest())[:3]
    return sorted(selected, key=lambda c: c['case_id'])


def shuffle_actions(events, seed):
    """Only permute action types; IDs, exposures, times and per-session counts stay fixed."""
    result = copy.deepcopy(events)
    groups = defaultdict(list)
    for i, event in enumerate(result):
        groups[event['session_id']].append(i)
    for session, indices in sorted(groups.items()):
        actions = [result[i]['interaction_type'] for i in indices]
        random.Random(f'D-shuffle-v1:{seed}:{session}').shuffle(actions)
        for index, action in zip(indices, actions):
            result[index]['interaction_type'] = action
    return result


def direction_controls(case, facets, vectors, baseline, api):
    """No truth argument. Same selected focus, confidence, C weights and scorer per family.

    Strict family: original protocol scorer and missingness/gate, change focus direction only.
    M0 family: fixed priority scorer and direction-independent tie key (always-similar score).
    Focus-unknown/tied sessions use identical baseline fallback in every arm.
    """
    focus = api['observed_focus'](case['context_facet'], baseline['directions'], baseline['direction_confidence'])
    channel = baseline['model'].removeprefix('direction_')
    neutral = api['intent_scores'](case, baseline['facet_importance'],
                                 dict.fromkeys(baseline['directions'], 'similar'), vectors)
    result = []
    for family in ('strict', 'm0'):
        for arm in ('predicted', 'similar', 'flipped'):
            changed = copy.deepcopy(baseline)
            directions = changed['directions']
            if focus:
                if arm == 'similar':
                    directions[focus] = 'similar'
                elif arm == 'flipped':
                    directions[focus] = 'different' if directions[focus] == 'similar' else 'similar'
            if focus is None:
                row = copy.deepcopy(baseline)
            elif family == 'strict':
                row = api['ranked'](case, 'temporary', api['intent_scores'](
                    case, changed['facet_importance'], directions, vectors))
                row.update(directions=directions, direction_confidence=changed['direction_confidence'],
                           facet_importance=changed['facet_importance'])
            else:
                # Never leak predicted direction via the baseline score used to break tier ties.
                changed['ranking'] = api['ranked'](case, 'neutral', neutral)['ranking']
                row = api['rerank'](case, facets, vectors, changed, 'priority')
            row.update(model=f'{family}_{channel}_{arm}', predicted_focus=focus,
                       intervention=arm, family=family, fallback_to_baseline=focus is None)
            assert row['facet_importance'] == baseline['facet_importance']
            assert row['directions'][case['context_facet']] == baseline['directions'][case['context_facet']]
            result.append(row)
    return result
