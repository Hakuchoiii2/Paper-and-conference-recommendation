"""Baseline temporal profile models: Static (full history) and Recent (single-period window)."""
from typing import Any, Dict, List

from baseline_common import facet_profiles
from exp_e.base import BaseTemporalModel
from exp_e.registry import register_temporal_model


@register_temporal_model('static')
@register_temporal_model('baseline__static__all')
class StaticProfileModel(BaseTemporalModel):
    """Accumulates all observable history before cutoff with uniform temporal weight (w_t = 1.0)."""

    def build_profiles(
        self,
        history: List[Dict[str, Any]],
        searches: List[Dict[str, Any]],
        facets: Dict[str, Dict[str, set]],
        cutoff: str,
        options: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        return facet_profiles(history, searches, facets, cutoff)


@register_temporal_model('recent')
@register_temporal_model('baseline__recent__prev_period')
class RecentProfileModel(BaseTemporalModel):
    """Retains only observable history from the immediately preceding period [recent_start, cutoff)."""

    def build_profiles(
        self,
        history: List[Dict[str, Any]],
        searches: List[Dict[str, Any]],
        facets: Dict[str, Dict[str, set]],
        cutoff: str,
        options: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        return facet_profiles(
            history,
            searches,
            facets,
            cutoff,
            recent_start=options['recent_start'],
        )
