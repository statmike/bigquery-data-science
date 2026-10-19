# `AI.SEARCH`

> **Source:** [`bigquery-ai/reference/embedding-generation-and-semantic-search.md#aisearch`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/embedding-generation-and-semantic-search.md#aisearch)

- **Description:** Table-valued function for semantic and hybrid search on tables that have autonomous embedding generation enabled. Embeds the search query at runtime and searches the specified table. Uses vector indexes when available.
- **Use cases:** Semantic search, hybrid semantic + keyword search, recommendation, classification, clustering, outlier detection.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-search)
- **Type:** Table-valued function (TVF) -- GA (the `mode` argument is Preview)

**Syntax:**
```sql
AI.SEARCH(
  { TABLE base_table | base_table_query },
  column_to_search,
  query_value
  [, mode => mode_value]
  [, top_k => top_k_value]
  [, distance_type => distance_type_value]
  [, options => options_value]
)
```

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `base_table` / `base_table_query` | Table/Query | Required | Table to search. **Must have autonomous embedding generation enabled.** |
| `column_to_search` | STRING literal | Required | Name of the **source string column** (not the generated embedding column). |
| `query_value` | STRING literal | Required | Search query text. Embedded at runtime using the base table's connection and endpoint. |
| `mode` | Named arg, STRING | Optional (Preview) | `AUTO` (default), `VECTOR`, or `HYBRID`. See below. |
| `top_k` | Named arg, INT64 | Optional | Default: 10. Negative = return all. |
| `distance_type` | Named arg, STRING | Optional | `EUCLIDEAN` (default), `COSINE`, or `DOT_PRODUCT`. Ignored in `HYBRID` mode. |
| `options` | Named arg, JSON STRING | Optional | `fraction_lists_to_search`, `use_brute_force`. |

**Search modes:**

| Mode | Behavior |
|------|----------|
| `AUTO` | Default. Runs hybrid search **only if** the base table has a vector index configured with `lexical_search_columns`; otherwise silently runs semantic-only search. |
| `VECTOR` | Semantic-only search. `distance` is a true distance in the chosen `distance_type`. |
| `HYBRID` | Combines semantic and lexical matching on `column_to_search`. Runs with or without a vector index. `distance` is an RRF score, not a distance. |

> **Gotcha:** `AUTO` does not mean "hybrid". Because a vector index cannot currently be built on an autonomous embedding generation column (see [Hybrid Search](hybrid-search-capability.md)), `AUTO` on an AI.SEARCH base table resolves to semantic-only. The query succeeds either way, so the fallback is silent. Specify `mode => 'HYBRID'` explicitly when you want hybrid behavior.

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `base` | STRUCT | All columns from base_table |
| `distance` | FLOAT64 | In `VECTOR`/`AUTO`-semantic mode, the distance between the query_value embedding and the base embedding. In `HYBRID` mode, a reciprocal rank fusion score -- not a distance, and not comparable across modes. |

**Supported models:** Uses whatever embedding model and connection are configured for the base table's autonomous embedding generation.

**AI.SEARCH vs VECTOR_SEARCH:** Use AI.SEARCH for simplified semantic or hybrid search when the base table has autonomous embedding generation and you want to search for a single string literal. Use VECTOR_SEARCH for batch queries, custom embeddings, control over which columns are matched lexically, or tables without autonomous embedding generation. In hybrid mode AI.SEARCH matches lexically only against `column_to_search`; VECTOR_SEARCH lets you name any set of columns in `lexical_search_columns`.

**Best practices:** Create a vector index on the embedding column for better performance on large tables. State `mode` explicitly rather than relying on `AUTO`.

**Limitations:** Base table must have autonomous embedding generation enabled. If embedding generation fails for query_value, the entire query fails. Rows with missing embeddings are skipped. Hybrid mode matches lexically only on `column_to_search`.

**Locations:** All locations supporting Vertex AI embedding models, plus US and EU multi-regions.

**Provisioned throughput:** Not specified in documentation.

**BigFrames API:** No direct equivalent. Use `%%bigquery` magics or `session.read_gbq_query()` to execute AI.SEARCH SQL from BigFrames.

---
