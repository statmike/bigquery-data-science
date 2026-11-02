![tracker](https://us-central1-vertex-ai-mlops-369716.cloudfunctions.net/pixel-tracking?path=statmike%2Fbigquery-data-science%2Fbigquery-ai%2Freference&file=managed-functions.md)
<!--- header table --->
<table>
<tr>     
  <td style="text-align: center">
    <a href="https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/managed-functions.md">
      <img width="32px" src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/github.svg" alt="GitHub logo">
      <br>View on<br>GitHub
    </a>
  </td>
</tr>
<tr>
  <td style="text-align: right">
    <b>Share On: </b> 
    <a href="https://www.linkedin.com/sharing/share-offsite/?url=https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/managed-functions.md"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/linkedin.svg" alt="Linkedin Logo" width="20px"></a> 
    <a href="https://reddit.com/submit?url=https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/managed-functions.md"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/reddit.png" alt="Reddit Logo" width="20px"></a> 
    <a href="https://bsky.app/intent/compose?text=https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/managed-functions.md"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/bluesky.svg" alt="BlueSky Logo" width="20px"></a> 
    <a href="https://x.com/intent/post?url=https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/managed-functions.md"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/x.svg" alt="X (Twitter) Logo" width="20px"></a> 
  </td>
</tr>
<tr>
  <td style="text-align: right">
    <b>Connect With Author On: </b> 
    <a href="https://www.linkedin.com/in/statmike"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/linkedin.svg" alt="Linkedin Logo" width="20px"></a>
    <a href="https://github.com/statmike"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/github.svg" alt="GitHub Logo" width="20px"></a> 
    <a href="https://www.youtube.com/@statmike-channel"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/youtube.svg" alt="YouTube Logo" width="20px"></a>
    <a href="https://bsky.app/profile/statmike.bsky.social"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/bluesky.svg" alt="BlueSky Logo" width="20px"></a> 
    <a href="https://x.com/statmike"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/x.svg" alt="X (Twitter) Logo" width="20px"></a>
  </td>
</tr>
<tr>
  <td style="text-align: right">
    <a href="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/bigquery-ai/reference/managed-functions.md"><img src="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/architectures/headers/icons/download.svg" alt="Download icon" width="20px"></a> <a href="https://raw.githubusercontent.com/statmike/bigquery-data-science/main/bigquery-ai/reference/managed-functions.md">Download File</a> <i>(right-click and "Save As")</i>
  </td>
</tr>
</table><br/><br/>

---
# Managed Functions

> Part of the [BigQuery AI Functions Resources](../RESOURCES.md) · [Project README](../README.md)

These are higher-level "managed" AI functions that provide **simplified interfaces** and **managed prompt or service execution** for common tasks without `CREATE MODEL` DDL.

**Key characteristics:**
- All five managed functions — `AI.IF`, `AI.SCORE`, `AI.CLASSIFY`, `AI.AGG`, and `AI.TRANSLATE` — are **GA** (optimized distillation mode via `embeddings` / `optimization_mode` on `AI.IF` and `AI.CLASSIFY` remains in **Preview**).
- `AI.IF`, `AI.SCORE`, `AI.CLASSIFY`, and `AI.TRANSLATE` are **scalar functions** returning simple values (`BOOL`, `FLOAT64`, `STRING` / `ARRAY<STRING>`, or `STRING` / `STRUCT` when `return_details => TRUE` on `AI.TRANSLATE`).
- `AI.AGG` is an **aggregate function** (like `SUM`, `COUNT`) that returns `STRING` (or `STRUCT` with `output_schema`) — one result per `GROUP BY` group.
- `AI.IF`, `AI.SCORE`, `AI.CLASSIFY`, and `AI.AGG` call Gemini using **dynamic shared quota (DSQ)** only (no Provisioned Throughput support) and automatically choose a cost/quality-balanced model when `endpoint` is omitted.
- `AI.TRANSLATE` calls **Cloud Translation Advanced** (`'nmt'` default or `'translation-llm'`) under **end-user credentials (EUC)** rather than Gemini or a Cloud resource connection.
- By default, failed row calls return `NULL` rather than throwing a job error (`AI.TRANSLATE` exposes per-row diagnostics when `return_details => TRUE`).
- Model sampling hyperparameters (`temperature`, `top_p`, etc.) are managed by BigQuery and cannot be overridden.

**Relationships to general-purpose and Cloud AI functions:**
- `AI.IF` relates to `AI.GENERATE_BOOL` — `AI.IF` optimizes prompts and returns a plain `BOOL`; `AI.GENERATE_BOOL` exposes `model_params`, `request_type`, and `full_response`.
- `AI.SCORE` relates to `AI.GENERATE_DOUBLE` — `AI.SCORE` automatically generates a scoring rubric; `AI.GENERATE_DOUBLE` exposes full parameter and response control.
- `AI.CLASSIFY` relates to `AI.GENERATE` with `output_schema` — `AI.CLASSIFY` structures taxonomy prompts automatically and supports single- or multi-label output.
- `AI.AGG` relates to manual `STRING_AGG` / `ARRAY_AGG` batching into `AI.GENERATE` — `AI.AGG` performs automatic multi-level batching beyond a single Gemini context window.
- `AI.TRANSLATE` relates to [`ML.TRANSLATE`](cloud-ai-service-models.md#mltranslate) and [`AI.GENERATE`](general-purpose-functions.md#aigenerate) — `AI.TRANSLATE` needs zero DDL and accepts dynamic per-row `target_language` / `source_language` columns; use `ML.TRANSLATE` when you need connection service-account auth, single-region data residency, `DETECT_LANGUAGE`, or `TRANSLITERATE_TEXT`.

| Feature | AI.IF | AI.SCORE | AI.CLASSIFY | AI.AGG | AI.TRANSLATE |
|---------|-------|----------|-------------|--------|--------------|
| **Release Status** | GA (`embeddings` / `optimization_mode` Preview) | GA | GA (`embeddings` / `optimization_mode` Preview) | GA | GA |
| **Function Type** | Scalar | Scalar | Scalar | Aggregate | Scalar |
| **Backend Service** | Vertex AI Gemini | Vertex AI Gemini | Vertex AI Gemini | Vertex AI Gemini | Cloud Translation (`nmt` \| `translation-llm`) |
| **Return Type** | `BOOL` | `FLOAT64` | `STRING` or `ARRAY<STRING>` | `STRING` or `STRUCT` (`output_schema`) | `STRING` or `STRUCT` (`return_details => TRUE`) |
| **Purpose** | Evaluate natural language condition | Rate/score inputs on a scale | Classify into user-defined categories | Aggregate data with natural language instructions | Translate text across languages per row |
| **Unique Input** | `PROMPT` | `PROMPT` | `INPUT` + `CATEGORIES` + optional `OUTPUT_MODE` | `INPUT` + `INSTRUCTION` | `CONTENT` + `TARGET_LANGUAGE` + optional `SOURCE_LANGUAGE` |
| **Supports DISTINCT / GROUP BY** | No (scalar) | No (scalar) | No (scalar) | Yes (aggregate) | No (scalar) |
| **Connection (`connection_id`)** | Optional (EUC default) | Optional (EUC default) | Optional (EUC default) | Optional (EUC default) | Not supported (EUC only) |
| **Multimodal Support** | Yes (`STRUCT` prompt) | Yes (tuple `(text, ref)`) | Yes (direct `ref` or `STRUCT`) | Yes (`STRUCT(ref)`) | No (`STRING` only) |
| **Few-shot Examples** | Yes (`examples`) | No | Yes (`examples`) | No | No |
| **Optimized Mode** | Yes (`optimization_mode`, `embeddings` — Preview) | No | Yes (`optimization_mode`, `embeddings` — Preview) | No | No |
| **Error Return** | `NULL` | `NULL` | `NULL` | `NULL` (partial on partial failure) | `NULL`, or `STRUCT` (`status != 'OK'`) with `return_details => TRUE` |
| **Provisioned Throughput** | Not supported (DSQ only) | Not supported (DSQ only) | Not supported (DSQ only) | Not supported (DSQ only) | N/A (Cloud Translation quota) |

---

## `AI.IF`
- **Description:** Scalar function that uses a Vertex AI Gemini model to evaluate a condition described in natural language and returns a `BOOL`. BigQuery automatically structures (optimizes) your prompts to improve output quality.
- **Use cases:** Sentiment analysis (find negative reviews), topic analysis (identify articles on a subject), image analysis (select images containing a specific item), security (identify suspicious emails), filtering in `WHERE` clauses, joining tables based on semantic or multimodal conditions.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-if)
- **Type:** Scalar function -- returns a single BOOL value per row (GA)

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

**Supported models:** Any GA or preview Gemini model. If no endpoint specified, BigQuery dynamically chooses for best cost-to-quality tradeoff.

**Best practices:**
- BigQuery optimizes queries to reduce Gemini calls. Place non-AI filters alongside `AI.IF` -- non-AI filters are evaluated first (e.g., `WHERE AI.IF(...) AND category = 'tech'`).
- Do not use the global endpoint if you have data processing location requirements.

**Limitations:** Returns `NULL` on error (no detailed error info). No model parameter control (`temperature`, `top_p`, etc.) unlike `AI.GENERATE_BOOL`. At most one video object per input. Optimized mode (`embeddings` / `optimization_mode`, Preview) requires ~3,000 rows minimum; only string columns are supported for multi-column prompts in optimized mode.

**Locations:** All regions supporting Gemini models, plus US and EU multi-regions.

**Provisioned throughput:** Not supported. Uses dynamic shared quota (DSQ) only.

**BigFrames API:** `bigframes.bigquery.ai.if_(prompt)` — Returns a Series of BOOL directly (not a struct, unlike `generate_bool`). No `endpoint` param -- auto-selects model. Example: `bbq.ai.if_((df["review"], " is a positive review"))`. Can be used for boolean indexing: `df[bbq.ai.if_(...)]`.

---

## `AI.SCORE`
- **Description:** Scalar function that uses a Vertex AI Gemini model to rate inputs based on a scoring system that you describe and returns a `FLOAT64` value. BigQuery rewrites your input prompt to generate a scoring rubric that improves consistency and result quality.
- **Use cases:** Find the most negative customer reviews (retail), find the most qualified resumes (hiring), find the best customer support interactions, rating and ranking items. Commonly used with `ORDER BY`.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-score)
- **Type:** Scalar function -- returns a single FLOAT64 value per row (GA)

