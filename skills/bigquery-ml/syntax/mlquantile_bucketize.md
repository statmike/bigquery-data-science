# `ML.QUANTILE_BUCKETIZE`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mlquantile_bucketize`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlquantile_bucketize)

- **Description:** Bucketizes a continuous numerical value into `num_buckets` buckets of approximately equal frequency, with boundaries computed from quantiles across all rows.
- **Use cases:**
  - Equal-frequency binning of skewed numeric features without choosing boundaries by hand.
  - Inside `TRANSFORM` — the training-time quantiles are stored and reapplied at prediction.
- **documentation:** [ML.QUANTILE_BUCKETIZE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-quantile-bucketize)
- **Type:** Analytic (requires an empty `OVER()` clause; computes statistics over all rows).
- **Applies to models:** Any model type supporting manual feature preprocessing when used in `TRANSFORM`; also usable in plain SQL with `OVER()`.

**Syntax:**
```sql
ML.QUANTILE_BUCKETIZE(numerical_expression, num_buckets[, output_format]) OVER()
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `numerical_expression` | NUMERIC/FLOAT64 | Yes | — | The numerical value to bucketize. |
| `num_buckets` | INT64 | Yes | — | Number of quantile buckets to split into. |
| `output_format` | STRING | No | `"bucket_names"` | `"bucket_names"` → `bin_<i>` (index starts at 1); `"bucket_ranges"` → interval notation, e.g. `(-inf, 2.5)`, `[2.5, 4.6)`, `[4.6, +inf)`; `"bucket_ranges_json"` → JSON, e.g. `{"start":"2.5","end":"4.6"}`. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (analytic result) | STRING | Quantile bucket label for the row. |

**Best practices:**
- ALWAYS use an empty `OVER()` clause — this is required for ML analytic functions and ensures statistics are collected over the whole column.
- Prefer over `ML.BUCKETIZE` when you want balanced bin populations rather than fixed cut points.

**Limitations:**
- Must use `OVER()` (empty); other window framing is not supported.
- Quantile estimates are approximate on very large inputs.

**BigFrames API:** `bigframes.ml.preprocessing.KBinsDiscretizer(strategy="quantile")`.
**Repo example (tested):** [`functions/bucketizing/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/bucketizing) — Example 3 runs `ML.QUANTILE_BUCKETIZE(culmen_length_mm, 4) OVER()` in both `bucket_names` and `bucket_ranges` form side by side; Example 5 embeds it in a `LOGISTIC_REG` `TRANSFORM` alongside `ML.HASH_BUCKETIZE`, where the training-time quantiles are stored with the model.

---
