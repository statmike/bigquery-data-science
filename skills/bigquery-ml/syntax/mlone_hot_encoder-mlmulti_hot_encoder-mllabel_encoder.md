# `ML.ONE_HOT_ENCODER` / `ML.MULTI_HOT_ENCODER` / `ML.LABEL_ENCODER`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mlone_hot_encoder--mlmulti_hot_encoder--mllabel_encoder`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlone_hot_encoder--mlmulti_hot_encoder--mllabel_encoder)

- **Description:** Categorical-encoding preprocessing functions. `ML.ONE_HOT_ENCODER` encodes a scalar `STRING` into a one-hot (or, with `drop`, dummy) sparse vector. `ML.MULTI_HOT_ENCODER` encodes an `ARRAY<STRING>` into a multi-hot sparse vector (one feature per unique element, useful for bag/tag columns). `ML.LABEL_ENCODER` maps a scalar `STRING` to an ordinal `INT64` in `[0, n]`. All three are **analytic (window) functions** — they require an `OVER()` clause to compute the vocabulary across the partition.
- **Use cases:**
  - One-hot encode nominal categoricals for linear/logistic/boosted-tree models that don't auto-encode the way you want.
  - Multi-hot encode array columns (tags, skus, multi-select fields) where a row has many categories.
  - Label-encode high-cardinality categoricals into a single compact integer column (ordinal — only appropriate where order is meaningful or for tree models).
  - Cap vocabulary explosion with `top_k` / `frequency_threshold`; the same fitted vocabulary is reused at prediction time when called inside `TRANSFORM`.
