# `AI.GENERATE_BOOL`

> **Source:** [`bigquery-ai/reference/general-purpose-functions.md#aigenerate_bool`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/general-purpose-functions.md#aigenerate_bool)

- **Description:** (Preview) Scalar function that analyzes any combination of text and unstructured data, returning a STRUCT containing a BOOL value for each row. Sends requests to a Vertex AI Gemini model. Contact `bqml-feedback@google.com` for support during preview.
- **Use cases:** Classification (e.g., "Is this article about technology?"), boolean filtering in WHERE clauses, sentiment analysis (positive/negative as boolean), image classification (e.g., "Is this cat food?").
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-generate-bool)
- **Type:** Scalar function (returns a STRUCT value per row) -- Preview

**Syntax:**
```sql
AI.GENERATE_BOOL(
  [prompt =>] 'PROMPT',
  [, endpoint => 'ENDPOINT']
  [, model_params => MODEL_PARAMS]
  [, connection_id => 'CONNECTION']
  [, request_type => 'REQUEST_TYPE']
)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` (positional, must be first) | STRING or STRUCT | Required | -- | Same semantics as AI.GENERATE: STRING or STRUCT with STRING/ARRAY\<STRING\>/ObjectRef/ARRAY\<ObjectRef\> fields. At most one video. |
| `endpoint` | STRING | Optional | `gemini-3.5-flash-lite` | Any GA or preview Gemini model. BigQuery auto-resolves the full endpoint from model name -- see [Choosing a Gemini Model Endpoint](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md#choosing-a-gemini-model-endpoint) for the 3.x multi-regional restriction. |
| `model_params` | JSON literal | Optional | -- | Conforms to generateContent request body (all fields except `contents`). Supports thinking_config, etc. |
| `connection_id` | STRING | Optional | End-user credentials | Format: `[PROJECT_ID].LOCATION.CONNECTION_ID` |
| `request_type` | STRING | Optional | UNSPECIFIED | `SHARED`, `DEDICATED`, `UNSPECIFIED` |

**Outputs:**

Returns a STRUCT per row:

| Field | Type | Description |
|-------|------|-------------|
| `result` | BOOL | Model's boolean response. NULL if request fails or is filtered. |
| `full_response` | JSON | Full response from `projects.locations.endpoints.generateContent`. |
| `status` | STRING | API response status (empty = success). |

**Supported models:** Any GA or preview Gemini model. Default: `gemini-3.5-flash-lite`.

**Best practices:** Incurs Vertex AI charges each call. Materialize data to a table before calling with LIMIT to minimize charges.

**Limitations:** Preview feature (Pre-GA Offerings Terms apply). Video limited to 2 minutes. At most one video object per prompt. Gemini 2.5 thinking charges apply. For Gemini 3.0+, use `thinking_level` in `thinking_config` instead of `thinking_budget`.

**Locations:** All regions supporting Gemini models, plus US and EU multi-regions.

**Provisioned throughput:** Supported via `request_type` parameter.

**BigFrames API:** `bigframes.bigquery.ai.generate_bool(prompt)` — Scalar function returning a Series of structs with BOOL result. Same tuple prompt pattern: `bbq.ai.generate_bool(("Is ", df["item"], " a fruit?"))`. Access result via `.struct.field("result")`.

---
