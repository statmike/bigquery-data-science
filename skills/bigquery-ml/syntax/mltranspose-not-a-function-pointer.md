# `ML.TRANSPOSE` — not a function (pointer)

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mltranspose--not-a-function-pointer`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mltranspose--not-a-function-pointer)

`ML.TRANSPOSE` does not exist in BigQuery ML. To "transpose" preprocessing into the model so it serves automatically, use the **`TRANSFORM` clause** of `CREATE MODEL`:
- `TRANSFORM` clause reference: <https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create#transform>
- Feature engineering with `TRANSFORM`: <https://cloud.google.com/bigquery/docs/bigqueryml-transform>
- Inspect the preprocessed output of a model's `TRANSFORM` with `ML.TRANSFORM` (function): <https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-transform>

**Repo examples (tested) — `TRANSFORM` in a real `CREATE MODEL`:**
- [`models/transform_only/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/transform_only) — the fullest version of the pattern: one `TRANSFORM` mixing `ML.IMPUTER`, two scalers, and `ML.ONE_HOT_ENCODER`, packaged as a `TRANSFORM_ONLY` model with no estimator, so the same preprocessing (and its frozen train-time statistics) can be reused by any downstream model:
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.transform_only_penguins`
TRANSFORM(
  species,
  island,
  ML.IMPUTER(body_mass_g, 'mean') OVER() AS body_mass_g,
  ML.STANDARD_SCALER(culmen_length_mm) OVER() AS culmen_length_mm,
  ML.STANDARD_SCALER(culmen_depth_mm) OVER() AS culmen_depth_mm,
  ML.ROBUST_SCALER(flipper_length_mm) OVER() AS flipper_length_mm,
  ML.ONE_HOT_ENCODER(sex) OVER() AS sex_encoded
)
OPTIONS(model_type = 'TRANSFORM_ONLY') AS
SELECT species, island, sex, body_mass_g, culmen_length_mm, culmen_depth_mm, flipper_length_mm
FROM `bigquery-public-data.ml_datasets.penguins`;
```
  Example 4 exports it (a transform-only model exports like any other); Examples 6 and 7 are the payoff — predicting on raw data through a *standalone* pipeline silently gives garbage unless `ML.TRANSFORM` is re-applied first.
- [`functions/scalers/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/scalers) Example 8 — the contrasting case: the `TRANSFORM` is embedded directly in a `LOGISTIC_REG`, so `ML.PREDICT` on raw unscaled input auto-applies the scaling and no re-application step exists to forget.
- [`models/export/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/export) Example 5 — `model_registry = 'VERTEX_AI'` with `vertex_ai_model_id`, registering the model at `CREATE MODEL` time rather than exporting it.


---
