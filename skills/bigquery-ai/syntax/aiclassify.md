# `AI.CLASSIFY`

> **Source:** [`bigquery-ai/reference/managed-functions.md#aiclassify`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/managed-functions.md#aiclassify)

- **Description:** (Preview) Scalar function that uses a Vertex AI Gemini model to classify inputs into categories that you provide. BigQuery automatically structures your input to improve the quality of the classification.
- **Use cases:** Classify reviews by sentiment, classify products by categories, classify support tickets by topic, image classification by style or contents, multi-label classification.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-classify)
- **Type:** Scalar function -- returns STRING or ARRAY\<STRING\> per row (Preview)

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

**Supported models:** Any GA or preview Gemini model. Uses various `gemini-2.5-*` models.

**Best practices:**
- Include an 'Other' category to handle input that doesn't closely match any category.
- Use categories with descriptions for more nuanced classification.
- Use `output_mode => 'multi'` when items may belong to multiple categories.

**Limitations:** Preview status. Returns NULL on error. Categories must be string literals in the array (unless using a variable). No model parameter control. `output_mode => 'multi'` is not supported in optimized mode. Optimized mode requires ~3,000 rows minimum; only string columns supported for multi-column inputs.

**Locations:** All regions supporting Gemini models, plus US and EU multi-regions.

**Provisioned throughput:** Not supported. Uses dynamic shared quota (DSQ) only.

**BigFrames API:** `bigframes.bigquery.ai.classify(input, categories)` — Returns a Series of STRING directly (not a struct). Takes `categories` as a list/tuple. Example: `bbq.ai.classify(df["text"], ["positive", "negative", "neutral"])`.

---