- **documentation:** [ML.ONE_HOT_ENCODER](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-one-hot-encoder) · [ML.MULTI_HOT_ENCODER](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-multi-hot-encoder) · [ML.LABEL_ENCODER](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-label-encoder) · [Preprocessing functions overview](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-preprocessing-functions)
- **Type:** Analytic (window) scalar functions — must be used with `OVER()`. Not table-valued; not aggregate.
- **Applies to models:** Any model type that supports **manual preprocessing**, used either as a standalone query transform or inside the `TRANSFORM` clause of `CREATE MODEL`. (When used in `TRANSFORM`, the fitted vocabulary + `top_k`/`frequency_threshold`/`drop` choices are stored with the model and auto-applied during `ML.PREDICT`/`ML.EVALUATE`.) Exportable with the model via [TRANSFORM-function export](https://cloud.google.com/bigquery/docs/exporting-models#export-transform-functions). No connection required.
- **Status:** GA.

**Syntax:**
```sql
-- scalar STRING -> one-hot / dummy sparse vector
ML.ONE_HOT_ENCODER(string_expression [, drop] [, top_k] [, frequency_threshold]) OVER()

-- ARRAY<STRING> -> multi-hot sparse vector
ML.MULTI_HOT_ENCODER(array_expression [, top_k] [, frequency_threshold]) OVER()

-- scalar STRING -> ordinal INT64
ML.LABEL_ENCODER(string_expression [, top_k] [, frequency_threshold]) OVER()
```

**Inputs:**

| Parameter | Type | Required | Default | Applies to | Description |
|-----------|------|----------|---------|------------|-------------|
| `string_expression` | STRING | Yes | — | ONE_HOT, LABEL | Scalar categorical value to encode. |
| `array_expression` | ARRAY\<STRING\> | Yes | — | MULTI_HOT | Array of categorical values to multi-hot encode. |
| `drop` | STRING | No | `'none'` | ONE_HOT only | `'none'` retains all categories; `'most_frequent'` drops the most frequent category (dummy encoding). |
| `top_k` | INT64 | No | `32000` | all three | Keep only the `top_k` most frequent categories; rarer categories encode to 0. Must be \< 1,000,000. |
| `frequency_threshold` | INT64 | No | `5` | all three | Keep only categories with frequency \>= threshold; rarer categories encode to 0. |

**Outputs:**

| Function | Output column type | Description |
|----------|--------------------|-------------|
| `ML.ONE_HOT_ENCODER` | ARRAY\<STRUCT\<index INT64, value DOUBLE\>\> | Sparse one-hot vector; vocabulary sorted alphabetically. NULL / out-of-vocab / dropped category -> `index 0`. |
| `ML.MULTI_HOT_ENCODER` | ARRAY\<STRUCT\<index INT64, value DOUBLE\>\> | Sparse multi-hot vector across unique array elements. NULL / out-of-vocab -> `index 0`. |
| `ML.LABEL_ENCODER` | INT64 | Ordinal code in `[0, n]`, vocabulary sorted alphabetically. NULL / out-of-vocab / excluded -> `0`. |

**Best practices:**
- Use inside `TRANSFORM` so the vocabulary fit at train time is automatically reapplied at prediction — avoids train/serve skew and manual re-encoding.
- Use `top_k` and `frequency_threshold` together to bound dimensionality on high-cardinality columns; both push trimmed categories to bucket `0` (shared with NULL/unseen).
- Prefer `ML.ONE_HOT_ENCODER` for nominal features fed to linear/logistic models; `ML.LABEL_ENCODER` only where an ordinal integer is acceptable (e.g., tree models) since it imposes an arbitrary alphabetical order.
- Reserve `ML.MULTI_HOT_ENCODER` for genuine array/multi-value columns rather than splitting a string yourself.

**Limitations:**
- All three are window functions: an `OVER()` clause is mandatory; omitting it is a syntax error.
- `top_k` must be less than 1,000,000 to avoid high-dimensionality issues.
- Bucket `0` is overloaded (NULL + below-`top_k` + below-`frequency_threshold` + unseen-at-predict), so you cannot distinguish those cases downstream.
- `drop` is unique to `ML.ONE_HOT_ENCODER`; `ML.LABEL_ENCODER` and `ML.MULTI_HOT_ENCODER` have no `drop` argument.
- **MAJOR GOTCHA, verified live — the default discrepancy is not just a docs footnote, it changes real output:** older documentation cites default `top_k = 1,000,000` / `frequency_threshold = 0`; current docs (and current live behavior) specify `top_k = 32,000` / `frequency_threshold = 5`. Tested with categories occurring 6x/7x/3x: under the **current** default, the category with only 3 occurrences (below the frequency-5 threshold) silently collapses into bucket `0` — indistinguishable from `NULL`/unseen-at-predict, no error or warning. Under `frequency_threshold=0` (the old default), that same category keeps its own index. **Any real dataset with a rare-but-meaningful category (fewer than 5 total occurrences) will silently lose it under current defaults** unless `frequency_threshold` is explicitly lowered.

**BigFrames API:** `bigframes.ml.preprocessing.OneHotEncoder`, `bigframes.ml.preprocessing.LabelEncoder` (and the broader `bigframes.ml.preprocessing` module); these compile to the corresponding `ML.*` encoders.

**Repo example (tested):**
- [`functions/encoding/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/encoding) — Example 1 puts `ML.ONE_HOT_ENCODER` default, dummy (`'most_frequent'`), and `'none', 32000, 0` side by side over an `UNNEST([...])` literal with a 6x/7x/3x frequency spread; Example 3 runs `ML.ONE_HOT_ENCODER` + `ML.LABEL_ENCODER` on `penguins.island` and `ML.MULTI_HOT_ENCODER(arr, 100, 0) OVER()` on a real `ARRAY<STRING>` (one feature per unique element across all rows, not per row).
- [`functions/encoding/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/encoding) Example 2 — live proof of the default discrepancy above: the 3-occurrence category collapses into bucket `0` under the current default, and keeps its own index under `frequency_threshold = 0`. Example 4 embeds `ML.ONE_HOT_ENCODER` + `ML.LABEL_ENCODER` in a real `LOGISTIC_REG` `TRANSFORM` (accuracy ~0.71 from `island` + `sex` alone).
- [`models/transform_only/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/transform_only) — one-hot encoding as part of a reusable `TRANSFORM_ONLY` preprocessing pipeline, with the vocabulary frozen at creation time.


---
