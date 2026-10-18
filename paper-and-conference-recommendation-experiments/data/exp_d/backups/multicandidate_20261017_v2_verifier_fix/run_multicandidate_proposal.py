"""Frozen v2 pool extension: real candidates, identical v1 evidence, no tuning.

Run from the experiments project. Existing outputs are never overwritten.
"""
import argparse
import collections
import csv
import datetime as dt
from pathlib import Path
import sys

from run_improve_trial import read, rows, write, write_rows, digest, verify, focus_metrics
from run_evidence_suite import bootstrap
from evidence_controls import direction_controls

PROJECT = Path(__file__).resolve().parents[2]
DATA = PROJECT / 'data/exp_d'
PROTOCOL = 'd_multicandidate_v2'
SEEDS = (42, 43, 44)
NOISE = (.2, .5)
MODELS = ('direction_behavior', 'direction_search', 'strict_behavior_predicted',
          'strict_behavior_similar', 'proposal_behavior_predicted', 'proposal_behavior_similar',
          'proposal_behavior_flipped', 'proposal_search_predicted', 'proposal_search_similar')
METRICS = ('ndcg@10', 'intent_compliance@1', 'intent_compliance@5', 'intent_compliance@10',
           'diagnostic_intent_recall@5', 'diagnostic_ceiling_fraction@5')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def csv_rows(path, values):
    with path.open('w', encoding='utf-8', newline='') as stream:
        fields = list(dict.fromkeys(key for row in values for key in row))
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(values)


def comparison_groups():
    return ('overall', 'intent_similar', 'intent_different', 'expanded', 'unchanged',
            'expanded_intent_similar', 'expanded_intent_different', 'different_count_5',
            'different_count_5_intent_different', 'clear', 'ambiguous', 'none',
            'focus_task', 'focus_method', 'focus_dataset', 'focus_contribution')


def paired_analysis(cases, lookups):
    """Average seeds within episode first, then resample whole anchors."""
    comparisons = []
    for noise in NOISE:
        runs = [lookups[f'seed_{seed}_noise_{noise:g}'] for seed in SEEDS]
        for family in ('strict', 'proposal'):
            for channel in ('behavior', 'search'):
                model = f'{family}_{channel}_predicted'
                for arm in ('similar', 'flipped'):
                    reference = f'{family}_{channel}_{arm}'
                    for group in comparison_groups():
                        chosen = [c for c in cases if group == 'overall'
                                  or group in runs[0][c['case_id'], model]['groups']]
                        if not chosen:
                            continue
                        for metric in METRICS:
                            deltas = [sum(run[c['case_id'], model]['metrics'][metric]
                                          - run[c['case_id'], reference]['metrics'][metric]
                                          for run in runs) / len(runs) for c in chosen]
                            anchors = collections.defaultdict(list)
                            for case, delta in zip(chosen, deltas):
                                anchors[case['query_paper_id']].append(delta)
                            leaving = []
                            for anchor in anchors:
                                kept = [x for a, xs in anchors.items() if a != anchor for x in xs]
                                if kept:
                                    leaving.append(sum(kept) / len(kept))
                            comparisons.append(dict(
                                noise=noise, model=model, reference=reference, group=group, metric=metric,
                                **bootstrap(deltas, chosen), seeds_averaged=list(SEEDS),
                                anchor_macro_mean=sum(sum(xs)/len(xs) for xs in anchors.values())/len(anchors),
                                anchor_deltas={a: sum(xs)/len(xs) for a, xs in sorted(anchors.items())},
                                leave_one_anchor_out_range=[min(leaving), max(leaving)] if leaving else None,
                                primary=(family == 'proposal' and channel == 'behavior' and arm == 'similar'
                                         and group == 'overall' and metric == 'ndcg@10'),
                                multiplicity='secondary/subgroup intervals are descriptive, unadjusted'))
    return comparisons


