# `TENSORFLOW`

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#tensorflow`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#tensorflow)

- **Description:** Imports a TensorFlow **SavedModel** for inference inside BigQuery ML.
- **When to use:**
  - You trained a TF model elsewhere (Vertex AI, on-prem) and want SQL-native serving.
  - You need feature-level attributions for a TF model via `ML.EXPLAIN_PREDICT`.
  - Your inputs include `tf.train.Example` / SparseTensor features BigQuery can auto-convert.
- **Category:** imported. **Connection required:** No (object-table serving needs reservations). **Status:** GA.
- **documentation:** [CREATE MODEL (TensorFlow)](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-tensorflow)

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
OPTIONS(
  MODEL_TYPE = 'TENSORFLOW',
  MODEL_PATH = 'gs://bucket/path/to/saved_model/*'
  -- [, KMS_KEY_NAME = 'projects/.../cryptoKeys/my_key']
);
```

**Options:**

| Option | Type | Required | Default | Values | Description |
|--------|------|----------|---------|--------|-------------|
| `MODEL_TYPE` | STRING | Yes | — | `'TENSORFLOW'` | Model type. |
| `MODEL_PATH` | STRING | Yes | — | `gs://...` URI (often ends `/*`) | GCS URI of the SavedModel to import. |
| `KMS_KEY_NAME` | STRING | No | — | CMEK resource name | Customer-managed encryption key for the model. |

**Supported lifecycle functions:** `ML.PREDICT`, `ML.EXPLAIN_PREDICT` (per official docs — **not reproduced live**, see the correction below). Inputs may be dense Tensors,
SparseTensors (pass as dense arrays — BQ converts), or `tf.train.Example` (BQ auto-maps columns).
RaggedTensors are not supported.
**Not supported:** `ML.CONFUSION_MATRIX`, `ML.EVALUATE`, `ML.FEATURE_INFO`, `ML.ROC_CURVE`, `ML.TRAINING_INFO`, `ML.WEIGHTS`.

**Correction (verified live, `models/imported/`, 2026-07-22):** calling `ML.EXPLAIN_PREDICT` on a live imported `TENSORFLOW` model (a small Keras classifier with a baked-in `Normalization` layer) returns `"TENSORFLOW model is unsupported in ml.explain_predict."` — an outright rejection, not the documented (if memory-heavy) support. Treat the official docs' claim as unverified/stale until reproduced against a model that actually supports it.

**Data types:** `tf.int*`/`tf.uint*` → `INT64`; `tf.float16/32/64`, `tf.bfloat16` → `FLOAT64`;
`tf.bool` → `BOOL`; `tf.string` → `STRING`. Complex, quantized (`qint`/`quint`), `tf.resource`, `tf.variant` unsupported.

**Limitations:** Must be a SavedModel that already exists in GCS; frozen at import. 450 MB file-size
limit. In-RAM prediction memory limit ~250 MB (`ML.EXPLAIN_PREDICT` can trigger *TensorFlow worker out
of memory*). GraphDef \< v20, unreleased TF versions, custom/`tf.contrib` ops, and RaggedTensors are
unsupported. Object-table use is reservation-only.
**BigFrames API:** `bigframes.ml.imported.TensorFlowModel(model_path=...)`.
**Repo example (tested):** `bigquery-ml/models/imported/imported.ipynb` (Step 4) — a small Keras `Sequential` classifier with a `tf.keras.layers.Normalization` layer baked in (so raw feature values work directly, since imported models support no `TRANSFORM`), exported via `model.export(...)`, imported with `MODEL_TYPE='TENSORFLOW'`, scored with `ML.PREDICT` (`ARRAY<FLOAT64>` input named `"input"`, auto-named `output_0` output).

---
