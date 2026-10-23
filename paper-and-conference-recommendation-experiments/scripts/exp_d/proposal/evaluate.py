"""Focus metrics and exact original metrics; oracle belongs to evaluator only."""
import collections
import csv
import hashlib
import math
import random
import statistics

from data_io import FACETS, read_rows, require
from baseline_common import aggregate as legacy_aggregate, intent_scores, ranked
from experiment_runner import evaluate_predictions as legacy_evaluate
from methods import MODELS

ORACLE = 'oracle_intent'
METRICS = ('direction_accuracy', 'joint_accuracy', 'coverage', 'joint_coverage',
           'ndcg10', 'ndcg5', 'pair_strict', 'pair_rank_success', 'top1_grade2',
           'paired_direction_success', 'legacy_direction_accuracy', 'legacy_direction_coverage',
           'importance_mae', 'intent_compliance@5', 'intent_compliance@10',
           'recall@5', 'recall@10', 'precision@5', 'precision@10', 'mrr@5', 'mrr@10')
CONTRASTS = (
    ('reaction_vs_no_signal', 'direction_behavior', 'profile_similar'),
    ('query_vs_no_signal', 'query_only', 'profile_similar'),
    ('query_added_to_reactions', 'direction_search', 'direction_behavior'),
    ('reactions_added_to_query', 'direction_search', 'query_only'),
    ('directions_vs_no_signal', 'direction_search', 'profile_similar'),
    ('vote_vs_delta', 'vote', 'direction_search'),
    ('bayes_vs_delta', 'bayes_h', 'direction_search'),
    ('ordinal_vs_delta', 'ordinal_intent', 'direction_search'))


def predicted_focus(case, directions):
    active = [f for f in FACETS if f != case['context_facet'] and directions.get(f) in ('similar','different')]
    return active[0] if len(active) == 1 else None


def load_truth(directory):
    return dict(intents={r['case_id']:r for r in read_rows(directory/'ground_truth/session_intents.jsonl')},
                designs={r['design_id']:r for r in read_rows(directory/'ground_truth/designs.jsonl')},
                labels=read_rows(directory/'ground_truth/intent_labels.jsonl'))


def oracle_predictions(cases, conditions, truth, vectors):
    """Called only after public predictions are persisted; includes true weights."""
    rows = []
    for condition in conditions:
        for case in cases:
            intent = truth['intents'][case['case_id']]
            weights, directions = intent['facet_importance'], intent['directions']
            row = ranked(case, ORACLE, intent_scores(case, weights, directions, vectors))
            row.update(condition=condition, facet_importance=dict(weights), directions=dict(directions),
                       ranking_directions=dict(directions), ranking_policy='true_session_intent',
                       privileged_information=True)
            rows.append(row)
    return rows


