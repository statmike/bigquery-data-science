# `OBJ.FETCH_METADATA`

> **Source:** [`bigquery-ai/reference/unstructured-data-infrastructure.md#objfetch_metadata`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/unstructured-data-infrastructure.md#objfetch_metadata)

- **Description:** (Preview) Scalar function that fetches Cloud Storage metadata for a partially populated `ObjectRef` value. Takes an ObjectRef with `uri` and `authorizer` (typically from `OBJ.MAKE_REF`) and fills in the `details` field with `content_type`, `md5_hash`, `size`, and `updated` from Cloud Storage. Still succeeds on error — the `details` field contains an `error` field instead.
- **Use cases:** Populate ObjectRef columns with full metadata when not using object tables, refresh metadata for existing ObjectRef values after underlying objects change, combine with `OBJ.MAKE_REF` in a single expression: `OBJ.FETCH_METADATA(OBJ.MAKE_REF(uri, 'connection'))`.
- [documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/objectref_functions)
- **Type:** Scalar function (returns fully-populated ObjectRef STRUCT) — Preview

**Syntax:**
```sql
OBJ.FETCH_METADATA(
  objectref
)

OBJ.FETCH_METADATA(
  ARRAY<objectref>
)
```
The array overload fetches metadata for a whole `ARRAY<ObjectRef>` column in one call.

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `objectref` | ObjectRef STRUCT | Required | Partially populated ObjectRef (with `uri` and `authorizer`). Typically from `OBJ.MAKE_REF()`. |

**Outputs:** Returns a fully populated `ObjectRef` STRUCT. The `details` JSON field contains:
```json
{
  "gcs_metadata": {
    "content_type": "image/png",
    "md5_hash": "d9c38814e44028bf7a012131941d5631",
    "size": 23000,
    "updated": 1741374857000000
  }
}
```
On error, `details` contains `{"errors": {"OBJ.FETCH_METADATA": "error message"}}` instead.

**Required permissions:** `bigquery.objectRefs.read` on the connection (from `roles/bigquery.objectRefReader` or `roles/bigquery.objectRefAdmin`). Connection service account needs `roles/storage.objectUser`.

**Limitations:**
- Same 20-connection limit per project+region.
- Less scalable than object tables for large numbers of objects (requires per-object metadata retrieval from Cloud Storage).

**Locations:** All BigQuery regions supporting Cloud resource connections.

---
