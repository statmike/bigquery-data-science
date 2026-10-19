# `OBJ.GET_ACCESS_URL`

> **Source:** [`bigquery-ai/reference/unstructured-data-infrastructure.md#objget_access_url`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/unstructured-data-infrastructure.md#objget_access_url)

- **Description:** (Preview) Scalar function that converts an `ObjectRef` into an `ObjectRefRuntime` JSON value containing signed access URLs, with a caller-chosen mode (`'r'` / `'rw'`) and TTL.
- **Use cases:** Generate a **writable** signed URL for saving transformation outputs back to Cloud Storage, hand a read URL to a consumer outside BigQuery, pin an explicit expiry shorter than the 6-hour default.
- **Not needed to call an AI function.** Every multimodal `AI.*` function takes an `ObjectRef` directly; wrapping the reference in `OBJ.GET_ACCESS_URL` buys nothing but a longer query. See [Multimodal Input Patterns](multimodal-input-patterns-by-function.md).
- [documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/objectref_functions)
- **Type:** Scalar function (returns ObjectRefRuntime JSON) — Preview

**Syntax:**
```sql
OBJ.GET_ACCESS_URL(
  objectref,
  mode
  [, duration]
)

OBJ.GET_ACCESS_URL(
  ARRAY<objectref>,
  mode
  [, duration]
)
```
The array overload signs a whole `ARRAY<ObjectRef>` column in one call.

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `objectref` | ObjectRef STRUCT | Required | -- | An ObjectRef value representing a Cloud Storage object. |
| `mode` | STRING | Required | -- | `'r'` for read-only URL, `'rw'` for read and write URLs. |
| `duration` | INTERVAL | Optional | `INTERVAL 6 HOUR` | URL validity period. Range: 30 minutes to 6 hours. |

**Outputs:** Returns `ObjectRefRuntime` JSON:
```json
{
  "obj_ref": {
    "uri": "gs://bucket/file.jpg",
    "version": "12345",
    "authorizer": "us.connection1",
    "details": {"gcs_metadata": {...}}
  },
  "access_urls": {
    "read_url": "https://storage.googleapis.com/...",
    "write_url": "https://storage.googleapis.com/...",
    "expiry_time": "2024-01-15T18:30:00Z"
  }
}
```
On error, `access_urls` is replaced by `runtime_errors`.

**Required permissions:**
- Read URLs (`'r'`): `bigquery.objectRefs.read` (from `roles/bigquery.objectRefReader` or `roles/bigquery.objectRefAdmin`).
- Write URLs (`'rw'`): `bigquery.objectRefs.write` (from `roles/bigquery.objectRefAdmin` only).

**Accepted by AI functions:** yes — `ObjectRefRuntime` still works everywhere `ObjectRef` does, and `AI.AGG`'s reference page is the one that still specifies it. It is no longer the required form for any of them.

**Limitations:**
- Access URLs expire after at most 6 hours. Do not persist `ObjectRefRuntime` values long-term — regenerate from `ObjectRef` values.
- Same 20-connection limit per project+region.
- The `AI.AGG` page's Known Issues note that rows carrying arrays of `ObjectRefRuntime` values "might be skipped," and that some image objects created by `OBJ.GET_ACCESS_URL` "might fail to process." Passing the `ObjectRef` avoids both.

**Locations:** All BigQuery regions supporting Cloud resource connections.

---
