# `AI.GENERATE_TABLE`

> **Source:** [`bigquery-ai/reference/general-purpose-functions.md#aigenerate_table`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/general-purpose-functions.md#aigenerate_table)

- **Description:** Table-valued function that performs generative natural language tasks and formats the response according to a user-specified schema. Requires a pre-created remote model representing a Vertex AI Gemini model.
- **Use cases:** Classification, sentiment analysis, image captioning, transcription, entity extraction with structured output, data formatting/enrichment using custom schemas.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-generate-table)
- **Type:** Table-valued function (returns a table with input columns plus structured output columns)

**Syntax:**
```sql
AI.GENERATE_TABLE(
  MODEL `PROJECT_ID.DATASET.MODEL`,
  { TABLE `PROJECT_ID.DATASET.TABLE` | (QUERY_STATEMENT) },
  STRUCT(
    OUTPUT_SCHEMA AS output_schema
    [, MAX_OUTPUT_TOKENS AS max_output_tokens]
    [, TOP_P AS top_p]
    [, TEMPERATURE AS temperature]
    [, STOP_SEQUENCES AS stop_sequences]
    [, SAFETY_SETTINGS AS safety_settings]
    [, REQUEST_TYPE AS request_type]
  )
)
```

**Inputs:**

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `MODEL` | Model reference | Required | -- | -- | Name of the remote model (must be a Gemini model) |
| `TABLE` / `QUERY_STATEMENT` | Table/Query | Required (one of) | -- | -- | Input data. Must produce a `prompt` column. |
| `output_schema` | STRING | Required | -- | -- | Schema as comma-separated fields with name, type, optional `OPTIONS(description='...')`. Supported types: `STRING`, `INT64`, `FLOAT64`, `BOOL`, `ARRAY`, `STRUCT`. |
| `max_output_tokens` | INT64 | Optional | Model-determined | [1, 8192] | Max tokens in response |
| `top_p` | FLOAT64 | Optional | Model-determined | [0.0, 1.0] | Nucleus sampling |
| `temperature` | FLOAT64 | Optional | Model-determined | [0.0, 2.0] | Randomness control |
| `stop_sequences` | ARRAY\<STRING\> | Optional | Empty array | -- | Strings to exclude |
| `safety_settings` | ARRAY\<STRUCT\<STRING AS category, STRING AS threshold\>\> | Optional | BLOCK_MEDIUM_AND_ABOVE | -- | Content safety thresholds |
| `request_type` | STRING | Optional | UNSPECIFIED | SHARED, DEDICATED, UNSPECIFIED | Provisioned Throughput quota control |

Prompt input can be a STRING value or a STRUCT value with STRING, ARRAY\<STRING\>, ObjectRef, or ARRAY\<ObjectRef\> fields (same semantics as AI.GENERATE_TEXT).

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| All input table columns | (varies) | Pass-through of input |
| Custom schema columns | As specified in `output_schema` | Columns from your schema definition |
| `full_response` | JSON | Response from `projects.locations.endpoints.generateContent` |
| `status` | STRING | API response status (empty = success) |

**Supported models:** Remote models over any GA or preview Gemini models (via CREATE MODEL).

**Best practices:** To minimize Vertex AI charges, write query results to a table and then reference that table. Model and input table must be in the same region.

**Limitations:** Model and input table must be in the same region. Resource exhausted errors possible. Video limited to 2 minutes. Gemini 2.5 models incur thinking charges.

**Locations:** Must run in the same region or multi-region as the remote model. Supported Gemini regions plus US and EU multi-regions.

**Provisioned throughput:** Supported via `request_type` parameter.

**BigFrames API:** `bigframes.bigquery.ai.generate_table(model, data, output_schema=...)` — TVF wrapper that takes a model name string, DataFrame/Series, and required `output_schema` (string or mapping). Also accessible via `GeminiTextGenerator.predict(X, output_schema={"col": "type"})` which routes to GENERATE_TABLE under the hood.

---
