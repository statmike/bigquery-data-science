# `ML.TRAINING_INFO`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mltraining_info`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mltraining_info)

- **Description:** Returns per-iteration training statistics (the loss/convergence curve), one row per iteration per training run.
- **Use cases:**
  - Plot the training vs. eval loss curve to diagnose under/over-fitting.
  - Confirm convergence and inspect `learning_rate` evolution.
  - Track training cost via `duration_ms`.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-train
- **Type:** Table-valued.
- **Applies to models:** Iterative learners (LINEAR_REG, LOGISTIC_REG, KMEANS, MATRIX_FACTORIZATION, DNN_*, AUTOENCODER, BOOSTED_TREE_* / RANDOM_FOREST_* via XGBoost iterations) and time-series (ARIMA_PLUS, reduced output). **Not** supported on imported TensorFlow models.

**Syntax:**
```sql
SELECT iteration, loss, eval_loss, learning_rate, duration_ms
FROM ML.TRAINING_INFO(MODEL `PROJECT_ID.DATASET.MODEL_NAME`)
ORDER BY iteration;
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model ref | Yes | — | The trained model to introspect. |

**Outputs (standard models):**

| Column | Type | Description |
|--------|------|-------------|
| `training_run` | INT64 | Training-run index. Multiple runs occur with warm-start or HP tuning. |
| `iteration` | INT64 | Iteration number within the training run. |
| `loss` | FLOAT64 | Loss on the training data after this iteration (e.g. log loss for logistic reg). |
| `eval_loss` | FLOAT64 | Loss on the holdout data. NULL when `DATA_SPLIT_METHOD = 'NO_SPLIT'`. |
| `learning_rate` | FLOAT64 | Learning rate used this iteration. |
| `duration_ms` | INT64 | Iteration duration in milliseconds. |

**Model-specific output differences:**

| Model family | Difference |
|---|---|
| K-means | No `eval_loss`; adds `cluster_info` ARRAY\<STRUCT\> with `centroid_id`, `cluster_radius`, `cluster_size` (computed on standardized features). |
| Time-series (ARIMA_PLUS) | Returns only `training_run`, `iteration`, `duration_ms`; no per-iteration metrics, and not broken out per time series; `duration_ms` is total cost. |
| Boosted tree / random forest (XGBoost-based) | `iteration` numbering starts at **1**, not 0 (unlike GLM/DNN gradient descent) — verified in `models/boosted_tree_classifier/`. The first iteration's `duration_ms` includes a one-time data-loading/indexing overhead (observed ~14 min on one run), so it is not representative of steady-state per-iteration cost; later iterations run in milliseconds. |

**Best practices:**
- `ORDER BY iteration` and chart `loss` vs `eval_loss` — divergence signals overfitting.
- For linear/logistic models, `learning_rate` can *rise* across iterations when `LEARN_RATE_STRATEGY = 'LINE_SEARCH'` (the default) — expected, not a bug.

**GOTCHA (measured, undocumented) — `ML.TRAINING_INFO` returns zero rows on a `BOOSTED_TREE_*` model trained with `xgboost_version = '2.1'` once training runs more than 10 iterations.** Nothing else about the model is affected: `CREATE MODEL` succeeds, and `ML.EVALUATE`, `ML.PREDICT`, `ML.EXPLAIN_PREDICT`, `ML.FEATURE_IMPORTANCE` and `ML.GLOBAL_EXPLAIN` all return normally. Only the training history is empty. Isolated with single-variable probes on `census_adult_income` (3 features, 5,000 rows, `early_stop = FALSE`, everything else held constant):

| `xgboost_version` | `max_iterations` | rows returned |
|---|---|---|
| `0.9` (the default) | 20 | 20 |
| `1.1` | 20 | 20 |
| `2.1` | 5 | 5 |
| `2.1` | 10 | 10 |
| `2.1` | 11 | **0** |
| `2.1` | 20 | **0** |

The boundary is exactly 10 iterations. Ruled out as causes: early stopping (disabled in the probes above, and the default `early_stop = TRUE` behaves identically), `auto_class_weights`, and `enable_global_explain` — both of the latter return rows normally at `'2.1'` with `max_iterations = 5`. Reproduced on a realistic config too: the full 11-feature `census_adult_income` classifier at default `max_iterations` returns 9 rows at `'0.9'` and 0 rows at `'2.1'`.

**Practical consequence:** on a boosted tree you get either a modern `model.ubj` export or a readable loss curve, not both. `RANDOM_FOREST_*` is unaffected — training is single-pass (one iteration), so it never reaches the boundary. To recover the curve, omit `xgboost_version` (back to the `0.9` default) or hold training to 10 iterations or fewer.

**Limitations:**
- No imported-TensorFlow support.
- Limited usefulness for ARIMA_PLUS (use `ML.ARIMA_EVALUATE` / `ML.ARIMA_COEFFICIENTS` for forecast diagnostics instead).
- Returns nothing for `BOOSTED_TREE_*` at `xgboost_version = '2.1'` past 10 iterations — see the gotcha above.

**BigFrames API:** No direct equivalent.
**Repo example (tested):**
- `bigquery-ml/models/logistic_regression/logistic_regression.sql` (Example 8) — the loss curve.
- The `'2.1'` empty-result case is documented in place in `models/boosted_tree_classifier/` (Example 8 / Step 6) and `models/boosted_tree_regressor/` (Example 6 / Step 5).
- `bigquery-ml/models/arima_plus/arima_plus.sql` (Example 4) — the reduced ARIMA output, paired with `ML.FEATURE_INFO`.
- `bigquery-ml/models/automl_classifier/automl_classifier.sql` (Example 6, and the header note) — `duration_ms` is how the AutoML wall-clock overrun was measured: `duration_ms = 9,475,200`, i.e. 2.63 hours actual for `budget_hours = 1.0`. This is the `ML.TRAINING_INFO` use that has nothing to do with loss curves — reading the real cost of a training run after the fact.
- `bigquery-ml/workflows/difference_in_differences/difference_in_differences.sql` (header gotcha) — `ML.TRAINING_INFO` as the *detection* mechanism for a silently wrong fit: with the default `AUTO_STRATEGY` the loss is still decreasing at the final iteration and no error is raised, which is the signal to force `optimize_strategy = 'NORMAL_EQUATION'` for small-sample or collinear regressions used for inference.

---
