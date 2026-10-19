# `ML.EVALUATE`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlevaluate`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlevaluate)

- **Description:** Computes evaluation metrics for a trained BigQuery ML model. Returns a single row of metrics whose columns depend on the model type. Called with no input data, it returns the metrics computed on the model's reserved evaluation split at training time; called with input data, it scores that new dataset.
- **Use cases:**
  - Read training-time metrics off the reserved eval split (no input data).
  - Score a held-out TEST/VALIDATE set or fresh data to check generalization / drift.
  - Compare metrics across splits, model versions, or hyperparameter trials.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-evaluate (evaluation overview: https://cloud.google.com/bigquery/docs/evaluate-overview)
- **Type:** Table-valued function.
- **Applies to models:** Supervised — `LINEAR_REG`, `LOGISTIC_REG`, `BOOSTED_TREE_*`, `RANDOM_FOREST_*`, `DNN_*`, `WIDE_AND_DEEP_*`, `AUTOML_*`. Unsupervised — `KMEANS`, `PCA`, `AUTOENCODER`, `MATRIX_FACTORIZATION`. Time series — `ARIMA_PLUS`, `ARIMA_PLUS_XREG` (with input data; no-input form is deprecated — use `ML.ARIMA_EVALUATE`).

**Syntax:**
```sql
ML.EVALUATE(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`
  [, { TABLE `PROJECT_ID.DATASET.TABLE` | (query_statement) }]
  [, STRUCT(threshold_value AS threshold [, trial_id AS trial_id])]
)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model ref | Yes | — | The trained model to evaluate. |
| `TABLE` / `query_statement` | table / subquery | No | training eval split | Evaluation data. Column names must match the model's features and label; with a `TRANSFORM` model only the raw `TRANSFORM` inputs are required. Omit to read training-time metrics. |
| `threshold` | FLOAT64 | No | 0.5 | Binary-classification cutoff between the two labels. Classification models only. |
| `trial_id` | INT64 | No | optimal trial | Selects a specific hyperparameter-tuning trial. Only valid when the model was trained with `NUM_TRIALS`. Not allowed for PCA models. |

**Outputs (metric columns vary by model type):**

| Model task | ML.EVALUATE metric columns |
|---|---|
| Regression (`LINEAR_REG`, tree/DNN regressors) | `mean_absolute_error`, `mean_squared_error`, `mean_squared_log_error`, `median_absolute_error`, `r2_score`, `explained_variance` |
| Classification (`LOGISTIC_REG`, tree/DNN classifiers) | `precision`, `recall`, `accuracy`, `f1_score`, `log_loss`, `roc_auc` (macro-averaged for multiclass) |
| K-means (`KMEANS`) | `davies_bouldin_index`, `mean_squared_distance` |
| Matrix factorization (`MATRIX_FACTORIZATION`) — explicit feedback | `mean_absolute_error`, `mean_squared_error`, `mean_squared_log_error`, `r2_score`, `explained_variance` (a regression metric set) |
| Matrix factorization (`MATRIX_FACTORIZATION`) — implicit feedback | `recall`, `mean_squared_error`, `normalized_discounted_cumulative_gain`, `average_rank` |
| PCA (`PCA`) | `total_explained_variance_ratio` |
| Autoencoder (`AUTOENCODER`) | `mean_absolute_error`, `mean_squared_error`, `mean_squared_log_error` |
| Time series (`ARIMA_PLUS`/`ARIMA_PLUS_XREG`, with input data + `perform_aggregation=TRUE`) | `mean_absolute_error`, `mean_squared_error`, `root_mean_squared_error`, `mean_absolute_percentage_error`, `symmetric_mean_absolute_percentage_error`, `mean_absolute_scaled_error` |

> A `trial_id` column is prepended to the output when the model was trained with hyperparameter tuning.

> **No model? Use [`ML.METRICS`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlmetrics).** It computes the regression and classification metric sets above from a table of actual and predicted columns, with no model argument — the case `ML.EVALUATE` structurally cannot cover, such as predictions from Vertex AI, a vendor API, or a model that has since been dropped. Measured on the same predictions, every regression metric agrees with `ML.EVALUATE`'s to at least 13 significant digits (relative gaps ~1e-16 — floating-point summation order, not a difference in definition). It does **not** return `log_loss` or `roc_auc`, and its `precision`/`recall`/`f1_score` are defined by the column type (`BOOL` binary, `STRING` macro-averaged) rather than by the model task.

