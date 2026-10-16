"""Power-law (hyperbolic) temporal decay profile model."""
from typing import Any, Dict, List

from exp_e.base import BaseTemporalModel, build_custom_weighted_profiles
from exp_e.registry import register_temporal_model


@register_temporal_model('decay__power_law__beta0.6', tau_days=14.0, beta=0.6)
class PowerLawDecayModel(BaseTemporalModel):
    """Hyperbolic / power-law forgetting curve: w_t = (1 + age_days / tau_days) ^ (-beta).

    Preserves a heavier long-term memory tail than exponential decay while still
    prioritizing recent interactions.
    """

    def build_profiles(
        self,
        history: List[Dict[str, Any]],
        searches: List[Dict[str, Any]],
        facets: Dict[str, Dict[str, set]],
        cutoff: str,
        options: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        tau_days = float(self.config.get('tau_days', 14.0))
        beta = float(self.config.get('beta', 0.6))

        def weight_fn(user_id: str, event_dt: Any, cutoff_dt: Any) -> float:
            age_days = max(0.0, (cutoff_dt - event_dt).total_seconds() / 86400.0)
            return (1.0 + age_days / tau_days) ** (-beta)

        return build_custom_weighted_profiles(history, searches, facets, cutoff, weight_fn)
