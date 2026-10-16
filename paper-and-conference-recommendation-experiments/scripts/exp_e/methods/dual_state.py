"""Dual-state hybrid profile combining short-term (recent) and long-term (static) representations."""
from typing import Any, Dict, List

from baseline_common import facet_profiles
from exp_e.base import BaseTemporalModel, blend_profiles
from exp_e.registry import register_temporal_model


@register_temporal_model('hybrid__dual_state__alpha0.35', alpha=0.35)
@register_temporal_model('hybrid__dual_state__alpha0.50', alpha=0.50)
@register_temporal_model('hybrid__dual_state__alpha0.65', alpha=0.65)
@register_temporal_model('hybrid__dual_state__alpha0.80', alpha=0.80)
class DualStateHybridModel(BaseTemporalModel):
    """Maintains separate normalized short-term and long-term profiles and blends them with `alpha`.

    Profile(u) = alpha * ShortProfile(u) + (1 - alpha) * LongProfile(u).
    """

    def build_profiles(
        self,
        history: List[Dict[str, Any]],
        searches: List[Dict[str, Any]],
        facets: Dict[str, Dict[str, set]],
        cutoff: str,
        options: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        alpha = float(self.config.get('alpha', 0.65))
        long_profiles = facet_profiles(history, searches, facets, cutoff)
        recent_start = options.get('recent_start')
        if not recent_start:
            return long_profiles

        short_profiles = facet_profiles(
            history, searches, facets, cutoff, recent_start=recent_start
        )
        all_users = set(long_profiles.keys()) | set(short_profiles.keys())
        blended = {}
        for uid in all_users:
            merged = blend_profiles(short_profiles.get(uid), long_profiles.get(uid), alpha=alpha)
            if merged:
                blended[uid] = merged
        return blended