def score_predictions(predictions, cases, truth, condition_metadata, include_oracle=False):
    by_case = {c['case_id']:c for c in cases}
    labels = collections.defaultdict(dict)
    for row in truth['labels']:
        require(row['candidate_id'] not in labels[row['case_id']], 'Duplicate label')
        labels[row['case_id']][row['candidate_id']] = row['relevance']
    expected_models = set(MODELS) | ({ORACLE} if include_oracle else set())
    expected = {(condition,cid,model) for condition in condition_metadata for cid in by_case for model in expected_models}
    keys = [(r['condition'],r['case_id'],r['model']) for r in predictions]
    require(len(keys)==len(set(keys)) and set(keys)==expected, 'Incomplete or duplicated prediction matrix')
    original = {}
    # Call the actual original evaluator, not a reimplementation of its metrics.
    for condition in condition_metadata:
        batch = [r for r in predictions if r['condition']==condition]
        groups = {cid:truth['designs'][truth['intents'][cid]['design_id']]['candidate_source_group'] for cid in by_case}
        for row in legacy_evaluate(batch, cases, labels, groups, [5,10], truth['intents']):
            original[condition,row['case_id'],row['model']] = row
    details = []
    for prediction in predictions:
        cid, model, condition = prediction['case_id'], prediction['model'], prediction['condition']
        case, intent, grades = by_case[cid], truth['intents'][cid], labels[cid]
        design = truth['designs'][intent['design_id']]
        require(set(grades)==set(case['candidate_ids']), 'Candidate pool differs from truth')
        ranking = [r['paper_id'] for r in prediction['ranking']]
        scores = {r['paper_id']:r['score'] for r in prediction['ranking']}
        require(all(math.isfinite(s) for s in scores.values()), 'Nonfinite score')
        focus = intent['focus_facet']
        actual, direction = intent['directions'][focus], prediction['directions'].get(focus,'unknown')
        inferred = predicted_focus(case,prediction['directions'])
        positives, negatives = ([p for p,g in grades.items() if g==v] for v in (2,1))
        require(len(positives)==len(negatives)==1, 'observation_v1 expects one grade 2 and one grade 1')
        positive, negative = positives[0], negatives[0]
        legacy = original[condition,cid,model]
        old = legacy['metrics']
        metrics = dict(direction_accuracy=float(direction==actual),
                       joint_accuracy=float(direction==actual and inferred==focus),
                       coverage=float(direction in ('similar','different')),
                       joint_coverage=float(inferred is not None),
                       ndcg10=old['ndcg@10'], ndcg5=old['ndcg@5'],
                       pair_strict=float(scores[positive]>scores[negative]),
                       pair_rank_success=float(ranking.index(positive)<ranking.index(negative)),
                       top1_grade2=float(grades[ranking[0]]==2),
                       legacy_direction_accuracy=old['direction_accuracy'],
                       legacy_direction_coverage=old['direction_coverage'],
                       **{m:old[m] for m in METRICS if m in old and m!='direction_accuracy'})
        metadata = condition_metadata[condition]
        details.append(dict(model=model, condition=condition, case_id=cid, design_id=intent['design_id'],
            anchor=case['query_paper_id'], cluster=design['work_group'], focus=focus,
            true_direction=actual, predicted_direction=direction, predicted_focus=inferred,
            query_mode=intent['query_mode'], candidate_source=design['candidate_source_group'],
            seed=metadata['seed'], noise=metadata['noise'], privileged_information=model==ORACLE,
            metrics=metrics, direction_pairs=legacy['direction_pairs'], legacy_metrics=old))
    pairs = collections.defaultdict(list)
    for row in details:
        pairs[row['model'],row['condition'],row['design_id'],row['query_mode']].append(row)
    for rows in pairs.values():
        require(len(rows)==2 and {r['true_direction'] for r in rows}=={'similar','different'}, 'Missing opposite intent')
        success = float(all(r['metrics']['pair_strict'] for r in rows))
        for row in rows:
            row['metrics']['paired_direction_success'] = success
    return details


def group_names(row):
    return ('overall', f"noise:{row['noise']:g}", 'query:'+row['query_mode'],
            'focus:'+row['focus'], 'source:'+row['candidate_source'], 'direction:'+row['true_direction'])


def macro_f1(weighted_pairs):
    values = []
    for label in ('similar','different'):
        tp = sum(w for t,p,w in weighted_pairs if t==label and p==label)
        fp = sum(w for t,p,w in weighted_pairs if t!=label and p==label)
        fn = sum(w for t,p,w in weighted_pairs if t==label and p!=label)
        values.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0)
    return statistics.mean(values)


