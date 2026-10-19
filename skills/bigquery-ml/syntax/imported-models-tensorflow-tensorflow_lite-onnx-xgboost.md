# Imported models (TENSORFLOW, TENSORFLOW_LITE, ONNX, XGBOOST)

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#imported-models-tensorflow-tensorflow_lite-onnx-xgboost`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#imported-models-tensorflow-tensorflow_lite-onnx-xgboost)

Imported models let you bring a model trained **outside** BigQuery — in TensorFlow, TensorFlow Lite,
ONNX, or XGBoost — into BigQuery ML from Cloud Storage and run inference with `ML.PREDICT` natively
inside BigQuery compute. This is the BigQuery ML **Inference Engine**: same SQL API, no Vertex AI
endpoint to deploy, manage, or pay for. Contrast with **remote models** (`CREATE MODEL ... REMOTE WITH
CONNECTION`), where the model runs on an external endpoint and BigQuery calls out to it — imported
models run in BigQuery itself but are size-limited and require pre-formatted (often numeric/ARRAY)
inputs.

- **Common shape:** all four are `CREATE MODEL ... OPTIONS(MODEL_TYPE='...', MODEL_PATH='gs://...')`.
- **Connection required:** **No connection** for reading the GCS model file (BigQuery uses the
  credentials of the user running `CREATE MODEL`). A connection *is* required only when serving an
  imported model over an **object table** (capacity/reservation pricing only).
- **No training, no preprocessing, no `TRANSFORM`, no HP tuning, no `ML.EVALUATE`.** The model is
  frozen at import; you supply inputs already in the model's expected schema/format.
- **documentation:** [Imported models journey](https://cloud.google.com/bigquery/docs/e2e-journey-import)
  · [Inference overview](https://cloud.google.com/bigquery/docs/inference-overview)
  · [ML.PREDICT](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-predict)

**Capability summary (all imported types):**

| Capability | Imported models |
|---|---|
| TRANSFORM clause | No |
| Hyperparameter tuning | No |
| `enable_global_explain` | No |
| `ML.EVALUATE` / `ML.CONFUSION_MATRIX` / `ML.ROC_CURVE` | No |
| Weights / feature attribution | Only `ML.FEATURE_IMPORTANCE` (XGBOOST only) |
| `ML.EXPLAIN_PREDICT` | TENSORFLOW only (memory-heavy; can OOM) |
| `ML.FEATURE_INFO` | No |
| Object-table serving | Yes — capacity/reservation pricing only (no on-demand) |

---
