"""Compatibility entry point: the complete runner now includes Ordinal-Intent.

The previous cached-results runner is preserved in scripts/exp_d/backup/
20261021_complete_runner. New runs always start from the dataset.
"""
from run_benchmark import main


if __name__ == '__main__':
    main()