def summarize(details):
    cells, buckets = collections.defaultdict(list), collections.defaultdict(list)
    for row in details:
        for group in group_names(row):
            cells[row['model'],group,row['cluster'],row['design_id']].append(row)
            buckets[row['model'],group].append(row)
    by_cluster = collections.defaultdict(list)
    for (model,group,cluster,_), rows in cells.items():
        by_cluster[model,group,cluster].append(rows)
    values = {}
    for key, designs in by_cluster.items():
        result = {m:statistics.mean(statistics.mean(r['metrics'][m] for r in rows) for rows in designs) for m in METRICS}
        focus_pairs, legacy_pairs = [], []
        for rows in designs:
            weight = 1/(len(designs)*len(rows))
            for row in rows:
                focus_pairs.append((row['true_direction'],row.get('predicted_direction','unknown'),weight))
                pairs = row.get('direction_pairs',[])
                legacy_pairs.extend((t,p,weight/len(pairs)) for t,p in pairs)
        result['focus_macro_f1'] = macro_f1(focus_pairs)
        result['legacy_direction_macro_f1'] = macro_f1(legacy_pairs)
        values[key] = result
    order = {m:i for i,m in enumerate(MODELS+(ORACLE,))}
    summary = []
    for (model,group), rows in sorted(buckets.items(),key=lambda x:(x[0][1],order[x[0][0]])):
        clusters = [r for (m,g,_),r in values.items() if m==model and g==group]
        metrics = {m:statistics.mean(r[m] for r in clusters) for m in METRICS+('focus_macro_f1','legacy_direction_macro_f1')}
        item = dict(model=model, group=group, evaluations=len(rows), sessions=len({r['case_id'] for r in rows}),
                    designs=len({r['design_id'] for r in rows}), anchors=len({r['anchor'] for r in rows}),
                    clusters=len(clusters), privileged_information=model==ORACLE, **metrics)
        item['conditional_accuracy'] = item['direction_accuracy']/item['coverage'] if item['coverage'] else None
        summary.append(item)
    return summary, values


def legacy_summary(details):
    rows = [dict(model=r['model'], case_id=r['case_id'], group=r['candidate_source'],
                 groups=group_names(r), metrics=r['legacy_metrics'], direction_pairs=r['direction_pairs'],
                 positive_candidates=2) for r in details]
    return legacy_aggregate(rows)


def quantile(values,p):
    values = sorted(values)
    index = (len(values)-1)*p
    low = int(index)
    return values[low]+(values[min(low+1,len(values)-1)]-values[low])*(index-low)


def paired_comparisons(cluster_values,repetitions=2000):
    output = []
    groups = sorted({g for _,g,_ in cluster_values if g=='overall' or g.startswith('noise:')})
    for group in groups:
        for label,method,baseline in CONTRASTS:
            units = sorted(c for m,g,c in cluster_values if m==method and g==group)
            require(units and all((baseline,group,c) in cluster_values for c in units), 'Unpaired anchors')
            for metric in ('direction_accuracy','joint_accuracy','coverage','ndcg10','top1_grade2','pair_strict'):
                differences = [cluster_values[method,group,c][metric]-cluster_values[baseline,group,c][metric] for c in units]
                seed = int(hashlib.sha256((group+'|'+label+'|'+metric).encode()).hexdigest()[:16],16)
                rng = random.Random(seed)
                draws = [statistics.mean(rng.choices(differences,k=len(units))) for _ in range(repetitions)]
                output.append(dict(comparison=label,method=method,baseline=baseline,group=group,metric=metric,
                    delta=statistics.mean(differences),ci_low=quantile(draws,.025),ci_high=quantile(draws,.975),
                    clusters=len(units),bootstrap_repetitions=repetitions,exploratory=True))
    return output


def write_csv(path,rows):
    require(bool(rows), 'Cannot export an empty table')
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def conclusions(comparisons,summary):
    claims = []
    for name,metric in (('reaction_vs_no_signal','direction_accuracy'),
                        ('query_added_to_reactions','direction_accuracy'),
                        ('directions_vs_no_signal','ndcg10'),('ordinal_vs_delta','direction_accuracy'),
                        ('ordinal_vs_delta','ndcg10')):
        row = next(r for r in comparisons if r['comparison']==name and r['metric']==metric and r['group']=='overall')
        status = ('positive' if row['ci_low']>0 else 'negative' if row['ci_high']<0 else 'uncertain')
        claims.append(dict(**row,status=status))
    public = [r for r in summary if r['group']=='overall' and not r['privileged_information']]
    return dict(scope='controlled_mock_pilot',independent_test=False,claims=claims,
                best_public_on_pilot={m:max(public,key=lambda r:r[m])['model'] for m in ('direction_accuracy','ndcg10')},
                oracle_is_not_competing=True,no_claim_of_novelty=True)
