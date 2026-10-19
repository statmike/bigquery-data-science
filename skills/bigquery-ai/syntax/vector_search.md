# `VECTOR_SEARCH`

> **Source:** [`bigquery-ai/reference/embedding-generation-and-semantic-search.md#vector_search`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/embedding-generation-and-semantic-search.md#vector_search)

- **Description:** Table-valued function that searches embeddings to find the top-K closest embeddings from a base table to a given query embedding. Supports both batch searches (multiple query rows) and single searches (one embedding value). Can use vector indexes for approximate nearest neighbor (ANN) search. The single search syntax additionally supports **hybrid search** -- combining semantic similarity with lexical (keyword) matching -- via `lexical_search_columns` and `lexical_search_query_value`.
- **Use cases:** Semantic search, hybrid semantic + keyword search, recommendation systems, classification, clustering, retrieval augmented generation (RAG).
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/search_functions#vector_search)
- **Type:** Table-valued function (TVF) -- GA (single search syntax is Preview)

**Syntax (batch search):**
```sql
VECTOR_SEARCH(
  { TABLE base_table | (base_table_query) },
  column_to_search,
  { TABLE query_table | (query_table_query) },
  [, query_column_to_search => query_column_to_search_value]
  [, top_k => top_k_value]
  [, distance_type => distance_type_value]
  [, options => options_value]
)
```

**Syntax (single search -- Preview; also the hybrid search syntax):**
```sql
VECTOR_SEARCH(
  { TABLE base_table | (base_table_query) },
  column_to_search,
  query_value => single_query_value,
  [, lexical_search_columns => lexical_search_columns_value]
  [, lexical_search_query_value => single_lexical_search_query_value]
  [, top_k => top_k_value]
  [, distance_type => distance_type_value]
  [, options => options_value]
)
```

Supplying a non-empty `lexical_search_columns` is what makes the search hybrid. Hybrid search is only available in the single search syntax -- **there is no batch hybrid search**. See [Hybrid Search](hybrid-search-capability.md) below for how the fused score is computed.

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `base_table` / `base_table_query` | Table/Query | Required | The table to search. Only SELECT, FROM, WHERE clauses allowed in query. Don't filter the embedding column. Can't use logical views. |
| `column_to_search` | STRING | Required | Base table column to search. Must be ARRAY\<FLOAT64\> or STRING (Preview, requires autonomous embedding generation). If indexed, BigQuery attempts to use it. |
| `query_table` / `query_table_query` | Table/Query | Required for batch | Query embeddings to find nearest neighbors for. |
| `query_column_to_search` | Named arg, STRING | Optional (batch only) | Column in query table containing embeddings. ARRAY\<FLOAT64\> or STRING. |
| `query_value` | Named arg, ARRAY\<FLOAT64\> or STRING | Required for single search | Single embedding or string to search for. |
| `lexical_search_columns` | Named arg, ARRAY\<STRING\> | Optional (single search only) | Base table columns to match lexically. Non-empty value switches the call to hybrid search. If the base table has a vector index with `lexical_search_columns`, these columns must be a subset of the indexed ones. |
| `lexical_search_query_value` | Named arg, STRING | Optional (single search only) | The keyword query text for the lexical leg. Defaults to `query_value` when that is a STRING. |
| `top_k` | Named arg, INT64 | Optional | Number of nearest neighbors per query. Default: 10. Negative = return all. |
| `distance_type` | Named arg, STRING | Optional | `EUCLIDEAN` (default), `COSINE`, or `DOT_PRODUCT`. |
| `options` | Named arg, JSON STRING | Optional | `fraction_lists_to_search` (0.0-1.0, index only), `use_brute_force` (boolean). |

**Outputs (batch search):**

| Column | Type | Description |
|--------|------|-------------|
| `query` | STRUCT | All selected columns from the query data |
| `base` | STRUCT | All columns from base_table |
| `distance` | FLOAT64 | Distance between base and query data |

**Outputs (single search):** Same but without the `query` column.

**Outputs (hybrid search):** Same shape as single search, but `distance` is **not a distance** -- it is a reciprocal rank fusion (RRF) score derived from the row's rank in the semantic and lexical result lists. Hybrid `distance` values are not comparable to semantic-only `distance` values. See [Hybrid Search](hybrid-search-capability.md).

**Supported models:** VECTOR_SEARCH does not directly reference models. Operates on pre-computed ARRAY\<FLOAT64\> embeddings or STRING columns with autonomous embedding generation. Embeddings can come from any source (AI.EMBED, AI.GENERATE_EMBEDDING, external).

**Best practices:** Use a vector index for large base tables. Use brute force for exact results. Use single search syntax for single queries (optimized performance).

**Limitations:** Row-level and column-level security policies apply. Project running the query must match the project containing the base table. Subqueries in base_table_query might interfere with index usage. Logical views cannot be used. Hybrid search requires the single search syntax and therefore cannot be combined with batch search.

**Locations:** Not specified specifically -- operates wherever BigQuery tables exist.

**Provisioned throughput:** Not specified. When used with autonomous embedding generation on STRING columns, generative AI function limits apply.

**BigFrames API:** `bigframes.bigquery.vector_search(base_table, column_to_search, query)` — Takes base table as string, query as DataFrame/Series. Supports `distance_type`, `top_k`, `fraction_lists_to_search`, `use_brute_force`. Also `bigframes.bigquery.create_vector_index()` for creating vector indexes.

---
