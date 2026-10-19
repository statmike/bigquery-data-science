# `ML.HASH_BUCKETIZE`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mlhash_bucketize`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlhash_bucketize)

- **Description:** Deterministically hashes a string and bucketizes it by taking the hash modulo `hash_bucket_size`, producing an INT64 bucket id. With `hash_bucket_size = 0` it hashes without bucketizing.
- **Use cases:**
  - Hash high-cardinality categorical/string features into a fixed number of buckets (the hashing trick).
  - Stable, deterministic feature encoding that needs no vocabulary fitting.
- **documentation:** [ML.HASH_BUCKETIZE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-hash-bucketize)
- **Type:** Scalar (row-by-row; no `OVER()`).
- **Applies to models:** Any model type supporting manual feature preprocessing when used in `TRANSFORM`; also usable in plain SQL.

**Syntax:**
```sql
ML.HASH_BUCKETIZE(string_expression, hash_bucket_size)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `string_expression` | STRING | Yes | — | The categorical string value to hash/bucketize. |
| `hash_bucket_size` | INT64 | Yes | — | Number of buckets (must be `>= 0`). If `0`, the value is hashed without taking the modulo (no bucketizing). |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (scalar result) | INT64 | Bucket id = `hash(string) mod hash_bucket_size`, or the raw hash when `hash_bucket_size = 0`. |

**Best practices:**
- Choose `hash_bucket_size` large enough to limit collisions for high-cardinality columns.
- Use inside `TRANSFORM` so the same hashing is applied automatically at serving.

**Limitations:**
- Hash collisions are unavoidable when distinct values exceed `hash_bucket_size`.
- Returns INT64 (unlike `ML.BUCKETIZE`/`ML.QUANTILE_BUCKETIZE` which return STRING bin labels); operates on strings, not numerics.

**BigFrames API:** No direct equivalent.
**Repo example (tested):** [`functions/bucketizing/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/bucketizing) — Example 4 contrasts `ML.HASH_BUCKETIZE(island, 0)` (hash only, no modulo) with `ML.HASH_BUCKETIZE(island, 3)` over `penguins`' distinct islands; Example 5 embeds it at `hash_bucket_size = 10` alongside `ML.QUANTILE_BUCKETIZE` in a real `LOGISTIC_REG` `TRANSFORM`, where BQML auto-encodes the INT64 hash bucket as an ordinary feature.

---

**Family note:** All three are exportable feature-preprocessing functions when used in the `TRANSFORM` clause, so the transformation is reapplied automatically during `ML.PREDICT` and accompanies exported / Vertex-registered models. `ML.BUCKETIZE` and `ML.HASH_BUCKETIZE` are scalar; `ML.QUANTILE_BUCKETIZE` is analytic and requires an empty `OVER()` clause. See the [Manual feature preprocessing](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-preprocessing-functions) reference.


---
