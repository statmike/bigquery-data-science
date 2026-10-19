# `ML.LP_NORM`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mllp_norm`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mllp_norm)

- **Description:** Model-free scalar function that computes the Lp norm (vector magnitude) of a single numeric vector for a given `degree`. `degree = 1.0` gives the Manhattan (L1) norm; `degree = 2.0` gives the Euclidean (L2) norm.
- **Use cases:**
  - Vector normalization (divide a vector by its norm to get a unit vector).
  - Feature magnitude / regularization-style measures.
  - Deriving metrics not built into `ML.DISTANCE` — e.g., Jaccard on binary vectors via dot products and the L1 (Manhattan) norm.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-lp-norm
- **Type:** Scalar.
- **Applies to models:** None — model-free utility.

**Syntax:**
```sql
ML.LP_NORM(vector, degree)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `vector` | `ARRAY<FLOAT64>` or `ARRAY<INT64>` | Yes | — | Vector to compute the norm of. |
| `degree` | `FLOAT64` (or `INT64`) | Yes | — | The p in the Lp norm. `1.0` = Manhattan/L1, `2.0` = Euclidean/L2; any p ≥ 0 supported. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (scalar) | `FLOAT64` | The Lp norm of the vector. Returns `NULL` if `vector` is `NULL`. |

**Best practices:**
- Use `degree = 2.0` for standard L2 normalization; `degree = 1.0` for L1.
- Combine with `ML.DISTANCE` only when you need a metric not directly supported (e.g., Jaccard — verified live: derivable via a dot product for the intersection count and `ML.LP_NORM(v, 1.0)` for each vector's set size, `jaccard = intersection / (norm_a + norm_b - intersection)`).

**Limitations:**
- Operates on a single vector (a norm), not a pair — use `ML.DISTANCE` for pairwise distance.
- `degree` is required (no implicit default).
- Brute-force scalar computation; not an index.

**BigFrames API:** No direct equivalent.
**Repo example (tested):** `bigquery-ml/functions/distance/distance.ipynb` — L0/L1/L2 norms; **verified live that `ML.NORMALIZER(v, p)` (see `functions/scalers/`) equals `v / ML.LP_NORM(v, p)` element-wise** — `ML.LP_NORM` computes exactly the denominator `ML.NORMALIZER` uses internally; also the Jaccard-derivation example above.

**Repo example (tested):** Not present in the bigquery-ml feature-engineering notebooks or elsewhere in this repo (no `ML.LP_NORM` occurrences found). Documentation example pattern: `SELECT ML.LP_NORM([1.0, 2.0, 3.0], 2.0)`.


---
