# `ML.RECOMMEND`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlrecommend`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlrecommend)

- **Description:** Generates recommendations (predicted ratings or confidences) from a trained `MATRIX_FACTORIZATION` model for user-item pairs. Because the training input is a sparse matrix, the function fills in predictions for the missing user-item entries.
- **Use cases:**
  - Score every item for a given user (top-N recommendations).
  - Score a specific user-item pair (predicted rating / confidence).
  - Batch-generate the full user x item recommendation matrix for offline serving.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-recommend
- **Type:** Table-valued function.
- **Applies to models:** `MATRIX_FACTORIZATION` only (explicit or implicit `feedback_type`).

**Syntax:**
```sql
SELECT *
FROM ML.RECOMMEND(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`
  [, { TABLE `PROJECT_ID.DATASET.INPUT` | (QUERY_STATEMENT) }]
  [, STRUCT(TRIAL_ID AS trial_id)]
);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model | Yes | — | A trained `MATRIX_FACTORIZATION` model. |
| `TABLE` / `QUERY_STATEMENT` | table/query | No | all user x item pairs | Input rows. If both user and item columns are present, returns one rating per pair; if only the user (or only the item) column is present, returns all item (or user) ratings; if omitted, returns predictions for every user-item combination. Column names/types must match the model's user and item columns (implicit coercion applies). |
| `trial_id` | INT64 | No | optimal trial | Selects a specific hyperparameter-tuning trial; only valid if the model was trained with HP tuning. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| \<user_col\> | matches model | The user identifier column (named as in the model). |
| \<item_col\> | matches model | The item identifier column (named as in the model). |
| `predicted_`\<rating_col\> | FLOAT64 | EXPLICIT feedback: predicted rating, roughly in the range of the original input ratings (values outside the range are normal). |
| `predicted_`\<rating_col\>`_confidence` | FLOAT64 | IMPLICIT feedback: relative confidence, approximately 0-1 when the model has converged. |
| `trial_id` | INT64 | Present only when the model was trained with HP tuning. |

**Best practices:**
- Output can be very large (all user x item pairs); write results to a table rather than streaming.
- For top-N, `ORDER BY predicted_<rating_col>[_confidence] DESC LIMIT N` per user.
- Pin `trial_id` only when you need a non-optimal HP-tuning trial.

**Limitations:**
- Matrix factorization models require reservation/flat-rate (slot) capacity to train; `ML.RECOMMEND` itself runs as a standard query but the upstream model has that prerequisite.
- Input user/item columns must align with the model's training columns.

**BigFrames API:** `bigframes.ml.decomposition.MatrixFactorization.predict()` (DataFrame in/out) is the recommendation equivalent.

**Repo example (tested):**
- `bigquery-ml/models/matrix_factorization/matrix_factorization.sql` — the full lifecycle on Google Merchandise Store `ga_sessions_*` data with `feedback_type = 'IMPLICIT'` (42,178 users x 320 items, ~1.3M interactions): create → evaluate → recommend → inspect factors → generate embeddings → item-item similarity via `VECTOR_SEARCH` → introspect → tune.
- `bigquery-ml/workflows/recommendation/recommendation.sql` (Step 3) — top-N per user done properly: `ROW_NUMBER() OVER (PARTITION BY visitor_id ORDER BY predicted_view_count_confidence DESC)` filtered to `rank <= 5`, rather than a global `ORDER BY ... LIMIT`.
- **Is the personalization real?** The same file (Step 4) answers it quantitatively rather than assuming: a real visitor's personalized top-10 overlapped the global most-viewed top-10 by **0 of 10** items.
- **GOTCHA, verified live: `ML.RECOMMEND` on a user absent from training does not error — it silently returns a ranking.** `workflows/recommendation/recommendation.sql` (Step 5) proves that ranking is not personalized by showing two different absent user IDs receive an identical top-5. Cold-start users need to be detected upstream; the function will not signal them.
- **Retraining variance:** `models/matrix_factorization/matrix_factorization.sql` (Example 2) records that WALS training is not deterministic — repeated identical runs landed at ~0.873 and ~0.860 — comparable to `models/kmeans/` and `RANDOM_FOREST_*`, unlike PCA's determinism.

---
