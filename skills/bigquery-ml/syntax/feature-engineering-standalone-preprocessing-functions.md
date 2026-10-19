# Feature engineering: standalone preprocessing functions

> **Source:** [`bigquery-ml/reference/model-free-functions.md#feature-engineering-standalone-preprocessing-functions`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#feature-engineering-standalone-preprocessing-functions)

These are **manual feature preprocessing** functions. They can be used two ways:
1. **Inline in a query / standalone** — plain SQL to shape data before `CREATE MODEL` (the model then does *automatic* preprocessing on the result).
2. **Inside the `TRANSFORM` clause** of `CREATE MODEL` — the computed statistics are stored with the model and **re-applied automatically at serving** by `ML.PREDICT` / `ML.TRANSFORM`, and travel with [exported models](https://cloud.google.com/bigquery/docs/exporting-models) and Vertex AI Model Registry registrations. This is the recommended way to prevent training-serving skew.

> **Analytic vs scalar.** Functions that compute statistics across *all* rows (mean, median, mode, min/max, quantiles, stddev) are **analytic** and require an empty `OVER()` clause. Functions that operate row-by-row (e.g. `ML.FEATURE_CROSS`, `ML.POLYNOMIAL_EXPAND`, `ML.BUCKETIZE`) are **scalar** and take no `OVER()`. An analytic function cannot be nested as the argument of another analytic function, but a scalar/analytic result can be wrapped by a scalar function.

> **Note on `ML.TRANSPOSE`:** there is **no `ML.TRANSPOSE` function** in BigQuery ML. Material that speaks of "transposing" refers to the inline `TRANSFORM` clause technique (transposing preprocessing *into* the model), not a function. See the `TRANSFORM` clause pointer at the end of this section. The full catalog of manual preprocessing functions (encoders, scalers, bucketizers, text/image functions) lives in the **Manual preprocessing** reference: <https://cloud.google.com/bigquery/docs/manual-preprocessing>.

---
