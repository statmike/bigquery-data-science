# `AI.SIMILARITY`

> **Source:** [`bigquery-ai/reference/embedding-generation-and-semantic-search.md#aisimilarity`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/embedding-generation-and-semantic-search.md#aisimilarity)

- **Description:** (Preview) Scalar function that computes the cosine similarity between two inputs (text or images). Creates embeddings for both inputs at runtime and computes the cosine similarity between them. Values closer to 1 indicate more similar inputs.
- **Use cases:** Semantic search without precomputed embeddings, recommendation, classification, prototyping similarity queries.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-similarity)
- **Type:** Scalar function (returns FLOAT64) -- Preview

**Syntax (text with endpoint):**
```sql
AI.SIMILARITY(
  content1 => 'CONTENT1',
  content2 => 'CONTENT2',
  endpoint => 'ENDPOINT'
  [, model_params => MODEL_PARAMS]
  [, connection_id => 'CONNECTION_ID']
)
```

**Syntax (text with built-in model — Preview):**
```sql
AI.SIMILARITY(
  content1 => 'CONTENT1',
  content2 => 'CONTENT2',
  model => 'MODEL'
)
```

**Syntax (multimodal):**
```sql
AI.SIMILARITY(
  content1 => 'CONTENT1',
  content2 => 'CONTENT2',
  connection_id => 'CONNECTION_ID',
  endpoint => 'ENDPOINT'
  [, model_params => MODEL_PARAMS]
)
```

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content1` | STRING, ObjectRef, or ObjectRefRuntime | Required | First value to compare. An `ObjectRef` is enough — no signing step. For `gemini-embedding-2`: can be a STRUCT (text, images, audio, video, PDFs). |
| `content2` | STRING, ObjectRef, or ObjectRefRuntime | Required | Second value to compare. Same types as `content1`. |
| `endpoint` | STRING | Required (unless `model` specified) | Embedding model endpoint (e.g., `text-embedding-005`, `multimodalembedding@001`, `gemini-embedding-2`). |
| `model` | STRING | Optional (Preview) | Built-in text embedding model. Only supported value: `embeddinggemma-300m`. When specified, cannot use `endpoint`, `model_params`, or `connection_id`. No Vertex AI charges. |
| `model_params` | JSON literal | Optional | For text: any parameters object fields including `outputDimensionality`. For multimodal: only `dimension`. |
| `connection_id` | STRING | Optional for text; Required for multimodal | Connection in format `PROJECT_ID.LOCATION.CONNECTION_ID`. |

**Outputs:** Returns FLOAT64 (cosine similarity). NULL on error.

**AI.SIMILARITY vs VECTOR_SEARCH:**

| Feature | AI.SIMILARITY | VECTOR_SEARCH |
|---------|---------------|---------------|
| Function type | Scalar | TVF |
| Primary purpose | Cosine similarity between two specific inputs | Top-K nearest neighbors from a base table |
| Embedding | Generates embeddings at runtime (2 per call) | Uses pre-computed embeddings |
| Indexing | No vector indexes | Designed to use vector indexes for ANN search |
| Use case | Small comparisons, prototyping | Large-scale semantic search, RAG |

**Supported models:** Same models as AI.EMBED: `embeddinggemma-300m` (built-in, Preview), `gemini-embedding-001`, `text-embedding-005`, `text-multilingual-embedding-002`, `gemini-embedding-2` (multimodal, GA), `multimodalembedding@001`.

**Best practices:**
- Use for small comparisons and prototyping. Use VECTOR_SEARCH for large-scale searches.
- Supports **cross-modal** comparisons: `content1` can be text while `content2` is an image (or vice versa) when using `multimodalembedding@001` or `gemini-embedding-2` (measured 2026-10-09 on `gemini-embedding-2`: image/image 0.79, text/image 0.28 on the same pet-store product photo). Text and image embeddings share the same vector space, so text descriptions can be matched against document images.
- `multimodalembedding@001` supports images only (JPEG, PNG, BMP, GIF) — **not PDFs** (status: *"Unsupported content type application/pdf for AI.EMBED MULTIMODAL_EMBEDDING endpoint"*). Use `gemini-embedding-2` for PDF support, or render PDFs to images first.

**Limitations:** Incurs charges for two embedding generations per call. For multimodal, `connection_id` is required and the connection's service account needs `roles/aiplatform.user` and `roles/storage.objectViewer`.

**Locations:** All regions supporting Gemini models, plus US and EU multi-regions.

**Provisioned throughput:** Not specified in documentation.

**BigFrames API:** No direct equivalent. Use `%%bigquery` magics or `session.read_gbq_query()` to execute AI.SIMILARITY SQL from BigFrames.

---
