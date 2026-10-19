# `ML.PRINCIPAL_COMPONENTS`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlprincipal_components`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlprincipal_components)

- **Description:** Returns the principal components (eigenvectors) of a trained `PCA` model — the per-feature loadings that define each component direction.
- **Use cases:**
  - Interpret which original features dominate each component (loadings).
  - Reconstruct/inspect the linear transform the model applies.
  - Combine with `ML.PRINCIPAL_COMPONENT_INFO` (eigenvalues) to rank components.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-principal-components
- **Type:** Table-valued function (model weights function).
- **Applies to models:** `PCA` only.

**Syntax:**
```sql
SELECT *
FROM ML.PRINCIPAL_COMPONENTS(MODEL `PROJECT_ID.DATASET.MODEL_NAME`);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model ref | Yes | — | A trained `PCA` model. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `principal_component_id` | INT64 | The principal component identifier (0-based). |
| `feature` | STRING | The feature/column name. |
| `numerical_value` | FLOAT64 | Loading for numeric features (else NULL). |
| `categorical_value` | ARRAY\<STRUCT\<category STRING, value FLOAT64\>\> | Loadings for categorical (one-hot) features. |

**Best practices:** Output is ordered descending by eigenvalue (most-explanatory component first). Join/compare against `ML.PRINCIPAL_COMPONENT_INFO` on `principal_component_id` to weight loadings by variance explained.
**Limitations:** `PCA` only. Categorical features are one-hot encoded — flatten `categorical_value` with `UNNEST`.
**BigFrames API:** `bigframes.ml.decomposition.PCA().components_`.
**Repo example (tested):** `bigquery-ml/models/pca/pca.sql` (Example 4) — one row per (`principal_component_id`, `feature`), so the row count is features x components. Two things it pins down: **`principal_component_id` is 0-indexed**, unlike `KMEANS`' 1-indexed `centroid_id` — indexing conventions are not consistent across unsupervised model types — and how to read a component as an axis: on the penguins model, component 0 loads negative on body mass, culmen length, and flipper length but positive on culmen depth, i.e. a body-size axis.

---
