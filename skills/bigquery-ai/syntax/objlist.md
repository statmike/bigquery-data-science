# `OBJ.LIST`

> **Source:** [`bigquery-ai/reference/unstructured-data-infrastructure.md#objlist`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/unstructured-data-infrastructure.md#objlist)

- **Description:** (GA) Table-valued function that lists Cloud Storage objects matching a URI with one `*` wildcard per path segment and returns their metadata plus an `ObjectRef` for each — ad-hoc discovery of unstructured data without creating an object table. Works across all Cloud Storage storage classes.
- **Use cases:** Point an `AI.*` function at "every PDF in this prefix" in one query, feed `AI.AGG` a set of images, build an extract-and-load pipeline over a landing bucket without DDL, prototype against a public sample bucket.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/objectref_functions#objlist)
- **Type:** Table-valued function — GA

**Syntax:**
```sql
SELECT uri, content_type, size, ref
FROM OBJ.LIST(
  uri
  [, authorizer]
)
```

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `uri` | STRING literal | Required | Cloud Storage path with at most one `*` per segment, e.g. `gs://bucket/images/*.png`. Must be a literal — scalar subqueries and `CONCAT` are rejected. Must not end in `/` or contain `//` (`gs://bucket/images/` fails with *"GCS paths cannot end with a slash"* and suggests the `/*` form). |
| `authorizer` | STRING | Optional | Cloud resource connection for **delegated access**, e.g. `project.us.connection`. Omit it and every returned `ref` uses **direct access** — fetched as the identity running the query. |

**Outputs:** one row per object: `uri` STRING, `content_type` STRING, `size` INT64, `md5_hash` STRING, `updated` TIMESTAMP, `metadata` ARRAY\<STRUCT\<name STRING, value STRING\>\>, `generation` INT64, and `ref` — an `ObjectRef` whose `authorizer` is populated only when you passed one.

**Measured 2026-10-09** against `gs://cloud-samples-data/bigquery/tutorials/cymbal-pets/images/*.png` (205 objects): the no-authorizer form and the authorizer form both feed `AI.GENERATE`, the typed variants, `AI.IF`/`AI.SCORE`/`AI.CLASSIFY`, `AI.AGG`, `AI.EMBED` and `AI.SIMILARITY` directly via `ref`, with an empty `status` on every row. Direct access worked here because the bucket is public; on a private bucket it works only if the query runner holds `storage.objectViewer`, and inside a VPC Service Controls perimeter it is the form that works (see the note under [`OBJ.MAKE_REF`](objmake_ref.md)).

**Limitations:** Shares the object-table limitations because it generates the same metadata dynamically. The listing is computed per query — there is no persistence and no change tracking; use an object table for that. `ML.PROCESS_DOCUMENT` still reads object tables only.

**Locations:** All BigQuery regions supporting Cloud resource connections.

---
