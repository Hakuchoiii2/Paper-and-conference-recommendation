"""Change-point shift-gate model for detecting preference drift across periods."""
from typing import Any, Dict, List

from baseline_common import facet_profiles
from exp_e.base import (
    BaseTemporalModel,
    build_custom_weighted_profiles,
    profile_similarity,
)
from exp_e.registry import register_temporal_model
from validate_all import validate_time


@register_temporal_model(
    'drift__shift_gate__cos0.55',
    similarity_threshold=0.55,
    drift_discount=0.15,
    stable_discount=0.90,
)
class ChangePointShiftGateModel(BaseTemporalModel):
    """Detects preference shift between older history and the recent period.

    - If similarity(recent, older) < threshold: triggers a drift gate that strongly
      discounts pre-recent history (`drift_discount` = 0.15).
    - Otherwise: retains older history with high weight (`stable_discount` = 0.90).
    """

    def build_profiles(
        self,
        history: List[Dict[str, Any]],
        searches: List[Dict[str, Any]],
        facets: Dict[str, Dict[str, set]],
        cutoff: str,
        options: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        threshold = float(self.config.get('similarity_threshold', 0.55))
        drift_discount = float(self.config.get('drift_discount', 0.15))
        stable_discount = float(self.config.get('stable_discount', 0.90))

        recent_start_str = options.get('recent_start')
        if not recent_start_str:
            return facet_profiles(history, searches, facets, cutoff)

        recent_start_dt = validate_time(recent_start_str)
        older_history = [e for e in history if validate_time(e['timestamp']) < recent_start_dt]
        older_searches = [q for q in searches if validate_time(q['timestamp']) < recent_start_dt]

        if not older_history and not older_searches:
            return facet_profiles(history, searches, facets, cutoff)

        older_profiles = facet_profiles(older_history, older_searches, facets, recent_start_str)
        recent_profiles = facet_profiles(
            history, searches, facets, cutoff, recent_start=recent_start_str
        )

        all_users = set(older_profiles.keys()) | set(recent_profiles.keys())
        past_multipliers: Dict[str, float] = {}
        for uid in all_users:
            sim = profile_similarity(recent_profiles.get(uid), older_profiles.get(uid))
            if sim is not None and sim < threshold:
                past_multipliers[uid] = drift_discount
            else:
                past_multipliers[uid] = stable_discount

        def weight_fn(user_id: str, event_dt: Any, cutoff_dt: Any) -> float:
            if event_dt >= recent_start_dt:
                return 1.0
            return past_multipliers.get(user_id, stable_discount)

        return build_custom_weighted_profiles(history, searches, facets, cutoff, weight_fn)
