"""Offline diagnostic replay and source-linked error inventory. No inference."""
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
FROZEN = BASE/'release_20261022_v1/preflight_project'
OUT = BASE.parents[1]/'evaluation/base_v1_improvement_pilot50_20261022'
ROOT = BASE/'completed_20261022_v2/base_v1_r1_r2'
SCORES = BASE/'summary_20261022_v2/base_v1_r1_r2/results'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def jsonl(p): return {r['paper_id']:r for r in map(json.loads,p.read_text(encoding='utf-8').splitlines())}
papers = jsonl(FROZEN/'model_inputs/papers.jsonl')
refs = jsonl(FROZEN/'evaluation_only/review_annotations.jsonl')
spec = importlib.util.spec_from_file_location('pilot_frozen_matrix',FROZEN/'data/exp_a/.kaggle/matrix.py')
shared = importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
v3 = shared.v3
FACETS = shared.FACETS
records = {a:{p.stem:read(p)['record'] for p in (ROOT/f'results/{a}/records').glob('*.json')} for a in ('R0','R1','R2')}
evals = {a:{d['paper_id']:d['comparison'] for d in read(SCORES/a/'evaluation.json')['details']} for a in records}
stats, casebook = {}, {}
replayed = 0
for arm, rows in records.items():
    counts = Counter(); errors = Counter(); qualities = Counter(); cases = []
    problem_changes = []; drops = []; merges = []
    for pid,r in rows.items():
        p = papers[pid]; audit = r['audit']; previous = None
        for attempt in audit['attempt_scores']:
            value,selection,assessment,application = v3.assess_attempt(attempt['raw_output'],p,'3.1',prompt_version='3.7',dataset_resource_filter=True,previous=previous)
            for k in assessment:
                assert assessment[k] == attempt[k], (arm,pid,attempt['attempt'],k)
            assert application['applied_output'] == attempt['applied_output'], (arm,pid,'merge drift')
            replayed += 1
            previous = (attempt,selection)
            counts['attempts'] += 1
            counts['schema_failures'] += not attempt['schema_valid']
            counts['parse_failures'] += not attempt['parseable']
            if attempt['raw_output'] != attempt['applied_output']:
                try:
                    raw = json.loads(attempt['raw_output']); applied = json.loads(attempt['applied_output'])
                    if raw != applied:
                        merges.append(dict(paper_id=pid,attempt=attempt['attempt'],raw=raw,applied=applied))
                except ValueError:
                    pass
        attempts = audit['attempt_scores']; chosen = attempts[audit['attempt']-1]
        first = json.loads(attempts[0]['applied_output']); selected = audit['evidence_selection']
        counts['fallback'] += r['fallback_used']
        counts['selected_draft'] += audit['attempt'] == 1
        counts['no_errors_selected_but_fallback'] += r['fallback_used'] and not chosen['validation_errors']
        counts['stagnant_applied_consecutive'] += any(json.loads(a['applied_output']) == json.loads(b['applied_output']) for a,b in zip(attempts,attempts[1:]))
        counts['final_equals_draft_selection'] += selected == first
        counts['final_all_empty'] += not any(r['facets'][f] for f in FACETS)
        counts['draft_invalid_final_valid'] += bool(attempts[0]['validation_errors']) and audit['validation_passed']
        counts['initially_valid'] += not attempts[0]['validation_errors']
        qualities[audit['source_quality']['status']] += 1
        for error in chosen['validation_errors']:
            facet = error.split('[')[0].split(':')[0]
            if 'original order' in error:
                category = 'source_word_order_or_invented_words'
            elif 'negation' in error: category = 'negation'
            elif 'caveat' in error or 'qualification' in error: category = 'qualification'
            elif 'quantity' in error: category = 'quantity'
            elif 'whether' in error: category = 'whether'
            elif 'duplicate' in error: category = 'duplicate'
            elif 'dataset' in error: category = 'named_dataset'
            else: category = error.split(';')[0].split(':')[-1].strip()
            errors[facet+'/'+category] += 1
            if 'split source word' in error: counts['final_split_word_errors'] += 1
        for facet in FACETS:
            final_items = selected[facet]
            for old in first[facet]:
                if old not in final_items:
                    drops.append(dict(paper_id=pid,facet=facet,item=old,final=final_items))
        if arm != 'R0':
            before = records['R0'][pid]
            if before['facets']['problem'] != r['facets']['problem']:
                problem_changes.append(dict(paper_id=pid,before=before['facets']['problem'],after=r['facets']['problem'],reference=refs[pid]['facets']['problem'],counts_before=evals['R0'][pid]['problem'],counts_after=evals[arm][pid]['problem']))
        total = lambda a: {k:sum(x[k] for x in evals[a][pid].values()) for k in ('tp','fp','fn')}
        oldtot,newtot = total('R0'),total(arm)
        changed = []
        for f in FACETS:
            old,new = evals['R0'][pid][f],evals[arm][pid][f]
            if tuple(old[k] for k in ('tp','fp','fn')) != tuple(new[k] for k in ('tp','fp','fn')):
                changed.append(f)
        entry = dict(paper_id=pid,title=p['title'],abstract=p['abstract'],counts_R0=oldtot,counts_arm=newtot,changed_score_facets=changed,
            baseline=records['R0'][pid]['facets'],prediction=r['facets'],reference=refs[pid]['facets'],
            comparison_R0=evals['R0'][pid],comparison_arm=evals[arm][pid],
            source_options=shared.base.evidence_options(p),
            draft=first,selected=selected,attempts=attempts,
            fallback=r['fallback_used'],source_quality=audit['source_quality'])
        cases.append(entry)
    stats[arm] = dict(counts=dict(counts),selected_errors=dict(errors),source_quality=dict(qualities),problem_changes=problem_changes,draft_items_changed_or_removed=drops,applied_merge_changes=merges)
    casebook[arm] = cases
