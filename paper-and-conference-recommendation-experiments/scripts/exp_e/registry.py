"""Model Registry and Presets for Experiment E."""
from typing import Any, Dict, List, Tuple, Type

from exp_e.base import BaseTemporalModel

_MODEL_REGISTRY: Dict[str, Tuple[Type[BaseTemporalModel], Dict[str, Any]]] = {}

MODEL_PRESETS: Dict[str, List[str]] = {
    # Canonical preset preserves 100% compatibility with global test suite & protocol
    'canonical': [
        'static',
        'recent',
        'decay',
    ],
    # Baselines with unified 3-part naming convention: <family>__<method>__<param>
    'baselines': [
        'baseline__static__all',
        'baseline__recent__prev_period',
        'decay__exp__hl30',
    ],
    # Novel temporal adaptation ideas
    'ideas': [
        'decay__adaptive__divergence',
        'drift__shift_gate__cos0.55',
        'hybrid__dual_state__alpha0.65',
        'decay__power_law__beta0.6',
        'hybrid__fast_slow_gated__w30',
    ],
    # Monolith-inspired Fast-Slow Gated preset
    'monolith': [
        'hybrid__fast_slow_gated__w14',
        'hybrid__fast_slow_gated__w30',
        'hybrid__fast_slow_gated__w45',
        'hybrid__fast_slow_gated__w60',
    ],
    # Comprehensive benchmark comparing baselines and all new ideas together
    'all': [
        'baseline__static__all',
        'baseline__recent__prev_period',
        'decay__exp__hl30',
        'decay__adaptive__divergence',
        'drift__shift_gate__cos0.55',
        'hybrid__dual_state__alpha0.65',
        'decay__power_law__beta0.6',
        'hybrid__fast_slow_gated__w30',
    ],
}


def register_temporal_model(key: str, **default_kwargs: Any):
    """Decorator to register a temporal model class under `key` with optional default parameters."""
    def decorator(cls: Type[BaseTemporalModel]) -> Type[BaseTemporalModel]:
        if key in _MODEL_REGISTRY:
            raise KeyError(f"Temporal model key '{key}' is already registered.")
        _MODEL_REGISTRY[key] = (cls, default_kwargs)
        return cls
    return decorator


def get_temporal_model(key: str, **override_kwargs: Any) -> BaseTemporalModel:
    """Instantiate a registered temporal model by its `key`."""
    if key not in _MODEL_REGISTRY:
        available = ', '.join(sorted(_MODEL_REGISTRY.keys()))
        raise KeyError(f"Unknown temporal model '{key}'. Available models: [{available}]")
    cls, default_kwargs = _MODEL_REGISTRY[key]
    merged_kwargs = {**default_kwargs, **override_kwargs}
    return cls(name=key, **merged_kwargs)


def resolve_model_keys(
    preset: str = 'canonical',
    models: List[str] = None,
) -> List[str]:
    """Resolve list of model keys from an explicit list or a named preset."""
    if models:
        for m in models:
            if m not in _MODEL_REGISTRY:
                available = ', '.join(sorted(_MODEL_REGISTRY.keys()))
                raise KeyError(f"Unknown model '{m}'. Available: [{available}]")
        return list(models)
    if preset not in MODEL_PRESETS:
        available = ', '.join(sorted(MODEL_PRESETS.keys()))
        raise KeyError(f"Unknown preset '{preset}'. Available presets: [{available}]")
    return list(MODEL_PRESETS[preset])


def list_registered_models() -> List[str]:
    """Return all registered model identifiers in sorted order."""
    return sorted(_MODEL_REGISTRY.keys())
