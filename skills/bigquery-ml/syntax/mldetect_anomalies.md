# `ML.DETECT_ANOMALIES`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mldetect_anomalies`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mldetect_anomalies)

- **Description:** Performs unsupervised anomaly detection against a trained BQML model. Returns each input row flagged `is_anomaly` (TRUE/FALSE) plus the score the flag is based on. The detection mechanism and threshold parameter differ by model family: error/distance-cutoff for IID models (PCA, AUTOENCODER, KMEANS) and prediction-interval probability for time-series models (ARIMA_PLUS, ARIMA_PLUS_XREG).
- **Use cases:**
  - Fraud / outlier detection on tabular data using a PCA, autoencoder, or k-means model (reconstruction error / distance from centroid).
  - Detecting anomalous points in a forecasted time series (value falls outside the model's prediction interval).
  - Turning an unsupervised dimensionality-reduction / clustering model into a binary anomaly classifier without labels.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-detect-anomalies
- **Type:** Table-valued function.
- **Applies to models:** `PCA`, `AUTOENCODER`, `KMEANS` (use `contamination`); `ARIMA_PLUS`, `ARIMA_PLUS_XREG` (use `anomaly_prob_threshold`). Not applicable to supervised regression/classification model types.

> Cross-link (do NOT duplicate): for foundation-model / TimesFM time-series anomaly detection see `AI.DETECT_ANOMALIES` in [../bigquery-ai/](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md).

**Syntax (IID models — PCA / AUTOENCODER / KMEANS):**
```sql
SELECT *
FROM ML.DETECT_ANOMALIES(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  STRUCT(0.02 AS contamination),
  (SELECT * FROM `PROJECT_ID.DATASET.NEW_DATA`)
);
```

**Syntax (time-series models — ARIMA_PLUS / ARIMA_PLUS_XREG):**
```sql
SELECT *
FROM ML.DETECT_ANOMALIES(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  STRUCT(0.95 AS anomaly_prob_threshold)
  -- optional new_data: , (SELECT ts_id, ts_timestamp, ts_value FROM `PROJECT_ID.DATASET.NEW_DATA`)
);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model | Yes | — | A trained PCA, AUTOENCODER, KMEANS, ARIMA_PLUS, or ARIMA_PLUS_XREG model. |
| `contamination` | FLOAT64 | No (IID only) | — | Proportion `[0, 0.5]` of rows expected to be anomalous; sets the cutoff on the target metric (MSE for PCA/AUTOENCODER, normalized distance for KMEANS). e.g. `0.1` flags the top 10% highest-error rows. |
| `anomaly_prob_threshold` | FLOAT64 | No (time-series only) | `0.95` | Probability cutoff in range `[0, 1)`. A point is anomalous if its `anomaly_probability` exceeds this; also sets the width of `lower_bound`/`upper_bound`. |
| `new_data` (query/TABLE) | table | No\* | — | Data to score. If omitted for time-series, the training data is scored. For IID models the data expression is supplied as the 3rd argument. |

\* For ARIMA_PLUS, scoring historical (training) data requires `decompose_time_series = TRUE` (the default) at CREATE MODEL time; scoring new data requires `anomaly_prob_threshold`. **Verified: all three IID model types (`KMEANS`, `PCA`, `AUTOENCODER`) require this 3rd argument** — omitting it errors immediately with `"DETECT_ANOMALIES expects 3 arguments for <model_type> models but 2 were passed"` (`models/kmeans/`, `models/pca/`, `models/autoencoder/`).

**Outputs (IID — PCA / AUTOENCODER / KMEANS):**

| Column | Type | Description |
|--------|------|-------------|
| `is_anomaly` | BOOL | TRUE if the row's target metric exceeds the `contamination`-derived cutoff. |
| `mean_squared_error` | FLOAT64 | Reconstruction error (PCA, AUTOENCODER). |
| `normalized_distance` | FLOAT64 | Distance from nearest centroid (KMEANS). |
| `CENTROID_ID` | INT64 | Nearest centroid (KMEANS). |
| (passthrough) | — | All input columns are echoed back (e.g. `Time`, `V1`…`V28`, `Amount`, plus `trial_id` for HP-tuned models). |

**Outputs (time-series — ARIMA_PLUS / ARIMA_PLUS_XREG):**

| Column | Type | Description |
|--------|------|-------------|
| `is_anomaly` | BOOL | TRUE if `anomaly_probability` \> `anomaly_prob_threshold`. |
| `anomaly_probability` | FLOAT64 | Probability the point is an anomaly. |
| `lower_bound` / `upper_bound` | FLOAT64 | Prediction-interval bounds (width grows with the threshold). |
| `time_series_timestamp` / `time_series_data` | — | The timestamp and observed value (plus the `time_series_id_col` value when present). |

**Best practices:**
- Set `contamination` to a domain-informed expected outlier rate. [`workflows/anomaly_fraud_detection/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/anomaly_fraud_detection) computes it from the training-data positive-class rate (`TRAIN_FRAUD_PCT ≈ 0.00174`) and passes it as `STRUCT(TRAIN_FRAUD_PCT AS contamination)`.
- For evaluation, map `is_anomaly` to 0/1 and build a confusion matrix against known labels (`CASE WHEN is_anomaly ... END`, as in `workflows/anomaly_fraud_detection/`).
- For ARIMA_PLUS, keep `decompose_time_series = TRUE` so forecast errors are retained for historical anomaly scoring.

