"""Real-paper contrast episodes, separate from canonical D. No fabricated candidate facets."""
import datetime as dt
import hashlib
import random


def feasible_designs(facets, api):
    index=api['facet_index'](facets);designs=[]
    for anchor,row in sorted(facets.items()):
        overlap={f:api['overlapping'](index,f,row[f]) for f in api['FACETS'] if row[f]}
        for context in overlap:
            for focus in overlap:
                if context==focus:continue
                related={pid for pid in overlap[context]-{anchor} if facets[pid][focus]}
                same=related&overlap[focus];different=related-overlap[focus]
                if not same or not different:continue
                outside={pid for pid,r in facets.items() if pid!=anchor and r[context] and r[focus]
                         and not r[context]&row[context]}
                if len(outside)>=18:
                    designs.append(dict(anchor=anchor,context=context,focus=focus,
                                        same=sorted(same),different=sorted(different),outside=sorted(outside)))
    return designs


def build(designs,facets,users,api):
    sessions=[];truth=[];labels=[];queries=[];pairs=[]
    for i,design in enumerate(designs):
        anchor,context,focus=(design[k] for k in ('anchor','context','focus'))
        rng=random.Random(f'D-contrast-pool-v1:{anchor}:{context}:{focus}')
        pool=[rng.choice(design['same']),rng.choice(design['different'])]+rng.sample(design['outside'],18)
        rng.shuffle(pool)
        for j,mode in enumerate(('clear','ambiguous','none')):
            group=f'PAIR_{i:03}_{j}';user=users[(3*i+j)%len(users)]['user_id']
            cutoff=dt.datetime(2026,3,1,tzinfo=dt.timezone.utc)+dt.timedelta(minutes=3*i+j+1)
            for direction in ('similar','different'):
                cid='DC_'+hashlib.sha256((group+direction).encode()).hexdigest()[:16]
                session=dict(case_id=cid,user_id=user,query_paper_id=anchor,context_facet=context,
                             candidate_ids=list(pool),cutoff=api['timestamp'](cutoff))
                dirs=dict.fromkeys(api['FACETS'],'ignore');dirs[context]='similar';dirs[focus]=direction
                weights=dict.fromkeys(api['FACETS'],0.);weights[context]=.6;weights[focus]=.4
                # Simulator chooses intent before generating language/actions/labels.
                intent=dict(case_id=cid,focus_facet=focus,directions=dirs,facet_importance=weights,query_mode=mode)
                sessions.append(session);truth.append(intent)
                labels += [dict(case_id=cid,candidate_id=pid,relevance=api['session_grade'](
                    facets[anchor],facets[pid],focus,direction,context)) for pid in pool]
                previous=None
                if mode!='none':
                    concept=sorted(facets[anchor][context])[0]
                    texts=[f'{context}: {concept} papers']
                    if mode=='clear':
                        focus_concept=sorted(facets[anchor][focus])[0]
                        phrase=f'alternatives to {focus_concept}' if direction=='different' else f'more papers using {focus_concept}'
                        texts.append(f'{context}: {concept}; {focus}: {phrase}')
                    for qi,text in enumerate(texts):
                        qid=cid+'Q'+str(qi)
                        queries.append(dict(query_id=qid,user_id=user,session_id=cid,text=text,parent_query_id=previous,
                                            timestamp=api['timestamp'](cutoff-dt.timedelta(seconds=60-qi))))
                        previous=qid
                pairs.append(dict(case_id=cid,pair_id=group,design_index=i,true_direction=direction,
                                  query_mode=mode,anchor=anchor,context=context,focus=focus))
    return sessions,truth,labels,queries,pairs
