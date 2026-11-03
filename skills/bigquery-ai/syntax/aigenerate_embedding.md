# `AI.GENERATE_EMBEDDING`

> **Source:** [`bigquery-ai/reference/embedding-generation-and-semantic-search.md#aigenerate_embedding`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/embedding-generation-and-semantic-search.md#aigenerate_embedding)

- **Description:** Table-valued function that creates embeddings from text, image, video data, or from PCA, autoencoder, and matrix factorization models. Requires a pre-created remote model via `CREATE MODEL`. This is the recommended embedding TVF for new queries.
- **Use cases:** Semantic search, recommendation, classification, clustering, outlier detection, PCA, autoencoding, matrix factorization.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-generate-embedding)
- **Type:** Table-valued function (returns a table)

**Syntax (text embedding):**
```sql
AI.GENERATE_EMBEDDING(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  { TABLE `PROJECT_ID.DATASET.TABLE_NAME` | (QUERY_STATEMENT) },
  STRUCT(
    [, TASK_TYPE AS task_type]
    [, OUTPUT_DIMENSIONALITY AS output_dimensionality]
  )
)
```

**Syntax (open models):**
```sql
AI.GENERATE_EMBEDDING(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  { TABLE `PROJECT_ID.DATASET.TABLE_NAME` | (QUERY_STATEMENT) }
)
```

**Syntax (multimodal, standard tables):**
```sql
AI.GENERATE_EMBEDDING(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  { TABLE `PROJECT_ID.DATASET.TABLE_NAME` | (QUERY_STATEMENT) },
  STRUCT(
    [, OUTPUT_DIMENSIONALITY AS output_dimensionality]
  )
)
```

**Syntax (multimodal, object tables):**
```sql
AI.GENERATE_EMBEDDING(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  { TABLE `PROJECT_ID.DATASET.TABLE_NAME` | (QUERY_STATEMENT) },
  STRUCT(
    [, START_SECOND AS start_second]
    [, END_SECOND AS end_second]
    [, INTERVAL_SECONDS AS interval_seconds]
    [, OUTPUT_DIMENSIONALITY AS output_dimensionality]
  )
)
```

Additional syntaxes exist for PCA, Autoencoder, and Matrix factorization models.

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `MODEL` | Model reference | Required | Remote model reference (`PROJECT_ID.DATASET.MODEL_NAME`). Must reference a Vertex AI embedding model (`gemini-embedding-2`, `gemini-embedding-001`, `text-embedding-005`, `multimodalembedding@001`), a supported open model, PCA, autoencoder, or matrix factorization model. |
| `TABLE` / `QUERY_STATEMENT` | Table or query | Required (except matrix factorization) | Input data. For text: must contain a STRING column named `content`. |
| `TASK_TYPE` | STRING literal | Optional (text only) | Values: `RETRIEVAL_QUERY`, `RETRIEVAL_DOCUMENT`, `SEMANTIC_SIMILARITY`, `CLASSIFICATION`, `CLUSTERING`, `QUESTION_ANSWERING`, `FACT_VERIFICATION`, `CODE_RETRIEVAL_QUERY`. **Rejected when the remote model points to `gemini-embedding-2`.** |
| `OUTPUT_DIMENSIONALITY` | INT64 | Optional | Number of embedding dimensions (`STRUCT(768 AS output_dimensionality)`). Supported on `gemini-embedding-2` (`128`–`3,072`, default `3,072`), `gemini-embedding-001` (`128`–`3,072`), `text-embedding-005` (`<= 768`), and `multimodalembedding@001` (`128`, `256`, `512`, `1408`; default `1408`). Cannot be used with video segment embeddings on `multimodalembedding@001`. |
| `START_SECOND` | FLOAT64 | Optional (video only) | Start second for video embedding. Default: 0. |
| `END_SECOND` | FLOAT64 | Optional (video only) | End second for video embedding. Max/default: 120. |
| `INTERVAL_SECONDS` | FLOAT64 | Optional (video only) | Interval for segmenting video. Must be >= 4 and < 120. Default: 16. |
| `TRIAL_ID` | INT64 | Optional (autoencoder, matrix factorization) | Identifies hyperparameter tuning trial. |

**Outputs (text embedding):**

| Column | Type | Description |
|--------|------|-------------|
| `embedding` | ARRAY\<FLOAT64\> | Generated embedding vector |
| `statistics` | JSON | Contains `token_count` and `truncated` fields (text only — not returned by `multimodalembedding@001`) |
| `status` | STRING | API response status (empty if successful) |

Additional output columns exist for multimodal (video_start_sec, video_end_sec), PCA, autoencoder (trial_id), and matrix factorization (trial_id, processed_input, feature).

