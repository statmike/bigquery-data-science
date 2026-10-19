# `TENSORFLOW_LITE`

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#tensorflow_lite`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#tensorflow_lite)

- **Description:** Imports a TensorFlow Lite (`.tflite`) model for inference.
- **When to use:** Edge/quantized TF Lite artifacts you want to serve in SQL; TF Text-based preprocessing graphs (within op limits).
- **Category:** imported. **Connection required:** No (object-table serving needs reservations). **Status:** GA.
- **documentation:** [CREATE MODEL (TFLite)](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-tflite)

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
OPTIONS(
  MODEL_TYPE = 'TENSORFLOW_LITE',
  MODEL_PATH = 'gs://bucket/path/to/tflite_model/*'
);
```

**Options:** identical set to TENSORFLOW (`MODEL_TYPE='TENSORFLOW_LITE'`, `MODEL_PATH`, optional `KMS_KEY_NAME`).

**Supported lifecycle functions:** `ML.PREDICT` **only**.
**Data types:** integer types → `INT64`; `FLOAT16/32/64` → `FLOAT64`; `BOOL` → `BOOL`; `STRING` → `STRING`. Complex, `RESOURCE`, `VARIANT` unsupported.
**Limitations:** Must be `.tflite` format, stored in GCS, exists before import. **450 MB** size limit.
Only TensorFlow core ops + TensorFlow Text ops supported; **SentencePiece operators not supported**;
sparse tensors not supported. Object-table use is reservation-only (no on-demand).
**BigFrames API:** No direct equivalent class (use TensorFlow/ONNX imported-model classes for the TF/ONNX paths).
**Repo example (tested):** `bigquery-ml/models/imported/imported.ipynb` (Step 5) — `tf.lite.TFLiteConverter.from_saved_model(...)` on the exact SavedModel used for the `TENSORFLOW` example, then imported with `MODEL_TYPE='TENSORFLOW_LITE'`. Verified predictions match the `TENSORFLOW` import to ~7 significant figures (not bit-for-bit — ordinary float32 kernel differences between the TF runtime and the TFLite interpreter, since no quantization was applied) — same `ARRAY<FLOAT64>` input contract, same auto-named `output_0` output.

---
