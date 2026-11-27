"""Shared scoring and venue-level aggregation contracts for runtime models and experiments."""
from collections import Counter, defaultdict
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

FACET_ORDER: Tuple[str, ...] = ("problem", "task", "method", "dataset", "contribution")
LOCKED_EXP_B_WEIGHTS: Dict[str, float] = {
    "problem": 0.40,
    "task": 0.20,
    "method": 0.20,
    "dataset": 0.10,
    "contribution": 0.10,
}


def observed(vector: Any) -> bool:
    if vector is None:
        return False
    if isinstance(vector, dict):
        return any(v != 0 for v in vector.values())
    return any(float(v) != 0 for v in vector)


def validate_weights(weights: Dict[str, float], facets: Sequence[str]) -> Dict[str, float]:
    if set(weights) != set(facets):
        raise ValueError(f"Weights must contain exactly {tuple(facets)}")
    result = {f: float(weights[f]) for f in facets}
    if any(not math.isfinite(w) or w < 0 for w in result.values()) or sum(result.values()) <= 0:
        raise ValueError("Weights must be finite, nonnegative and have positive sum")
    total = sum(result.values())
    return {f: w / total for f, w in result.items()}


def _filter_valid_rows(
    pids: Sequence[str],
    venues: Sequence[str],
    similarities: Sequence[float],
    valid_mask: Optional[Sequence[bool]] = None,
) -> List[Tuple[str, str, float]]:
    rows: List[Tuple[str, str, float]] = []
    if valid_mask is None:
        for pid, venue, sim in zip(pids, venues, similarities):
            val = float(sim)
            if math.isfinite(val):
                rows.append((pid, venue, val))
    else:
        for pid, venue, sim, ok in zip(pids, venues, similarities, valid_mask):
            val = float(sim)
            if bool(ok) and math.isfinite(val):
                rows.append((pid, venue, val))
    return rows


def rank_neighbors(
    pids: Sequence[str],
    venues: Sequence[str],
    similarities: Sequence[float],
    candidate_venues: Sequence[str],
    k: int,
    valid_mask: Optional[Sequence[bool]] = None,
) -> List[Tuple[str, float]]:
    """Baseline Sum-kNN venue voting with deterministic tie-breaking."""
    if not isinstance(k, int) or k <= 0:
        raise ValueError("k must be a positive integer")
    scores = {v: 0.0 for v in sorted(candidate_venues)}
    valid_rows = _filter_valid_rows(pids, venues, similarities, valid_mask)
    neighbors = sorted(valid_rows, key=lambda row: (-row[2], row[0]))[:k]
    for _, venue, score in neighbors:
        if venue in scores:
            scores[venue] += score
    return sorted(scores.items(), key=lambda row: (-row[1], row[0]))


def rank_venues_temp_softmax(
    pids: Sequence[str],
    venues: Sequence[str],
    similarities: Sequence[float],
    candidate_venues: Sequence[str],
    k: int,
    tau: float = 0.05,
    valid_mask: Optional[Sequence[bool]] = None,
) -> List[Tuple[str, float]]:
    """Temperature-scaled softmax voting over top-k valid neighbors."""
    if not isinstance(k, int) or k <= 0:
        raise ValueError("k must be a positive integer")
    if not math.isfinite(tau) or tau <= 0:
        raise ValueError("tau must be a positive finite float")

    scores = {v: 0.0 for v in sorted(candidate_venues)}
    valid_rows = _filter_valid_rows(pids, venues, similarities, valid_mask)
    neighbors = sorted(valid_rows, key=lambda row: (-row[2], row[0]))[:k]
    if not neighbors:
        return sorted(scores.items(), key=lambda row: (-row[1], row[0]))

    max_sim = max(row[2] for row in neighbors)
    exps = [math.exp((row[2] - max_sim) / tau) for row in neighbors]
    total_exp = sum(exps)
    if total_exp > 0.0:
        for (_, venue, _), weight in zip(neighbors, exps):
            if venue in scores:
                scores[venue] += weight / total_exp
    return sorted(scores.items(), key=lambda row: (-row[1], row[0]))


