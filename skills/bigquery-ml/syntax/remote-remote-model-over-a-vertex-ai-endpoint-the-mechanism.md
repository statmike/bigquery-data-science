# `REMOTE` (Remote model over a Vertex AI endpoint — the mechanism)

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#remote-remote-model-over-a-vertex-ai-endpoint--the-mechanism`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#remote-remote-model-over-a-vertex-ai-endpoint--the-mechanism)

- **Description:** A remote model registers an external prediction service as a BigQuery ML model so it can be queried in-warehouse with `ML.PREDICT`. This entry covers the **generic mechanism**: `CREATE MODEL ... REMOTE WITH CONNECTION` pointing at a **custom model deployed to a Vertex AI prediction endpoint** (any framework — TensorFlow, PyTorch, scikit-learn, XGBoost, custom container). BigQuery sends rows to the endpoint through a Cloud Resource Connection and merges the returned predictions back into the result set. No model artifacts live in BigQuery; the model runs on the endpoint's infrastructure (incl. GPUs).
- **When to use:**
  - The model is already hosted on a Vertex AI endpoint for online serving and you want SQL-native inference.
  - The model is too large to import into BigQuery (the ONNX/imported path caps at ~250 MB) or needs GPU/custom-container serving.
  - You want one SQL inference surface (`ML.PREDICT`) over a model whose framework BigQuery can't train or import.
  - You want scheduled queries for automated batch scoring without a separate Python serving step.
- **Category:** remote.
- **Connection required:** **Yes** — a BigQuery **Cloud Resource Connection** (`CLOUD_RESOURCE`). `DEFAULT` connection is also accepted.
- **Status:** GA.
- **documentation:**
  - CREATE MODEL (custom models on Vertex AI endpoints): https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-remote-model-https
  - Remote model index (LLMs / embeddings / Cloud AI services variants): https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-remote-model
  - Tutorial — Make predictions with remote models on Vertex AI: https://cloud.google.com/bigquery/docs/bigquery-ml-remote-model-tutorial
  - Cloud Resource Connection: https://cloud.google.com/bigquery/docs/create-cloud-resource-connection
  - `ML.PREDICT`: https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-predict

