"""Read-only canonical audit plus separately labelled synthetic direction/evidence controls.

No training/tuning. Anchor partitions are retrospective audits, NOT untouched test data.
"""
import argparse
import collections
import csv
import importlib.util
import json
from pathlib import Path
import random
import sys

from run_improve_trial import read, rows, digest, verify, write, write_rows, focus_metrics
from evidence_controls import anchor_split, select_panel, shuffle_actions, direction_controls

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]


def bootstrap(deltas, cases, samples=2000):
    by_anchor = collections.defaultdict(list)
    for case, delta in zip(cases, deltas):
        if delta is not None:
            by_anchor[case['query_paper_id']].append(delta)
    if not by_anchor:
        return dict(mean=None, ci95=None, anchors=0)
    values = list(by_anchor.values())
    rng = random.Random(20261016)
    means = []
    for _ in range(samples):
        draws = [rng.choice(values) for _ in values]
        means.append(sum(sum(x) for x in draws) / sum(len(x) for x in draws))
    means.sort()
    flat = [x for xs in values for x in xs]
    return dict(mean=sum(flat) / len(flat), ci95=[means[int(.025*samples)], means[int(.975*samples)]],
                anchors=len(values), cases=len(flat), wins=sum(x > 1e-12 for x in flat),
                ties=sum(abs(x) <= 1e-12 for x in flat), losses=sum(x < -1e-12 for x in flat),
                bootstrap_samples=samples, inference_scope='conditional on this fixed simulator configuration')


