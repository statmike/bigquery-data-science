# `PCA`

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#pca`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#pca)

- **Description:** Principal Component Analysis — an unsupervised, linear dimensionality-reduction model. It transforms a set of correlated numeric/categorical features into a smaller set of orthogonal (uncorrelated) **principal components** ordered by the amount of variance each explains, preserving as much information as possible. Components are derived from the eigendecomposition of the (optionally scaled) feature covariance matrix.
- **When to use:**
  - Reduce dimensionality before training another model, or for visualization of high-dimensional data.
  - Unsupervised **anomaly detection** via `ML.DETECT_ANOMALIES` (reconstruction-loss based), e.g. fraud detection without labels.
  - Generate compact embeddings of structured rows for downstream similarity / clustering.
  - Inspect feature loadings to understand which features drive the most variance.
- **Category:** unsupervised (dimensionality reduction).
- **Connection required:** No. (A connection is only involved if you add `MODEL_REGISTRY = 'VERTEX_AI'` for registry/serving, or `EXPORT MODEL` to GCS — neither is required to train or use the model in BQ.)
- **Status:** GA.
- **documentation:** [CREATE MODEL for PCA](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-pca) · weights/output functions: [ML.PRINCIPAL_COMPONENTS](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-principal-components), [ML.PRINCIPAL_COMPONENT_INFO](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-principal-component-info)

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
OPTIONS(
  model_type = 'PCA',
  -- specify EXACTLY ONE of the next two:
  num_principal_components = 2,            -- OR
  -- pca_explained_variance_ratio = 0.90,
  scale_features = TRUE,
  pca_solver = 'AUTO'
) AS
SELECT * EXCEPT(id_col, label_col)         -- PCA ignores no column automatically; SELECT only the features
FROM `PROJECT_ID.DATASET.TABLE`
WHERE splits = 'TRAIN';
```

**Options (model-specific):**

| Option | Type | Required | Default | Range / Values | Description |
|--------|------|----------|---------|----------------|-------------|
| `model_type` | STRING | Yes | — | `'PCA'` | Selects the PCA algorithm. |
| `num_principal_components` | INT64 | One of these two | — | 1 .. 10,000 | Number of components to keep. Mutually exclusive with `pca_explained_variance_ratio`. |
| `pca_explained_variance_ratio` | FLOAT64 | One of these two | — | (0, 1) | Keep the fewest components whose cumulative explained-variance ratio meets this target (computed under the 10,000-component cap). Mutually exclusive with `num_principal_components`. |
| `scale_features` | BOOL | No | `TRUE` | `TRUE` \| `FALSE` | Scale numeric features to unit variance. Features are always mean-centered regardless; categoricals are one-hot encoded. |
| `pca_solver` | STRING | No | `'AUTO'` | `'FULL'` \| `'RANDOMIZED'` \| `'AUTO'` | Eigendecomposition strategy. `FULL` = exact; `RANDOMIZED` = approximate (large cardinality); `AUTO` picks based on post-one-hot feature cardinality (threshold typically ~1,000–1,500). |

You must specify **exactly one** of `num_principal_components` / `pca_explained_variance_ratio`. None of the PCA options accept `HPARAM_RANGE` / `HPARAM_CANDIDATES` (no HP tuning — see below). Registry/serving options (`model_registry`, `vertex_ai_model_id`, `vertex_ai_model_version_aliases`) are model-agnostic and shown working in the repo example.

**Supported lifecycle functions:** `ML.EVALUATE`, `ML.PREDICT` (projects rows onto the components), `ML.DETECT_ANOMALIES` (reconstruction-loss anomaly detection with a `contamination` STRUCT param), `ML.GENERATE_EMBEDDING` / `AI.GENERATE_EMBEDDING` (in-scope here: extract embeddings FROM the trained PCA model), `ML.PRINCIPAL_COMPONENTS`, `ML.PRINCIPAL_COMPONENT_INFO`, `ML.FEATURE_INFO`, `ML.TRAINING_INFO`, `EXPORT MODEL`. Not applicable: `ML.CONFUSION_MATRIX`, `ML.ROC_CURVE`, `ML.GLOBAL_EXPLAIN`, `ML.WEIGHTS`, `ML.FEATURE_IMPORTANCE`, `ML.CENTROIDS`, `ML.RECOMMEND`, `ML.FORECAST`.

**ML.EVALUATE output metrics (this type):**

| Column | Description |
|--------|-------------|
| `total_explained_variance_ratio` | FLOAT64 — fraction of total variance captured by the retained components. |

**Preprocessing support:** Automatic — numeric features are mean-centered (and unit-scaled when `scale_features = TRUE`); categorical features are automatically one-hot encoded. `TRANSFORM` is supported for custom feature engineering and the transforms are stored with the model so they auto-apply at `ML.PREDICT` / `ML.DETECT_ANOMALIES` time.

**Hyperparameter tuning:** Not supported (`num_trials` / HP tuning is N/A for PCA). To search over component counts, train multiple models or use `pca_explained_variance_ratio` to let the variance target choose the count.

**Explainability / weights:** Use the dedicated **weights functions** instead of the standard explainers. `ML.PRINCIPAL_COMPONENTS` returns the per-feature loadings (eigenvectors) for each component; `ML.PRINCIPAL_COMPONENT_INFO` returns each component's `eigenvalue`, `explained_variance_ratio`, and `cumulative_explained_variance_ratio`. `ML.GLOBAL_EXPLAIN` / `ML.WEIGHTS` / `ML.FEATURE_IMPORTANCE` do not apply.

**Best practices:**
- Set `scale_features = TRUE` (default) when features are on different units/scales so high-variance features don't dominate.
- Prefer `pca_explained_variance_ratio` (e.g. 0.90) when you care about retained information rather than a fixed component count.
- For anomaly detection, set `contamination` to your expected outlier rate (e.g. the training-set positive rate) — the repo example derives this from the training fraud rate.
- Use `ML.PRINCIPAL_COMPONENT_INFO` to choose a sensible component count via the cumulative explained-variance "elbow."

**Limitations:**
- Maximum 10,000 principal components.
- `FULL`/`AUTO` solvers cap post-one-hot feature cardinality dynamically (~1,000–1,500); high-cardinality categorical inputs can force `RANDOMIZED`.
- Exactly one of `num_principal_components` / `pca_explained_variance_ratio` must be set.
- Linear method only — does not capture nonlinear structure (consider `AUTOENCODER` for nonlinear dimensionality reduction / anomaly detection).
- No `ML.EVALUATE` label-based metrics; evaluation is variance-based only.

**Locations:** Available in all BigQuery ML regions/multi-regions. `MODEL_REGISTRY = 'VERTEX_AI'` registration and online serving require a Vertex AI-supported region (repo example uses `us-central1`).

**BigFrames API:** `bigframes.ml.decomposition.PCA` (`n_components` maps to `num_principal_components`, `svd_solver` maps to `pca_solver`). **Verified: `.fit(X)` then `.predict(X)`** — unlike scikit-learn, there is no `.transform()`/`.fit_transform()`; `.predict()` returns the projected components, matching `ML.PREDICT`'s convention. `.score(X)` returns `total_explained_variance_ratio`, matching `ML.EVALUATE` (`models/pca/`).

**Verified (`models/pca/`):**
- **PCA is fully deterministic** — retraining the identical `CREATE OR REPLACE MODEL` statement (same SQL, same options) reproduces `total_explained_variance_ratio` bit-for-bit every time. Unlike `KMEANS` (see its entry above), PCA is a closed-form eigendecomposition with no random initialization, so there's no retraining variance to guard against. A third independent confirmation: training via `bigframes.ml.decomposition.PCA` — a completely different, independently-named model — reproduces the exact same value again, a contrast to `KMEANS`, where BigFrames' independently-trained model produces yet a different value each time.
- **MAJOR NUANCE (verified live, `workflows/anomaly_fraud_detection/`):** the determinism above covers `ML.EVALUATE`'s own metric — it does **not** guarantee stable *downstream* `ML.DETECT_ANOMALIES` results when using `pca_explained_variance_ratio` (a variable component **count**, chosen to hit a variance target) instead of a fixed `num_principal_components`. On a 30-feature, 284K-row real dataset, three otherwise-identical retrainings with `pca_explained_variance_ratio = 0.95` produced true-positive counts of 3, 235, and 279 (out of 492 known anomalies) — even though `total_explained_variance_ratio` stayed bit-for-bit stable (~0.95473) across all three. Near-threshold eigenvalues can flip exactly which components get retained between runs, which swings per-row reconstruction error dramatically despite the aggregate captured variance looking identical. **Mitigation:** use a fixed `num_principal_components` instead — substantially more stable across retrainings (two independent runs both landed in a TP=114-132 range, versus the 3-279 swing above).
- **`principal_component_id` (in `ML.PRINCIPAL_COMPONENTS`/`ML.PRINCIPAL_COMPONENT_INFO`) is 0-indexed** (0, 1, 2, ...) — unlike `KMEANS`' `centroid_id`, which is 1-indexed, and unlike `ML.PREDICT`'s own output columns (`principal_component_1`, `principal_component_2`, ...), which are 1-indexed. Don't assume a consistent indexing convention across unsupervised model types or even within the same model type's own functions.
- **`ML.DETECT_ANOMALIES` requires the 3rd (input-data) argument for PCA**, same as `KMEANS` — see the general `ML.DETECT_ANOMALIES` entry.
- **`ML.GENERATE_EMBEDDING` on a PCA model** wraps `ML.PREDICT`'s projection into a single `ml_generate_embedding_result` ARRAY<FLOAT> column; the array values match `ML.PREDICT`'s `principal_component_1`/`principal_component_2` columns exactly, in order.

**Repo example (tested):**
- `bigquery-ml/models/pca/` — `model_type='PCA'` on `penguins`, covering `ML.EVALUATE` (`total_explained_variance_ratio`), `ML.PRINCIPAL_COMPONENT_INFO`, `ML.PRINCIPAL_COMPONENTS`, `ML.PREDICT` (per-row component projections), `ML.GENERATE_EMBEDDING`, `ML.FEATURE_INFO`, and `ML.DETECT_ANOMALIES` with an explicit `contamination`.
- `bigquery-ml/workflows/anomaly_fraud_detection/anomaly_fraud_detection.ipynb` — the same technique used for real fraud detection on `bigquery-public-data.ml_datasets.ulb_fraud_detection`, with `contamination` set from the training fraud rate and precision/recall scored against the true label, alongside `AUTOENCODER` and a supervised `BOOSTED_TREE_CLASSIFIER`.
- `bigquery-ml/functions/distance/` — uses a `PCA` model's projections as the input to `ML.DISTANCE` / `ML.LP_NORM` / `ML.NORMALIZER`.
- `EXPORT MODEL` (`PCA` exports as a TensorFlow SavedModel) and Endpoint deployment: `bigquery-ml/models/export/` and `bigquery-ml/models/remote/`.

**Repo example (tested):** `bigquery-ml/workflows/anomaly_fraud_detection/anomaly_fraud_detection.ipynb` — trains `PCA` with `num_principal_components=10` on `bigquery-public-data.ml_datasets.ulb_fraud_detection` (the real ULB/Kaggle fraud dataset, 492 genuine fraud cases) and measures real precision/recall against the true `Class` label — the source of the `pca_explained_variance_ratio` non-determinism finding above; contrasts with `AUTOENCODER` and a supervised `BOOSTED_TREE_CLASSIFIER`.


---