**Syntax:**
```sql
AI.SCORE(
  [ prompt => ] 'PROMPT'
  [, connection_id => 'CONNECTION' ]
  [, endpoint => 'ENDPOINT' ]
  [, max_error_ratio => MAX_ERROR_RATIO ]
)
```

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `PROMPT` | STRING or STRUCT | Required (must be first argument) | The prompt describing the scoring criteria. STRING or STRUCT with STRING/ARRAY\<STRING\>/ObjectRef/ARRAY\<ObjectRef\> fields. At most one video object. For a document plus its criteria, the tuple form `('criteria text', ref)` is the usual shape. |
| `CONNECTION` | STRING | Optional | Connection to use, format: `[PROJECT_ID].LOCATION.CONNECTION_ID`. |
| `ENDPOINT` | STRING | Optional | Vertex AI endpoint. If not specified, BigQuery dynamically chooses a model. |
| `MAX_ERROR_RATIO` | FLOAT64 | Optional | Range 0.0–1.0, default 1.0. If the error ratio exceeds this threshold, the query fails with an error. |

**Outputs:**

| Return Type | Description |
|-------------|-------------|
| FLOAT64 | The score assigned to the input. **There is no fixed default range for the score** -- provide a scoring range in your prompt. |
| NULL | Returned if the call to Vertex AI is unsuccessful. |

