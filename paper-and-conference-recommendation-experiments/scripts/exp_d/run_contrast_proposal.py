"""Prospectively fixed synthetic-episode contrast benchmark; preserves canonical artifacts."""
import collections
import csv
import json
from pathlib import Path
import sys

from run_improve_trial import read,rows,write,write_rows,digest,verify,focus_metrics
from run_evidence_suite import bootstrap
from evidence_controls import shuffle_actions,direction_controls

PROJECT=Path(__file__).resolve().parents[2];DATA=PROJECT/'data/exp_d'


def main():
    source=DATA/'workspace_baseline_20261016_v1';output=DATA/'results/contrast_proposal_20261016_v1'
    if output.exists():raise ValueError('Output exists; preserve prior run')
    output.mkdir(parents=True)
    write(output/'design.json',dict(registered_before_predictions=True,candidates=[1,1,18],
        pool_roles=['same-focus same-context','different-focus same-context','outside-context'],
        sampling='all feasible anchor/context/focus designs; pool shared across direction/query-mode; no metric selection',
        primary='ndcg@10, proposal predicted vs always-similar within the same ranker',
        secondary=['compliance@5/10','diagnostic compliance@1','flipped-direction control','strict original scorer'],
        seeds=[42,43,44],noise=[.2,.5],shuffle_replicates=10,bootstrap=2000,
        training=False,tuning=False,source_anchors='previously seen, NOT an independent generalization test',
        scope='real candidates + synthetic-only observation; separate mechanistic benchmark, not canonical replacement'))
    sys.path[:0]=[str(source/'scripts'),str(source),str(DATA),str(PROJECT/'scripts/exp_d')]
    from validate_experiments import validate_experiment,check_d
    from experiment_io import FACETS
    from baseline_common import facet_vectors,facet_profiles,direction_estimate,intent_scores,ranked,aggregate
    from experiment_runner import evaluate_predictions,markdown_report
    from validate_all import validate_time
    from data.experiment_common import facet_index,overlapping,session_grade,timestamp,behavior
    import build_contrast_sessions as builder
    import run_synthetic_observation_pilot as pilot
    from proposal_ranker import predict
    from intent_priority import observed_focus,rerank
    validated=validate_experiment(source,'d');config=validated['config']
    audit=DATA/'evaluation/contrast_feasibility_v1'
    verify(audit,read(audit/'manifest.json')['files'])
    verify(source,read(audit/'report.json')['input_hashes'])
    facets={r['paper_id']:{f:set(r[f]) for f in FACETS} for r in rows(audit/'facets.jsonl')}
    watched={p:digest(p) for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for p in (DATA/'README.md',PROJECT/'docs/EXPERIMENT_PROTOCOL.md',PROJECT/'scripts/baseline_common.py',
              PROJECT/'scripts/exp_d/run_exp_d.py',DATA/'run_synthetic_observation_pilot.py'):
        watched[p]=digest(p)
    api=dict(FACETS=FACETS,facet_index=facet_index,overlapping=overlapping,session_grade=session_grade,timestamp=timestamp,
        behavior=behavior,validate_time=validate_time,check_d=check_d,facet_profiles=facet_profiles,direction_estimate=direction_estimate,
        intent_scores=intent_scores,ranked=ranked,observed_focus=observed_focus,rerank=rerank)
    users=rows(source/config['users_path']);designs=builder.feasible_designs(facets,api)
    if not designs:raise ValueError('No feasible contrast designs; do not fabricate data')
    cases,intents,labels,queries,pairs=builder.build(designs,facets,users,api)
    truth={r['case_id']:r for r in intents};groups={r['case_id']:r['query_mode'] for r in intents}
    judged={c['case_id']:{} for c in cases}
    for r in labels:judged[r['case_id']][r['candidate_id']]=r['relevance']
    base_report=dict(shortfall=len(users)*config['sessions_per_user']-len(cases),actual_cases=len(cases),actual_pairs=len(labels))
    check_d({'sessions.jsonl':cases,'search_events.jsonl':queries,'exposures.jsonl':[],'interactions_train.jsonl':[]},
            {'session_intents.jsonl':intents,'intent_labels.jsonl':labels},facets,config,base_report,users)
    generated=output/'generated';hidden=output/'ground_truth';generated.mkdir();hidden.mkdir()
    write_rows(generated/'sessions.jsonl',cases);write_rows(generated/'search_events.jsonl',queries)
    write_rows(hidden/'session_intents.jsonl',intents);write_rows(hidden/'intent_labels.jsonl',labels)
    write_rows(hidden/'paired_designs.jsonl',pairs)
    write(output/'generation_report.json',dict(base_report,diagnostic_target=len(cases),designs=len(designs),
        anchors=len({c['query_paper_id'] for c in cases}),focus_counts=dict(collections.Counter(t['focus_facet'] for t in intents)),
        grade_counts=dict(collections.Counter(r['relevance'] for r in labels)),
        target_1500_status='partial diagnostic; never canonical complete',
        feasibility_initial_1same_9different_10outside='0 designs; changed quota BEFORE any metric evaluation'))
    vectors=facet_vectors(facets);handoff=source/Path(config['users_path']).parent
    ch=rows(handoff/'interactions_train.jsonl');cq=rows(handoff/'search_events.jsonl')
    control=pilot.public_predictions(cases,facets,facets,ch,cq,queries,[],[],config,vectors,api)
    all_stats=[];all_focus=[]

    def evaluate(name,public,destination):
        predictions=list(public);by_id={c['case_id']:c for c in cases}
        for base in public:
            if base['model'] not in ('direction_behavior','direction_search'):continue
            case=by_id[base['case_id']]
            predictions += [r for r in direction_controls(case,facets,vectors,base,api) if r['family']=='strict']
            predictions += [predict(case,facets,vectors,base,arm) for arm in ('predicted','similar','flipped')]
        for case in cases:
            t=truth[case['case_id']]
            oracle=ranked(case,'oracle_intent',intent_scores(case,t['facet_importance'],t['directions'],vectors))
            oracle.update(directions=t['directions'],facet_importance=t['facet_importance'],privileged_information=True)
            predictions.append(oracle)
        details=evaluate_predictions(predictions,cases,judged,groups,[1,5,10],truth)
        for r in details:
            t=truth[r['case_id']];r['groups']+=['intent_'+t['directions'][t['focus_facet']],'focus_'+t['focus_facet']]
        summary=aggregate(details);lookup={(r['case_id'],r['model']):r for r in details}
        destination.mkdir(parents=True,exist_ok=False)
        write_rows(destination/'predictions.jsonl',predictions);write_rows(destination/'details.jsonl',details)
        fm=focus_metrics(predictions,truth,groups);write(destination/'focus_metrics.json',fm)
        all_focus.extend(dict(r,condition=name) for r in fm)
        report=dict(experiment='d',dataset_kind='synthetic_observation_contrast_diagnostic',dataset_status='partial',
                    protocol='d_contrast_v1',cases=len(cases),summary=summary,notes=[
                        'Real candidates, paired opposite intents; all feasible designs, no metric-selected subset.',
                        'Synthetic observation only; not canonical data or A silver. 8 anchors limit generalization.',
                        'Original baseline scorer unchanged. Proposal differs in active-facet gate and priority.',
                        'Direction ablations hold the proposal gate, weights, focus and neutral tie key fixed.',
                        'Primary nDCG@10; compliance@1 is an extra diagnostic; @5/10 also retained.',
                        'No training, tuning or new unseen-corpus generalization claim.'
                    ])
        write(destination/'report.json',report)
        (destination/'report.md').write_text(markdown_report(report),encoding='utf-8')
        with (destination/'summary.csv').open('w',encoding='utf-8',newline='') as f:
            fields=['model','group','cases','positive_cases']+list(summary[0]['defined_cases'])
            writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(summary)
        stats=[]
        for family in ('strict','proposal'):
            for channel in ('behavior','search'):
                for reference in ('similar','flipped'):
                    a=f'{family}_{channel}_predicted';b=f'{family}_{channel}_{reference}'
                    for group in ('overall','intent_similar','intent_different','clear','ambiguous','none'):
                        selected=[c for c in cases if group=='overall' or group in lookup[c['case_id'],a]['groups']]
                        for metric in ('ndcg@10','intent_compliance@1','intent_compliance@5'):
                            deltas=[lookup[c['case_id'],a]['metrics'][metric]-lookup[c['case_id'],b]['metrics'][metric] for c in selected]
                            stats.append(dict(condition=name,model=a,reference=b,group=group,metric=metric,**bootstrap(deltas,selected)))
        write(destination/'paired_comparisons.json',stats);all_stats.extend(stats)
        print(f'PASS {name}: {len(cases)} cases, {len(predictions)} predictions',flush=True)
        return public

    evaluate('no_observations',control,output/'no_observations')
    shuffle_summary=[]
    for seed in (42,43,44):
        for noise in (.2,.5):
            name=f'seed_{seed}_noise_{noise:g}';run=output/name
            sf,prov,ex,ev=pilot.make_observations(cases,truth,facets,queries,config,seed,noise,4,api)
            pilot.validate_overlay(cases,truth,labels,queries,facets,sf,prov,ex,ev,users,config,4,api)
            (run/'generated').mkdir(parents=True);(run/'ground_truth').mkdir()
            write_rows(run/'generated/exposures.jsonl',ex);write_rows(run/'generated/interactions_train.jsonl',ev)
            write_rows(run/'generated/observation_facets.jsonl',[dict(paper_id=pid,**{f:sorted(v) for f,v in row.items()}) for pid,row in sorted(sf.items())])
            write_rows(run/'ground_truth/observation_provenance.jsonl',prov)
            observed={**facets,**sf}
            public=pilot.public_predictions(cases,facets,observed,ch,cq,queries,ex,ev,config,vectors,api)
            for model in ('fixed_similar','profile_similar'):
                assert [r for r in control if r['model']==model]==[r for r in public if r['model']==model]
            evaluate(name,public,run/'results')
            shuffle_predictions=[]
            for rep in range(10):
                shuffled=shuffle_actions(ev,rep)
                for case in cases:
                    prefix=lambda rs:[r for r in rs if r['session_id']==case['case_id'] and validate_time(r['timestamp'])<validate_time(case['cutoff'])]
                    dirs,conf=direction_estimate(case,prefix(shuffled),[],prefix(ex),observed,
                        margin=config['direction_margin'],minimum_pairs=config['min_direction_pairs'],use_search=False)
                    shuffle_predictions.append(dict(case_id=case['case_id'],model='shuffled_behavior',replicate=rep,directions=dirs))
            write_rows(run/'results/shuffled_directions.jsonl',shuffle_predictions)
            for rep in range(10):
                rs=[r for r in shuffle_predictions if r['replicate']==rep]
                accuracy=sum(r['directions'][truth[r['case_id']]['focus_facet']]==truth[r['case_id']]['directions'][truth[r['case_id']]['focus_facet']] for r in rs)/len(rs)
                coverage=sum(r['directions'][truth[r['case_id']]['focus_facet']] in ('similar','different') for r in rs)/len(rs)
                shuffle_summary.append(dict(condition=name,replicate=rep,accuracy=accuracy,coverage=coverage))
    write(output/'paired_comparisons.json',all_stats);write(output/'focus_metrics.json',all_focus)
    write(output/'shuffle_summary.json',shuffle_summary)
    if any(digest(p)!=h for p,h in watched.items()):raise ValueError('Protected source changed')
    code=[Path(__file__),DATA/'build_contrast_sessions.py',PROJECT/'scripts/exp_d/proposal_ranker.py',
          PROJECT/'scripts/exp_d/evidence_controls.py',DATA/'run_synthetic_observation_pilot.py']
    write(output/'manifest.json',dict(protocol='d_contrast_v1',source_unchanged=True,not_canonical=True,
        code_hashes={str(p.relative_to(PROJECT)):digest(p) for p in code},input_hashes={str(p):h for p,h in watched.items()},
        files={p.relative_to(output).as_posix():digest(p) for p in sorted(output.rglob('*')) if p.is_file()}))
    print('CONTRAST PROPOSAL COMPLETE: '+str(output),flush=True)


if __name__=='__main__':main()
