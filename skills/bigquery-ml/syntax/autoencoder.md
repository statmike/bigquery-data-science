# `AUTOENCODER`

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#autoencoder`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#autoencoder)

- **Description:** A symmetric feed-forward neural network that learns to compress (encode) input rows into a lower-dimensional latent space and then reconstruct (decode) them. The middle hidden layer defines the latent dimension. Quality is measured by reconstruction loss (how closely outputs match inputs).
- **When to use:**
  - Unsupervised anomaly detection on tabular data (high reconstruction error = anomaly) via `ML.DETECT_ANOMALIES`.
  - Dimensionality reduction / nonlinear feature compression where a linear method (PCA) is insufficient.
  - Producing row-level embeddings (latent vectors) for similarity search, recommendation, or outlier detection.
  - Data sanitation: flag/repair records that the model cannot reconstruct well.
- **Category:** unsupervised.
- **Connection required:** No (in-BigQuery training). A Cloud connection/Vertex AI is only needed for the optional `MODEL_REGISTRY = 'VERTEX_AI'` registration or `EXPORT MODEL` to GCS — not for training/eval/predict.
- **Status:** GA.
- **documentation:** [CREATE MODEL for autoencoder](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-autoencoder) · [ML.RECONSTRUCTION_LOSS](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-reconstruction-loss) · journey links: [Anomaly detection](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-detect-anomalies), [Hyperparameter tuning](https://cloud.google.com/bigquery/docs/hp-tuning-overview), [E2E user journeys](https://cloud.google.com/bigquery/docs/e2e-journey).

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
[TRANSFORM(...)]
OPTIONS(
  model_type = 'AUTOENCODER',
  hidden_units = [128, 64, 8, 64, 128],   -- middle value = latent dimension
  activation_fn = 'RELU',
  batch_size = 30,
  dropout = 0.5,
  learn_rate = 0.001,
  optimizer = 'ADAM',
  max_iterations = 30,
  early_stop = TRUE,
  min_rel_progress = 0.001
) AS
SELECT * EXCEPT(label_or_id_cols)            -- no label column; unsupervised
FROM `PROJECT_ID.DATASET.TABLE`
WHERE splits = 'TRAIN';
```

**Options (model-specific):**

| Option | Type | Required | Default | Range / Values | Description |
|--------|------|----------|---------|----------------|-------------|
| `model_type` | STRING | Yes | — | `'AUTOENCODER'` | Selects the model. |
| `hidden_units` | ARRAY\<INT64\> | No | network auto-sized | e.g. `[128,64,8,64,128]` | Layer sizes; symmetric. **Middle element = latent-space dimension.** Tunable via `HPARAM_CANDIDATES([struct([...]), ...])`. |
| `activation_fn` | STRING | No | `'RELU'` | `RELU`, `RELU6`, `ELU`, `SELU`, `SIGMOID`, `TANH` (no `CRELU`) | Hidden-layer activation. Tunable (`HPARAM_CANDIDATES`). |
| `batch_size` | INT64 | No | auto (\<=1024) | \>0 | Mini-batch size. Tunable (`HPARAM_RANGE`/`HPARAM_CANDIDATES`). |
| `dropout` | FLOAT64 | No | 0 | tuning range `[0, 1.0)`, default tuning range `[0, 0.8]` | Dropout rate. Tunable. |
| `learn_rate` | FLOAT64 | No | 0.001 | \>0 | Optimizer learning rate. Tunable. |
| `learn_rate_strategy` | STRING | No | `'LINE_SEARCH'` | `LINE_SEARCH`, `CONSTANT` | How learn rate evolves. |
| `optimizer` | STRING | No | `'ADAM'` | `ADAGRAD`, `ADAM`, `FTRL`, `RMSPROP`, `SGD` | Training optimizer. Tunable. |
| `l1_reg_activation` | FLOAT64 | No | 0 | \>=0 | L1 regularization of the activation output (autoencoder-specific; **note: not `l1_reg`/`l2_reg`**). Tunable. |
| `max_iterations` | INT64 | No | 20 | \>0 | Max training iterations (epochs). |
| `early_stop` | BOOL | No | TRUE | TRUE/FALSE | Stop when `min_rel_progress` not met. |
| `min_rel_progress` | FLOAT64 | No | 0.01 | \>0 | Min relative loss improvement to continue (when `early_stop=TRUE`). |
| `warm_start` | BOOL | No | FALSE | TRUE/FALSE | Continue training existing model. |
| `kms_key_name` | STRING | No | — | Cloud KMS key | CMEK for the model. |
| `model_registry` | STRING | No | — | `'VERTEX_AI'` | Register model in Vertex AI Model Registry. |
| `vertex_ai_model_id` | STRING | No | — | string | Vertex AI model id (with `model_registry`). |
| `vertex_ai_model_version_aliases` | ARRAY\<STRING\> | No | — | strings | Version aliases in Vertex AI. |

HP-tuning options (used when `num_trials` set): `num_trials`, `max_parallel_trials`, `hparam_tuning_algorithm` (e.g. `'VIZIER_DEFAULT'`), `hparam_tuning_objectives` (e.g. `['mean_absolute_error']`). Tunable hyperparameters: `hidden_units`, `activation_fn`, `batch_size`, `dropout`, `learn_rate`, `optimizer`, `l1_reg_activation`.

**Supported lifecycle functions:** `ML.EVALUATE`, `ML.RECONSTRUCTION_LOSS`, `ML.PREDICT` (returns `latent_col_N` latent vector + input columns), [`ML.GENERATE_EMBEDDING`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md) (latent space as a single `ml_generate_embedding_result` ARRAY — in-scope here as a lifecycle use of a trained BQML model), `ML.DETECT_ANOMALIES` (with `STRUCT(<contamination> AS contamination)`), `ML.FEATURE_INFO`, `ML.TRAINING_INFO`, `ML.TRIAL_INFO` (HP tuning), `EXPORT MODEL`. Pair with `ML.NORMALIZER` + `VECTOR_SEARCH` for similarity. No `ML.WEIGHTS`/`ML.GLOBAL_EXPLAIN`/`ML.CONFUSION_MATRIX`/`ML.ROC_CURVE`/`ML.CENTROIDS`/`ML.PRINCIPAL_COMPONENTS`.

**ML.EVALUATE output metrics (this type):** `mean_absolute_error`, `mean_squared_error`, `mean_squared_log_error`. (For HP-tuned models the output also includes a `trial_id` column, one row per trial.) `ML.RECONSTRUCTION_LOSS` returns the same three metric columns **per input row** (plus `trial_id` for tuned models) alongside the input columns.

**Preprocessing support:** automatic (standardization of numeric features) | manual | TRANSFORM (supported; if TRANSFORM is used, `ML.PREDICT`/`ML.RECONSTRUCTION_LOSS` accept only the pre-TRANSFORM input columns).

**Hyperparameter tuning:** Supported. Set `num_trials` and use `HPARAM_RANGE`/`HPARAM_CANDIDATES` on `hidden_units`, `activation_fn`, `batch_size`, `dropout`, `learn_rate`, `optimizer`, `l1_reg_activation`. Default algorithm `VIZIER_DEFAULT` (Vertex AI Vizier); objective defaults to the key metric, override with `hparam_tuning_objectives` (e.g. `mean_absolute_error`). Recommended trials >= 10 x number of tuned hyperparameters. Tuned models expose results via `ML.TRIAL_INFO` and add a `trial_id` column to evaluate/predict output.

**Explainability / weights:** None of `ML.WEIGHTS`, `ML.ADVANCED_WEIGHTS`, `ML.GLOBAL_EXPLAIN`, `ML.FEATURE_IMPORTANCE`, or `ML.EXPLAIN_PREDICT` apply (`enable_global_explain` not supported for autoencoders). Interpretability comes from per-row reconstruction loss and the latent representation.

**Best practices:**
- Set the latent dimension via the middle of `hidden_units` (e.g. `[128,64,8,64,128]` => 8-dim latent / embedding).
- Train on clean/normal data only for anomaly detection; pass the expected fraud/anomaly rate as `contamination` to `ML.DETECT_ANOMALIES`.
- **Verified: `ML.NORMALIZER` + `DOT_PRODUCT` is unnecessary for `VECTOR_SEARCH`** — `distance_type='COSINE'` on the raw, un-normalized `ML.GENERATE_EMBEDDING` output gives mathematically equivalent rankings (`COSINE` distance = `1 - cosine_similarity` = `DOT_PRODUCT` distance on unit vectors, up to sign) without a manual normalization step. Reach for `ML.NORMALIZER` only if you need normalized vectors for something other than `VECTOR_SEARCH`, or need `DOT_PRODUCT` specifically (e.g. a vector index type that doesn't support `COSINE`).
- HP tuning scans large data per trial — autoencoder training is compute/byte heavy (the repo example processed ~1.9 TB across 40 trials); cap `num_trials`/`max_parallel_trials` and use `early_stop`.

**Limitations:**
- Unsupervised — no label column; exclude id/label/split columns from the training SELECT.
- No model weight/feature-attribution functions; no `enable_global_explain`.
- `ML.RECONSTRUCTION_LOSS` does not support imported TensorFlow models.
- Exported model is TensorFlow SavedModel format.

**Locations:** Available in BigQuery ML regions/multi-regions; Vertex AI registration/online serving requires a matching Vertex AI region (notebooks use `us-central1`).

**BigFrames API:** `bigframes.ml.imported`/`bigframes.ml.decomposition` have no direct autoencoder class; no direct BigFrames equivalent — use SQL `CREATE MODEL ... AUTOENCODER` (confirmed against the live BigFrames API reference, `models/autoencoder/`).

**Verified (`models/autoencoder/`):**
- **The default `activation_fn = 'RELU'` genuinely breaks small, narrow networks — a real dying-ReLU collapse, not a theoretical concern.** On a `hidden_units = [3, 2, 3]` network (2-dim latent), a substantial and highly variable share of rows have BOTH latent dimensions simultaneously clipped to exactly `0.0` — verified across three independent retrains, with wildly different severity each time (observed `n_both_zero`/`n_total` rates: 40%, 50%, 65%) and different specific shapes (sometimes one entire latent column pinned to `0.0` for every row, sometimes the zeros spread unevenly across both columns). `ML.EVALUATE`'s aggregate metrics look like a normally-trained model every time — the collapse is only visible by directly inspecting `ML.PREDICT`'s `latent_col_*` output. **Fix: switch `activation_fn` to `'TANH'`** (no dead zone) — this fixed the collapse every time it was tested and consistently landed `mean_squared_error` around ~0.21, well below the RELU baseline's own highly variable range (~0.66-0.94 observed) — the exact improvement ratio isn't fixed (it depends on how badly RELU happened to collapse that retrain), but the direction and TANH's ~0.21 landing point are consistent.
- **`ML.EVALUATE`'s reconstruction metrics are reproducible bit-for-bit under a fixed model name** (same as `DNN_*`), but the **latent-space values are not** — two retrains of the identical model produced identical aggregate metrics but different specific `latent_col_*` values/ranges. Unlike `PCA`'s uniquely-ordered, variance-ranked components, a generic autoencoder bottleneck has no constraint forcing a stable, canonical basis — any invertible transform of the latent space paired with the inverse transform in the decoder reconstructs identically. Don't treat individual `latent_col_N` values as stable/comparable across retrains the way `PCA`'s `principal_component_N` is.
- **`ML.DETECT_ANOMALIES` requires the 3rd (input-data) argument for `AUTOENCODER` too** — same as `KMEANS` and `PCA`; all three unsupervised model types in this project share this requirement.
- **HP tuning over `activation_fn`/`learn_rate` did NOT reliably confirm `TANH` beats `RELU` — a claim from initial testing that did not survive retesting.** One 4-trial run sampled mostly `TANH` and found it winning; a second 4-trial run (the real notebook execution) sampled mostly `RELU` and found a `RELU` trial winning instead, with **all 4 trials scoring worse than both the untuned RELU baseline and the untuned TANH fix**. With only 4 trials spread across two hyperparameters simultaneously, the search is too sparse to reliably explore either dimension — the same small-trial-budget limitation already documented for `DNN_*`. The direct, controlled, same-`learn_rate` comparison (RELU vs. TANH, nothing else changed) remains the reliable evidence that TANH fixes the collapse; a small-budget joint HP search over both hyperparameters does not reproduce that conclusion reliably and shouldn't be read as confirming or refuting it either way.
- **`ML.GENERATE_EMBEDDING` does NOT normalize its output.** Its raw `ml_generate_embedding_result` is bit-for-bit identical to `ML.PREDICT`'s un-normalized latent columns — confirmed by applying `ML.NORMALIZER` independently to both and getting the exact same normalized vector either way. Its real convenience over the manual `ML.PREDICT` + hand-built `ARRAY[latent_col_1, ...]` path is not having to enumerate the latent columns yourself, not automatic normalization.
- **`VECTOR_SEARCH` does not accept `ML.PREDICT`/`ML.GENERATE_EMBEDDING` output directly as its base-table argument** (`"Unsupported query pattern"`) — materialize embeddings into a real table first.
- **Manually normalizing + `DOT_PRODUCT` is unnecessary** — `distance_type='COSINE'` on the raw `ML.GENERATE_EMBEDDING` output gives mathematically equivalent `VECTOR_SEARCH` rankings (verified: identical top-k neighbors, with distances that convert exactly via `COSINE = 1 - cosine_similarity` and `DOT_PRODUCT = -cosine_similarity` on unit vectors).

**Repo example (tested):**
- `bigquery-ml/models/autoencoder/` — full lifecycle on `penguins`: HP-tuned `AUTOENCODER` (`HPARAM_CANDIDATES`/`HPARAM_RANGE` over `num_trials`), `ML.FEATURE_INFO`, `ML.TRIAL_INFO`, `ML.EVALUATE`, `ML.RECONSTRUCTION_LOSS`, `ML.PREDICT` (the `latent_col_*` outputs), and `ML.DETECT_ANOMALIES` with `contamination`. The same notebook covers the second use of this model type — the latent space *as* a table embedding, via `ML.GENERATE_EMBEDDING` plus `ML.NORMALIZER`, then `VECTOR_SEARCH` for row-to-row similarity.
- `EXPORT MODEL` (`AUTOENCODER` exports as a TensorFlow SavedModel) and Endpoint serving: `bigquery-ml/models/export/` and `bigquery-ml/models/remote/`.
- `bigquery-ml/workflows/anomaly_fraud_detection/anomaly_fraud_detection.ipynb` — trains on the real ULB/Kaggle fraud dataset (`bigquery-public-data.ml_datasets.ulb_fraud_detection`, 492 genuine fraud cases) and measures real precision/recall against the true label — contrasts with `PCA` (comparable performance here, not dramatically different) and a supervised `BOOSTED_TREE_CLASSIFIER` (far higher recall).


---