**Supported models:** Any GA or preview Gemini model.

**Best practices:**
- Provide a scoring range in your prompt (e.g., "On a scale from 1 to 10") since there is no fixed default range.
- `AI.SCORE` automatically rewrites your prompt to generate a scoring rubric.
- Combine with `AI.IF` to filter results before or alongside scoring.
- Use with `ORDER BY` and `LIMIT` for ranking.

**Limitations:** Returns `NULL` on error. No model parameter control. No fixed default score range.

**Locations:** All regions supporting Gemini models, plus US and EU multi-regions.

**Provisioned throughput:** Not supported. Uses dynamic shared quota (DSQ) only.

**BigFrames API:** `bigframes.bigquery.ai.score(prompt)` — Returns a Series of FLOAT64 directly (not a struct). No `endpoint` param -- auto-selects model. Example: `bbq.ai.score(("Rate the negativity of: ", df["review"], " on scale 1-10"))`.

---

## `AI.CLASSIFY`
- **Description:** Scalar function that uses a Vertex AI Gemini model to classify inputs into categories that you provide. BigQuery automatically structures your input to improve classification quality.
- **Use cases:** Classify reviews by sentiment, classify products by categories, classify support tickets by topic, image classification by style or contents, multi-label classification.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-classify)
- **Type:** Scalar function -- returns STRING or ARRAY\<STRING\> per row (GA)