def add_diagnostics(details, cases, truth, judged, metadata):
    by_id = {c['case_id']: c for c in cases}
    for row in details:
        cid = row['case_id']
        intent, meta = truth[cid], metadata[cid]
        direction = intent['directions'][intent['focus_facet']]
        status = 'expanded' if meta['expanded'] else 'unchanged'
        row['groups'] += ['intent_'+direction, 'focus_'+intent['focus_facet'], status,
                          status+'_intent_'+direction, f"different_count_{meta['different_count']}",
                          f"different_count_{meta['different_count']}_intent_{direction}"]
        positive_count = sum(g == 2 for g in judged[cid].values())
        require(positive_count > 0, 'No intent-positive candidates')
        row['grade2_candidates'] = positive_count
        row['intent_compliance_ceiling@5'] = min(positive_count, 5) / 5
        compliance = row['metrics']['intent_compliance@5']
        row['metrics']['diagnostic_intent_recall@5'] = compliance * 5 / positive_count
        row['metrics']['diagnostic_ceiling_fraction@5'] = compliance / row['intent_compliance_ceiling@5']
        require(row['candidates'] == len(by_id[cid]['candidate_ids']), 'Wrong candidate count')


def verify_public_replay(public, original, cases):
    old = {(r['case_id'], r['model']): r for r in original}
    for row in public:
        baseline = old[row['case_id'], row['model']]
        for key in ('directions', 'direction_confidence', 'facet_importance'):
            require(row[key] == baseline[key], f'Public evidence/profile changed: {key}')
        previous = {r['paper_id']: r['score'] for r in baseline['ranking']}
        for candidate in row['ranking']:
            if candidate['paper_id'] in previous:
                require(candidate['score'] == previous[candidate['paper_id']], 'Retained-candidate score changed')
    require(len(public) == 4 * len(cases), 'Incomplete public baseline replay')


def verify_direction_arms(arms, baseline):
    require(len(arms) == 3, 'Three proposal arms required')
    first = arms[0]
    for row in arms:
        for key in ('facet_importance', 'predicted_focus', 'direction_confidence', 'fallback_to_baseline'):
            require(row[key] == first[key], f'Proposal arms differ beyond direction: {key}')
        if row['fallback_to_baseline']:
            require(row['ranking'] == baseline['ranking'], 'Fallback ranking changed')


