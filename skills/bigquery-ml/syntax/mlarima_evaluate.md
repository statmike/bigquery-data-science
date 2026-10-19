# `ML.ARIMA_EVALUATE`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlarima_evaluate`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlarima_evaluate)

- **Description:** Returns the auto-ARIMA model selection results and quality metrics, one row per time series (the candidate chosen by auto.ARIMA, or all candidates with `show_all_candidate_models`).
- **Use cases:**
  - Inspect the selected `(p,d,q)` order, drift, and AIC per series.
  - See which decomposition features fired (`has_holiday_effect`, `has_spikes_and_dips`, `has_step_changes`) and detected seasonalities.
  - Surface per-series training failures via `error_message`.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-arima-evaluate
- **Type:** Table-valued. **Applies to models:** `ARIMA_PLUS`, `ARIMA_PLUS_XREG`. **Status:** GA.

**Syntax:**
```sql
SELECT *
FROM ML.ARIMA_EVALUATE(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  STRUCT(FALSE AS show_all_candidate_models)
);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `show_all_candidate_models` | BOOL | No | FALSE | If TRUE, returns every candidate ARIMA model evaluated by auto.ARIMA; if FALSE, only the selected model per series. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `\<time_series_id_col\>` | (varies) | Series id (when trained with `time_series_id_col`). |
| `non_seasonal_p` / `non_seasonal_d` / `non_seasonal_q` | INT64 | ARIMA order (AR lags, differencing degree, MA terms). |
| `has_drift` | BOOL | Whether a drift term is included. |
| `log_likelihood` | FLOAT64 | Model log-likelihood. |
| `AIC` | FLOAT64 | Akaike Information Criterion (lower is better; selection criterion). |
| `variance` | FLOAT64 | Variance of the model residuals. |
| `seasonal_periods` | ARRAY\<STRING\> | Detected seasonalities, e.g. `[WEEKLY]`, `[WEEKLY, YEARLY]`, `[NO_SEASONALITY]`. |
| `has_holiday_effect` | BOOL | Holiday effect detected (when `holiday_region` set). |
| `has_spikes_and_dips` | BOOL | Spike/dip outliers detected. |
| `has_step_changes` | BOOL | Step (level) changes detected. |
| `error_message` | STRING | Per-series training error, empty when successful. |

**Best practices:** Order by the series id column for stable review; check `error_message` for short/failed series.
**Limitations:** `seasonal_periods`, `has_holiday_effect`, etc. depend on `CREATE MODEL` options (e.g. `holiday_region`).
**BigFrames API:** No direct equivalent.
**Repo example (tested):** `bigquery-ml/models/arima_plus/arima_plus.sql` (Example 3) — the full per-series model-selection table for a multi-series model. Example 10 in the same file uses it as the *verification* of a manual order: training with `auto_arima = FALSE` and `non_seasonal_order = STRUCT(2 AS p, 1 AS d, 1 AS q)`, then reading `non_seasonal_p/d/q` back to confirm auto.ARIMA was actually bypassed.

---
