# `ML.TRANSFORM` (applying a saved transform)

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mltransform-applying-a-saved-transform`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mltransform-applying-a-saved-transform)

- **Description:** Applies the preprocessing captured in a model's `TRANSFORM` clause to new data and returns the transformed feature columns only — no prediction. The transformation statistics (scaler mins/maxes, bucket edges, encoder vocabularies, etc.) computed at training time are reused, so training and serving see identical preprocessing.
- **Use cases:**
  - Inspect exactly what a model feeds its algorithm after preprocessing (debugging feature engineering).
  - Reuse a saved transform (especially a `model_type = 'TRANSFORM_ONLY'` model) to preprocess data feeding a *different* model's training or `ML.PREDICT`.
  - Materialize preprocessed features for downstream non-BQML use.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-transform
- **Type:** Table-valued function.
- **Applies to models:** Any model created with a `TRANSFORM(...)` clause, including transform-only models (`model_type = 'TRANSFORM_ONLY'`).

> Automatic application: you usually do NOT need `ML.TRANSFORM`. A `TRANSFORM` clause defined in `CREATE MODEL` is applied automatically inside `ML.PREDICT`, `ML.EVALUATE`, `ML.DETECT_ANOMALIES`, `ML.RECONSTRUCTION_LOSS`, and online serving — call raw columns and BQML re-preprocesses them. `ML.TRANSFORM` is for the cases where you want the preprocessed output by itself.

**Syntax:**
```sql
SELECT *
FROM ML.TRANSFORM(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  (SELECT * FROM `PROJECT_ID.DATASET.NEW_DATA`)
);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model | Yes | — | Must have been created with a `TRANSFORM` clause. |
| `query_statement` / `TABLE` | table | Yes | — | Data to preprocess. Column names must match the inputs of the model's `TRANSFORM` clause; types must be coercion-compatible. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (transform output) | varies | Exactly the columns produced by the model's `TRANSFORM` clause (scaled numerics, encoded categoricals, etc.). Label/passthrough columns named in `TRANSFORM` are returned as-is. |

**Best practices:**
- Pair with a `TRANSFORM_ONLY` model to centralize and version preprocessing once, then feed `ML.TRANSFORM(...)` output into multiple downstream model trainings / predictions.
- Pull required input column names/types from the model metadata (feature columns) before calling.

**Limitations:**
- Fails if the model has no `TRANSFORM` clause.
- Input column names must match the `TRANSFORM` clause inputs.
- **GOTCHA (verified live, `models/transform_only/`):** any column present in the input query but **not** referenced anywhere in the `TRANSFORM` clause passes straight through untouched, appended after the transform outputs — the "exactly the columns produced by TRANSFORM" description above is true for referenced columns, but unreferenced extras ride along too. Useful for carrying an id/label column through without re-listing it in the pipeline, but easy to mistake for the pipeline itself re-emitting a raw column.
- **GOTCHA (verified live, `models/transform_only/`):** a downstream model trained on `ML.TRANSFORM` output but with no *embedded* `TRANSFORM` of its own does not know to re-apply the pipeline at predict time. Calling `ML.PREDICT` on it with raw (untransformed) data does **not** error — it silently predicts using values on the wrong scale. Reproduced live: every row predicted the same class regardless of true label until the raw input was re-wrapped in `ML.TRANSFORM` first.

**BigFrames API:** Transform reuse is handled implicitly by pipeline/estimator objects; no standalone one-to-one `ML.TRANSFORM` call needed in typical BigFrames pipelines.

**Repo example (tested):**
- `bigquery-ml/models/transform_only/transform_only.ipynb` — both gotchas above reproduced live; a `TRANSFORM_ONLY` pipeline (`ML.IMPUTER` + scalers + `ML.ONE_HOT_ENCODER`) feeding a downstream `LOGISTIC_REG` with no embedded `TRANSFORM`.
- `bigquery-ml/models/logistic_regression/logistic_regression.sql` (Example 9) — `CREATE MODEL ... TRANSFORM(ML.STANDARD_SCALER(age) OVER() AS age, ...)`; the scaler is saved with the model and reapplied automatically at predict time (the SQL comments note no need to repeat it in `ML.PREDICT`) — this is the embedded-`TRANSFORM` case, which does NOT need the re-application `ML.TRANSFORM` gotcha above applies to.
