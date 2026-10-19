# `OBJ.MAKE_REF`

> **Source:** [`bigquery-ai/reference/unstructured-data-infrastructure.md#objmake_ref`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/unstructured-data-infrastructure.md#objmake_ref)

- **Description:** (Preview) Scalar function that creates an `ObjectRef` value containing reference information for a Cloud Storage object. This is the entry point for creating ObjectRef values from raw URI strings — no validation is performed on JSON input.
- **Use cases:** Create ObjectRef values for standard table columns without object tables, build ad-hoc ObjectRef values inline in queries for one-off multimodal analysis, reference transformation outputs saved to Cloud Storage.
- [documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/objectref_functions)
- **Type:** Scalar function (returns ObjectRef STRUCT) — Preview

**Syntax (URI, optional authorizer):**
```sql
OBJ.MAKE_REF(
  uri
  [, authorizer]
  [, version => version_value]
  [, details => gcs_metadata_json]
)
```

**Syntax (JSON input):**
```sql
OBJ.MAKE_REF(
  objectref_json
)
```

**Syntax (re-authorize an existing ObjectRef):**
```sql
OBJ.MAKE_REF(
  objectref,
  authorizer
)
```
The top-level `authorizer` overwrites whatever the input `objectref` carried.

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `uri` | STRING | Required (overload 1) | Cloud Storage URI, e.g., `gs://mybucket/file.jpg`. Can be a column reference. |
| `authorizer` | STRING | Optional (overload 1) | Cloud resource connection, e.g., `us.myconnection`, used for **delegated access**. Must be in the same project and region as the query. Omit it and the ObjectRef uses **direct access** instead. |
| `version_value` | STRING | Optional | Cloud Storage object version. |
| `gcs_metadata_json` | JSON | Optional | Pre-supplied metadata: `{"content_type", "md5_hash", "size", "updated"}`. Fills `details` without a Cloud Storage round-trip. |
| `objectref_json` | JSON | Required (overload 2) | JSON with schema `{"uri": "string", "authorizer": "string"}`. No validation performed. |

**Outputs:** Returns `STRUCT<uri STRING, version STRING, authorizer STRING, details JSON>`. Only `uri` and `authorizer` are populated unless you supply `version` / `details`; otherwise use `OBJ.FETCH_METADATA` to fill them.

> **Dropping the authorizer changes who reads the object, not whether it works.** `OBJ.MAKE_REF('gs://bucket/file.pdf')` is legal and succeeds against private buckets — but only because the identity running the query holds `storage.objectViewer` on that bucket. That is **direct access**: the object is fetched as the query runner. Passing the connection gives **delegated access**, where the object is fetched as the connection's service account and the grant is auditable and independent of whoever runs the query. The examples throughout this project pass the connection for that reason.
>
> **Inside a VPC Service Controls perimeter the recommendation inverts.** Delegated access mints a signed HTTPS URL, and Agent Platform blocks HTTP/HTTPS fetches for projects inside a perimeter — so a delegated-access `ObjectRef`, **including an object table's `ref` column**, fails with `INVALID_ARGUMENT: HTTP links are not supported for requests restricted by VPCSC.` in the output's `status` field. In that environment use the single-argument `OBJ.MAKE_REF(uri)`: direct access sends the Cloud Storage URI to the model with no signed URL in between. This is also a reason to prefer inline `OBJ.MAKE_REF` over object tables inside a perimeter — an object table has no direct-access form.

**Limitations:**
- Maximum **20 connections** per project+region for queries referencing ObjectRef values.
- Connection must be in the same project and region as the query.

**Locations:** All BigQuery regions supporting Cloud resource connections.

---
