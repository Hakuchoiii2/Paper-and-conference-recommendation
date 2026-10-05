"""Shared dataset generation CLI; experiment-specific builders live under data/exp_*."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

import argparse
import json
import random

from data.experiment_common import (affinity, facet_relevance, intent_satisfaction,
                                    validate_sampling, validate_simulator)
from data.exp_b.build_exp_b import build_b
from data.exp_c.build_exp_c import build_c, validate_templates
from data.exp_d.build_exp_d import build_d
from data.exp_e.build_exp_e import build_e
from experiment_io import (ROOT, concept_sets, input_paths, load_silver, load_users,
                           output_paths, project_path, write_dataset)
from validate_all import require

def generate(root, experiment, config_path=None, dry_run=False):
    root = Path(root).resolve()
    require(experiment in ('b','c','d','e'), 'Unknown experiment')
    config_path = config_path or f'configs/exp_{experiment}.json'
    config = json.loads(project_path(root, config_path).read_text(encoding='utf-8'))
    require(config['dataset_kind'] == 'mock', 'B–E generators create mock datasets only')
    require(type(config['seed']) is int and config['seed'] >= 0, 'Invalid seed')
    require(project_path(root,config['corpus_path']) == root/'data/processed/papers.jsonl', 'Use the canonical corpus')
    output_paths(root, config, experiment)
    source = Path(config['facets_path']).parent.as_posix()
    require(Path(config['facets_path']).name == 'facets_silver.jsonl', 'Use verified A facets_silver.jsonl')
    papers, raw, metadata, _ = load_silver(root, source)
    facets = concept_sets(raw, metadata)
    rng = random.Random(config['seed'])
    users, templates = None, None
    if experiment in ('b','c'):
        validate_sampling(config, 'num_queries' if experiment == 'b' else 'num_cases',
                          'candidates_per_query' if experiment == 'b' else 'candidates_per_case')
        if experiment == 'c':
            templates = json.loads(project_path(root,config['templates_path']).read_text(encoding='utf-8'))
            validate_templates(templates,config['num_cases'])
    else:
        validate_simulator(config)
        if experiment == 'e':
            users = load_users(root,config)
    targets = ({'queries':config['num_queries'],'pairs':config['num_queries']*config['candidates_per_query']}
               if experiment == 'b' else {'cases':config['num_cases'],'pairs':config['num_cases']*config['candidates_per_case']}
               if experiment == 'c' else {'users':config['num_users'],'events':config['num_users']*config['events_per_user']}
               if experiment == 'd' else {'users':len(users),'profiles':len(users)*4,
                                         'events':len(users)*4*config['events_per_user_per_period']})
    if dry_run:
        return dict(experiment=experiment, targets=targets, corpus_count=len(papers),
                    clean_annotated_count=len(facets), excluded_flagged_count=len(raw)-len(facets))
    if experiment == 'b':
        observed, truth, report = build_b(facets,config,rng)
    elif experiment == 'c':
        observed, truth, report = build_c(facets,config,templates,rng)
    elif experiment == 'd':
        observed, truth, report = build_d(facets,config,rng)
    else:
        observed, truth, report = build_e(facets,users,config,rng)
    report.update(excluded_flagged_count=len(raw)-len(facets), targets=targets)
    manifest = write_dataset(root,config,experiment,observed,truth,report,input_paths(config,experiment,config_path))
    from validate_experiments import validate_experiment
    validate_experiment(root,experiment,config_path,allow_shortfall=True)
    return manifest


def run(experiment=None):
    parser = argparse.ArgumentParser(description=__doc__)
    if experiment is None:
        parser.add_argument('--experiment', choices=['b','c','d','e'], required=True)
    parser.add_argument('--config')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--dry-run', action='store_true')
    modes.add_argument('--validate-only', action='store_true')
    parser.add_argument('--allow-shortfall', action='store_true', help='Permit explicit partial output in validation')
    args = parser.parse_args()
    experiment = experiment or args.experiment
    try:
        if args.validate_only:
            from validate_experiments import validate_experiment
            manifest = validate_experiment(ROOT,experiment,args.config,allow_shortfall=args.allow_shortfall)
        else:
            manifest = generate(ROOT,experiment,args.config,args.dry_run)
        if args.dry_run:
            print(f"DRY RUN {experiment.upper()}: {json.dumps(manifest,ensure_ascii=False)}; no output written")
        else:
            print(f"{manifest['status'].upper()} {experiment.upper()}: {json.dumps(manifest['counts'],ensure_ascii=False)}")
            if manifest['status'] == 'partial' and not args.allow_shortfall:
                parser.exit(2, 'Target shortfall recorded in generation_report.json; partial output is not complete.\n')
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f"EXPERIMENT {experiment.upper()} FAILED: {error}\n")

if __name__ == '__main__':
    run()
