# `AI.IF`

> **Source:** [`bigquery-ai/reference/managed-functions.md#aiif`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/managed-functions.md#aiif)

- **Description:** (Preview) Scalar function that uses a Vertex AI Gemini model to evaluate a condition described in natural language and returns a BOOL. BigQuery automatically structures (optimizes) your prompts to improve the quality of the output.
- **Use cases:** Sentiment analysis (find negative reviews), topic analysis (identify articles on a subject), image analysis (select images containing a specific item), security (identify suspicious emails), filtering in WHERE clauses, joining tables based on semantic or multimodal conditions.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-if)
- **Type:** Scalar function -- returns a single BOOL value per row (Preview)

**Syntax:**
```sql
AI.IF(
  [ prompt => ] 'PROMPT'
  [, examples => EXAMPLES ]
  [, connection_id => 'CONNECTION' ]
  [, endpoint => 'ENDPOINT' ]
  [, embeddings => EMBEDDINGS ]
  [, optimization_mode => 'OPTIMIZATION_MODE' ]
  [, max_error_ratio => MAX_ERROR_RATIO ]
)
```

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `PROMPT` | STRING or STRUCT | Required (must be first argument) | The prompt value to send to the model. STRING or STRUCT with STRING/ARRAY\<STRING\>/ObjectRef/ARRAY\<ObjectRef\> fields. At most one video object. |
| `EXAMPLES` | ARRAY\<STRUCT\<STRING, BOOL\>\> | Optional | Few-shot examples to guide the model. Each struct maps an example input string to an expected BOOL output. Example: `[("I love this product", TRUE), ("The product performed well", FALSE)]`. |
| `CONNECTION` | STRING | Optional | Connection to use, format: `[PROJECT_ID].LOCATION.CONNECTION_ID`. If not specified, end-user credentials are used. |
| `ENDPOINT` | STRING | Optional | Vertex AI endpoint. Any GA or preview Gemini model. If not specified, BigQuery ML dynamically chooses a model for best cost-to-quality tradeoff. |
| `EMBEDDINGS` | (Preview) | Optional | Embeddings for optimized mode. Can be generated on-the-fly via `AI.EMBED(...)` or pre-materialized. If autonomous embedding generation is enabled on the table, BigQuery automatically uses the embeddings. |
| `OPTIMIZATION_MODE` | STRING | Optional (Preview) | `MINIMIZE_COST` (default when embeddings provided — trains a local distilled model, up to 230x token reduction) or `MAXIMIZE_QUALITY` (always uses remote LLM). Requires ~3,000 rows minimum. |
| `MAX_ERROR_RATIO` | FLOAT64 | Optional | Range 0.0–1.0, default 1.0. If the error ratio exceeds this threshold, the query fails with an error describing the most frequent error types. Not supported when `optimization_mode` is `MINIMIZE_COST`. |

**Outputs:**

| Return Type | Description |
|-------------|-------------|
| BOOL | The result of evaluating the condition in the input prompt. |
| NULL | Returned if the call to Vertex AI is unsuccessful for any reason. |

**Supported models:** Any GA or preview Gemini model. If no endpoint specified, BigQuery dynamically chooses for best cost-to-quality tradeoff. Uses various `gemini-2.5-*` models.

**Best practices:**
- BigQuery optimizes queries to reduce Gemini calls. Place non-AI filters alongside AI.IF -- non-AI filters are evaluated first (e.g., `WHERE AI.IF(...) AND category = 'tech'`).
- Do not use the global endpoint if you have data processing location requirements.

**Limitations:** Preview status. Returns NULL on error (no detailed error info). No model parameter control (temperature, top_p, etc.) unlike AI.GENERATE_BOOL. At most one video object per input. Optimized mode requires ~3,000 rows minimum; only string columns supported for multi-column prompts in optimized mode.

**Locations:** All regions supporting Gemini models, plus US and EU multi-regions.

**Provisioned throughput:** Not supported. Uses dynamic shared quota (DSQ) only.

**BigFrames API:** `bigframes.bigquery.ai.if_(prompt)` — Returns a Series of BOOL directly (not a struct, unlike generate_bool). No endpoint param -- auto-selects model. Example: `bbq.ai.if_((df["review"], " is a positive review"))`. Can be used for boolean indexing: `df[bbq.ai.if_(...)]`.

---
