# `AI.TRANSLATE`

> **Source:** [`bigquery-ai/reference/managed-functions.md#aitranslate`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/managed-functions.md#aitranslate)

- **Description:** Scalar managed translation function that translates text per row using Cloud Translation Advanced (`'nmt'` Neural Machine Translation by default, or `'translation-llm'`) with **zero `CREATE MODEL` DDL and zero Cloud resource connection setup**. Unlike [`ML.TRANSLATE`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/cloud-ai-service-models.md#mltranslate), `target_language` and `source_language` can vary dynamically row by row from table columns.
- **Use cases:** Translating multilingual customer reviews, support tickets, or product catalogs into a canonical analytics language; per-row localized outbound messaging where each recipient row specifies its own `target_language`; lightweight language detection + translation via `return_details => TRUE`.
- [documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-translate) · [notebook](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ai_translate/ai_translate.ipynb) · [sql](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ai_translate/ai_translate.sql)
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
- `details` keys use **snake_case** (`translated_text`, `detected_language_code`, `model`), whereas [`ML.TRANSLATE`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/cloud-ai-service-models.md#mltranslate) uses camelCase inside `ml_translate_result`.

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

If your workload runs in a single-region dataset with strict regional data-residency requirements (or requires Cloud resource connection service-account auth), either run the translation query in the `US`/`EU` multi-region or use [`ML.TRANSLATE`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/cloud-ai-service-models.md#mltranslate).

**Choosing between `AI.TRANSLATE`, `ML.TRANSLATE`, and `AI.GENERATE`:**

| Dimension | `AI.TRANSLATE` | [`ML.TRANSLATE`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/cloud-ai-service-models.md#mltranslate) | [`AI.GENERATE`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/general-purpose-functions.md#aigenerate) |
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
