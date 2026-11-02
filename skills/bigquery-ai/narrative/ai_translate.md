> **Source (`statmike/bigquery-data-science`):** **Notebook:** [`bigquery-ai/functions/ai_translate/ai_translate.ipynb`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ai_translate/ai_translate.ipynb) · **SQL:** [`bigquery-ai/functions/ai_translate/ai_translate.sql`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/functions/ai_translate/ai_translate.sql)

# AI.TRANSLATE — BigQuery AI Functions

`AI.TRANSLATE` (GA) is a managed scalar function that translates `STRING` expressions directly through the [Cloud Translation API](https://cloud.google.com/translate/docs) using **end-user credentials**. Unlike `functions/ml_translate` (`ML.TRANSLATE`), there is no `CREATE MODEL` step, no Cloud Resource connection (`connection_id` is rejected), no `text_content` column-rename rule, and no JSON output to unpack unless you ask for details.

**When to use it:**
- You want inline translation inside `SELECT`, `WHERE`, or `JOIN` expressions without creating a remote model or connection
- Each row needs its own `target_language` or `source_language` read dynamically from table columns (for example, replying to each ticket in that customer's preferred locale)
- You want to choose per query between fast Neural Machine Translation (`model => 'nmt'`, default — first 500K input characters/month free, then $20/1M input characters) and Cloud Translation's purpose-built LLM (`model => 'translation-llm'` — $10/1M input + $10/1M output characters)
- You want predictable per-character pricing and zero prompt-injection surface compared with free-form LLM prompting

**Alternatives:**
- `functions/ml_translate` (`ML.TRANSLATE`) — Table-valued `CLOUD_AI_TRANSLATE_V3` remote model over a Cloud Resource connection. Reach for it when a **connection service account** (rather than caller end-user credentials) must own Cloud Translation IAM and quotas, or when you want **standalone language detection** (`DETECT_LANGUAGE` mode) without translating.
- `functions/ai_generate` (`AI.GENERATE`) — General-purpose Gemini generation. Reach for it when translation must obey custom brand glossaries, tone/register rewrites, or multi-field `output_schema` extraction in the same pass.

**Three rules to know before you start:**
1. **`status = 'OK'` on success, not `''`:** When you pass `return_details => TRUE`, `AI.TRANSLATE` returns `STRUCT<result STRING, status STRING, details JSON>` with `status = 'OK'` for successful rows — unlike `ML.TRANSLATE`, `AI.CHUNK_DOCUMENT`, and `AI.GENERATE*`, which return an empty string `''`. Filtering `WHERE t.status = ''` drops every valid translation.
2. **Dynamic columns vs constant literals:** `content`, `target_language`, and `source_language` accept per-row column expressions, whereas `model` (`'nmt'` or `'translation-llm'`) and `return_details` (`BOOL`) must be analysis-time constants.
3. **Residency & row-length cap:** Queries in `US` or `EU` multi-regions process data in the US or EU, while **all single regions** (such as `us-central1` or `europe-west1`) route to the Cloud Translation **global endpoint** with no regional residency guarantee. Each input string is capped at **30,000 code points (characters)** (5,000 or fewer recommended for low latency).

**References:** `RESOURCES.md` (Full syntax reference) | `reference/managed-functions.md#aitranslate` (Managed AI Functions) | [Official documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-translate) | `setup` (Setup guide)

---
## Setup

`AI.TRANSLATE` itself requires **no connection and no model** — it calls the Cloud Translation API (`translate.googleapis.com`) directly under the caller's own credentials (`roles/cloudtranslate.user`).

> Example 7 at the end of this notebook compares `AI.TRANSLATE` side-by-side against `functions/ml_translate` (`ML.TRANSLATE`) and `functions/ai_generate` (`AI.GENERATE`) on the same rows. The setup cells below create the shared `bq_ai_functions` dataset, enable the required APIs, and prepare a temporary `CLOUD_AI_TRANSLATE_V3` remote model (`ai_translate_ml_model`) solely for that head-to-head comparison. See the `setup` (Setup Reference) for details.

```python
import os
from pathlib import Path
import google.auth

PROJECT_ID = 'your-gcp-project-id'  # <-- Replace with your project ID (or leave to auto-detect)
if PROJECT_ID == 'your-gcp-project-id':
    for _p in [Path.cwd(), *Path.cwd().parents]:
        if (_p / '.env').is_file():
            for _k, _v in (l.split('=', 1) for l in (_p / '.env').read_text().splitlines() if '=' in l and not l.strip().startswith('#')):
                os.environ.setdefault(_k.strip(), _v.strip().strip('\'"'))
            break
    PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT') or google.auth.default()[1] or 'your-gcp-project-id'
LOCATION = 'US'  # Multi-region US keeps AI.TRANSLATE data processing in the US
DATASET_ID = 'bq_ai_functions'  # Shared dataset across all notebooks
CONNECTION_ID = 'bq_ai_functions'  # Shared connection (used only for Example 7's ML.TRANSLATE comparison)
```

### Environment

> **Already set up the project environment?** The cell below is a no-op — packages are already in your kernel. See the `setup` (Setup Reference) for details.
>
> **Running standalone** (Colab, Colab Enterprise, Vertex AI Workbench)? The cell below installs required packages into your current kernel.

```python
from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project=PROJECT_ID)
pd.set_option('display.max_colwidth', None)

# Create the shared dataset (idempotent)
dataset_ref = bigquery.DatasetReference(PROJECT_ID, DATASET_ID)
dataset = bigquery.Dataset(dataset_ref)
dataset.location = LOCATION
client.create_dataset(dataset, exists_ok=True)
print(f'Dataset ready: {PROJECT_ID}.{DATASET_ID} ({LOCATION})')

%load_ext bigquery_magics
```

### Enable APIs and prepare the sibling comparison model

- **For `AI.TRANSLATE` (Examples 1–7):** enables `translate.googleapis.com`. Your user or workload identity uses end-user credentials directly.
- **For Example 7's `ML.TRANSLATE` / `AI.GENERATE` comparison:** enables `bigqueryconnection.googleapis.com` and `aiplatform.googleapis.com`, ensures the shared `bq_ai_functions` connection has `roles/cloudtranslate.user` and `roles/aiplatform.user`, and creates a temporary `ai_translate_ml_model` remote model (dropped in Cleanup).

```python
import time
import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.cloud import bigquery_connection_v1 as bq_conn

creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
authed_session = AuthorizedSession(creds)

# 1. Enable required APIs (idempotent)
apis = [
    'bigquery.googleapis.com',
    'bigqueryconnection.googleapis.com',
    'translate.googleapis.com',
    'aiplatform.googleapis.com',
]
for api in apis:
    url = f'https://serviceusage.googleapis.com/v1/projects/{PROJECT_ID}/services/{api}:enable'
    resp = authed_session.post(url)
    if resp.status_code not in (200, 201):
        print(f'Warning enabling {api}: {resp.status_code} {resp.text[:200]}')
print('APIs enabled:', ', '.join(apis))

# 2. Ensure shared Cloud Resource connection exists for Example 7's ML.TRANSLATE comparison
conn_client = bq_conn.ConnectionServiceClient()
parent = f'projects/{PROJECT_ID}/locations/{LOCATION.lower()}'
conn_path = f'{parent}/connections/{CONNECTION_ID}'
try:
    conn = conn_client.get_connection(name=conn_path)
except Exception:
    conn = conn_client.create_connection(
        parent=parent,
        connection_id=CONNECTION_ID,
        connection=bq_conn.Connection(cloud_resource=bq_conn.CloudResourceProperties()),
    )

sa_email = conn.cloud_resource.service_account_id
member = f'serviceAccount:{sa_email}'
required_roles = [
    'roles/serviceusage.serviceUsageConsumer',
    'roles/bigquery.connectionUser',
    'roles/cloudtranslate.user',
    'roles/aiplatform.user',
]

policy_resp = authed_session.post(
    f'https://cloudresourcemanager.googleapis.com/v1/projects/{PROJECT_ID}:getIamPolicy',
    json={},
)
policy_resp.raise_for_status()
policy = policy_resp.json()
bindings = policy.setdefault('bindings', [])

added_roles = []
for role in required_roles:
    binding = next((b for b in bindings if b['role'] == role), None)
    if binding is None:
        bindings.append({'role': role, 'members': [member]})
        added_roles.append(role)
    elif member not in binding.get('members', []):
        binding.setdefault('members', []).append(member)
        added_roles.append(role)

if added_roles:
    set_resp = authed_session.post(
        f'https://cloudresourcemanager.googleapis.com/v1/projects/{PROJECT_ID}:setIamPolicy',
        json={'policy': policy},
    )
    set_resp.raise_for_status()
    print(f'Granted {added_roles} to connection service account; waiting 60s for IAM propagation...')
    time.sleep(60)

# 3. Create temporary ML.TRANSLATE remote model for Example 7 (dropped in Cleanup)
client.query(f"""
CREATE OR REPLACE MODEL `{PROJECT_ID}.{DATASET_ID}.ai_translate_ml_model`
REMOTE WITH CONNECTION `{PROJECT_ID}.{LOCATION}.{CONNECTION_ID}`
OPTIONS (REMOTE_SERVICE_TYPE = 'CLOUD_AI_TRANSLATE_V3')
""").result()
print(f'Comparison remote model ready: {DATASET_ID}.ai_translate_ml_model')
```

### Sample table: multilingual customer feedback

Create `ai_translate_feedback` with 10 rows spanning Spanish, French, Japanese, German, Portuguese, and English. The rows deliberately include:
- Straightforward billing and product feedback (`id` 1, 5)
- Everyday idioms (`id` 2 *"met dans le mille"*, `id` 4 *"wie am Schnürchen"*, `id` 8 *"un ojo de la cara"*) and cloud-warehouse technical jargon (`id` 3) to test `'nmt'` against `'translation-llm'`
- An English resolution row (`id` 7) and per-customer `preferred_reply_lang` codes for dynamic per-row target routing
- Edge-case rows (`id` 9 empty string `''`, `id` 10 `NULL`) for boundary testing

```python
client.query(f"""
CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_ID}.ai_translate_feedback` AS
SELECT * FROM UNNEST([
  STRUCT(
    1 AS id, 'es' AS declared_lang, 'es' AS preferred_reply_lang, 'billing' AS category,
    'El cargo apareció dos veces en mi factura de marzo y necesito un reembolso.' AS comment
  ),
  STRUCT(
    2, 'fr', 'fr', 'ux_idiom',
    "Franchement, votre nouvelle interface met dans le mille — bravo à toute l'équipe !"
  ),
  STRUCT(
    3, 'ja', 'ja', 'tech_jargon',
    'クエリ結果は速いですが、スロット予約の上限に達するとバッチジョブが待機状態になります。'
  ),
  STRUCT(
    4, 'de', 'de', 'ux_idiom',
    'Das Dashboard läuft wie am Schnürchen, aber beim CSV-Export klemmt es manchmal.'
  ),
  STRUCT(
    5, 'pt', 'pt', 'feature',
    'Seria ótimo poder exportar os relatórios semanais diretamente para uma planilha.'
  ),
  STRUCT(
    6, 'fr', 'fr', 'ambiguous_short',
    'chat'
  ),
  STRUCT(
    7, 'en', 'es', 'outbound_reply',
    'Your refund has been approved and will post to your card within three business days.'
  ),
  STRUCT(
    8, 'es', 'de', 'billing_idiom',
    'Me cobraron un ojo de la cara por el soporte prioritario y nadie respondió.'
  ),
  STRUCT(
    9, 'en', 'en', 'empty_edge',
    ''
  ),
  STRUCT(
    10, 'en', 'en', 'null_edge',
    CAST(NULL AS STRING)
  )
])
""").result()

client.query(f"""
SELECT id, declared_lang, preferred_reply_lang, category, comment
FROM `{PROJECT_ID}.{DATASET_ID}.ai_translate_feedback`
ORDER BY id
""").to_dataframe()
```

---
## Examples — SQL

### Example 1: Simplest starter call — inline `SELECT AI.TRANSLATE(comment, 'en')`

Only two arguments are required: the `STRING` expression to translate (`content`) and a [BCP-47 / ISO-639](https://cloud.google.com/translate/docs/languages) `target_language` code. When `source_language` is omitted, Cloud Translation detects the source language automatically; when the input is already in the target language, it passes through cleanly.

Notice what is **not** here compared with `ML.TRANSLATE`: no `MODEL` reference, no `FROM ML.TRANSLATE(...)` table-valued wrapper, no `comment AS text_content` alias, and no `JSON_VALUE(ml_translate_result, ...)` extraction. Because `AI.TRANSLATE` is a standard scalar `STRING` function, you can call it directly inside `SELECT`, `CONCAT`, `LOWER`, or `WHERE`.

```python
client.query(f"""
SELECT
  id,
  declared_lang,
  comment,
  AI.TRANSLATE(comment, 'en') AS comment_en
FROM `{PROJECT_ID}.{DATASET_ID}.ai_translate_feedback`
WHERE id IN (1, 2, 3, 4, 5)
ORDER BY id
""").to_dataframe()
```

### Example 2: Dynamic per-row `target_language` and `source_language` columns

Both `target_language` and `source_language` accept **column expressions**, not just string literals — a capability `ML.TRANSLATE` does not offer (its `STRUCT` options must be query-wide constants).

1. **Dynamic `target_language` (outbound localization):** Translate a single canonical support update into every customer's own `preferred_reply_lang` in one query.
2. **Explicit `source_language` (disambiguating short or homograph tokens):** Single words and short UI labels often exist in multiple languages with completely different meanings — `'chat'` means *cat* in French vs *online chat* in English, and `'gift'` means *poison* in German vs *present* in English. Passing `source_language => declared_lang` eliminates auto-detection guesswork.

```python
# 2a. Route one canonical English resolution into each customer's preferred_reply_lang
client.query(f"""
WITH outbound AS (
  SELECT
    id,
    preferred_reply_lang,
    'We resolved the duplicate charge and credited your account.' AS resolution_en
  FROM `{PROJECT_ID}.{DATASET_ID}.ai_translate_feedback`
  WHERE id IN (1, 2, 3, 4, 5)
)
SELECT
  id,
  preferred_reply_lang,
  AI.TRANSLATE(
    resolution_en,
    target_language => preferred_reply_lang,
    source_language => 'en'
  ) AS localized_reply
FROM outbound
ORDER BY id
""").to_dataframe()
```

```python
# 2b. Disambiguate cross-language homographs ('chat' FR vs EN, 'gift' DE vs EN) into Spanish
client.query("""
WITH homographs AS (
  SELECT * FROM UNNEST([
    STRUCT('chat' AS token, 'fr' AS declared_source, 'French noun ("cat")' AS context),
    STRUCT('chat',          'en',                    'English noun ("online chat")'),
    STRUCT('gift',          'de',                    'German noun ("poison")'),
    STRUCT('gift',          'en',                    'English noun ("present")')
  ])
)
SELECT
  token,
  declared_source,
  context,
  AI.TRANSLATE(token, 'es') AS auto_detect_to_es,
  AI.TRANSLATE(token, 'es', source_language => declared_source) AS explicit_source_to_es
FROM homographs
""").to_dataframe()
```

### Example 3: Choosing the engine — `model => 'nmt'` vs `model => 'translation-llm'`

`AI.TRANSLATE` exposes two Cloud Translation engines through the constant `model` parameter:

| `model` literal | Engine | Cloud Translation Pricing | Strengths |
|---|---|---|---|
| `'nmt'` *(default)* | Neural Machine Translation | First **500K input chars/month free** (up to $10 credit), then **$20 / 1M input chars** (output chars unbilled) | Lowest latency, deterministic decoding, broadest language-pair coverage, free monthly tier |
| `'translation-llm'` | Translation LLM (TLLM) | **$10 / 1M input chars + $10 / 1M output chars** (no free tier; ~$20/1M combined when input and output lengths match) | Natural rendering of idioms, colloquialisms, register, and domain/technical terminology |

Below we run both engines side-by-side on the rows containing idioms (*"met dans le mille"*, *"wie am Schnürchen"*, *"un ojo de la cara"*) and BigQuery slot-reservation terminology.

```python
client.query(f"""
SELECT
  id,
  declared_lang,
  category,
  comment,
  AI.TRANSLATE(comment, 'en', model => 'nmt') AS nmt_en,
  AI.TRANSLATE(comment, 'en', model => 'translation-llm') AS translation_llm_en
FROM `{PROJECT_ID}.{DATASET_ID}.ai_translate_feedback`
WHERE id IN (2, 3, 4, 8)
ORDER BY id
""").to_dataframe()
```

### Example 4: `return_details => TRUE` and the `status = 'OK'` contract

Setting `return_details => TRUE` changes the return type from `STRING` to `STRUCT<result STRING, status STRING, details JSON>`:

- `t.result` — the translated `STRING` (`NULL` if the row failed)
- `t.status` — **`'OK'` on success**, or a human-readable error message when a row fails
- `t.details` — snake_case JSON metadata containing `translated_text`, `model` (`projects/.../locations/.../models/general/nmt` or `.../translation-llm`), and — **only when `source_language` was omitted** — `detected_language_code`

> **Watch the `status` convention across BigQuery AI functions:**
>
> | Function(s) | Success `status` value | Safe filter |
> |---|---|---|
> | **`AI.TRANSLATE`** (`return_details => TRUE`) | **`'OK'`** | `WHERE t.status = 'OK'` |
> | `ML.TRANSLATE`, `AI.CHUNK_DOCUMENT`, `AI.GENERATE*` | `''` (empty string) | `WHERE status = ''` |
> | `AI.EVALUATE`, `AI.DETECT_ANOMALIES` | `NULL` | `WHERE status IS NULL` |

*(Catalog note: the live `AI.TRANSLATE` signature also accepts an optional sixth named argument, `options => JSON '{}'`, reserved for service options.)*

```python
# Compare auto-detected source_language (populates $.detected_language_code)
# vs explicit source_language (omits $.detected_language_code)
client.query(f"""
WITH detailed AS (
  SELECT
    id,
    declared_lang,
    AI.TRANSLATE(comment, 'en', return_details => TRUE) AS auto_src,
    AI.TRANSLATE(
      comment,
      'en',
      source_language => declared_lang,
      model => 'translation-llm',
      return_details => TRUE
    ) AS explicit_src
  FROM `{PROJECT_ID}.{DATASET_ID}.ai_translate_feedback`
  WHERE id IN (1, 2, 3)
)
SELECT
  id,
  auto_src.result AS nmt_result,
  auto_src.status AS nmt_status,
  JSON_VALUE(auto_src.details, '$.detected_language_code') AS auto_detected_lang,
  JSON_VALUE(auto_src.details, '$.model') AS nmt_backend_model,
  JSON_VALUE(explicit_src.details, '$.detected_language_code') AS explicit_detected_lang,
  JSON_VALUE(explicit_src.details, '$.model') AS tllm_backend_model
FROM detailed
WHERE auto_src.status = 'OK'
ORDER BY id
""").to_dataframe()
```

### Example 5: Boundary conditions, silent `NULL` masking, and signature guardrails

Production pipelines run into malformed locale codes, blank inputs, and `NULL` columns. `AI.TRANSLATE` handles row-level edge cases without aborting your query — which makes `return_details => TRUE` essential whenever `target_language` or `source_language` comes from user data:

1. **`NULL` input (`content IS NULL`):** Returns `NULL` when `return_details => FALSE`, and **`NULL` for the entire `STRUCT`** (`t IS NULL` is `TRUE`) when `return_details => TRUE`.
2. **Empty string `''`:** Short-circuits locally without calling Cloud Translation — returns `''` (`FALSE`) or `STRUCT('' AS result, 'OK' AS status, JSON '{}' AS details)` (`TRUE`, with an empty `{}` JSON object and no `model` key). Whitespace-only `'   '` is **not** empty and still invokes the backend model.
3. **Invalid per-row `target_language` (for example `'xx-invalid'`):** Does **not** fail the query! With `return_details => FALSE`, it silently returns `NULL` — **indistinguishable from a `NULL` input**. With `return_details => TRUE`, `t` is non-null, `t.result` is `NULL`, `t.status` explains `'Target language is invalid.'`, and `t.details` carries the structured `INVALID_ARGUMENT` error payload.
4. **Compile-time signature guardrails:** Passing `connection_id => ...`, passing a column expression to `model`, or naming a model outside `'nmt'` and `'translation-llm'` fails immediately at SQL analysis time.

> **Operational limits & residency reminder:** Each row is capped at **30,000 code points (characters)** (`400 INVALID_ARGUMENT` above 30,000; split longer documents first with `functions/ai_chunk_document` (`AI.CHUNK_DOCUMENT`), targeting `<= 5,000` characters per chunk for low latency). For data residency, run jobs in the **`US`** or **`EU`** multi-regions; single-region jobs (`us-central1`, `europe-west1`, etc.) route to the Cloud Translation **global endpoint**.

```python
# 5a. Probe NULL, empty string '', whitespace '   ', and invalid target_language 'xx-invalid'
client.query("""
WITH edge_inputs AS (
  SELECT * FROM UNNEST([
    STRUCT(1 AS probe_id, 'NULL content' AS case_label, CAST(NULL AS STRING) AS txt, 'en' AS target_lang),
    STRUCT(2,             'Empty string (local short-circuit)', '',                   'en'),
    STRUCT(3,             'Whitespace-only string (calls backend)', '   ',            'en'),
    STRUCT(4,             'Invalid per-row target_language', 'Hola mundo',            'xx-invalid')
  ])
),
evaluated AS (
  SELECT
    probe_id,
    case_label,
    AI.TRANSLATE(txt, target_lang) AS plain_result,
    AI.TRANSLATE(txt, target_lang, return_details => TRUE) AS detailed
  FROM edge_inputs
)
SELECT
  probe_id,
  case_label,
  plain_result,
  detailed IS NULL AS struct_is_null,
  detailed.result AS detail_result,
  detailed.status AS detail_status,
  TO_JSON_STRING(detailed.details) AS detail_json
FROM evaluated
ORDER BY probe_id
""").to_dataframe()
```

```python
from google.api_core.exceptions import GoogleAPIError

# 5b. Verify compile-time signature rules with intentional error probes
negative_probes = [
    (
        'connection_id rejected (EUC-only)',
        "SELECT AI.TRANSLATE('Hola', 'en', connection_id => 'us.bq_ai_functions')",
    ),
    (
        'Non-constant model column rejected',
        """
        WITH t AS (SELECT 'Hola' AS txt, 'nmt' AS chosen_model)
        SELECT AI.TRANSLATE(txt, 'en', model => chosen_model) FROM t
        """,
    ),
    (
        'Unsupported model literal rejected',
        "SELECT AI.TRANSLATE('Hola', 'en', model => 'INVALID_MODEL_NAME')",
    ),
]

for label, bad_sql in negative_probes:
    try:
        client.query(bad_sql).result()
    except GoogleAPIError as exc:
        first_line = (exc.message or str(exc)).splitlines()[0]
        print(f'[{label}]\n  -> {first_line}\n')
```

### Example 6: Uncached determinism — `'nmt'` vs `'translation-llm'`

When you disable the BigQuery query cache (`use_query_cache=False`), every execution calls Cloud Translation fresh:
- `model => 'nmt'` runs a deterministic neural machine translation decoder, so repeated calls over identical text and language codes are built for repeatable outputs.
- `model => 'translation-llm'` runs a generative translation LLM; like other LLM endpoints, phrasing can occasionally vary on open-ended or idiomatic sentences across independent calls.

Below we run two uncached jobs back-to-back over the five non-English feedback rows and verify `job.cache_hit` is `False` on both runs.

```python
determinism_sql = f"""
SELECT
  id,
  declared_lang,
  AI.TRANSLATE(comment, 'en', model => 'nmt') AS nmt_en,
  AI.TRANSLATE(comment, 'en', model => 'translation-llm') AS tllm_en
FROM `{PROJECT_ID}.{DATASET_ID}.ai_translate_feedback`
WHERE id IN (1, 2, 3, 4, 5)
ORDER BY id
"""

uncached_cfg = bigquery.QueryJobConfig(use_query_cache=False)

job_1 = client.query(determinism_sql, job_config=uncached_cfg)
run_1 = job_1.to_dataframe()

job_2 = client.query(determinism_sql, job_config=uncached_cfg)
run_2 = job_2.to_dataframe()

assert job_1.cache_hit is False and job_2.cache_hit is False
print(f'Cache hits -> run 1: {job_1.cache_hit}, run 2: {job_2.cache_hit}')

comparison = pd.DataFrame({
    'id': run_1['id'],
    'lang': run_1['declared_lang'],
    'nmt_match': run_1['nmt_en'] == run_2['nmt_en'],
    'tllm_match': run_1['tllm_en'] == run_2['tllm_en'],
    'nmt_run1': run_1['nmt_en'],
    'tllm_run1': run_1['tllm_en'],
    'tllm_run2': run_2['tllm_en'],
})
print(
    f"Exact matches across 2 uncached runs -> "
    f"nmt: {int(comparison['nmt_match'].sum())}/{len(comparison)}, "
    f"translation-llm: {int(comparison['tllm_match'].sum())}/{len(comparison)}"
)
comparison
```

### Example 7: Four-way head-to-head — `AI.TRANSLATE` (`'nmt'` & `'translation-llm'`) vs `ML.TRANSLATE` vs `AI.GENERATE`

Run all four BigQuery translation paths over the exact same five rows (`id` 1, 2, 3, 4, 8):
1. **`AI.TRANSLATE(..., model => 'nmt')`** — zero-DDL scalar Cloud Translation NMT (EUC)
2. **`AI.TRANSLATE(..., model => 'translation-llm')`** — zero-DDL scalar Cloud Translation LLM (EUC)
3. **`ML.TRANSLATE`** — table-valued `CLOUD_AI_TRANSLATE_V3` remote model (`ai_translate_ml_model`) over a Cloud Resource connection (`comment` aliased to `text_content`, unpacked with `JSON_VALUE`)
4. **`AI.GENERATE(..., endpoint => 'gemini-3.5-flash-lite')`** — general-purpose Gemini prompt (EUC)

```python
client.query(f"""
WITH target_rows AS (
  SELECT id, declared_lang, comment
  FROM `{PROJECT_ID}.{DATASET_ID}.ai_translate_feedback`
  WHERE id IN (1, 2, 3, 4, 8)
),
ml_tvf AS (
  SELECT
    id,
    STRING(ml_translate_result.translations[0].translatedText) AS ml_translate_en
  FROM ML.TRANSLATE(
    MODEL `{PROJECT_ID}.{DATASET_ID}.ai_translate_ml_model`,
    (SELECT id, comment AS text_content FROM target_rows),
    STRUCT('TRANSLATE_TEXT' AS translate_mode, 'en' AS target_language_code)
  )
)
SELECT
  r.id,
  r.declared_lang,
  r.comment,
  AI.TRANSLATE(r.comment, 'en', model => 'nmt') AS ai_translate_nmt,
  m.ml_translate_en,
  AI.TRANSLATE(r.comment, 'en', model => 'translation-llm') AS ai_translate_tllm,
  AI.GENERATE(
    ('Translate the following text into natural English. Return only the translation, without quotes or commentary: ', r.comment),
    endpoint => 'gemini-3.5-flash-lite'
  ).result AS ai_generate_gemini
FROM target_rows AS r
JOIN ml_tvf AS m USING (id)
ORDER BY r.id
""").to_dataframe()
```

---
## Examples — `%%bigquery` Magics

In notebooks (Colab, Colab Enterprise, BigQuery Studio, Vertex AI Workbench, local Jupyter), `%%bigquery` runs SQL directly without wrapping strings in `client.query(...)`. Because `AI.TRANSLATE` needs no connection or model DDL, a magic cell is self-contained.

### Display inline with `return_details => TRUE`

```sql
%%bigquery --project {PROJECT_ID}
SELECT
  id,
  t.result AS translated_en,
  t.status,
  JSON_VALUE(t.details, '$.detected_language_code') AS detected_lang
FROM (
  SELECT
    id,
    AI.TRANSLATE(comment, 'en', return_details => TRUE) AS t
  FROM `bq_ai_functions.ai_translate_feedback`
  WHERE id IN (1, 2, 3, 5)
)
WHERE t.status = 'OK'
ORDER BY id
```

### Capture into a DataFrame

Pass a variable name (`df_magic`) after `%%bigquery` to store the result as a pandas DataFrame for downstream Python inspection.

```sql
%%bigquery df_magic --project {PROJECT_ID}
SELECT
  id,
  declared_lang,
  AI.TRANSLATE(comment, 'en', model => 'nmt') AS nmt_en,
  AI.TRANSLATE(comment, 'en', model => 'translation-llm') AS tllm_en
FROM `bq_ai_functions.ai_translate_feedback`
WHERE id IN (2, 4, 8)
ORDER BY id
```

```python
df_magic[['id', 'declared_lang', 'nmt_en', 'tllm_en']]
```

---
## Examples — BigFrames

`bigframes.bigquery.ai` currently provides dedicated Python wrappers for generative and scoring functions (`generate`, `if_`, `classify`, `score`, `forecast`), and does **not** yet expose a `bbq.ai.translate` helper in `bigframes` 2.x. Run `AI.TRANSLATE` server-side from BigFrames via `bpd.read_gbq_query(...)` to keep translation inside BigQuery while working with a BigFrames `DataFrame`.

```python
import bigframes.pandas as bpd
import bigframes.bigquery as bbq

print(f'bigframes version: {bpd.__version__}')
print(f'hasattr(bbq.ai, "translate"): {hasattr(bbq.ai, "translate")}')

bpd.options.bigquery.project = PROJECT_ID
bpd.options.bigquery.location = LOCATION

bf_df = bpd.read_gbq_query(f"""
SELECT
  id,
  declared_lang,
  AI.TRANSLATE(comment, 'en', model => 'translation-llm') AS translated_en
FROM `{PROJECT_ID}.{DATASET_ID}.ai_translate_feedback`
WHERE id IN (1, 2, 3)
ORDER BY id
""")
bf_df.to_pandas()
```

---
## Which one should you reach for?

All four columns in Example 7 translate inside BigQuery SQL, but they sit at genuinely different points in the operational design space:

| Dimension | `AI.TRANSLATE` (`'nmt'`) | `AI.TRANSLATE` (`'translation-llm'`) | `functions/ml_translate` (`ML.TRANSLATE`) | `functions/ai_generate` (`AI.GENERATE`) |
|---|---|---|---|---|
| **Setup & credentials** | Zero DDL; **caller EUC only** | Zero DDL; **caller EUC only** | `CREATE MODEL` + Cloud Resource **connection SA** | Zero DDL (EUC or optional connection) |
| **SQL shape** | Scalar `STRING` (or `STRUCT`) anywhere | Scalar `STRING` (or `STRUCT`) anywhere | Table-valued function requiring `text_content` alias + JSON unpack | Scalar `STRUCT` (`result`, `status`, `full_response`) |
| **Dynamic per-row `target_language`** | **Yes** (column expression) | **Yes** (column expression) | No (query-wide constant `STRUCT`) | Yes (interpolated into prompt) |
| **Standalone language detection** | Only as a side-effect of translating (`return_details => TRUE`) | Only as a side-effect of translating (`return_details => TRUE`) | **Yes** (`DETECT_LANGUAGE` mode without translating) | Possible via prompt, higher cost/latency |
| **Idioms & domain jargon** | Literal / standard NMT | **Strong** (purpose-built Translation LLM) | Literal / standard NMT (same v3 NMT engine) | **Strongest** when guided by glossary/style instructions |
| **Prompt-injection surface** | None (dedicated translation API) | Minimal (dedicated translation API) | None (dedicated translation API) | **Real** — untrusted user text can try to override your prompt |
| **Success `status` check** | `t.status = 'OK'` | `t.status = 'OK'` | `ml_translate_status = ''` | `status = ''` |
| **Service pricing** | **500K chars/mo free**, then **$20 / 1M input chars** | **$10 / 1M input + $10 / 1M output chars** | Same Cloud Translation NMT tier ($20 / 1M input chars after 500K free) | Vertex AI Gemini input + output token pricing (prompt overhead on short rows) |

**Practical rule of thumb:**
- **Default to `AI.TRANSLATE` (`model => 'nmt'`)** for straightforward multilingual text, dynamic per-row target locales, deterministic repeatability, and the 500K-character monthly free tier.
- **Step up to `AI.TRANSLATE` (`model => 'translation-llm'`)** when customer idioms, colloquialisms, or technical terminology read stiffly under NMT, while keeping zero prompt engineering and per-character billing.
- **Keep `functions/ml_translate` (`ML.TRANSLATE`)** when governance requires a **Cloud Resource connection service account** rather than end-user credentials (for example, scheduled pipelines whose runners lack `roles/cloudtranslate.user`), or when you only need `DETECT_LANGUAGE` without paying to translate.
- **Reach for `functions/ai_generate` (`AI.GENERATE`)** when translation is combined with custom tasks Cloud Translation cannot express — enforcing a product glossary ("never translate *BigQuery Slot*"), adapting tone, or extracting structured fields alongside the translation in a single pass.
