# `AI.EMBED`

> **Source:** [`bigquery-ai/reference/embedding-generation-and-semantic-search.md#aiembed`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/embedding-generation-and-semantic-search.md#aiembed)

- **Description:** Scalar function that creates embeddings from text or multimodal data. Sends a request to a Vertex AI embedding model (or runs the built-in Preview `embeddinggemma-300m` model) and returns a `STRUCT` with the embedding vector and status. No pre-created model object required.
- **Use cases:** Semantic search, recommendation, classification, clustering, outlier detection.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-embed)
- **Type:** Scalar function (returns a STRUCT value per row) -- GA

**Syntax (text embedding with endpoint):**
```sql
AI.EMBED(
  [content =>] 'content',
  endpoint => 'endpoint'
  [, task_type => 'task_type']
  [, title => 'title']
  [, model_params => model_params]
  [, connection_id => 'connection']
)
```

**Syntax (text embedding with built-in model — Preview):**
```sql
AI.EMBED(
  [content =>] 'content',
  model => 'model'
)
```

**Syntax (multimodal embedding):**
```sql
AI.EMBED(
  [content =>] 'content',
  connection_id => 'connection',
  endpoint => 'endpoint'
  [, model_params => model_params]
)
```

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content` | STRING, ObjectRef, ObjectRefRuntime, or STRUCT | Required | The data to embed. For text: string literal, column name, or expression. For images and documents: an `ObjectRef` — `OBJ.MAKE_REF(uri, connection)` or an object table's `ref` column. (`ObjectRefRuntime` is still accepted; it is not required.) For `gemini-embedding-2`: can be a STRING, an `ObjectRef`, or a STRUCT containing STRING, ARRAY\<STRING\>, ObjectRef, and ARRAY\<ObjectRef\> (text, images, audio, video, PDFs). |
| `endpoint` | STRING | Required (unless `model` specified) | Embedding model endpoint on the Gemini Enterprise Agent Platform (formerly Vertex AI). Must include model version (e.g., `gemini-embedding-2`, `gemini-embedding-001`, `text-embedding-005`, `multimodalembedding@001`). BigQuery auto-resolves full endpoint from model name; `gemini-embedding-2` is served from multi-regional endpoints only and resolves `us` / `eu` / `global` by the same rule as the Gemini 3.x models (see [Choosing a Gemini Model Endpoint](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md#choosing-a-gemini-model-endpoint)). |
| `model` | STRING | Optional (Preview) | Built-in text embedding model. Only supported value: `embeddinggemma-300m` (768 dims, 2048 tokens). When specified, cannot use `endpoint`, `title`, `model_params`, or `connection_id`. Data stays in BigQuery — no Vertex AI charges, uses BQ slots. |
| `task_type` | STRING literal | Optional (text only) | Intended downstream application. Values: `RETRIEVAL_QUERY`, `RETRIEVAL_DOCUMENT`, `SEMANTIC_SIMILARITY`, `CLASSIFICATION`, `CLUSTERING`, `QUESTION_ANSWERING`, `FACT_VERIFICATION`, `CODE_RETRIEVAL_QUERY`. **GOTCHA:** Supported on `gemini-embedding-001`, `text-embedding-005`, and `text-multilingual-embedding-002`; **rejected by `gemini-embedding-2`** (`400 Bad Request: task_type is not supported for gemini-embedding-2 model`). |
| `title` | STRING | Optional (text only) | Document title to improve embedding quality. Can only be used when `task_type` is `RETRIEVAL_DOCUMENT`. **GOTCHA:** Supported on `gemini-embedding-001`, `text-embedding-005`, and `text-multilingual-embedding-002`; **rejected by `gemini-embedding-2`** (`400 Bad Request: title is not supported for gemini-embedding-2 model`). |
| `model_params` | JSON literal | Optional | For `gemini-embedding-2`, `gemini-embedding-001`, `text-embedding-005`, and `text-multilingual-embedding-002`: pass camelCase `JSON '{"outputDimensionality": 768}'` (MRL truncation on `gemini-embedding-2` and `gemini-embedding-001`). For `multimodalembedding@001`: pass `JSON '{"dimension": 512}'` (`128`, `256`, `512`, `1408`). **GOTCHA:** Passing `"dimension"` or snake_case `"output_dimensionality"` inside `model_params` JSON to `gemini-embedding-2` is **silently ignored** and returns `3,072` dimensions. |
| `connection_id` | STRING | Optional for text; Required for multimodal | Connection in format `PROJECT_ID.LOCATION.CONNECTION_ID`. The connection's service account needs the Vertex AI User role. If query runs 48+ hours, use a connection. |

**Outputs:**

Returns a STRUCT with:

| Field | Type | Description |
|-------|------|-------------|
| `result` | ARRAY\<FLOAT64\> | The generated embedding vector. |
| `status` | STRING | API response status (empty string if successful). |

**Supported models:**

| Model | Type | Max Dimensions | Max Tokens | Notes |
|-------|------|----------------|------------|-------|
| `endpoint => 'gemini-embedding-2'` (GA) | Unified text & multimodal | up to 3072 (MRL `outputDimensionality` down to 768/512/256/128) | 8192 | **Primary text & multimodal model.** Text, images, audio, video, PDF, or a STRUCT mixing them in a shared semantic space. Multi-regional (`us`/`eu`/`global`) endpoints only. `task_type` and `title` are rejected outright (*"not supported for gemini-embedding-2 model"*). The `-preview` suffix still resolves to the same model. |
| `endpoint => 'gemini-embedding-001'` | Text | up to 3072 | 2048 | Multilingual text model supporting `task_type` and `title` |
| `model => 'embeddinggemma-300m'` (Preview) | Built-in text | 768 | 2048 | No Vertex AI charges, uses BQ slots |
| `endpoint => 'text-embedding-005'` | Text (legacy) | up to 768 | 2048 | English text |
| `endpoint => 'text-multilingual-embedding-002'` | Text (legacy) | up to 768 | 2048 | Multilingual text |
| `endpoint => 'multimodalembedding@001'` | Multimodal (legacy) | 128, 256, 512, 1408 | — | Images/video only (JPEG, PNG, BMP, GIF — not PDF) |

**Best practices:**
- If you need to reuse embeddings across many queries, save results to a table.
- For multimodal input, pass an inline `OBJ.MAKE_REF(uri, connection)` as the content. This avoids needing an object table or BigQuery reservation.
- `gemini-embedding-2` embeds PDFs, images, audio, video, and text directly; legacy `multimodalembedding@001` supports images/video only (JPEG, PNG, BMP, GIF) — **not PDFs**.

**Limitations:** Image content must be in supported formats (JPEG, PNG, BMP, GIF; `gemini-embedding-2` also accepts PDF, audio, and video). For multimodal embeddings, `connection_id` is required and the connection's service account needs `roles/aiplatform.user` and `roles/storage.objectViewer`. Incurs Vertex AI charges per call.

**Locations:** All locations supporting Vertex AI embedding models, plus US and EU multi-regions.

**Provisioned throughput:** Not specified in documentation.

**BigFrames API:** `bigframes.bigquery.ai.embed(content, *, endpoint=..., model=..., connection_id=..., task_type=..., title=..., model_params=...)` (available in `bigframes 2.51.0+`) — Scalar wrapper returning a Series of `STRUCT<result ARRAY<FLOAT64>, status STRING>`. Access vectors with `.struct.field("result")`. For table-valued remote models, `bbq.ai.generate_embedding()` is also available.

---
