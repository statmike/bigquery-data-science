# `ML.VALIDATE_DATA_DRIFT`

> **Source:** [`bigquery-ml/reference/model-management-monitoring.md#mlvalidate_data_drift`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-management-monitoring.md#mlvalidate_data_drift)

- **Description:** Detects **data drift** — compares statistics between **two datasets** (typically two serving windows) to flag anomalous distribution changes over time. The `MODEL` argument here is optional and only adds the visualization link.
- **Use cases:**
  - Compare last week vs. this week of serving data.
  - Compare training data vs. current serving data as a manual skew check (no stored stats needed).
  - Drift on model-transformed features by wrapping inputs in `ML.TRANSFORM`.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-validate-data-drift
- **Type:** Table-valued function.
- **Applies to models:** Any (model is optional, used only for the visualization link).

**Syntax:**
```sql
SELECT *
FROM ML.VALIDATE_DATA_DRIFT(
  (base_query_statement),       -- baseline window
  (compare_query_statement),    -- comparison window
  [STRUCT(
     categorical_default_threshold AS categorical_default_threshold,
     numerical_default_threshold   AS numerical_default_threshold,
     categorical_metric_type       AS categorical_metric_type,
     thresholds                    AS thresholds,
     num_rank_histogram_buckets    AS num_rank_histogram_buckets
   )]
  [, MODEL `PROJECT_ID.DATASET.MODEL_NAME`]   -- optional: enables visualization_link
);
```

**Inputs:** same STRUCT options as `ML.VALIDATE_DATA_SKEW` (defaults: categorical/numerical threshold `0.3`,
`categorical_metric_type='L_INFTY'`, `num_rank_histogram_buckets=50`). Pass `STRUCT()` to accept all defaults.
The two positional args are both `(query_statement)` (base, compare).

**Outputs (shared by SKEW and DRIFT):** one row per compared column.

| Column | Type | Description |
|--------|------|-------------|
| `input` | STRING | Input (feature) column name. |
| `metric` | STRING | Comparison metric: `JENSEN_SHANNON_DIVERGENCE` (numerical), `L_INFTY` or `JENSEN_SHANNON_DIVERGENCE` (categorical). |
| `value` | FLOAT64 | Computed statistical difference between the two datasets. |
| `threshold` | FLOAT64 | Threshold applied to `value`. |
| `is_anomaly` | BOOL | TRUE when `value` > `threshold`. |
| `visualization_link` | STRING | Present only when `MODEL` / `enable_visualization_link` is supplied; URL to Vertex AI monitoring visualization. |

### How the metric is computed (measured, not quoted)

Reproduced by hand against the function in [`functions/model_monitoring/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/model_monitoring) Example 4, on
two disjoint deterministic populations of `census_adult_income`. This applies to `ML.VALIDATE_DATA_SKEW`,
`ML.TFDV_VALIDATE`, and Vertex AI Model Monitoring equally — they report the same quantities.

**Categorical columns — statistics of the data, reproducible exactly.**

- `L_INFTY` is the [Chebyshev distance](https://en.wikipedia.org/wiki/Chebyshev_distance): the largest absolute
  difference in category proportion between the two datasets. One category decides it.
- `JENSEN_SHANNON_DIVERGENCE` mixes the two proportion vectors (`mix = (p + q) / 2`), takes a
  Kullback-Leibler divergence of each side from the mixture using **base-2** logs, averages the two, and sums
  across categories. It is the **divergence**, not the Jensen-Shannon *distance* — no square root.
- Verified: `race`, `relationship`, and `sex` reproduce for both metrics with a largest disagreement of
  exactly zero across all six numbers.

**Numeric columns — a histogram comparison, not a comparison of the values.**

1. Each input gets its **own** ten-bucket equal-width histogram spanning **its own minimum to its own
   maximum** (the untyped histogram in the `ML.TFDV_DESCRIBE` proto, alongside the `QUANTILES` one). Counts
   are fractional: mass crossing a bucket edge is split across it.
2. The two histograms are realigned onto the union of both edge sets, each bucket's mass divided in
   proportion to overlap width.
3. Jensen-Shannon divergence, base 2, over the two aligned histograms.

Reproducing those three steps matches BigQuery to ~1e-16 on `age`, `education_num`, and `hours_per_week`.

**The operational consequence.** Jensen-Shannon divergence is maximized by the finest partition, so the
divergence over a column's distinct values is a *ceiling* for any bucketing of it. On `education_num` the
function returns **4.5x that ceiling** — 0.181256 against 0.039775 — because one population's values start at
1 and the other's at 2, offsetting the two bucket grids. Appending a single row holding `education_num = 1`
to the 1,116-row comparison set (a value the base population already holds 51 of) re-cuts the edges onto the
base population's and drops the reported drift to 0.036175, `is_anomaly = FALSE`.

This is TFDV semantics rather than a defect: the metric is defined on the statistics proto, and the proto's
histogram is a fixed-size summary. Three properties combine to produce the gap — ten buckets regardless of
cardinality, per-dataset edges, and uniform density assumed inside a bucket.

**Reading numeric drift in practice:**

1. Categorical metrics need no such care — both are statistics of the data.
2. A numeric drift value is only meaningful alongside the two ranges it was computed from; `ML.DESCRIBE_DATA`'s
   `min`/`max` ([`functions/exploration/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/exploration)) is the cheapest way to see them, and a
   range that moves between windows means the number is not comparable across them.
