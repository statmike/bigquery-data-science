# `ML.RECONSTRUCTION_LOSS`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlreconstruction_loss`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlreconstruction_loss)

- **Description:** Computes per-row reconstruction error between the input and the autoencoder's reconstructed output. The magnitude of the error is the basis for anomaly scoring.
- **Use cases:**
  - Score how poorly each row reconstructs (high error = candidate anomaly).
  - Data sanitation / outlier detection on new data.
  - Inspect the error distribution feeding `ML.DETECT_ANOMALIES`.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-reconstruction-loss
- **Type:** Table-valued function (evaluation function).
- **Applies to models:** `AUTOENCODER` only. (PCA does NOT support it — use `ML.EVALUATE`'s `total_explained_variance_ratio` for PCA quality. Imported TensorFlow models are not supported.)

**Syntax:**
```sql
SELECT *
FROM ML.RECONSTRUCTION_LOSS(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  { TABLE `PROJECT_ID.DATASET.TABLE` | (QUERY_STATEMENT) });
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model ref | Yes | — | A trained `AUTOENCODER` model. |
| `TABLE` / `QUERY_STATEMENT` | table or query | Yes | — | Input rows to reconstruct; column names/types must match the model (or the `TRANSFORM` clause inputs if one was used). |

**Outputs:** (input columns are passed through alongside these error metrics)

| Column | Type | Description |
|--------|------|-------------|
| `mean_absolute_error` | FLOAT64 | Per-row mean absolute reconstruction error. |
| `mean_squared_error` | FLOAT64 | Per-row mean squared reconstruction error. |
| `mean_squared_log_error` | FLOAT64 | Per-row mean squared log reconstruction error. |
| `trial_id` | INT64 | Present for hyperparameter-tuned models; identifies the optimal trial used. |

**Best practices:** For anomaly detection prefer `ML.DETECT_ANOMALIES` (handles contamination thresholding) and reserve `ML.RECONSTRUCTION_LOSS` for inspecting the raw error distribution. Larger errors indicate rows the model could not reconstruct (likely anomalous).
**Limitations:** `AUTOENCODER` only; no imported TensorFlow models. If `TRANSFORM` was used at training, the input may only reference the `TRANSFORM` input columns.
**BigFrames API:** No direct equivalent (`bigframes.ml` autoencoder reconstruction-loss helper not exposed); use the SQL function.
**Repo example (tested):** `bigquery-ml/models/autoencoder/autoencoder.sql` (Example 6) — returns `mean_absolute_error`, `mean_squared_error`, and `mean_squared_log_error` per input row (the same three metrics `ML.EVALUATE` reports in aggregate), `ORDER BY mean_squared_error DESC` to surface the rows the model reconstructs worst. That is the manual, row-level view of exactly the signal `ML.DETECT_ANOMALIES` automates in the same file's Example 8. On a hyperparameter-tuned model the output also carries `trial_id`.

---

> Cross-reference: for anomaly detection from these models see `ML.DETECT_ANOMALIES`; for extracting embeddings from a trained PCA/AUTOENCODER/MATRIX_FACTORIZATION model see the in-scope `ML.GENERATE_EMBEDDING` lifecycle entry. Foundation-model (text/multimodal) embedding generation lives in [../bigquery-ai](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md).


---
