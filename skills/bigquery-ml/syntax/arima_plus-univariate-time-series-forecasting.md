# `ARIMA_PLUS`  (univariate time series forecasting)

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#arima_plus--univariate-time-series-forecasting`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#arima_plus--univariate-time-series-forecasting)

- **Description:** A univariate time series forecasting model built on the auto.ARIMA algorithm wrapped in an automated pipeline ("PLUS"). Beyond fitting ARIMA (autoregressive `p`, integrated `d`, moving-average `q`), it automatically infers data frequency, handles irregular intervals, deduplicates timestamps (mean), interpolates missing/absent data points linearly, cleans spikes and dips, adjusts abrupt step changes, decomposes trend + multiple seasonalities (STL + double-exponential smoothing), and models holiday effects. auto.ARIMA trains dozens of candidate models in parallel and selects the one with the lowest AIC.
- **When to use:**
  - You have a single demand signal over time (one `time` + one `value` column) and want a forecast plus prediction intervals.
  - You want to forecast many independent series in one query (one model per `time_series_id_col` group, up to 100,000,000 series).
  - You want interpretable decomposition (trend, seasonality, holiday, spikes/dips, step changes) via `ML.EXPLAIN_FORECAST`.
  - You want in-database time series anomaly detection via `ML.DETECT_ANOMALIES`.
  - For zero-config foundation-model forecasting, prefer `AI.FORECAST` (TimesFM) instead — see the cross-link below.
- **Category:** time-series.
- **Connection required:** No.
- **Status:** GA. (Note: the plain `ARIMA` model type is deprecated; use `ARIMA_PLUS`.)
- **documentation:** [CREATE MODEL for ARIMA_PLUS](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-time-series) · [ML.FORECAST](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-forecast) · [ML.ARIMA_EVALUATE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-arima-evaluate) · [ML.EXPLAIN_FORECAST](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-explain-forecast) · [ML.ARIMA_COEFFICIENTS](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-arima-coefficients) · single / multiple time-series tutorials.

