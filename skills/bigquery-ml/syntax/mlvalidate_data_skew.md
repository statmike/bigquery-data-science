# `ML.VALIDATE_DATA_SKEW`

> **Source:** [`bigquery-ml/reference/model-management-monitoring.md#mlvalidate_data_skew`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-management-monitoring.md#mlvalidate_data_skew)

- **Description:** Detects **training/serving skew** — compares statistics of new (serving) data against the **training statistics saved inside the model** at creation time. Original training data is not required.
- **Use cases:**
  - Catch serving inputs that diverge from what the model was trained on.
  - Trigger retraining when feature distributions shift from baseline.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-validate-data-skew
- **Type:** Table-valued function.
- **Applies to models:** Any model trained on structured columns whose training statistics were stored (standard BQML model_types with feature columns).

**Syntax:**
```sql
SELECT *
FROM ML.VALIDATE_DATA_SKEW(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,           -- baseline = stored training stats
  (query_statement)                                 -- compare = serving data
  [, STRUCT(
       categorical_default_threshold AS categorical_default_threshold,
       numerical_default_threshold   AS numerical_default_threshold,
       categorical_metric_type       AS categorical_metric_type,
       thresholds                    AS thresholds,
       num_rank_histogram_buckets    AS num_rank_histogram_buckets,
       TRUE AS enable_visualization_link
     )]
);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model ref | Yes | — | Supplies the baseline (stored training) statistics. |
| compare data | `(query_statement)` | Yes | — | Serving data to validate. Only columns matching training feature columns are compared. |
| `categorical_default_threshold` | FLOAT64 | No | 0.3 | Anomaly threshold for categorical features. Range \[0, 1). |
| `numerical_default_threshold` | FLOAT64 | No | 0.3 | Anomaly threshold for numerical features. Range \[0, 1). |
| `categorical_metric_type` | STRING | No | `L_INFTY` | `L_INFTY` or `JENSEN_SHANNON_DIVERGENCE`. |
| `thresholds` | ARRAY\<STRUCT\<STRING, FLOAT64\>\> | No | — | Per-column overrides, e.g. `[('col_a', 0.1)]`. |
| `num_rank_histogram_buckets` | INT64 | No | 50 | Buckets for categorical rank histogram. Range \[1, 10000\]. |
| `enable_visualization_link` | BOOL | No | FALSE | Emits `visualization_link` (model must be Vertex-registered). |

**Outputs:** see shared output schema under `ML.VALIDATE_DATA_DRIFT`.

**Best practices:** Register the model in Vertex AI (`MODEL_REGISTRY='VERTEX_AI'`) to get clickable distribution visualizations. **MAJOR GOTCHA, verified live: how you sample the comparison data matters as much as the function call itself.** `SELECT ... LIMIT N` (no `ORDER BY`) on a non-randomly-ordered table returns a non-representative slice — tested on `bigquery-public-data.ml_datasets.census_adult_income`, a `LIMIT 5000` grab flagged `education_num` as `is_anomaly=TRUE` (Jensen-Shannon divergence ~0.65 vs. a 0.3 threshold) even though it came from the exact same table the model trained on. Switching to `WHERE RAND() < p` for a true random sample dropped every column's divergence to near-zero, correctly reporting no skew. A naive `LIMIT` can manufacture a false skew alarm.
**Limitations:** Numerical metric is always Jensen-Shannon divergence (not configurable); needs a model that stored training stats.
**BigFrames API:** No direct equivalent.
**Repo example (tested):** [`functions/model_monitoring/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/model_monitoring) Example 1 — the `LIMIT`-vs-`RAND()` sampling gotcha above, run against a self-contained scratch `LOGISTIC_REG` model. `census_adult_income` is not randomly ordered, so a `LIMIT 5000` "serving" slice of the *identical* source table makes `education_num` flag `is_anomaly = TRUE` at JS divergence ~0.65 (threshold 0.3); switching to `WHERE RAND() < 0.15` drops every column's divergence to near zero, confirming the alarm was a sampling artifact rather than real skew.

---
