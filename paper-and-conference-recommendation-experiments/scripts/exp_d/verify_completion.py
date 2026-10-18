"""Read-only replay of D completion outputs; writes a NEW review directory."""
import argparse
import json
from pathlib import Path
import numpy as np

from run_completion import (DATA, SOURCE, BASELINE, V2, CHANNELS, load_dataset,
    split_anchors, require, evaluate, mean_summary, comparisons, read, rows, write,
    digest, verify, features, predict, proposal, facet_vectors, load_silver,
    concept_sets, aggregate, focus_metrics)


def normalized(value):
    return json.loads(json.dumps(value))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run,output=args.run.resolve(),args.output.resolve()
    require(DATA in output.parents and not output.exists(),'Choose NEW review directory in D')
    manifest=read(run/'manifest.json')
    verify(run,manifest['files'])
    for path,h in manifest['input_hashes'].items():
        require(digest(Path(path))==h,'Changed protected input: '+path)
    registration=read(run/'registration.json')
    canonical,auxiliary=load_dataset(SOURCE/'data/exp_d'),load_dataset(V2)
    mapping=registration['global_anchor_split']
    require(mapping==split_anchors(canonical['cases'],auxiliary['cases']),'Split changed')
    config=read(SOURCE/'configs/exp_d.json')
    _,raw,metadata,_=load_silver(SOURCE,Path(config['facets_path']).parent)
    facets=concept_sets(raw,metadata);vectors=facet_vectors(facets)
    checks=dict(input_hashes=len(manifest['input_hashes']),output_hashes=len(manifest['files']),
                linear_test_predictions=0,validation_replays=0,proposal_replays=0,
                metric_bundles=0,summary_and_CI_replays=0)
    full=rows(run/'canonical/full/predictions.jsonl')
    base={(r['case_id'],r['model']):r for r in rows(BASELINE/'predictions.jsonl')}
    by_id={c['case_id']:c for c in canonical['cases']}
    for r in full:
        if r['model'].startswith('proposal_'):
            ch=r['model'].split('_')[1]
            require(r==proposal(by_id[r['case_id']],facets,vectors,base[r['case_id'],'direction_'+ch]),'Proposal replay differs')
            checks['proposal_replays']+=1
    full_ds=evaluate(canonical,full)
    require(normalized(full_ds)==rows(run/'canonical/full/details.jsonl'),'Full details mismatch')
    require(mean_summary([aggregate(full_ds)],[focus_metrics(full,canonical['truth'],canonical['groups'])])==
            read(run/'canonical/full_summary.json')['metrics'],'Full summary mismatch')
    fs=read(run/'canonical/full_summary.json')
    refs=[(f'proposal_{ch}_predicted',ref) for ch in CHANNELS for ref in
          ('fixed_similar','profile_similar','direction_'+ch,'oracle_intent')]
    require(comparisons(canonical,[full_ds],canonical['cases'],refs)==fs['comparisons'],'Full comparisons mismatch')
    checks['summary_and_CI_replays']+=1
    tables={'canonical_full':fs['metrics']}
    composition={}
    for dataset,bundle in (('canonical',canonical),('auxiliary',auxiliary)):
        conditions={'canonical':full} if dataset=='canonical' else {
            f'seed_{s}_noise_{n}':rows(V2/f'seed_{s}_noise_{n}/results/predictions.jsonl')
            for s in (42,43,44) for n in ('0.2','0.5')}
        split={s:[c for c in bundle['cases'] if mapping[c['query_paper_id']]==s]
               for s in ('train','validation','test')}
        require(not {c['query_paper_id'] for c in split['train']} &
                {c['query_paper_id'] for c in split['test']},'Train/test anchor leakage')
        composition[dataset]={s:dict(cases=len(cs),anchors=sorted({c['query_paper_id'] for c in cs}),
            focus_counts=dict(__import__('collections').Counter(bundle['truth'][c['case_id']]['focus_facet'] for c in cs)),
            ceiling={str(k):sum(min(k,sum(g==2 for g in bundle['labels'][c['case_id']].values()))/k
                               for c in cs)/len(cs) for k in (5,10)}) for s,cs in split.items()}
        lookups={name:{(r['case_id'],r['model']):r for r in ps} for name,ps in conditions.items()}
        models={ch:read(run/dataset/'models'/(ch+'.json')) for ch in CHANNELS}
        for ch,saved in models.items():
            model=saved['model']
            best=max(saved['trials'],key=lambda r:(round(r['validation_ndcg10'],12),r['l2']))
            require(model['l2']==best['l2'],'Selection rule mismatch')
            require(saved['train_anchors']==composition[dataset]['train']['anchors'],'Train anchors mismatch')
            train_x=[features(c,facets,vectors,lookups[name][c['case_id'],'direction_'+ch])
                     for name in conditions for c in split['train']]
            all_x=np.concatenate(train_x)
            scale=all_x.std(axis=0);scale[scale<1e-12]=1.
            np.testing.assert_array_equal(all_x.mean(axis=0),model['mean'])
            np.testing.assert_array_equal(scale,model['scale'])
            val_scores=[]
            for name in conditions:
                ps=[predict(c,lookups[name][c['case_id'],'direction_'+ch],
                    features(c,facets,vectors,lookups[name][c['case_id'],'direction_'+ch]),model)
                    for c in split['validation']]
                val_scores += [r['metrics']['ndcg@10'] for r in evaluate(bundle,ps,split['validation'])]
            require(abs(sum(val_scores)/len(val_scores)-best['validation_ndcg10'])<1e-12,'Validation score mismatch')
            checks['validation_replays']+=1
        details,summaries,fms={},{},{}
        for name in conditions:
            destination=run/dataset/'heldout'/name
            ps=rows(destination/'predictions.jsonl')
            expected={(r['case_id'],r['model']):r for r in ps}
            require({r['case_id'] for r in ps}=={c['case_id'] for c in split['test']},'Non-test prediction')
            for c in split['test']:
                for ch,saved in models.items():
                    b=lookups[name][c['case_id'],'direction_'+ch]
                    replay=predict(c,b,features(c,facets,vectors,b),saved['model'])
                    require(replay==expected[c['case_id'],replay['model']],'Linear prediction replay mismatch')
                    checks['linear_test_predictions']+=1
            ds=evaluate(bundle,ps,split['test']);ss=aggregate(ds)
            fm=focus_metrics(ps,bundle['truth'],bundle['groups'])
            require(normalized(ds)==rows(destination/'details.jsonl'),'Held-out details mismatch')
            require(ss==read(destination/'summary.json'),'Held-out summary mismatch')
            require(fm==read(destination/'focus_metrics.json'),'Focus metrics mismatch')
            details[name],summaries[name],fms[name]=ds,ss,fm
            checks['metric_bundles']+=1
        groups={'canonical':['canonical']} if dataset=='canonical' else {
            'noise_'+n:[f'seed_{s}_noise_{n}' for s in (42,43,44)] for n in ('0.2','0.5')}
        saved=read(run/dataset/'heldout_summary.json')
        refs=[(f'linear_ranknet_{ch}',ref) for ch in CHANNELS for ref in
              ('profile_similar',f'direction_{ch}',f'proposal_{ch}_predicted')]
        for group,names in groups.items():
            require(saved[group]['metrics']==mean_summary([summaries[n] for n in names],[fms[n] for n in names]),'Seed mean mismatch')
            require(saved[group]['comparisons']==comparisons(bundle,[details[n] for n in names],split['test'],refs),'CI mismatch')
            tables[dataset+'_'+group]=saved[group]['metrics']
            checks['summary_and_CI_replays']+=1
    output.mkdir(parents=True,exist_ok=False)
    write(output/'verification.json',dict(checks,passed=True,train_only_scaling=True,
          test_only_learned_results=True,previously_seen_data=True,semantic_relevance_validated=False))
    write(output/'subset_composition.json',composition)
    write(output/'report_tables.json',tables)
    write(output/'manifest.json',dict(run_manifest_sha256=digest(run/'manifest.json'),
          verifier_sha256=digest(Path(__file__)),files={p.name:digest(p) for p in output.iterdir() if p.is_file()}))
    print(json.dumps(checks,indent=2))
    print('VERIFIED '+str(run))


if __name__=='__main__':
    main()