def rank_venues_prior_norm(
    pids: Sequence[str],
    venues: Sequence[str],
    similarities: Sequence[float],
    candidate_venues: Sequence[str],
    k: int,
    tau: float = 0.05,
    alpha: float = 0.5,
    valid_mask: Optional[Sequence[bool]] = None,
) -> List[Tuple[str, float]]:
    """Prior-normalized temperature-scaled voting: divides venue score by N_v^alpha."""
    if not isinstance(k, int) or k <= 0:
        raise ValueError("k must be a positive integer")
    if not math.isfinite(tau) or tau <= 0:
        raise ValueError("tau must be a positive finite float")
    if not math.isfinite(alpha) or alpha < 0:
        raise ValueError("alpha must be a nonnegative finite float")

    scores = {v: 0.0 for v in sorted(candidate_venues)}
    # Count reference papers per venue strictly from the supplied reference partition
    venue_counts = Counter(venues)
    valid_rows = _filter_valid_rows(pids, venues, similarities, valid_mask)
    neighbors = sorted(valid_rows, key=lambda row: (-row[2], row[0]))[:k]
    if not neighbors:
        return sorted(scores.items(), key=lambda row: (-row[1], row[0]))

    max_sim = max(row[2] for row in neighbors)
    for _, venue, sim in neighbors:
        if venue in scores:
            scores[venue] += math.exp((sim - max_sim) / tau)

    for venue in scores:
        n_v = venue_counts.get(venue, 0)
        if n_v > 0 and scores[venue] > 0.0:
            scores[venue] /= (float(n_v) ** alpha)

    return sorted(scores.items(), key=lambda row: (-row[1], row[0]))


def rank_venues_per_venue_top_m(
    pids: Sequence[str],
    venues: Sequence[str],
    similarities: Sequence[float],
    candidate_venues: Sequence[str],
    m: int = 3,
    valid_mask: Optional[Sequence[bool]] = None,
) -> List[Tuple[str, float]]:
    """Per-venue Top-m local pooling: average similarity of top-m valid papers per venue."""
    if not isinstance(m, int) or m <= 0:
        raise ValueError("m must be a positive integer")

    by_venue: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    valid_rows = _filter_valid_rows(pids, venues, similarities, valid_mask)
    for pid, venue, sim in valid_rows:
        by_venue[venue].append((pid, sim))

    scores: Dict[str, float] = {}
    for venue in sorted(candidate_venues):
        items = by_venue.get(venue)
        if not items:
            scores[venue] = float("-inf")
        else:
            top_items = sorted(items, key=lambda row: (-row[1], row[0]))[:m]
            scores[venue] = sum(sim for _, sim in top_items) / len(top_items)

    return sorted(scores.items(), key=lambda row: (-row[1], row[0]))


def aggregate_venue_scores(
    pids: Sequence[str],
    venues: Sequence[str],
    similarities: Sequence[float],
    candidate_venues: Sequence[str],
    config: Dict[str, Any],
    valid_mask: Optional[Sequence[bool]] = None,
) -> List[Tuple[str, float]]:
    """Dispatch venue-level aggregation according to config['aggregation']."""
    agg = config.get("aggregation", "sum_knn")
    if agg == "sum_knn":
        return rank_neighbors(
            pids, venues, similarities, candidate_venues,
            k=int(config["k"]), valid_mask=valid_mask,
        )
    if agg == "temp_softmax":
        return rank_venues_temp_softmax(
            pids, venues, similarities, candidate_venues,
            k=int(config["k"]), tau=float(config.get("agg_tau", 0.05)),
            valid_mask=valid_mask,
        )
    if agg == "prior_norm":
        return rank_venues_prior_norm(
            pids, venues, similarities, candidate_venues,
            k=int(config["k"]),
            tau=float(config.get("agg_tau", 0.05)),
            alpha=float(config.get("alpha", 0.5)),
            valid_mask=valid_mask,
        )
    if agg == "per_venue_top_m":
        return rank_venues_per_venue_top_m(
            pids, venues, similarities, candidate_venues,
            m=int(config.get("m", 3)), valid_mask=valid_mask,
        )
    raise ValueError(f"Unsupported venue aggregation method: {agg}")


