"""Facet-wise Fast-Slow Gated profile model with continuous Sigmoid Delta Synchronization.

Inspired by ByteDance Monolith architecture:
- Disjoint temporal partition: Fast State [t - n, t) and Slow State [0, t - n).
- Slow State aggregates long-term cumulative history with slow exponential decay (T_{1/2} = 180 days).
- Fast State captures recent intent within a sliding window of n days.
- Delta Synchronization calculates facet-specific semantic divergence D_f = 1 - cos(F_f, S_f).
- Continuous Sigmoid Soft-Gating alpha_f = min_a + (max_a - min_a) * sigma(k * (D_f - tau)) adapts blending independently per facet.
"""
import datetime as dt
import math
from typing import Any, Dict, List, Optional

from baseline_common import FACETS, dot, facet_profiles, unit_vector
from exp_e.base import BaseTemporalModel
from exp_e.registry import register_temporal_model
from validate_all import validate_time


@register_temporal_model('hybrid__fast_slow_gated__w7', fast_window_days=7.0)
@register_temporal_model('hybrid__fast_slow_gated__w14', fast_window_days=14.0)
@register_temporal_model('hybrid__fast_slow_gated__w21', fast_window_days=21.0)
@register_temporal_model('hybrid__fast_slow_gated__w30', fast_window_days=30.0)
@register_temporal_model('hybrid__fast_slow_gated__w45', fast_window_days=45.0)
@register_temporal_model('hybrid__fast_slow_gated__w60', fast_window_days=60.0)
@register_temporal_model('fast_slow_gated', fast_window_days=30.0)
class FastSlowFacetGatedModel(BaseTemporalModel):
    """Monolith-inspired Dual-Speed Facet-Gated Temporal Adaptation Model."""

    def build_profiles(
        self,
        history: List[Dict[str, Any]],
        searches: List[Dict[str, Any]],
        facets: Dict[str, Dict[str, set]],
        cutoff: str,
        options: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        fast_window_days = float(self.config.get('fast_window_days', 30.0))
        slow_half_life = float(self.config.get('slow_half_life_days', 180.0))
        gate_k = float(self.config.get('gate_steepness', 10.0))
        gate_tau = float(self.config.get('gate_threshold', 0.50))
        min_alpha = float(self.config.get('min_alpha', 0.15))
        max_alpha = float(self.config.get('max_alpha', 0.85))

        cutoff_dt = validate_time(cutoff)
        fast_start_dt = cutoff_dt - dt.timedelta(days=fast_window_days)
        fast_start_str = fast_start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

        # 1. Disjoint partition of history and search logs
        slow_history = [e for e in history if validate_time(e['timestamp']) < fast_start_dt]
        slow_searches = [q for q in searches if validate_time(q['timestamp']) < fast_start_dt]

        fast_history = [e for e in history if validate_time(e['timestamp']) >= fast_start_dt]
        fast_searches = [q for q in searches if validate_time(q['timestamp']) >= fast_start_dt]

        # 2. Build Fast State [t - n, t)
        if not fast_history and not fast_searches:
            # Fallback if no activity in fast window: use all observable history
            return facet_profiles(history, searches, facets, cutoff, half_life_days=slow_half_life)

        fast_profiles = facet_profiles(
            history, searches, facets, cutoff, recent_start=fast_start_str
        )

        # 3. Build Slow State [0, t - n) with long-term decay
        if not slow_history and not slow_searches:
            # Fallback if early period (no history prior to fast window)
            return fast_profiles

        slow_profiles = facet_profiles(
            slow_history, slow_searches, facets, fast_start_str, half_life_days=slow_half_life
        )

        # 4. Facet-wise Delta Synchronization and Soft-Gated Blending
        all_users = set(fast_profiles.keys()) | set(slow_profiles.keys())
        blended_profiles = {}

        for uid in all_users:
            pf = fast_profiles.get(uid)
            ps = slow_profiles.get(uid)

            if not pf and not ps:
                continue
            if not ps:
                blended_profiles[uid] = pf
                continue
            if not pf:
                blended_profiles[uid] = ps
                continue

            vectors = {}
            raw_importance = {}

            for f in FACETS:
                vec_f = pf['vectors'].get(f, {})
                vec_s = ps['vectors'].get(f, {})

                if vec_f and vec_s:
                    cos_val = dot(vec_f, vec_s)
                    sim_01 = max(0.0, min(1.0, 0.5 * (cos_val + 1.0)))
                    div_f = 1.0 - sim_01
                    # Continuous Sigmoid Soft-Gating
                    sig_arg = max(-30.0, min(30.0, gate_k * (div_f - gate_tau)))
                    sig_val = 1.0 / (1.0 + math.exp(-sig_arg))
                    alpha_f = min_alpha + (max_alpha - min_alpha) * sig_val
                elif vec_f:
                    alpha_f = max_alpha
                elif vec_s:
                    alpha_f = min_alpha
                else:
                    alpha_f = 0.5

                # Concept blending per facet
                all_concepts = set(vec_f.keys()) | set(vec_s.keys())
                combined_vec = {
                    c: alpha_f * vec_f.get(c, 0.0) + (1.0 - alpha_f) * vec_s.get(c, 0.0)
                    for c in all_concepts
                }
                vectors[f] = unit_vector(combined_vec)

                imp_f = pf['facet_importance'].get(f, 0.2)
                imp_s = ps['facet_importance'].get(f, 0.2)
                raw_importance[f] = alpha_f * imp_f + (1.0 - alpha_f) * imp_s

            total_imp = sum(raw_importance.values())
            facet_importance = {
                f: raw_importance[f] / total_imp if total_imp > 0 else 1.0 / len(FACETS)
                for f in FACETS
            }
            blended_profiles[uid] = dict(vectors=vectors, facet_importance=facet_importance)

        return blended_profiles