**Syntax:**
```sql
AI.CLASSIFY(
  [ input => ] 'INPUT',
  [ categories => ] 'CATEGORIES'
  [, examples => EXAMPLES ]
  [, connection_id => 'CONNECTION' ]
  [, endpoint => 'ENDPOINT' ]
  [, output_mode => 'OUTPUT_MODE' ]
  [, embeddings => EMBEDDINGS ]
  [, optimization_mode => 'OPTIMIZATION_MODE' ]
  [, max_error_ratio => MAX_ERROR_RATIO ]
)
```

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `INPUT` | STRING or STRUCT | Required (must be first argument) | The input to classify. STRING, an `ObjectRef`, or a STRUCT with STRING/ARRAY\<STRING\>/ObjectRef/ARRAY\<ObjectRef\> fields. At most one video object. An object table's `ref` column goes in directly — `EXTERNAL_OBJECT_TRANSFORM` is not required (verified live 2026-09-15). |
| `CATEGORIES` | ARRAY\<STRING\> or ARRAY\<STRUCT\<STRING, STRING\>\> | Required (must be second argument) | The categories to classify into. Without descriptions: `['positive', 'neutral', 'negative']`. With descriptions: `[('green', 'positive'), ('yellow', 'neutral'), ('red', 'negative')]`. Must be string literals (or use a DECLARE variable from a table column). |
| `EXAMPLES` | ARRAY\<STRUCT\<STRING, STRING\>\> (single) or ARRAY\<STRUCT\<STRING, ARRAY\<STRING\>\>\> (multi) | Optional | Few-shot examples. For single mode: maps input to expected category. For multi mode: maps input to expected array of categories. Example: `[("This is a great phone", "tech"), ("The match was exciting", "sport")]`. |
| `CONNECTION` | STRING | Optional | Connection to use, format: `[PROJECT_ID].LOCATION.CONNECTION_ID`. |
| `ENDPOINT` | STRING | Optional | Vertex AI endpoint. If not specified, BigQuery dynamically chooses a model. |
| `OUTPUT_MODE` | STRING | Optional | `'single'` or `'multi'`. Changes return type to ARRAY\<STRING\>. |
| `EMBEDDINGS` | (Preview) | Optional | Embeddings for optimized mode, same as AI.IF. |
| `OPTIMIZATION_MODE` | STRING | Optional (Preview) | `MINIMIZE_COST` or `MAXIMIZE_QUALITY`. Same as AI.IF. Note: `output_mode => 'multi'` is NOT supported in optimized mode. |
| `MAX_ERROR_RATIO` | FLOAT64 | Optional | Range 0.0–1.0, default 1.0. Not supported when `optimization_mode` is `MINIMIZE_COST`. |

