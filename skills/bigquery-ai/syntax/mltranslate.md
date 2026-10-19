# `ML.TRANSLATE`

> **Source:** [`bigquery-ai/reference/cloud-ai-service-models.md#mltranslate`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/cloud-ai-service-models.md#mltranslate)

- **Description:** Table-valued function that translates a text column, or detects its language, using the Cloud Translation V3 API.
- [documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-translate) · [notebook](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ml_translate/ml_translate.ipynb) · [sql](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ml_translate/ml_translate.sql)

```sql
SELECT * FROM ML.TRANSLATE(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  { TABLE `PROJECT_ID.DATASET.TABLE` | (QUERY_STATEMENT) },
  STRUCT('TRANSLATE_TEXT' AS translate_mode, 'LANGUAGE_CODE' AS target_language_code));
```

| Argument | Values | Notes |
|---|---|---|
| `translate_mode` | `'TRANSLATE_TEXT'`, `'DETECT_LANGUAGE'` | Two modes in one function |
| `target_language_code` | ISO-639 code | **Required** for `TRANSLATE_TEXT`; `DETECT_LANGUAGE` does not take one |

**Output:** `ml_translate_result` (JSON), `ml_translate_status`, plus the input columns including `text_content`.

**Worth knowing:**
- **One target language per call, and it cannot come from a column.** `target_language_code` is a scalar in the `STRUCT`, evaluated once for the whole call; a column reference fails to compile with `Unrecognized name`. Fanning out over three languages is three calls unioned together, each re-reading and re-billing the source text.
- **The source language is detected for free** in `TRANSLATE_TEXT` mode — the result carries `detected_language_code` beside `translated_text`, so there is no reason to run `DETECT_LANGUAGE` first just to route rows. The two modes return different JSON shapes: `translations[]` versus `languages[]` with a confidence.
- **It is stable across runs.** The notebook compares run-to-run output with the query cache off, and puts `AI.GENERATE` on the same rows for contrast.

---
