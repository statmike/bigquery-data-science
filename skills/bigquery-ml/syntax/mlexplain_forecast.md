# `ML.EXPLAIN_FORECAST`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlexplain_forecast`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlexplain_forecast)

- **Description:** Superset of `ML.FORECAST`: returns the forecast **plus** the full time-series decomposition (trend, seasonality per period, holiday effects, spikes/dips, step changes, residual) for both history and forecast rows. Enabled by `decompose_time_series = TRUE` (the ARIMA_PLUS default).
- **Use cases:**
  - Explain *why* a forecast moves (trend vs. weekly seasonality vs. a holiday).
  - Recover the cleaned/adjusted fit (`time_series_adjusted_data`) for plotting and custom metrics.
  - Per-holiday and per-feature (XREG) attribution.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-explain-forecast
- **Type:** Table-valued. **Applies to models:** `ARIMA_PLUS`, `ARIMA_PLUS_XREG`. **Status:** GA.

**Syntax:**
```sql
SELECT *
FROM ML.EXPLAIN_FORECAST(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  STRUCT(28 AS horizon, 0.95 AS confidence_level)
);
```

**Inputs:** same `horizon` / `confidence_level` STRUCT as `ML.FORECAST` (`ARIMA_PLUS_XREG` also takes a future-features table/query).

**Outputs (in addition to the `ML.FORECAST` columns):**

| Column | Type | Description |
|--------|------|-------------|
| `time_series_timestamp` | TIMESTAMP | Point in time (history or forecast). |
| `time_series_type` | STRING | `history` or `forecast`. |
| `time_series_data` | FLOAT64 | Observed (history) or forecast value, including noise components. |
| `time_series_adjusted_data` | FLOAT64 | Cleaned fit (excludes `spikes_and_dips`, `step_changes`, `residual`). |
| `trend` | FLOAT64 | Long-term level. |
| `seasonal_period_yearly`/`_quarterly`/`_monthly`/`_weekly`/`_daily` | FLOAT64 | Per-period seasonal effect; NULL if that period isn't detected. |
| `holiday_effect` | FLOAT64 | Total holiday effect = sum of `holiday_effect_\<holiday_name\>` subcolumns (one column per detected holiday). |
| `spikes_and_dips` | FLOAT64 | Outlier component (history only). |
| `step_changes` | FLOAT64 | Abrupt level-shift component (history only). |
| `residual` | FLOAT64 | Unexplained remainder (history only). |
| `attribution_feature_\<name\>` | FLOAT64 | Per-covariate contribution (`ARIMA_PLUS_XREG` only). |

Decomposition identity: `time_series_data = trend + Σ seasonal_period_* + holiday_effect + spikes_and_dips + step_changes + residual`. For `forecast` rows, `spikes_and_dips`/`step_changes`/`residual` are not applicable, so `time_series_data` and `time_series_adjusted_data` coincide.

**Best practices:** Use `time_series_adjusted_data WHERE time_series_type='forecast'` as the fitted forecast for custom SQL metrics (MAPE/MAE/RMSE).
**Limitations:** Decomposition components for spikes/step/residual exist only for history. Same large-output memory caveat as `ML.FORECAST`.
**BigFrames API:** No direct equivalent (use `ML.EXPLAIN_FORECAST` via SQL).
**Repo example (tested):**
- `bigquery-ml/models/arima_plus/arima_plus.sql` (Example 7) — selects `time_series_type`, `time_series_data`, `time_series_adjusted_data`, `trend`, `seasonal_period_weekly`, `seasonal_period_yearly`, and `holiday_effect` for one series out of a multi-series model.
- Custom holidays (Example 10 in the same file) surface as a `holiday_effect_<holiday_name>` column. Reported honestly: with only 4 occurrences in the training history the estimated effect came out at **0.0** — statistically indistinguishable from no effect. The column existing is not evidence the effect is real.
- **GOTCHA, verified: `forecast_limit_lower_bound` / `forecast_limit_upper_bound` are incompatible with `ML.EXPLAIN_FORECAST`.** `ML.FORECAST` and every other lifecycle function are unaffected — only this one is blocked, which is why the multi-series model in that file deliberately does not set a bound.

---
