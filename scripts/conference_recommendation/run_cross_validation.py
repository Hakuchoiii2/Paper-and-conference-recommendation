"""Compatibility entry point: tune ALL methods on the same train folds."""
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from scripts.conference_recommendation.experiment_protocol import (
    main, WEIGHT_PRESETS, FLAT_5_FACET_PRESETS, get_stratified_folds,
)

if __name__ == "__main__":
    main(default_stage="tune")