**Categories from a table column (using DECLARE):**
```sql
DECLARE article_types ARRAY<STRING>
  DEFAULT (SELECT ARRAY_AGG(category) FROM mydataset.categories);

SELECT AI.CLASSIFY(body, categories => article_types) AS category
FROM `bigquery-public-data.bbc_news.fulltext`;
```

**Outputs:**

| Condition | Return Type | Description |
|-----------|-------------|-------------|
| No OUTPUT_MODE specified | STRING | The single category that best fits the input. |
| OUTPUT_MODE = 'single' | ARRAY\<STRING\> | Array of length 1 containing the best-fit category. |
| OUTPUT_MODE = 'multi' | ARRAY\<STRING\> | Array of 0 to N categories. Empty array if no category applies. |
| Error | NULL | Returned if the call to Vertex AI is unsuccessful. |

**Supported models:** Any GA or preview Gemini model.

**Best practices:**
- Include an `'Other'` category to handle input that doesn't closely match any category.
- Use categories with descriptions for more nuanced classification.
- Use `output_mode => 'multi'` when items may belong to multiple categories.
- Materialize `AI.CLASSIFY` predictions once to a table and score them against ground-truth labels with model-free [`ML.METRICS`](../../bigquery-ml/reference/model-free-functions.md#mlmetrics) to compute deterministic `precision`, `recall`, `accuracy`, and `f1_score` (overall or per segment via `segment_by_cols`) at zero additional token cost.

**Limitations:** Returns `NULL` on error. Categories must be string literals in the array (unless using a `DECLARE` variable). No model parameter control. `output_mode => 'multi'` is not supported in optimized mode. Optimized mode (`embeddings` / `optimization_mode`, Preview) requires ~3,000 rows minimum; only string columns are supported for multi-column inputs.

**Locations:** All regions supporting Gemini models, plus US and EU multi-regions.

**Provisioned throughput:** Not supported. Uses dynamic shared quota (DSQ) only.

**BigFrames API:** `bigframes.bigquery.ai.classify(input, categories)` — Returns a Series of STRING directly (not a struct). Takes `categories` as a list/tuple. Example: `bbq.ai.classify(df["text"], ["positive", "negative", "neutral"])`.

---

## `AI.AGG`
- **Description:** Aggregate function that uses a Vertex AI Gemini model to aggregate data based on natural language instructions. Automatically performs multi-level aggregation through batching, so it can analyze data exceeding the Gemini context window. Returns a single STRING per group (or a structured STRUCT when `output_schema` is specified).
- **Use cases:** Sentiment analysis across reviews, content summarization of text or images, log analysis and incident investigation, agent performance analysis, finding common categories or patterns across data, summarizing grouped data.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-agg)
- **Type:** Aggregate function -- returns a single STRING value per group (or STRUCT with `output_schema`). Use with GROUP BY for per-group results; without GROUP BY, aggregates all rows (GA)

