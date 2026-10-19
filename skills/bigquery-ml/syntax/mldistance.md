# `ML.DISTANCE`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mldistance`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mldistance)

- **Description:** Model-free scalar function that computes the distance between two equal-length numeric vectors (`ARRAY<FLOAT64>` / `ARRAY<INT64>`). Supports Euclidean, Manhattan, and Cosine distance. No model is required.
- **Use cases:**
  - Nearest-neighbor / similarity scoring between embedding vectors (e.g., cosine similarity as `1 - ML.DISTANCE(..., 'COSINE')`).
  - Pairwise distance for lookalike, dedup, and recommendation candidate ranking.
  - Building custom clustering / KNN logic outside of a trained model.
  - Ad-hoc distance computation in `SELECT` without `ML.PREDICT`.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-distance
- **Type:** Scalar.
- **Applies to models:** None — model-free utility (operates on raw vectors, not a model).

**Syntax:**
```sql
ML.DISTANCE(vector1, vector2 [, type])
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `vector1` | `ARRAY<FLOAT64>` or `ARRAY<INT64>` | Yes | — | First vector. Must be same length as `vector2`. |
| `vector2` | `ARRAY<FLOAT64>` or `ARRAY<INT64>` | Yes | — | Second vector. Must be same length as `vector1`. |
| `type` | `STRING` | No | `'EUCLIDEAN'` | Distance metric: `'EUCLIDEAN'`, `'MANHATTAN'`, or `'COSINE'`. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (scalar) | `FLOAT64` | Distance between the two vectors. Returns `NULL` if either input vector is `NULL`. |

**Best practices:**
- For cosine *similarity*, compute `1 - ML.DISTANCE(v1, v2, 'COSINE')` (the function returns cosine *distance*).
- Pre-filter/limit candidate pairs before pairwise distance to control cost on large cross joins.
- `'EUCLIDEAN'` is applied when `type` is omitted — pass it explicitly for readability.

**Limitations:**
- Both vectors must be non-`NULL` and the same length; mismatched lengths error.
- Only the three metrics above are supported; other metrics (e.g., Jaccard) must be derived manually (see `ML.LP_NORM`).
- This is brute-force distance, not an index — for scalable ANN search use `VECTOR_SEARCH` / a vector index instead.

**BigFrames API:** No direct equivalent (use array math or `VECTOR_SEARCH`).

**Repo example (tested):** `bigquery-ml/functions/distance/distance.ipynb` — all three metrics standalone, the cosine distance-vs-similarity pattern (same one used in `bigquery-ai/functions/ai_embed/ai_embed.sql`, lines 67/136), and real embedding similarity: trains a scratch `PCA` model on `penguins` and computes `ML.DISTANCE` between two penguins' projections from different species.

---
