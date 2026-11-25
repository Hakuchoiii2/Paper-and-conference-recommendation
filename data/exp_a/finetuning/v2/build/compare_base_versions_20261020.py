"""Replay the existing paired 100-paper runs; never generate or edit labels."""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).with_suffix('')
FACETS = ('problem', 'task', 'method', 'dataset', 'contribution')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def load(path):
    spec = importlib.util.spec_from_file_location('base_comparison_evaluation', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def concepts(value, pid):
    if not isinstance(value, dict) or value.get('paper_id') != pid:
        return dict(paper_id=pid, **{f: [] for f in FACETS})
    return dict(paper_id=pid, **{f: [x['concept'] for x in value.get(f, [])
        if isinstance(x, dict) and isinstance(x.get('concept'), str) and x['concept'].strip()]
        for f in FACETS})


def parse(raw):
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return {}


def main():
    assert not OUT.exists(), 'Use a new destination; never overwrite diagnostic evidence'
    old = ROOT/'data/exp_a/finetuning/downloads/v1/exp_a_qlora'
    new = ROOT/'data/exp_a/finetuning/v2/downloads/test_v1_20261020/exp_a_qlora_v2_test'
    s1, s2 = read(old/'qlora_settings.json'), read(new/'v2_settings.json')
    assert s1['test_ids'] == s2['test_ids'] and s1['model'] == s2['model']
    assert s1['files']['evaluation_only/test_references.jsonl'] == s2['test_files']['evaluation_only/test_references.jsonl']
    assert s1['files']['model_inputs/test_papers.jsonl'] == s2['test_files']['model_inputs/test_papers.jsonl']
    assert not set(s2['test_ids']) & set(s2['train_dev_ids'])
    shared = load(ROOT/'data/exp_a/finetuning/v2/evaluation.py').shared
    runner = load(ROOT/'data/exp_a/finetuning/v2/evaluation.py').runner
    papers = shared.base.read_jsonl(old/'model_inputs/test_papers.jsonl')
    refs = shared.base.read_jsonl(old/'evaluation_only/test_references.jsonl')
    assert shared.base.sha256(old/'evaluation_only/test_references.jsonl') == s2['test_files']['evaluation_only/test_references.jsonl']
    groups, stats, envelopes, probe_examples = {}, {}, {}, []
    arms = {'base_v1': (old/'results/original', s1['experiment_signature']),
            'adapter_v1': (old/'results/qlora', s1['experiment_signature']),
            'base_v2': (new/'results/base', s2['signature']),
            'adapter_v2': (new/'results/qlora_v2', s2['signature'])}
    for arm, (directory, signature) in arms.items():
        assert len(list((directory/'records').glob('*.json'))) == 100
        final, raw_rows, common_grounding_rows = [], [], []
        totals = collections.Counter()
        raw_facets, kept_facets, errors = collections.Counter(), collections.Counter(), collections.Counter()
        cross_errors = collections.Counter()
        for paper in papers:
            pid = paper['paper_id']
            env = read(directory/f'records/{pid}.json'); r = env['record']; a = r['audit']
            assert env['signature'] == signature and env['record_sha256'] == digest(r) and r['paper_id'] == pid
            attempts = a['attempt_scores'] if arm.endswith('v1') else a['attempts']
            chosen = a['attempt'] if arm.endswith('v1') else a['selected_attempt']
            attempt = next(x for x in attempts if x['attempt'] == chosen)
            raw = parse(attempt['raw_output']); raw_fac = concepts(raw, pid)
            final.append(r); raw_rows.append(dict(facets=raw_fac))
            converted_raw = dict(paper_id=pid, **{f: [] for f in FACETS})
            if isinstance(raw, dict) and raw.get('paper_id') == pid:
                for f in FACETS:
                    converted_raw[f] = [dict(concept=x.get('concept'),
                        evidence_ids=x.get('evidence_ids', [x.get('evidence_id')]))
                        for x in raw.get(f, []) if isinstance(x, dict)]
            assessed = runner.assess_new(json.dumps(converted_raw), paper)
            common = concepts(assessed['selection'], pid)
            common_grounding_rows.append(dict(facets=common))
            if arm.endswith('v2'):
                assert all(common[f] == r['facets'][f] for f in FACETS), 'v2 selected grounding replay drift'
            totals.update(papers=1, calls=len(attempts), fallback=r['fallback_used'],
                raw_parseable=bool(raw), draft_schema=bool(attempts[0]['schema_valid']),
                selected_schema=bool(attempt['schema_valid']),
                selected_validator=not a['validation_errors'],
                unchanged_review=attempts[0]['raw_output'].strip() == attempts[1]['raw_output'].strip())
            for error in a['validation_errors']:
                errors[error.split(': ', 1)[-1]] += 1
            for f in FACETS:
                raw_facets[f] += len(raw_fac[f]); kept_facets[f] += len(r['facets'][f])
                totals['raw_words'] += sum(len(x.split()) for x in raw_fac[f])
                totals['final_words'] += sum(len(x.split()) for x in r['facets'][f])
                totals['raw_empty_facets'] += not bool(raw_fac[f])
                totals['final_empty_facets'] += not bool(r['facets'][f])
                draft = concepts(parse(attempts[0]['raw_output']), pid)[f]
                review = concepts(parse(attempts[1]['raw_output']), pid)[f]
                totals['draft_items_absent_from_review'] += len(set(map(shared.evaluator.label_key, draft)) - set(map(shared.evaluator.label_key, review)))
                for item in raw.get(f, []) if isinstance(raw, dict) else []:
                    if not isinstance(item, dict) or 'concept' not in item:
                        continue
                    ids = item.get('evidence_ids', [item.get('evidence_id')])
                    converted = dict(paper_id=pid, **{k: [] for k in FACETS})
                    converted[f] = [dict(concept=item['concept'], evidence_ids=ids)]
                    totals['cross_v2_items_tested'] += 1
                    try:
                        runner.multi.ground_response(converted, paper)
                        totals['cross_v2_items_pass'] += 1
                    except (ValueError, TypeError, KeyError) as error:
                        cross_errors[str(error)] += 1
                if arm.endswith('v2'):
                    for item in r['selection'][f]:
                        if len(item['evidence_ids']) != 1:
                            totals['multi_sentence_final_items'] += 1
                            continue
                        one = dict(paper_id=pid, **{k: [] for k in FACETS})
                        one[f] = [dict(concept=item['concept'], evidence_id=item['evidence_ids'][0])]
                        totals['v1_guard_items_tested'] += 1
                        try:
                            shared.v3.ground_response(one, paper)
                        except (ValueError, TypeError, KeyError) as error:
                            totals['v1_guard_items_flagged'] += 1
                            if len(probe_examples) < 30:
                                probe_examples.append(dict(arm=arm, paper_id=pid, facet=f,
                                    item=item, error=str(error), title=paper['title'], abstract=paper['abstract']))
            envelopes[str((directory/f'records/{pid}.json').relative_to(ROOT))] = shared.base.sha256(directory/f'records/{pid}.json')
        groups[arm], groups[arm+'_raw_unvalidated'] = final, raw_rows
        groups[arm+'_common_v2_grounding'] = common_grounding_rows
        stats[arm] = dict(totals=totals, raw_items_by_facet=raw_facets,
            final_items_by_facet=kept_facets, selected_errors=errors, cross_v2_errors=cross_errors)
    labels = sorted({v for rows in groups.values() for r in rows for f in FACETS for v in r['facets'][f]}
                    | {v for r in refs for f in FACETS for v in r['facets'][f]})
    vectors, runtime = shared.evaluator.encode_labels(ROOT, labels)
    OUT.mkdir()
    (OUT/'label_vectors.json').write_text(json.dumps(vectors)+'\n', encoding='utf-8')
    scores = {}
    for arm, rows in groups.items():
        report = shared.score_rows(papers, rows, refs, vectors, threshold=0.85)
        (OUT/(arm+'.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        scores[arm] = dict(micro=report['micro'], macro_f1=report['macro_f1'], by_facet=report['by_facet'])
        if arm in arms:
            historical = read(arms[arm][0]/'evaluation.json')
            assert all(report['micro'][k] == historical['micro'][k] for k in ('tp', 'fp', 'fn')), arm+' scoring drift'
        print(arm, report['micro'], flush=True)
    result = dict(status='verified', papers=100, same_model=True, same_sources=True, same_references=True,
        threshold=0.85, generation_performed=False, runtime=runtime, scores=scores, diagnostics=stats,
        v1_guard_probe_examples=probe_examples, input_record_hashes=envelopes,
        limitations=['Historical pipeline comparison, not a one-variable causal ablation',
            'Raw scores are unvalidated diagnostic agreement, never deployment quality',
            'Pre-v2 AI references, human review pending', 'Legacy guard flags are review candidates, not semantic verdicts'])
    (OUT/'comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Verified all four historical score counts; saved', OUT, flush=True)


if __name__ == '__main__':
    main()
