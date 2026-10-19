# `AI.SCORE`

> **Source:** [`bigquery-ai/reference/managed-functions.md#aiscore`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/managed-functions.md#aiscore)

- **Description:** (Preview) Scalar function that uses a Vertex AI Gemini model to rate inputs based on a scoring system that you describe and returns a FLOAT64 value. BigQuery rewrites your input prompt to generate a scoring rubric that can improve the consistency and quality of the results.
- **Use cases:** Find the most negative customer reviews (retail), find the most qualified resumes (hiring), find the best customer support interactions, rating and ranking items. Commonly used with ORDER BY.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-score)
- **Type:** Scalar function -- returns a single FLOAT64 value per row (Preview)

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

**Supported models:** Any GA or preview Gemini model. Uses various `gemini-2.5-*` models.

**Best practices:**
- Provide a scoring range in your prompt (e.g., "On a scale from 1 to 10") since there is no fixed default range.
- AI.SCORE automatically rewrites your prompt to generate a scoring rubric.
- Combine with AI.IF to filter results before or alongside scoring.
- Use with ORDER BY and LIMIT for ranking.

**Limitations:** Preview status. Returns NULL on error. No model parameter control. No fixed default score range.

**Locations:** All regions supporting Gemini models, plus US and EU multi-regions.

**Provisioned throughput:** Not supported. Uses dynamic shared quota (DSQ) only.

**BigFrames API:** `bigframes.bigquery.ai.score(prompt)` — Returns a Series of FLOAT64 directly (not a struct). No endpoint param -- auto-selects model. Example: `bbq.ai.score(("Rate the negativity of: ", df["review"], " on scale 1-10"))`.

---
