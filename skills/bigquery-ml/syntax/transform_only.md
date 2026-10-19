# `TRANSFORM_ONLY`

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#transform_only`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#transform_only)

- **Description:** A model that contains *only* a `TRANSFORM` clause and no learning algorithm. It captures a set of feature‑preprocessing rules (plus the statistics computed at creation time, e.g. the mean/stddev used by `ML.STANDARD_SCALER`) as a reusable, exportable model object. There is no training of a predictive estimator — the model output is the preprocessed data, materialized via `ML.TRANSFORM`.
- **When to use:**
  - Decouple feature engineering from model training so the same preprocessing can be reused across many models and serving paths.
  - Build modular, feature‑level (feature‑store‑like) transforms and chain them into a pipeline with CTEs (`WITH`) or a view.
  - Guarantee training/serving consistency — computed statistics are frozen at creation, eliminating training/serving skew.
  - Run large‑scale batch feature transformations efficiently.
- **Category:** transform-only.
- **Connection required:** No. (A connection is only needed if you later `EXPORT MODEL` to GCS or register to Vertex AI — those are optional lifecycle steps.)
- **Status:** GA.
- **documentation:** [CREATE MODEL for transform-only models](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-transform) · [ML.TRANSFORM function](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-transform) · [TRANSFORM clause](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create#transform) · [Perform feature engineering with the TRANSFORM clause](https://cloud.google.com/bigquery/docs/bigqueryml-transform)

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
TRANSFORM(
  -- pass-through columns + transformed columns (named aliases required)
  species, island, sex,
  ML.ROBUST_SCALER(body_mass_g) OVER() AS body_mass_g,
  ML.STANDARD_SCALER(culmen_length_mm) OVER() AS culmen_length_mm
)
OPTIONS(
  model_type = 'TRANSFORM_ONLY'
  -- optional: model_registry = 'VERTEX_AI', VERTEX_AI_MODEL_ID = '...'
)
AS SELECT * FROM `PROJECT_ID.DATASET.SOURCE_TABLE`;
```

**Options (model-specific):**

| Option | Type | Required | Default | Range / Values | Description |
|--------|------|----------|---------|----------------|-------------|
| `model_type` | STRING | Yes | — | `'TRANSFORM_ONLY'` | Selects the transform-only model. No learning options apply. |
| `model_registry` | STRING | No | none | `'VERTEX_AI'` | Optionally register the transform model to Vertex AI Model Registry. |
| `vertex_ai_model_id` | STRING | No | none | any | Model ID used in the registry when `model_registry='VERTEX_AI'`. |
| `vertex_ai_model_version_aliases` | ARRAY\<STRING\> | No | none | any | Version aliases for the registered model. |

(No HP‑tuning, label, data‑split, or learning options exist for this type — there is no estimator to train. Any unsupported learning option causes an error.)

**TRANSFORM clause rules (the `select_list`):**
- Pass columns through untransformed via `*`, `* EXCEPT(...)`, or by naming them.
- Transform columns with preprocessing functions; every transformed/derived column **must** have a named alias (anonymous expressions like `a + b` are not allowed; `a + b AS c` is).
- Omitting a `query_statement` column from `TRANSFORM` drops it from the output.
- Output columns may be any BigQuery‑supported type.
- Analytic preprocessing functions (scalers, imputer, etc.) use the `... OVER()` syntax so statistics are computed over the creation data and frozen into the model.

**Applying the model (consume with `ML.TRANSFORM`):**
```sql
SELECT * FROM ML.TRANSFORM(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  (SELECT * FROM `PROJECT_ID.DATASET.NEW_DATA`)  -- or TABLE `...`
);
```
Input column names must match the names in the model's `TRANSFORM` clause, with implicitly coercible types. `ML.TRANSFORM` returns exactly the columns the `TRANSFORM` clause produces.

**Supported lifecycle functions:** `ML.TRANSFORM` (the primary/only way to apply it), `ML.FEATURE_INFO` (pre‑transform summary stats), `EXPORT MODEL`, and BQ model management (`ALTER MODEL`, `DROP MODEL`, `bq ls`). NOT supported: `ML.PREDICT`, `ML.EVALUATE`, `ML.WEIGHTS`/`ML.ADVANCED_WEIGHTS`, `ML.GLOBAL_EXPLAIN`, `ML.FEATURE_IMPORTANCE`, `ML.EXPLAIN_PREDICT` — there is no trained estimator to predict/evaluate/explain.

**ML.EVALUATE output metrics (this type):** N/A — `ML.EVALUATE` is not applicable (no estimator, no labels).

**Preprocessing support:** This IS the preprocessing primitive. Supports the full BQML preprocessing function family inside `TRANSFORM`: general (`ML.IMPUTER`); numeric (`ML.STANDARD_SCALER`, `ML.ROBUST_SCALER`, `ML.MIN_MAX_SCALER`, `ML.MAX_ABS_SCALER`, `ML.NORMALIZER`, `ML.BUCKETIZE`, `ML.QUANTILE_BUCKETIZE`, `ML.POLYNOMIAL_EXPAND`); categorical (`ML.ONE_HOT_ENCODER`, `ML.MULTI_HOT_ENCODER`, `ML.LABEL_ENCODER`, `ML.FEATURE_CROSS`, `ML.HASH_BUCKETIZE`); text (`ML.NGRAMS`, `ML.BAG_OF_WORDS`, `ML.TF_IDF`); image (`ML.DECODE_IMAGE`, `ML.RESIZE_IMAGE`, `ML.CONVERT_IMAGE_TYPE`, `ML.CONVERT_COLOR_SPACE`).

**Hyperparameter tuning:** N/A — no learner, nothing to tune.

**Explainability / weights:** N/A — none of the explainability/weights functions apply (no model parameters). For attribution, apply the transform then train a separate estimator that supports explainability.

**Best practices:**
- Build one transform model per logical step (impute, then scale) and compose them in order with CTEs; or wrap the whole pipeline in a view for reuse.
- Build feature‑specific transform‑only models for feature‑store‑style modularity.
- Train downstream estimators on the *output* of the transform pipeline; the estimator then has no embedded `TRANSFORM`, so you must re‑apply the same `ML.TRANSFORM` pipeline before `ML.PREDICT`/`ML.EVALUATE`.
- Prefer transform‑only models for large batch feature jobs.
- Note the contrast vs. an *embedded* `TRANSFORM` (TRANSFORM clause on a predictive model): embedded transforms auto‑apply at predict time (no re‑application needed) but are not reusable across models; transform‑only models are reusable but must be explicitly re‑applied.

**Limitations:**
- Cannot predict, evaluate, or explain — it is a preprocessing object only.
- Consumed almost exclusively through `ML.TRANSFORM`; column names/types must align with the `TRANSFORM` clause.
- No labels, no data split, no learning options.
- Anonymous (unaliased) transformed columns are rejected.

**Locations:** Available in BigQuery ML regions/multi-regions generally; same location rules as `CREATE MODEL`. Vertex AI registration/export follow standard cross-service location requirements.

**BigFrames API:** No single direct `TRANSFORM_ONLY` class. Equivalent functionality is the `bigframes.ml.preprocessing` transformers (e.g. `StandardScaler`, `MaxAbsScaler`, `OneHotEncoder`, `LabelEncoder`) and `bigframes.ml.pipeline.Pipeline`/`ColumnTransformer`, which compile to BQML preprocessing under the hood. A persisted transform-only model can be read with `bigframes.pandas.read_gbq_model`.

**Repo example (tested):**
- `bigquery-ml/models/transform_only/transform_only.ipynb` — dedicated `TRANSFORM_ONLY` notebook on `penguins`: one pipeline chaining `ML.IMPUTER` + `ML.STANDARD_SCALER`/`ML.ROBUST_SCALER`/`ML.ONE_HOT_ENCODER`, applied via `ML.TRANSFORM`, feeding a downstream `LOGISTIC_REG` with no embedded `TRANSFORM` of its own. **Two verified findings:** (1) `ML.TRANSFORM` silently passes through any input column not referenced by the `TRANSFORM` clause, appended after the transform outputs — useful (carry an id/label through) but easy to mistake for pipeline output; (2) calling `ML.PREDICT` on the downstream model with *raw* (untransformed) data does **not** error — it silently predicts using values on the wrong scale, reproduced live: every row predicted the same class ("Gentoo penguin") regardless of true label until the input was re-wrapped in `ML.TRANSFORM`. Also confirms `EXPORT MODEL` on a transform-only model (`transform/saved_model.pb`, no predictive weights since there's no estimator).
- **Composition patterns this model type enables**, beyond the single-pipeline case above: one `TRANSFORM_ONLY` model per preprocessing *stage* (imputation, then scaling), chained with CTEs and exposed as a view so downstream queries see one clean surface; or one per *feature*, feature-store style, so a transform can be versioned and reused independently of any estimator. Either way the output feeds a `CREATE MODEL` that carries no `TRANSFORM` of its own, and `ML.TRANSFORM` reapplies the exact learned statistics at scoring time. `ML.FEATURE_INFO` reports the pre-transform summary stats, and a transform-only model can also be consumed from BigFrames via `read_gbq_model().predict()`.


---
