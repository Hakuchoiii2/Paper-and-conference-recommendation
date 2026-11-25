"""Formatting and validation only; concepts are supplied explicitly by GPT."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
spec = importlib.util.spec_from_file_location('_batch1_matrix', ROOT / 'data/exp_a/.kaggle/matrix/matrix.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
papers = m.base.read_jsonl(HERE / 'sources.jsonl')
by_id = {paper['paper_id']: paper for paper in papers}


def show(start, count=10):
    for paper in papers[start:start + count]:
        print(paper['paper_id'])
        for eid, option in m.base.evidence_options(paper).items():
            print(eid + ': ' + option['evidence'])
        print()


def row(pid, p='', t='', mth='', d='', c=''):
    result = dict(paper_id=pid)
    for facet, values in zip(m.FACETS, (p, t, mth, d, c)):
        result[facet] = [dict(concept=value.rsplit('@', 1)[0], evidence_id=value.rsplit('@', 1)[1])
                         for value in values.split(' || ') if value]
    return result


def save(part, rows):
    directory = HERE / 'drafts'
    directory.mkdir(exist_ok=True)
    failures = []
    for value in rows:
        try:
            grounded = m.v3.ground_response(value, by_id[value['paper_id']])
            _, audit = m.v3.filter_named_datasets(grounded, by_id[value['paper_id']])
            if audit['removed']:
                raise ValueError('Named resource guard: ' + json.dumps(audit['removed'], ensure_ascii=False))
        except (ValueError, KeyError) as error:
            failures.append(dict(paper_id=value['paper_id'], error=str(error)))
    (directory / f'part_{part:02d}.jsonl').write_text(
        ''.join(json.dumps(value, ensure_ascii=False) + '\n' for value in rows), encoding='utf-8')
    (HERE / f'part_{part:02d}_validation.json').write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding='utf-8')
    print('saved', len(rows), 'rows; validation failures:', json.dumps(failures, ensure_ascii=False))
