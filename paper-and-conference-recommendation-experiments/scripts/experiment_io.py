"""Verified A handoff and versioned mock artifacts; standard library only."""
import json
import re
import sys
from pathlib import Path
from build_corpus import normalize,read_jsonl,write_jsonl
from download_sources import ROOT,sha256,write_json
from validate_all import require
sys.path.insert(0,str(ROOT / 'data/exp_a'))
import build_exp_a as annotation

FACETS = annotation.FACET_NAMES
CONTRACT_VERSION = '2.0'
BEHAVIOR_FILES = ('interactions_train.jsonl','search_events.jsonl','exposures.jsonl')
FUTURE_FILES = ('interactions_test.jsonl','search_events_test.jsonl','exposures_test.jsonl')
FILES = {
    'b': (('retrieval_queries.jsonl','splits.json'),('retrieval_labels.jsonl','label_provenance.jsonl')),
    'c': (('users.jsonl',*BEHAVIOR_FILES,'cases.jsonl'),('latent_user_profiles.jsonl',*FUTURE_FILES)),
    'd': (('sessions.jsonl',*BEHAVIOR_FILES),('session_intents.jsonl','intent_labels.jsonl')),
    'e': ((*BEHAVIOR_FILES,'cases.jsonl'),('temporal_profiles.jsonl',*FUTURE_FILES,'period_metadata.json')),
}

def project_path(root, value):
    root = Path(root).resolve()
    path = (root / value).resolve()
    require(path == root or root in path.parents,f'Path must stay inside project: {value}')
    return path

def load_silver(root, directory, complete=True):
    root = Path(root)
    directory = project_path(root,directory)
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    config = dict(max_new_tokens=2048,max_attempts=3,**manifest['provenance']['config'])
    require(project_path(root,config['output_dir']) == directory,'A output path differs from provenance config')
    require(project_path(root,config['corpus']) == root.resolve() / 'data/processed/papers.jsonl',
            'A must use the canonical corpus')
    for field in ('corpus','prompt','guideline'):
        project_path(root,config[field])
    annotation.check_outputs(root,config,allow_partial=not complete)
    papers = sorted(read_jsonl(root / config['corpus']),key=lambda r:r['paper_id'])
    return ({r['paper_id']:r for r in papers},
            {r['paper_id']:r for r in read_jsonl(directory / 'facets_silver.jsonl')},
            {r['paper_id']:r for r in read_jsonl(directory / 'annotation_metadata.jsonl')},manifest)

def concept_sets(facets, metadata):
    return {pid:{f:set(filter(None,(normalize(v) for v in row[f]))) for f in FACETS}
            for pid,row in sorted(facets.items())
            if not metadata[pid].get('fallback_used') and not metadata[pid].get('validation_errors')}

def check_users(users):
    require(users and all(set(r) == {'user_id'} and isinstance(r['user_id'],str)
                         and re.fullmatch(r'U[0-9]{4}',r['user_id']) for r in users),'Invalid observable users')
    require(len({r['user_id'] for r in users}) == len(users),'Duplicate user IDs')

def input_paths(config, experiment, config_path):
    directory = Path(config['facets_path']).parent
    paths = [config_path,config['corpus_path'],config['facets_path'],
             (directory / 'annotation_metadata.jsonl').as_posix(),(directory / 'manifest.json').as_posix()]
    if experiment in ('d','e'):
        parent = Path(config['users_path']).parent
        paths += [config['users_path'],(parent / 'manifest.json').as_posix()]
        if experiment == 'd':
            paths += [(parent / name).as_posix() for name in BEHAVIOR_FILES]
    return sorted(paths)

def load_users(root, config):
    path = project_path(root,config['users_path'])
    users = read_jsonl(path)
    check_users(users)
    manifest = json.loads((path.parent / 'manifest.json').read_text(encoding='utf-8'))
    require(manifest['experiment'] == 'c' and manifest['dataset_kind'] == 'mock'
            and manifest['contract_version'] == CONTRACT_VERSION and manifest['status'] == 'complete',
            'D/E require the new C user handoff (contract 2.0)')
    key = path.relative_to(Path(root).resolve()).as_posix()
    require(manifest['files'].get(key) == sha256(path),'C users checksum mismatch')
    require(manifest['counts']['users.jsonl'] == len(users),'C user count differs')
    for name,value in {**manifest['input_hashes'],**manifest['files']}.items():
        require(sha256(project_path(root,name)) == value,f'C handoff checksum mismatch: {name}')
    require(manifest['generator_hashes'] == {name:sha256(ROOT / name) for name in generator_files('c')},
            'C generator changed; rebuild C before D/E')
    for name in ('corpus_path','facets_path'):
        require(manifest['config'][name] == config[name],'C/D/E input paths differ')
    return sorted(users,key=lambda r:r['user_id'])

def output_paths(root, config, experiment):
    output,hidden = (project_path(root,config[k]) for k in ('output_dir','truth_dir'))
    base = project_path(root,f'data/exp_{experiment}')
    require(base in output.parents and base in hidden.parents,'Outputs must stay in their experiment folder')
    require(output != hidden and output not in hidden.parents and hidden not in output.parents,
            'Observable and truth directories must be separate')
    return output,hidden

def generator_files(experiment):
    return ('data/build_experiments.py','data/experiment_common.py',
            f'data/exp_{experiment}/build_exp_{experiment}.py','scripts/experiment_io.py','scripts/build_corpus.py')

def write_dataset(root, config, experiment, observable, truth, report, inputs):
    # shortcut: dataset generation is single-writer; add a lock before parallel runs on one output.
    output,hidden = output_paths(root,config,experiment)
    if (output / 'manifest.json').exists():
        old = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
        require(old.get('contract_version') == CONTRACT_VERSION,
                'Legacy dataset preserved; choose new output_dir/truth_dir for contract 2.0')
    for directory,names in ((output,FILES[experiment][0]),(hidden,FILES[experiment][1])):
        if directory.exists():
            allowed = set(names) | {'manifest.json','generation_report.json','.gitkeep'}
            require(all(p.is_file() and not p.is_symlink() and p.name in allowed for p in directory.iterdir()),
                    'Dataset directory has unrelated files; use new output/truth directories')
    files = {}
    for directory,values in ((output,observable),(hidden,truth)):
        for name,rows in values.items():
            path = directory / name
            (write_jsonl if name.endswith('.jsonl') else write_json)(path,rows)
            files[path.relative_to(root).as_posix()] = sha256(path)
    write_json(output / 'generation_report.json',report)
    files[(output / 'generation_report.json').relative_to(root).as_posix()] = sha256(output / 'generation_report.json')
    manifest = dict(contract_version=CONTRACT_VERSION,generator_version=CONTRACT_VERSION,dataset_kind='mock',
                    experiment=experiment,seed=config['seed'],config=config,
                    generator_hashes={name:sha256(ROOT / name) for name in generator_files(experiment)},
                    input_hashes={name:sha256(project_path(root,name)) for name in inputs},
                    files=files,counts={name:len(rows) for values in (observable,truth)
                                       for name,rows in values.items() if name.endswith('.jsonl')},
                    status='partial' if report.get('shortfall',0) else 'complete')
    write_json(output / 'manifest.json',manifest)
    return manifest
