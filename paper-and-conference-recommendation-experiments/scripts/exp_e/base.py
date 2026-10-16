"""Base interface and shared profile utilities for Experiment E temporal models."""
from abc import ABC, abstractmethod
import collections
from typing import Any, Callable, Dict, List, Optional

from baseline_common import (
    BEHAVIOR_WEIGHTS,
    FACETS,
    dot,
    parse_search,
    profile_score,
    search_vocabulary,
    unit_vector,
)
from validate_all import require, validate_time


class BaseTemporalModel(ABC):
    """Abstract base class for all temporal profile adaptation models in Exp E.

    Naming convention for `name`:
        `<family>__<method>__<param>` (e.g., `decay__exp__hl30`, `decay__adaptive__divergence`)
        or canonical aliases (`static`, `recent`, `decay`).
    """

    def __init__(self, name: str, **kwargs: Any):
        self.name = name
        self.config = kwargs

    @abstractmethod
    def build_profiles(
        self,
        history: List[Dict[str, Any]],
        searches: List[Dict[str, Any]],
        facets: Dict[str, Dict[str, set]],
        cutoff: str,
        options: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        """Build per-user 5-facet profiles using only observable evidence before `cutoff`.

        Returns:
            Mapping `user_id -> {'vectors': {facet: unit_vec}, 'facet_importance': {facet: float}}`.
        """
        raise NotImplementedError

    def score_candidates(
        self,
        profile: Optional[Dict[str, Any]],
        candidate_ids: List[str],
        facets: Dict[str, Dict[str, set]],
    ) -> Dict[str, float]:
        """Score candidate papers against the constructed user profile."""
        if not profile:
            return {pid: 0.0 for pid in candidate_ids}
        return {pid: profile_score(profile, pid, facets) for pid in candidate_ids}


def build_custom_weighted_profiles(
    history: List[Dict[str, Any]],
    searches: List[Dict[str, Any]],
    facets: Dict[str, Dict[str, set]],
    cutoff: str,
    weight_fn: Callable[[str, Any, Any], float],
) -> Dict[str, Dict[str, Any]]:
    """Build 5-facet profiles with a custom temporal weight function `weight_fn(user_id, event_time, cutoff_time)`."""
    raw = collections.defaultdict(lambda: {f: collections.Counter() for f in FACETS})
    vocabulary = search_vocabulary(facets)
    cutoff_dt = validate_time(cutoff)

    for event in history:
        time_dt = validate_time(event['timestamp'])
        require(time_dt < cutoff_dt, 'Future event reached profile builder')
        t_weight = weight_fn(event['user_id'], time_dt, cutoff_dt)
        if t_weight == 0:
            continue
        weight = t_weight * BEHAVIOR_WEIGHTS[event['interaction_type']]
        for f in FACETS:
            values = facets[event['paper_id']][f]
            if values:
                share = weight / len(values)
                for concept in sorted(values):
                    raw[event['user_id']][f][concept] += share

    for query in searches:
        time_dt = validate_time(query['timestamp'])
        require(time_dt < cutoff_dt, 'Future event reached profile builder')
        t_weight = weight_fn(query['user_id'], time_dt, cutoff_dt)
        if t_weight == 0:
            continue
        for f, values in parse_search(query['text'], facets, vocabulary).items():
            for key, sign in (('include', 1), ('exclude', -1)):
                for concept in sorted(values[key]):
                    raw[query['user_id']][f][concept] += sign * t_weight

    profiles = {}
    for user, values in raw.items():
        mass = {f: sum(abs(v) for v in values[f].values()) for f in FACETS}
        total = sum(mass.values())
        profiles[user] = dict(
            vectors={f: unit_vector(values[f]) for f in FACETS},
            facet_importance={f: mass[f] / total if total else 1.0 / len(FACETS) for f in FACETS},
        )
    return profiles


def profile_similarity(
    profile_a: Optional[Dict[str, Any]],
    profile_b: Optional[Dict[str, Any]],
) -> Optional[float]:
    """Compute weighted cosine similarity in [0, 1] between two 5-facet profiles.

    Returns None if either profile is missing or empty.
    """
    if not profile_a or not profile_b:
        return None
    active_facets = [
        f for f in FACETS if profile_a['vectors'].get(f) and profile_b['vectors'].get(f)
    ]
    if not active_facets:
        return None
    total_weight = 0.0
    weighted_sim = 0.0
    for f in active_facets:
        w = 0.5 * (profile_a['facet_importance'][f] + profile_b['facet_importance'][f])
        cos = dot(profile_a['vectors'][f], profile_b['vectors'][f])
        # Map cosine from [-1, 1] to [0, 1]
        sim_01 = max(0.0, min(1.0, 0.5 * (cos + 1.0)))
        weighted_sim += w * sim_01
        total_weight += w
    return weighted_sim / total_weight if total_weight > 0 else 0.5


def blend_profiles(
    short_profile: Optional[Dict[str, Any]],
    long_profile: Optional[Dict[str, Any]],
    alpha: float,
) -> Optional[Dict[str, Any]]:
    """Linearly blend short-term profile (weight `alpha`) and long-term profile (weight `1 - alpha`)."""
    require(0.0 <= alpha <= 1.0, 'Blend parameter alpha must be in [0, 1]')
    if not short_profile and not long_profile:
        return None
    if not short_profile:
        return long_profile
    if not long_profile:
        return short_profile

    vectors = {}
    raw_importance = {}
    for f in FACETS:
        vec_s = short_profile['vectors'].get(f, {})
        vec_l = long_profile['vectors'].get(f, {})
        merged_concepts = set(vec_s.keys()) | set(vec_l.keys())
        combined_vec = {
            c: alpha * vec_s.get(c, 0.0) + (1.0 - alpha) * vec_l.get(c, 0.0)
            for c in merged_concepts
        }
        vectors[f] = unit_vector(combined_vec)
        raw_importance[f] = (
            alpha * short_profile['facet_importance'][f]
            + (1.0 - alpha) * long_profile['facet_importance'][f]
        )

    total_imp = sum(raw_importance.values())
    facet_importance = {
        f: raw_importance[f] / total_imp if total_imp > 0 else 1.0 / len(FACETS)
        for f in FACETS
    }
    return dict(vectors=vectors, facet_importance=facet_importance)
