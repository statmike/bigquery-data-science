# `AI.GENERATE_INT`

> **Source:** [`bigquery-ai/reference/general-purpose-functions.md#aigenerate_int`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/general-purpose-functions.md#aigenerate_int)

- **Description:** (Preview) Scalar function that analyzes any combination of text and unstructured data, returning a STRUCT containing an INT64 value. Sends requests to a Vertex AI Gemini model. Contact `bqml-feedback@google.com` for support during preview.
- **Use cases:** Population counts / numeric fact retrieval, counting / quantity estimation, classification with integer labels, scoring with integer values.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-generate-int)
- **Type:** Scalar function (returns a STRUCT value per row) -- Preview

**Syntax:**
```sql
AI.GENERATE_INT(
  [prompt =>] 'PROMPT',
  [, endpoint => 'ENDPOINT']
  [, model_params => MODEL_PARAMS]
  [, connection_id => 'CONNECTION']
  [, request_type => 'REQUEST_TYPE']
)
```

**Inputs:** Identical parameter set to AI.GENERATE_BOOL (see above for full details).

**Outputs:**

Returns a STRUCT per row:

| Field | Type | Description |
|-------|------|-------------|
| `result` | INT64 | Model's integer response. NULL if request fails or is filtered. |
| `full_response` | JSON | Full response from generateContent. |
| `status` | STRING | API response status (empty = success). |

**Supported models:** Any GA or preview Gemini model. Default: `gemini-3.5-flash-lite`.

**Best practices:** Same as AI.GENERATE_BOOL.

**Limitations:** Same as AI.GENERATE_BOOL (Preview, video limits, thinking charges).

**Locations:** All Gemini-supporting regions plus US and EU multi-regions.

**Provisioned throughput:** Supported via `request_type` parameter.

**BigFrames API:** `bigframes.bigquery.ai.generate_int(prompt)` — Scalar function returning a Series of structs with INT64 result. Same tuple prompt pattern as generate_bool. Access result via `.struct.field("result")`.

---
