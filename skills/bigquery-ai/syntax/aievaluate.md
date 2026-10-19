# `AI.EVALUATE`

> **Source:** [`bigquery-ai/reference/predictive-ai.md#aievaluate`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/predictive-ai.md#aievaluate)

- **Description:** Dual-purpose table-valued function. Given history and actuals it evaluates a **TimesFM forecast** (MAE, MSE, RMSE, MAPE, sMAPE, MASE). Given training and prediction inputs plus a `label_col` it evaluates a **TabFM prediction** (regression or classification metrics). Which branch runs is selected entirely by which arguments you pass.
- **Use cases:** Evaluating forecast accuracy, benchmarking model configurations, comparing forecast quality across multiple time series, scoring AI.PREDICT output against a held-out set.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-evaluate)
- **Type:** Table-valued function -- GA (the TabFM branch is Preview)

**Branch selection:**

| You pass | Branch | Model |
|---|---|---|
| `data_col` + `timestamp_col` | Forecast evaluation | TimesFM |
| `label_col` | Prediction evaluation | TabFM |

**Syntax (TimesFM -- forecast evaluation):**
```sql
SELECT *
FROM AI.EVALUATE(
  { TABLE HISTORY_TABLE | (HISTORY_QUERY_STATEMENT) },
  { TABLE ACTUAL_TABLE | (ACTUAL_QUERY_STATEMENT) },
  data_col => 'DATA_COL',
  timestamp_col => 'TIMESTAMP_COL'
  [, model => 'MODEL']
  [, id_cols => ID_COLS]
  [, horizon => HORIZON]
  [, context_window => CONTEXT_WINDOW]
)
```

**Syntax (TabFM -- prediction evaluation, Preview):**
```sql
SELECT *
FROM AI.EVALUATE(
  { TABLE TRAINING_TABLE | (TRAINING_QUERY) },
  { TABLE PREDICTION_TABLE | (PREDICTION_QUERY) },
  label_col => 'LABEL_COL'
)
```

**Inputs -- TimesFM:**

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `HISTORY_TABLE` / `HISTORY_QUERY_STATEMENT` | Table/Query | Required | -- | -- | Historical time series data used to generate a forecast |
| `ACTUAL_TABLE` / `ACTUAL_QUERY_STATEMENT` | Table/Query | Required | -- | -- | Actual time series data to evaluate the forecast against |
| `data_col` | STRING | Required | -- | -- | Data column name. Must be INT64, NUMERIC, BIGNUMERIC, or FLOAT64. |
| `timestamp_col` | STRING | Required | -- | -- | Timestamp column name. Must be TIMESTAMP, DATE, or DATETIME. |
| `model` | STRING | Optional | `'TimesFM 2.5'` | -- | `'TimesFM 2.5'` or `'TimesFM 3.0'` (Preview). |
| `id_cols` | ARRAY\<STRING\> | Optional | -- | -- | ID columns identifying unique time series |
| `horizon` | INT64 | Optional | 1024 | [1, 10000] on 2.5; [1, 1024] on 3.0 | Number of forecasted time points to evaluate |
| `context_window` | INT64 | Optional | Auto-selected | See AI.FORECAST | Context window length for the TimesFM model. Same supported values as AI.FORECAST per model version. |

**Inputs -- TabFM:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `TRAINING_TABLE` / `TRAINING_QUERY` | Table/Query | Required | -- | Labeled training data. Every column other than the label is a feature. |
| `PREDICTION_TABLE` / `PREDICTION_QUERY` | Table/Query | Required | -- | Labeled evaluation data. Must contain all training feature columns. |
| `label_col` | STRING | **Required** | none | Label column name. **Unlike AI.PREDICT, this has no default** -- AI.PREDICT falls back to `'label'`, AI.EVALUATE does not. A `STRING`/`BOOL` label evaluates classification; a numeric label evaluates regression. |

The TabFM branch accepts no `model`, `horizon`, `id_cols`, `context_window`, `data_col`, or `timestamp_col`.

**Outputs -- TimesFM:**

| Column | Type | Description |
|--------|------|-------------|
| *id_cols* | (inherited) | Time series identifiers |
| `mean_absolute_error` | FLOAT64 | MAE for the time series |
| `mean_squared_error` | FLOAT64 | MSE for the time series |
| `root_mean_squared_error` | FLOAT64 | RMSE for the time series |
| `mean_absolute_percentage_error` | FLOAT64 | MAPE for the time series |
| `symmetric_mean_absolute_percentage_error` | FLOAT64 | sMAPE for the time series |
| `mean_absolute_scaled_error` | FLOAT64 | MASE for the time series |
| `ai_evaluate_status` | STRING | **`NULL` on success** -- not an empty string; error string if unsuccessful. A common value is `The time series data is too short.` |

