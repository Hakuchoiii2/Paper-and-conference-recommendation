"""Complete D on immutable canonical/v2 inputs; fresh outputs, grouped held-out LTR.

Run: python -B scripts/exp_d/run_completion.py --output data/exp_d/results/completion_20261018_v1
The split and search space are written before fitting. Never refit on validation.
"""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_key] = '1'
import argparse
import collections
import datetime as dt
import hashlib
import sys
from pathlib import Path

from run_improve_trial import read, rows, write, write_rows, digest, verify, focus_metrics

PROJECT = Path(__file__).resolve().parents[2]
DATA = PROJECT/'data/exp_d'
SOURCE = DATA/'workspace_baseline_20261016_v1'
BASELINE = DATA/'results/baseline_20261016_v1'
V2 = DATA/'results/multicandidate_proposal_20261017_v2_verified'
sys.path[:0] = [str(SOURCE/'scripts'), str(SOURCE), str(DATA)]
from experiment_io import FACETS, load_silver, concept_sets
from baseline_common import aggregate, facet_vectors, facet_profiles, direction_estimate, intent_scores, ranked
from experiment_runner import evaluate_predictions
from validate_experiments import validate_experiment, check_d
from validate_all import validate_time
from data.experiment_common import timestamp
from proposal_ranker import predict as proposal
from linear_ranknet import features, fit, predict, FEATURE_NAMES
from run_evidence_suite import bootstrap
import run_synthetic_observation_pilot as pilot

METRICS = ('ndcg@10', 'intent_compliance@5', 'intent_compliance@10')
L2 = (.001, .01, .1)
CHANNELS = ('behavior', 'search')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def split_anchors(canonical, auxiliary):
    """One global mapping: even anchors shared by datasets cannot cross splits.

    Stratify only on public dataset membership so the 8-anchor auxiliary has
    nonempty train/validation/test; SHA ordering uses neither labels nor scores.
    """
    extra = {c['query_paper_id'] for c in auxiliary}
    all_ids = extra | {c['query_paper_id'] for c in canonical}
    mapping = {}
    for ids in (extra, all_ids-extra):
        ordered = sorted(ids, key=lambda a: hashlib.sha256(('D-RankNet-20261018:'+a).encode()).hexdigest())
        a, b = round(.6*len(ordered)), round(.8*len(ordered))
        for split, anchors in (('train', ordered[:a]), ('validation', ordered[a:b]), ('test', ordered[b:])):
            mapping.update(dict.fromkeys(anchors, split))
    return mapping


def load_dataset(path):
    cases = rows(path/'generated/sessions.jsonl')
    truth = {r['case_id']: r for r in rows(path/'ground_truth/session_intents.jsonl')}
    label_rows = rows(path/'ground_truth/intent_labels.jsonl')
    judged = {c['case_id']: {} for c in cases}
    for r in label_rows:
        judged[r['case_id']][r['candidate_id']] = r['relevance']
    return dict(cases=cases, truth=truth, label_rows=label_rows, labels=judged,
                groups={cid:t['query_mode'] for cid,t in truth.items()},
                queries=rows(path/'generated/search_events.jsonl'))


