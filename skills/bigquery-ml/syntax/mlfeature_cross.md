# `ML.FEATURE_CROSS`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mlfeature_cross`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlfeature_cross)

- **Description:** Given a `STRUCT` of categorical (string) features, returns a `STRUCT` of all feature-cross combinations up to `degree`. Each output field is the concatenated source values (e.g. `'a_A'`), useful as interaction features.
- **Use cases:**
  - Capture interactions between categorical columns (e.g. `region` × `device`).
  - Generate crosses for linear / logistic models that don't learn interactions natively.
- **documentation:** <https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-feature-cross>
- **Type:** Scalar (no `OVER()`).
- **Category:** Categorical manual preprocessing.
- **Applies to models:** Any model type. **Not exportable** in `TRANSFORM` (cannot accompany an exported / Vertex-registered model).

**Syntax:**
```sql
ML.FEATURE_CROSS(struct_categorical_features [, degree])
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `struct_categorical_features` | `STRUCT` of `STRING` | Yes | — | Named categorical columns to cross (use `STRUCT(col1, col2, ...)`). |
| `degree` | `INT64` | No | `2` | Highest combination degree; range `[2, 4]`. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (result) | `STRUCT<STRING>` | One field per crossed combination, named `\<col_a\>_\<col_b\>`, valued `\<val_a\>_\<val_b\>`. |

**Best practices:** Keep `degree` low (2) — combinations grow combinatorially and can explode cardinality. Pre-bucketize numeric columns to strings before crossing.
**Limitations:** Categorical (string) inputs only; `degree` capped at 4. **Not exportable** in `TRANSFORM`. **Verified live:** a `CREATE MODEL ... TRANSFORM(ML.FEATURE_CROSS(...))` trains and predicts (`ML.PREDICT`) completely normally — the limitation only bites at `EXPORT MODEL` time, which fails with `"400 Model TRANSFORM contains unsupported function for exporting."` A model needing portability/serving outside BQ (`EXPORT MODEL`, `model_registry='VERTEX_AI'`, remote-model deployment) must compute crosses in the input query instead.
**BigFrames API:** No direct equivalent (build via DataFrame ops).
**Repo example (tested):** [`functions/feature_engineering/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/feature_engineering) — Example 3 crosses `penguins`' `island` × `sex`:
```sql
SELECT island, sex,
  ML.FEATURE_CROSS(STRUCT(island, sex)) AS crossed
FROM `bigquery-public-data.ml_datasets.penguins`
WHERE sex IS NOT NULL;
-- e.g. {'island_sex': 'Dream_FEMALE'} -- one field per crossed combination,
-- named <col_a>_<col_b>, valued <val_a>_<val_b>. Scalar function, no OVER().
```
Example 4 then plugs it into a live `CREATE MODEL` — training and `ML.PREDICT` work normally, and only the subsequent `EXPORT MODEL` fails, with the exact error captured.

---
