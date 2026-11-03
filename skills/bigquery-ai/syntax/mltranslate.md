# `ML.TRANSLATE`

> **Source:** [`bigquery-ai/reference/cloud-ai-service-models.md#mltranslate`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/cloud-ai-service-models.md#mltranslate)

- **Description:** Table-valued function that translates a text column, detects its language, or transliterates text using the Cloud Translation V3 API via a Cloud resource connection. For zero-DDL scalar translation or per-row dynamic `target_language` columns under end-user credentials, see [`AI.TRANSLATE`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/managed-functions.md#aitranslate).
- [documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-translate) · [notebook](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ml_translate/ml_translate.ipynb) · [sql](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ml_translate/ml_translate.sql)

```sql
SELECT * FROM ML.TRANSLATE(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  { TABLE `PROJECT_ID.DATASET.TABLE` | (QUERY_STATEMENT) },
  STRUCT('TRANSLATE_TEXT' AS translate_mode, 'LANGUAGE_CODE' AS target_language_code));
```

| Argument | Values | Notes |
|---|---|---|
| `translate_mode` | `'TRANSLATE_TEXT'`, `'DETECT_LANGUAGE'`, `'TRANSLITERATE_TEXT'` | Task modes on the Cloud Translation V3 remote model |
| `target_language_code` | ISO-639 code | **Required** for `TRANSLATE_TEXT`; `DETECT_LANGUAGE` does not take one |

**Output:** `ml_translate_result` (JSON), `ml_translate_status` (`''` on success), plus the input columns including `text_content`.

**Worth knowing:**
- **One target language per call, and it cannot come from a column.** `target_language_code` is a scalar in the `STRUCT`, evaluated once for the whole call; a column reference fails to compile with `Unrecognized name`. When each row needs its own `target_language` (or you want `model => 'translation-llm'` with zero `CREATE MODEL` setup), use [`AI.TRANSLATE`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/managed-functions.md#aitranslate).
- **When to keep `ML.TRANSLATE` over `AI.TRANSLATE`:** `ML.TRANSLATE` authenticates via a Cloud resource connection service account (rather than caller EUC), supports standalone `DETECT_LANGUAGE` and `TRANSLITERATE_TEXT` modes, and does not route single-region queries to the global endpoint (`AI.TRANSLATE` guarantees regional residency only in the `US` and `EU` multi-regions). Also note the status convention difference: `ml_translate_status = ''` on success, whereas `AI.TRANSLATE(..., return_details => TRUE)` returns `status = 'OK'`.
- **The source language is detected for free** in `TRANSLATE_TEXT` mode — the result carries `detected_language_code` beside `translated_text`, so there is no reason to run `DETECT_LANGUAGE` first just to route rows. The two modes return different JSON shapes: `translations[]` versus `languages[]` with a confidence.
- **It is stable across runs.** The notebook compares run-to-run output with the query cache off, and puts `AI.GENERATE` on the same rows for contrast.

---