def run(args):
    source, v1, output = args.source.resolve(), args.v1.resolve(), args.output.resolve()
    require(DATA in output.parents and not output.exists(), 'Choose a NEW output below data/exp_d')
    require(source != output and source not in output.parents and v1 not in output.parents,
            'Output must be separate from source and v1')
    sys.path[:0] = [str(source/'scripts'), str(source), str(DATA), str(PROJECT/'scripts/exp_d')]
    from validate_experiments import validate_experiment, check_d
    from experiment_io import FACETS, load_silver, concept_sets
    from baseline_common import (facet_vectors, facet_profiles, direction_estimate, intent_scores,
                                 ranked, aggregate)
    from experiment_runner import evaluate_predictions, markdown_report
    from validate_all import validate_time
    from data.experiment_common import facet_index, overlapping, session_grade, timestamp
    from intent_priority import observed_focus, rerank
    from proposal_ranker import predict
    import build_contrast_sessions as builder
    from build_multicandidate_sessions import expand
    import run_synthetic_observation_pilot as pilot

    validated = validate_experiment(source, 'd')
    config = validated['config']
    old_manifest = read(v1/'manifest.json')
    verify(v1, old_manifest['files'])
    for path, expected in old_manifest['input_hashes'].items():
        require(digest(Path(path)) == expected, 'v1 source changed: '+path)
    verify(PROJECT, old_manifest['code_hashes'])
    _, raw, annotation_metadata, _ = load_silver(source, Path(config['facets_path']).parent)
    facets = concept_sets(raw, annotation_metadata)
    users = rows(source/config['users_path'])
    api = dict(FACETS=FACETS, facet_index=facet_index, overlapping=overlapping, session_grade=session_grade,
               timestamp=timestamp, check_d=check_d, validate_time=validate_time, facet_profiles=facet_profiles,
               direction_estimate=direction_estimate, intent_scores=intent_scores, ranked=ranked,
               observed_focus=observed_focus, rerank=rerank)
    designs = builder.feasible_designs(facets, api)
    old_cases, intents, old_labels, queries, pairs = builder.build(designs, facets, users, api)
    for actual, path in ((old_cases, 'generated/sessions.jsonl'), (intents, 'ground_truth/session_intents.jsonl'),
                         (old_labels, 'ground_truth/intent_labels.jsonl'), (queries, 'generated/search_events.jsonl'),
                         (pairs, 'ground_truth/paired_designs.jsonl')):
        require(actual == rows(v1/path), 'Cannot exactly reproduce v1 '+path)
    cases, labels, metadata = expand(old_cases, intents, designs, facets, api)
    truth = {r['case_id']: r for r in intents}
    meta = {r['case_id']: r for r in metadata}
    groups = {cid: r['query_mode'] for cid, r in truth.items()}
    judged = {c['case_id']: {} for c in cases}
    for row in labels:
        judged[row['case_id']][row['candidate_id']] = row['relevance']
    report_counts = dict(shortfall=len(users)*config['sessions_per_user']-len(cases),
                         actual_cases=len(cases), actual_pairs=len(labels))
    check_d({'sessions.jsonl': cases, 'search_events.jsonl': queries, 'exposures.jsonl': [],
             'interactions_train.jsonl': []}, {'session_intents.jsonl': intents, 'intent_labels.jsonl': labels},
            facets, config, report_counts, users)
    watched = {Path(path): h for path, h in old_manifest['input_hashes'].items()}
    watched.update({v1/name: h for name, h in old_manifest['files'].items()})
    watched[v1/'manifest.json'] = digest(v1/'manifest.json')
    for path in [PROJECT/'docs/EXPERIMENT_PROTOCOL.md', DATA/'README.md',
                 PROJECT/'scripts/experiment_io.py', PROJECT/'scripts/baseline_common.py',
                 PROJECT/'scripts/experiment_runner.py', PROJECT/'scripts/validate_experiments.py',
                 PROJECT/'data/experiment_common.py', PROJECT/'scripts/exp_d/run_exp_d.py',
                 DATA/'build_contrast_sessions.py', DATA/'run_synthetic_observation_pilot.py']:
        watched[path] = digest(path)
    code_paths = [Path(__file__), DATA/'build_multicandidate_sessions.py',
                  PROJECT/'scripts/exp_d/test_multicandidate_proposal.py',
                  PROJECT/'scripts/exp_d/proposal_ranker.py', PROJECT/'scripts/exp_d/evidence_controls.py',
                  PROJECT/'scripts/exp_d/intent_priority.py', PROJECT/'scripts/exp_d/run_improve_trial.py',
                  PROJECT/'scripts/exp_d/run_evidence_suite.py']
    code_hashes = {p.relative_to(PROJECT).as_posix(): digest(p) for p in code_paths}
    output.mkdir(parents=True)
    # Persist the complete v2 decision before computing any new prediction or metric.
    design = dict(protocol=PROTOCOL, fixed_before_v2_predictions=True,
                  created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                  prior_v1_results_inspected=True, evaluation_scope='development diagnostic, no untouched test',
                  primary='seed-averaged paired proposal_behavior_predicted minus proposal_behavior_similar nDCG@10',
                  secondary=list(METRICS[1:]), seeds=list(SEEDS), noise=list(NOISE), bootstrap_samples=2000,
                  pool_rule='retain v1 same/different; replace outside with up to 5 total different, all designs',
                  intervention='candidate composition only; exact v1 queries/observations/intents/C profiles',
                  subgroup_rule='expanded (>=2 different), unchanged, count=5, direction, query mode, focus; descriptive',
                  label_rule='unchanged session_grade; equal-grade internal order has no judged preference',
                  training=False, tuning=False, source=str(source), v1=str(v1),
                  code_hashes=code_hashes,
                  expected_limitations=['8 previously used anchors; synthetic reactions; overlap labels',
                                        'compliance pool ceilings change; cross-dataset deltas are pool effects',
                                        'no human/generalization/acceptance or novelty claim'])
    write(output/'design.json', design)
    for directory in ('generated', 'ground_truth', 'analysis'):
        (output/directory).mkdir()
    write_rows(output/'generated/sessions.jsonl', cases)
    write_rows(output/'generated/search_events.jsonl', queries)
    write_rows(output/'ground_truth/session_intents.jsonl', intents)
    write_rows(output/'ground_truth/intent_labels.jsonl', labels)
    write_rows(output/'ground_truth/paired_designs.jsonl', pairs)
    write_rows(output/'ground_truth/pool_changes.jsonl', metadata)
    unique_meta = { (r['anchor'], r['context'], r['focus']): r for r in metadata }
    write(output/'generation_report.json', dict(report_counts, designs=len(designs),
          anchors=len({c['query_paper_id'] for c in cases}), filtered_papers=len(facets),
          grade_counts=dict(collections.Counter(r['relevance'] for r in labels)),
          designs_by_different_count=dict(collections.Counter(r['different_count'] for r in unique_meta.values())),
          expanded_designs=sum(r['expanded'] for r in unique_meta.values()),
          expanded_anchors=len({r['anchor'] for r in unique_meta.values() if r['expanded']}),
          dataset_status='partial separate diagnostic; not canonical replacement'))
    ceilings = [dict(case_id=c['case_id'], anchor=c['query_paper_id'],
                     direction=truth[c['case_id']]['directions'][truth[c['case_id']]['focus_facet']],
                     grade2=sum(g == 2 for g in judged[c['case_id']].values()),
                     ceiling5=min(5, sum(g == 2 for g in judged[c['case_id']].values()))/5,
                     expanded=meta[c['case_id']]['expanded']) for c in cases]
    write(output/'analysis/pool_ceilings.json', ceilings)
    vectors = facet_vectors(facets)
    handoff = source/Path(config['users_path']).parent
    c_history, c_queries = rows(handoff/'interactions_train.jsonl'), rows(handoff/'search_events.jsonl')
    lookups, summaries, all_focus, pool_effects = {}, [], [], []
    checks = dict(v1_exact_rebuild=True, structural_checks=True, paired_pools=True,
                  observation_copies=0, public_profile_direction_replays=0, proposal_arm_checks=0,
                  non_direction_baseline_invariance=0)

    def evaluate(name, public, original, destination):
        verify_public_replay(public, original, cases)
        checks['public_profile_direction_replays'] += len(public)
        predictions = list(public)
        by_id = {c['case_id']: c for c in cases}
        for base in public:
            if base['model'] not in ('direction_behavior', 'direction_search'):
                continue
            case = by_id[base['case_id']]
            predictions.extend(r for r in direction_controls(case, facets, vectors, base, api) if r['family']=='strict')
            arms = [predict(case, facets, vectors, base, arm) for arm in ('predicted', 'similar', 'flipped')]
            verify_direction_arms(arms, base)
            checks['proposal_arm_checks'] += 1
            predictions.extend(arms)
        # Privileged oracle is constructed only here, on the evaluator side.
        for case in cases:
            intent = truth[case['case_id']]
            oracle = ranked(case, 'oracle_intent', intent_scores(case, intent['facet_importance'],
                                                               intent['directions'], vectors))
            oracle.update(directions=intent['directions'], facet_importance=intent['facet_importance'],
                          privileged_information=True)
            predictions.append(oracle)
        details = evaluate_predictions(predictions, cases, judged, groups, [1, 5, 10], truth)
        add_diagnostics(details, cases, truth, judged, meta)
        summary = aggregate(details)
        lookup = {(r['case_id'], r['model']): r for r in details}
        destination.mkdir(parents=True, exist_ok=True)
        write_rows(destination/'predictions.jsonl', predictions)
        write_rows(destination/'details.jsonl', details)
        fm = focus_metrics(predictions, truth, groups)
        old_fm = focus_metrics(original, truth, groups)
        require(fm == old_fm, 'Focus metrics changed despite fixed evidence')
        write(destination/'focus_metrics.json', fm)
        all_focus.extend(dict(row, condition=name) for row in fm)
        report = dict(experiment='d', protocol=PROTOCOL, dataset_kind='synthetic_observation_contrast_diagnostic',
                      dataset_status='partial', cases=len(cases), summary=summary, notes=[
                          'Only candidate composition differs from v1; evidence and labels rule are fixed.',
                          'Real candidates; synthetic observations only; previously seen 8 anchors.',
                          'Primary: proposal behavior predicted vs always-similar nDCG@10 within v2.',
                          'Direction arms fix focus, C weights, gate, missingness and neutral tie key.',
                          'Intent recall and ceiling fraction are secondary diagnostics, not changed primary metrics.',
                          'Cross-dataset changes reflect the pool intervention, not an algorithm improvement.',
                          'No training/tuning; descriptive subgroup intervals; no human relevance claim.'])
        write(destination/'report.json', report)
        (destination/'report.md').write_text(markdown_report(report), encoding='utf-8')
        csv_rows(destination/'summary.csv', [{k:v for k,v in row.items() if k!='defined_cases'} for row in summary])
        lookups[name] = lookup
        summaries.extend(dict(row, condition=name) for row in summary)
        old_result = v1/'no_observations' if name=='no_observations' else v1/name/'results'
        old_summary = {(r['model'], r['group']): r for r in read(old_result/'report.json')['summary']}
        for row in summary:
            if row['group']=='overall' and row['model'] in MODELS:
                old_row = old_summary[row['model'], 'overall']
                pool_effects.append(dict(condition=name, model=row['model'],
                    v1_ndcg10=old_row['ndcg@10'], v2_ndcg10=row['ndcg@10'],
                    v1_compliance5=old_row['intent_compliance@5'], v2_compliance5=row['intent_compliance@5'],
                    interpretation='same method, changed dataset composition; NOT method gain'))
        print(f'PASS {name}: {len(cases)} cases / {len(predictions)} predictions', flush=True)
        return predictions

    control = pilot.public_predictions(cases, facets, facets, c_history, c_queries, queries,
                                       [], [], config, vectors, api)
    evaluate('no_observations', control, rows(v1/'no_observations/predictions.jsonl'), output/'no_observations')
    for seed in SEEDS:
        for noise in NOISE:
            name = f'seed_{seed}_noise_{noise:g}'
            old_run, run = v1/name, output/name
            # Byte-for-byte copies avoid changing synthetic feedback draws with the pool.
            for relative in ('generated/exposures.jsonl', 'generated/interactions_train.jsonl',
                             'generated/observation_facets.jsonl', 'ground_truth/observation_provenance.jsonl',
                             'results/shuffled_directions.jsonl'):
                target = run/relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((old_run/relative).read_bytes())
                require(digest(target) == digest(old_run/relative), 'Observation/control copy changed')
                checks['observation_copies'] += 1
            exposures, events = rows(run/'generated/exposures.jsonl'), rows(run/'generated/interactions_train.jsonl')
            synthetic = {r['paper_id']: {f:set(r[f]) for f in FACETS}
                         for r in rows(run/'generated/observation_facets.jsonl')}
            provenance = rows(run/'ground_truth/observation_provenance.jsonl')
            pilot.validate_overlay(cases, truth, labels, queries, facets, synthetic, provenance,
                                   exposures, events, users, config, 4, api)
            public = pilot.public_predictions(cases, facets, {**facets, **synthetic}, c_history, c_queries,
                                              queries, exposures, events, config, vectors, api)
            for model in ('fixed_similar', 'profile_similar'):
                require([r for r in control if r['model']==model] == [r for r in public if r['model']==model],
                        'Direction-independent baseline changed with observations')
                checks['non_direction_baseline_invariance'] += 1
            evaluate(name, public, rows(old_run/'results/predictions.jsonl'), run/'results')
    # Reuse verified negative-control summaries because evidence/directions are identical.
    write(output/'shuffle_summary.json', read(v1/'shuffle_summary.json'))
    write(output/'focus_metrics.json', all_focus)
    comparisons = paired_analysis(cases, lookups)
    write(output/'analysis/seed_averaged_comparisons.json', comparisons)
    write(output/'analysis/pool_effects.json', pool_effects)
    csv_rows(output/'analysis/pool_effects.csv', pool_effects)
    csv_rows(output/'analysis/paired_comparisons.csv', [
        {k:v for k,v in row.items() if k not in ('anchor_deltas', 'seeds_averaged')} for row in comparisons])
    write(output/'analysis/absolute_metrics.json', summaries)
    for path, expected in watched.items():
        require(digest(path) == expected, 'Protected input changed: '+str(path))
    verify(PROJECT, code_hashes)
    checks.update(protected_input_hashes=len(watched), protected_inputs_unchanged=True,
                  source_validation=True, no_metric_selection=True,
                  predictions=sum(len(v) for v in lookups.values()),
                  all_six_overlays_validated=True, focus_metrics_identical_to_v1=True)
    write(output/'verification.json', checks)
    write_report(output, summaries, comparisons, ceilings, read(output/'generation_report.json'), all_focus)
    write(output/'manifest.json', dict(protocol=PROTOCOL, not_canonical=True, source_unchanged=True,
          code_hashes=code_hashes, input_hashes={str(p):h for p,h in sorted(watched.items())},
          files={p.relative_to(output).as_posix():digest(p) for p in sorted(output.rglob('*')) if p.is_file()}))
    print('MULTICANDIDATE COMPLETE: '+str(output), flush=True)