3. Where a numeric column's range moves for reasons that are not drift, bucketize it yourself (`ML.BUCKETIZE`
   with fixed split points, or a `CASE`) and monitor the bucket label as a categorical column. Then the edges
   are yours and identical in every window.

**Best practices:** Filter `WHERE is_anomaly = True` to drive alerts/retraining (see job SQL). Use `ML.TRANSFORM(MODEL, data)` as the inputs to monitor drift on engineered features rather than raw columns.
**Limitations:** No schema validation between the two inputs (mismatched columns are ignored). For categorical, choosing `JENSEN_SHANNON_DIVERGENCE` changes which features appear in the report vs. `L_INFTY`.
**BigFrames API:** No direct equivalent.
**Repo example (tested):** [`functions/model_monitoring/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/model_monitoring) Example 2 — real (non-sampling-artifact) drift on `census_adult_income`, between two disjoint deterministic populations (`workclass = ' Self-emp-inc'`, 1,116 rows, against everyone else, 31,445 rows): `education_num` 0.181256 crosses a 0.1 threshold while `age` 0.081105 and `hours_per_week` 0.095444 do not. Plus a live `categorical_metric_type` comparison showing `L_INFTY` and `JENSEN_SHANNON_DIVERGENCE` flag genuinely different columns at the same threshold (at 0.05, `L_INFTY` flags `race` 0.0804 / `relationship` 0.3097 / `sex` 0.2173, while JS flags only `relationship` 0.0792 — `race` falls to 0.0244 and `sex` to 0.0497, three ten-thousandths under the line), and a `thresholds` per-column override demo. Example 4 then computes both metrics by hand (see *How the metric is computed* above). **`bigquery-ml/pipelines/`** uses the 3-argument form (no `MODEL` — verified live that a plain `CREATE MODEL`-trained model doesn't qualify as the "Model Registry MODEL" the optional argument requires) as the core drift-check trigger for a real conditional-retrain pipeline, re-expressed across three orchestrators: `sql_scripting/` (inside a multi-statement `BEGIN...END` script), `cloud_workflows/` (via the BigQuery connector, built across several `assign` steps due to a 400-character YAML expression limit), and `composer_airflow/` (`BigQueryInsertJobOperator` + `BranchPythonOperator` reading the result via XCom). All three find the identical real, non-contrived signal — 5 of 12 GA4 behavioral features drift genuinely (`total_engagement_time_msec` strongest), driven by a real Black Friday/Cyber Monday population shift in the underlying data, not a sampling artifact.

---