> **Cross-links (owned by `../bigquery-ai/`, not duplicated here):** TimesFM foundation-model forecasting — [`AI.FORECAST`, `AI.EVALUATE`, `AI.DETECT_ANOMALIES`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md). For the multivariate variant with external regressors, see `ARIMA_PLUS_XREG` ([CREATE MODEL ARIMA_PLUS_XREG](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-multivariate-time-series)).

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
OPTIONS(
  MODEL_TYPE                = 'ARIMA_PLUS',
  TIME_SERIES_TIMESTAMP_COL = 'starttime',   -- TIMESTAMP/DATE/DATETIME
  TIME_SERIES_DATA_COL      = 'num_trips',   -- INT64/NUMERIC/BIGNUMERIC/FLOAT64
  TIME_SERIES_ID_COL        = 'start_station_name', -- optional; many series at once
  DATA_FREQUENCY            = 'DAILY',
  HORIZON                   = 28,
  AUTO_ARIMA_MAX_ORDER      = 5,
  HOLIDAY_REGION            = ['GLOBAL', 'US']
) AS
SELECT start_station_name, starttime, num_trips
FROM `PROJECT_ID.DATASET.forecasting_data`
WHERE splits IN ('TRAIN','VALIDATE');   -- ARIMA+ is univariate; fold VALIDATE into training
```

**Options (model-specific):**

| Option | Type | Required | Default | Range / Values | Description |
|--------|------|----------|---------|----------------|-------------|
| `model_type` | STRING | Yes | — | `'ARIMA_PLUS'` | Model type. |
| `time_series_timestamp_col` | STRING | Yes | — | col of TIMESTAMP/DATE/DATETIME | Time points column. |
| `time_series_data_col` | STRING | Yes | — | col of INT64/NUMERIC/BIGNUMERIC/FLOAT64 | Value to forecast. |
| `time_series_id_col` | STRING or ARRAY\<STRING\> | No | — | STRING/INT64/ARRAY of those | ID column(s); fit+forecast multiple series in one query. |
| `horizon` | INT64 | No | `1000` | max `10000` | Number of future time points to forecast (per series). |
| `auto_arima` | BOOL | No | `TRUE` | TRUE/FALSE | Auto-tune p,d,q (and drift). Must be `TRUE` for multiple series. |
| `auto_arima_max_order` | INT64 | No | `2` | `1`–`5` | Max of non-seasonal p+q search space. Higher = more accurate, slower/costlier. |
| `auto_arima_min_order` | INT64 | No | `0` | INT64 | Min of non-seasonal p+q search space. |
| `non_seasonal_order` | (INT64,INT64,INT64) | No | — | p,q in `0`–`5`; d in `0`–`2` | Manual (p,d,q); requires `auto_arima=FALSE`; single series only. |
| `data_frequency` | STRING | No | `'AUTO_FREQUENCY'` | AUTO_FREQUENCY, PER_MINUTE, HOURLY, DAILY, WEEKLY, MONTHLY, QUARTERLY, YEARLY | Frequency of the series. |
| `include_drift` | BOOL | No | `FALSE` | TRUE/FALSE | Linear drift term (only when d=1, and `auto_arima=FALSE`). |
| `holiday_region` | STRING or ARRAY\<STRING\> | No | none | GLOBAL, continental (NA/JAPAC/EMEA/LAC), or country codes | Model holiday effects. Only used for DAILY/WEEKLY series longer than a year. |
| `clean_spikes_and_dips` | BOOL | No | `TRUE` | TRUE/FALSE | Detect+interpolate spike/dip outliers. |
| `adjust_step_changes` | BOOL | No | `TRUE` | TRUE/FALSE | Detect+adjust abrupt step (level) changes. |
| `decompose_time_series` | BOOL | No | `TRUE` | TRUE/FALSE | Save components for `ML.EXPLAIN_FORECAST` / confidence intervals. |
| `time_series_length_fraction` | FLOAT64 | No | use all points | `(0,1)` | Fraction of (recent) points used for trend modeling (speedup). Not with `max_time_series_length`. |
| `min_time_series_length` | INT64 | No | `20` | `>=4` | Min trend points; requires `time_series_length_fraction`. |
| `max_time_series_length` | INT64 | No | none (try `30`) | `>=4` | Cap trend points; not with the fraction/min options. |
| `trend_smoothing_window_size` | INT64 | No | none | positive INT64 | Centered moving-average smoothing of trend (display only; doesn't change forecast). |
| `forecast_limit_lower_bound` | FLOAT64 | No | none | FLOAT64 | Hard lower bound on forecast values (e.g. `0` for non-negative demand). |
| `forecast_limit_upper_bound` | FLOAT64 | No | none | FLOAT64 | Hard upper bound on forecast values. |
| `seasonalities` | ARRAY\<STRING\> | No | auto | seasonality names | Override auto-detected seasonal patterns. |
| `hierarchical_time_series_cols` | ARRAY\<STRING\> | No | — | id col subset | Dimensions to roll up + reconcile (bottom-up hierarchical forecasts). |
| `kms_key_name` | STRING | No | — | KMS key | CMEK for the model. |

HP-tuning note: ARIMA_PLUS does **not** use the `num_trials` HP-tuning framework; `auto_arima` is its built-in hyperparameter search over (p,d,q). `auto_arima_max_order` / `auto_arima_min_order` control the search space.

**Supported lifecycle functions:**
`ML.FORECAST` (forecast + intervals), `ML.EXPLAIN_FORECAST` (forecast + decomposition; needs `decompose_time_series=TRUE`; **verified incompatible with `forecast_limit_lower_bound`/`forecast_limit_upper_bound`** — see GOTCHA below), `ML.EVALUATE` (forecast accuracy metrics, optional eval data), `ML.ARIMA_EVALUATE` (per-series model selection diagnostics), `ML.ARIMA_COEFFICIENTS` (AR/MA coefficients + drift), `ML.DETECT_ANOMALIES` (anomaly probability per point), `ML.FEATURE_INFO`, `ML.TRAINING_INFO`, `ML.HOLIDAY_INFO` (modeled holidays when `holiday_region` set). Not applicable: `ML.PREDICT`, `ML.GLOBAL_EXPLAIN`, `ML.WEIGHTS`, `ML.CONFUSION_MATRIX`, `ML.ROC_CURVE`, `ML.CENTROIDS`.

**GOTCHA (verified): `forecast_limit_lower_bound`/`forecast_limit_upper_bound` are incompatible with `ML.EXPLAIN_FORECAST`.** A model trained with either bound set fails `ML.EXPLAIN_FORECAST` with `"This model was trained with either 'forecast_limit_lower_bound' or 'forecast_limit_upper_bound' being specified. In this case, EXPLAIN_FORECAST is not supported."` `ML.FORECAST` and every other lifecycle function are unaffected — only `ML.EXPLAIN_FORECAST` is blocked. Not documented in the official options reference. If a notebook/pipeline needs both a forecast floor/ceiling and decomposition, they require two separate models.

**`hierarchical_time_series_cols` — verified mechanics.** Given an ordered list of grouping columns (e.g. `['neighborhood', 'station']`), `CREATE MODEL` trains the base-level series as usual, then `ML.FORECAST`/`ML.EVALUATE` return one row per hierarchy level: base-level rows (every id column set), each intermediate rollup level (finer id columns `NULL`), and one overall-total row (all id columns `NULL`). **Verified directly (exact match to the penny, every forecast day): reconciliation is bottom-up only** — the rolled-up value at any level is the plain sum of its children's forecasts; the base-level forecasts themselves are never adjusted to make higher levels more accurate. There is no built-in top-down option (disaggregating a higher-level forecast down through the hierarchy) — that requires a custom implementation; see `workflows/hierarchical_forecasting/` for a from-scratch top-down (forecast-proportions) approach compared against this built-in bottom-up one.

**ML.EVALUATE output metrics (this type):** `mean_absolute_error`, `mean_squared_error`, `root_mean_squared_error`, `mean_absolute_percentage_error`, `symmetric_mean_absolute_percentage_error`, and **`mean_absolute_scaled_error`** (verified present in a real call with explicit eval data + `perform_aggregation=TRUE` — not previously listed here). Metric granularity depends on inputs: with eval data and `perform_aggregation = TRUE` (default), metrics are per `time_series_id_col`; with `FALSE`, per timestamp. Without eval data, ARIMA-fit metrics (e.g. AIC, variance, log_likelihood) are returned per series instead — same shape as `ML.ARIMA_EVALUATE`, confirmed identical.

**ML.ARIMA_EVALUATE output columns:** `non_seasonal_p`, `non_seasonal_d`, `non_seasonal_q`, `has_drift`, `log_likelihood`, `AIC`, `variance`, `seasonal_periods` (e.g. `[WEEKLY, YEARLY]` or `[NO_SEASONALITY]`), `has_holiday_effect`, `has_spikes_and_dips`, `has_step_changes`, `error_message` (+ the id column). `show_all_candidate_models` (BOOL, default FALSE) returns every candidate instead of only the selected model.

**ML.FORECAST output columns:** id col, `forecast_timestamp`, `forecast_value`, `standard_error`, `confidence_level`, `prediction_interval_lower_bound`, `prediction_interval_upper_bound`, `confidence_interval_lower_bound`, `confidence_interval_upper_bound`. Args: `STRUCT(<n> AS horizon, <p> AS confidence_level)` — default `horizon` is 3, so set it to the trained horizon.

**ML.EXPLAIN_FORECAST adds:** `time_series_type` (`history`/`forecast`), `time_series_data`, `time_series_adjusted_data`, plus decomposition columns `trend`, `seasonal_period_{weekly,daily,monthly,quarterly,yearly}`, `holiday_effect` (and per-holiday columns like `holiday_effect_US_Thanksgiving`), `spikes_and_dips`, `step_changes`.

**Preprocessing support:** Automatic (the entire ARIMA_PLUS pipeline). `TRANSFORM` is supported but **not** when doing custom holiday modeling.

**Hyperparameter tuning:** N/A in the `num_trials` sense. Built-in auto.ARIMA search; tune via `auto_arima_max_order`/`auto_arima_min_order`. `non_seasonal_order` disables the search for a single series.

**Explainability / weights:** No `ML.WEIGHTS`/`ML.GLOBAL_EXPLAIN`/`ML.FEATURE_IMPORTANCE`. Explainability is via `ML.EXPLAIN_FORECAST` (time series decomposition) and `ML.ARIMA_COEFFICIENTS` (`ar_coefficients`, `ma_coefficients`, `intercept_or_drift`).

**Custom holiday modeling (verified, exact syntax):** `holiday_region` only covers built-in regional holidays. To model an event that matters for a specific series but isn't a public holiday, `CREATE MODEL`'s `AS` clause takes a special two-block form — **no `WITH` keyword**, and `training_data`/`custom_holiday` are required block names (not ordinary CTEs you can rename):
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
OPTIONS(model_type = 'ARIMA_PLUS', holiday_region = 'US', time_series_timestamp_col = 'date', time_series_data_col = 'value', horizon = 7)
AS (
  training_data AS (
    SELECT date, value FROM `PROJECT_ID.DATASET.SOURCE_TABLE`
  ),
  custom_holiday AS (
    SELECT 'US' AS region, 'MyEvent' AS holiday_name, primary_date, 1 AS preholiday_days, 1 AS postholiday_days
    FROM UNNEST([DATE('2016-11-06'), DATE('2017-11-05')]) AS primary_date
  )
);
```
`custom_holiday` columns: `region` (existing region code to supplement, or an arbitrary custom region name), `holiday_name` (must be a valid column-name string — no spaces, since it becomes `holiday_effect_<holiday_name>` in `ML.EXPLAIN_FORECAST`), `primary_date`, `preholiday_days`/`postholiday_days` (window size, ≥1). Verified: `ML.HOLIDAY_INFO` lists the custom holiday alongside built-ins, and `ML.EXPLAIN_FORECAST` gains a `holiday_effect_<holiday_name>` column. Can combine with `time_series_id_col` for multi-series. Max 50,000 rows in the `custom_holiday` query.

