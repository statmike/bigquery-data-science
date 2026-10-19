# ObjectRef and ObjectRefRuntime Schema Reference

> **Source:** [`bigquery-ai/reference/unstructured-data-infrastructure.md#objectref-and-objectrefruntime-schema-reference`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/unstructured-data-infrastructure.md#objectref-and-objectrefruntime-schema-reference)

**ObjectRef** — a STRUCT stored in BigQuery table columns:
```sql
STRUCT<
  uri STRING,           -- Cloud Storage URI (gs://bucket/path/file)
  version STRING,       -- Cloud Storage object version
  authorizer STRING,    -- Cloud resource connection for access
  details JSON          -- Cloud Storage metadata (content_type, md5_hash, size, updated)
>
```

**ObjectRefRuntime** — a JSON value produced by `OBJ.GET_ACCESS_URL`:
```json
{
  "obj_ref": { "uri", "version", "authorizer", "details" },
  "access_urls": { "read_url", "write_url", "expiry_time" }
}
```

**Array support:** `ARRAY<STRUCT<uri STRING, version STRING, authorizer STRING, details JSON>>` columns can store ordered collections of ObjectRef values (e.g., video frames). Use `ARRAY_AGG` with `ORDER BY` to aggregate and `UNNEST` with `WITH OFFSET` to decompose.

**Content requirements** (documented on `AI.GENERATE` and `AI.GENERATE_TEXT`, and applying wherever object references are accepted):
- Content must be in one of the formats the Gemini API's `mimeType` parameter supports.
- **At most one video object per input.** More than one is not rejected loudly — plan around the cap.
- Videos are truncated to **two minutes**; a longer video returns results based on its first two minutes only.

**Typical workflow:**
```
URI string
  → OBJ.MAKE_REF(uri, connection)     → ObjectRef
  → AI.GENERATE(STRUCT(prompt, ref))  → Generated output
```

**Shortcut from object tables:** when the `ref` column is available (preview allowlist), skip `OBJ.MAKE_REF` too — the column already *is* an `ObjectRef`.

**Where the other two functions fit.** `OBJ.FETCH_METADATA` and `OBJ.GET_ACCESS_URL` are no longer steps on the path to an AI call; they are tools you reach for on purpose:

| You want | Call |
|----------|------|
| Feed an object to an AI function | Nothing — pass the `ObjectRef` |
| `content_type`, `size`, `md5_hash`, `updated` in SQL | `OBJ.FETCH_METADATA(objectref)` |
| Display the object in query results | `OBJ.GET_READ_URL(objectref)` |
| Hand a URL to a consumer outside BigQuery | `OBJ.GET_ACCESS_URL(objectref, 'r')` |
| Write a transformation output back to GCS | `OBJ.GET_ACCESS_URL(objectref, 'rw')` |
| An expiry shorter than the 6-hour default | `OBJ.GET_ACCESS_URL(objectref, 'r', INTERVAL 30 MINUTE)` |

---