**Syntax:**
```sql
AI.AGG(
  [ DISTINCT ]
  INPUT,
  INSTRUCTION
  [, connection_id => 'CONNECTION']
  [, endpoint => 'ENDPOINT']
  [, max_error_ratio => MAX_ERROR_RATIO]
  [, output_schema => 'OUTPUT_SCHEMA']
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
| `max_error_ratio` | FLOAT64 | Optional | A FLOAT64 between 0.0 and 1.0 specifying the maximum acceptable ratio of row-level inference failures. Default is 1.0 (returns partial results). If exceeded, the query fails with an error describing frequent error types. |
| `output_schema` | STRING | Optional | Schema for structured output as comma-separated fields (e.g. `'summary STRING, sentiment STRING'`). When specified, `AI.AGG` returns a STRUCT conforming to this schema instead of a plain STRING. |

**Outputs:**

| Return Type | Description |
|-------------|-------------|
| STRING | Default return type without `output_schema`. The aggregated result for the group. One result per GROUP BY group, or one result total without GROUP BY. |
| STRUCT | Returned when `output_schema` is specified, containing fields conforming to the requested schema. |
| STRING (partial) | If some Vertex AI calls fail, returns partial results from successful calls. |
| NULL | Returned if all calls to Vertex AI fail, or if all input rows are invalid. |

**Output cap:** 10,000 tokens per group.

**Supported models:** Any Gemini model that doesn't require thinking budget (including `gemini-4-argon`, Gemini 3.x, and `gemini-2.5-*` models). If no endpoint specified, BigQuery dynamically chooses a model.

**Best practices:**
- Use `TO_JSON_STRING` to pass multiple columns as structured input -- the model sees each row's full context.
- Use `DISTINCT` to remove duplicate inputs and reduce token usage.
- Use `output_schema` to return typed records (e.g. `ARRAY<STRUCT<name STRING, explanation STRING>>`) directly into SQL rather than parsing unstructured text.
- Use `max_error_ratio` to guard against large jobs failing silently on high error rates or failing completely on a single transient row error.
- Keep groups under 20 million rows per query and under 1,000 distinct groups to avoid timeouts.
- Prefer AI.AGG over manual aggregation with AI.GENERATE (STRING_AGG/ARRAY_AGG into a prompt) -- AI.AGG handles batching automatically and scales beyond the context window.

**Limitations:** Returns NULL on total failure (no detailed error info). No model parameter control (temperature, top_p, etc.). Output capped at 10,000 tokens per group. Recommended limit of 20 million rows per query and 1,000 distinct groups. Cannot use Gemini models that require thinking budget.

**Known issues:**
- Passing a `NULL` instruction string might return an internal error instead of an invalid-query error.
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

---

## `AI.TRANSLATE`
- **Description:** Scalar managed translation function that translates text per row using Cloud Translation Advanced (`'nmt'` Neural Machine Translation by default, or `'translation-llm'`) with **zero `CREATE MODEL` DDL and zero Cloud resource connection setup**. Unlike [`ML.TRANSLATE`](cloud-ai-service-models.md#mltranslate), `target_language` and `source_language` can vary dynamically row by row from table columns.
- **Use cases:** Translating multilingual customer reviews, support tickets, or product catalogs into a canonical analytics language; per-row localized outbound messaging where each recipient row specifies its own `target_language`; lightweight language detection + translation via `return_details => TRUE`.
- [documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-translate) · [notebook](../functions/ai_translate/ai_translate.ipynb) · [sql](../functions/ai_translate/ai_translate.sql)
- **Type:** Scalar function -- returns STRING, or STRUCT when `return_details => TRUE` (GA)

**Syntax:**
```sql
AI.TRANSLATE(
  [ content => ] CONTENT,
  [ target_language => ] TARGET_LANGUAGE
  [, source_language => SOURCE_LANGUAGE ]
  [, model => MODEL ]
  [, return_details => RETURN_DETAILS ]
)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `CONTENT` | `STRING` | Required (1st positional or `content =>`) | -- | Text expression or column to translate (up to `30,000` Unicode code points per row). |
| `TARGET_LANGUAGE` | `STRING` | Required (2nd positional or `target_language =>`) | -- | Target BCP-47 / ISO-639 language code (for example `'en'`, `'es'`, `'ja'`, `'zh-TW'`). Accepts either a literal **or a dynamic per-row `STRING` column expression**. |
| `SOURCE_LANGUAGE` | `STRING` | Optional (`source_language =>`) | Auto-detect | Source BCP-47 / ISO-639 language code. Omit or pass `''` to auto-detect the source language per row; accepts either a literal or a dynamic per-row `STRING` column expression. |
| `MODEL` | `STRING` literal | Optional (`model =>`) | `'nmt'` | Translation engine constant across the query: `'nmt'` (Cloud Translation Neural Machine Translation) or `'translation-llm'` (Cloud Translation LLM for higher fluency and idiomatic nuance). |
| `RETURN_DETAILS` | `BOOL` literal | Optional (`return_details =>`) | `FALSE` | Constant `BOOL` literal. When `FALSE`, returns a scalar `STRING` (`NULL` on per-row error). When `TRUE`, returns `STRUCT<result STRING, status STRING, details JSON>`. |

