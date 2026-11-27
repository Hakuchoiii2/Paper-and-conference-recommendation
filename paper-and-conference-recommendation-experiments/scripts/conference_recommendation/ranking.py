"""Shared scoring and venue-level aggregation contracts for runtime models and experiments."""
from collections import Counter, defaultdict
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple


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
