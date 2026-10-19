# `MATRIX_FACTORIZATION`

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#matrix_factorization`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#matrix_factorization)

- **Description:** Collaborative-filtering recommendation model. Learns low-dimensional latent factor vectors for users and items by factorizing the sparse user-item rating matrix, then predicts ratings/confidences for the (mostly missing) user-item pairs. Explicit feedback uses Alternating Least Squares (ALS); implicit feedback uses Weighted ALS (WALS).
- **When to use:**
  - Build product / content / movie recommenders from a (user, item, rating) interaction table.
  - You have explicit ratings (e.g., 1-5 stars) → `FEEDBACK_TYPE = 'EXPLICIT'`.
  - You only have implicit signals (clicks, views, session/engagement time, purchase counts) → `FEEDBACK_TYPE = 'IMPLICIT'`.
  - You want to score all missing user-item pairs at scale with `ML.RECOMMEND` without enumerating them.
- **Category:** recommendation
- **Connection required:** No. BUT see *Limitations* — `MATRIX_FACTORIZATION` is the one model type that does **not** run on BigQuery on-demand pricing; it requires a slot reservation/edition (capacity-based pricing).
- **Status:** GA.
- **documentation:** [CREATE MODEL (matrix factorization)](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-matrix-factorization) · [ML.RECOMMEND](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-recommend) · Journey/tutorials: [Explicit feedback tutorial](https://cloud.google.com/bigquery/docs/bigqueryml-mf-explicit-tutorial), [Implicit feedback tutorial](https://cloud.google.com/bigquery/docs/bigqueryml-mf-implicit-tutorial)

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
OPTIONS(
  model_type        = 'MATRIX_FACTORIZATION',
  feedback_type     = 'EXPLICIT',          -- or 'IMPLICIT'
  user_col          = 'user_id',
  item_col          = 'item_id',
  rating_col        = 'rating',            -- default 'rating'
  num_factors       = 34,
  l2_reg            = 9.83
  -- wals_alpha = 40   -- IMPLICIT only
) AS
SELECT user_id, item_id, rating
FROM `PROJECT_ID.DATASET.ratings`;
```
The training query must produce three columns: a user column, an item column, and a rating column. There is no `TRANSFORM` clause / feature engineering for this model type.

**Options (model-specific):**

| Option | Type | Required | Default | Range / Values | Description |
|--------|------|----------|---------|----------------|-------------|
| `model_type` | STRING | Yes | — | `'MATRIX_FACTORIZATION'` | Selects the model algorithm. |
| `feedback_type` | STRING | No | `'EXPLICIT'` | `'EXPLICIT'` \| `'IMPLICIT'` | EXPLICIT → ALS (user-supplied ratings); IMPLICIT → WALS (proxy signals like clicks/engagement). |
| `user_col` | STRING | No | `'user'` | column name | The user column in the input. |
| `item_col` | STRING | No | `'item'` | column name | The item column in the input. |
| `rating_col` | STRING | No | `'rating'` | column name | The rating/feedback column. Names the output column of `ML.RECOMMEND` (`predicted_\<rating_col\>`). |
| `num_factors` | INT64 | No | model-chosen | \>= 0 | Number of latent factors. Higher → more capacity, more cost/overfit risk. **HP-tunable** (`HPARAM_RANGE`/`HPARAM_CANDIDATES`). |
| `l2_reg` | FLOAT64 | No | `1.0` | \> 0 | L2 regularization strength. **HP-tunable**. |
| `wals_alpha` | FLOAT64 | No | `40` | \> 0 | IMPLICIT only: confidence weight on observed interactions. **HP-tunable**. Ignored for EXPLICIT. |
| `max_iterations` | INT64 | No | `20` | \>= 1 | Max training iterations. |
| `early_stop` | BOOL | No | `TRUE` | TRUE/FALSE | Stop when improvement \< `min_rel_progress`. |
| `min_rel_progress` | FLOAT64 | No | `0.01` | \> 0 | Minimum relative loss improvement to continue when `early_stop=TRUE`. |
| `data_split_method` | STRING | No | `'AUTO_SPLIT'` (`'RANDOM'` semantics) | `'AUTO_SPLIT'`,`'RANDOM'`,`'CUSTOM'`,`'SEQ'`,`'NO_SPLIT'` | How to carve out an eval set. |
| `data_split_eval_fraction` | FLOAT64 | No | `0.2` | 0–1 | Fraction reserved for evaluation. |
| `data_split_test_fraction` | FLOAT64 | No | — | 0–1 | Test fraction (used with HP tuning). |

**Supported lifecycle functions:**
- `ML.RECOMMEND` — primary inference function (predict ratings/confidence for user-item pairs).
- `ML.EVALUATE` — quality metrics (differ by feedback type, below).
- `ML.WEIGHTS` — returns the learned user and item latent factor vectors (the embeddings + intercept). Useful for similarity / nearest-neighbor item search.
- `ML.GENERATE_EMBEDDING` — extract the per-user / per-item factor embeddings from the trained MF model (in-scope here: lifecycle use of a BQML model, not the foundation-model use).
- `ML.TRAINING_INFO`, `ML.FEATURE_INFO` — training/iteration and input column stats.
- `ML.TRIAL_INFO` / `ML.EVALUATE(..., TRIAL_ID)` — when trained with hyperparameter tuning.
- Not applicable: `ML.PREDICT` (use `ML.RECOMMEND` instead), `ML.CONFUSION_MATRIX`, `ML.ROC_CURVE`, `ML.GLOBAL_EXPLAIN`, `ML.FEATURE_IMPORTANCE`, `ML.EXPLAIN_PREDICT`.

**ML.EVALUATE output metrics (this type):**
- **EXPLICIT** (regression-style): `mean_absolute_error`, `mean_squared_error`, `mean_squared_log_error`, `median_absolute_error`, `r2_score`, `explained_variance`.
- **IMPLICIT** (ranking-style): `mean_average_precision`, `mean_squared_error`, `normalized_discounted_cumulative_gain`, `average_rank`.

**Preprocessing support:** None. No `TRANSFORM` clause; input is the raw (user, item, rating) triple. Aggregate/derive your rating signal in the training `SELECT`.

**Hyperparameter tuning:** Supported. Tunable options: `num_factors`, `l2_reg`, and (IMPLICIT only) `wals_alpha`, via `HPARAM_RANGE` / `HPARAM_CANDIDATES` with `num_trials`. Default `hparam_tuning_objective`: `MEAN_SQUARED_ERROR` for EXPLICIT, `MEAN_AVERAGE_PRECISION` for IMPLICIT.

**Explainability / weights:** No feature attributions (`ML.GLOBAL_EXPLAIN` / `ML.EXPLAIN_PREDICT` / `ML.FEATURE_IMPORTANCE` do not apply; `enable_global_explain` is not used). The model's interpretability surface is `ML.WEIGHTS` (latent factor vectors for users and items) and the embeddings via `ML.GENERATE_EMBEDDING`.

**Best practices:**
- Choose `feedback_type` to match your data: explicit star ratings → EXPLICIT; behavioral proxies → IMPLICIT (and tune `wals_alpha`).
- For IMPLICIT, engineer the rating signal (e.g., capped session duration, view/purchase counts) in the training query.
- `ML.RECOMMEND` output scales as users × items — write results to a table rather than scanning interactively; filter to a user (or item) subset when you only need targeted recommendations.
- Use `ML.WEIGHTS` factor vectors for fast item-item similarity instead of recomputing full recommendation matrices.
- Tune `num_factors` and `l2_reg` together — more factors needs more regularization.

**Limitations:**
- **Pricing/slots:** Unlike every other BQML model type, `MATRIX_FACTORIZATION` cannot train under on-demand (per-byte) pricing. You must use a reservation / BigQuery Editions (capacity-based) slots. Evaluation and `ML.RECOMMEND` run as standard `QUERY` jobs.
- No `TRANSFORM` / automatic feature engineering.
- Output volume from `ML.RECOMMEND` can be very large (full sparse matrix).

**Locations:** Model-type availability varies by region; check [BigQuery ML locations](https://cloud.google.com/bigquery/docs/locations). Reservation availability in the model's region is required (see pricing note).

**BigFrames API:** `bigframes.ml.decomposition.MatrixFactorization(feedback_type=..., num_factors=..., user_col=..., item_col=..., rating_col=..., l2_reg=...)` — `.fit(X)` on a single (user, item, rating) DataFrame (all three columns together, no separate `y`), then `.score(X)` for evaluation metrics. **Verified: no `wals_alpha` parameter exists on this wrapper** (confirmed via the live installed constructor signature) — for `feedback_type='implicit'`, BigFrames always uses BigQuery ML's default `wals_alpha` (40) with no way to override it; use SQL directly if you need to tune it.

**Verified (`models/matrix_factorization/`):**
- **The on-demand pricing block is real and immediate** — `CREATE MODEL` without a reservation fails instantly with `"Training Matrix Factorization models is not available for on-demand usage."` This is the only model type in this project that hits this error.
- **The reservation's edition matters, not just its existence.** A `STANDARD` edition reservation still fails to train — with a *different* error: `"Using BQML related functionalities is disallowed in STANDARD edition."` `ENTERPRISE` (or higher) is required for any BQML training. A `STANDARD`-edition reservation is otherwise valid for regular `QUERY` jobs — it's specifically BQML that's blocked.
- **No capacity commitment is required** — a reservation created with `--edition=ENTERPRISE --autoscale_max_slots=N` (no `--capacity_commitment` flag; baseline `--slots=0`) is a pay-per-second, no-minimum-term BigQuery Editions reservation, and is sufficient to unblock `MATRIX_FACTORIZATION` training.
- **A freshly created reservation assignment needs time to propagate** — `CREATE MODEL` failed on the first attempt immediately after creating and assigning a brand-new reservation, and succeeded only after waiting (~90 seconds observed).
- **Real, measured cost:** building and validating this notebook (one base model, one 4-trial tuning job, one BigFrames retrain) consumed ~6.4 cumulative slot-hours under `ENTERPRISE` autoscale. Check current BigQuery Editions pricing before running — this is not a hypothetical cost like every other on-demand model type in this project.
- **Cold start does NOT error, contradicting the intuitive reading of "cannot recommend for absent users/items."** Calling `ML.RECOMMEND` with a `user_col`/`item_col` value never seen in training returns a full ranked list with no error — verified by comparing a confirmed real trained user's recommendations against an obviously fake user ID, which produced a completely different (but still populated) top-5 list, consistent with the unseen entity falling back to item-side bias/popularity alone rather than genuine personalization.
- **`ML.WEIGHTS` includes one extra row beyond per-user/per-item factors**: `processed_input=NULL`, `feature='global__INTERCEPT__'` — the single global bias term, separate from every user's/item's own intercept.
- **`ML.GENERATE_EMBEDDING` has a different argument count for this model type than PCA/AUTOENCODER.** It takes ONLY the model — no input table/query argument. Passing one errors: `"Function ML.GENERATE_EMBEDDING for MATRIX_FACTORIZATION models only expects 1 argument but 2 were passed."` It returns embeddings for every user AND item in the model in a single call (`processed_input`/`feature`/`ml_generate_embedding_result`), mirroring `ML.WEIGHTS`' shape rather than `ML.PREDICT`'s per-query-row shape.
- **The embedding array has `num_factors + 1` elements, not `num_factors`** — verified: with `num_factors=16`, `ML.GENERATE_EMBEDDING`'s array had 17 elements, one more than `ML.WEIGHTS`' `factor_weights` array for the same model (confirmed 16 elements there). The extra element is almost certainly the per-user/per-item `intercept` appended onto the raw factor vector. Don't assume the embedding array length equals `num_factors` for this model type.
- **`ML.EVALUATE` on a tuned model takes no `STRUCT(trial_id)` argument** — unlike `ML.RECOMMEND`, which accepts one. Calling `ML.EVALUATE(MODEL, STRUCT(trial_id AS trial_id))` errors (`"argument 2 must be a relation"`); calling `ML.EVALUATE(MODEL)` alone returns every trial's metrics in one result, one row per `trial_id`.
- **`ML.TRAINING_INFO`'s `eval_loss` column is `NULL` throughout** for this model type, unlike the supervised model types in this project.
- **Retraining shows measurable variance, similar to `KMEANS`/`RANDOM_FOREST_*`.** Retraining the identical `CREATE OR REPLACE MODEL` statement (same name, same SQL) does not reproduce `mean_average_precision` exactly — observed 0.873 and 0.860 across two runs. Unlike `PCA` (fully deterministic) or the `DNN_*` family (bit-for-bit reproducible under a fixed name), matrix factorization's WALS training has real run-to-run variance.
- **HP tuning produced a genuine, positive result in every run tested — though not with reproducible exact numbers.** 4 trials over `num_factors`/`l2_reg`/`wals_alpha` beat the untuned baseline both times, but the specific winning config and margin varied: one run's best trial reached `mean_average_precision=0.899` against a `0.860` baseline; a separate run's best trial reached `0.915` against a `0.873` baseline (same `num_factors`/`l2_reg`, a different `wals_alpha`). The qualitative finding — tuning beats the untuned baseline — held both times; the exact numbers didn't. A real contrast either way to `models/autoencoder/`'s equally-sized 4-trial search, which failed to beat its own untuned baseline at all.

**Repo example (tested):** `bigquery-ml/models/matrix_factorization/` — full lifecycle on `bigquery-public-data.google_analytics_sample` (IMPLICIT feedback), including the temporary-reservation setup/teardown pattern this model type forces on you. `bigquery-ml/workflows/recommendation/` then applies it end-to-end. The on-demand pricing exception is documented in *Pricing/slots* and *Limitations* above — this is the one model type that cannot train under on-demand pricing at all.

---

### `ML.RECOMMEND` (inference function for this model type)

**Type:** Table-valued function. **Applies to:** `MATRIX_FACTORIZATION` models only.

**Syntax:**
```sql
ML.RECOMMEND(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`
  [, { TABLE `PROJECT_ID.DATASET.TABLE` | (query_statement) }]
  [, STRUCT(trial_id AS trial_id)]
)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model | Yes | — | The trained matrix factorization model. |
| `TABLE` / `query_statement` | table/query | No | all user-item pairs | Optional input. If it has only the user column → all items scored for those users; only the item column → all users scored for those items; both → that specific pair. User/item column names and types must match the model. |
| `trial_id` | INT64 | No | optimal trial | Only when the model was trained with HP tuning; selects which trial to use. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `\<user_col\>` | (matches input) | The user. |
| `\<item_col\>` | (matches input) | The item. |
| `predicted_\<rating_col\>` | FLOAT64 | EXPLICIT models: predicted rating (≈ the input rating range; values just outside are normal). |
| `predicted_\<rating_col\>_confidence` | FLOAT64 | IMPLICIT models: relative confidence (≈ 0–1 if converged). |

**Examples:**
```sql
-- Every user-item pair (no input data; can be very large)
SELECT * FROM ML.RECOMMEND(MODEL `PROJECT_ID.DATASET.MODEL_NAME`);

-- Top recommendations for one user (EXPLICIT model)
SELECT * FROM ML.RECOMMEND(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  (SELECT 'user_123' AS user_id))
ORDER BY predicted_rating DESC
LIMIT 5;

-- IMPLICIT model: order by confidence
SELECT * FROM ML.RECOMMEND(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  (SELECT 'user_123' AS user_id))
ORDER BY predicted_rating_confidence DESC
LIMIT 5;
```

**Best practices:** Save large outputs to a table; filter to target users/items; for similarity use cases prefer `ML.WEIGHTS` factor vectors.
**Limitations:** Output can be huge (users × items); cannot recommend for unseen users/items.
**BigFrames API:** `MatrixFactorization.predict()`.


---
