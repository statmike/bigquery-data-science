# `AI.GENERATE`

> **Source:** [`bigquery-ai/reference/general-purpose-functions.md#aigenerate`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/general-purpose-functions.md#aigenerate)

- **Description:** Scalar function that analyzes any combination of structured and unstructured data. You can generate text or structured output according to a custom schema. Sends requests to a Vertex AI Gemini model and returns a STRUCT containing generated data, the full model response, and a status.
- **Use cases:** Summarization, translation, entity extraction, classification, sentiment analysis, image analysis/captioning (via ObjectRef), grounding with Google Search or Google Maps, any general-purpose generative AI task.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-generate)
- **Type:** Scalar function (returns a STRUCT value per row)

**Syntax:**
```sql
AI.GENERATE(
  [prompt =>] 'PROMPT',
  [, endpoint => 'ENDPOINT']
  [, model_params => MODEL_PARAMS]
  [, output_schema => 'OUTPUT_SCHEMA']
  [, connection_id => 'CONNECTION']
  [, request_type => 'REQUEST_TYPE']
)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` (positional, must be first) | STRING or STRUCT | Required | -- | The prompt to send to the model. Can be a STRING value or a STRUCT containing one or more fields of type STRING, ARRAY\<STRING\>, ObjectRef, or ARRAY\<ObjectRef\>. STRUCT fields are concatenated in order (like CONCAT), so the field *names* carry no meaning. At most one video object is allowed. |
| `endpoint` | STRING | Optional | `gemini-3.5-flash-lite` | The model endpoint on the Gemini Enterprise Agent Platform (formerly Vertex AI). Specify any GA or preview Gemini model by name (BigQuery auto-resolves the full endpoint). Can also specify a full global endpoint URL. The default is measured, not inferred -- see [Choosing a Gemini Model Endpoint](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md#choosing-a-gemini-model-endpoint). |
| `model_params` | JSON literal | Optional | -- | Additional parameters conforming to the `generateContent` request body format. Can set any field except `contents`. Supports `thinking_config` (use `thinking_budget` for Gemini 2.5 models, `thinking_level` for Gemini 3.0+), `cachedContent`, `tools` (e.g., `googleSearch` — requires Gemini 2.0+, `googleMaps`), `generation_config`, etc. |
| `output_schema` | STRING | Optional | -- | Schema for structured output as comma-separated fields. Each field has a name, data type, and optional `OPTIONS(description = '...')`. Supported types: `STRING`, `INT64`, `FLOAT64`, `BOOL`, `ARRAY`, `STRUCT`. When specified, replaces the `result` field in output with custom schema fields. |
| `connection_id` | STRING | Optional | End-user credentials | Connection for model communication, in format `[PROJECT_ID].LOCATION.CONNECTION_ID`. |
| `request_type` | STRING | Optional | `UNSPECIFIED` | Quota type. Values: `SHARED` (DSQ only), `DEDICATED` (Provisioned Throughput only, error if unavailable), `UNSPECIFIED` (default -- uses Provisioned Throughput first if purchased, overflows to DSQ). |

**ObjectRef/Unstructured Data Input Details:**
- An `ObjectRef` from `OBJ.MAKE_REF('gs://path', 'connection')` or an object table's `ref` column. Nothing needs signing first.
- `ObjectRefRuntime` values from `OBJ.GET_ACCESS_URL(objectref, 'r')` are still accepted, but no longer required; if you pass one it must have `access_url.read_url` and `details.gcs_metadata.content_type` populated.
- Content must be in supported Gemini mimeType formats
- Video max length: 2 minutes (only first 2 minutes analyzed if longer)

**Outputs:**

Returns a STRUCT with:

| Field | Type | Description |
|-------|------|-------------|
| `result` | STRING (or custom schema if `output_schema` specified) | The model's response. NULL if request fails or is filtered by responsible AI. When `output_schema` is specified, this field is replaced by the custom schema columns. |
| `full_response` | JSON | Full response from `projects.locations.endpoints.generateContent`. |
| `status` | STRING | API response status. Empty if successful. |

**Supported models:** Any GA or preview Gemini model; the reference page lists `gemini-4-argon` and the Gemini 3.x family. Default: `gemini-3.5-flash-lite`. Can use global endpoint for cross-region processing.

**Best practices:**
- Function incurs Vertex AI charges each time it is called. Track costs accordingly.
- To minimize charges when using LIMIT, materialize the selected data to a table first, then call AI.GENERATE on that table (avoids re-evaluating the subquery).

**Limitations:**
- Video input limited to 2 minutes maximum (only first 2 min processed).
- At most one video object per prompt.
- Global endpoint does not allow controlling or knowing the data processing region.
- Gemini 2.5 models incur thinking charges; budget can be set for Flash/Flash-Lite but not Pro.
- Google Search grounding requires Gemini 2.0 or later models.
- For Gemini 3.0+, use `thinking_level` (`LOW`, `MEDIUM`, `HIGH`) in `thinking_config` instead of `thinking_budget`.

**Locations:** All regions that support Gemini models, plus US and EU multi-regions.

**Provisioned throughput:** Supported via `request_type` parameter. Must purchase Provisioned Throughput quota matching the same Gemini model and region. For US multi-region: select `us-central1` region when purchasing. For EU multi-region: select `europe-west4` region when purchasing.

**BigFrames API:** `bigframes.bigquery.ai.generate()` — Scalar function returning a Series of structs. Supports `output_schema` as `Mapping[str, str]`. Prompt is a tuple of string literals and Series: `bbq.ai.generate(("Summarize: ", df["text"]), output_schema={"summary": "STRING"})`. Access result via `.struct.field("result")`.

---
