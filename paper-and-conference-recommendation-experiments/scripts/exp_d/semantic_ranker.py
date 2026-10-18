"""Frozen dense facet representation ablations; estimator and lexical gate stay fixed."""
from baseline_common import dot, ranked
from intent_priority import observed_focus


def rerank(case, facets, lexical_vectors, embeddings, baseline, mode):
    if mode not in ('full', 'active', 'hybrid'):
        raise ValueError('Unknown semantic policy')
    channel, separator, arm = baseline['model'].removeprefix('direction_').partition('__')
    if channel not in ('behavior', 'search') or not baseline['model'].startswith('direction_'):
        raise ValueError('Expected public direction prediction')
    model = ('hybrid_active_' if mode == 'hybrid' else 'semantic_' + mode + '_') + channel
    if separator:
        model += '__' + arm
    weights = dict(baseline['facet_importance'])
    directions = dict(baseline['directions'])
    confidence = dict(baseline['direction_confidence'])
    context, anchor = case['context_facet'], case['query_paper_id']
    focus = observed_focus(context, directions, confidence)
    fallback = False
    if mode != 'full':
        total = weights.get(context, 0) + weights.get(focus, 0) if focus else 0
        fallback = focus is None or total <= 0
        if not fallback:
            weights = {f: w / total if f in (context, focus) else 0.0 for f, w in weights.items()}
    if fallback:
        scores = {r['paper_id']: r['score'] for r in baseline['ranking']}
    else:
        scores = {}
        for pid in case['candidate_ids']:
            # Preserve baseline lexical context gate; dense cosine does not admit new contexts.
            if not lexical_vectors[anchor, context] or not lexical_vectors[pid, context] or \
                    dot(lexical_vectors[anchor, context], lexical_vectors[pid, context]) <= 0:
                scores[pid] = -1.0
                continue
            numerator = denominator = 0.0
            missing = False
            for f, w in weights.items():
                direction = directions.get(f, 'unknown')
                if not w or direction == 'ignore' or not lexical_vectors[anchor, f]:
                    continue
                if not lexical_vectors[pid, f]:
                    missing = True
                    break
                dense = max(0.0, min(1.0, float(embeddings[anchor, f] @ embeddings[pid, f])))
                if mode == 'hybrid':
                    lexical = max(0.0, min(1.0, dot(lexical_vectors[anchor, f], lexical_vectors[pid, f])))
                    similarity = .5 * lexical + .5 * dense  # Fixed in advance; no label tuning.
                else:
                    similarity = dense
                numerator += w * (1 - similarity if direction == 'different' else similarity)
                denominator += w
            scores[pid] = -1.0 if missing else numerator / denominator if denominator else 0.0
    result = ranked(case, model, scores)
    result.update(directions=directions, direction_confidence=confidence, facet_importance=weights,
                  predicted_focus=focus, fallback_to_baseline=fallback, training='frozen_pretrained_encoder',
                  semantic_policy=mode, context_gate='original_tfidf_positive',
                  hybrid_dense_weight=.5 if mode == 'hybrid' else 1.0)
    return result
