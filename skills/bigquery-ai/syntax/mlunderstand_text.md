# `ML.UNDERSTAND_TEXT`

> **Source:** [`bigquery-ai/reference/cloud-ai-service-models.md#mlunderstand_text`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/cloud-ai-service-models.md#mlunderstand_text)

- **Description:** Table-valued function that runs one of five Cloud Natural Language analyses over a text column.
- [documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-understand-text) · [notebook](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ml_understand_text/ml_understand_text.ipynb) · [sql](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ml_understand_text/ml_understand_text.sql)

```sql
SELECT * FROM ML.UNDERSTAND_TEXT(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  { TABLE `PROJECT_ID.DATASET.TABLE` | (QUERY_STATEMENT) },
  STRUCT('ANALYZE_SENTIMENT' AS nlu_option, TRUE AS flatten_json_output));
```

| `nlu_option` | What comes back |
|---|---|
| `ANALYZE_SENTIMENT` | Document and per-sentence sentiment, as a score and a magnitude |
| `ANALYZE_ENTITIES` | Named things in the text, with a type and a salience |
| `ANALYZE_ENTITY_SENTIMENT` | The same entities, each carrying its own sentiment |
| `ANALYZE_SYNTAX` | Tokens with part of speech, lemma and dependency edges |
| `CLASSIFY_TEXT` | Categories from a published, fixed taxonomy |

Two more arguments: `flatten_json_output` (`BOOL`) adds unpacked columns beside the JSON, and `encoding_type` (`'UTF8'`, `'UTF16'`, `'UTF32'`) turns on the text-span offsets. Its default is `NONE`, which means `begin_offset` is simply not computed — and when you do ask, the offsets are measured in that encoding's units, so UTF-8 and UTF-16 disagree on any accented text.

**Output:** `ml_understand_text_result` (JSON), `ml_understand_text_status`, the input columns, and — with `flatten_json_output` — the flattened columns.

**Worth knowing:**
- **Language support differs per analysis**, and an unsupported language fails **the row**, not the job. Measured: `ANALYZE_ENTITY_SENTIMENT` returns `INVALID_ARGUMENT: The language ko is not supported for entity_sentiment analysis.` for Korean and Vietnamese rows while the same call succeeds for the rest — entity sentiment supports fewer languages than sentiment does.
- **An empty sentiment object reads as `NULL`, not `0`.** An entity can come back with no sentiment, and the accessor cannot tell that apart from neutral unless you coalesce.
- **The taxonomy and the entity types are closed vocabularies.** That is the feature — the same text yields the same category next quarter — and the limit: if your business needs a category the taxonomy does not have, this is the wrong function.

---