**Limitations:**
- `contamination` and `anomaly_prob_threshold` are mutually exclusive — each applies only to its model family.
- IID detection is purely error/distance-rank based: a row is "anomalous" only relative to the chosen contamination cutoff, not an absolute judgement.
- Recall on rare classes is typically low (fraud notebooks show high precision-0 / low recall-1), since these are unsupervised methods.

**BigFrames API:** `model.detect_anomalies(X, contamination=...)` on `bigframes.ml.decomposition.PCA`, `bigframes.ml.cluster.KMeans`, and the autoencoder/forecasting estimators.

**Repo example (tested):**
- `bigquery-ml/models/kmeans/kmeans.sql` (Example 6) — `STRUCT(0.05 AS contamination)`, ranked by `normalized_distance` from the nearest centroid.
- `bigquery-ml/models/pca/pca.sql` (Example 7) — the same contamination cutoff, ranked by `mean_squared_error` (reconstruction error).
- `bigquery-ml/models/autoencoder/autoencoder.sql` (Example 8) — reconstruction-based detection; its Example 6 shows the manual `ML.RECONSTRUCTION_LOSS` view of the same underlying signal.
- `bigquery-ml/models/arima_plus/arima_plus.sql` (Example 11) — the time-series form, `STRUCT(0.95 AS anomaly_prob_threshold)` with `is_anomaly` / `anomaly_probability`. `models/arima_plus_xreg/` carries the covariate variant.
- **The ground-truth check the mechanism demos can't give you:** `bigquery-ml/workflows/anomaly_fraud_detection/anomaly_fraud_detection.sql` runs PCA and AUTOENCODER detection on `ulb_fraud_detection` (284,807 rows, 492 real frauds at 0.17%) trained on features only, then scores real precision/recall against the withheld `Class` label and contrasts it with a supervised `BOOSTED_TREE_CLASSIFIER` trained *with* the label. That file is also the source of the PCA variable-component-count instability documented under `ML.PRINCIPAL_COMPONENT_INFO`.
- **Not the same thing as data-quality monitoring, despite the name.** `ML.DETECT_ANOMALIES` finds row-level outliers *within* one dataset; `ML.VALIDATE_DATA_SKEW` / `ML.VALIDATE_DATA_DRIFT` in `functions/model_monitoring/` compare whole datasets or time windows to each other. Different concept, similar name.

---
