# Data Pipeline Runbook

## Environment setup

### Conda (preferred)

```powershell
conda env create -f environment/env.yaml
conda activate f1_project
```

### Pip

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## End-to-end run

```powershell
python src/run_data_pipeline.py --year 2024 --grand-prix monaco --session-name race
```

This runs:
1. raw collection to `data/raw/<session_id>/`
2. cleaned interim exports to `data/interim/<session_id>/`
3. processed estimator contract files to `data/processed/<session_id>/`

## Useful run modes

Collect only:

```powershell
python src/run_data_pipeline.py --year 2024 --grand-prix monaco --session-name race --collect-raw --no-build-processed
```

Preprocess only (uses existing raw files):

```powershell
python src/run_data_pipeline.py --year 2024 --grand-prix monaco --session-name race --no-collect-raw --build-processed
```

## Output checks

After a successful run, check:

1. `data/raw/<session_id>/manifest.json`
2. `data/raw/<session_id>/collection_report.json`
3. `data/processed/<session_id>/quality_report.json`

`quality_report.json` includes dataset coverage percentages and a single `ready_for_estimation` flag.
