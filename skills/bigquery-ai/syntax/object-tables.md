# Object Tables

> **Source:** [`bigquery-ai/reference/unstructured-data-infrastructure.md#object-tables`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/unstructured-data-infrastructure.md#object-tables)

- **Description:** Read-only external tables over unstructured data objects in Cloud Storage. Each row corresponds to a Cloud Storage object, with columns for object metadata. Object tables use access delegation via a Cloud resource connection — users need access to the table, not direct access to Cloud Storage.
- **Use cases:** Indexing Cloud Storage objects for AI function processing, document analysis pipelines, image/video/audio inference, joining unstructured data results with structured BigQuery data.
- [introduction](https://cloud.google.com/bigquery/docs/object-table-introduction) · [create](https://cloud.google.com/bigquery/docs/object-table-create) · [DDL reference](https://cloud.google.com/bigquery/docs/reference/standard-sql/data-definition-language#create_external_table_statement)

**CREATE syntax:**
```sql
CREATE [ OR REPLACE ] EXTERNAL TABLE [ IF NOT EXISTS ] `PROJECT_ID.DATASET.TABLE_NAME`
WITH CONNECTION { `PROJECT_ID.REGION.CONNECTION_ID` | DEFAULT }
OPTIONS (
    object_metadata = 'SIMPLE',
    uris = ['BUCKET_PATH'[, ...]],
    [max_staleness = STALENESS_INTERVAL,]
    [metadata_cache_mode = 'CACHE_MODE']
);
```

**Example (minimal):**
```sql
CREATE EXTERNAL TABLE `myproject.mydataset.documents`
WITH CONNECTION `myproject.us.myconnection`
OPTIONS (
    object_metadata = 'SIMPLE',
    uris = ['gs://mybucket/documents/*.pdf']
);
```

**Example (with metadata caching):**
```sql
CREATE EXTERNAL TABLE `myproject.mydataset.documents`
WITH CONNECTION `myproject.us.myconnection`
OPTIONS (
    object_metadata = 'SIMPLE',
    uris = ['gs://mybucket/*'],
    max_staleness = INTERVAL 1 DAY,
    metadata_cache_mode = 'AUTOMATIC'
);
```

**Metadata columns:**

| Column | Type | Description |
|--------|------|-------------|
| `uri` | STRING | Cloud Storage URI (`gs://bucket/path/object`). |
| `generation` | INTEGER | Object version identifier. |
| `content_type` | STRING | MIME type of the object (e.g., `image/jpeg`, `application/pdf`). Defaults to `application/octet-stream` if not set. |
| `size` | INTEGER | Content length in bytes. |
| `md5_hash` | STRING | MD5 hash of the data, base64-encoded. |
| `updated` | TIMESTAMP | Last time the object's metadata was modified. |
| `metadata` | RECORD (REPEATED) | Custom metadata as key-value pairs (`name` STRING, `value` STRING). |
| `ref` | STRUCT (Preview) | `ObjectRef` value: `STRUCT<uri STRING, version STRING, authorizer STRING, details JSON>`. Created only if on the multimodal data preview allowlist. |

There is also a `data` pseudocolumn containing raw file bytes, used by `ML.DECODE_IMAGE`. It cannot be directly queried.

> **The image-preprocessing family lives in the sibling project** — `ML.DECODE_IMAGE`, `ML.RESIZE_IMAGE`, `ML.CONVERT_COLOR_SPACE`, `ML.CONVERT_IMAGE_TYPE`, documented in [`bigquery-ml/reference/model-free-functions.md`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#image-preprocessing-functions-mldecode_image-mlresize_image-mlconvert_image_type-mlconvert_color_space) with a tested example in [`bigquery-ml/functions/image/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/image). Two things carry over to any object-table work here: those four functions **require a BigQuery Editions reservation** and fail outright on on-demand pricing (verified live 2026-09-11; no official page says so), and `ML.DECODE_IMAGE` accepts **any** `BYTES` value, so the `data` pseudocolumn is the usual source rather than the only one.

**CREATE parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `object_metadata` | STRING | Required | -- | Must be `'SIMPLE'` for object tables. |
| `uris` | ARRAY\<STRING\> | Required | -- | Cloud Storage URIs. One `*` wildcard allowed per path. Multiple buckets supported. |
| `max_staleness` | INTERVAL | Optional | `0` (disabled) | Metadata cache staleness. Range: 30 minutes to 7 days. |
| `metadata_cache_mode` | STRING | Optional (required if `max_staleness > 0`) | -- | `'AUTOMATIC'` (system-refreshed every 30–60 min) or `'MANUAL'` (you call `BQ.REFRESH_EXTERNAL_METADATA_CACHE`). |

**Metadata caching:**
- Without caching, queries must list files from Cloud Storage — can take several minutes for large tables.
- With caching, queries use cached metadata. Set `max_staleness` and `metadata_cache_mode`.
- Automatic refresh: system-defined interval (30–60 min). Recommended: create a `BACKGROUND` reservation for refresh jobs.
- Manual refresh: `CALL BQ.REFRESH_EXTERNAL_METADATA_CACHE('project.dataset.table');`
- Cache expires after 7 days if not refreshed.

**Signed URLs (EXTERNAL_OBJECT_TRANSFORM):**
```sql
SELECT uri, signed_url
FROM EXTERNAL_OBJECT_TRANSFORM(TABLE `mydataset.myobjecttable`, ['SIGNED_URL']);
```
Signed URLs expire after 6 hours. Row-level access policies restrict which URLs a user can generate.

`EXTERNAL_OBJECT_TRANSFORM` also rewrites the table's `ref` column from an `ObjectRef` into a signed `ObjectRefRuntime`. **No AI function requires that rewrite** — they all take the `ObjectRef` directly. Use the transform when something outside the AI call needs a fetchable URL: a display link, delegated access for another consumer, a shorter-lived credential.

**Connection requirements:**
- Requires a **Cloud resource connection** (type: "Vertex AI remote models, remote functions, BigLake and Spanner").
- Connection's service account needs `roles/storage.objectViewer` on the Cloud Storage bucket.
- Connection must be in the same region as the dataset.

**AI function integration:** every one of these reads the `ref` column as-is — an `ObjectRef` — with no signing step in between.
- `ML.PROCESS_DOCUMENT` — document extraction via Document AI processors.
- `AI.GENERATE_TEXT` / `AI.GENERATE` — text generation from object data: `STRUCT(text AS prompt, [ref] AS object_refs)`.
- `AI.GENERATE_EMBEDDING` — embeddings from image/video data: a `content` column of `ObjectRef`.
- `AI.SCORE` — score documents using tuple syntax: `AI.SCORE(('text', ref))`.
- `AI.CLASSIFY` — classify documents: `AI.CLASSIFY(ref, categories)`.
- `ML.ANNOTATE_IMAGE` — image annotation via Cloud Vision API.
- `ML.TRANSCRIBE` — audio transcription via Speech-to-Text API.

**Limitations:**
- Read-only — cannot alter data or use DML.
- Maximum **60 million rows** (300 million in preview with allowlist).
- Maximum **10 GB of object metadata** per query.
- Not available in Legacy SQL, AWS, or Azure.
- `UNION ALL` combining empty and non-empty object tables may error.
- Signed URLs expire after 6 hours.

**Locations:** Any BigQuery region or multi-region. Connection must be colocated with the dataset.

---
