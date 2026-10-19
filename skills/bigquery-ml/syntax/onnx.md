# `ONNX`

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#onnx`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#onnx)

- **Description:** Imports an Open Neural Network Exchange (`.onnx`) model — the framework-agnostic
  interchange format. Lets you serve scikit-learn, PyTorch, XGBoost, etc. once converted to ONNX.
- **When to use:**
  - You have a scikit-learn / PyTorch model and want SQL-native inference without an endpoint.
  - Inputs are numeric/tabular or pre-tokenized ARRAYs (best fit for ONNX import).
  - You want one portable format across frameworks.
- **Category:** imported. **Connection required:** No (object-table serving needs reservations). **Status:** GA.
- **documentation:** [CREATE MODEL (ONNX)](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-onnx)
  · Tutorials: [scikit-learn → ONNX](https://cloud.google.com/bigquery/docs/making-predictions-with-sklearn-models-in-onnx-format)

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
OPTIONS(
  MODEL_TYPE = 'ONNX',
  MODEL_PATH = 'gs://bucket/path/to/onnx_model/*'   -- or '.../model.onnx'
);
```

**Options:** `MODEL_TYPE='ONNX'`, `MODEL_PATH` (accepts a directory wildcard `/*` or a direct
`model.onnx` path), optional `KMS_KEY_NAME`.

**Supported lifecycle functions:** `ML.PREDICT` **only**. (`ML.FEATURE_INFO` is *not* supported — verify
import via the Python/BigFrames client, e.g. `bq.get_model(...)`.)
**Data types:** ONNX **Tensor** type only. Int/uint element types → `INT64`; `FLOAT16/BFLOAT16/FLOAT/DOUBLE` → `FLOAT64`; `BOOL` → `BOOL`; `STRING` → `STRING`. Map, Opaque, Sequence, Optional, Sparse-tensor value types unsupported.
**Limitations:** `.onnx` format only; `ML.PREDICT` only; **450 MB** size limit. Runs on **ONNX Runtime
1.12.0** — your model's opset/IR version must be compatible ([`models/imported/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/imported) sets
`onnx_model.ir_version = 8` and `target_opset = 13` before upload to satisfy this). Only the Tensor value
type is supported. Object-table use is reservation-only.
**Gotcha (scikit-learn classifiers):** sklearn-onnx emits a *sequence of map* for probabilities by
default → import error `unsupported ONNX type: ONNX_TYPE_SEQUENCE`. Fix at conversion time with
`zipmap=False` (or `zipmap='columns'`) — [`models/imported/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/imported) does exactly this.
**BigFrames API:** `bigframes.ml.imported.ONNXModel(model_path=...)`.
**Repo examples (tested):**
- A scikit-learn Pipeline converts with `skl2onnx.convert_sklearn(..., options={id(model): {'zipmap': False}})`
  — the `zipmap=False` is what avoids the sequence-of-map gotcha above — then uploads to GCS and imports
  with `CREATE OR REPLACE MODEL ... OPTIONS(MODEL_TYPE='ONNX', MODEL_PATH='gs://.../*')`, and `ML.PREDICT`
  returns `label` + `probabilities`.
- **A transformer is the case where ONNX import stops being the right tool.** Exporting a PyTorch
  DistilBERT via `torch.onnx.export` takes float16 plus `ir_version=8` just to fit the 250 MB
  practical / 450 MB hard limit and ONNX Runtime 1.12; inputs arrive pre-tokenized as ARRAYs
  (`input_ids`, `attention_mask`) and `ML.PREDICT` returns raw `logits`, leaving softmax/argmax to SQL.
  That is the import-vs-remote tradeoff: ONNX import suits small numeric models and pushes tokenization
  onto the caller, while a `REMOTE` model over an Endpoint (below) keeps the whole pipeline server-side.
- `bigquery-ml/models/imported/imported.ipynb` (Step 2) —
  scikit-learn `LogisticRegression` → ONNX via `skl2onnx.convert_sklearn(..., target_opset=13)`, then
  `onnx_model.ir_version = 8` set explicitly (both needed: a modern skl2onnx defaults to IR version 10
  and opset 22, both too new for ONNX Runtime 1.12). `zipmap=False` avoids the sequence-of-map gotcha.
  Single `ARRAY<FLOAT64>` input named `"input"`, `ML.PREDICT` returns `label` + `probabilities`.

---