def write_report(output, summaries, comparisons, ceilings, generation, focus):
    def cell(value):
        return f'{value:.6f}'
    def comparison(noise, group, metric, family='proposal'):
        return next(r for r in comparisons if r['noise']==noise and r['model']==f'{family}_behavior_predicted'
                    and r['reference']==f'{family}_behavior_similar' and r['group']==group and r['metric']==metric)
    primary = [r for r in comparisons if r['primary']]
    positive_primary = all(r['mean'] > 0 and r['ci95'][0] > 0 for r in primary)
    lines = ['# D v2: mở rộng pool nhiều ứng viên thật', '',
             '**Phạm vi:** bộ phụ chẩn đoán trên 8 anchors đã dùng; giữ v1 và dữ liệu canonical.', '',
             '## Thiết kế đã chốt trước prediction v2', '',
             '- 15 thiết kế / 8 anchors / 90 phiên / 20 candidates mỗi phiên.',
             '- Giữ same và different của v1; thay outside bằng different bổ sung đến tối đa 5 bài.',
             '- 9 thiết kế giữ 1 different; 2 thiết kế có 2; 4 thiết kế có 5. Không bỏ thiết kế theo điểm.',
             '- 6 thiết kế / 5 anchors được mở rộng; vẫn chỉ 4/5 loại focus, không có problem.',
             '- Query, intent, cutoff, C profiles, TF-IDF và phản ứng/observation giữ nguyên v1.',
             '- 3 seed × 2 noise; không observation và xáo phản ứng giữ làm đối chứng.',
             '- Không thay scorer, nhãn overlap, evaluator, validator hoặc thresholds.',
             '- Xáo phản ứng tái sử dụng kết quả v1 đã kiểm hash vì evidence hoàn toàn giống nhau.', '',
             '## Kết quả chính: cùng pool v2, cùng proposal, chỉ thay hướng', '',
             '| Noise | Nhóm | Δ nDCG@10 | CI 95% theo anchor | Δ compliance@5 |',
             '|---|---|---:|---|---:|']
    for noise in NOISE:
        for group in ('overall', 'intent_similar', 'intent_different', 'expanded', 'expanded_intent_different'):
            nd = comparison(noise, group, 'ndcg@10')
            cp = comparison(noise, group, 'intent_compliance@5')
            lines.append(f"| {noise:g} | {group} | {cell(nd['mean'])} | [{cell(nd['ci95'][0])}; {cell(nd['ci95'][1])}] | {cell(cp['mean'])} |")
    lines += ['', 'Primary là overall Δ nDCG@10 behavior predicted − always-similar, chốt trước chạy.',
              'Trung bình ba seed tại từng phiên trước cluster bootstrap 2.000 lần theo anchor.',
              'CI nhóm phụ là mô tả, chưa điều chỉnh nhiều phép so; 8 anchors không đại diện ngoài phân bố.', '',
              '## Điểm tuyệt đối theo từng cấu hình', '',
              '| Cấu hình | Model | nDCG@10 | Compliance@5 | Intent recall@5 (phụ) |',
              '|---|---|---:|---:|---:|']
    for row in summaries:
        if row['condition']!='no_observations' and row['group']=='overall' and row['model'] in MODELS:
            lines.append(f"| {row['condition']} | {row['model']} | {cell(row['ndcg@10'])} | {cell(row['intent_compliance@5'])} | {cell(row['diagnostic_intent_recall@5'])} |")
    lines += ['', '## Suy intent và giới hạn trần pool', '',
              'Focus accuracy/coverage/F1 giữ nguyên v1: chỉ thay candidates, không thay evidence hoặc estimator.', '',
              '| Cấu hình | Behavior focus accuracy | Behavior focus coverage |', '|---|---:|---:|']
    for row in focus:
        if row['condition']!='no_observations' and row['model']=='direction_behavior' and row['group']=='overall':
            lines.append(f"| {row['condition']} | {cell(row['focus_accuracy'])} | {cell(row['focus_coverage'])} |")
    lines += ['', '| Intent | Trần compliance@5 trung bình |', '|---|---:|']
    for direction in ('similar', 'different'):
        values = [r['ceiling5'] for r in ceilings if r['direction']==direction]
        lines.append(f'| {direction} | {cell(sum(values)/len(values))} |')
    lines += ['', 'Compliance v2 cao hơn v1 không tự chứng minh thuật toán tốt hơn: v2 có nhiều grade 2 hơn.',
              'So v1/v2 chỉ là độ nhạy theo thành phần pool; xem analysis/pool_effects.csv.',
              'Các bài cùng grade có gain bằng nhau; nDCG không đánh giá thứ tự nội bộ giữa chúng.',
              'Proposal vẫn có thể đạt nDCG=1 khi suy đúng hướng vì ưu tiên đúng quy tắc overlap của nhãn.', '',
              '## Kết luận và cách dùng trong báo cáo', '',
              ('Primary dương và CI theo anchor nằm trên 0 ở cả hai mức nhiễu.' if positive_primary else
               'Primary chưa đồng thời dương với CI nằm trên 0 ở cả hai mức nhiễu; không tuyên bố đạt mạnh H2.'),
              'V2 mở rộng kiểm chứng từ một sang nhiều bài thỏa intent ở một phần cohort; không tăng anchors độc lập.',
              'Đối chứng strict scorer được giữ đầy đủ; không quy chênh lệch giữa hai scorer thành hiệu ứng riêng của direction.', '',
              '| Noise | Strict Δ nDCG@10 overall | CI 95% | Proposal leave-one-anchor-out |',
              '|---|---:|---|---|']
    for noise in NOISE:
        strict = comparison(noise, 'overall', 'ndcg@10', 'strict')
        proposal = comparison(noise, 'overall', 'ndcg@10')
        lines.append(f"| {noise:g} | {cell(strict['mean'])} | {strict['ci95']} | {proposal['leave_one_anchor_out_range']} |")
    lines += ['', 'Cách diễn đạt phù hợp: “Trong benchmark overlap mô phỏng có pool nhiều ứng viên ở một phần thiết kế,',
              'chúng tôi đánh giá tác dụng của hướng suy được bằng các đối chứng giữ nguyên ranker, trọng số và bằng chứng.”',
              'Kèm số liệu đạt/không đạt ở trên; không suy ra semantic relevance, người dùng thật, novelty hoặc khả năng nhận bài.',
              'Muốn khẳng định tổng quát hơn cần anchors/corpus giữ riêng và relevance được đánh giá độc lập.', '',
              '## Kiểm tra và tái lập', '',
              '- verification.json: kiểm nguồn, replay hướng/profile, ba arms, fallback, sáu overlays và v1 không đổi.',
              '- manifest.json: hashes code/input/output; design.json: quyết định trước prediction v2.',
              '- analysis/seed_averaged_comparisons.json: CI, leave-one-anchor-out và delta từng anchor.',
              '- analysis/pool_ceilings.json: trần compliance từng phiên; ground_truth/pool_changes.jsonl: thay đổi IDs.', '',
              '```powershell',
              'python -B -m unittest discover -s scripts/exp_d -p test_multicandidate_proposal.py',
              'python -B scripts/exp_d/run_multicandidate_proposal.py --output data/exp_d/results/my_multicandidate_v2',
              'python -B scripts/exp_d/run_multicandidate_proposal.py --verify-only --output '+output.relative_to(PROJECT).as_posix(),
              '```', '',
              'Mỗi lượt dùng output mới; không ghi đè. Không sửa dữ liệu hoặc kết quả cũ để cải thiện điểm.', '']
    (output/'report.md').write_text('\n'.join(lines), encoding='utf-8')


