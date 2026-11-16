"""Shared scoring contracts for runtime models and experiment matrices."""
import math


def observed(vector):
    if vector is None:
        return False
    if isinstance(vector, dict):
        return any(v != 0 for v in vector.values())
    return any(float(v) != 0 for v in vector)


def validate_weights(weights, facets):
    if set(weights) != set(facets):
        raise ValueError(f"Weights must contain exactly {tuple(facets)}")
    result = {f: float(weights[f]) for f in facets}
    if any(not math.isfinite(w) or w < 0 for w in result.values()) or sum(result.values()) <= 0:
        raise ValueError("Weights must be finite, nonnegative and have positive sum")
    total = sum(result.values())
    return {f: w / total for f, w in result.items()}


def rank_neighbors(pids, venues, similarities, candidate_venues, k):
    if not isinstance(k, int) or k <= 0:
        raise ValueError("k must be a positive integer")
    scores = {v: 0.0 for v in sorted(candidate_venues)}
    neighbors = sorted(zip(pids, venues, similarities), key=lambda row: (-float(row[2]), row[0]))[:k]
    for _, venue, score in neighbors:
        scores[venue] += float(score)
    return sorted(scores.items(), key=lambda row: (-row[1], row[0]))
