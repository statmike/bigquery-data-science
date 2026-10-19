# `OBJ.GET_READ_URL`

> **Source:** [`bigquery-ai/reference/unstructured-data-infrastructure.md#objget_read_url`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/unstructured-data-infrastructure.md#objget_read_url)

- **Description:** (Preview) Scalar function that returns a `STRUCT<url STRING, status STRING>` holding a read URL for a Cloud Storage object. The URL expires after **45 minutes**.
- **Use cases:** Render an object inline in BigQuery Studio query results — the `url` column displays the image rather than the link text. A shorter-lived, read-only alternative to `OBJ.GET_ACCESS_URL` when all you need is to look at the object.
- [documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/objectref_functions)
- **Type:** Scalar function (returns STRUCT) — Preview

**Syntax:**
```sql
OBJ.GET_READ_URL(objectref)
```

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `objectref` | ObjectRef STRUCT | Required | Must use **delegated access** — the ObjectRef has to carry an `authorizer`. A direct-access ObjectRef is rejected. |

**Outputs:** `STRUCT<url STRING, status STRING>`. On success `url` holds the read URL and `status` is `NULL`; on failure `url` is `NULL` and `status` holds the error message. Nothing raises — check `status`.

```sql
SELECT OBJ.GET_READ_URL(poster) AS read_url
FROM `mydataset.films`;
```

**How it differs from `OBJ.GET_ACCESS_URL`:**

| | `OBJ.GET_READ_URL` | `OBJ.GET_ACCESS_URL` |
|---|---|---|
| Returns | `STRUCT<url, status>` | `ObjectRefRuntime` JSON |
| Modes | Read only | `'r'` or `'rw'` |
| TTL | Fixed 45 minutes | 30 min – 6 hours, caller-set |
| Access | Delegated access required | Either |
| Errors | Reported in `status` | Reported in `runtime_errors` |

**Locations:** All BigQuery regions supporting Cloud resource connections.

---
