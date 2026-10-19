# `ML.GENERATE_EMBEDDING`

> **Source:** [`bigquery-ai/reference/embedding-generation-and-semantic-search.md#mlgenerate_embedding`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/embedding-generation-and-semantic-search.md#mlgenerate_embedding)

- **Description:** Table-valued function identical in capability to `AI.GENERATE_EMBEDDING` but with `ml_generate_embedding_*` prefixed output column names and an additional `flatten_json_output` parameter. **Google recommends using `AI.GENERATE_EMBEDDING` instead for new queries.**
- **Use cases:** Same as AI.GENERATE_EMBEDDING.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-generate-embedding)
- **Type:** Table-valued function

**Syntax:** Same patterns as AI.GENERATE_EMBEDDING, with the addition of `FLATTEN_JSON_OUTPUT AS flatten_json_output` in the STRUCT parameter.

**Key difference from AI.GENERATE_EMBEDDING:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `flatten_json_output` | BOOL | TRUE | Determines whether JSON content is parsed into separate columns. |

All other inputs are the same as AI.GENERATE_EMBEDDING. Additionally, when using `RETRIEVAL_DOCUMENT` task type, you can include a `title` column in the input query.

**Outputs (column naming difference):**

| Column | Type | Description |
|--------|------|-------------|
| `ml_generate_embedding_result` | ARRAY\<FLOAT64\> (flatten=TRUE) or JSON (flatten=FALSE) | Embedding vector or full JSON response |
| `ml_generate_embedding_statistics` | JSON | Token count and truncated fields (flatten=TRUE only) |
| `ml_generate_embedding_status` | STRING | API response status |
| `ml_generate_embedding_start_sec` | INT64 | Video only (NULL for images) |
| `ml_generate_embedding_end_sec` | INT64 | Video only (NULL for images) |

**Supported models / Limitations / Locations / Provisioned throughput:** Same as AI.GENERATE_EMBEDDING. Note: `gemini-embedding-001` has a default output dimensionality of 3072 (vs 768 for `text-embedding-005`). `gemini-embedding-2` (GA) is also supported for multimodal, same as AI.GENERATE_EMBEDDING.

**BigFrames API:** No direct `ML.GENERATE_EMBEDDING` wrapper. BigFrames routes through `AI.GENERATE_EMBEDDING` instead. Use `bbq.ai.generate_embedding()` or `TextEmbeddingGenerator`/`MultimodalEmbeddingGenerator` classes.

---