def verify_run(output):
    manifest = read(output/'manifest.json')
    verify(output, manifest['files'])
    verify(PROJECT, manifest['code_hashes'])
    for path, expected in manifest['input_hashes'].items():
        require(digest(Path(path)) == expected, 'Protected input hash mismatch: '+path)
    checks = read(output/'verification.json')
    require(checks['protected_inputs_unchanged'] and checks['all_six_overlays_validated'], 'Incomplete verification')
    design = read(output/'design.json')
    source, v1 = Path(design['source']), Path(design['v1'])
    sys.path[:0] = [str(source/'scripts'), str(source), str(DATA)]
    from baseline_common import aggregate
    from experiment_runner import evaluate_predictions
    from experiment_io import FACETS
    from data.experiment_common import facet_index, overlapping, session_grade, timestamp
    import build_contrast_sessions as builder
    from build_multicandidate_sessions import expand
    # Reconstruct the intervention independently from the frozen source and v1.
    from experiment_io import load_silver, concept_sets
    from validate_experiments import validate_experiment
    validated = validate_experiment(source, 'd')
    config = validated['config']
    _, raw, annotation_metadata, _ = load_silver(source, Path(config['facets_path']).parent)
    facets = concept_sets(raw, annotation_metadata)
    api = dict(FACETS=FACETS, facet_index=facet_index, overlapping=overlapping,
               session_grade=session_grade, timestamp=timestamp)
    designs = builder.feasible_designs(facets, api)
    original_cases = rows(v1/'generated/sessions.jsonl')
    intents = rows(v1/'ground_truth/session_intents.jsonl')
    rebuilt, rebuilt_labels, rebuilt_meta = expand(original_cases, intents, designs, facets, api)
    cases = rows(output/'generated/sessions.jsonl')
    require(cases == rebuilt, 'Saved sessions do not match the registered pool intervention')
    require(rows(output/'ground_truth/intent_labels.jsonl') == rebuilt_labels, 'Saved labels do not reproduce')
    require(rows(output/'ground_truth/pool_changes.jsonl') == rebuilt_meta, 'Pool metadata does not reproduce')
    require(rows(output/'ground_truth/session_intents.jsonl') == intents, 'Hidden intents changed')
    require((output/'generated/search_events.jsonl').read_bytes() == (v1/'generated/search_events.jsonl').read_bytes(),
            'Query bytes changed')
    truth = {r['case_id']:r for r in intents}
    groups = {cid:r['query_mode'] for cid,r in truth.items()}
    judged = {c['case_id']:{} for c in cases}
    for row in rebuilt_labels:
        judged[row['case_id']][row['candidate_id']] = row['relevance']
    metadata = {r['case_id']:r for r in rebuilt_meta}
    lookups, all_focus = {}, []
    for name in ['no_observations'] + [f'seed_{seed}_noise_{noise:g}' for seed in SEEDS for noise in NOISE]:
        destination = output/name if name=='no_observations' else output/name/'results'
        original = v1/name if name=='no_observations' else v1/name/'results'
        predictions = rows(destination/'predictions.jsonl')
        details = evaluate_predictions(predictions, cases, judged, groups, [1,5,10], truth)
        add_diagnostics(details, cases, truth, judged, metadata)
        require(details == rows(destination/'details.jsonl'), 'Saved per-case metrics do not reproduce: '+name)
        require(aggregate(details) == read(destination/'report.json')['summary'], 'Summary does not reproduce: '+name)
        fm = focus_metrics(predictions, truth, groups)
        require(fm == read(destination/'focus_metrics.json'), 'Focus metrics do not reproduce: '+name)
        require(fm == read(original/'focus_metrics.json'), 'Focus metrics differ from v1: '+name)
        all_focus.extend(dict(row, condition=name) for row in fm)
        lookups[name] = {(r['case_id'],r['model']):r for r in details}
        if name!='no_observations':
            for relative in ('generated/exposures.jsonl', 'generated/interactions_train.jsonl',
                             'generated/observation_facets.jsonl', 'ground_truth/observation_provenance.jsonl',
                             'results/shuffled_directions.jsonl'):
                require((output/name/relative).read_bytes() == (v1/name/relative).read_bytes(),
                        'Evidence/control bytes differ: '+name+'/'+relative)
    require(all_focus == read(output/'focus_metrics.json'), 'Suite focus metrics do not reproduce')
    require(paired_analysis(cases, lookups) == read(output/'analysis/seed_averaged_comparisons.json'),
            'Seed-averaged comparisons do not reproduce')
    print(f"VERIFIED {len(manifest['files'])} outputs / {len(manifest['input_hashes'])} inputs / "
          f"{len(manifest['code_hashes'])} code files; all metrics/CI reconstructed: {output}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DATA/'workspace_baseline_20261016_v1')
    parser.add_argument('--v1', type=Path, default=DATA/'results/contrast_proposal_20261016_v1')
    parser.add_argument('--output', type=Path, default=DATA/'results/multicandidate_proposal_20261017_v2')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    if args.verify_only:
        verify_run(args.output.resolve())
    else:
        run(args)


if __name__ == '__main__':
    main()
