# Numerical scalers: `ML.STANDARD_SCALER`, `ML.MIN_MAX_SCALER`, `ML.MAX_ABS_SCALER`, `ML.ROBUST_SCALER`, `ML.NORMALIZER`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#numerical-scalers-mlstandard_scaler-mlmin_max_scaler-mlmax_abs_scaler-mlrobust_scaler-mlnormalizer`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#numerical-scalers-mlstandard_scaler-mlmin_max_scaler-mlmax_abs_scaler-mlrobust_scaler-mlnormalizer)

- **Description:** Manual feature-preprocessing functions that rescale numerical inputs into ML-ready features. The first four are **analytic** functions that compute column statistics across all rows and therefore require an empty `OVER()` clause; `ML.NORMALIZER` is a row-wise **scalar** function that normalizes each numerical ARRAY independently (no `OVER()`). All five can be used standalone in SQL or inside the `TRANSFORM` clause of `CREATE MODEL`, where the learned statistics are stored with the model and re-applied automatically at `ML.PREDICT` (no training/serving skew).
- **Use cases:**
  - Put numerical features on a common scale for distance/gradient-based models (`KMEANS`, `LINEAR_REG`/`LOGISTIC_REG`, `DNN_*`, `PCA`).
  - `ML.ROBUST_SCALER` for columns with outliers (centers on median, scales by IQR).
  - `ML.MAX_ABS_SCALER` to preserve sparsity / sign (no centering).
  - `ML.NORMALIZER` to give each row's feature vector unit norm (e.g. text/embedding-like vectors).