def audit_dataset(bundle, facets, users, config, path, auxiliary=False):
    """Data-only checks; no predictions or model metrics are used here."""
    cases, truth, judged = (bundle[k] for k in ('cases', 'truth', 'labels'))
    require(len({c['case_id'] for c in cases}) == len(cases), 'Duplicate case ID')
    require(len(bundle['label_rows']) == sum(len(c['candidate_ids']) for c in cases), 'Duplicate/missing labels')
    for c in cases:
        require(len(c['candidate_ids']) == len(set(c['candidate_ids'])) == 20, 'Duplicate candidate')
        require(c['query_paper_id'] not in c['candidate_ids'], 'Anchor in pool')
        anchor, intent = facets[c['query_paper_id']], truth[c['case_id']]
        f, ctx = intent['focus_facet'], c['context_facet']
        for pid in c['candidate_ids']:
            candidate = facets[pid]
            complete = bool(anchor[ctx] and anchor[f] and candidate[ctx] and candidate[f])
            related = complete and bool(anchor[ctx] & candidate[ctx])
            same = bool(anchor[f] & candidate[f])
            # Independent expression, not session_grade or any model score.
            expected = (2 if same == (intent['directions'][f] == 'similar') else 1) if related else 0
            require(judged[c['case_id']][pid] == expected, 'Independent label-rule mismatch')
    observed = {'sessions.jsonl': cases, 'search_events.jsonl': bundle['queries'],
                'exposures.jsonl': [], 'interactions_train.jsonl': []}
    report = dict(shortfall=len(users)*config['sessions_per_user']-len(cases),
                  actual_cases=len(cases), actual_pairs=len(bundle['label_rows']))
    check_d(observed, {'session_intents.jsonl': list(truth.values()),
                      'intent_labels.jsonl': bundle['label_rows']}, facets, config, report, users)
    pair_count, overlays = 0, 0
    if auxiliary:
        grouped = collections.defaultdict(list)
        by_id = {c['case_id']:c for c in cases}
        for p in rows(path/'ground_truth/paired_designs.jsonl'):
            grouped[p['pair_id']].append(by_id[p['case_id']])
        for pair in grouped.values():
            require(len(pair) == 2, 'Incomplete paired intent')
            a,b = pair
            require({k:v for k,v in a.items() if k != 'case_id'} ==
                    {k:v for k,v in b.items() if k != 'case_id'}, 'Paired public inputs differ')
            ta,tb = truth[a['case_id']],truth[b['case_id']]
            f = ta['focus_facet']
            require(f == tb['focus_facet'] and {ta['directions'][f],tb['directions'][f]} ==
                    {'similar','different'}, 'Paired intent mismatch')
            for pid in a['candidate_ids']:
                ga,gb = judged[a['case_id']][pid],judged[b['case_id']][pid]
                require((ga == gb == 0) or ga+gb == 3, 'Opposite-intent label asymmetry')
            pair_count += 1
        api = dict(check_d=check_d)
        for name in [f'seed_{s}_noise_{n}' for s in (42,43,44) for n in ('0.2','0.5')]:
            run = path/name
            synthetic = {r['paper_id']:{f:set(r[f]) for f in FACETS}
                         for r in rows(run/'generated/observation_facets.jsonl')}
            provenance = rows(run/'ground_truth/observation_provenance.jsonl')
            for p in provenance:
                # Verify each constructed facet against its recorded real donor.
                for f in FACETS:
                    donor = p['focus_donor_id'] if f == p['true_focus'] else p['source_anchor_id']
                    require(synthetic[p['paper_id']][f] == facets[donor][f], 'Provenance reconstruction mismatch')
            exposures = rows(run/'generated/exposures.jsonl')
            events = rows(run/'generated/interactions_train.jsonl')
            require(len({e['exposure_id'] for e in exposures}) == len(exposures), 'Duplicate exposure ID')
            require(len({(e['exposure_id'],e['paper_id']) for e in events}) == len(events), 'Duplicate reaction')
            pilot.validate_overlay(cases, truth, bundle['label_rows'], bundle['queries'], facets,
                                   synthetic, provenance, exposures, events, users, config, 4, api)
            overlays += 1
    return dict(cases=len(cases), anchors=len({c['query_paper_id'] for c in cases}),
                independent_rule_labels=len(bundle['label_rows']), paired_intents=pair_count,
                overlays_checked=overlays, cutoff_matching_separation=True,
                semantic_relevance_validated=False,
                ceiling={str(k):sum(min(k,sum(g==2 for g in judged[c['case_id']].values()))/k
                                   for c in cases)/len(cases) for k in (5,10)})


def evaluate(bundle, predictions, selected=None):
    cases = selected if selected is not None else bundle['cases']
    ids = {c['case_id'] for c in cases}
    return evaluate_predictions([r for r in predictions if r['case_id'] in ids], cases,
                                bundle['labels'], bundle['groups'], [5,10], bundle['truth'])


