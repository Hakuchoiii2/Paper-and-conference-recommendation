"""Verified A inputs and deterministic experiment files; standard library only."""
import json
import re
import sys
from pathlib import Path

from build_corpus import normalize, read_jsonl, write_jsonl
from download_sources import ROOT, sha256, write_json
from validate_all import require

sys.path.insert(0, str(ROOT / 'data/exp_a'))
import build_exp_a as annotation

FACETS = annotation.FACET_NAMES
FILES = {
    'b': (('retrieval_queries.jsonl', 'splits.json'), ('retrieval_labels.jsonl', 'label_provenance.jsonl')),
    'c': (('intents.jsonl', 'splits.json'), ('intent_labels.jsonl', 'label_provenance.jsonl')),
    'd': (('users.jsonl', 'interactions_train.jsonl'), ('latent_user_profiles.jsonl', 'interactions_test.jsonl')),
    'e': (('interactions_train.jsonl',), ('temporal_profiles.jsonl', 'interactions_test.jsonl', 'period_metadata.json')),
}


def project_path(root, value):
    root = Path(root).resolve()
    path = (root / value).resolve()
    require(path == root or root in path.parents, f'Path must stay inside project: {value}')
    return path


def load_silver(root, directory, complete=True):
    root = Path(root)
    directory = project_path(root, directory)
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    config = dict(max_new_tokens=2048, max_attempts=3, **manifest['provenance']['config'])
    require(project_path(root, config['output_dir']) == directory, 'A output path differs from provenance config')
    require(project_path(root, config['corpus']) == root.resolve() / 'data/processed/papers.jsonl',
            'A must use the canonical corpus')
    for field in ('corpus', 'prompt', 'guideline'):
        project_path(root, config[field])
    annotation.check_outputs(root, config, allow_partial=not complete)
    papers = sorted(read_jsonl(root / config['corpus']), key=lambda row: row['paper_id'])
    facets = read_jsonl(directory / 'facets_silver.jsonl')
    metadata = read_jsonl(directory / 'annotation_metadata.jsonl')
    return ({row['paper_id']: row for row in papers},
            {row['paper_id']: row for row in facets},
            {row['paper_id']: row for row in metadata}, manifest)


def concept_sets(facets, metadata):
    """Exclude flagged papers; empty evidence remains empty, never imputed."""
    return {pid: {facet: set(filter(None, (normalize(value) for value in row[facet])))
                  for facet in FACETS}
            for pid, row in sorted(facets.items())
            if not metadata[pid].get('fallback_used') and not metadata[pid].get('validation_errors')}


def check_users(users):
    require(users and all(set(row) == {'user_id'} and isinstance(row['user_id'], str)
                         and re.fullmatch(r'U[0-9]{4}', row['user_id']) for row in users),
            'users must contain only valid observable user IDs')
    require(len({row['user_id'] for row in users}) == len(users), 'Duplicate user IDs')


def input_paths(config, experiment, config_path):
    directory = Path(config['facets_path']).parent
    paths = [config_path, config['corpus_path'], config['facets_path'],
             (directory / 'annotation_metadata.jsonl').as_posix(), (directory / 'manifest.json').as_posix()]
    if experiment == 'c':
        paths.append(config['templates_path'])
    if experiment == 'e':
        paths.extend([config['users_path'], (Path(config['users_path']).parent / 'manifest.json').as_posix()])
    return sorted(paths)


def load_users(root, config):
    path = project_path(root, config['users_path'])
    users = read_jsonl(path)
    check_users(users)
    manifest = json.loads((path.parent / 'manifest.json').read_text(encoding='utf-8'))
    require(manifest['experiment'] == 'd' and manifest['dataset_kind'] == 'mock'
            and manifest['contract_version'] == '1.0', 'E requires the D user handoff')
    key = path.relative_to(Path(root).resolve()).as_posix()
    require(manifest['files'].get(key) == sha256(path), 'D users checksum mismatch')
    require(manifest['counts']['users.jsonl'] == len(users), 'D user count differs from manifest')
    for name in ('corpus_path', 'facets_path'):
        require(manifest['config'][name] == config[name], 'D/E input paths differ')
        require(manifest['input_hashes'][config[name]] == sha256(project_path(root, config[name])),
                'D/E corpus or A facets input hashes differ')
    return sorted(users, key=lambda row: row['user_id'])


def output_paths(root, config, experiment):
    output = project_path(root, config['output_dir'])
    hidden = project_path(root, config['truth_dir'])
    base = project_path(root, f'data/exp_{experiment}')
    require(base in output.parents and base in hidden.parents, 'Outputs must stay in their experiment folder')
    require(output != hidden and output not in hidden.parents and hidden not in output.parents,
            'Observable and truth directories must be separate')
    return output, hidden


def generator_files(experiment):
    return ('data/build_experiments.py', 'data/experiment_common.py',
            f'data/exp_{experiment}/build_exp_{experiment}.py',
            'scripts/experiment_io.py', 'scripts/build_corpus.py')


def write_dataset(root, config, experiment, observable, truth, report, input_paths):
    output, hidden = output_paths(root, config, experiment)
    files = {}
    for directory, values in ((output, observable), (hidden, truth)):
        for name, rows in values.items():
            path = directory / name
            if name.endswith('.jsonl'):
                write_jsonl(path, rows)
            else:
                write_json(path, rows)
            files[path.relative_to(root).as_posix()] = sha256(path)
    write_json(output / 'generation_report.json', report)
    files[(output / 'generation_report.json').relative_to(root).as_posix()] = sha256(output / 'generation_report.json')
    manifest = dict(contract_version='1.0', dataset_kind='mock', experiment=experiment,
                    generator_version='1.0', seed=config['seed'], config=config,
                    generator_hashes={name: sha256(ROOT / name) for name in generator_files(experiment)},
                    input_hashes={str(path): sha256(project_path(root, path)) for path in sorted(input_paths)},
                    files=files, counts={name: len(rows) for values in (observable, truth)
                                        for name, rows in values.items() if name.endswith('.jsonl')},
                    status='partial' if report.get('shortfall', 0) else 'complete')
    write_json(output / 'manifest.json', manifest)
    return manifest
