"""Fixed exponential time-decay profile models."""
from typing import Any, Dict, List

from baseline_common import facet_profiles
from exp_e.base import BaseTemporalModel
from exp_e.registry import register_temporal_model


@register_temporal_model('decay')
@register_temporal_model('decay__exp__hl30')
@register_temporal_model('decay__exp__hl14', fixed_half_life=14.0)
@register_temporal_model('decay__exp__hl21', fixed_half_life=21.0)
@register_temporal_model('decay__exp__hl60', fixed_half_life=60.0)
class ExponentialDecayModel(BaseTemporalModel):
    """Exponential time-decay profile: w_t = 2 ^ (-age_days / half_life_days)."""

    def build_profiles(
        self,
        history: List[Dict[str, Any]],
        searches: List[Dict[str, Any]],
        facets: Dict[str, Dict[str, set]],
        cutoff: str,
        options: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        hl = self.config.get('fixed_half_life') or options.get('half_life_days', 30.0)
        return facet_profiles(
            history,
            searches,
            facets,
            cutoff,
            half_life_days=hl,
        )
