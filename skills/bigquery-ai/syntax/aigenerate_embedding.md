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
| `MODEL` | Model reference | Required | Remote model reference (`PROJECT_ID.DATASET.MODEL_NAME`). Must reference a Vertex AI embedding model, multimodalembedding@001, a supported open model, PCA, autoencoder, or matrix factorization model. |
| `TABLE` / `QUERY_STATEMENT` | Table or query | Required (except matrix factorization) | Input data. For text: must contain a STRING column named `content`. |
| `TASK_TYPE` | STRING literal | Optional (text only) | Values: `RETRIEVAL_QUERY`, `RETRIEVAL_DOCUMENT`, `SEMANTIC_SIMILARITY`, `CLASSIFICATION`, `CLUSTERING`, `QUESTION_ANSWERING`, `FACT_VERIFICATION`, `CODE_RETRIEVAL_QUERY` |
| `OUTPUT_DIMENSIONALITY` | INT64 | Optional | Number of embedding dimensions. For multimodal: valid values are 128, 256, 512, 1408 (default: 1408). Cannot be used with video embeddings. |
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
| `gemini-embedding-001` | up to 3072 | 2048 tokens | Multilingual |
| `text-embedding-005` | up to 768 | 2048 tokens | English |
| `text-multilingual-embedding-002` | up to 768 | 2048 tokens | Multilingual |
| `multilingual-e5-small` (Preview) | up to 384 | 512 tokens | Multilingual |
| `multilingual-e5-large` (Preview) | up to 1024 | 512 tokens | Multilingual |
| `multimodalembedding@001` | 128, 256, 512, 1408 | -- | -- |
| `gemini-embedding-2` (GA) | up to 3072 | 8192 | Multimodal (text, image, video, audio, PDF, or a STRUCT mixing them). No `statistics` column. Multi-regional endpoints only. Measured: `model_params => JSON '{"dimension": 256}'` still returned 3072 dimensions through `AI.EMBED`. |

Also supports PCA, autoencoder, and matrix factorization models.

**Best practices:**
- For multimodal input, prefer inline ObjectRef subqueries (`OBJ.MAKE_REF(uri, connection)` as the `content` column) over object tables. Inline ObjectRef queries do not require a BigQuery reservation, while object tables used with remote models do.
- `multimodalembedding@001` supports images only (JPEG, PNG, BMP, GIF) — **not PDFs**. Render PDFs to images first.

**Limitations:** Model and input table must be in the same region. Resource exhausted errors possible when API volume exceeds quota. Videos: only first 2 minutes processed. Object tables used with remote models require a BigQuery reservation — use inline ObjectRef to avoid this requirement.

**Locations:** Must run in the same region or multi-region as the model. Also available in US multi-region.

**Provisioned throughput:** For multimodalembedding: default RPM for non-EU regions is 600; default RPM for EU regions is 120. See Vertex AI quotas.

**BigFrames API:** `bigframes.bigquery.ai.generate_embedding(model, data)` — TVF wrapper that takes a model name string and DataFrame/Series. Generates `AI.GENERATE_EMBEDDING` SQL. Also available as `bigframes.ml.llm.TextEmbeddingGenerator` (sklearn-style: create model, then `.predict()`) and `bigframes.ml.llm.MultimodalEmbeddingGenerator` for multimodal.

---
