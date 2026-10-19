# `ML.IMPUTER`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mlimputer`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlimputer)

- **Description:** Replaces `NULL` values in a numerical or categorical (string) expression with a computed statistic.
- **Use cases:**
  - Fill missing numeric values with `mean` or `median`.
  - Fill missing categorical values with `most_frequent` (mode).
  - Stable imputation at serving — the train-time statistic is reused.
- **documentation:** <https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-imputer>
- **Type:** Analytic (requires empty `OVER()`).
- **Category:** General manual preprocessing.
- **Applies to models:** Any model type, via `TRANSFORM` or pre-query. **Exportable** in `TRANSFORM`.

**Syntax:**
```sql
ML.IMPUTER(expression, strategy) OVER()
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `expression` | `INT64`/`FLOAT64` or `STRING` | Yes | — | Numerical or categorical column to impute. |
| `strategy` | `STRING` | Yes | — | `'mean'` or `'median'` (numerical only), or `'most_frequent'` (numerical or string). |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (result) | `FLOAT64` (numeric) or `STRING` (categorical) | Original value, or the imputed statistic where input was `NULL`. |

**Best practices:** Choose `median` for skewed numeric data; `most_frequent` is the only valid strategy for strings. Use inside `TRANSFORM` so prediction reuses training statistics.
**Limitations:** `mean`/`median` reject string inputs. Requires `OVER()` (empty window).
**BigFrames API:** `bigframes.ml.impute.SimpleImputer`.
**Repo example (tested):** [`functions/feature_engineering/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/feature_engineering) — Example 1 imputes a numeric column two ways and a string column by mode, on real `penguins` data:
```sql
SELECT
  ML.IMPUTER(body_mass_g, 'mean')   OVER() AS imputed_mean,
  ML.IMPUTER(body_mass_g, 'median') OVER() AS imputed_median,
  ML.IMPUTER(sex, 'most_frequent')  OVER() AS sex_imputed_mode
FROM `bigquery-public-data.ml_datasets.penguins`;
```
Example 2 embeds it in a real `LOGISTIC_REG` `TRANSFORM` (unlike `ML.FEATURE_CROSS`/`ML.POLYNOMIAL_EXPAND`, `ML.IMPUTER` **is** exportable) — verified that predicting with a `NULL` `body_mass_g` at predict time auto-imputes with the training-time mean rather than erroring. Also [`models/transform_only/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/transform_only) Example 1, where `ML.IMPUTER` opens a reusable preprocessing pipeline (and where its required strategy argument is contrasted against the single-argument scalers).

---