def save_bundle(destination, bundle, predictions, cases=None):
    destination.mkdir(parents=True, exist_ok=False)
    selected = cases if cases is not None else bundle['cases']
    details = evaluate(bundle, predictions, selected)
    write_rows(destination/'predictions.jsonl', predictions)
    write_rows(destination/'details.jsonl', details)
    summary = aggregate(details)
    write(destination/'summary.json', summary)
    fm = focus_metrics(predictions, bundle['truth'], bundle['groups'])
    write(destination/'focus_metrics.json', fm)
    return details, summary, fm


def comparisons(bundle, conditions, cases, refs):
    """Average seeds per case before cluster bootstrap; each condition is same pool."""
    lookups = [{(r['case_id'],r['model']):r for r in ds} for ds in conditions]
    result = []
    for model, reference in refs:
        for metric in METRICS:
            values = [sum(d[c['case_id'],model]['metrics'][metric]-d[c['case_id'],reference]['metrics'][metric]
                          for d in lookups)/len(lookups) for c in cases]
            result.append(dict(model=model, reference=reference, metric=metric,
                               seeds_averaged=len(conditions), **bootstrap(values,cases)))
    return result


def mean_summary(summaries, focus):
    result = []
    models = sorted({r['model'] for r in summaries[0]})
    for model in models:
        rs = [next(r for r in s if r['model']==model and r['group']=='overall') for s in summaries]
        fs = [next(r for r in s if r['model']==model and r['group']=='overall') for s in focus]
        result.append(dict(model=model, cases=rs[0]['cases'],
                           **{k:sum(r[k] for r in rs)/len(rs) for k in (*METRICS,'direction_macro_f1')},
                           **{k:sum(r[k] for r in fs)/len(fs) for k in
                              ('focus_accuracy','focus_coverage','focus_macro_f1')}))
    return result


