# `ML.CENTROIDS`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlcentroids`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlcentroids)

- **Description:** Returns the learned centroid (cluster center) coordinates of a trained `KMEANS` model — one row per feature per centroid, so you can inspect what each cluster "looks like."
- **Use cases:**
  - Profile/interpret clusters by comparing each centroid's feature values.
  - Compare centroids across hyperparameter-tuning trials (one `trial_id` per tuned model).
  - Feed centroid coordinates into downstream segmentation/labeling logic.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-centroids
- **Type:** Table-valued function (model weights function).
- **Applies to models:** `KMEANS` only.

**Syntax:**
```sql
SELECT *
FROM ML.CENTROIDS(MODEL `PROJECT_ID.DATASET.MODEL_NAME`
  [, STRUCT(standardize AS standardize)]);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model ref | Yes | — | A trained `KMEANS` model. |
| `standardize` | BOOL | No | `TRUE` | Whether to return centroid feature values in standardized (`TRUE`) or original (`FALSE`) space. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `centroid_id` | INT64 | The cluster (centroid) identifier. |
| `feature` | STRING | The feature/column name. |
| `numerical_value` | FLOAT64 | Centroid value for numeric features (else NULL). |
| `categorical_value` | ARRAY\<STRUCT\<category STRING, value FLOAT64\>\> | Centroid values for categorical (one-hot) features. |
| `trial_id` | INT64 | Present only for hyperparameter-tuned models; identifies the trial. |

**Best practices:** Use `standardize = FALSE` to read centroids in the original feature units when profiling clusters for business stakeholders.
**Limitations:** `KMEANS` only — not valid for PCA/autoencoder/MF or supervised models. Numeric vs. categorical features land in separate columns; `UNNEST(categorical_value)` to flatten one-hot categories.
**BigFrames API:** `bigframes.ml.cluster.KMeans().cluster_centers_` (centroid attribute).
**Repo example (tested):**
- `bigquery-ml/models/kmeans/kmeans.sql` (Example 4) — one row per (`centroid_id`, `feature`) `ORDER BY centroid_id, feature`, read as the interpretation step: the centroid with the highest body-mass and flipper-length coordinates is the large-species cluster. Because `KMEANS` is non-deterministic (Example 7), read the profile off the coordinates, not off a remembered `centroid_id`.
- `bigquery-ml/workflows/customer_segmentation/customer_segmentation.sql` (Step 3) — the same call on RFM features, feeding the aggregated segment profiles in Step 4.
- On a hyperparameter-tuned model the output also carries `trial_id`, so the row count multiplies by the number of trials (one row per feature x centroid x trial) — see `models/kmeans/kmeans.sql`'s tuning example for the tuned variant.

---
