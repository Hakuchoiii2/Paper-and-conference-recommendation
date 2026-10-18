"""Nested real-candidate pools for a separate D v2 diagnostic.

Keep every v1 episode and its intent/query/observation. Only replace outside-context
candidates with additional different-focus candidates; never manufacture papers.
"""
import copy
import random


def expand(cases, intents, designs, facets, api, max_different=5):
    if type(max_different) is not int or not 1 <= max_different <= 5:
        raise ValueError('max_different must be an integer in [1, 5]')
    truth = {row['case_id']: row for row in intents}
    available = {(d['anchor'], d['context'], d['focus']): d for d in designs}
    output, metadata, pools = [], [], {}
    for original in cases:
        case = copy.deepcopy(original)
        intent = truth[case['case_id']]
        key = case['query_paper_id'], case['context_facet'], intent['focus_facet']
        design = available[key]
        old = case['candidate_ids']
        same = set(old) & set(design['same'])
        different = set(old) & set(design['different'])
        outside = set(old) & set(design['outside'])
        if (len(old) != 20 or len(set(old)) != 20 or len(same) != 1
                or len(different) != 1 or len(outside) != 18):
            raise ValueError('Expected an unmodified v1 pool with roles 1/1/18')
        # One pool across both directions and all three query modes.
        if key not in pools:
            rng = random.Random('D-multicandidate-v2:' + ':'.join(key))
            count = min(max_different, len(design['different'])) - 1
            additions = rng.sample(sorted(set(design['different']) - different), count)
            removed = rng.sample(sorted(outside), count)
            replacements = dict(zip(removed, additions))
            pool = [replacements.get(pid, pid) for pid in old]
            pools[key] = (list(old), pool, additions, removed)
        saved_old, pool, additions, removed = pools[key]
        if old != saved_old:
            raise ValueError('v1 paired episodes must share exactly the same pool')
        case['candidate_ids'] = list(pool)
        output.append(case)
        n = len(different) + len(additions)
        metadata.append(dict(case_id=case['case_id'], anchor=key[0], context=key[1], focus=key[2],
                             same_count=1, different_count=n, outside_count=19-n,
                             available_different=len(design['different']),
                             added_ids=list(additions), removed_outside_ids=list(removed),
                             expanded=n > 1))
    labels = []
    for case in output:
        intent = truth[case['case_id']]
        focus = intent['focus_facet']
        for pid in case['candidate_ids']:
            labels.append(dict(case_id=case['case_id'], candidate_id=pid,
                               relevance=api['session_grade'](
                                   facets[case['query_paper_id']], facets[pid], focus,
                                   intent['directions'][focus], case['context_facet'])))
    return output, labels, metadata