**Manual ARIMA order (verified):** `auto_arima = FALSE` with `non_seasonal_order = STRUCT(<p> AS p, <d> AS d, <q> AS q)` pins an exact order instead of searching — confirmed `ML.ARIMA_EVALUATE` reports back exactly the specified `(p,d,q)`. Single-series only (fails with `time_series_id_col`).

**Best practices:**
- ARIMA+ is univariate and ignores a validation split — fold any `VALIDATE` rows into the training data. [`models/arima_plus/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/arima_plus) uses a plain two-way TRAIN/TEST split for exactly this reason.
- Set `horizon` at training to cover test + future; remember `ML.FORECAST`/`ML.EXPLAIN_FORECAST` default `horizon` is 3.
- For 10k+ series, first time a 1k-series query to estimate cost/runtime; lower `auto_arima_max_order` to cut runtime (1 vs 2 cuts runtime >50%); use `time_series_length_fraction`/`max_time_series_length` to trim trend-modeling points; wrap in multi-statement queries.
- Cost scales with the number of candidate models (`auto_arima_max_order`/`min_order`) since input bytes are multiplied per candidate.
- Use `forecast_limit_lower_bound = 0` for non-negative demand — but only on a model where `ML.EXPLAIN_FORECAST` isn't needed (see the `ML.EXPLAIN_FORECAST` incompatibility GOTCHA above); `ML.FORECAST` still works fine with a bound set.

**Limitations:**
- Min series length 3 time points. Max length 500,000 points when `decompose_time_series=TRUE`, 1,000,000 when FALSE (per series). Max series simultaneously: 100,000,000. Max forecast points: 10,000.
- Holiday effect modeling only for DAILY/WEEKLY series longer than ~1 year; effective for ~5 years. Custom holidays only for `DAILY`/`AUTO_FREQUENCY`(daily) and not with `TRANSFORM`.
- Will **not** aggregate to a coarser granularity: requesting `data_frequency='WEEKLY'` on daily data errors `400 Invalid time series: All input time intervals must be no less than the interval unit specified by data_frequency (WEEKLY)`. Requesting a *finer* granularity (e.g. `HOURLY` on daily data) is allowed and interpolates the gaps.
- Missing/absent time points (null values or absent rows) are linearly interpolated between observed values based on the detected/declared frequency. **Verified: this has no special-case handling for very long gaps** — a real ~6-month gap (confirmed in `bigquery-public-data.new_york_citibike.citibike_trips`, October 2016 – March 2017) is linearly interpolated across its *entire* span with no different treatment than a 1-2 day gap (confirmed: a station's value declined by a constant per-day amount for all ~183 missing days, in `ML.DETECT_ANOMALIES`'s and `ML.EXPLAIN_FORECAST`'s output `time_series_data`) — a straight 6-month line necessarily discards all the weekly/seasonal structure that would have occurred in between. Treat any value inside a long gap as a crude placeholder, not a real observation.
- Invalid series (e.g. single point) are silently skipped from forecasts; retrieve their `error_message` via `ML.ARIMA_EVALUATE`.

**Locations:** Available in BigQuery ML non-remote-model locations (regions and multi-regions). See "Locations for non-remote models."

**BigFrames API:** [`bigframes.ml.forecasting.ARIMAPlus`](https://cloud.google.com/python/docs/reference/bigframes/latest/bigframes.ml.forecasting.ARIMAPlus) — `model = ARIMAPlus(horizon=..., auto_arima=True, data_frequency="daily", holiday_region=...)`, `model.fit(X_timestamp_df, y_value_df)`, then `model.predict(horizon=..., confidence_level=0.95)` (= `ML.FORECAST`), `model.predict_explain(...)` (= `ML.EXPLAIN_FORECAST`), `model.coef_` (= `ML.ARIMA_COEFFICIENTS`), `model.register(...)`.

**Repo example (tested):**
- `bigquery-ml/functions/time_series/` — the model-free `ML.TREND`, `ML.SEASONALITY`, and `ML.DETECT_CHANGE_POINTS` on the same Citi Bike series, for the questions that need no `CREATE MODEL` at all.
- The interpolation and granularity behavior — missing/absent points linearly interpolated, `WEEKLY` requested on daily data rejected, `HOURLY` on daily interpolated — is stated in *Limitations* above and verified in `models/arima_plus/`; there is no separate notebook for it.
- This project's own `models/arima_plus/` — from-scratch build on 5 real `bigquery-public-data.new_york_citibike.citibike_trips` stations (daily trip counts), single-series then multi-series via `time_series_id_col`; folds the granularity/missing-data gotchas above into the main notebook (verified a real gap day's linearly-interpolated value exactly: `(141+363)/2=252`) rather than keeping them in a separate notes file; adds a dedicated step verifying the custom-holiday syntax, manual `non_seasonal_order`, `forecast_limit_lower_bound` (as small standalone single-station models, kept separate from the main model specifically because of the `ML.EXPLAIN_FORECAST` incompatibility above — discovered when the main model was first built with the bound set and `ML.EXPLAIN_FORECAST` broke), and `hierarchical_time_series_cols` (a separate 6-station table grouped into 2 real Manhattan neighborhoods, since the main 5-station table has no real hierarchy) — verified bottom-up reconciliation exact to the penny at every level.
- `bigquery-ml/workflows/hierarchical_forecasting/` — hierarchical forecasting on `bigquery-public-data.iowa_liquor_sales.sales` (real State/County/City/Store hierarchy): built-in bottom-up reconciliation via `hierarchical_time_series_cols`, compared head-to-head at every hierarchy level against a from-scratch top-down disaggregation (forecast proportions) that BigQuery ML has no built-in option for. Uses weekly granularity — real per-store *daily* coverage is only ~15-30%, so daily would force heavy interpolation. Modernizes and replaces the retired `Applied ML/Forecasting/BigQuery ML For Hierarchical Forecasting.ipynb`, deleted 2026-07-21 after the rebuild was verified feature-for-feature.


---
