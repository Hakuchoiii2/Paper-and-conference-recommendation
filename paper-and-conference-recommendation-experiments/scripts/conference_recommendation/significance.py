"""Statistical significance tests and rank correlation diagnostics (IEEE standard).

All randomized procedures are deterministic with default seed=42.
"""

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .metrics import evaluate_predictions


def mcnemar_exact_test(
    hits_a: Sequence[float], hits_b: Sequence[float]
) -> Dict[str, Any]:
    """Two-sided exact McNemar's test using the binomial distribution.

    Suitable for small discordant counts (n_10 + n_01 < 25) on N=168 test papers.
    """
    if len(hits_a) != len(hits_b):
        raise ValueError("hits_a and hits_b must have the same length")
    a = [1 if float(x) >= 0.5 else 0 for x in hits_a]
    b = [1 if float(x) >= 0.5 else 0 for x in hits_b]

    n_10 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    n_01 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    n = n_10 + n_01

    if n == 0:
        p_value = 1.0
    else:
        k_min = min(n_10, n_01)
        # Exact two-sided binomial tail probability: 2 * sum_{j=0}^{k_min} C(n, j) * 0.5^n
        tail = sum(math.comb(n, j) for j in range(k_min + 1)) * (0.5 ** n)
        p_value = min(1.0, 2.0 * tail)

    return {
        "n_10": int(n_10),
        "n_01": int(n_01),
        "discordant": int(n),
        "p_value": float(p_value),
        "significant_005": bool(p_value < 0.05),
    }


def paired_permutation_test(
    scores_a: Sequence[float],
    scores_b: Sequence[float],
    n_resamples: int = 10000,
    seed: int = 42,
) -> Dict[str, Any]:
    """Two-sided paired sign-flip permutation test (default 10,000 resamples, seed=42)."""
    if len(scores_a) != len(scores_b):
        raise ValueError("scores_a and scores_b must have the same length")
    if n_resamples <= 0:
        raise ValueError("n_resamples must be positive")

    arr_a = np.asarray(scores_a, dtype=np.float64)
    arr_b = np.asarray(scores_b, dtype=np.float64)
    n = len(arr_a)
    if n == 0:
        return {
            "mean_a": 0.0,
            "mean_b": 0.0,
            "delta": 0.0,
            "p_value": 1.0,
            "n_resamples": int(n_resamples),
            "significant_005": False,
        }

    diffs = arr_a - arr_b
    obs_delta = float(np.mean(diffs))
    abs_obs = abs(obs_delta)

    if np.all(diffs == 0.0):
        p_value = 1.0
    else:
        rng = np.random.default_rng(seed)
        # Chunked sign-flip matrix to keep peak memory small for large n_resamples
        exceed = 0
        chunk_size = 2000
        remaining = n_resamples
        while remaining > 0:
            batch = min(chunk_size, remaining)
            signs = rng.choice((-1.0, 1.0), size=(batch, n))
            perm_means = np.abs(np.mean(signs * diffs[None, :], axis=1))
            exceed += int(np.sum(perm_means >= abs_obs - 1e-12))
            remaining -= batch
        p_value = float((1 + exceed) / (n_resamples + 1))

    return {
        "mean_a": float(np.mean(arr_a)),
        "mean_b": float(np.mean(arr_b)),
        "delta": obs_delta,
        "p_value": p_value,
        "n_resamples": int(n_resamples),
        "significant_005": bool(p_value < 0.05),
    }


