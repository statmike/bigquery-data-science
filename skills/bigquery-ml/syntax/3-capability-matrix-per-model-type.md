# 3. Capability matrix (per model type)

> **Source:** [`bigquery-ml/reference/comparison-tables.md#3-capability-matrix-per-model-type`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/comparison-tables.md#3-capability-matrix-per-model-type)

| Model type | TRANSFORM | HP tuning | `enable_global_explain` | Weights fn | Feature attributions | `ML.DETECT_ANOMALIES` |
|---|---|---|---|---|---|---|
| `LINEAR_REG` / `LOGISTIC_REG` | ✅ | ✅ | ✅ | `ML.WEIGHTS` / `ML.ADVANCED_WEIGHTS` | `ML.EXPLAIN_PREDICT`, `ML.GLOBAL_EXPLAIN` | — |
| `BOOSTED_TREE_*` | ✅ | ✅ | ✅ | — | `ML.FEATURE_IMPORTANCE`, `ML.EXPLAIN_PREDICT`, `ML.GLOBAL_EXPLAIN` | — |
| `RANDOM_FOREST_*` | ✅ | ✅ | ✅ | — | `ML.FEATURE_IMPORTANCE`, `ML.EXPLAIN_PREDICT`, `ML.GLOBAL_EXPLAIN` | — |
| `DNN_*` | ✅ | ✅ | ✅ | — | `ML.EXPLAIN_PREDICT`, `ML.GLOBAL_EXPLAIN` (Integrated Gradients) | — |
| `DNN_LINEAR_COMBINED_*` | ✅ | ✅ | ✅ | — | `ML.EXPLAIN_PREDICT`, `ML.GLOBAL_EXPLAIN` | — |
| `AUTOML_*` | — | (internal) | (auto) | — | `ML.GLOBAL_EXPLAIN` only | — |
| `KMEANS` | ✅ | ✅ (`num_clusters`) | — | `ML.CENTROIDS` | — | ✅ (`contamination`) |
| `PCA` | ✅ | — | — | `ML.PRINCIPAL_COMPONENTS` / `_INFO` | — | ✅ (`contamination`) |
| `AUTOENCODER` | ✅ | ✅ | — | — | — | ✅ (`contamination`) |
| `MATRIX_FACTORIZATION` | — | ✅ | — | `ML.WEIGHTS` | — | — |
| `ARIMA_PLUS` / `_XREG` | ✅* | (auto.ARIMA) | — | `ML.ARIMA_COEFFICIENTS` | `ML.EXPLAIN_FORECAST` | ✅ (`anomaly_prob_threshold`) |
| Imported (`TENSORFLOW`/`ONNX`/`XGBOOST`/`TFLITE`) | — | — | — | — | `ML.FEATURE_IMPORTANCE` (XGBOOST), `ML.EXPLAIN_PREDICT` (TF) | — |
| Remote (custom endpoint) | — | — | — | — | — | — |

\* ARIMA_PLUS supports `TRANSFORM` except when modeling custom holidays; `ARIMA_PLUS_XREG` does not support `TRANSFORM`.
