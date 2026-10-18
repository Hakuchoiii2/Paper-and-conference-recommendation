"""Feasibility audit only: real 1-same/9-different/10-outside candidate pools."""
import collections
import sys
from pathlib import Path

from run_improve_trial import read, rows, write, write_rows, digest

PROJECT=Path(__file__).resolve().parents[2]
DATA=PROJECT/'data/exp_d'


def main():
    source=DATA/'workspace_baseline_20261016_v1'
    output=DATA/'evaluation/contrast_feasibility_v1'
    if output.exists():raise ValueError('Audit output already exists')
    sys.path[:0]=[str(source/'scripts'),str(source)]
    from validate_experiments import validate_experiment
    from experiment_io import load_silver,concept_sets,FACETS
    from data.experiment_common import facet_index,overlapping
    m=validate_experiment(source,'d');config=m['config']
    _,raw,metadata,_=load_silver(source,Path(config['facets_path']).parent)
    facets=concept_sets(raw,metadata);index=facet_index(facets)
    seen=set()
    for p in [DATA/'generated/sessions.jsonl',source/'data/exp_d/generated/sessions.jsonl']:
        if p.exists():seen.update(r['query_paper_id'] for r in rows(p))
    designs=[]
    eligible={(c,f):{pid for pid,row in facets.items() if row[c] and row[f]}
              for c in FACETS for f in FACETS if c!=f}
    for anchor,row in sorted(facets.items()):
        overlaps={f:overlapping(index,f,row[f]) for f in FACETS if row[f]}
        for context in overlaps:
            for focus in overlaps:
                if focus==context:continue
                pool=eligible[context,focus]-{anchor}
                related=overlaps[context]&pool
                same=related&overlaps[focus];different=related-overlaps[focus];outside=pool-related
                if same and len(different)>=9 and len(outside)>=10:
                    designs.append(dict(anchor=anchor,context=context,focus=focus,same=len(same),
                                        different=len(different),outside=len(outside),previously_evaluated=anchor in seen))
    output.mkdir(parents=True)
    write_rows(output/'feasible_designs.jsonl',designs)
    write_rows(output/'facets.jsonl',[dict(paper_id=pid,**{f:sorted(v) for f,v in row.items()}) for pid,row in sorted(facets.items())])
    report=dict(policy='one same-focus + nine different-focus + ten outside-context; real unique candidates only',
                designs=len(designs),anchors=len({r['anchor'] for r in designs}),
                previously_evaluated_anchors=len(seen),new_anchors=len({r['anchor'] for r in designs if not r['previously_evaluated']}),
                by_focus=dict(collections.Counter(r['focus'] for r in designs)),
                source=str(source),input_hashes=m['input_hashes'],source_files=m['files'],generator_hashes=m['generator_hashes'])
    write(output/'report.json',report)
    write(output/'manifest.json',dict(code_sha256=digest(Path(__file__)),files={p.name:digest(p) for p in output.iterdir() if p.is_file()}))
    print({k:report[k] for k in ('designs','anchors','previously_evaluated_anchors','new_anchors','by_focus')},flush=True)


if __name__=='__main__':main()