- **documentation:** [Manual feature preprocessing](https://cloud.google.com/bigquery/docs/manual-preprocessing) · [STANDARD_SCALER](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-standard-scaler) · [MIN_MAX_SCALER](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-min-max-scaler) · [MAX_ABS_SCALER](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-max-abs-scaler) · [ROBUST_SCALER](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-robust-scaler) · [NORMALIZER](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-normalizer)
- **Type:** Analytic (STANDARD / MIN_MAX / MAX_ABS / ROBUST) · Scalar (NORMALIZER).
- **Status:** GA.
- **Applies to models:** Any model type that supports manual preprocessing; used as raw SQL or in a `TRANSFORM` clause. Exportable with the model's transform when used in `TRANSFORM` (the scaler transforms accompany exported models / Vertex AI Model Registry).

**Transformation reference:**

| Function | Output range | Formula (per value `x`) | Centers data? | Notes |
|----------|--------------|--------------------------|---------------|-------|
| `ML.STANDARD_SCALER` | unbounded (~mean 0, std 1) | `(x - AVG(x)) / STDDEV_POP(x)` (z-score) | Yes (mean) | Stores AVG/STDDEV for `ML.PREDICT`. **Verified live: uses population stddev (`STDDEV_POP`, ÷N), NOT the sample stddev (`STDDEV`/`STDDEV_SAMP`, ÷N-1) BigQuery's plain `STDDEV()` computes by default** — a manual "sanity check" using `STDDEV(x)` will NOT match. |
| `ML.MIN_MAX_SCALER` | `[0, 1]` | `(x - MIN) / (MAX - MIN)` | No | Caps prediction inputs to 0 or 1 when outside the training range. |
| `ML.MAX_ABS_SCALER` | `[-1, 1]` | `x / MAX(ABS(x))` | No | Preserves sign and sparsity; no shift. |
| `ML.ROBUST_SCALER` | unbounded | `(x - median) / (q_hi - q_lo)` | Optional (median) | Outlier-robust; quantile range default `[25, 75]`. |
| `ML.NORMALIZER` | unit-norm vector | `x_i / \|\|vector\|\|_p` | No | Row-wise on an ARRAY; default p=2. |

**Syntax:**
```sql
-- Analytic scalers (require empty OVER())
ML.STANDARD_SCALER(numerical_expression) OVER()
ML.MIN_MAX_SCALER(numerical_expression)  OVER()
ML.MAX_ABS_SCALER(numerical_expression)  OVER()
ML.ROBUST_SCALER(numerical_expression [, quantile_range] [, with_median] [, with_quantile_range]) OVER()

-- Scalar normalizer (no OVER(); operates on an ARRAY per row)
ML.NORMALIZER(array_expression [, p])
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `numerical_expression` | numeric | Yes | — | The numeric column/expression to scale (scaler functions). |
| `quantile_range` | ARRAY\<INT64\> (2 elems) | No | `[25, 75]` | ROBUST only. Lower/upper percentile boundaries; min 0, max 100; 2nd \> 1st. |
| `with_median` | BOOL | No | `TRUE` | ROBUST only. Subtract the median before scaling. |
| `with_quantile_range` | BOOL | No | `TRUE` | ROBUST only. Divide by the quantile range. |
| `array_expression` | ARRAY\<numeric\> | Yes | — | NORMALIZER only. The numeric vector to give unit norm. |
| `p` | FLOAT64 | No | `2` | NORMALIZER only. p-norm; accepts `0`, `>= 1`, or `+inf` via `CAST('+inf' AS FLOAT64)`. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (scaler result) | FLOAT64 | Scaled value of `numerical_expression`. |
| (normalizer result) | ARRAY\<FLOAT64\> | Input array rescaled to unit p-norm. |

**Best practices:**
- Prefer the `TRANSFORM` clause over preprocessing in the source query so the learned statistics travel with the model and are reapplied at prediction (avoids training/serving skew). Scale each column inside one `TRANSFORM` and alias each result (`ML.STANDARD_SCALER(col) OVER() AS col_scaled`) — see `functions/scalers/scalers.sql` (Example 8).
- Choose the scaler to match the data: `ROBUST` for outliers, `MAX_ABS` for sparse/sign-bearing data, `STANDARD` for roughly Gaussian features, `MIN_MAX` when a bounded `[0,1]` range is needed.
- Validate `ML.STANDARD_SCALER` equals `(x - AVG) / STDDEV_POP` (not the default `STDDEV`/`STDDEV_SAMP`) — verified live in `functions/scalers/scalers.sql` (Example 1).

**Limitations / gotchas:**
- The four analytic scalers MUST use an empty `OVER()`; omitting it errors. `ML.NORMALIZER` must NOT use `OVER()`.
- An analytic function cannot be an argument to another analytic function, but a scalar function can take an analytic function's result as an argument (e.g. `ML.POLYNOMIAL_EXPAND` wrapping `ML.IMPUTER(...) OVER()`) — see `functions/feature_engineering/feature_engineering.sql` (Example 6).
- `ML.NORMALIZER` normalizes across the elements of each row's ARRAY (row-wise), not down a column — semantically different from the column scalers.
- `ML.MIN_MAX_SCALER` caps prediction-time inputs to `[0, 1]` when they fall outside the training min/max.
- Imputation of NULLs is not done by scalers; pair with `ML.IMPUTER` (impute in the input query or earlier in the transform chain).

**BigFrames API:** `bigframes.ml.preprocessing.StandardScaler`, `MinMaxScaler`, `MaxAbsScaler` (and `compose.ColumnTransformer`); not every scaler has a 1:1 class — use SQL `TRANSFORM` for full parity.

**Repo examples (tested):**
- [`functions/scalers/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/scalers) — all five scalers on `penguins`, standalone (Examples 1–5) and side-by-side on one column (Example 7). Covers `ML.ROBUST_SCALER` with all three optional parameters (`[10,90]` custom range, `with_median = FALSE`, `with_quantile_range = FALSE`) and `ML.NORMALIZER` at p ∈ {0, 1, 2, +inf} on `[3.0, 4.0]`, then on a real per-penguin measurement vector. Verifies the `STDDEV_POP` gotcha above (Example 1), `ML.MIN_MAX_SCALER`'s prediction-time capping via a live `CREATE MODEL` + `ML.TRANSFORM` test — 20.0 → 0.0 and 100.0 → 1.0 against a training range of `[32.1, 59.6]` (Example 2) — and `ML.ROBUST_SCALER`'s outlier robustness against `ML.STANDARD_SCALER` on an injected outlier (500 among 10–14): standard compresses the normal points into −0.35…−0.32, robust keeps them spread across −0.8…0.8 (Example 4). Example 6 shows NULLs passing through untouched. Example 8 ends with a `LOGISTIC_REG` embedding the `TRANSFORM` directly (roc_auc = 1.0), so `ML.PREDICT` on raw unscaled input works — contrast with `models/transform_only/`, whose standalone pipeline needs explicit re-application.
- Scalers inside a real `TRANSFORM` of an estimator, across model types: [`models/linear_regression/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/linear_regression) and [`models/dnn_regressor/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/dnn_regressor) (`ML.STANDARD_SCALER` on the measurement columns), [`models/dnn_classifier/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/dnn_classifier), [`models/wide_and_deep_regressor/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/wide_and_deep_regressor), [`models/wide_and_deep_classifier/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/wide_and_deep_classifier), [`models/logistic_regression/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/logistic_regression), [`models/kmeans/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/kmeans).
- [`models/transform_only/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/transform_only) — `ML.IMPUTER` + scaling + one-hot encoding in one `TRANSFORM_ONLY` model, the reusable/modular pattern: the preprocessing statistics are frozen at creation time and reapplied via `ML.TRANSFORM` for any downstream model.
- [`workflows/customer_segmentation/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/customer_segmentation) — `ML.STANDARD_SCALER` on RFM features before `KMEANS` (Step 2) — raw scale would let `monetary`, which ranges into the thousands, dominate the distance calculation. Carries the verified gotcha that `user_id` must be kept out of the training query or it becomes an unscaled feature distorting every distance.


---
