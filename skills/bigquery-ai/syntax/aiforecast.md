# `AI.FORECAST`

> **Source:** [`bigquery-ai/reference/predictive-ai.md#aiforecast`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/predictive-ai.md#aiforecast)

- **Description:** Table-valued time series forecasting function. Forecasts a time series using BigQuery ML's built-in TimesFM model without requiring model creation or training.
- **Use cases:** Forecasting future values (e.g., daily bike trips), forecasting multiple independent time series using ID columns (e.g., forecast by user type), generating prediction intervals, comparing historical vs forecasted data.
- [documentation](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-forecast)
- **Type:** Table-valued function

**Syntax (univariate -- GA):**
```sql
SELECT *
FROM AI.FORECAST(
  { TABLE TABLE | (QUERY_STATEMENT) },
  data_col => 'DATA_COL',
  timestamp_col => 'TIMESTAMP_COL'
  [, model => 'MODEL']
  [, id_cols => ID_COLS]
  [, { horizon => HORIZON | forecast_end_timestamp => FORECAST_END_TIMESTAMP }]
  [, confidence_level => CONFIDENCE_LEVEL]
  [, output_historical_time_series => OUTPUT_HISTORICAL_TIME_SERIES]
  [, context_window => CONTEXT_WINDOW]
)
```

**Syntax (multivariate -- Preview, TimesFM 3.0 only):**
```sql
SELECT *
FROM AI.FORECAST(
  { TABLE TABLE | (QUERY_STATEMENT) },
  target_cols => [TARGET_COLS],
  timestamp_col => 'TIMESTAMP_COL',
  model => 'TimesFM 3.0'
  [, id_cols => [ID_COLS]]
  [, horizon => HORIZON]
  [, confidence_level => CONFIDENCE_LEVEL]
  [, context_window => CONTEXT_WINDOW]
  [, past_covariate_cols => [PAST_COVARIATE_COLS]]
  [, future_covariate_cols => [FUTURE_COVARIATE_COLS]]
  [, output_historical_time_series => OUTPUT_HISTORICAL_TIME_SERIES]
)
```

`target_cols` replaces `data_col`; the two forms are exclusive. `model => 'TimesFM 3.0'` is mandatory on this form -- omit it, or name another version, and the call fails with the generic `Invalid table-valued function AI.FORECAST`. The documented multivariate syntax lists only `horizon`, but `forecast_end_timestamp` is accepted here too (measured).

**Inputs:**

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `TABLE` / `QUERY_STATEMENT` | Table/Query | Required | -- | -- | Input data to forecast |
| `data_col` | STRING | Required | -- | -- | Name of the data column. Must be INT64, NUMERIC, BIGNUMERIC, or FLOAT64. |
| `timestamp_col` | STRING | Required | -- | -- | Name of the timestamp column. Must be TIMESTAMP, DATE, or DATETIME. |
| `model` | STRING | Optional | `'TimesFM 2.5'` | -- | `'TimesFM 2.5'` or `'TimesFM 3.0'` (Preview). Required, and must be 3.0, for the multivariate form. |
| `target_cols` | ARRAY\<STRING\> | Multivariate only | -- | -- | One or more data columns to forecast jointly (INT64, NUMERIC, BIGNUMERIC, FLOAT64). Replaces `data_col`. |
| `past_covariate_cols` | ARRAY\<STRING\> | Optional (multivariate) | -- | -- | Numeric columns known only historically (e.g. visits that drive sales). NULL on any future rows. |
| `future_covariate_cols` | ARRAY\<STRING\> | Optional (multivariate) | -- | -- | Numeric columns known for past *and* future (e.g. a promotion calendar, weekend flag). Must be populated on a row for every future timestamp to forecast; targets are NULL on those rows. **`horizon` is capped by the future rows supplied** -- 30 requested with 14 future rows returns 14, silently. |
| `id_cols` | ARRAY\<STRING\> | Optional | -- | -- | ID columns identifying unique time series. Must be STRING, INT64, ARRAY\<STRING\>, or ARRAY\<INT64\>. |
| `horizon` | INT64 | Optional | 10 | [1, 10000] on 2.5; [1, 1024] on 3.0 | Number of time series data points to forecast. Mutually exclusive with `forecast_end_timestamp`. |
| `forecast_end_timestamp` | TIMESTAMP | Optional | -- | -- | End timestamp for forecasted values. Horizon is calculated from the end timestamp and input frequency. Mutually exclusive with `horizon`. Valid calculated horizon range: [1, 10000]. |
| `confidence_level` | FLOAT64 | Optional | 0.95 | [0, 1) | Percentage of future values that fall in the prediction interval |
| `output_historical_time_series` | BOOL | Optional | FALSE | -- | When TRUE, returns input data along with forecasted data |
| `context_window` | INT64 | Optional | Per model, see below | See below | Context window length for the TimesFM model |

**Context Window Supported Values:**

| Model | Supported Context Window Lengths | Default when unspecified |
|-------|----------------------------------|--------------------------|
| TimesFM 2.5 | 64, 128, 256, 512, 1024, 2048, 4096, 8192, 15360 | The smallest window covering the input data |
| TimesFM 3.0 | `n * 32` for `n` in [2, 64] -- i.e. 64 to 2048 | The maximum, 2048; older points are ignored |

Measured: 2.5 rejects a value off its grid (`96` fails); 3.0 rejects a value above 2048 but accepts one that is not a multiple of 32 (`100` runs), so stay on the documented grid if you want to know what the model saw.

**Outputs (when `output_historical_time_series = FALSE`):**

| Column | Type | Description |
|--------|------|-------------|
| *id_cols* | (inherited) | Time series identifiers |
| `forecast_timestamp` | TIMESTAMP | Timestamps of the forecasted time series |
| `forecast_value` | FLOAT64 | 50% quantile (median) value of the forecast |
| `confidence_level` | FLOAT64 | The confidence level value |
| `prediction_interval_lower_bound` | FLOAT64 | Lower bound of prediction interval |
| `prediction_interval_upper_bound` | FLOAT64 | Upper bound of prediction interval |
| `ai_forecast_status` | STRING | Empty string (zero-length, not `NULL`) if successful; error string if unsuccessful. This is the *only* one of the three TimesFM status columns that behaves this way -- `ai_evaluate_status` and `ai_detect_anomalies_status` return `NULL` on success. |

**Outputs (when `output_historical_time_series = TRUE`):**

| Column | Type | Description |
|--------|------|-------------|
| *id_cols* | (inherited) | Time series identifiers |
| `time_series_type` | STRING | `'history'` or `'forecast'` |
| `time_series_timestamp` | TIMESTAMP | Timestamps |
| `time_series_data` | FLOAT64 | Historical value or forecast median |
| `confidence_level` | FLOAT64 | The confidence level value |
| `prediction_interval_lower_bound` | FLOAT64 | Lower bound (NULL for historical points) |
| `prediction_interval_upper_bound` | FLOAT64 | Upper bound (NULL for historical points) |
| `ai_forecast_status` | STRING | Status |

**Outputs (multivariate form):** the schema is restructured around the targets.

| Column | Type | Description |
|--------|------|-------------|
| *id_cols* | (inherited) | Time series identifiers |
| *timestamp column* | TIMESTAMP | **Keeps the input column's name** (`date`, not `forecast_timestamp`) |
| *one per target* | STRUCT\<`value` FLOAT64, `prediction_interval_lower_bound` FLOAT64, `prediction_interval_upper_bound` FLOAT64\> | Named after the target column. Bounds are NULL on `history` rows |
| `time_series_type` | STRING | `'forecast'`, or `'history'` when `output_historical_time_series = TRUE` |
| `confidence_level` | FLOAT64 | The confidence level value |
| `ai_forecast_status` | STRING | Empty string on success; error string otherwise |

**Supported models:** TimesFM 2.5 (default), TimesFM 3.0 (Preview). Multivariate forecasting requires TimesFM 3.0.

**Best practices:** Set `output_historical_time_series` to TRUE to compare historical values with forecasted values. Minimum 3 data points required. With future covariates, supply one input row per future timestamp with the targets NULL and the covariates populated -- the forecast cannot run past the rows you give it.

**Limitations:** TimesFM 2.5 max context: 15,360 data points; TimesFM 3.0 max context: 2,048 data points and max horizon 1,024. Additional data points beyond the max are ignored. Minimum 3 data points. Covariates require the `target_cols` form -- `data_col` plus a covariate argument is rejected. `AI.EVALUATE` has no multivariate branch, so a multivariate forecast is scored one target at a time.

**Locations:** All supported BigQuery ML locations.

**Provisioned throughput:** Not specified. Billed at the evaluation, inspection, and prediction rate (BigQuery ML on-demand pricing). TimesFM 3.0 moves to token-based pricing on **2026-12-01**; the pricing page publishes the formula (each data point is one token): `input tokens = S * (L * (N_target + N_past_cov) + (L + H) * N_fut_cov)` and `output tokens = S * H * (N_target + N_past_cov)` -- `S` series, `L` context length, `H` horizon, `N_*` the target / past-covariate / future-covariate column counts -- at $0.05 / mtok input and $0.20 / mtok output. Note that 3.0's default context is the full 2,048 points, so an unspecified `context_window` also maximizes `L`.

**BigFrames API:** `bigframes.bigquery.ai.forecast(df, data_col=..., timestamp_col=...)` — Wraps `AI.FORECAST` SQL directly. No model object needed. Supports `id_cols`, `horizon`, `confidence_level`, `context_window`, and `model` parameters. Note: `bigframes.ml.forecasting.ARIMAPlus` is a different model (ARIMA_PLUS, not TimesFM).

> **Wrapper skew:** the BigFrames wrapper (`bigframes` 2.39.0) declares `model: str = "TimesFM 2.0"` -- a version the SQL reference page no longer lists -- while the SQL function defaults to TimesFM 2.5. Calling `bbq.ai.forecast()` without `model` therefore runs a different model than the equivalent SQL; measured 2026-10-09, the unpinned wrapper call still executes, and `model="TimesFM 3.0"` passes through to the univariate form. The wrapper has no `target_cols` or covariate arguments. Pass `model` explicitly from BigFrames, and use SQL for the multivariate form.

---