> **Signature note:** Engine signature errors also show an undocumented trailing `[options => JSON]` parameter (`AI.TRANSLATE(STRING, STRING, [source_language => STRING], [model => STRING], [return_details => BOOL], [options => JSON])`), which is reserved and not documented for general queries. Passing `connection_id => ...` fails signature validation (`Named argument connection_id not found in signature`).

**Outputs:**

When `return_details => FALSE` (default): returns `STRING` (translated text, or **silent `NULL`** on `NULL` input or per-row API error such as an unsupported language code).

When `return_details => TRUE`: returns `STRUCT<result STRING, status STRING, details JSON>`:

| Field | Type | Description |
|-------|------|-------------|
| `result` | `STRING` | Translated text (`''` when `content` is `''`; `NULL` when `content` is `NULL` or an API error occurs). |
| `status` | `STRING` | **`'OK'` on success** (NOT empty string `''`!), a non-empty error string when the API rejects the row (for example invalid `target_language`), or `NULL` when `content` is `NULL`. |
| `details` | `JSON` | **Snake_case** metadata payload from Cloud Translation, e.g. `{"detected_language_code":"fr","model":"projects/000000000000/locations/us/models/general/nmt","translated_text":"Hello"}` (`{}` when `content = ''`, `NULL` on error or `NULL` input). |

