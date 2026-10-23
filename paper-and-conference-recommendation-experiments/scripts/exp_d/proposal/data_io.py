"""Public-only D loader. Ground truth is deliberately loaded in evaluate.py."""
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
DATA_ROOT = PROJECT / 'data/exp_d/proposal'
for directory in (PROJECT / 'scripts', DATA_ROOT):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from baseline_common import FACETS, facet_profiles, facet_vectors


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def write_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n' for r in rows), encoding='utf-8')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def time(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'Timezone required')
    return result


def inside(root, name):
    root = Path(root).resolve()
    path = (root / name).resolve()
    require(path.is_relative_to(root), 'Path escapes root: ' + str(name))
    return path


@dataclass(frozen=True)
class Evidence:
    # No evaluation candidate IDs, labels, true focus, query mode or noise parameter.
    case: dict
    reactions: tuple
    queries: tuple
    exposures: tuple


def evidence_for(case, condition, queries):
    cutoff = time(case['cutoff'])
    def visible(row):
        return (row['session_id'] == case['case_id'] and row['user_id'] == case['user_id']
                and time(row['timestamp']) < cutoff)
    exposures = sorted((r for r in condition['exposures'] if visible(r)),
                       key=lambda r: (time(r['timestamp']), r['exposure_id']))
    exposed = {r['exposure_id']:set(r['paper_ids']) for r in exposures}
    reactions = sorted((r for r in condition['reactions'] if visible(r)
                        and r['exposure_id'] in exposed and r['paper_id'] in exposed[r['exposure_id']]),
                       key=lambda r: (time(r['timestamp']), r['exposure_id'], r['paper_id']))
    searches = sorted((r for r in queries if visible(r)), key=lambda r:(time(r['timestamp']), r['query_id']))
    public_case = {k:case[k] for k in ('case_id', 'user_id', 'query_paper_id', 'context_facet', 'cutoff')}
    return Evidence(public_case, tuple(reactions), tuple(searches), tuple(exposures))


def load_public(directory):
    directory = Path(directory).resolve()
    require(directory.is_relative_to(DATA_ROOT) and directory != DATA_ROOT, 'Dataset must be inside D proposal')
    manifest = read_json(directory / 'manifest.json')
    require(manifest['protocol'] == 'd_observation_v1' and manifest['status'] == 'structurally_valid', 'Invalid dataset')
    # Static public catalog/vocabulary is shared; methods never receive pool membership.
    facets = {r['paper_id']:{f:set(r[f]) for f in FACETS} for r in read_rows(directory / 'catalog/facets.jsonl')}
    cases = read_rows(directory / 'generated/sessions.jsonl')
    require(cases and len({r['case_id'] for r in cases}) == len(cases), 'Empty or duplicate cases')
    return dict(facets=facets, cases=cases, queries=read_rows(directory / 'generated/search_events.jsonl'),
                history=read_rows(directory / 'history/interactions_train.jsonl'),
                history_queries=read_rows(directory / 'history/search_events.jsonl'),
                conditions={name:dict(exposures=read_rows(inside(directory, 'conditions/'+name+'/generated/exposures.jsonl')),
                                     reactions=read_rows(inside(directory, 'conditions/'+name+'/generated/interactions_train.jsonl')))
                            for name in sorted(manifest['conditions'])},
                condition_metadata=manifest['conditions'])


def shared_representation(public):
    cutoff = min((r['cutoff'] for r in public['cases']), key=time)
    require(all(time(r['timestamp']) < time(cutoff) for r in public['history'] + public['history_queries']),
            'Future C history reached frozen profile')
    profiles = facet_profiles(public['history'], public['history_queries'], public['facets'], cutoff)
    require(all(r['user_id'] in profiles for r in public['cases']), 'Missing C profile for session user')
    return profiles, facet_vectors(public['facets']), cutoff


def new_output(path):
    path = Path(path).resolve()
    root = (DATA_ROOT / 'results').resolve()
    require(path.is_relative_to(root) and path != root, 'Output must be a new run inside data/exp_d/proposal/results')
    require(not path.exists(), 'Output exists; use a new run name')
    return path
