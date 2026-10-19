# `KMEANS`

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#kmeans`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#kmeans)

- **Description:** Unsupervised clustering algorithm that partitions `n` observations into `k` clusters, assigning each row to the cluster with the nearest centroid (mean). Trained with `CREATE MODEL ... OPTIONS(model_type='KMEANS')`. Beyond clustering, a trained k-means model also powers `ML.DETECT_ANOMALIES` (rows far from their nearest centroid are anomalies).
- **When to use:**
  - Customer / market segmentation and grouping unlabeled records.
  - Exploratory analysis to discover natural structure in data.
  - Unsupervised anomaly / outlier detection (distance-to-centroid based).
  - When you have no labels and want fast, in-SQL clustering at BigQuery scale.
- **Category:** unsupervised (clustering).
- **Connection required:** No. (A connection is only needed for unrelated remote/imported models, not for k-means.)
- **Status:** GA.
- **Documentation:** [CREATE MODEL for K-means](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-kmeans) · journey/tutorial group: [k-means tutorial (London bike hires)](https://cloud.google.com/bigquery/docs/kmeans-tutorial) · [E2E user journey for models](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-e2e-journey)

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
[TRANSFORM(...)]
OPTIONS(
  model_type           = 'KMEANS',
  num_clusters         = 4,            -- or HPARAM_RANGE(2, 100) / HPARAM_CANDIDATES([...])
  kmeans_init_method   = 'KMEANS++',
  distance_type        = 'EUCLIDEAN',
  standardize_features = TRUE,
  max_iterations       = 20,
  early_stop           = TRUE,
  min_rel_progress     = 0.01
) AS
SELECT * EXCEPT(id_col, label_col)
FROM `PROJECT_ID.DATASET.TABLE`;
```

**Options (model-specific):**

| Option | Type | Required | Default | Range / Values | Description |
|--------|------|----------|---------|----------------|-------------|
| `model_type` | STRING | Yes | — | `'KMEANS'` | Selects k-means. |
| `num_clusters` | INT64 | No | reasonable default from row count | `2`–`100` (typical) | Number of clusters `k`. Accepts `HPARAM_RANGE`/`HPARAM_CANDIDATES` for tuning. |
| `kmeans_init_method` | STRING | No | `'RANDOM'` | `'RANDOM'`, `'KMEANS++'`, `'CUSTOM'` | Centroid seeding. `KMEANS++` gives slower init but faster convergence and repeatably better results. |
| `kmeans_init_col` | STRING | No | — | name of a `BOOL` column | Only with `CUSTOM`. Rows where the column is `TRUE` become initial centroids; count of `TRUE` rows must equal `num_clusters`. Auto-excluded as a feature. |
| `distance_type` | STRING | No | `'EUCLIDEAN'` | `'EUCLIDEAN'`, `'COSINE'` | Distance metric between points. |
| `standardize_features` | BOOL | No | `TRUE` | `TRUE`/`FALSE` | Standardize numeric features before clustering (recommended; scale-sensitive). |
| `max_iterations` | INT64 | No | `20` | \<positive int\> | Max training iterations. |
| `min_rel_progress` | FLOAT64 | No | `0.01` | \<float\> | Min relative loss improvement to continue when `early_stop=TRUE`. |
| `early_stop` | BOOL | No | `TRUE` | `TRUE`/`FALSE` | Stop early once improvement \< `min_rel_progress`. |
| `warm_start` | BOOL | No | `FALSE` | `TRUE`/`FALSE` | Continue training from existing centroids on retrain. |

HP-tuning-eligible option: `num_clusters` (use `HPARAM_RANGE`/`HPARAM_CANDIDATES`), plus tuning controls `num_trials`, `max_parallel_trials`, `hparam_tuning_algorithm`, `hparam_tuning_objectives`.

**Supported lifecycle functions:** `ML.EVALUATE`, `ML.PREDICT` (returns `CENTROID_ID` + `NEAREST_CENTROIDS_DISTANCE`), `ML.CENTROIDS` (centroid coordinates per feature), `ML.DETECT_ANOMALIES`, `ML.FEATURE_INFO`, `ML.TRIAL_INFO` (HP tuning), `EXPORT MODEL` (exports as TensorFlow SavedModel). Not applicable: `ML.CONFUSION_MATRIX`, `ML.ROC_CURVE`, `ML.WEIGHTS`/`ML.ADVANCED_WEIGHTS`, `ML.GLOBAL_EXPLAIN`, `ML.FEATURE_IMPORTANCE` (no coefficients/attributions for clustering).

**ML.EVALUATE output metrics (this type):** `davies_bouldin_index`, `mean_squared_distance`. (With HP tuning, a `trial_id` column is prepended.)

**Preprocessing support:** automatic (BQML standardizes numeric features by default via `standardize_features`); `TRANSFORM` clause supported for in-model feature engineering.

**Hyperparameter tuning:** Supported. Primary tunable option is `num_clusters` (e.g. `HPARAM_RANGE(2, 100)`); objective `davies_bouldin_index` (minimize). Uses Vertex AI Vizier (`VIZIER_DEFAULT`).

**Explainability / weights:** None of `ML.WEIGHTS`/`ML.ADVANCED_WEIGHTS`/`ML.GLOBAL_EXPLAIN`/`ML.FEATURE_IMPORTANCE`/`ML.EXPLAIN_PREDICT` apply. Interpret clusters via `ML.CENTROIDS` (per-feature centroid values) and `ML.PREDICT` distances. `enable_global_explain` is not applicable.

**Best practices:**
- Keep `standardize_features = TRUE` (default) — k-means is scale-sensitive.
- Prefer `kmeans_init_method = 'KMEANS++'` for stable, better-converging results.
- Tune `num_clusters` with `HPARAM_RANGE` + `davies_bouldin_index` objective rather than guessing `k` — but verified (`models/kmeans/`) that this is itself subject to the non-determinism below: one run of `HPARAM_RANGE(2, 10)` selected the domain-correct answer (3, matching the 3 real penguin species in the training data) as optimal; a separate run of the identical tuning config selected 2 instead. Don't treat a single tuning run's chosen `num_clusters` as definitive — if the choice matters, tune more than once (or with more trials) and look for a value that wins consistently.
- HP tuning can be expensive/slow (e.g. tens of trials over hundreds of thousands of rows ran ~46 min in the repo example) — bound `num_trials` and use `max_parallel_trials`.
- Exclude id/label columns from the feature set (`SELECT * EXCEPT(...)`).
- **Verified: K-means retraining is genuinely non-deterministic, even with `kmeans_init_method = 'KMEANS++'` (`models/kmeans/`).** Retraining the identical `CREATE OR REPLACE MODEL` statement (same SQL, same options, no seed exposed) multiple times produced meaningfully different `davies_bouldin_index` values each time (observed range ~0.87–1.02 on a 342-row dataset) and different specific cluster-to-external-label alignment (which cluster cleanly separates a given group shifted between runs) — a third independent training via `bigframes.ml.cluster.KMeans` on the same config reproduced yet a different value again. **Practical implication: a single before/after comparison (e.g. "does adding this feature improve clustering?") is not reliable evidence of a causal effect** — the same magnitude of change can come from ordinary retraining variance. Retrain each configuration multiple times and look at the range before drawing a conclusion.
- **Verified, still true independent of the point above: a lower `davies_bouldin_index` does NOT by itself mean more meaningful clusters.** It only measures internal cluster separation/compactness in whatever feature space you give it — it says nothing about whether clusters line up with any domain-meaningful grouping. When you have any external signal to check against (even one not used in training), use it — don't rely on the intrinsic metric alone to judge whether a clustering is useful, and combine it with the non-determinism point above (check the metric's range across retrains, not a single value) before trusting any comparison.

**Limitations:**
- No supervised metrics or feature attributions (unsupervised).
- `kmeans_init_col` (CUSTOM) requires exactly `num_clusters` TRUE rows.
- `COSINE` distance changes geometry — choose deliberately.
- **Verified gotcha: `ML.DETECT_ANOMALIES`'s input-data argument is REQUIRED for `KMEANS`, not optional.** Calling it with only `(MODEL, STRUCT(contamination))` (2 arguments) errors immediately: `"DETECT_ANOMALIES expects 3 arguments for KMEANS models but 2 were passed."` Always pass the scoring data as the 3rd argument. Verified since on `models/pca/` and `models/autoencoder/` as well: the requirement is not KMEANS-specific — it holds for all three IID model types, with the model name substituted into the same error. See the general `ML.DETECT_ANOMALIES` entry, whose syntax block shows the 3-argument form but does not mark it mandatory.
- HP-tuned models return per-trial rows in `ML.EVALUATE`/`ML.PREDICT`; downstream queries must handle/filter `trial_id`.

**Locations:** Available in all BigQuery ML regions/multi-regions; no special location constraint (no connection required).

**BigFrames API:** `bigframes.ml.cluster.KMeans` — e.g. `KMeans(n_clusters=4).fit(X)` then `.predict(X)`.

**Repo example (tested):**
- `bigquery-ml/models/kmeans/` — `KMEANS` on `penguins` with `num_clusters` swept via `HPARAM_RANGE` and `standardize_features=TRUE`, tuned across trials; covers `ML.EVALUATE`, `ML.CENTROIDS`, `ML.TRIAL_INFO`, `ML.FEATURE_INFO`, `ML.PREDICT`, and `ML.DETECT_ANOMALIES` (with `contamination`).
- `bigquery-ml/workflows/customer_segmentation/customer_segmentation.ipynb` — the same model type on a real problem: RFM (recency/frequency/monetary) features engineered from raw `thelook_ecommerce` order history, then `KMEANS` at a fixed `num_clusters = 4`. The deliberate contrast with `models/kmeans/`'s `penguins` run is mechanism demo vs. applied segmentation.
- `EXPORT MODEL` (a `KMEANS` model exports as a TensorFlow SavedModel) and Endpoint serving are covered in `bigquery-ml/models/export/` and `bigquery-ml/models/remote/`.


---
