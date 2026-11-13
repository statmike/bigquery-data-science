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
| `endpoint` | STRING | Optional | `gemini-3.5-flash-lite` | The model endpoint on the Gemini Enterprise Agent Platform (formerly Vertex AI). Specify any GA or preview Gemini model by name, such as `'gemini-3.8-flash'`, `'gemini-4-argon'`, `'gemini-4-carbon'` (GA `2026-11-10`), or `'gemini-4-hydrogen'` (GA `2026-11-12`) (BigQuery auto-resolves the full endpoint). Can also specify a full global endpoint URL. The default is measured, not inferred -- see [Choosing a Gemini Model Endpoint](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md#choosing-a-gemini-model-endpoint). |
| `model_params` | JSON literal | Optional | -- | Additional parameters conforming to the `generateContent` request body format. Can set any field except `contents`. Supports `thinking_config` (use `thinking_level` (`"LOW"`, `"MEDIUM"`, `"HIGH"`) for Gemini 3.0+ and Gemini 4 models including `gemini-3.8-flash`, `gemini-4-argon`, `gemini-4-carbon`, and `gemini-4-hydrogen`; legacy Gemini 2.5 models used `thinking_budget`), `cachedContent`, `tools` (e.g., `googleSearch` — requires Gemini 2.0+, `googleMaps`), `generation_config`, etc. On all Gemini 4 models (`gemini-4-argon`, `gemini-4-carbon`, `gemini-4-hydrogen`), BigQuery's SQL `model_params` `GenerateContent` proto validator accepts `"LOW"`, `"MEDIUM"`, and `"HIGH"` for `thinking_level` and rejects `"MINIMAL"`, `"XHIGH"`, and `thinking_budget` at query analysis time (`400 The model_params is invalid and does not conform to the GenerateContent request body`), while custom sampling parameters (`temperature`, `top_p`, `top_k`) are ignored. |
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

**Supported models:** Any GA or preview Gemini model; pinned examples standardize on `gemini-3.8-flash` (preferred Flash default; `$0.75 / $3.75` per 1M input/output tokens through Dec 31, 2026, and supports custom `temperature`) and `gemini-4-argon` (preferred Pro / frontier reasoning default, replacing `gemini-2.5-pro`), alongside the newly GA Gemini 4 endpoints `gemini-4-carbon` (GA `2026-11-10`; frontier/Pro reasoning model alongside `gemini-4-argon`, `$2.00 / $10.00` per 1M input/output tokens through Nov 30, 2026 and `$4.00 / $20.00` starting Dec 1, 2026) and `gemini-4-hydrogen` (GA `2026-11-12`; Gemini 4 speed & efficiency model for everyday coding, agentic workflows, multimodal analysis, and tool use, `$1.50 / $7.50` per 1M input/output tokens, `65,536` max output tokens per segment) as well as `gemini-3.5-flash-lite`. All three Gemini 4 models (`gemini-4-argon`, `gemini-4-carbon`, `gemini-4-hydrogen`) share a unified `1,048,576`-token input+output context window. Default when omitted: `gemini-3.5-flash-lite`. Can use global endpoint for cross-region processing.

| Endpoint | Tier / Role | GA Date | Pricing (per 1M input / output tokens) | Context / Max Output | BigQuery SQL `thinking_level` (`model_params`) | Custom Sampling (`temperature` / `top_p` / `top_k`) |
|----------|-------------|---------|----------------------------------------|----------------------|------------------------------------------------|-----------------------------------------------------|
| `gemini-3.8-flash` | Preferred Flash default | 2026-09-10 | `$0.75 / $3.75` (intro through Dec 31, 2026) | `1,048,576` / `65,536` | `"LOW"`, `"MEDIUM"`, `"HIGH"` | Supported |
| `gemini-4-argon` | Preferred Pro / frontier reasoning default | 2026-10-08 | `$2.00 / $10.00` (intro through Nov 30, 2026; `$4.00 / $20.00` Dec 1+) | `1,048,576` unified / `65,536` | `"LOW"`, `"MEDIUM"`, `"HIGH"` (`"MINIMAL"`, `"XHIGH"`, `thinking_budget` rejected with 400) | Ignored |
| `gemini-4-carbon` | Frontier / Pro reasoning | 2026-11-10 | `$2.00 / $10.00` (intro through Nov 30, 2026; `$4.00 / $20.00` Dec 1+) | `1,048,576` unified / `65,536` | `"LOW"`, `"MEDIUM"`, `"HIGH"` (`"MINIMAL"`, `"XHIGH"`, `thinking_budget` rejected with 400) | Ignored |
| `gemini-4-hydrogen` | Gemini 4 speed & efficiency (coding, agentic, multimodal, tool use) | 2026-11-12 | `$1.50 / $7.50` | `1,048,576` unified / `65,536` | `"LOW"`, `"MEDIUM"`, `"HIGH"` (`"MINIMAL"`, `"XHIGH"`, `thinking_budget` rejected with 400) | Ignored |
| `gemini-3.5-flash-lite` | Low-cost / high-throughput (unpinned default) | 2026-05-14 | `$0.10 / $0.40` | `1,048,576` / `65,536` | `"LOW"`, `"MEDIUM"`, `"HIGH"` | Supported |

**Best practices:**
- Function incurs Vertex AI charges each time it is called. Track costs accordingly.
- To minimize charges when using LIMIT, materialize the selected data to a table first, then call AI.GENERATE on that table (avoids re-evaluating the subquery).

**Limitations:**
- Video input limited to 2 minutes maximum (only first 2 min processed).
- At most one video object per prompt.
- Global endpoint does not allow controlling or knowing the data processing region.
- Gemini 2.5 models incur thinking charges; budget can be set for Flash/Flash-Lite but not Pro.
- Google Search grounding requires Gemini 2.0 or later models.
- For Gemini 3.0+ and Gemini 4 (`gemini-3.8-flash`, `gemini-4-argon`, `gemini-4-carbon`, `gemini-4-hydrogen`), use `thinking_level` (`"LOW"`, `"MEDIUM"`, `"HIGH"`) in `thinking_config` instead of `thinking_budget`. Even though the Vertex AI Gemini 4 Hydrogen model card lists `"XHIGH"`, BigQuery's SQL `model_params` `GenerateContent` proto validator rejects both `"MINIMAL"` and `"XHIGH"` (and `thinking_budget`) at query analysis time (`400 The model_params is invalid and does not conform to the GenerateContent request body`).
- All three Gemini 4 models (`gemini-4-argon`, `gemini-4-carbon`, `gemini-4-hydrogen`) ignore custom sampling parameters (`temperature`, `top_p`, `top_k`); use `gemini-3.8-flash` when custom `temperature` control is required.

**Locations:** All regions that support Gemini models, plus US and EU multi-regions.

**Provisioned throughput:** Supported via `request_type` parameter. Must purchase Provisioned Throughput quota matching the same Gemini model and region. For US multi-region: select `us-central1` region when purchasing. For EU multi-region: select `europe-west4` region when purchasing.

**BigFrames API:** `bigframes.bigquery.ai.generate()` — Scalar function returning a Series of structs. Supports `output_schema` as `Mapping[str, str]`. Prompt is a tuple of string literals and Series: `bbq.ai.generate(("Summarize: ", df["text"]), output_schema={"summary": "STRING"})`. Access result via `.struct.field("result")`. Prefer `bbq.ai.generate` / `bbq.ai.generate_text` over `bigframes.ml.llm.GeminiTextGenerator`, which in `bigframes 2.51.0` hardcodes a client-side `_GEMINI_ENDPOINTS` allowlist (`gemini-1.5-*`, `gemini-2.0-*`, `gemini-2.5-*`) and emits an `UnknownModelWarning` for `gemini-3.8-flash`, `gemini-4-argon`, `gemini-4-carbon`, or `gemini-4-hydrogen` even though `CREATE MODEL` succeeds.

### Reusable column aliases for unpacking `AI.*` outputs

Calling `AI.GENERATE` (or `AI.GENERATE_BOOL` / `_DOUBLE` / `_INT` / `AI.TRANSLATE(..., return_details => TRUE)`) returns a `STRUCT`. Historically, unpacking multiple `STRUCT` fields and filtering `WHERE status = ''` without invoking the model multiple times per row required wrapping the call in a `WITH` CTE or subquery. With **reusable column aliases** ([column aliases guide](https://docs.cloud.google.com/bigquery/docs/column-aliases) · [query syntax](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax#using_aliases)), a `SELECT`-list alias can be referenced laterally to the right in the **same** `SELECT` list and in `WHERE`, evaluating `AI.GENERATE` once per row:

```sql
-- Check whether reusable_column_aliases_mode is enabled in the region:
SELECT option_name, option_value
FROM `region-us`.INFORMATION_SCHEMA.EFFECTIVE_PROJECT_OPTIONS
WHERE option_name = 'reusable_column_aliases_mode';

-- Enable project-wide for a region (requires bigquery.projects.update / roles/bigquery.admin; bigquery.organizations.update at org level):
ALTER PROJECT `your-gcp-project-id`
SET OPTIONS (`region-us.reusable_column_aliases_mode` = 'on');

-- Single-SELECT unpacking + WHERE filtering (AI.GENERATE runs once per row):
SELECT
  review_id,
  AI.GENERATE(
    ('Extract sentiment and 1-sentence summary: ', review_text),
    endpoint => 'gemini-3.8-flash',
    output_schema => 'sentiment STRING, summary STRING'
  ) AS ai_gen,
  ai_gen.sentiment,
  ai_gen.summary,
  JSON_VALUE(ai_gen.full_response, '$.modelVersion') AS model_version
FROM `your-gcp-project-id.DATASET_ID.reviews`
WHERE ai_gen.status = '';
```

**GOTCHA — 5-tier name resolution & 2 silent shadowing traps:**
When `reusable_column_aliases_mode = 'on'`, GoogleSQL resolves bare identifiers in strict precedence order from highest (`#1`) to lowest (`#5`):
1. `FROM` clause table column names *(highest — silently shadows a `SELECT` alias of the same name!)*
2. Reusable column aliases defined to the left in the current `SELECT` list *(silently shadows `#3`–`#5`!)*
3. Correlated column names from outer query scopes
4. SQL UDF / TVF parameter names
5. Procedural language (`DECLARE`) script variables *(lowest)*

Two silent shadowing traps follow directly from this order:
- **Trap 1 (`FROM` column shadows `SELECT` alias):** If the input table already has a column named `gen`, `result`, or `score`, defining `AI.GENERATE(...) AS gen` and referencing `gen.sentiment` (or `WHERE score > 0.8`) resolves to the **`FROM` table column**, ignoring your `SELECT` alias with no warning!
- **Trap 2 (`SELECT` alias shadows outer/UDF/script names):** A `SELECT` alias silently overrides correlated outer columns (`#3`), UDF/TVF parameters (`#4`), and `DECLARE` variables (`#5`) of the same name. Always pick a distinct alias prefix (such as `ai_gen`) that never collides with table columns, parameters, or variables.

**Documented limitations:**
1. In queries with grouping or aggregation (`GROUP BY` or aggregate functions), aliases to unaggregated expressions (grouping columns or projections of grouping columns) cannot be referenced in the `WHERE` clause or as arguments to aggregate functions.
2. Aliases over **aggregate** (`AI.AGG`, `COUNT`) or **window** functions cannot be referenced in `WHERE` or nested inside another aggregate function (filter aggregates in `HAVING` and window outputs in `QUALIFY`).
3. A **window function** cannot reference an alias defined by another window function in the same `SELECT` list.
4. **Not supported in pipe query syntax (`|>`)** — pipe syntax natively provides `|> EXTEND AI.GENERATE(...) AS ai_gen |> SELECT ai_gen.result` without any project option.
5. **Not supported in Graph Query Language (`GRAPH_TABLE` / GQL)**.

**Portability guidance:** Because `reusable_column_aliases_mode = 'on'` is an opt-in regional project option, keep a standard `WITH generated AS (...)` CTE in shared SQL scripts, public notebooks, and cross-project templates that must run unmodified in projects where the option is unset.

---