def learning(dataset_name, bundle, conditions, facets, vectors, mapping, output):
    """Two signal sources of ONE linear model; no test score read during selection."""
    split_cases = {s:[c for c in bundle['cases'] if mapping[c['query_paper_id']]==s]
                   for s in ('train','validation','test')}
    require(all(split_cases.values()), 'Insufficient split')
    learned = {name:[] for name in conditions}
    budgets = {}
    for channel in CHANNELS:
        lookup = {name:{r['case_id']:r for r in predictions if r['model']=='direction_'+channel}
                  for name,predictions in conditions.items()}
        # Public feature creation precedes attaching train-only target labels.
        cache = {(name,c['case_id']):features(c,facets,vectors,lookup[name][c['case_id']])
                 for name in conditions for c in bundle['cases']}
        train = [(cache[name,c['case_id']], [bundle['labels'][c['case_id']][p] for p in c['candidate_ids']])
                 for name in conditions for c in split_cases['train']]
        trials = []
        winner = None
        for l2 in L2:
            model = fit(train, l2)
            validation_scores = []
            for name in conditions:
                ps = [predict(c,lookup[name][c['case_id']],cache[name,c['case_id']],model)
                      for c in split_cases['validation']]
                validation_scores += [r['metrics']['ndcg@10'] for r in evaluate(bundle,ps,split_cases['validation'])]
            score = sum(validation_scores)/len(validation_scores)
            trials.append(dict(l2=l2, validation_ndcg10=score, loss=model['loss'], iterations=model['iterations']))
            # Predeclared tie rule: prefer larger regularization, no test metrics.
            key = (round(score,12),l2)
            if winner is None or key > winner[0]:
                winner = (key,model)
        destination = output/dataset_name/'models'
        destination.mkdir(parents=True,exist_ok=True)
        model = winner[1]
        write(destination/(channel+'.json'), dict(model=model, trials=trials,
              selection='maximum validation mean nDCG@10; ties at 12 decimals prefer larger L2; no refit',
              train_anchors=sorted({c['query_paper_id'] for c in split_cases['train']}),
              validation_anchors=sorted({c['query_paper_id'] for c in split_cases['validation']})))
        # Only now generate the registered held-out test predictions.
        for name in conditions:
            learned[name] += [predict(c,lookup[name][c['case_id']],cache[name,c['case_id']],model)
                              for c in split_cases['test']]
        budgets[channel] = dict(unique_train_sessions=len(split_cases['train']),
                                unique_train_labels=20*len(split_cases['train']),
                                repeated_observation_conditions=len(conditions),
                                unequal_pair_instances=model['unequal_pairs'],selected_l2=model['l2'])
        print(f'FIT {dataset_name}/{channel}: validation={winner[0][0]:.6f}, L2={model["l2"]}',flush=True)
    results = {}
    detail_sets = {}
    for name,original in conditions.items():
        ids = {c['case_id'] for c in split_cases['test']}
        predictions = [r for r in original if r['case_id'] in ids] + learned[name]
        ds,ss,fm = save_bundle(output/dataset_name/'heldout'/name,bundle,predictions,split_cases['test'])
        detail_sets[name] = ds
        results[name] = (ss,fm)
    refs = [(f'linear_ranknet_{ch}',ref) for ch in CHANNELS for ref in
            ('profile_similar',f'direction_{ch}',f'proposal_{ch}_predicted')]
    groups = {'canonical':['canonical']} if dataset_name=='canonical' else {
        'noise_'+n:[f'seed_{s}_noise_{n}' for s in (42,43,44)] for n in ('0.2','0.5')}
    report = {}
    for group,names in groups.items():
        report[group] = dict(scope='held-out anchors outside training; previously seen development data',
            cases=len(split_cases['test']), anchors=len({c['query_paper_id'] for c in split_cases['test']}),
            metrics=mean_summary([results[n][0] for n in names],[results[n][1] for n in names]),
            comparisons=comparisons(bundle,[detail_sets[n] for n in names],split_cases['test'],refs))
    write(output/dataset_name/'heldout_summary.json', report)
    write(output/dataset_name/'label_budget.json',budgets)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(DATA in output.parents and not output.exists(), 'Choose NEW output below data/exp_d')
    canonical,auxiliary = load_dataset(SOURCE/'data/exp_d'),load_dataset(V2)
    mapping = split_anchors(canonical['cases'],auxiliary['cases'])
    output.mkdir(parents=True,exist_ok=False)
    registration = dict(created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        prior_data_seen=True, scope='retrospective grouped held-out evaluation, not untouched test',
        global_anchor_split=mapping, split_rule='SHA256 D-RankNet-20261018 + anchor; 60/20/20 within auxiliary-membership strata',
        split_counts={name:{s:dict(anchors=len({c['query_paper_id'] for c in b['cases'] if mapping[c['query_paper_id']]==s}),
                                  sessions=sum(mapping[c['query_paper_id']]==s for c in b['cases']))
                           for s in ('train','validation','test')} for name,b in
                      (('canonical',canonical),('auxiliary',auxiliary))},
        primary='nDCG@10', l2_grid=list(L2), selection='validation nDCG@10 only; tie at 12 decimals prefer larger L2',
        model='linear score, RankNet pairwise logistic, no ties, session-balanced, train-only scaling, L-BFGS maxiter400',
        sources=list(CHANNELS), auxiliary_fit='one model per channel pooled across 3 seeds x 2 noises on train anchors',
        no_refit_on_validation=True, features=FEATURE_NAMES,
        reference='https://www.microsoft.com/en-us/research/wp-content/uploads/2005/08/icml_ranking.pdf',
        source_equations='1-3, section 3; paper also reports a linear net in sections 5-6',
        adapted='D features/interactions, L2 grid, session weights, scaling, optimizer, grouped split and cutoff 10')
    write(output/'registration.json',registration)
    old_manifest=read(BASELINE/'manifest.json')
    verify(SOURCE,old_manifest['input_hashes']);verify(SOURCE,old_manifest['code_hashes'])
    verify(BASELINE,old_manifest['files'])
    from run_multicandidate_proposal import verify_run
    verify_run(V2)
    validated=validate_experiment(SOURCE,'d');config=validated['config']
    _,raw,metadata,_=load_silver(SOURCE,Path(config['facets_path']).parent)
    facets=concept_sets(raw,metadata);vectors=facet_vectors(facets)
    users=rows(SOURCE/config['users_path'])
    audit={name:audit_dataset(b,facets,users,config,path,aux) for name,b,path,aux in
           (('canonical',canonical,SOURCE/'data/exp_d',False),('auxiliary',auxiliary,V2,True))}
    write(output/'data_audit.json',audit)
    print('PASS data-only audit: labels, provenance, cutoff, matching, IDs, paired symmetry',flush=True)
    watched={SOURCE/p:h for p,h in {**old_manifest['input_hashes'],**old_manifest['code_hashes']}.items()}
    for base in (BASELINE,V2):
        watched.update({p:digest(p) for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    v2manifest=read(V2/'manifest.json')
    watched.update({Path(p):h for p,h in v2manifest['input_hashes'].items()})
    for p in (Path(__file__),Path(__file__).with_name('linear_ranknet.py'),
              Path(__file__).with_name('proposal_ranker.py'),Path(__file__).with_name('intent_priority.py')):
        watched[p]=digest(p)
    original=rows(BASELINE/'predictions.jsonl')
    require(aggregate(evaluate(canonical,original))==read(BASELINE/'report.json')['summary'], 'Canonical metric replay differs')
    # Replay observable prefixes/profile C independently of saved predictions.
    api=dict(FACETS=FACETS,facet_profiles=facet_profiles,direction_estimate=direction_estimate,
             intent_scores=intent_scores,ranked=ranked,validate_time=validate_time)
    handoff=SOURCE/Path(config['users_path']).parent
    public=pilot.public_predictions(canonical['cases'],facets,facets,rows(handoff/'interactions_train.jsonl'),
        rows(handoff/'search_events.jsonl'),canonical['queries'],[],[],config,vectors,api)
    require(public==[r for r in original if r['model']!='oracle_intent'], 'Canonical public/profile replay differs')
    by_id={c['case_id']:c for c in canonical['cases']}
    proposals=[proposal(by_id[r['case_id']],facets,vectors,r) for r in public if r['model'].startswith('direction_')]
    full=original+proposals
    ds,ss,fm=save_bundle(output/'canonical/full',canonical,full)
    full_summary=mean_summary([ss],[fm])
    refs=[(f'proposal_{ch}_predicted',ref) for ch in CHANNELS for ref in
          ('fixed_similar','profile_similar','direction_'+ch,'oracle_intent')]
    write(output/'canonical/full_summary.json',dict(cases=1500,metrics=full_summary,
        comparisons=comparisons(canonical,[ds],canonical['cases'],refs),
        fallback_counts={f'proposal_{ch}_predicted':sum(r['fallback_to_baseline'] for r in proposals
                         if r['model']==f'proposal_{ch}_predicted') for ch in CHANNELS}))
    learning('canonical',canonical,{'canonical':full},facets,vectors,mapping,output)
    conditions={f'seed_{s}_noise_{n}':rows(V2/f'seed_{s}_noise_{n}/results/predictions.jsonl')
                for s in (42,43,44) for n in ('0.2','0.5')}
    learning('auxiliary',auxiliary,conditions,facets,vectors,mapping,output)
    require(all(digest(p)==h for p,h in watched.items()),'Protected input/code changed')
    write(output/'verification.json',dict(protected_hashes=len(watched),unchanged=True,
          canonical_public_replay=len(public),canonical_baseline_metrics_reproduced=True,
          reused_v2_full_verification=True,learned_full90_metrics_reported=False,
          split_registered_before_fit=True,semantic_relevance_validated=False))
    write(output/'manifest.json',dict(input_hashes={str(p):h for p,h in watched.items()},
          files={p.relative_to(output).as_posix():digest(p) for p in output.rglob('*') if p.is_file()}))
    print('COMPLETE '+str(output),flush=True)


if __name__=='__main__':
    main()