def paired_bootstrap_ci(
    predictions_a: Dict[str, List[Tuple[str, float]]],
    predictions_b: Optional[Dict[str, List[Tuple[str, float]]]],
    ground_truth: Dict[str, str],
    candidate_venues: List[str],
    n_boot: int = 10000,
    seed: int = 42,
) -> Dict[str, Any]:
    """Paired bootstrap 95% confidence intervals for Macro-Hit@3 and Macro-MRR.

    Resamples query paper_ids with replacement B times (seed=42) and computes
    exact per-bootstrap macro averages across venues present in the bootstrap sample.
    """
    if n_boot <= 0:
        raise ValueError("n_boot must be positive")
    pids = sorted(pid for pid in predictions_a if pid in ground_truth)
    if predictions_b is not None:
        pids = [pid for pid in pids if pid in predictions_b]
    n = len(pids)
    if n == 0:
        empty = {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0}
        return {"macro_hit@3": empty, "macro_mrr": empty}

    venue_to_idx = {v: i for i, v in enumerate(sorted(candidate_venues))}
    num_venues = len(venue_to_idx)
    venue_ids = np.array([venue_to_idx[ground_truth[pid]] for pid in pids], dtype=np.int64)

    def extract_arrays(preds: Dict[str, List[Tuple[str, float]]]) -> Tuple[np.ndarray, np.ndarray]:
        hits3 = np.zeros(n, dtype=np.float64)
        rrs = np.zeros(n, dtype=np.float64)
        for i, pid in enumerate(pids):
            tv = ground_truth[pid]
            ranked = preds[pid]
            for rank, (venue, _) in enumerate(ranked, start=1):
                if venue == tv:
                    rrs[i] = 1.0 / rank
                    if rank <= 3:
                        hits3[i] = 1.0
                    break
        return hits3, rrs

    hits3_a, rrs_a = extract_arrays(predictions_a)
    hits3_b, rrs_b = (extract_arrays(predictions_b) if predictions_b is not None else (None, None))

    rng = np.random.default_rng(seed)
    boot_mh3_a = np.zeros(n_boot, dtype=np.float64)
    boot_mmrr_a = np.zeros(n_boot, dtype=np.float64)
    boot_delta_mh3 = np.zeros(n_boot, dtype=np.float64) if predictions_b is not None else None
    boot_delta_mmrr = np.zeros(n_boot, dtype=np.float64) if predictions_b is not None else None

    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        v_sample = venue_ids[idx]
        counts = np.bincount(v_sample, minlength=num_venues)
        active = counts > 0
        denom = counts[active]

        sum_h3_a = np.bincount(v_sample, weights=hits3_a[idx], minlength=num_venues)[active]
        sum_rr_a = np.bincount(v_sample, weights=rrs_a[idx], minlength=num_venues)[active]
        mh3_a = float(np.mean(sum_h3_a / denom))
        mmrr_a = float(np.mean(sum_rr_a / denom))
        boot_mh3_a[b] = mh3_a
        boot_mmrr_a[b] = mmrr_a

        if predictions_b is not None:
            sum_h3_b = np.bincount(v_sample, weights=hits3_b[idx], minlength=num_venues)[active]
            sum_rr_b = np.bincount(v_sample, weights=rrs_b[idx], minlength=num_venues)[active]
            mh3_b = float(np.mean(sum_h3_b / denom))
            mmrr_b = float(np.mean(sum_rr_b / denom))
            boot_delta_mh3[b] = mh3_a - mh3_b
            boot_delta_mmrr[b] = mmrr_a - mmrr_b

    def summarize(samples: np.ndarray, point_estimate: float) -> Dict[str, float]:
        low, high = np.percentile(samples, [2.5, 97.5])
        return {
            "point": float(point_estimate),
            "boot_mean": float(np.mean(samples)),
            "ci_low": float(low),
            "ci_high": float(high),
        }

    sum_a, _ = evaluate_predictions(predictions_a, ground_truth, candidate_venues)
    result: Dict[str, Any] = {
        "n_boot": int(n_boot),
        "seed": int(seed),
        "macro_hit@3": summarize(boot_mh3_a, sum_a["macro_hit@3"]),
        "macro_mrr": summarize(boot_mmrr_a, sum_a["macro_mrr"]),
    }

    if predictions_b is not None:
        sum_b, _ = evaluate_predictions(predictions_b, ground_truth, candidate_venues)
        result["delta_macro_hit@3"] = summarize(
            boot_delta_mh3, sum_a["macro_hit@3"] - sum_b["macro_hit@3"]
        )
        result["delta_macro_mrr"] = summarize(
            boot_delta_mmrr, sum_a["macro_mrr"] - sum_b["macro_mrr"]
        )

    return result


def holm_bonferroni(
    p_values: Dict[str, float], alpha: float = 0.05
) -> Dict[str, Dict[str, Any]]:
    """Apply Holm-Bonferroni step-down multiple testing correction."""
    if not p_values:
        return {}
    items = sorted(p_values.items(), key=lambda kv: (float(kv[1]), kv[0]))
    m = len(items)
    adjusted: Dict[str, Dict[str, Any]] = {}
    running_max = 0.0
    for idx, (label, raw_p) in enumerate(items):
        raw = float(raw_p)
        adj = min(1.0, (m - idx) * raw)
        running_max = max(running_max, adj)
        adjusted[label] = {
            "raw_p": raw,
            "adjusted_p": float(running_max),
            "reject_null": bool(running_max < alpha),
        }
    return adjusted


def win_tie_loss(ranks_a: Sequence[int], ranks_b: Sequence[int]) -> Dict[str, int]:
    """Count per-query Win / Tie / Loss where lower rank is better (rank_a < rank_b)."""
    if len(ranks_a) != len(ranks_b):
        raise ValueError("ranks_a and ranks_b must have the same length")
    win = sum(1 for ra, rb in zip(ranks_a, ranks_b) if ra < rb)
    tie = sum(1 for ra, rb in zip(ranks_a, ranks_b) if ra == rb)
    loss = sum(1 for ra, rb in zip(ranks_a, ranks_b) if ra > rb)
    return {"win": int(win), "tie": int(tie), "loss": int(loss)}


