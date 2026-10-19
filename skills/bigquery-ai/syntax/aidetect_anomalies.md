# `AI.DETECT_ANOMALIES`

> **Source:** [`bigquery-ai/reference/predictive-ai.md#aidetect_anomalies`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/predictive-ai.md#aidetect_anomalies)

- **Description:** Table-valued function that detects anomalies in time series data using BigQuery ML's built-in TimesFM model. Forecasts expected values from historical data, then compares target data against those forecasts to identify anomalous data points.
- **Use cases:** Detecting anomalous spikes or drops in time series (e.g., sales, bike trips), detecting anomalies across multiple time series simultaneously, computing anomaly probability.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-detect-anomalies)
- **Type:** Table-valued function -- GA

**Syntax:**
```sql
SELECT *
FROM AI.DETECT_ANOMALIES(
  { TABLE HISTORY_TABLE | (HISTORY_QUERY_STATEMENT) },
  { TABLE TARGET_TABLE | (TARGET_QUERY_STATEMENT) },
  data_col => 'DATA_COL',
  timestamp_col => 'TIMESTAMP_COL'
  [, model => 'MODEL']
  [, id_cols => ID_COLS]
  [, anomaly_prob_threshold => ANOMALY_PROB_THRESHOLD]
  [, context_window => CONTEXT_WINDOW]
)
```

**Inputs:**

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `HISTORY_TABLE` / `HISTORY_QUERY_STATEMENT` | Table/Query | Required | -- | -- | Historical data used to generate a forecast baseline |
| `TARGET_TABLE` / `TARGET_QUERY_STATEMENT` | Table/Query | Required | -- | -- | Data in which to detect anomalies. Schema must match historical data. |
| `data_col` | STRING | Required | -- | -- | Data column name. Must be INT64, NUMERIC, BIGNUMERIC, or FLOAT64. |
| `timestamp_col` | STRING | Required | -- | -- | Timestamp column name. Must be TIMESTAMP, DATE, or DATETIME. |
| `model` | STRING | Optional | `'TimesFM 2.5'` | -- | `'TimesFM 2.5'` or `'TimesFM 3.0'` (Preview). |
| `id_cols` | ARRAY\<STRING\> | Optional | -- | -- | ID columns identifying unique time series |
| `anomaly_prob_threshold` | FLOAT64 | Optional | 0.95 | [0, 1) | Threshold for anomaly detection. A target value is anomalous if its anomaly probability exceeds this threshold. |
| `context_window` | INT64 | Optional | Auto-selected | See AI.FORECAST | Context window length for the TimesFM model. Same supported values as AI.FORECAST per model version. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| *id_cols* | (inherited) | Time series identifiers |
| `time_series_timestamp` | STRING | Timestamp column |
| `time_series_data` | FLOAT64 | Data column value |
| `is_anomaly` | BOOL | Whether the value is an anomaly |
| `lower_bound` | FLOAT64 | Lower bound of prediction |
| `upper_bound` | FLOAT64 | Upper bound of prediction |
| `anomaly_probability` | FLOAT64 | Probability that the value is an anomaly |
| `ai_detect_anomalies_status` | STRING | **`NULL` on success** -- not an empty string (verified live 2026-09-02); error string if unsuccessful. Test with `IS NOT NULL`, not `<> ''` -- see the note under [`AI.EVALUATE`](aievaluate.md)'s forecast outputs. |

**Supported models:** TimesFM 2.5 (default), TimesFM 3.0 (Preview).

**Best practices:** Historical and target data schemas must match. Use `id_cols` to break anomalies down by dimensions.

**Limitations:** **Not reproducible run to run, and pinning `model` does not fix it** -- a minority of runs return a different anomaly set and different baselines even with `model` and `context_window` pinned and the query cache off, the same behavior measured in detail on `AI.EVALUATE`. Materialize the result once rather than re-running the function; see the reproducibility note at the top of this section. Only the most recent 1,024 time points are evaluated (contact bqml-feedback@google.com for more). Minimum 3 data points required.

**Locations:** All supported BigQuery ML locations.

**Provisioned throughput:** Not specified. Billed at the evaluation, inspection, and prediction rate.

**BigFrames API:** No direct equivalent for TimesFM-based anomaly detection. Use `%%bigquery` magics or `session.read_gbq_query()` to execute AI.DETECT_ANOMALIES SQL from BigFrames. Note: `bigframes.ml.forecasting.ARIMAPlus.detect_anomalies()` exists but uses ARIMA_PLUS, not TimesFM.

---
