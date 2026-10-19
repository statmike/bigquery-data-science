# `ML.WEIGHTS`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlweights`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlweights)

- **Description:** Returns the learned model parameters (weights/coefficients) of a trained linear regression, logistic regression, or matrix factorization model. For GLMs it returns one weight per processed feature (plus the intercept); for matrix factorization it returns the latent factor weights per user/item.
- **Use cases:**
  - Inspect feature coefficients to understand direction/magnitude of each feature's effect.
  - Compare relative feature importance using `STANDARDIZE => TRUE` (puts all weights on a comparable scale).
  - Extract user/item latent factors and intercepts from a matrix factorization recommender.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-weights · weights overview: https://cloud.google.com/bigquery/docs/weights-overview
- **Type:** Table-valued function.
- **Applies to models:** `LINEAR_REG`, `LOGISTIC_REG` (binary and multiclass), `MATRIX_FACTORIZATION`. NOT supported for boosted trees, random forest, DNN, wide-and-deep, k-means, PCA, autoencoder, ARIMA_PLUS, or AutoML (export the model and inspect externally, or use `ML.FEATURE_IMPORTANCE` / `ML.GLOBAL_EXPLAIN` / `ML.CENTROIDS` / `ML.PRINCIPAL_COMPONENTS` / `ML.ARIMA_COEFFICIENTS` as appropriate).

**Syntax:**
```sql
-- GLM (linear / logistic regression)
SELECT *
FROM ML.WEIGHTS(MODEL `PROJECT_ID.DATASET.MODEL_NAME`
                [, STRUCT(TRUE AS standardize)]);

-- Matrix factorization (no standardize argument)
SELECT *
FROM ML.WEIGHTS(MODEL `PROJECT_ID.DATASET.MODEL_NAME`);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model ref | Yes | — | The trained model. |
| `STANDARDIZE` | BOOL (in STRUCT) | No | `FALSE` | Standardize weights as if all features had mean 0 / std 1 so magnitudes are comparable. Applies to linear and logistic regression only (ignored / N/A for matrix factorization). |

**Outputs (linear & logistic regression):**

| Column | Type | Description |
|--------|------|-------------|
| `trial_id` | INT64 | HP-tuning trial ID. Only present if the model was trained with hyperparameter tuning. |
| `processed_input` | STRING | Feature input column name (matches the training query column). |
| `weight` | FLOAT64 | Weight for a numeric feature; NULL when the feature is categorical (see `category_weights`). Intercept appears as processed_input `__INTERCEPT__`. |
| `category_weights` | ARRAY\<STRUCT\> | For non-numeric (one-hot/dummy-encoded) columns: per-category weights. NULL for numeric columns. |
| `category_weights.category` | STRING | Category name. |
| `category_weights.weight` | FLOAT64 | Weight for that category. |
| `class_label` | STRING | Only for multiclass models; one row per `\<class_label, processed_input\>` pair. |

**Outputs (matrix factorization):**

| Column | Type | Description |
|--------|------|-------------|
| `processed_input` | STRING | Name of the user or item column. |
| `feature` | STRING | The specific user/item value. |
| `factor_weights` | ARRAY\<STRUCT\> | Latent factors and their weights. |
| `factor_weights.factor` | INT64 | Latent factor index (1..`NUM_FACTORS`). |
| `factor_weights.weight` | FLOAT64 | Weight of that factor for the feature. |
| `intercept` | FLOAT64 | Bias term for the feature. A `global__intercept__` row (NULL `processed_input`/`factor_weights`) is also returned; it is 0 for implicit-feedback models. |

**Querying nested `category_weights`:**
```sql
SELECT category, weight
FROM UNNEST((
  SELECT category_weights
  FROM ML.WEIGHTS(MODEL `PROJECT_ID.DATASET.MODEL_NAME`)
  WHERE processed_input = 'occupation'));
```

**Best practices:**
- Use `STRUCT(TRUE AS standardize)` to rank feature importance by absolute weight magnitude.
- With a `TRANSFORM` clause, weights are reported on the TRANSFORM output features (denormalized by default).
- **Train with `category_encoding_method = 'DUMMY_ENCODING'` if you intend to read `category_weights`.** The default `ONE_HOT_ENCODING` makes every categorical feature's dummies collinear with the intercept, so individual category weights are not uniquely identified — **verified**: retraining an identical `LINEAR_REG` model twice (same query, different `AUTO_SPLIT` draw) swung one category's weight from +305/+353/+340 to −39/−4/+8.6 between runs. `DUMMY_ENCODING` pins one category per feature to `weight: 0.0` and makes the rest stable, well-defined deltas. See `models/linear_regression/`.

**Limitations:**
- Tree/DNN/clustering/forecast/AutoML models are not supported (use type-specific functions or export).
- Categorical columns split their weights into the nested `category_weights` array, so a flat `SELECT *` shows NULL in `weight` for those rows.
- With `ONE_HOT_ENCODING` (the default), per-category weights are not uniquely identified and can vary substantially run-to-run (see best practice above) — this does not affect `ML.PREDICT`/`ML.EVALUATE`, only the individual weight breakdown.

**BigFrames API:** `model.global_explain()` covers attribution; raw coefficients via the underlying model are exposed through the BigQuery SQL function. No dedicated `ml_weights()` wrapper — call `ML.WEIGHTS` via `bigframes.pandas.read_gbq(...)` over the TVF.

**Repo example (tested):**
- `bigquery-ml/models/linear_regression/linear_regression.sql` — `LINEAR_REG` on `penguins`/`body_mass_g`, trained with `DUMMY_ENCODING` specifically to keep `ML.WEIGHTS` stable and interpretable; SQL comments explain why. Example 7 immediately follows it with `ML.ADVANCED_WEIGHTS` on the same model, which is the direct way to see what `ML.WEIGHTS` alone cannot tell you — that `island`'s non-zero weights are not statistically distinguishable from zero. (`models/logistic_regression/logistic_regression.sql` covers the GLM lifecycle but not `ML.WEIGHTS` — the linear-regression file is the one to read for it; it uses `ML.ADVANCED_WEIGHTS` instead.)
- `bigquery-ml/workflows/difference_in_differences/difference_in_differences.sql` (Step 3) — the coefficient *is* the answer: the `treated_post` weight is the DiD estimate. Verified −19.29 with `optimize_strategy = 'NORMAL_EQUATION'`, matching `statsmodels.OLS` exactly, versus −6.19 under the default `AUTO_STRATEGY` — read weights for inference only from a normal-equation fit.
- `bigquery-ml/workflows/price_elasticity_dml/price_elasticity_dml.sql` (Steps 2 and 4) — `ML.WEIGHTS` on the naive and the double-ML model, verified −1.43 vs. −0.71: roughly half the apparent price sensitivity was confounding, visible only by comparing two weight readouts.
- `bigquery-ml/workflows/synthetic_control/synthetic_control.sql` (Step 2) — `ML.WEIGHTS` used as a *diagnostic of an invalid fit*: several weights come back negative and others far above 1, none of which a real percentage blend allows, on an underdetermined system (9 pre-period weeks vs. 13 donor columns).
- `bigquery-ml/workflows/survival_analysis/survival_analysis.sql` — weights on a discrete-time hazard `LOGISTIC_REG` read as hazard direction: activity features carry positive weights (faster time-to-event), `week` a small negative one.

---
