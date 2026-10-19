# `AI.AGG`

> **Source:** [`bigquery-ai/reference/managed-functions.md#aiagg`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/managed-functions.md#aiagg)

- **Description:** (Preview) Aggregate function that uses a Vertex AI Gemini model to aggregate data based on natural language instructions. Automatically performs multi-level aggregation through batching, so it can analyze data exceeding the Gemini context window. Returns a single STRING per group.
- **Use cases:** Sentiment analysis across reviews, content summarization of text or images, log analysis and incident investigation, agent performance analysis, finding common categories or patterns across data, summarizing grouped data.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-agg)
- **Type:** Aggregate function -- returns a single STRING value per group (Preview). Use with GROUP BY for per-group results; without GROUP BY, aggregates all rows.

**Syntax:**
```sql
AI.AGG(
  [ DISTINCT ]
  INPUT,
  INSTRUCTION
  [, connection_id => 'CONNECTION']
  [, endpoint => 'ENDPOINT']
)
```

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `DISTINCT` | keyword | Optional | When specified, deduplicates input values before aggregating. |
| `INPUT` | STRING or STRUCT | Required (must be first argument) | The data to aggregate. STRING value, or STRUCT consisting of STRING values, object references, and arrays of either. **The reference page still specifies `ObjectRefRuntime` here — it is the only `AI.*` page that does.** A bare `ObjectRef` works anyway: `AI.AGG(STRUCT(ref), instruction)` over an object table returns real summaries (verified live 2026-09-15 over 50 PDFs), and the Known Issues below argue for it. |
| `INSTRUCTION` | STRING | Required (must be second argument) | Natural language aggregation prompt describing what to extract or summarize from the input data. Can be a string literal or query parameter. |
| `CONNECTION` | STRING | Optional | Connection to use, format: `[PROJECT_ID.]LOCATION.CONNECTION_ID`. If not specified, end-user credentials are used. |
| `ENDPOINT` | STRING | Optional | Vertex AI endpoint. Any Gemini model that doesn't require thinking budget. If not specified, BigQuery chooses a model for you. |

**Outputs:**

| Return Type | Description |
|-------------|-------------|
| STRING | The aggregated result for the group. One result per GROUP BY group, or one result total without GROUP BY. |
| STRING (partial) | If some Vertex AI calls fail, returns partial results from successful calls. |
| NULL | Returned if all calls to Vertex AI fail, or if all input rows are invalid. |

**Output cap:** 10,000 tokens per group.

**Supported models:** Any Gemini model that doesn't require thinking budget. If no endpoint specified, BigQuery dynamically chooses a model. Uses various `gemini-2.5-*` models.

**Best practices:**
- Use `TO_JSON_STRING` to pass multiple columns as structured input -- the model sees each row's full context.
- Use `DISTINCT` to remove duplicate inputs and reduce token usage.
- Keep groups under 20 million rows per query and under 1,000 distinct groups to avoid timeouts.
- Prefer AI.AGG over manual aggregation with AI.GENERATE (STRING_AGG/ARRAY_AGG into a prompt) -- AI.AGG handles batching automatically and scales beyond the context window.

**Limitations:** Preview status. Returns NULL on total failure (no detailed error info). No model parameter control (temperature, top_p, etc.). Output capped at 10,000 tokens per group. Recommended limit of 20 million rows per query and 1,000 distinct groups. Cannot use Gemini models that require thinking budget.

**Known issues:**
- Input rows with 10 or more images in a single row might be skipped.
- Input rows with arrays of ObjectRefRuntime objects that call `OBJ.GET_ACCESS_URL` might be skipped.
- Some ObjectRefRuntime **image** objects created by `OBJ.GET_ACCESS_URL` might fail to process.
- Both of the above are about `ObjectRefRuntime` specifically. Passing the `ObjectRef` sidesteps them — the practical argument for the unwrapped form even though this page's `INPUT` row still names the runtime type.
- Individual rows larger than **10 MiB** might fail with an internal error.
- Mixing `AI.AGG()` without `DISTINCT` and another aggregate function *with* `DISTINCT` in the same query might return an internal error.
- Workforce Identity Federation without a specified Cloud resource connection may cause failures on long-running queries.
- Queries using Gemini 3.0 or 3.1 with connection-based authentication might receive an unauthenticated error.

**Cost caveat:** The actual number of rows processed by the model might differ from expectations, particularly with complex queries (JOIN, ORDER BY ... LIMIT). Materialize data to a separate table first to ensure predictable processing.

**Locations:** All regions supporting Gemini models, plus US and EU multi-regions.

**Provisioned throughput:** Not supported. Uses dynamic shared quota (DSQ) only.

**BigFrames API:** No native BigFrames API. Use `bpd.read_gbq_query(sql)` to execute AI.AGG queries and get results as a BigFrames DataFrame.