def rank_venues_from_score_row(
    venue_scores: Sequence[float],
    candidate_venues: Sequence[str],
    valid_row: Optional[Sequence[bool]] = None,
) -> List[Tuple[str, float]]:
    """Convert a 1D venue score vector [V] into a deterministically sorted list of (venue_id, score)."""
    if len(venue_scores) != len(candidate_venues):
        raise ValueError("venue_scores and candidate_venues must have the same length")
    items: List[Tuple[str, float]] = []
    for idx, (venue, sc) in enumerate(zip(candidate_venues, venue_scores)):
        ok = True if valid_row is None else bool(valid_row[idx])
        val = float(sc)
        if not ok or math.isnan(val):
            val = float("-inf")
        items.append((str(venue), val))
    return sorted(items, key=lambda row: (-row[1], row[0]))


def rank_venues_from_score_matrix(
    scores_matrix: np.ndarray,
    query_pids: Sequence[str],
    candidate_venues: Sequence[str],
    valid_mask: Optional[np.ndarray] = None,
) -> Dict[str, List[Tuple[str, float]]]:
    """Convert a 2D [Q, V] venue score matrix into predictions dict {paper_id: [(venue_id, score), ...]}."""
    if scores_matrix.shape != (len(query_pids), len(candidate_venues)):
        raise ValueError(
            f"Expected scores_matrix shape {(len(query_pids), len(candidate_venues))}, got {scores_matrix.shape}"
        )
    predictions: Dict[str, List[Tuple[str, float]]] = {}
    for q_idx, pid in enumerate(query_pids):
        v_row = None if valid_mask is None else valid_mask[q_idx]
        predictions[str(pid)] = rank_venues_from_score_row(
            scores_matrix[q_idx], candidate_venues, valid_row=v_row
        )
    return predictions


def compute_active_weight_mass(
    query_masks: Dict[str, Sequence[bool]],
    weights: Optional[Dict[str, float]] = None,
    facets: Sequence[str] = FACET_ORDER,
) -> np.ndarray:
    """Compute query-only active weight mass g(q) = sum_f w_f * mask_f(q) in [0.0, 1.0]."""
    norm_weights = validate_weights(weights or LOCKED_EXP_B_WEIGHTS, facets)
    first_f = facets[0]
    n_queries = len(query_masks[first_f]) if first_f in query_masks else 0
    g_q = np.zeros(n_queries, dtype=np.float64)
    for f in facets:
        mask_arr = np.asarray(query_masks[f], dtype=bool)
        if len(mask_arr) != n_queries:
            raise ValueError(f"Inconsistent query mask length for facet {f}")
        g_q += norm_weights[f] * mask_arr.astype(np.float64)
    return np.clip(g_q, 0.0, 1.0)


def _infer_mask(
    explicit_masks: Optional[Dict[str, Sequence[bool]]],
    embeddings: Optional[Dict[str, Any]],
    facet: str,
    expected_len: int,
) -> np.ndarray:
    if explicit_masks is not None and facet in explicit_masks:
        arr = np.asarray(explicit_masks[facet], dtype=bool)
        if len(arr) != expected_len:
            raise ValueError(f"Mask length mismatch for facet {facet}: {len(arr)} != {expected_len}")
        return arr
    if embeddings is not None and facet in embeddings:
        emb = embeddings[facet]
        if isinstance(emb, np.ndarray) and emb.ndim == 2:
            if emb.shape[0] != expected_len:
                raise ValueError(f"Embedding rows mismatch for facet {facet}: {emb.shape[0]} != {expected_len}")
            return np.linalg.norm(emb, axis=1) > 0.0
        arr = np.array([observed(v) for v in emb], dtype=bool)
        if len(arr) != expected_len:
            raise ValueError(f"Embedding sequence mismatch for facet {facet}: {len(arr)} != {expected_len}")
        return arr
    raise ValueError(f"Must provide masks or embeddings for facet '{facet}'")


def _extract_dense_row(emb_container: Any, idx: int) -> Optional[np.ndarray]:
    v = emb_container[idx]
    if v is None or isinstance(v, dict):
        return None
    arr = np.asarray(v, dtype=np.float64)
    norm = float(np.linalg.norm(arr))
    if norm == 0.0:
        return None
    return arr / norm


