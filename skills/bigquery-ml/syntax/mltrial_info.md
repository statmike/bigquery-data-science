# `ML.TRIAL_INFO`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mltrial_info`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mltrial_info)

- **Description:** Returns one row per hyperparameter-tuning trial, with the hyperparameters tried, the objective metrics achieved, and which trial is optimal. Only meaningful for models trained with `NUM_TRIALS > 0`.
- **Use cases:**
  - Compare trials and see the search space the tuner explored.
  - Identify the optimal trial (`is_optimal`) used by default at serving time.
  - Debug `INFEASIBLE` trials (invalid hyperparameter combinations).
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-trial-info
- **Type:** Table-valued.
- **Applies to models:** Any model type that supports hyperparameter tuning **and** was created with `NUM_TRIALS` set (LINEAR_REG, LOGISTIC_REG, KMEANS, MATRIX_FACTORIZATION, BOOSTED_TREE_*, RANDOM_FOREST_*, DNN_*, AUTOENCODER, PCA, etc.).

**Syntax:**
```sql
SELECT
  trial_id,
  hyperparameters,
  hparam_tuning_evaluation_metrics,
  is_optimal
FROM ML.TRIAL_INFO(MODEL `PROJECT_ID.DATASET.MODEL_NAME`)
ORDER BY trial_id;
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model ref | Yes | — | A model trained with `NUM_TRIALS > 0`. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `trial_id` | INT64 | Trial ID in approximate execution order; starts at 1. |
| `hyperparameters` | STRUCT | The hyperparameter values used in this trial. |
| `hparam_tuning_evaluation_metrics` | STRUCT | Eval metrics matching the `hparam_tuning_objectives`; computed on eval data. |
| `training_loss` | FLOAT64 | Final training loss for the trial. |
| `eval_loss` | FLOAT64 | Final eval loss for the trial. |
| `status` | STRING | Trial state — e.g. `SUCCEEDED`, `INFEASIBLE` (invalid hyperparameter combo), `FAILED` (see gotcha below). |
| `error_message` | STRING | Error message if the trial did not succeed. |
| `is_optimal` | BOOL | TRUE for the best-objective trial; used by default at serving (override with `TRIAL_ID` arg). |

**Best practices:**
- Reach into the metric STRUCT to sort, e.g. `hparam_tuning_evaluation_metrics.roc_auc`.
- The optimal trial is used automatically by `ML.PREDICT`/`ML.EVALUATE` etc.; pass a `TRIAL_ID` to those functions to force a different trial.

**Limitations:**
- Returns nothing meaningful (errors) on models trained without `NUM_TRIALS`.
- **Corrected (was unverified speculation, now disproven by direct observation): `is_optimal = TRUE` is NOT guaranteed to mark exactly one row.** Verified on `models/random_forest_regressor/`: 2 of 6 trials (different `num_parallel_tree`/`max_tree_depth` combos) tied on `r2_score` and **both** showed `is_optimal = TRUE` simultaneously. Don't assume `WHERE is_optimal` returns a single row — `LIMIT 1` or an explicit tiebreak (e.g. smallest `trial_id`) if you need exactly one.
- **Verified**: a trial can transiently `FAILED` with `error_message = "An internal error happened during trial training."` — its objective metric column is `NULL` in `ML.TRIAL_INFO`, but this does **not** fail the overall `CREATE MODEL` job; BigQuery still selects `is_optimal` from among the successful trials (`models/boosted_tree_classifier/`, 1 of 6 trials failed this way; `models/random_forest_classifier/`, 2 of 6 failed under concurrent notebook execution — job completed normally both times). Check `status`/`error_message` before assuming a `NULL` metric means a bad hyperparameter combination.
- **Verified (DNN): the search order for a given model name is reproducible, not freshly randomized on each retrain — and this extends to DNN training generally, not just tuning.** Three full runs of `models/dnn_regressor/` (identical SQL, no seed) reproduced bit-for-bit identical `ML.TRIAL_INFO` sampled hyperparameters and `is_optimal` trial, plus bit-identical `ML.EVALUATE` results on the non-tuned baseline and fix models. A differently-named model with the same search-space config explored a different, worse region. Don't assume renaming/duplicating a `CREATE MODEL` with `NUM_TRIALS` will reproduce a known-good (or known-bad) search outcome from a differently-named model — see the `DNN_CLASSIFIER`/`DNN_REGRESSOR` entry for details.

**BigFrames API:** No direct equivalent.
**Repo example (tested):** `bigquery-ml/models/logistic_regression/logistic_regression.sql` (Example 10 — `NUM_TRIALS=10` + `HPARAM_RANGE`, then sorts trials by `hparam_tuning_evaluation_metrics.roc_auc` and `is_optimal`). `bigquery-ml/models/boosted_tree_classifier/boosted_tree_classifier.sql` (Example 10 — tunes `learn_rate`/`max_tree_depth`; observed a transient trial `FAILED`, see gotcha above). `bigquery-ml/models/random_forest_regressor/random_forest_regressor.sql` (Example 9 — observed the `is_optimal` tie, see limitation above). For the unsupervised types the tuning objective is the model's own quality metric rather than an accuracy metric: `bigquery-ml/models/kmeans/kmeans.sql` sorts trials by `hparam_tuning_evaluation_metrics.davies_bouldin_index ASC`, and `bigquery-ml/models/autoencoder/autoencoder.sql` by `hparam_tuning_evaluation_metrics.mean_squared_error ASC`. `models/pca/pca.sql` (Example 10) is the deliberate exception — PCA supports no tuning at all, so it uses `pca_explained_variance_ratio` to let BigQuery ML pick the component count instead.

> Related hyperparameter-tuning option reference (`NUM_TRIALS`, `HPARAM_RANGE`, `HPARAM_CANDIDATES`, `HPARAM_TUNING_OBJECTIVES`) lives with the per-model-type entries and the capability matrix.


---