stats['replayed_attempts'] = replayed
special = next(r for r in casebook['R2'] if r['paper_id']=='P001181')
paper = dict(paper_id=special['paper_id'],title=special['title'],abstract=special['abstract'])
scope_probe = {}
for policy in ('3.1','3.2'):
    _,_,assessment = v3.assess_generation(special['attempts'][0]['raw_output'],paper,policy,prompt_version='3.7',dataset_resource_filter=True)
    scope_probe[policy] = assessment['validation_errors']
assert len(scope_probe['3.1']) == 1 and 'negation' in scope_probe['3.1'][0] and not scope_probe['3.2']
pair = next(p for p in special['comparison_arm']['contribution']['matched_pairs'] if 'not to improve' in p['silver'])
decision = shared.evaluator.pair_score(pair['silver'],pair['gold'],'contribution',pair['similarity'],paper['title']+'\n'+paper['abstract'])
assert decision['blocked_reason'] is None and decision['score'] >= 0.85
assert not special['selected']['problem']
assert not any('effective for parser domain adaptation' in x['concept'] for x in special['selected']['contribution'])
stats['confirmed_diagnostic_probes'] = dict(P001181=dict(same_draft_validator_policy_comparison=scope_probe,accepted_opposite_finding_match=pair,scorer_replay=decision,final_lost_problem_and_positive_finding=True),
    R2_single_pair_sensitivity=dict(tp=214,fp=145,fn=188,f1=2*214/(2*214+145+188),official_rescore=False))
(OUT/'error_diagnostics_20261022.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'error_casebook_20261022.json').write_text(json.dumps(casebook,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for a in records:
    print(a,json.dumps({k:v for k,v in stats[a].items() if k in ('counts','selected_errors','source_quality')},ensure_ascii=False))
print('Replayed attempts',replayed)
for arm in ('R1','R2'):
    print('\nPROBLEM CHANGES',arm)
    for c in stats[arm]['problem_changes']:
        print(c['paper_id'],'R0',c['before'],'NEW',c['after'],'GOLD',c['reference'])
