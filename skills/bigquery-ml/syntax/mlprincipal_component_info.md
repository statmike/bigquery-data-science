# `ML.PRINCIPAL_COMPONENT_INFO`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlprincipal_component_info`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlprincipal_component_info)

- **Description:** Returns per-component statistics (eigenvalue, explained variance ratio, cumulative explained variance ratio) for a trained `PCA` model.
- **Use cases:**
  - Decide how many components to keep (scree / cumulative-variance analysis).
  - Quantify how much information each component captures.
  - Pair with `ML.PRINCIPAL_COMPONENTS` to interpret loadings weighted by variance.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-principal-component-info
- **Type:** Table-valued function (model weights function).
- **Applies to models:** `PCA` only.

**Syntax:**
```sql
SELECT *
FROM ML.PRINCIPAL_COMPONENT_INFO(MODEL `PROJECT_ID.DATASET.MODEL_NAME`);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model ref | Yes | — | A trained `PCA` model. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `principal_component_id` | INT64 | The principal component (rows ordered descending by eigenvalue). |
| `eigenvalue` | FLOAT64 | Scaling factor of the eigenvector (same concept as the component's variance). |
| `explained_variance_ratio` | FLOAT64 | This component's variance / total variance. |
| `cumulative_explained_variance_ratio` | FLOAT64 | Running sum of `explained_variance_ratio` through this component. |

**Best practices:** Use `cumulative_explained_variance_ratio` to pick a component count. Note `ML.EVALUATE` on a PCA model returns the single complementary metric `total_explained_variance_ratio`.
**Limitations:** `PCA` only.
**BigFrames API:** `bigframes.ml.decomposition.PCA().explained_variance_` / `.explained_variance_ratio_`.
**Repo example (tested):**
- `bigquery-ml/models/pca/pca.sql` (Example 5) — one row per component; on the penguins model component 0 alone explains ~69% of variance and adding component 1 brings the cumulative total to ~88%, which is how the elbow is read. Example 10 then targets `pca_explained_variance_ratio = 0.90` and BigQuery ML picks 3 components (2 reach only ~0.88, just short), landing at ~0.97 cumulative.
- **GOTCHA, verified live — prefer a fixed component count over a variance target when downstream results must be stable.** `bigquery-ml/workflows/anomaly_fraud_detection/anomaly_fraud_detection.sql` (Step 1) trains PCA on `ulb_fraud_detection`: with `pca_explained_variance_ratio` (a *variable* component count chosen to hit a variance target), three runs of the identical `CREATE OR REPLACE MODEL` statement gave `ML.DETECT_ANOMALIES` true-positive counts of 3, 235, and 279 out of 492 real frauds — while `total_explained_variance_ratio` stayed bit-for-bit stable at ~0.95473 every time. Near-threshold eigenvalues flip which components get retained, which swings per-row reconstruction error even though the aggregate variance captured looks identical. Switching to a fixed `num_principal_components = 10` was substantially more stable (TP 114-124 across independent runs). The aggregate metric is not a stability check.

---