def compute_facet_first_venue_scores(
    ref_venues: Sequence[str],
    candidate_venues: Sequence[str],
    weights: Optional[Dict[str, float]] = None,
    mode: str = "top_m",
    top_m: int = 3,
    facet_sims: Optional[Dict[str, np.ndarray]] = None,
    query_masks: Optional[Dict[str, Sequence[bool]]] = None,
    ref_masks: Optional[Dict[str, Sequence[bool]]] = None,
    query_embeddings: Optional[Dict[str, Any]] = None,
    ref_embeddings: Optional[Dict[str, Any]] = None,
    ref_pids: Optional[Sequence[str]] = None,
    facets: Sequence[str] = FACET_ORDER,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Mechanism 1: Facet-First Venue Aggregation with locked weights & dynamic denominator renormalization.

    Scores each candidate venue v per facet f independently over P_{v, f} = {p in D_ref | venue(p) == v and mask_f(p) == 1},
    then combines active facet venue scores over V_venue(q, v) = {f | mask_f(q) == 1 and |P_{v, f}| > 0}.

    Returns:
        (scores_matrix [Q, V], valid_mask [Q, V], activation_stats dict)
    """
    if mode not in ("top_m", "centroid"):
        raise ValueError(f"Unsupported Facet-First mode: {mode}. Expected 'top_m' or 'centroid'.")
    if mode == "top_m" and (not isinstance(top_m, int) or top_m <= 0):
        raise ValueError("top_m must be a positive integer")

    norm_weights = validate_weights(weights or LOCKED_EXP_B_WEIGHTS, facets)
    n_ref = len(ref_venues)
    n_venues = len(candidate_venues)
    if ref_pids is not None and len(ref_pids) != n_ref:
        raise ValueError("ref_pids must match length of ref_venues")

    # Determine number of queries Q
    first_f = facets[0]
    if query_masks is not None and first_f in query_masks:
        n_queries = len(query_masks[first_f])
    elif facet_sims is not None and first_f in facet_sims:
        n_queries = int(np.asarray(facet_sims[first_f]).shape[0])
    elif query_embeddings is not None and first_f in query_embeddings:
        n_queries = len(query_embeddings[first_f])
    else:
        raise ValueError("Cannot infer number of queries; provide query_masks, facet_sims, or query_embeddings")

    q_masks: Dict[str, np.ndarray] = {}
    r_masks: Dict[str, np.ndarray] = {}
    for f in facets:
        q_masks[f] = _infer_mask(query_masks, query_embeddings, f, n_queries)
        r_masks[f] = _infer_mask(ref_masks, ref_embeddings, f, n_ref)

    numerator = np.zeros((n_queries, n_venues), dtype=np.float64)
    denominator = np.zeros((n_queries, n_venues), dtype=np.float64)
    active_by_facet: Dict[str, np.ndarray] = {}
    venue_pool_sizes: Dict[str, Dict[str, int]] = {f: {} for f in facets}

    for f in facets:
        w_f = norm_weights[f]
        q_mask_f = q_masks[f]
        r_mask_f = r_masks[f]
        r_f_mat = np.zeros((n_queries, n_venues), dtype=np.float64)
        active_f = np.zeros((n_queries, n_venues), dtype=bool)
        active_q_indices = np.where(q_mask_f)[0]

        # Prepare similarities or embeddings depending on mode
        sim_f: Optional[np.ndarray] = None
        if mode == "top_m":
            if facet_sims is not None and f in facet_sims:
                sim_f = np.asarray(facet_sims[f], dtype=np.float64)
                if sim_f.shape != (n_queries, n_ref):
                    raise ValueError(f"facet_sims[{f}] shape {sim_f.shape} != {(n_queries, n_ref)}")
            elif query_embeddings is not None and ref_embeddings is not None:
                sim_f = np.zeros((n_queries, n_ref), dtype=np.float64)
                q_emb_f = query_embeddings[f]
                r_emb_f = ref_embeddings[f]
                for qi in active_q_indices:
                    qv = _extract_dense_row(q_emb_f, qi)
                    if qv is not None:
                        for ri in range(n_ref):
                            if r_mask_f[ri]:
                                rv = _extract_dense_row(r_emb_f, ri)
                                if rv is not None:
                                    sim_f[qi, ri] = float(np.clip(np.dot(qv, rv), -1.0, 1.0))
                    elif isinstance(q_emb_f[qi], dict):
                        qd = q_emb_f[qi]
                        for ri in range(n_ref):
                            if r_mask_f[ri] and isinstance(r_emb_f[ri], dict):
                                rd = r_emb_f[ri]
                                sim_f[qi, ri] = float(sum(val * rd.get(k, 0.0) for k, val in qd.items()))
            else:
                raise ValueError(f"mode='top_m' requires facet_sims or (query_embeddings, ref_embeddings) for '{f}'")
        else:
            if query_embeddings is None or ref_embeddings is None or f not in query_embeddings or f not in ref_embeddings:
                raise ValueError(f"mode='centroid' requires query_embeddings and ref_embeddings for '{f}'")

        for v_idx, venue in enumerate(candidate_venues):
            p_indices = [ri for ri, rv in enumerate(ref_venues) if rv == venue and bool(r_mask_f[ri])]
            venue_pool_sizes[f][str(venue)] = len(p_indices)
            if not p_indices:
                continue
            active_f[:, v_idx] = q_mask_f
            if len(active_q_indices) == 0:
                continue

            if mode == "top_m":
                assert sim_f is not None
                m_eff = min(top_m, len(p_indices))
                sub_sims = sim_f[np.ix_(active_q_indices, p_indices)]
                if m_eff == len(p_indices):
                    r_f_mat[active_q_indices, v_idx] = np.mean(sub_sims, axis=1)
                elif ref_pids is not None:
                    sub_pids = [str(ref_pids[ri]) for ri in p_indices]
                    for row_i, qi in enumerate(active_q_indices):
                        ranked_p = sorted(
                            zip(sub_sims[row_i], sub_pids),
                            key=lambda item: (-float(item[0]), item[1]),
                        )[:m_eff]
                        r_f_mat[qi, v_idx] = sum(float(s) for s, _ in ranked_p) / m_eff
                else:
                    # Partition top m_eff largest similarities
                    part = np.partition(sub_sims, -m_eff, axis=1)[:, -m_eff:]
                    r_f_mat[active_q_indices, v_idx] = np.mean(part, axis=1)
            else:
                # mode == "centroid"
                q_emb_f = query_embeddings[f]
                r_emb_f = ref_embeddings[f]
                sample_ref = r_emb_f[p_indices[0]]
                if isinstance(sample_ref, dict):
                    # Sparse dictionary centroid (TF-IDF)
                    mean_dict: Dict[str, float] = defaultdict(float)
                    inv_n = 1.0 / len(p_indices)
                    for ri in p_indices:
                        rd = r_emb_f[ri]
                        if isinstance(rd, dict):
                            for k, val in rd.items():
                                mean_dict[k] += float(val) * inv_n
                    norm_c = math.sqrt(sum(val * val for val in mean_dict.values()))
                    denom_c = norm_c + 1e-8
                    centroid_dict = {k: val / denom_c for k, val in mean_dict.items()}
                    for qi in active_q_indices:
                        qd = q_emb_f[qi]
                        if isinstance(qd, dict) and qd:
                            r_f_mat[qi, v_idx] = float(
                                sum(float(val) * centroid_dict.get(k, 0.0) for k, val in qd.items())
                            )
                else:
                    # Dense vector centroid: c_{v, f} = mean(e_f(P_{v, f})) / (||mean||_2 + 1e-8)
                    ref_rows = []
                    for ri in p_indices:
                        rv = _extract_dense_row(r_emb_f, ri)
                        if rv is not None:
                            ref_rows.append(rv)
                    if not ref_rows:
                        active_f[:, v_idx] = False
                        continue
                    ref_stack = np.vstack(ref_rows)
                    mean_vec = np.mean(ref_stack, axis=0, dtype=np.float64)
                    centroid = mean_vec / (float(np.linalg.norm(mean_vec)) + 1e-8)
                    for qi in active_q_indices:
                        qv = _extract_dense_row(q_emb_f, qi)
                        if qv is not None:
                            r_f_mat[qi, v_idx] = float(np.dot(qv, centroid))

        active_by_facet[f] = active_f
        if w_f > 0.0:
            numerator += w_f * r_f_mat * active_f
            denominator += w_f * active_f

    valid_mask = denominator > 0.0
    scores_matrix = np.full((n_queries, n_venues), -np.inf, dtype=np.float64)
    np.divide(numerator, denominator, out=scores_matrix, where=valid_mask)

    activation_stats: Dict[str, Any] = {
        "n_queries": int(n_queries),
        "n_venues": int(n_venues),
        "n_ref": int(n_ref),
        "mode": mode,
        "top_m": int(top_m) if mode == "top_m" else None,
        "valid_pair_rate": float(np.mean(valid_mask)) if (n_queries * n_venues) > 0 else 0.0,
        "valid_query_rate": float(np.mean(np.any(valid_mask, axis=1))) if (n_queries > 0 and n_venues > 0) else 0.0,
        "per_facet_pair_activation_rate": {},
        "per_facet_query_activation_rate": {},
        "per_facet_venue_pool_coverage": {},
    }
    for f in facets:
        act_f = active_by_facet[f]
        pair_rate = float(np.mean(act_f)) if (n_queries * n_venues) > 0 else 0.0
        q_rate = float(np.mean(q_masks[f])) if n_queries > 0 else 0.0
        v_cov = (
            float(sum(1 for cnt in venue_pool_sizes[f].values() if cnt > 0) / n_venues)
            if n_venues > 0
            else 0.0
        )
        activation_stats[f"{f}_activation_rate"] = pair_rate
        activation_stats[f"{f}_query_activation_rate"] = q_rate
        activation_stats[f"{f}_venue_pool_coverage"] = v_cov
        activation_stats["per_facet_pair_activation_rate"][f] = pair_rate
        activation_stats["per_facet_query_activation_rate"][f] = q_rate
        activation_stats["per_facet_venue_pool_coverage"][f] = v_cov

    return scores_matrix, valid_mask, activation_stats


def _zscore_normalize_row(
    scores_row: np.ndarray,
    valid_row: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Per-query z-score normalization over valid venue entries with zero-variance & invalid fallback."""
    row = np.asarray(scores_row, dtype=np.float64)
    n_venues = len(row)
    if n_venues == 0:
        return np.zeros(0, dtype=np.float64)
    valid = np.isfinite(row) if valid_row is None else (np.asarray(valid_row, dtype=bool) & np.isfinite(row))
    if not np.any(valid):
        return np.zeros(n_venues, dtype=np.float64)

    vals = row[valid]
    mean_v = float(np.mean(vals))
    std_v = float(np.std(vals))
    if std_v < 1e-12:
        z_valid = np.zeros_like(vals, dtype=np.float64)
    else:
        z_valid = (vals - mean_v) / (std_v + 1e-8)

    result = np.empty(n_venues, dtype=np.float64)
    result[valid] = z_valid
    if not np.all(valid):
        fill_val = float(np.min(z_valid)) - 1.0
        result[~valid] = fill_val
    return result


def compute_adaptive_fusion_scores(
    full_scores: np.ndarray,
    facet_scores: np.ndarray,
    query_masks: Dict[str, Sequence[bool]],
    beta: float = 0.2,
    facet_valid_mask: Optional[np.ndarray] = None,
    weights: Optional[Dict[str, float]] = None,
    facets: Sequence[str] = FACET_ORDER,
) -> Tuple[np.ndarray, np.ndarray]:
    """Mechanism 2: Coverage-Aware Adaptive Fusion.

    Computes g(q) = sum_f w_f * mask_f(q) in [0, 1], z-score normalizes full_scores[q, :]
    and facet_scores[q, :] independently across candidate venues, and fuses:
        score_adaptive(q, v) = (1 - beta * g(q)) * z_full(q, v) + (beta * g(q)) * z_facet(q, v).

    Returns:
        (adaptive_scores [Q, V], g_q [Q])
    """
    if not math.isfinite(beta) or beta < 0.0 or beta > 1.0:
        raise ValueError("beta must be a finite float in [0.0, 1.0]")

    full_mat = np.asarray(full_scores, dtype=np.float64)
    facet_mat = np.asarray(facet_scores, dtype=np.float64)
    if full_mat.shape != facet_mat.shape or full_mat.ndim != 2:
        raise ValueError(f"full_scores {full_mat.shape} and facet_scores {facet_mat.shape} must have identical 2D shape")
    if facet_valid_mask is not None and facet_valid_mask.shape != facet_mat.shape:
        raise ValueError("facet_valid_mask shape must match facet_scores shape")

    n_queries, n_venues = full_mat.shape
    g_q = compute_active_weight_mass(query_masks, weights=weights, facets=facets)
    if len(g_q) != n_queries:
        raise ValueError(f"g_q length {len(g_q)} does not match number of queries {n_queries}")

    adaptive_scores = np.zeros((n_queries, n_venues), dtype=np.float64)
    for q_idx in range(n_queries):
        z_full = _zscore_normalize_row(full_mat[q_idx], valid_row=None)
        v_row = None if facet_valid_mask is None else facet_valid_mask[q_idx]
        z_facet = _zscore_normalize_row(facet_mat[q_idx], valid_row=v_row)
        alpha_q = float(beta) * float(g_q[q_idx])
        adaptive_scores[q_idx] = (1.0 - alpha_q) * z_full + alpha_q * z_facet

    return adaptive_scores, g_q


def rerank_coarse_to_fine(
    stage1_ranked: List[Tuple[str, float]],
    stage2_scores: Union[Dict[str, float], Sequence[float]],
    top_c: int = 5,
    candidate_venues: Optional[Sequence[str]] = None,
    stage2_valid_mask: Optional[Union[Dict[str, bool], Sequence[bool]]] = None,
) -> List[Tuple[str, float]]:
    """Mechanism 3: Coarse-to-Fine Facet Reranking.

    Stage 1 provides ranked venue list [v_(1), ..., v_(V)].
    Stage 2 extracts top_c venues, re-sorts ONLY those top_c venues by (-stage2_score(q, v), conference_id)
    (handling valid_mask=False as -np.inf), and concatenates with the untouched tail [v_(top_c+1), ..., v_(V)].
    """
    if not isinstance(top_c, int) or top_c <= 0:
        raise ValueError("top_c must be a positive integer")

    if isinstance(stage2_scores, dict):
        score_map = {str(k): float(v) for k, v in stage2_scores.items()}
    else:
        if candidate_venues is None or len(candidate_venues) != len(stage2_scores):
            raise ValueError("candidate_venues must be provided and match length when stage2_scores is a sequence")
        score_map = {str(v): float(s) for v, s in zip(candidate_venues, stage2_scores)}

    if stage2_valid_mask is None:
        valid_map = {k: True for k in score_map}
    elif isinstance(stage2_valid_mask, dict):
        valid_map = {str(k): bool(v) for k, v in stage2_valid_mask.items()}
    else:
        if candidate_venues is None or len(candidate_venues) != len(stage2_valid_mask):
            raise ValueError("candidate_venues must match stage2_valid_mask length")
        valid_map = {str(v): bool(ok) for v, ok in zip(candidate_venues, stage2_valid_mask)}

    c_eff = min(top_c, len(stage1_ranked))
    head = stage1_ranked[:c_eff]
    tail = list(stage1_ranked[c_eff:])

    head_stage2: List[Tuple[str, float]] = []
    for venue, _ in head:
        ok = valid_map.get(venue, False)
        raw_s = score_map.get(venue, float("-inf"))
        s2 = raw_s if (ok and not math.isnan(raw_s)) else float("-inf")
        head_stage2.append((venue, s2))

    reranked_head = sorted(head_stage2, key=lambda row: (-row[1], row[0]))
    return reranked_head + tail


def rerank_coarse_to_fine_batch(
    stage1_predictions: Dict[str, List[Tuple[str, float]]],
    query_pids: Sequence[str],
    stage2_scores_matrix: np.ndarray,
    candidate_venues: Sequence[str],
    top_c: int = 5,
    stage2_valid_mask: Optional[np.ndarray] = None,
) -> Dict[str, List[Tuple[str, float]]]:
    """Batch Coarse-to-Fine reranking across Q queries."""
    if stage2_scores_matrix.shape != (len(query_pids), len(candidate_venues)):
        raise ValueError("stage2_scores_matrix shape mismatch with (query_pids, candidate_venues)")
    predictions: Dict[str, List[Tuple[str, float]]] = {}
    for q_idx, pid in enumerate(query_pids):
        s1_list = stage1_predictions[str(pid)]
        v_row = None if stage2_valid_mask is None else stage2_valid_mask[q_idx]
        predictions[str(pid)] = rerank_coarse_to_fine(
            s1_list,
            stage2_scores_matrix[q_idx],
            top_c=top_c,
            candidate_venues=candidate_venues,
            stage2_valid_mask=v_row,
        )
    return predictions
