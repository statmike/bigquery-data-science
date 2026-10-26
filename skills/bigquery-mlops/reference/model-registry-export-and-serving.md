# Vertex AI Model Registry, Model Export/Import & Hybrid Serving

Contents: [1. Decision matrix: where is the model trained and where is it served?](#1-decision-matrix-where-is-the-model-trained-and-where-is-it-served) · [2. Vertex AI Model Registry & online endpoint deployment](#2-vertex-ai-model-registry--online-endpoint-deployment) · [3. Exporting BigQuery ML models (`EXPORT MODEL`)](#3-exporting-bigquery-ml-models-export-model) · [4. Importing external models into BigQuery (`ONNX`, `XGBOOST`, `TENSORFLOW`, `TENSORFLOW_LITE`)](#4-importing-external-models-into-bigquery-onnx-xgboost-tensorflow-tensorflow_lite) · [5. Calling Vertex AI Endpoints from SQL (`REMOTE WITH CONNECTION`)](#5-calling-vertex-ai-endpoints-from-sql-remote-with-connection) · [6. Reusable preprocessing pipelines (`TRANSFORM_ONLY`)](#6-reusable-preprocessing-pipelines-transform_only) · [7. Canonical snippets](#7-canonical-snippets) · [8. Go deeper (Lens 3 & Lens 4)](#8-go-deeper-lens-3--lens-4)

BigQuery ML is not a closed island: models trained in BigQuery can be registered in **Vertex AI Model Registry**, exported to Cloud Storage (`EXPORT MODEL`) for serving in Vertex AI Endpoints, Cloud Run, GKE, or edge runtimes, and models trained outside BigQuery (scikit-learn, PyTorch, XGBoost, TensorFlow/Keras) can be imported into BigQuery (`ONNX`, `XGBOOST`, `TENSORFLOW`, `TENSORFLOW_LITE`) or called over HTTPS via `REMOTE WITH CONNECTION`.

---

## 1. Decision matrix: where is the model trained and where is it served?

| Training Location | Serving Location | Mechanism | Connection Needed? | Key Requirement / Limit |
| --- | --- | --- | --- | --- |
| **BigQuery (`CREATE MODEL`)** | **BigQuery (`ML.PREDICT` / `ML.FORECAST`)** | Native BQML | Only for `MATRIX_FACTORIZATION` / `AUTOML_*` | Zero data movement; `TRANSFORM(...)` statistics applied automatically at predict time. |
| **BigQuery (`CREATE MODEL`)** | **Vertex AI Model Registry** | `OPTIONS(model_registry='VERTEX_AI', vertex_ai_model_id='...', vertex_ai_model_version_aliases=[...])` | No | Syncs model lineage and versions to Vertex AI Model Registry. *(See `LOGISTIC_REG` endpoint deploy gotcha in Section 2.)* |
| **BigQuery (`CREATE MODEL`)** | **External (Vertex AI Endpoint, Cloud Run, GKE, Local Python)** | `EXPORT MODEL ... OPTIONS(URI='gs://...')` | No (uses caller's GCS write permissions) | Emits TensorFlow SavedModel or XGBoost Booster (`model.ubj` when `xgboost_version='2.1'`). Baked-in `TRANSFORM` exports as a companion SavedModel. |
| **External (scikit-learn, PyTorch, XGBoost, Keras)** | **BigQuery (`ML.PREDICT` in SQL)** | `CREATE MODEL ... OPTIONS(model_type='ONNX' \| 'XGBOOST' \| 'TENSORFLOW' \| 'TENSORFLOW_LITE', model_path='gs://...')` | No (unless scoring an Object Table) | Runs inside BigQuery's native inference engine with zero hourly endpoint cost; artifact size limits apply (`250–450 MB`). |
| **External or Exported BQML** | **Vertex AI Endpoint called from BigQuery (`ML.PREDICT`)** | `CREATE MODEL ... REMOTE WITH CONNECTION ... OPTIONS(endpoint='https://...')` | **Yes** (`CLOUD_RESOURCE` + `roles/aiplatform.user`) | Supports models > 450 MB, GPU serving, and custom containers; billed by the hour while the Vertex AI Endpoint is deployed. |
| **Google Pre-Trained Cloud AI API** | **BigQuery (`ML.PROCESS_DOCUMENT`, `ML.TRANSLATE`, etc.)** | `CREATE MODEL ... REMOTE WITH CONNECTION ... OPTIONS(REMOTE_SERVICE_TYPE='...')` | **Yes** (`CLOUD_RESOURCE` + service IAM) | No model artifact deployed or billed hourly; see [`../../bigquery-ai/reference/cloud-ai-service-models.md`](../../bigquery-ai/reference/cloud-ai-service-models.md). |

---

## 2. Vertex AI Model Registry & online endpoint deployment

Setting `model_registry = 'VERTEX_AI'` inside `CREATE MODEL ... OPTIONS(...)` automatically registers the BigQuery ML model in Vertex AI Model Registry (`vertex_ai_model_id` sets the name; `vertex_ai_model_version_aliases = ['champion', 'v1']` tags the version).

- **Verified Gotcha — `model_registry='VERTEX_AI'` direct endpoint deployment fails for `LOGISTIC_REG`**:
  - When BigQuery registers a `LOGISTIC_REG` model into Vertex AI Model Registry, it attaches an unconditional Sampled-Shapley `explanationSpec` to the registry entry. Attempting to deploy that registered model directly to a Vertex AI Online Prediction Endpoint fails with `InvalidArgument: Explanation preprocessing failed` (confirmed upstream issue `vertex-ai-samples#2723`).
  - **Reliable Production Workaround**: When you need to deploy a BQML model to a Vertex AI Endpoint for online REST serving or `REMOTE WITH CONNECTION` round-trip scoring, use the explicit 3-step pipeline verified in [`remote.md`](../../bigquery-ml/narrative/remote.md):
    1. `EXPORT MODEL` to `gs://...`
    2. `aiplatform.Model.upload(artifact_uri=..., serving_container_image_uri=...)` (without the broken explanation spec)
    3. `model.deploy(machine_type="n1-standard-2")`

---

## 3. Exporting BigQuery ML models (`EXPORT MODEL`)

`EXPORT MODEL` writes a trained BQML model to Cloud Storage (`gs://bucket/path/`) as either a TensorFlow SavedModel (`LINEAR_REG`, `LOGISTIC_REG`, `DNN_*`, `WIDE_AND_DEEP_*`, `KMEANS`, `PCA`, `AUTOENCODER`, `MATRIX_FACTORIZATION`, `TRANSFORM_ONLY`) or an XGBoost Booster (`BOOSTED_TREE_*`, `RANDOM_FOREST_*`).

- **Pin `xgboost_version = '2.1'` at training time (`model.ubj` vs `model.bst`)**:
  - At BigQuery ML's default `xgboost_version = '0.9'`, `EXPORT MODEL` writes `model.bst` in a legacy binary format that modern `xgboost >= 2.0` cannot load (`Check failed: str[0] == '{'`).
  - Setting `xgboost_version = '2.1'` (GA) causes `EXPORT MODEL` to write `model.ubj` (Universal Binary JSON), which loads cleanly in current `xgboost 2.x/3.x` without version pinning *and* can be re-imported directly back into BigQuery via `model_type = 'XGBOOST'`.
- **`EXPORT MODEL` strips `feature_names` on XGBoost models**:
  - The exported Booster's `feature_names` attribute is `None` (features are named `f0`, `f1`, ...). Reassign `booster.feature_names` manually from the training query's non-label column order (verified 1:1 with raw column order in [`export.md`](../../bigquery-ml/narrative/export.md)).
- **`ML.FEATURE_CROSS` and `ML.POLYNOMIAL_EXPAND` inside `TRANSFORM` block `EXPORT MODEL`**:
  - Models using `ML.IMPUTER`, scalers, encoders, bucketizers, text functions, or image functions inside `TRANSFORM(...)` export cleanly, but `ML.FEATURE_CROSS` and `ML.POLYNOMIAL_EXPAND` fail `EXPORT MODEL` with `400 Model TRANSFORM contains unsupported function for exporting`.
- **`EXPORT MODEL` requires a literal string `URI`**:
  - BigQuery SQL rejects expressions like `CONCAT('gs://', @@project_id, '/...')` inside `EXPORT MODEL ... OPTIONS(URI = ...)`. In multi-statement SQL scripts where the bucket name derives from `@@project_id`, wrap the statement in `EXECUTE IMMEDIATE FORMAT("EXPORT MODEL \`dataset.model\` OPTIONS(URI = 'gs://%s/path')", @@project_id);`.

---

## 4. Importing external models into BigQuery (`ONNX`, `XGBOOST`, `TENSORFLOW`, `TENSORFLOW_LITE`)

Importing an external model lets you score millions of BigQuery rows in SQL (`ML.PREDICT`) using BigQuery's distributed execution engine with **no Cloud Resource Connection** and **no running Vertex AI Endpoint**.

| `model_type` | Source Frameworks | Verified Compatibility & Schema Rules |
| --- | --- | --- |
| **`ONNX`** | `scikit-learn`, `PyTorch`, `LightGBM` (via `skl2onnx` / `torch.onnx`) | **Must target ONNX Runtime 1.12.0**: pin `target_opset=13` and set `onnx_model.ir_version = 8` explicitly (default `skl2onnx` emits IR 10 / opset 22, which BigQuery rejects). For `scikit-learn` classifiers, pass `options={id(clf): {'zipmap': False}}` or import fails with `unsupported ONNX type: ONNX_TYPE_SEQUENCE`. |
| **`XGBOOST`** | Native Python/R `xgboost.Booster` | **File extension decides acceptance, not library version**: BigQuery accepts `model.json` or `model.ubj` written by `xgboost 3.x` and rejects byte-identical `model.bst` (`Invalid XGBoost model: could not load model from file`). Requires explicit `INPUT (...)` and `OUTPUT (...)` schema clauses on `CREATE MODEL`. Supports `ML.FEATURE_IMPORTANCE`. |
| **`TENSORFLOW`** | TensorFlow / Keras SavedModel directory (`saved_model.pb` + `variables/`) | Reads input/output tensor names directly from the SavedModel `serving_default` signature. Note: although official docs claim `ML.EXPLAIN_PREDICT` support, live testing on a Keras classifier returned `TENSORFLOW model is unsupported in ml.explain_predict` — verify on your own graph before relying on it. |
| **`TENSORFLOW_LITE`** | `.tflite` flatbuffer | Supports `ML.PREDICT` only (no `ML.EXPLAIN_PREDICT` or `ML.FEATURE_IMPORTANCE`). |

---

## 5. Calling Vertex AI Endpoints from SQL (`REMOTE WITH CONNECTION`)

When a model exceeds BigQuery's import size limit, requires GPU/custom-container inference, or is already serving real-time traffic on a Vertex AI Endpoint, register it in BigQuery with `REMOTE WITH CONNECTION`:

- **Requires `INPUT (...)` and `OUTPUT (...)` signatures matching the endpoint's JSON prediction contract**.
- **Requires a `CLOUD_RESOURCE` connection co-located with the BigQuery dataset** whose service account holds `roles/aiplatform.user`. Wait/retry for IAM propagation (~20s intervals for up to 2–3 minutes) when provisioning a new connection in automation.
- **Only shared public Vertex AI Endpoints are supported** (Dedicated Endpoints, Private Service Connect, and private peered endpoints cannot be called from `REMOTE` models).
- **Tear down billable endpoints immediately after batch scoring** if the endpoint is not serving 24/7 online traffic (`endpoint.undeploy_all(); endpoint.delete()`).

---

## 6. Reusable preprocessing pipelines (`TRANSFORM_ONLY`)

`CREATE MODEL ... TRANSFORM(...) OPTIONS(model_type = 'TRANSFORM_ONLY')` freezes training-time preprocessing statistics (`ML.IMPUTER` medians, `ML.STANDARD_SCALER` means/stddevs, `ML.ONE_HOT_ENCODER` vocabularies) into a standalone model artifact consumed via `ML.TRANSFORM(MODEL ..., TABLE ...)`.

- **Critical Serving Rule**: When a downstream model is trained on the output of `ML.TRANSFORM(MODEL transform_model, ...)` instead of having its own embedded `TRANSFORM(...)` clause, `ML.PREDICT` on the downstream model **does not check** whether serving inputs were transformed first. Passing raw unscaled inputs produces silent garbage predictions (in [`transform_only.md`](../../bigquery-ml/narrative/transform_only.md), every row predicted the same class until wrapped in `ML.TRANSFORM`).

---

## 7. Canonical snippets

### A. Export a BQML XGBoost Model (`xgboost_version = '2.1'`) and Re-Import It

```sql
-- 1. Train with xgboost_version = '2.1' so EXPORT MODEL writes modern model.ubj
CREATE OR REPLACE MODEL `bq_ml.churn_xgb`
OPTIONS (
  model_type = 'BOOSTED_TREE_CLASSIFIER',
  input_label_cols = ['churned'],
  xgboost_version = '2.1'
) AS
SELECT age, tenure_days, monthly_spend, churned
FROM `bq_ml.customer_training`;

-- 2. Export to Cloud Storage
EXECUTE IMMEDIATE FORMAT("""
  EXPORT MODEL `bq_ml.churn_xgb`
  OPTIONS (URI = 'gs://%s/bq_ml/exports/churn_xgb')
""", @@project_id);

-- 3. Import an external XGBoost .ubj / .json Booster into BigQuery (no connection required)
CREATE OR REPLACE MODEL `bq_ml.imported_xgb`
INPUT (age FLOAT64, tenure_days FLOAT64, monthly_spend FLOAT64)
OUTPUT (predicted_churned ARRAY<FLOAT64>)
OPTIONS (
  model_type = 'XGBOOST',
  model_path = 'gs://your-bucket/models/model.ubj'
);
```

### B. Convert a `scikit-learn` Classifier to ONNX for BigQuery Import

```python
import onnx
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

# Pin target_opset=13, zipmap=False, and ir_version=8 for BigQuery ONNX Runtime 1.12.0
initial_types = [("float_input", FloatTensorType([None, X_train.shape[1]]))]
onnx_model = convert_sklearn(
    clf,
    initial_types=initial_types,
    target_opset=13,
    options={id(clf): {"zipmap": False}},
)
onnx_model.ir_version = 8
onnx.save_model(onnx_model, "model.onnx")
```

---

## 8. Go deeper (Lens 3 & Lens 4)

- **Lens 4 — Worked Walkthroughs (`../../bigquery-ml/narrative/`)**:
  - [`export.md`](../../bigquery-ml/narrative/export.md) (`bigquery-ml/models/export/`) — `EXPORT MODEL`, `model_registry='VERTEX_AI'`, `xgboost_version='2.1'` `.ubj` vs `.bst`, and local TF/XGBoost scoring
  - [`imported.md`](../../bigquery-ml/narrative/imported.md) (`bigquery-ml/models/imported/`) — `TENSORFLOW`, `TENSORFLOW_LITE`, `ONNX`, and `XGBOOST` imports built and scored in SQL
  - [`remote.md`](../../bigquery-ml/narrative/remote.md) (`bigquery-ml/models/remote/`) — Full round-trip: BQML export → Vertex AI Endpoint deploy → `REMOTE WITH CONNECTION` → `ML.PREDICT` → endpoint teardown
  - [`transform_only.md`](../../bigquery-ml/narrative/transform_only.md) (`bigquery-ml/models/transform_only/`) — Reusable `TRANSFORM_ONLY` feature pipeline + downstream model serving
- **Lens 3 — Syntax Cards (`../../bigquery-ml/syntax/`)**:
  - [`export-model.md`](../../bigquery-ml/syntax/export-model.md) · [`imported-models-tensorflow-tensorflow_lite-onnx-xgboost.md`](../../bigquery-ml/syntax/imported-models-tensorflow-tensorflow_lite-onnx-xgboost.md) · [`onnx.md`](../../bigquery-ml/syntax/onnx.md) · [`xgboost.md`](../../bigquery-ml/syntax/xgboost.md) · [`tensorflow.md`](../../bigquery-ml/syntax/tensorflow.md) · [`tensorflow_lite.md`](../../bigquery-ml/syntax/tensorflow_lite.md) · [`remote-remote-model-over-a-vertex-ai-endpoint-the-mechanism.md`](../../bigquery-ml/syntax/remote-remote-model-over-a-vertex-ai-endpoint-the-mechanism.md) · [`transform_only.md`](../../bigquery-ml/syntax/transform_only.md)
