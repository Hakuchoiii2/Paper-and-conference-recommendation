"""Auto-register all temporal profile methods for Experiment E."""
from exp_e.methods import (
    baselines,
    change_point,
    decay_adaptive,
    decay_fixed,
    decay_power_law,
    dual_state,
    fast_slow_gated,
)

__all__ = [
    'baselines',
    'change_point',
    'decay_adaptive',
    'decay_fixed',
    'decay_power_law',
    'dual_state',
    'fast_slow_gated',
]
