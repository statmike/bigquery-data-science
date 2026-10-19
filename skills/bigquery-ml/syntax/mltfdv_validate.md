# `ML.TFDV_VALIDATE`

> **Source:** [`bigquery-ml/reference/model-management-monitoring.md#mltfdv_validate`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-management-monitoring.md#mltfdv_validate)

- **Description:** Compares two `DatasetFeatureStatisticsList` protos to identify anomalous differences; returns a TFDV `Anomalies` proto (JSON). Supports `SKEW` (training vs. serving) and `DRIFT` (serving vs. serving) modes.
- **Use cases:**
  - TFDV-native anomaly detection inside BigQuery.
  - Integrate BQML monitoring with an existing TFDV/TFX pipeline.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-tfdv-validate
- **Type:** Scalar function (returns one proto value).
- **Applies to models:** N/A.

**Syntax:**
```sql
SELECT ML.TFDV_VALIDATE(
  base_stats,        -- DatasetFeatureStatisticsList (from ML.TFDV_DESCRIBE or a stored column)
  compare_stats,     -- DatasetFeatureStatisticsList
  'SKEW'             -- or 'DRIFT'
  [, categorical_default_threshold FLOAT64
   , categorical_metric_type STRING
   , numerical_default_threshold FLOAT64
   , numerical_metric_type STRING
   , thresholds ARRAY<STRUCT<STRING, FLOAT64>> ]
) AS validate;
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| base / compare stats | `DatasetFeatureStatisticsList` (JSON) | Yes | — | From `ML.TFDV_DESCRIBE` or a persisted snapshot column. |
| validation type | STRING | Yes | — | `'SKEW'` or `'DRIFT'`. |
| `categorical_default_threshold` | FLOAT64 | No | 0.3 | — |
| `categorical_metric_type` | STRING | No | `L_INFTY` | `L_INFTY` / `JENSEN_SHANNON_DIVERGENCE`. |
| `numerical_default_threshold` | FLOAT64 | No | 0.3 | — |
| `numerical_metric_type` | STRING | No | `JENSEN_SHANNON_DIVERGENCE` | — |
| `thresholds` | ARRAY\<STRUCT\<STRING, FLOAT64\>\> | No | — | Per-feature overrides. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (scalar) | JSON/STRING | TFDV `Anomalies` proto as JSON. Parse with `json_format.ParseDict` into `tfmd.proto.anomalies_pb2.Anomalies`; render via `tfdv.display_anomalies`. |

**Best practices:** Reuse stored `ML.TFDV_DESCRIBE` snapshots as one input to avoid recomputing baseline stats.
**Limitations:** No schema validation; choosing `JENSEN_SHANNON_DIVERGENCE` as the default threshold metric can exclude a feature from the report. Requires TFDV Python libs to visualize.
**BigFrames API:** No direct equivalent.
**Repo example (tested):** [`functions/model_monitoring/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/model_monitoring) Example 3 — both `'DRIFT'` mode (reproducing the same `education_num` signal as `ML.VALIDATE_DATA_DRIFT` above, JSON-parsed to show the actual `drift_skew_info` measurement rather than a truncated raw string) and `'SKEW'` mode (same divergence value, confirming `'SKEW'`/`'DRIFT'` differ only in the baseline schema's comparator type and semantic framing, not the underlying computation).