**Best practices:**
- Run with no input data first to get the training eval-split metrics for free, then pass TEST/VALIDATE data to confirm generalization.
- Stack splits with `SELECT 'TEST' AS SPLIT, * FROM ML.EVALUATE(...) UNION ALL ...` to compare TRAIN/VALIDATE/TEST side by side (see repo example).
- Tune the `threshold` to your precision/recall trade-off rather than relying on 0.5; inspect the full curve with `ML.ROC_CURVE` (binary) first.
- **BigQuery ML has no native k-fold cross-validation** — `CREATE MODEL`'s `data_split_method` only supports single-split holdout (`AUTO_SPLIT`/`RANDOM`/`CUSTOM`/`SEQ`/`NO_SPLIT`). Hand-roll it: assign folds with a deterministic hash (`MOD(ABS(FARM_FINGERPRINT(TO_JSON_STRING(t))), K)` when there's no natural row-id column), train K models with `data_split_method='NO_SPLIT'` each excluding its own fold (submit concurrently — see `ML.PREDICT`'s "join needs a stable key" note below for a related gotcha when combining per-row results across models), then `ML.EVALUATE` each fold model against its own held-out fold and `UNION ALL` to see the real spread, not just one number.

**Limitations:**
- **GOTCHA, verified live — the query cache serves stale metrics after a retrain.** BigQuery's result cache keys on the **query text**, and `CREATE OR REPLACE MODEL` does not change the text of the `ML.EVALUATE` that follows it. Re-running a notebook therefore hands you the *previous* run's metrics for a model that has since been retrained on different data. Measured during the build of [`workflows/feature_store/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/feature_store): after a retrain that genuinely changed both arms of a comparison, each arm reported its prior `roc_auc` to four decimals — two plausible-looking numbers that were simply not from the models on disk. Nothing errors and nothing looks wrong. Defend against it wherever an evaluation follows a retrain: `bq query --nouse_cache`, or `QueryJobConfig(use_query_cache=False)` from the client library. Note this bites hardest in exactly the situation it is least visible — an iterative build loop, where the model changes on every pass and the evaluation query never does.
- `precision`/`recall` of 0 means the threshold yielded no true positives; `NaN` precision means no positive predictions at all.
- For `ARIMA_PLUS`, the no-input form is deprecated — use `ML.ARIMA_EVALUATE` for model-fitting diagnostics (`AIC`, `log_likelihood`, `variance`, `non_seasonal_p/d/q`, `seasonal_periods`, `has_holiday_effect`, ...).
- `trial_id` argument is not supported for PCA models.

**BigFrames API:** `model.score(X, y)` on any `bigframes.ml` estimator returns the same metrics as a DataFrame.

**Repo example (tested):**
- `bigquery-ml/models/logistic_regression/logistic_regression.sql` (Example 2) — minimal no-input `ML.EVALUATE`.
- `bigquery-ml/workflows/ensembling/ensembling.sql` — a three-way TRAIN/VALIDATE/TEST `split` column assigned by deterministic hash, then `ML.EVALUATE` on the held-out TEST split `UNION ALL`'d across three model types into one comparison table.
- `bigquery-ml/models/kmeans/kmeans.sql` (Example 2) — no-input `ML.EVALUATE` returning `davies_bouldin_index` and `mean_squared_distance`.
- `bigquery-ml/models/pca/pca.sql` (Example 2) and `bigquery-ml/models/autoencoder/autoencoder.sql` (Example 2) — no-input `ML.EVALUATE` for unsupervised reconstruction models (`total_explained_variance_ratio` for PCA; `mean_absolute_error`/`mean_squared_error`/`mean_squared_log_error` for the autoencoder). The autoencoder example doubles as the caution that these aggregates look entirely normal while a latent unit is dead — only `ML.PREDICT`'s `latent_col_*` values expose it.
- `bigquery-ml/models/arima_plus/arima_plus.sql` (Example 5) — `ML.EVALUATE` with input data plus `STRUCT(TRUE AS perform_aggregation)` for `ARIMA_PLUS` forecast-accuracy metrics; called without eval data it falls back to ARIMA-fit stats in the shape of `ML.ARIMA_EVALUATE`.
- `bigquery-ml/workflows/feature_store/feature_store.ipynb` — two `LOGISTIC_REG` arms differing *only* in how their features were built, evaluated against a shared `FARM_FINGERPRINT` hash split with `data_split_method='NO_SPLIT'` so the metric gap cannot be a split artifact. Also the source of the query-cache gotcha above, and a demonstration that the *bigger* `roc_auc` (0.9387 vs 0.5194) is the wrong one: cross-evaluating the leaky model against point-in-time features collapses it to 0.5299.
- `bigquery-ml/workflows/cross_validation/cross_validation.ipynb` — hand-rolled 5-fold cross-validation on `ulb_fraud_detection` (BQML has no native k-fold support): deterministic hash-based fold assignment, 5 `LOGISTIC_REG` models submitted concurrently, per-fold `ML.EVALUATE` `UNION ALL`'d to show real fold-to-fold variance (roc_auc 0.968-0.985), then compared against a same-model-type single holdout to check whether it's representative of the fold distribution.

---
