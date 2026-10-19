# 5. Connection matrix

> **Source:** [`bigquery-ml/reference/comparison-tables.md#5-connection-matrix`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/comparison-tables.md#5-connection-matrix)

| Model category | Connection required? |
|---|---|
| All natively-trained models (GLM, trees, DNN, k-means, PCA, autoencoder, MF, ARIMA, contribution analysis) | **No** |
| AutoML | No (uses an internal `ML_EXTERNAL` Vertex AI job) |
| Imported (TF / TFLite / ONNX / XGBoost) | No for `ML.PREDICT`; **Yes** (Cloud Resource + reservation) only for object-table serving |
| Remote (custom Vertex AI endpoint) | **Yes** — Cloud Resource Connection |
| `EXPORT MODEL` to GCS | No (writer needs GCS write IAM, not a BQ connection) |