def _average_ranks(values: Sequence[float]) -> np.ndarray:
    """Compute average ranks (1-based) handling ties identically to scipy.stats.rankdata."""
    arr = np.asarray(values, dtype=np.float64)
    n = len(arr)
    order = np.argsort(arr, kind="mergesort")
    ranks = np.empty(n, dtype=np.float64)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and arr[order[j + 1]] == arr[order[i]]:
            j += 1
        avg_rank = 0.5 * (i + j) + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def _spearman_fallback(x: Sequence[float], y: Sequence[float]) -> Tuple[float, Optional[float]]:
    import itertools

    rx = _average_ranks(x)
    ry = _average_ranks(y)
    dx = rx - np.mean(rx)
    dy = ry - np.mean(ry)
    denom = float(np.sqrt(np.sum(dx * dx) * np.sum(dy * dy)))
    if denom == 0.0:
        return float("nan"), None
    rho = float(np.sum(dx * dy) / denom)
    n = len(x)
    p_val: Optional[float] = None
    if n <= 8:
        # Exact two-sided permutation p-value over all n! permutations
        abs_obs = abs(rho)
        total = 0
        exceed = 0
        for perm in itertools.permutations(ry):
            dp = np.asarray(perm, dtype=np.float64) - np.mean(ry)
            r_perm = float(np.sum(dx * dp) / denom)
            if abs(r_perm) >= abs_obs - 1e-12:
                exceed += 1
            total += 1
        p_val = float(exceed / total)
    return rho, p_val


def _kendall_fallback(x: Sequence[float], y: Sequence[float]) -> Tuple[float, Optional[float]]:
    import itertools

    n = len(x)

    def tau_b(xs: Sequence[float], ys: Sequence[float]) -> float:
        concordant = 0
        discordant = 0
        ties_x = 0
        ties_y = 0
        for i in range(n):
            for j in range(i + 1, n):
                dx = xs[i] - xs[j]
                dy = ys[i] - ys[j]
                if dx == 0 and dy == 0:
                    continue
                if dx == 0:
                    ties_x += 1
                elif dy == 0:
                    ties_y += 1
                elif dx * dy > 0:
                    concordant += 1
                else:
                    discordant += 1
        denom = math.sqrt((concordant + discordant + ties_x) * (concordant + discordant + ties_y))
        if denom == 0.0:
            return float("nan")
        return float((concordant - discordant) / denom)

    tau = tau_b(x, y)
    if math.isnan(tau):
        return tau, None
    p_val: Optional[float] = None
    if n <= 8:
        abs_obs = abs(tau)
        total = 0
        exceed = 0
        for perm in itertools.permutations(y):
            t_perm = tau_b(x, perm)
            if not math.isnan(t_perm) and abs(t_perm) >= abs_obs - 1e-12:
                exceed += 1
            total += 1
        p_val = float(exceed / total)
    return tau, p_val


def rank_correlation_matrix(
    exp_a_metrics: Dict[str, Dict[str, float]],
    downstream_metrics: Dict[str, Dict[str, float]],
) -> Dict[str, Dict[str, Dict[str, Optional[float]]]]:
    """Compute Spearman's rho and Kendall's tau between Exp A and Conference metrics."""
    try:
        from scipy.stats import kendalltau as _scipy_kendalltau, spearmanr as _scipy_spearmanr
        has_scipy = True
    except ImportError:
        has_scipy = False

    shared_models = sorted(set(exp_a_metrics) & set(downstream_metrics))
    if len(shared_models) < 2:
        return {}

    exp_a_keys = sorted({k for m in shared_models for k in exp_a_metrics[m]})
    down_keys = sorted({k for m in shared_models for k in downstream_metrics[m]})

    matrix: Dict[str, Dict[str, Dict[str, Optional[float]]]] = {}
    for a_key in exp_a_keys:
        vec_a = [float(exp_a_metrics[m][a_key]) for m in shared_models if a_key in exp_a_metrics[m]]
        if len(vec_a) != len(shared_models):
            continue
        matrix[a_key] = {}
        for d_key in down_keys:
            vec_d = [float(downstream_metrics[m][d_key]) for m in shared_models if d_key in downstream_metrics[m]]
            if len(vec_d) != len(shared_models):
                continue
            if len(set(vec_a)) < 2 or len(set(vec_d)) < 2:
                matrix[a_key][d_key] = {
                    "spearman_rho": None,
                    "spearman_p": None,
                    "kendall_tau": None,
                    "kendall_p": None,
                }
                continue
            if has_scipy:
                rho, rho_p = _scipy_spearmanr(vec_a, vec_d)
                tau, tau_p = _scipy_kendalltau(vec_a, vec_d)
            else:
                rho, rho_p = _spearman_fallback(vec_a, vec_d)
                tau, tau_p = _kendall_fallback(vec_a, vec_d)
            matrix[a_key][d_key] = {
                "spearman_rho": None if math.isnan(rho) else float(rho),
                "spearman_p": None if rho_p is None or math.isnan(rho_p) else float(rho_p),
                "kendall_tau": None if math.isnan(tau) else float(tau),
                "kendall_p": None if tau_p is None or math.isnan(tau_p) else float(tau_p),
            }
    return matrix
