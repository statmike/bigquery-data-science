# `ML.BUCKETIZE`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mlbucketize`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlbucketize)

- **Description:** Bucketizes a continuous numerical value into a string-named bucket using a manually supplied array of split points (bin boundaries).
- **Use cases:**
  - Convert a numeric column (age, price) into categorical bins for linear/logistic models.
  - Encode domain knowledge as explicit boundaries (e.g. age brackets).
  - Inside `TRANSFORM` so the same boundaries are reapplied at `ML.PREDICT`.
- **documentation:** [ML.BUCKETIZE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-bucketize)
- **Type:** Scalar (operates row-by-row; no `OVER()`).
- **Applies to models:** Any model type that supports manual feature preprocessing (linear/logistic regression, boosted trees, DNN, k-means, etc.) when used in `TRANSFORM`; also usable in plain SQL.

**Syntax:**
```sql
ML.BUCKETIZE(numerical_expression, array_split_points[, exclude_boundaries[, output_format]])
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `numerical_expression` | NUMERIC/FLOAT64 | Yes | — | The numerical value to bucketize. |
| `array_split_points` | ARRAY\<numeric\> | Yes | — | Sorted points at which to split into buckets. |
| `exclude_boundaries` | BOOL | No | `FALSE` | If `TRUE`, drops the implicit lower (`-inf`) and upper (`+inf`) overflow buckets so only interior bins remain. |
| `output_format` | STRING | No | `"bucket_names"` | `"bucket_names"` → `bin_<i>` (index starts at 1); `"bucket_ranges"` → `[lower, upper)`; `"bucket_ranges_json"` → `{"start":"..","end":".."}`. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (scalar result) | STRING | Bucket label, e.g. `bin_3` or `[2, 3)` depending on `output_format`. |

**Best practices:**
- Generate boundaries dynamically with `GENERATE_ARRAY(start, end, step)` for evenly spaced bins.
- Place inside `TRANSFORM` so the bin definition travels with the model to serving/export.
- Use `exclude_boundaries = TRUE` to suppress overflow buckets when out-of-range values are not expected.

**Limitations:**
- Split points must be numeric and sorted; behavior with NULL `numerical_expression` returns NULL.
- Boundaries are fixed (no data-driven balancing) — for equal-frequency bins use `ML.QUANTILE_BUCKETIZE`.
- **GOTCHA, verified live — `exclude_boundaries=TRUE` does NOT null out-of-range values.** It's easy to misread "drops the implicit lower/upper overflow buckets" as "values outside the split-point range become NULL." What actually happens: the **outermost split points are dropped entirely**, merging the overflow bucket into its nearest interior neighbor. With split points `[10, 20, 30]`: default gives 4 bins `(-inf,10)` `[10,20)` `[20,30)` `[30,+inf)`; with `exclude_boundaries=TRUE` this becomes just 2 bins `(-inf,20)` `[20,+inf)` — the `10` and `30` split points disappear, leaving only `20` as the sole effective boundary. No value ever becomes NULL from this option alone.

**BigFrames API:** `bigframes.ml.preprocessing.KBinsDiscretizer` (strategy-dependent; not a 1:1 of explicit split points).
**Repo example (tested):** [`functions/bucketizing/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/bucketizing) — Example 1 runs all three `output_format` values against the same `[3000, 4000, 5000]` split points on `penguins.body_mass_g`; Example 2 is the `exclude_boundaries` clarification above, proven live with `[10, 20, 30]`; Example 5 embeds `ML.QUANTILE_BUCKETIZE` and `ML.HASH_BUCKETIZE` together in a real `LOGISTIC_REG` `TRANSFORM` (accuracy ~0.81).

---