def evaluate(name, cases, original, truth, labels, facets, vectors, split, output, api):
    public = [r for r in original if r['model'] in ('direction_behavior', 'direction_search')]
    by_id = {c['case_id']: c for c in cases}
    additions = [row for base in public for row in direction_controls(
        by_id[base['case_id']], facets, vectors, base, api)]
    predictions = original + additions
    judged = {cid: {} for cid in by_id}
    for row in labels:
        judged[row['case_id']][row['candidate_id']] = row['relevance']
    groups = {cid: t['query_mode'] for cid, t in truth.items()}
    details = api['evaluate_predictions'](predictions, cases, judged, groups, [5, 10], truth)
    for row in details:
        case, t = by_id[row['case_id']], truth[row['case_id']]
        row['groups'] += ['intent_' + t['directions'][t['focus_facet']], 'focus_' + t['focus_facet'],
                          'anchor_' + split[case['query_paper_id']]]
    summary = api['aggregate'](details)
    output.mkdir(parents=True, exist_ok=False)
    write_rows(output / 'predictions.jsonl', predictions)
    write_rows(output / 'details.jsonl', details)
    write(output / 'focus_metrics.json', focus_metrics(predictions, truth, groups))
    report = dict(experiment='d', dataset_kind='mock' if name == 'canonical' else 'synthetic_observation_overlay',
                  dataset_status='retrospective_audit', protocol='d_evidence_controls_v1', cases=len(cases),
                  summary=summary, notes=[
                      'Strict family preserves protocol C weights, scorer, missingness and context gate.',
                      'Only the selected observed focus direction changes; context and unknowns are fixed.',
                      'M0 is an explicitly separate ranking-policy extension, not the canonical protocol scorer.',
                      'M0 ties use direction-independent all-similar scores in every intervention.',
                      'Anchor groups are retrospective; all canonical data have already been used in development.',
                      'Synthetic observations are not real papers or A silver; no user-realistic claim.',
                      'Bootstrap intervals condition on one seed/noise; seeds are not independent cohorts.'
                  ])
    write(output / 'report.json', report)
    (output / 'report.md').write_text(api['markdown_report'](report), encoding='utf-8')
    fields = ['model','group','cases','positive_cases'] + list(summary[0]['defined_cases'])
    with (output / 'summary.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(summary)
    lookup = {(r['case_id'], r['model']): r for r in details}
    comparisons = []
    for family in ('strict','m0'):
        for channel in ('behavior','search'):
            for control in ('similar','flipped'):
                predicted=f'{family}_{channel}_predicted';reference=f'{family}_{channel}_{control}'
                for group in ('overall','intent_similar','intent_different','anchor_development','anchor_validation','anchor_audit'):
                    selected=[c for c in cases if group=='overall' or group in lookup[c['case_id'],predicted]['groups']]
                    for metric in ('ndcg@10','intent_compliance@5'):
                        deltas=[]
                        for c in selected:
                            a=lookup[c['case_id'],predicted]['metrics'][metric]
                            b=lookup[c['case_id'],reference]['metrics'][metric]
                            deltas.append(a-b if a is not None and b is not None else None)
                        comparisons.append(dict(condition=name,model=predicted,reference=reference,group=group,
                                                 metric=metric,**bootstrap(deltas,selected)))
    write(output/'paired_comparisons.json',comparisons)
    # Representative selection is deterministic after evaluation; explicitly a case analysis.
    case_studies=[]
    for family in ('strict','m0'):
        ranked_cases=[]
        for c in cases:
            a=lookup[c['case_id'],f'{family}_search_predicted'];b=lookup[c['case_id'],f'{family}_search_similar']
            delta=a['metrics']['intent_compliance@5']-b['metrics']['intent_compliance@5']
            ranked_cases.append((delta,c['case_id']))
        for category,predicate in [('gain',lambda x:x>1e-12),('tie',lambda x:abs(x)<=1e-12),('loss',lambda x:x < -1e-12)]:
            eligible=sorted((x,cid) for x,cid in ranked_cases if predicate(x))
            if eligible:
                delta,cid=eligible[-1] if category=='gain' else eligible[0]
                case_studies.append(dict(family=family,category=category,case=by_id[cid],truth=truth[cid],
                    compliance_delta=delta,predicted=lookup[cid,f'{family}_search_predicted'],
                    similar=lookup[cid,f'{family}_search_similar']))
    write(output/'case_studies.json',case_studies)
    print(f'PASS {name}: {len(cases)} cases, {len(predictions)} predictions',flush=True)
    return comparisons


def shuffled_focus(cases, facets, exposures, events, queries, config, originals, api, output):
    by_id={c['case_id']:c for c in cases}
    records=[]
    # Public predictions are produced before evaluator receives truth.
    for seed in range(10):
        shuffled=shuffle_actions(events,seed)
        assert collections.Counter((e['session_id'],e['interaction_type']) for e in events)==collections.Counter(
            (e['session_id'],e['interaction_type']) for e in shuffled)
        changed=sum(a['interaction_type']!=b['interaction_type'] for a,b in zip(events,shuffled))
        for case in cases:
            cutoff=api['validate_time'](case['cutoff'])
            prefix=lambda data:[r for r in data if r['session_id']==case['case_id'] and api['validate_time'](r['timestamp'])<cutoff]
            directions,confidence=api['direction_estimate'](case,prefix(shuffled),[],prefix(exposures),facets,
                margin=config['direction_margin'],minimum_pairs=config['min_direction_pairs'],use_search=False)
            records.append(dict(case_id=case['case_id'],replicate=seed,directions=directions,
                                direction_confidence=confidence,model='shuffled_behavior',changed_actions=changed))
    write_rows(output/'shuffled_direction_predictions.jsonl',records)
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=HERE/'results/evidence_20261016_v1')
    args=parser.parse_args();output=args.output.resolve()
    source=HERE/'workspace_baseline_20261016_v1';baseline=HERE/'results/baseline_20261016_v1'
    pilot_root=HERE/'results/baseline_20261016_v1_synthetic'
    if output.exists() or (HERE/'results') not in output.parents:
        raise ValueError('Output must be a NEW child of exp_d/results')
    sys.path[:0]=[str(source/'scripts'),str(source),str(PROJECT/'scripts/exp_d')]
    from validate_experiments import validate_experiment,check_d
    from experiment_io import FACETS,load_silver,concept_sets
    from baseline_common import facet_vectors,facet_profiles,direction_estimate,intent_scores,ranked,aggregate
    from experiment_runner import evaluate_predictions,markdown_report
    from validate_all import validate_time
    from data.experiment_common import behavior,session_grade,timestamp
    from intent_priority import observed_focus,rerank
    import run_synthetic_observation_pilot as pilot
    api=dict(FACETS=FACETS,check_d=check_d,validate_time=validate_time,behavior=behavior,session_grade=session_grade,
             timestamp=timestamp,facet_profiles=facet_profiles,direction_estimate=direction_estimate,
             intent_scores=intent_scores,ranked=ranked,aggregate=aggregate,evaluate_predictions=evaluate_predictions,
             markdown_report=markdown_report,observed_focus=observed_focus,rerank=rerank)
    validated=validate_experiment(source,'d');config=validated['config']
    bm=read(baseline/'manifest.json');pm=read(pilot_root/'manifest.json')
    for base,hashes in [(source,bm['input_hashes']),(source,bm['code_hashes']),
                        (baseline,bm['files']),(source,pm['source_hashes']),(pilot_root,pm['files'])]:verify(base,hashes)
    watched={p:digest(p) for root in (source,baseline,pilot_root) for p in root.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    for p in (PROJECT/'docs/EXPERIMENT_PROTOCOL.md',HERE/'README.md',PROJECT/'scripts/exp_d/run_exp_d.py',
              PROJECT/'scripts/baseline_common.py',HERE/'run_synthetic_observation_pilot.py'):
        watched[p]=digest(p)
    _,raw,metadata,_=load_silver(source,Path(config['facets_path']).parent)
    facets=concept_sets(raw,metadata);vectors=facet_vectors(facets)
    data=source/'data/exp_d';cases=rows(data/'generated/sessions.jsonl')
    truth={r['case_id']:r for r in rows(data/'ground_truth/session_intents.jsonl')}
    labels=rows(data/'ground_truth/intent_labels.jsonl');queries=rows(data/'generated/search_events.jsonl')
    original=rows(baseline/'predictions.jsonl');split=anchor_split(cases)
    panel=select_panel(cases);ids={c['case_id'] for c in panel}
    output.mkdir(parents=True,exist_ok=False)
    write(output/'design.json',dict(primary='strict fixed-scorer direction ablation',secondary='M0 neutral tie-key ablation',
        seeds=[42,43,44],noise=[.2,.5],shuffle_replicates=10,bootstrap_samples=2000,
        split_policy='SHA256 D-evidence-v1, 60/20/20 by anchor, retrospective audit only',anchor_split=split,
        panel_policy='up to 3 cases per anchor by SHA256 D-panel-v1; no metric/label selection',
        panel_case_ids=sorted(ids),no_training_or_parameter_selection=True))
    comparisons=evaluate('canonical',cases,original,truth,labels,facets,vectors,split,output/'canonical',api)
    handoff=source/Path(config['users_path']).parent
    ch=rows(handoff/'interactions_train.jsonl');cq=rows(handoff/'search_events.jsonl');users=rows(source/config['users_path'])
    # Expanded overlay keeps 171 canonical sessions/candidates/labels intact, including every anchor.
    pt={cid:truth[cid] for cid in ids};pl=[r for r in labels if r['case_id'] in ids];pq=[r for r in queries if r['session_id'] in ids]
    panel_root=output/'expanded_overlay';(panel_root/'generated').mkdir(parents=True)
    (panel_root/'ground_truth').mkdir()
    write_rows(panel_root/'generated/sessions.jsonl',panel);write_rows(panel_root/'generated/search_events.jsonl',pq)
    write_rows(panel_root/'ground_truth/session_intents.jsonl',list(pt.values()));write_rows(panel_root/'ground_truth/intent_labels.jsonl',pl)
    control=pilot.public_predictions(panel,facets,facets,ch,cq,pq,[],[],config,vectors,api)
    existing_control={(r['case_id'],r['model']):r for r in original if r['case_id'] in ids and not r['model'].startswith('oracle')}
    assert {(r['case_id'],r['model']):r for r in control}==existing_control
    write_rows(panel_root/'no_observations_predictions.jsonl',control)
    comparisons+=evaluate('expanded_no_observations',panel,control,pt,pl,facets,vectors,split,
                          output/'expanded_no_observations',api)
    focus_summary=[]
    for seed in (42,43,44):
        for noise in (.2,.5):
            name=f'seed_{seed}_noise_{noise:g}';run=panel_root/name
            sf,prov,ex,ev=pilot.make_observations(panel,pt,facets,pq,config,seed,noise,4,api)
            pilot.validate_overlay(panel,pt,pl,pq,facets,sf,prov,ex,ev,users,config,4,api)
            assert (sf,prov,ex,ev)==pilot.make_observations(panel,pt,facets,pq,config,seed,noise,4,api)
            (run/'generated').mkdir(parents=True);(run/'ground_truth').mkdir()
            write_rows(run/'generated/exposures.jsonl',ex);write_rows(run/'generated/interactions_train.jsonl',ev)
            write_rows(run/'generated/observation_facets.jsonl',[dict(paper_id=pid,**{f:sorted(v) for f,v in row.items()}) for pid,row in sorted(sf.items())])
            write_rows(run/'ground_truth/observation_provenance.jsonl',prov)
            augmented=pilot.public_predictions(panel,facets,{**facets,**sf},ch,cq,pq,ex,ev,config,vectors,api)
            for model in ('fixed_similar','profile_similar'):
                assert [r for r in control if r['model']==model]==[r for r in augmented if r['model']==model]
            comparisons+=evaluate(name,panel,augmented,pt,pl,facets,vectors,split,run/'results',api)
            shuffled=shuffled_focus(panel,{**facets,**sf},ex,ev,pq,config,augmented,api,run/'results')
            cohorts=[('aligned',[r for r in augmented if r['model']=='direction_behavior'],None),
                     ('no_observations',[r for r in control if r['model']=='direction_behavior'],None)]
            cohorts += [('shuffled',[r for r in shuffled if r['replicate']==rep],rep) for rep in range(10)]
            for arm,predictions,rep in cohorts:
                pairs=[(pt[r['case_id']]['directions'][pt[r['case_id']]['focus_facet']],
                        r['directions'][pt[r['case_id']]['focus_facet']]) for r in predictions]
                focus_summary.append(dict(condition=name,arm=arm,replicate=rep,cases=len(pairs),
                    accuracy=sum(t==p for t,p in pairs)/len(pairs),
                    coverage=sum(p in ('similar','different') for t,p in pairs)/len(pairs)))
    write(output/'paired_comparisons.json',comparisons);write(output/'focus_evidence.json',focus_summary)
    if any(digest(p)!=h for p,h in watched.items()):raise ValueError('Protected input changed')
    code=[Path(__file__),HERE/'evidence_controls.py',HERE/'run_improve_trial.py',
          HERE/'run_synthetic_observation_pilot.py',PROJECT/'scripts/exp_d/intent_priority.py']
    write(output/'manifest.json',dict(protocol='d_evidence_controls_v1',canonical_protocol='2.0',
        synthetic_protocol='d_synthetic_observation_overlay_v1 extension, never canonical A silver',source_unchanged=True,
        input_hashes={str(p):h for p,h in watched.items()},code_hashes={str(p.relative_to(PROJECT)):digest(p) for p in code},
        files={p.relative_to(output).as_posix():digest(p) for p in sorted(output.rglob('*')) if p.is_file()}))
    print('EVIDENCE SUITE COMPLETE: '+str(output),flush=True)


if __name__=='__main__':main()
