# ml-experiments

Offline model experiments for the disruption-advisor delay-risk model.
Each experiment lives in its own numbered folder matching the task ID.

| Folder | Date       | What                                                              | Winner            | AUC-60 |
|--------|------------|-------------------------------------------------------------------|-------------------|--------|
| T-511  | 2026-11-21 | Baseline comparison of 7 models + Optuna tuning; 3 new features  | LightGBM (Optuna) | 0.7887 |

## How to re-run an experiment

```bash
cd <repo-root>
python3 -I products/disruption-advisor/ml-experiments/<folder>/experiment.py
```

Requires: `lightgbm`, `xgboost`, `scikit-learn`, `optuna`, `duckdb`, `pyarrow`, `numpy`
(all present in the backend venv; optuna: `pip install optuna`)

Data path is hard-coded to `input/data/disruption-uc5/parquet/ops/` relative to the repo root.
Results are written to `execution/logs/output/` and to the experiment folder's `results.json`.