**GOTCHA — `status = 'OK'` (not `''`), empty-string short-circuit, and snake_case `details`:**
- Unlike `AI.GENERATE`, `AI.CHUNK_DOCUMENT`, and `ML.TRANSLATE` (which all emit `status = ''` on success), `AI.TRANSLATE(..., return_details => TRUE)` emits **`status = 'OK'`** on every successful row. Filtering with `WHERE tr.status = ''` silently discards **100% of successful translations** — always write `WHERE tr.status = 'OK'`.
- Passing `content = ''` (empty string) short-circuits locally inside BigQuery (`result = ''`, `status = 'OK'`, `details = JSON '{}'`), incurring zero Cloud Translation API call or character charge. Passing `content = NULL` returns a `NULL` `STRUCT` (field accesses evaluate to `NULL`; no API call).
- `details` keys use **snake_case** (`translated_text`, `detected_language_code`, `model`), whereas [`ML.TRANSLATE`](cloud-ai-service-models.md#mltranslate) uses camelCase inside `ml_translate_result`.

**Examples:**
```sql
-- 1. Zero-DDL translation with dynamic per-row target_language column
SELECT
  message_id,
  locale,
  AI.TRANSLATE(body, locale, model => 'translation-llm') AS localized_body
FROM `your-gcp-project-id.DATASET_ID.outbound_messages`;

-- 2. Auditing detected source language and row-level errors with return_details => TRUE
WITH translated AS (
  SELECT
    ticket_id,
    AI.TRANSLATE(
      comment_text,
      'en',
      model => 'nmt',
      return_details => TRUE
    ) AS tr
  FROM `your-gcp-project-id.DATASET_ID.support_tickets`
)
SELECT
  ticket_id,
  tr.result AS english_text,
  JSON_VALUE(tr.details, '$.detected_language_code') AS detected_lang,
  tr.status
FROM translated
WHERE tr.status = 'OK';
```

**Authentication & IAM prerequisites:**
1. Enable the Cloud Translation API (`translate.googleapis.com`) in the query execution project.
2. Grant `roles/cloudtranslate.user` (`cloudtranslate.generalModels.predict`) directly to the **query caller** (end-user credentials, or the service account executing a scheduled query / workflow). `AI.TRANSLATE` does **not** accept a Cloud resource `connection_id`.

**GOTCHA — Data residency & single-region global-endpoint routing:**

| BigQuery Query Location | Cloud Translation Endpoint Used | Residency Guarantee |
|-------------------------|---------------------------------|---------------------|
| **`US`** multi-region | `us` multi-regional endpoint | Stays in US |
| **`EU`** multi-region | `eu` multi-regional endpoint | Stays in EU |
| **Any single region** (`us-central1`, `europe-west1`, `asia-northeast1`, etc.) | **`global` endpoint** | **None** — request can be processed in any Cloud Translation region |

If your workload runs in a single-region dataset with strict regional data-residency requirements (or requires Cloud resource connection service-account auth), either run the translation query in the `US`/`EU` multi-region or use [`ML.TRANSLATE`](cloud-ai-service-models.md#mltranslate).

**Choosing between `AI.TRANSLATE`, `ML.TRANSLATE`, and `AI.GENERATE`:**

| Dimension | `AI.TRANSLATE` | [`ML.TRANSLATE`](cloud-ai-service-models.md#mltranslate) | [`AI.GENERATE`](general-purpose-functions.md#aigenerate) |
|-----------|----------------|----------------------------------------------------------|----------------------------------------------------------|
| **Setup DDL** | None (zero-DDL scalar) | `CREATE MODEL ... REMOTE_SERVICE_TYPE = 'CLOUD_AI_TRANSLATE_V3'` + connection | None (zero-DDL scalar) |
| **Dynamic per-row `target_language`** | **Yes** (column expression) | No (fixed in `STRUCT` options per query) | Yes (interpolated in prompt) |
| **Authentication** | Caller EUC only (`roles/cloudtranslate.user`) | Cloud resource connection SA | Caller EUC or optional `connection_id` |
| **Single-region data residency** | Routes single regions to **global** endpoint | Supported in `US` and `EU` multi-regions | Follows Gemini regional / multi-regional endpoint rules |
| **Extra task modes** | Translate (+ auto-detect in `details`) | `TRANSLATE_TEXT`, standalone `DETECT_LANGUAGE`, `TRANSLITERATE_TEXT` | Arbitrary instructions (glossary tone, JSON extraction + translation) |
| **Success status value** | `status = 'OK'` (`return_details => TRUE`) | `ml_translate_status = ''` | `status = ''` |

**Quotas, limits & pricing:**
- **Limits:** Maximum `30,000` Unicode code points per row; default project quota of `6,000,000` characters per minute across Cloud Translation v3 calls.
- **Pricing:** `model => 'nmt'` includes the first **500,000 characters per month free**, then **$20 per 1M input characters**; `model => 'translation-llm'` is billed at **$10 per 1M input characters + $10 per 1M output characters** (no free tier), plus standard BigQuery SQL compute.

**Locations:** Available across BigQuery regions; see the residency table above for `US`/`EU` multi-region vs single-region `global` endpoint routing.

**Provisioned throughput:** Not applicable — governed by Cloud Translation API character-per-minute quotas rather than Vertex AI Provisioned Throughput.

**BigFrames API:** As of `bigframes 2.51.0`, there is no dedicated `bigframes.bigquery.ai.translate()` wrapper; execute via `bpd.read_gbq_query("SELECT AI.TRANSLATE(...) ...")`.