> **Test this column with `IS NOT NULL`, not `<> ''`.** The three TimesFM status columns are *not* consistent with each other, verified live 2026-09-02: `ai_evaluate_status` and `ai_detect_anomalies_status` come back **`NULL`** on success (`IS NULL` is `true`, `LENGTH` is `NULL`), while `ai_forecast_status` comes back as a genuine **zero-length empty string** (`IS NULL` is `false`, `LENGTH` is `0`). So on AI.EVALUATE and AI.DETECT_ANOMALIES, `WHERE ai_evaluate_status = ''` matches nothing at all, and `WHERE ai_evaluate_status <> ''` silently drops **every successful row** -- three-valued logic makes the `NULL` comparison unknown, not true. Select failures with `IS NOT NULL` and successes with `IS NULL`. Only AI.FORECAST's column behaves the way the empty-string wording suggests.

**Outputs -- TabFM regression** (6 columns; no `ai_evaluate_status`, no id passthrough):

| Column | Type | Description |
|--------|------|-------------|
| `mean_absolute_error` | FLOAT64 | MAE for the data |
| `mean_squared_error` | FLOAT64 | MSE for the data |
| `mean_squared_log_error` | FLOAT64 | Mean squared logarithmic error |
| `median_absolute_error` | FLOAT64 | Median absolute error |
| `r2_score` | FLOAT64 | Coefficient of determination |
| `explained_variance` | FLOAT64 | Explained variance |

**Outputs -- TabFM classification** (4 columns):

| Column | Type | Description |
|--------|------|-------------|
| `precision` | FLOAT64 | Precision -- macro-averaged across classes for a `STRING` label, the positive (`TRUE`) class alone for a `BOOL` label |
| `recall` | FLOAT64 | Recall -- same rule as `precision` |
| `accuracy` | FLOAT64 | Accuracy of the prediction; identical under either label type |
| `f1_score` | FLOAT64 | F1 -- same rule as `precision`. When macro-averaged it is the mean of the per-class F1s, not the F1 of the macro precision and recall |

> **GOTCHA -- the label column's TYPE decides which convention you get, and it is not announced anywhere in the output.** A `BOOL` `label_col` is scored as **binary**: `precision`, `recall` and `f1_score` describe the positive (`TRUE`) class only. The `STRING` rendering of the identical values is scored as **multiclass and macro-averaged**, even with exactly two classes. `accuracy` is the same either way. Measured on one imbalanced problem (12 positives of 62 rows, TabFM confusion matrix TP 12 / FP 11 / FN 0 / TN 39): the `BOOL` label returned precision `0.5217391304347826` and recall `1.0`, the `STRING` label returned `0.7608695652173914` and `0.89` -- the two-class means. Four isolated runs of each agreed. On balanced data the two nearly coincide, which is how this hides until the classes are lopsided. **This is a BigQuery-wide convention, not an `AI.EVALUATE` behavior** -- `ML.METRICS` follows the identical rule, measured side by side in [`bigquery-ml/functions/evaluation/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/evaluation).

> Note what is **missing** relative to `ML.EVALUATE` on a trained classification model: TabFM's AI.EVALUATE returns no `log_loss` and no `roc_auc`, and no confusion matrix. If you need threshold-tuning or ranking metrics, this function will not give them to you.

**Supported models:** TimesFM 2.5 (default), TimesFM 3.0 (Preview) on the forecast branch -- univariate only; there is no `target_cols` argument. TabFM on the prediction branch, where the `model` argument is not accepted.

**Best practices:** For forecasting, split data into historical (for forecasting) and actual (for comparison) portions using date-based filtering, and use `id_cols` to evaluate across multiple time series. For prediction, pass AI.EVALUATE exactly the same training and holdout inputs you passed AI.PREDICT -- the pair is only meaningful if the split matches.

**Limitations:** **Not reproducible run to run on either branch, and pinning `model` does not fix it** -- a minority of runs (measured at 2 of 16, with `model` and `context_window` both pinned and the query cache off) return a materially different metric, a ~32% swing in `mean_absolute_error` in the measured case. The majority value is the correct one, verified by recomputing MAE from `AI.FORECAST` output. See the reproducibility note at the top of this section for the full measurement and the workaround. Minimum 3 data points required on the forecast branch. Default horizon is 1,024 (unlike AI.FORECAST which defaults to 10). TimesFM silently ignores data points beyond the max context (15,360 for 2.5, 2,048 for 3.0). On the TabFM branch, AI.PREDICT's documented caps -- **50 feature columns** and **10 classification categories** -- apply to the same model, though the AI.EVALUATE page has no Limitations section and does not restate them.

**Locations:** All supported BigQuery ML locations.

**Provisioned throughput:** Not specified. Billed at the evaluation, inspection, and prediction rate.

**BigFrames API:** No direct equivalent for either branch. Use `%%bigquery` magics or `session.read_gbq_query()` to execute AI.EVALUATE SQL from BigFrames. Note: `bigframes.ml.forecasting.ARIMAPlus.evaluate()` exists but uses ARIMA_PLUS, not TimesFM.
