# `ML.METRICS`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mlmetrics`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlmetrics)

- **Description:** Model-free table-valued function that computes evaluation metrics from a relation that already contains an **actual** column and a **predicted** column. There is no model argument — nothing is trained and nothing is loaded, so the predictions may come from BigQuery ML, Vertex AI batch prediction, a third-party scoring API, or a file someone loaded last quarter. **Preview.**
- **Use cases:**
  - Scoring predictions after the model that produced them has been deleted, deprecated, or moved out of reach.
  - Comparing a BQML model, an external model, and a naive baseline under one implementation of `r2_score` / `f1_score`, so the numbers are actually comparable.
  - Recomputing a metric on demand for a model card, a release gate, or an audit — the computation is reproducible where `AI.EVALUATE` is not.
  - Backfilling metrics over an archive of predictions and actuals.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-metrics
- **Type:** Table-valued function. Returns exactly one row.
- **Applies to models:** None — model-free utility (operates on saved predictions, not a model).

**Syntax:**
```sql
ML.METRICS(
  { TABLE `project.dataset.table` | (QUERY_STATEMENT) },
  predicted_col => 'predicted_column_name',
  actual_col    => 'actual_column_name',
  task_type     => 'regression' | 'classification'
)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| relation | `TABLE` reference or `(QUERY_STATEMENT)` | Yes | — | The rows to score. See the `80038528` limitation below before choosing the query form. |
| `predicted_col` | `STRING` | Yes | — | Name of the column holding predictions. |
| `actual_col` | `STRING` | Yes | — | Name of the column holding ground truth. Must share a type with `predicted_col`. |
| `task_type` | `STRING` | Yes | — | `'regression'` or `'classification'`. Determines which metric set is returned. |

**Outputs (`task_type => 'regression'`):**

| Column | Type | Description |
|--------|------|-------------|
| `mean_absolute_error` | `FLOAT64` | Mean of `ABS(actual - predicted)`. |
| `mean_squared_error` | `FLOAT64` | Mean of `(actual - predicted)^2`. |
| `mean_squared_log_error` | `FLOAT64` | Mean squared error of `LOG(1 + x)` values. |
| `median_absolute_error` | `FLOAT64` | Median of `ABS(actual - predicted)`. |
| `r2_score` | `FLOAT64` | Coefficient of determination. Negative when the predictions are worse than predicting the mean. |
| `explained_variance` | `FLOAT64` | Fraction of variance explained; differs from `r2_score` when the errors are biased. |

**Outputs (`task_type => 'classification'`):**

| Column | Type | Description |
|--------|------|-------------|
| `precision` | `FLOAT64` | See the BOOL/STRING note below — the definition depends on the column type. |
| `recall` | `FLOAT64` | Same. |
| `accuracy` | `FLOAT64` | Fraction of correct predictions. Type-independent. |
| `f1_score` | `FLOAT64` | Same type dependence as `precision`/`recall`. |

**Best practices:**
- **Materialize predictions you intend to score.** Once written down, a prediction table outlives the model, the endpoint, and the vendor contract — and `ML.METRICS` is what makes that table useful.
- **Prefer the `TABLE` form.** It succeeded on every relation tested; the `(QUERY_STATEMENT)` form did not (below).
- Choose the label column type deliberately rather than inheriting it from an upstream `CAST` — the type changes the metric definitions.
- Use it as the single scorer when comparing models from different systems, so "our MAE" and "their MAE" mean the same thing.

**Limitations:**
- **Preview.**
- `predicted_col` and `actual_col` must share a type. Rows where either is `NULL` are dropped before anything is computed.
- No `log_loss`, no `roc_auc`, and no confusion matrix — `ML.EVALUATE` on a trained classification model returns the first two. Probability-threshold tuning is not possible from these four numbers.
- **The column type silently redefines `precision`, `recall` and `f1_score`.** A `BOOL` pair is scored as **binary** — the positive (`TRUE`) class alone. The `STRING` rendering of the identical values is scored as **multiclass and macro-averaged**, even with exactly two classes. Measured on one 62-row table (12 positives; TP 11, FP 10, FN 1, TN 40): precision `0.5238095238095238` as `BOOL` versus `0.7497096399535423` as `STRING`, `f1_score` `0.6666666666666666` versus `0.7728937728937728`; `accuracy` was `0.8225806451612904` either way. On balanced data the two agree, which is how this stays hidden until the classes are lopsided. Note also that macro `f1_score` is the mean of the per-class F1s, not the F1 of the macro precision and recall. **This is a BigQuery-wide convention, not an `ML.METRICS` quirk** — [`AI.EVALUATE`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md)'s TabFM branch was measured to follow the identical rule.
- **Internal error `80038528` on the `(QUERY_STATEMENT)` form.** Some relations fail with a generic "An internal error occurred... usually caused by a transient issue" and `Error: 80038528`. It is not transient — the same statement fails identically on every run. The `TABLE` form of the very same data succeeded in every case tested (7 of 7), including every relation whose query form failed. No rule for *when* the query form breaks emerged; ruled out by direct test: cross-project references (a public table works in query form; a copy of the failing table inside the caller's own project still fails), `JOIN`s (a join across two of the caller's own tables works), `NULL`s in either column, `REQUIRED` schema modes, row count (62 works, 150 fails, 32,561 works), and the presence of `WHERE` / `LIMIT` / computed expressions. Observed failing: `ml_datasets.penguins`, `ml_datasets.iris`, a copy of `penguins` in the caller's project. Observed working: `ml_datasets.census_adult_income`, `usa_names.usa_1910_2013`, a 62-row prediction table, and `penguins` wrapped in a `GROUP BY`. No mechanism is claimed. **Workaround: materialize and pass `TABLE`.**
- **The client libraries retry that error.** `internalError` is on `google-cloud-bigquery`'s default retryable list, so `client.query(sql).result()` resubmits the job until its 600-second deadline — **12 job attempts over 604 seconds, measured** — before raising. Pass `retry=None` to `client.query()` and `retry=None, job_retry=None` to `.result()` to fail fast.

**Related — three ways to get evaluation metrics:**

| You have | Function | Notes |
|---|---|---|
| A trained model plus an eval set | [`ML.EVALUATE`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlevaluate) | Returns `log_loss` and `roc_auc` too; requires the model object to exist |
| Two columns, actual and predicted | `ML.METRICS` | No model. Measured against `ML.EVALUATE` on the same predictions, every regression metric agrees to at least 13 significant digits (relative gaps ~1e-16, floating-point summation order); which ones land bit-identical varies between runs |
| Raw data and no model at all | [`AI.EVALUATE`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md) | Trains TabFM/TimesFM internally; same metric names, but not reproducible run to run |

**BigFrames API:** No wrapper for `ML.METRICS`. `bigframes.ml.metrics` (`r2_score`, `accuracy_score`, `roc_auc_score`, …) computes metrics client-side over BigFrames Series — a different thing, useful when the predictions are already in a DataFrame. Reach the SQL function via `bigframes.pandas.read_gbq`.

**Repo example (tested):** `bigquery-ml/functions/evaluation/evaluation.ipynb` and `evaluation.sql` — trains a `LINEAR_REG` on `penguins`, saves predictions, **drops the model**, and shows `ML.EVALUATE` failing with *Not found: Model* while `ML.METRICS` returns the same six metrics; scores a constant baseline the model can be compared against; measures the BOOL/STRING split on one table and reproduces both rows by hand from the confusion matrix; tests the same split in `AI.EVALUATE`; and reproduces `80038528` with the ruled-out mechanisms above. Two workflows in this project already score saved predictions the long way and now cross-link it: `workflows/hierarchical_forecasting/` Step 4 (TEST actuals joined to two reconciled forecasts) and `workflows/regression_based_forecasting/` (its custom metrics helper, used wherever `ML.EVALUATE` does not apply). Both keep their hand-written arithmetic, which is the useful part of the comparison — they report RMSE, MAPE and pMAE, and `ML.METRICS` returns none of the three.

---