> **Note:** The `statistics` column is returned by the text embedding models only. Neither `multimodalembedding@001` nor `gemini-embedding-2` returns it (measured 2026-10-09: `gemini-embedding-2`'s output is `STRUCT<result ARRAY<FLOAT64>, status STRING>`) — queries that SELECT `statistics` against either will error with *"Field name statistics does not exist"*.

**Supported models:**

| Model | Output Dimensions | Max Sequence Length | Languages |
|-------|-------------------|---------------------|-----------|
| `gemini-embedding-2` (GA) | up to 3072 (`output_dimensionality` down to 128) | 8192 | Unified text & multimodal (text, image, video, audio, PDF, or a STRUCT mixing them). No `statistics` column. Multi-regional endpoints only. Honors camelCase `model_params => JSON '{"outputDimensionality": 768}'` on `AI.EMBED` and `STRUCT(768 AS output_dimensionality)` on `AI.GENERATE_EMBEDDING` (whereas `model_params => JSON '{"dimension": 256}'` is the `multimodalembedding@001`-only key and is silently ignored by `gemini-embedding-2`, returning 3072 dims). |
| `gemini-embedding-001` | up to 3072 | 2048 tokens | Multilingual |
| `text-embedding-005` | up to 768 | 2048 tokens | English |
| `text-multilingual-embedding-002` | up to 768 | 2048 tokens | Multilingual |
| `multilingual-e5-small` (Preview) | up to 384 | 512 tokens | Multilingual |
| `multilingual-e5-large` (Preview) | up to 1024 | 512 tokens | Multilingual |
| `multimodalembedding@001` | 128, 256, 512, 1408 | -- | -- |

Also supports PCA, autoencoder, and matrix factorization models.

**Best practices:**
- For multimodal input, prefer inline ObjectRef subqueries (`OBJ.MAKE_REF(uri, connection)` as the `content` column) over object tables. Inline ObjectRef queries do not require a BigQuery reservation, while object tables used with remote models do.
- `gemini-embedding-2` supports text, PDFs, images, audio, and video; legacy `multimodalembedding@001` supports images/video only (JPEG, PNG, BMP, GIF) — **not PDFs**.

**Limitations:** Model and input table must be in the same region. Resource exhausted errors possible when API volume exceeds quota. Videos: only first 2 minutes processed. Object tables used with remote models require a BigQuery reservation — use inline ObjectRef to avoid this requirement.

**Locations:** Must run in the same region or multi-region as the model. Also available in US multi-region.

**Provisioned throughput:** For multimodalembedding: default RPM for non-EU regions is 600; default RPM for EU regions is 120. See Vertex AI quotas.

**BigFrames API:** `bigframes.bigquery.ai.generate_embedding(model, data)` — TVF wrapper that takes a model name string and DataFrame/Series. Generates `AI.GENERATE_EMBEDDING` SQL. Also available as `bigframes.ml.llm.TextEmbeddingGenerator` (sklearn-style: create model, then `.predict()`) and `bigframes.ml.llm.MultimodalEmbeddingGenerator` for multimodal. Note that in `bigframes 2.51.0`, `TextEmbeddingGenerator` hardcodes `_TEXT_EMBEDDING_ENDPOINTS = ("text-embedding-005", "text-multilingual-embedding-002", "gemini-embedding-001")` and `MultimodalEmbeddingGenerator` hardcodes `("multimodalembedding@001",)` — prefer `bbq.ai.embed` or `bbq.ai.generate_embedding` for `gemini-embedding-2`.

### Remote embedding models as MaaS (`CREATE MODEL`)

Google publishes a dedicated reference page for creating BigQuery ML remote models over managed embedding Model-as-a-Service (MaaS) endpoints on Vertex AI / Gemini Enterprise Agent Platform: [CREATE MODEL for remote embedding models (MaaS)](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-remote-model-embedding-maas).

```sql
-- Unified text & multimodal Gemini Embedding 2 MaaS remote model (multi-regional us / eu / global)
CREATE OR REPLACE MODEL `your-gcp-project-id.DATASET_ID.multimodal_embedding_maas`
  REMOTE WITH CONNECTION `your-gcp-project-id.us.CONNECTION_ID`
  OPTIONS (
    ENDPOINT = 'gemini-embedding-2'
  );

-- Text MaaS remote embedding model supporting task_type (or 'text-embedding-005')
CREATE OR REPLACE MODEL `your-gcp-project-id.DATASET_ID.embedding_maas_model`
  REMOTE WITH CONNECTION `your-gcp-project-id.us.CONNECTION_ID`
  OPTIONS (
    ENDPOINT = 'gemini-embedding-001'
  );
```

- **IAM & service agents:** Grant `roles/aiplatform.user` (and `roles/storage.objectViewer` when embedding Cloud Storage `ObjectRef` inputs) to the Cloud resource connection's service account (`bqcx-000000000000-xxxx@gcp-sa-bigquery-condel.iam.gserviceaccount.com`); Vertex AI endpoint provisioning in the host project uses the Vertex AI service agent (`service-000000000000@gcp-sa-aiplatform.iam.gserviceaccount.com`).
- **Supported MaaS endpoints:** First-party Vertex AI text and multimodal embedding endpoints (`gemini-embedding-2`, `gemini-embedding-001`, `text-embedding-005`, `text-multilingual-embedding-002`, `multimodalembedding@001`) as well as Vertex AI MaaS open/partner text embedding endpoints (such as `multilingual-e5-small` and `multilingual-e5-large` in Preview).
- **When to use [`AI.EMBED`](aiembed.md) vs `CREATE MODEL` + `AI.GENERATE_EMBEDDING`:** Prefer scalar `AI.EMBED` when you want zero DDL, inline `SELECT`/`WHERE` expressions, or autonomous table embedding generation (`GENERATED ALWAYS AS (AI.EMBED(...).result) STORED`). Reach for `CREATE MODEL` + `AI.GENERATE_EMBEDDING` when you need governed model-level IAM via a connection, MaaS open embedding models (`multilingual-e5-*`), video segment embedding (`start_second` / `end_second` / `interval_seconds`), or local BQML PCA / Autoencoder / Matrix Factorization models.

---
