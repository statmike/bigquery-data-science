# `ML.TFDV_DESCRIBE`

> **Source:** [`bigquery-ml/reference/model-management-monitoring.md#mltfdv_describe`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-management-monitoring.md#mltfdv_describe)

- **Description:** Computes fine-grained descriptive statistics emitted as a TensorFlow Data Validation `DatasetFeatureStatisticsList` proto (JSON). Same behavior as `tfdv.generate_statistics_from_csv`.
- **Use cases:**
  - Produce TFDV-compatible stats for `tfdv.visualize_statistics` / `display_anomalies`.
  - Persist serving-stats snapshots over time for later drift comparison.
  - Feed `ML.TFDV_VALIDATE`.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-tfdv-describe
- **Type:** Table-valued function.
- **Applies to models:** N/A (operates on data).

**Syntax:**
```sql
SELECT *
FROM ML.TFDV_DESCRIBE(
  { TABLE `PROJECT_ID.DATASET.TABLE_NAME` | (query_statement) }
  [, STRUCT(...)]
);
```

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `dataset_feature_statistics_list` | JSON/STRING | TFDV `DatasetFeatureStatisticsList` proto serialized as JSON. Parse with `json_format.ParseDict` into `tfmd.proto.statistics_pb2.DatasetFeatureStatisticsList`. |

**Best practices:** Store the output column into a snapshot table (`t TIMESTAMP, dataset_feature_statistics_list ...`) to enable historical drift.
**Limitations:** Output is a proto blob, not tabular per-feature rows; needs the `tensorflow-data-validation` / `tensorflow-metadata` Python libs to render.
**BigFrames API:** No direct equivalent.
**Repo example (tested):** [`functions/model_monitoring/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/model_monitoring) Example 3 — `ML.TFDV_DESCRIBE` on `census_adult_income`, JSON-parsed in SQL so the proto's contents are readable without installing the `tensorflow-data-validation` Python package. Rendering the proto graphically (`tfdv.visualize_statistics`) requires that package and is outside this project's dependency set; the parsed output carries the same measurements.

---
