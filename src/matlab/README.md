# MATLAB Filter Pipeline

This folder contains a modular MATLAB scaffold for estimator comparison on processed race sessions.

## Implemented filters

1. Batch LUMVE (windowed weighted least squares)
2. EKF
3. UKF

## Folder structure

- `run_monaco_filter_comparison.m`: one-command Monaco run
- `matlab_config_default.m`: central config
- `io/`: data loading and session series building
- `model/`: mode logic and dynamics
- `filters/`: filter implementations and shared math
- `eval/`: metrics and exports

## Quick start

1. Open MATLAB.
2. Set working directory to project root.
3. Run:

```matlab
run("src/matlab/run_monaco_filter_comparison.m")
```

To run every requested 2024 race that has completed processed data, run:

```matlab
run("src/matlab/run_all_race_filter_comparisons.m")
```

Outputs are written to:

- `results/matlab/<session_id>/summary_metrics.csv`
- `results/matlab/<session_id>/rejoin_case_metrics.csv`
- `results/matlab/<session_id>/filter_outputs.mat` (if enabled in config)

The all-races runner also writes:

- `results/matlab/batch_2024_races/combined_summary_metrics.csv`
- `results/matlab/batch_2024_races/run_log.csv`

## Evaluation metric style

The only external model prediction is `predicted_rejoin_position`.
The filters still estimate and propagate `[s, v, a]` internally for the grid, but those states are not treated as the prediction target.

Rejoin comparison is classification-first:

- `accuracy`: exact rejoin-position match (true/false)
- `within_one_accuracy`: within +/- 1 position
- `true_count` and `false_count`
- `prediction_coverage`

For each case, the pitting car rejoin state is not estimated as `[s,v,a]`.
Instead, the rest of the grid is propagated from decision time to rejoin time,
using phase-binned mean input profiles estimated causally from history so far.
