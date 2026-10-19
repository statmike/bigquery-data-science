# `ML.FORECAST`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlforecast`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlforecast)

- **Description:** Returns forecasted values with standard error and prediction/confidence intervals for a trained `ARIMA_PLUS` or `ARIMA_PLUS_XREG` time-series model.
- **Use cases:**
  - Produce point forecasts + intervals over a future horizon.
  - Serve demand/volume forecasts directly in BigQuery (one row per `forecast_timestamp` per series).
  - Multivariate forecasting using future covariate values (`ARIMA_PLUS_XREG`).
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-forecast
- **Type:** Table-valued.
- **Applies to models:** `ARIMA_PLUS`, `ARIMA_PLUS_XREG`. **Status:** GA.

**Syntax:**
```sql
-- ARIMA_PLUS (univariate):
SELECT *
FROM ML.FORECAST(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  STRUCT(14 AS horizon, 0.95 AS confidence_level)
);

-- ARIMA_PLUS_XREG (multivariate) — future feature values are REQUIRED:
SELECT *
FROM ML.FORECAST(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  STRUCT(30 AS horizon, 0.8 AS confidence_level),
  (SELECT date, temperature, wind_speed
   FROM `PROJECT_ID.DATASET.future_features`)
);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `horizon` | INT64 | No | 3 | Number of future time points to forecast. Max = `horizon` set in `CREATE MODEL` (or 1000 if unset). Set `horizon` at model creation to save query time. |
| `confidence_level` | FLOAT64 | No | 0.95 | Fraction of future values expected within the prediction interval. Range `[0, 1)`. |
| `TABLE`/`QUERY_STATEMENT` | table/query | `ARIMA_PLUS_XREG` only | — | Future covariate values; column names/types must match the model. Ignored extra columns are dropped. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `\<time_series_id_col\>` | (varies) | Series id column(s), present only when the model was trained with `time_series_id_col`. |
| `forecast_timestamp` | TIMESTAMP | Forecast point (rows sorted chronologically per series). |
| `forecast_value` | FLOAT64 | Point forecast (midpoint of the prediction interval). |
| `standard_error` | FLOAT64 | Standard error of the forecast. |
| `confidence_level` | FLOAT64 | Echoes the input confidence level. |
| `prediction_interval_lower_bound` / `prediction_interval_upper_bound` | FLOAT64 | Prediction interval bounds (depend on `standard_error` and `confidence_level`). |
| `confidence_interval_lower_bound` / `confidence_interval_upper_bound` | FLOAT64 | Confidence interval bounds (legacy columns; equal the prediction bounds). |

**Measured:** the prediction interval is **not** `forecast_value ± Φ⁻¹((1+confidence_level)/2) · standard_error`. The multiplier it actually uses is constant across horizons and differs from the exact normal quantile. It is the inverse of **Abramowitz & Stegun 26.2.18** — the Hastings quartic approximation to the normal CDF, `P(x) = 1 − ½(1 + 0.196854x + 0.115194x² + 0.000344x³ + 0.019527x⁴)⁻⁴`, with `\|error\| < 2.5e-4` — which reproduces every multiplier to about a millionth, the precision at which they print:

| `confidence_level` | multiplier used | A&S 26.2.18 inverse | A&S error | normal quantile | normal error |
|---|---|---|---|---|---|
| 0.80 | 1.282287 | 1.282284 | −0.000002 | 1.281552 | −0.000735 |
| 0.90 | 1.643071 | 1.643074 | +0.000003 | 1.644854 | +0.001782 |
| 0.95 | 1.956458 | 1.956457 | −0.000001 | 1.959964 | +0.003506 |
| 0.98 | 2.327237 | 2.327236 | −0.000001 | 2.326348 | −0.000889 |
| 0.99 | 2.587695 | 2.587694 | −0.000002 | 2.575829 | −0.011866 |

Errors are *candidate minus multiplier used*. A Student *t* quantile is ruled out by direction — *t* is always wider than normal. A constant scale factor is ruled out by the sign change in the `normal error` column: non-monotone error that grows in the tail is what a fixed-degree polynomial approximation does, not what a different distribution does. **Word this carefully** — what is established is that the rendered multipliers are numerically *indistinguishable* from that published approximation at every level tested. It is a claim about arithmetic, not about what BigQuery's source contains.

**Practical rule: never back a standard error out of the rendered bounds.** Dividing a 95% width by `2 × 1.959964` returns a value 0.18% too small — invisible on a chart, and enough to swamp any arithmetic check built on it. The `standard_error` column is the quantity itself.

The same approximation, used forward rather than inverted, reproduces `AI.CAUSAL_EFFECT`'s p-value exactly — see [`model-free-functions.md#aicausal_effect`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#aicausal_effect). Verified 2026-09-16 on an `ARIMA_PLUS` model in [`workflows/causal_effect/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/causal_effect).

**Best practices:** Set `horizon` (and `holiday_region`) at `CREATE MODEL` time. Use the forecast-with-`LIMIT` pattern instead of post-filtering large outputs.
**Limitations:** Adding computation on top of large outputs (min/max, arithmetic, filters) can raise "Resources exceeded during query execution". `ARIMA_PLUS_XREG` requires future feature values to forecast.
**BigFrames API:** `bigframes.ml.forecasting.ARIMAPlus().predict(X)`.
**Repo example (tested):**
- `bigquery-ml/models/arima_plus/arima_plus.sql` (Example 6) — `STRUCT(28 AS horizon, 0.9 AS confidence_level)` over a multi-series Citibike-style model built with `time_series_id_col`, selecting the forecast plus both prediction-interval bounds. Example 1 shows the single-series form with only `STRUCT(28 AS horizon)`.
- `bigquery-ml/models/arima_plus_xreg/arima_plus_xreg.sql` — the same call for the covariate model, where future feature values must be supplied to forecast at all.

---
