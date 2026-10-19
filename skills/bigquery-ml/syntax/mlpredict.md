# `ML.PREDICT`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlpredict`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlpredict)

- **Description:** Generates predictions (inference) from a trained model over an input table or query. Output has one row per input row, carrying the model's prediction columns plus pass-through input columns. Any `TRANSFORM` clause baked into the model is reapplied automatically — no need to repeat preprocessing.
- **Use cases:**
  - Batch-score new data with a classification/regression model.
  - Assign cluster membership with k-means; project rows onto principal components with PCA.
  - Produce the inputs for downstream `ML.EXPLAIN_PREDICT` / business logic.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-predict
- **Type:** Table-valued function.
- **Applies to models:** `LINEAR_REG`, `LOGISTIC_REG`, `BOOSTED_TREE_*`, `RANDOM_FOREST_*`, `DNN_*`, `WIDE_AND_DEEP_*`, `KMEANS`, `PCA`, `AUTOENCODER`, `AUTOML_*`, and imported models (`TENSORFLOW`, `TENSORFLOW_LITE`, `ONNX`, `XGBOOST`). Note: time-series models use `ML.FORECAST`, matrix factorization uses `ML.RECOMMEND`.

**Syntax:**
```sql
ML.PREDICT(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  { TABLE `PROJECT_ID.DATASET.TABLE` | (query_statement) }
  [, STRUCT(threshold_value AS threshold
            [, keep_original_columns_value AS keep_original_columns]
            [, trial_id AS trial_id])]
)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model ref | Yes | — | The trained model used for inference. |
| `TABLE` / `query_statement` | table / subquery | Yes | — | Rows to score. Input columns must match the model's features (or, for a `TRANSFORM` model, only the raw `TRANSFORM` inputs). Unused columns are passed through. |
| `threshold` | FLOAT64 | No | 0.5 | Binary-classification cutoff. Classification models only. |
| `keep_original_columns` | BOOL | No | FALSE | k-means only — also emit the original (non-standardized) feature columns alongside the cluster output. |
| `trial_id` | INT64 | No | optimal trial | Selects a hyperparameter-tuning trial. Only valid when trained with `NUM_TRIALS`. |

**Outputs (vary by model type; all input columns are appended):**

| Model task | ML.PREDICT output columns |
|---|---|
| Classification | `predicted_<label>` (chosen class); `predicted_<label>_probs` — `ARRAY<STRUCT<label, prob>>` of per-class probabilities |
| Regression | `predicted_<label>` (FLOAT64) |
| K-means | `centroid_id` (INT64); `nearest_centroids_distance` — `ARRAY<STRUCT<centroid_id, distance>>` for the nearest min(`num_clusters`, 5) clusters |
| PCA | `principal_component_<index>` — projection of the row onto each kept component |
| Autoencoder | `latent_col_<index>` — one column per bottleneck dimension (encoded low-dimensional representation); original input columns appended after |

**Best practices:**
- Prefer the `TRANSFORM` clause at `CREATE MODEL` time so preprocessing travels with the model and `ML.PREDICT` stays a plain `SELECT *` — no manual feature engineering at inference.
- Select only the columns you need (`predicted_<label>`, `predicted_<label>_probs`) instead of `SELECT *` on wide tables to cut bytes scanned.
- For k-means segmentation, read the closest distance with `nearest_centroids_distance[OFFSET(0)].distance`.

**Limitations:**
- Not for time-series (`ML.FORECAST`) or matrix-factorization (`ML.RECOMMEND`) models.
- Object-table / image inputs must be decoded with `ML.DECODE_IMAGE`; imported-model inputs must coerce to the model's expected types. **An `ML.PREDICT` whose input expression contains any of the four image functions inherits their reservation requirement** and fails on on-demand pricing — see [model-free-functions.md](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#image-preprocessing-functions-mldecode_image-mlresize_image-mlconvert_image_type-mlconvert_color_space) and [`functions/image/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/image). The same applies to a `TRANSFORM` clause that embeds them.
- `keep_original_columns` applies to k-means only.
- **GOTCHA, verified live: joining multiple models' `ML.PREDICT` outputs back together on raw feature columns (instead of a stable row ID) can silently fan out.** When stacking several models' predictions into one meta-feature table (see `workflows/ensembling/`), joining on the full feature-column set duplicated rows — a 6,587-row split fanned out to 11,027 rows, because different source rows shared identical values across every feature column. Add a synthetic `ROW_NUMBER()` row ID when the source table first materializes (before training any model) and join every downstream `ML.PREDICT` output on that instead — then sanity-check the joined row count against the expected pre-join count rather than assuming a 1:1 join.

**BigFrames API:** `model.predict(X)` on a `bigframes.ml` estimator returns a DataFrame with the predicted columns.

**Repo example (tested):**
- `bigquery-ml/models/logistic_regression/logistic_regression.sql` (Example 5) — `predicted_income_bracket` + `predicted_income_bracket_probs`.
- `bigquery-ml/models/kmeans/kmeans.sql` (Example 3) — `CENTROID_ID` plus `NEAREST_CENTROIDS_DISTANCE` (distance to every centroid, nearest-first), with a non-training column passed through as an external check on the clusters.
- `bigquery-ml/models/pca/pca.sql` (Example 3) — `ML.PREDICT` projecting rows onto `principal_component_1..N`.
- `bigquery-ml/models/autoencoder/autoencoder.sql` (Example 3) — `ML.PREDICT` returning `latent_col_*` for the autoencoder, used to aggregate min/max/zero-count per latent column and catch a collapsed unit; paired with `ML.RECONSTRUCTION_LOSS` (Example 6) for the per-row view.
- `bigquery-ml/workflows/customer_segmentation/customer_segmentation.sql` (Step 4) — `ML.PREDICT` over the full RFM table, aggregated by `CENTROID_ID` into segment profiles. Its Step 2 comment carries the matching gotcha: keep the ID column out of the training query, then join it back via `ML.PREDICT`, or it becomes a raw unscaled feature that distorts every distance.
- `bigquery-ml/workflows/ensembling/ensembling.ipynb` — `ML.PREDICT` from 3 heterogeneous model types (`LOGISTIC_REG`/`BOOSTED_TREE_CLASSIFIER`/`RANDOM_FOREST_CLASSIFIER`) joined into one meta-feature table for a stacked ensemble; the source of the row-ID join-fanout gotcha above.


---
