"""Adaptive exponential decay model guided by short-vs-long profile divergence."""
from typing import Any, Dict, List

from baseline_common import facet_profiles
from exp_e.base import (
    BaseTemporalModel,
    build_custom_weighted_profiles,
    profile_similarity,
)
from exp_e.registry import register_temporal_model
from validate_all import validate_time


@register_temporal_model('decay__adaptive__divergence', min_hl=10.0, max_hl=60.0, default_hl=21.0)
class AdaptiveDriftDecayModel(BaseTemporalModel):
    """Adjusts each user's half-life dynamically based on preference stability before cutoff.

    - Users whose recent period profile closely matches their older history receive a long
      half-life (`max_hl` = 60 days) to preserve historical signal.
    - Users exhibiting divergence between recent and older history receive a short
      half-life (`min_hl` = 10 days) to rapidly adapt to concept drift.
    """

    def build_profiles(
        self,
        history: List[Dict[str, Any]],
        searches: List[Dict[str, Any]],
        facets: Dict[str, Dict[str, set]],
        cutoff: str,
        options: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        min_hl = float(self.config.get('min_hl', 10.0))
        max_hl = float(self.config.get('max_hl', 60.0))
        default_hl = float(self.config.get('default_hl', 21.0))

        recent_start_str = options.get('recent_start')
        if not recent_start_str:
            return facet_profiles(history, searches, facets, cutoff, half_life_days=default_hl)

        recent_start_dt = validate_time(recent_start_str)
        older_history = [e for e in history if validate_time(e['timestamp']) < recent_start_dt]
        older_searches = [q for q in searches if validate_time(q['timestamp']) < recent_start_dt]

        # When evaluating Period 2, no history precedes recent_start (Period 1)
        if not older_history and not older_searches:
            return facet_profiles(history, searches, facets, cutoff, half_life_days=default_hl)

        older_profiles = facet_profiles(older_history, older_searches, facets, recent_start_str)
        recent_profiles = facet_profiles(
            history, searches, facets, cutoff, recent_start=recent_start_str
        )

        all_users = set(older_profiles.keys()) | set(recent_profiles.keys())
        user_half_lives: Dict[str, float] = {}
        for uid in all_users:
            sim = profile_similarity(recent_profiles.get(uid), older_profiles.get(uid))
            if sim is None:
                user_half_lives[uid] = default_hl
            else:
                # Non-linear scaling sharpens responsiveness when similarity drops
                stability = sim * sim
                user_half_lives[uid] = min_hl + stability * (max_hl - min_hl)

        def weight_fn(user_id: str, event_dt: Any, cutoff_dt: Any) -> float:
            hl = user_half_lives.get(user_id, default_hl)
            age_days = (cutoff_dt - event_dt).total_seconds() / 86400.0
            return 2.0 ** (-age_days / hl)

        return build_custom_weighted_profiles(history, searches, facets, cutoff, weight_fn)
