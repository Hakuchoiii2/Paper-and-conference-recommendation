"""Data/metric diagnostics after fixed evaluation; no fitting or selection."""
import argparse
import collections
from pathlib import Path
from run_completion import (DATA,SOURCE,read,rows,write,digest,require,load_dataset,
    load_silver,concept_sets,aggregate)
from data.experiment_common import session_grade


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run=args.run.resolve();output=args.output.resolve()
    require(DATA in output.parents and not output.exists(),'Use NEW diagnostics directory in D')
    b=load_dataset(SOURCE/'data/exp_d')
    config=read(SOURCE/'configs/exp_d.json')
    _,raw,meta,_=load_silver(SOURCE,Path(config['facets_path']).parent)
    facets=concept_sets(raw,meta);counts=collections.Counter()
    for c in b['cases']:
        t=b['truth'][c['case_id']];f=t['focus_facet'];ctx=c['context_facet']
        direction=t['directions'][f];counts[direction+'_sessions']+=1
        grades=b['labels'][c['case_id']]
        if direction=='different' and 1 not in grades.values():
            counts['different_sessions_without_grade1']+=1
        for pid,g in grades.items():
            opposite='different' if direction=='similar' else 'similar'
            flipped=session_grade(facets[c['query_paper_id']],facets[pid],f,opposite,ctx)
            require((g==flipped==0) or g+flipped==3,'Counterfactual symmetry failed')
            counts['counterfactual_label_checks']+=1
            if facets[c['query_paper_id']][ctx] & facets[pid][ctx]:
                counts['context_overlap_grade_'+str(g)]+=1
    analyses={}
    for name,relative in (('canonical_full','canonical/full/details.jsonl'),
                           ('canonical_heldout','canonical/heldout/canonical/details.jsonl')):
        details=rows(run/relative)
        for r in details:
            t=b['truth'][r['case_id']]
            r['groups'] += ['intent_'+t['directions'][t['focus_facet']], 'focus_'+t['focus_facet']]
        analyses[name]=aggregate(details)
    output.mkdir(parents=True,exist_ok=False)
    write(output/'canonical_pool_audit.json',dict(counts,interpretation=
          'Counterfactual rule consistency, not saved matched opposite sessions or human relevance; no new method'))
    write(output/'group_metrics.json',analyses)
    write(output/'manifest.json',dict(run_manifest_sha256=digest(run/'manifest.json'),
          script_sha256=digest(Path(__file__)),files={x.name:digest(x) for x in output.iterdir() if x.is_file()}))
    print(dict(counts))


if __name__=='__main__':main()