> **Scope note (foundation / LLM endpoints):** Remote models over Vertex AI **foundation/LLM** endpoints (Gemini text generation, foundation-model embeddings, fine-tuned Gemini) are documented in [`../bigquery-ai/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai) — see the remote-model LLM pattern there, plus `ML.GENERATE_TEXT`, `AI.GENERATE_*`, and foundation-model `ML.GENERATE_EMBEDDING` / `AI.GENERATE_EMBEDDING`. This entry covers ONLY the custom-endpoint mechanism queried with `ML.PREDICT`.
>
> **Scope note (Cloud AI services):** The same DDL with `REMOTE_SERVICE_TYPE` in place of `endpoint` points at a **pre-trained Cloud AI service** rather than an endpoint you deployed — `CLOUD_AI_TRANSLATE_V3`, `CLOUD_AI_NATURAL_LANGUAGE_V1`, `CLOUD_AI_VISION_V1`, `CLOUD_AI_SPEECH_TO_TEXT_V2`, `CLOUD_AI_DOCUMENT_V1`. Nothing trains, nothing is deployed, and the consuming function is `ML.TRANSLATE` / `ML.UNDERSTAND_TEXT` / `ML.ANNOTATE_IMAGE` / `ML.TRANSCRIBE` / `ML.PROCESS_DOCUMENT` rather than `ML.PREDICT`. All five are documented in the sibling project: [Cloud AI Service Models](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/cloud-ai-service-models.md).

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
INPUT  (field_name field_type [, ...])
OUTPUT (field_name field_type [, ...])
REMOTE WITH CONNECTION `PROJECT_ID.REGION.CONNECTION_ID`   -- or:  REMOTE WITH CONNECTION DEFAULT
OPTIONS(
  ENDPOINT = 'https://REGION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/REGION/endpoints/ENDPOINT_ID'
);
```

**Options:**

| Option | Type | Required | Default | Range / Values | Description |
|--------|------|----------|---------|----------------|-------------|
| `ENDPOINT` | STRING | Yes | — | Shared public endpoint URL `https://\<region\>-aiplatform.googleapis.com/v1/projects/\<project\>/locations/\<region\>/endpoints/\<endpoint_id\>` | The Vertex AI endpoint serving the custom model. Dedicated public endpoints, Private Service Connect endpoints, and private endpoints are NOT supported. |

(No HP-tuning options apply — a remote model is a registration, not a training run. The request batch size is managed by BigQuery; the endpoint receives batches of instances, defaulting to ~128 instances per request.)

**INPUT / OUTPUT clauses (required for custom endpoints):**

| Clause | Rule |
|--------|------|
| `INPUT (...)` | Must list the fields BigQuery sends as the `instances` payload. Field **names must match** the endpoint request's field names. Supported types incl. `INT64`, `FLOAT64`, `STRING`, `BOOL`, `ARRAY\<...\>`. |
| `OUTPUT (...)` | Must list the fields BigQuery reads from each `predictions` element. Field **names must match** the endpoint response's field names. **Single-output special case:** if the endpoint returns one unnamed output, any name may be used. |

BigQuery wraps each row's `INPUT` columns into one element of the `instances` array, and unpacks each `predictions` element back into the `OUTPUT` columns. `ML.PREDICT` also returns a `remote_model_status` column reporting per-row call status.

**Supported lifecycle functions:** **`ML.PREDICT` only.** Training/evaluation lifecycle functions do not apply — the model is not trained in BigQuery, so `ML.EVALUATE`, `ML.WEIGHTS`/`ML.ADVANCED_WEIGHTS`, `ML.GLOBAL_EXPLAIN`, `ML.FEATURE_IMPORTANCE`, `ML.EXPLAIN_PREDICT`, `ML.CONFUSION_MATRIX`, etc. are N/A. (You can compute evaluation metrics yourself in SQL over `ML.PREDICT` output joined to labels.)

**ML.EVALUATE output metrics (this type):** N/A — `ML.EVALUATE` is not supported for remote models over custom endpoints.

**Preprocessing support:** None inside BigQuery. `TRANSFORM` is not applied; any feature engineering must happen in the `ML.PREDICT` input subquery or inside the served container.

**Hyperparameter tuning:** N/A — no training occurs.

**Explainability / weights:** N/A in BigQuery (no `enable_global_explain`, no weights). Explanations, if any, must be produced by the Vertex AI endpoint and surfaced as `OUTPUT` fields.

**Best practices:**
- Two-step setup: (1) create a `CLOUD_RESOURCE` connection, (2) grant its auto-provisioned service account `roles/aiplatform.user`, then create the model. IAM propagation is variable and **verified live to exceed two minutes** in one case despite the grant itself succeeding immediately — retry `CREATE MODEL` on a permission error with a loop (several attempts, ~20s apart), not a single fixed sleep.
- Keep the connection in the **same location/region as the dataset** holding the model (location requirement).
- Reuse one connection across multiple remote models.
- Make `OUTPUT` names/types exactly mirror the endpoint response to avoid silent NULLs.
- Push filters/limits into the `ML.PREDICT` input subquery to control endpoint call volume and cost.

**Limitations:**
- `INPUT` and `OUTPUT` are **required** for custom-model endpoints.
- Only **shared public** Vertex AI endpoints — dedicated public, PSC, and private endpoints are unsupported.
- Only `ML.PREDICT` is supported; no evaluation/explainability/weights lifecycle functions.
- Cost has two parts: Vertex AI endpoint compute + the BigQuery query; latency includes a network round-trip per batch.
- **The `model_registry='VERTEX_AI'` shortcut (see `CREATE MODEL` general options) is NOT currently a working alternative to the manual export+upload path above, for at least `LOGISTIC_REG`.** Verified live: a model registered this way carries an unconditional Sampled-Shapley `explanationSpec` (confirmed via `gcloud ai models describe` — present even with no explainability options set), and deploying it to an Endpoint fails with `InvalidArgument: 400 Error occurred in Explanation preprocessing. ValueError: NodeDef mentions attr 'debug_name' not in Op<name=VarHandleOp...>`. This is a confirmed, currently-open Google issue — [vertex-ai-samples#2723](https://github.com/GoogleCloudPlatform/vertex-ai-samples/issues/2723), filed against Google's own official BQML-online-prediction sample notebook, closed "not planned." The manually-exported-and-uploaded model (no baked-in explanation spec) is the reliable path until this is fixed. `REMOTE` itself is not limited to models that ever touched BigQuery ML — any model registered to Vertex AI Model Registry (any framework, any training origin) can back a `REMOTE WITH CONNECTION` model once deployed to an endpoint.

**Locations:** Connection must match the dataset's BigQuery location (e.g., dataset in `US` → connection in `US`). Endpoint region is encoded in the `ENDPOINT` URL.

**BigFrames API:** No direct training equivalent; remote-endpoint inference is generally orchestrated via SQL/`ML.PREDICT` or the Vertex AI SDK (`aiplatform.Endpoint.predict`).

**Repo example (tested):**
- `bigquery-ml/models/remote/` — the full path, picking up where `models/export/` leaves off: `CREATE MODEL` → `EXPORT MODEL` → deploy to a Vertex AI Endpoint → register that Endpoint as a `REMOTE` model → `ML.PREDICT`. Derives `INPUT`/`OUTPUT` from the exported SavedModel signature, creates the `CLOUD_RESOURCE` connection, grants `roles/aiplatform.user` to the connection's service agent, then `CREATE OR REPLACE MODEL ... INPUT(...) OUTPUT(...) REMOTE WITH CONNECTION ... OPTIONS(endpoint=...)`. Covers single-row, multi-row, and batch table scoring, and reads the per-row `remote_model_status` column (verified: 0 errors across 200 rows). Carries a real, small dollar cost for as long as the Endpoint stays deployed — the notebook tears it down.
- The signature is not restricted to numeric features: an `INPUT (text STRING) OUTPUT (label STRING, score FLOAT64)` model over a text-classification container is the same mechanism, and is the alternative to ONNX import above when you want tokenization to stay server-side.
- `bigquery-ml/models/remote/remote.ipynb` — the full round trip from a BQML model: trains a `LOGISTIC_REG` → `EXPORT MODEL` (TF SavedModel) → `aiplatform.Model.upload()` with the pre-built `tf2-cpu.2-15` serving container (no Dockerfile) → deploys to a minimal `n1-standard-2` Endpoint → creates a `CLOUD_RESOURCE` connection + grants `roles/aiplatform.user` → `CREATE MODEL ... INPUT(...) OUTPUT(...) REMOTE WITH CONNECTION ... OPTIONS(endpoint=...)` → `ML.PREDICT` (single-row + 200-row batch, verified 0 `remote_model_status` errors). Verified the TF-serving container's response uses the exact field names the SavedModel signature itself exposes (`{label}_probs`/`{label}_values`/`predicted_{label}`), so `OUTPUT` can mirror them directly. Endpoint torn down within a few minutes of deployment — cross-link this entry with [`models/export/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/export), which this notebook picks up from. Also demonstrates, as a documented live failure, the `model_registry='VERTEX_AI'` shortcut's Explanation-preprocessing bug described above (Step 4), and proves the mechanism is framework-agnostic by registering (not deploying) an XGBoost model trained entirely outside BigQuery with the `xgboost-cpu.2-1` container (Step 5).


---
