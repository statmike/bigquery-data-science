# `ARIMA_PLUS_XREG`  (multivariate time series with external regressors)

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#arima_plus_xreg--multivariate-time-series-with-external-regressors`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#arima_plus_xreg--multivariate-time-series-with-external-regressors)

- **Description:** Multivariate time-series forecasting model = an `ARIMA_PLUS` model plus *linear external regressors* (side features / covariates). Internally it fits a linear regression on the supplied covariates and models the regression residuals with the full `ARIMA_PLUS` pipeline (auto-ARIMA order selection, holiday effects, spike/dip cleaning, step-change adjustment, seasonal & trend decomposition). Conceptually "ARIMAX": ARIMA's `p`/`d`/`q` plus `b` linear-regressor weights.
- **When to use:**
  - You have a target series **and** time-varying covariates (e.g. promotions, weather, capacity) that improve forecast accuracy.
  - Covariate values **are known/available for the forecast horizon** (required at forecast time — see Limitations).
  - You want ARIMA_PLUS automation (holidays, seasonality, anomaly handling) but with explanatory regressors.
  - You want per-regressor attributions in the forecast (`ML.EXPLAIN_FORECAST`).
- **Category:** time-series.
- **Connection required:** No.
- **Status:** GA. Multiple-series support via `time_series_id_col` and `ML.DETECT_ANOMALIES` support were both added after the original 2023 Preview; both are exercised live in [`models/arima_plus_xreg/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/arima_plus_xreg) (Example 2 trains all five stations as one multi-series model; Example 10 runs `ML.DETECT_ANOMALIES` against it).
- **documentation:** [CREATE MODEL for ARIMA_PLUS_XREG](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-multivariate-time-series) · journey/tutorials: [single series tutorial](https://cloud.google.com/bigquery/docs/arima-plus-xreg-single-time-series-forecasting-tutorial), [multiple series tutorial](https://cloud.google.com/bigquery/docs/arima-plus-xreg-multiple-time-series-forecasting-tutorial), [E2E user journey](https://cloud.google.com/bigquery/docs/e2e-journey). Related univariate model: [`ARIMA_PLUS`](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-time-series).

> Built-in foundation forecasting (TimesFM via `AI.FORECAST`) is owned by `../bigquery-ai/` — see [AI.FORECAST / AI.DETECT_ANOMALIES there](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md). `ARIMA_PLUS_XREG` is the in-scope BQML *trained-model* forecaster; since TimesFM 3.0 (Preview) `AI.FORECAST` also takes past and future covariates, so choose `ARIMA_PLUS_XREG` for the trained model's explainability (`ML.EXPLAIN_FORECAST` per-regressor attribution, `ML.ARIMA_COEFFICIENTS` weights), holidays and GA status rather than for covariate support alone.

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
OPTIONS(
  model_type                = 'ARIMA_PLUS_XREG',
  time_series_timestamp_col = 'starttime',
  time_series_data_col      = 'num_trips',
  time_series_id_col        = 'start_station_name',   -- optional: one OR an array of cols -> many series
  data_frequency            = 'DAILY',
  auto_arima_max_order      = 5,
  holiday_region            = ['GLOBAL', 'US'],
  horizon                   = 28
) AS
SELECT starttime, num_trips, avg_tripduration, pct_subscriber, ratio_gender, capacity
FROM `PROJECT_ID.DATASET.forecasting_data_prepped`;
-- every selected column that is NOT the timestamp / data / id col is treated as an external regressor (covariate)
```
The covariates are defined implicitly by the `SELECT` list: any column other than the timestamp, data, and id column(s) becomes a linear external regressor.

**Options (model-specific):**

| Option | Type | Required | Default | Range / Values | Description |
|--------|------|----------|---------|----------------|-------------|
| `model_type` | STRING | Yes | — | `'ARIMA_PLUS_XREG'` | Selects the multivariate ARIMA+ model. |
| `time_series_timestamp_col` | STRING | Yes | — | column name | Timestamp/date column defining the series order. |
| `time_series_data_col` | STRING | Yes | — | column name | Target (data) column to forecast. |
| `time_series_id_col` | STRING or ARRAY\<STRING\> | No | (single series) | one or more column names | Identifies distinct series; enables forecasting many series in one model. |
| `horizon` | INT64 | No | `1000` | \> 0 | Max number of future time points the model can forecast (also fit cost driver). |
| `auto_arima` | BOOL | No | `TRUE` | TRUE/FALSE | Auto-select non-seasonal `p,d,q`. |
| `auto_arima_max_order` | INT64 | No | `5` | typically 1–5 | Upper bound on `p+q` search; higher = slower, more candidates. |
| `auto_arima_min_order` | INT64 | No | `0` | ≥ 0 | Lower bound on order search. |
| `data_frequency` | STRING | No | `'AUTO_FREQUENCY'` | `AUTO_FREQUENCY`, `PER_MINUTE`, `HOURLY`, `DAILY`, `WEEKLY`, `MONTHLY`, `QUARTERLY`, `YEARLY` | Granularity of input rows. |
| `holiday_region` | STRING or ARRAY\<STRING\> | No | (none) | e.g. `'US'`, `['GLOBAL','US']` | Enables holiday-effect modeling for the given region(s). |
| `clean_spikes_and_dips` | BOOL | No | `TRUE` | TRUE/FALSE | Detect & clean outliers before fitting. |
| `adjust_step_changes` | BOOL | No | `TRUE` | TRUE/FALSE | Detect & adjust level/step changes. |
| `decompose_time_series` | BOOL | No | `TRUE` | TRUE/FALSE | Store decomposition (trend/seasonal/holiday) so `ML.EXPLAIN_FORECAST` returns components. |
| `seasonalities` | ARRAY\<STRING\> | No | auto | `NO_SEASONALITY`,`DAILY`,`WEEKLY`,`MONTHLY`,`QUARTERLY`,`YEARLY` | Override auto seasonality detection. |
| `time_series_length_fraction` | FLOAT64 | No | auto | (0,1] | Fraction of series used for trend modeling. |
| `min_time_series_length` | INT64 | No | auto | ≥ 0 | Min points required for trend modeling. |
| `max_time_series_length` | INT64 | No | auto | ≥ 0 | Cap on most-recent points used for trend modeling. |
| `trend_smoothing_window_size` | INT64 | No | auto | ≥ 0 | Trend smoothing window. |
| `kms_key_name` | STRING | No | (none) | KMS resource | CMEK for the model. |

**Supported lifecycle functions:** `ML.FORECAST`, `ML.EXPLAIN_FORECAST` (forecast + trend/seasonal/holiday components + **per-regressor attributions**), `ML.EVALUATE`, `ML.ARIMA_EVALUATE` (per-series ARIMA stats), `ML.ARIMA_COEFFICIENTS` (AR/MA coefficients **plus the external-regressor weights**), `ML.FEATURE_INFO`, `ML.TRAINING_INFO`, `ML.HOLIDAY_INFO`, `ML.DETECT_ANOMALIES` (anomaly detection; added post-2023). No `ML.PREDICT`, no `ML.WEIGHTS`/`ML.GLOBAL_EXPLAIN`/`ML.FEATURE_IMPORTANCE`.

**ML.EVALUATE output metrics (this type):** `mean_absolute_error`, `mean_squared_error`, `root_mean_squared_error`, `mean_absolute_percentage_error`, `symmetric_mean_absolute_percentage_error`. **Verified: unlike plain `ARIMA_PLUS`, this does NOT include `mean_absolute_scaled_error`** — confirmed by comparing the actual output columns of both types side by side on the same underlying data. With `time_series_id_col`, `ML.EVALUATE` evaluates each series independently. Behavior depends on inputs: if eval (test) data is supplied, forecast-accuracy metrics are returned; `perform_aggregation = TRUE` gives metrics per series, `FALSE` gives per-timestamp. (For ARIMA model-fit stats — `AIC`, `log_likelihood`, `variance`, `p/d/q`, `seasonal_periods`, `has_holiday_effect`, `has_spikes_and_dips`, `has_step_changes` — use `ML.ARIMA_EVALUATE`.)

**GOTCHA (verified): `ML.FORECAST`'s 2-argument form (`MODEL`, `STRUCT`) fails immediately** with `"Model type ARIMA_PLUS_XREG requires three parameters in ML.FORECAST."` — the third argument (a table/query supplying covariate values for the forecast horizon) is mandatory, not merely recommended. `ML.EXPLAIN_FORECAST` has the same 3-argument requirement.

**GOTCHA (verified): `forecast_limit_lower_bound`/`forecast_limit_upper_bound` are not a supported option AT ALL for this model type** — `CREATE MODEL` rejects it outright at training time: `"Option(s) FORECAST_LIMIT_LOWER_BOUND are not supported for ARIMA_PLUS_XREG model training."` This is a **different** limitation from plain `ARIMA_PLUS`, where the option is accepted but breaks `ML.EXPLAIN_FORECAST` (see that entry) — do not assume the two model types share identical option compatibility.

**GOTCHA (verified): custom holiday modeling and manual `non_seasonal_order` both work identically to `ARIMA_PLUS`** (same two-block `AS (training_data AS (...), custom_holiday AS (...))` syntax; same `auto_arima = FALSE` + `non_seasonal_order = STRUCT(p,d,q)`) — see that entry for the full syntax.

**GOTCHA (verified): a covariate with a few NULL values (not an entire series) does not block training.** A partial-NULL covariate (e.g. a handful of days with an undefined ratio due to `0/0`) triggers a warning — `"The input data has NULL values in one or more columns: <col>. ... For NULLs in the time_series_data column, BQML replaces them with meaningful values using local linear interpolation."` — but `CREATE MODEL` still succeeds and produces a real (non-NULL) regression weight for that covariate. This is a different situation from the existing "all-NULL for some series" limitation below, which does block training and requires dropping the covariate.

**Preprocessing support:** automatic (ARIMA+ pipeline: missing-value handling, spike/dip cleaning, step-change adjustment, holiday & seasonal decomposition). Covariates are consumed directly from the `SELECT` list. TRANSFORM is **not** supported for this model type.

**Hyperparameter tuning:** Not supported (`num_trials`/HP tuning N/A for ARIMA_PLUS_XREG). Order selection is handled internally by `auto_arima`; tune `auto_arima_max_order` / `auto_arima_min_order` manually if needed.

**Explainability / weights:** `ML.GLOBAL_EXPLAIN` / `ML.FEATURE_IMPORTANCE` / `ML.WEIGHTS` do not apply. Explainability comes from (1) `ML.ARIMA_COEFFICIENTS` — returns AR/MA coefficients and the **regression `weight` per processed input** (incl. `__INTERCEPT__`); and (2) `ML.EXPLAIN_FORECAST` — returns trend, seasonal, holiday effects, spikes/dips, step changes, and `attribution_<regressor>` columns per timestamp. No `enable_global_explain` option.

**Best practices:**
- Provide covariate values for the **entire forecast horizon** — `ML.FORECAST`/`ML.EXPLAIN_FORECAST` require the side features as input (the target column is omitted in that input).
- Include validation data in training: ARIMA is fit on the historical series and does not consume a separate validation split — fold TRAIN+VALIDATE into the training `SELECT` (notebook does this).
- Set `horizon` at/above the largest forecast you'll request; `ML.FORECAST` default `horizon` is small (3) and must be passed via `STRUCT(... AS horizon)`.
- Drop covariates that are all-NULL for some series before training a multi-series model (notebook drops `capacity` for that reason).
- Use `ML.ARIMA_EVALUATE` (not the console Evaluation tab) to inspect all series — the console shows only the first 100.

**Limitations:**
- Covariates must be known at forecast time (no built-in handling of unknown future covariates).
- Invalid series (e.g. single-point) are silently skipped in multi-series fits; a warning is surfaced via `ML.ARIMA_EVALUATE.error_message`.
- No TRANSFORM, no HP tuning, no `ML.PREDICT`.
- Multi-series cost scales with series count and `horizon` (notebook: ~34 s single series; ~5 min for 12 series via `EXECUTE IMMEDIATE` loop).
- Regressors are **linear**; non-linear effects must be feature-engineered into covariates.
- **GOTCHA (verified): gap handling differs from plain `ARIMA_PLUS`.** Plain `ARIMA_PLUS` linearly interpolates a real numeric value across an entire missing-data gap, however long (see that entry's Limitations). `ARIMA_PLUS_XREG` does not — confirmed directly against a real ~6-month gap (`bigquery-public-data.new_york_citibike.citibike_trips`, October 2016 – March 2017): `ML.DETECT_ANOMALIES` returns `NULL` for the target/anomaly columns on every day inside the gap, rather than an interpolated value. Don't assume identical gap-handling behavior between the two model types just because they share most lifecycle functions and options. A third behavior exists on the same gap: the model-free TVFs (`ML.TREND`/`ML.SEASONALITY`/`ML.DETECT_CHANGE_POINTS`, see *Model-Free Time-Series Functions* below) gap-fill each series to its own span before computing, which is what makes `ML.DETECT_CHANGE_POINTS` report the gap's edges as change points. Establish which of the three surfaces produced a value before trusting anything inside a gap.

**Locations:** Available in BigQuery ML regions/multi-regions; no external connection needed. CMEK via `kms_key_name`.

**BigFrames API:** `bigframes.ml.forecasting.ARIMAPlus` covers univariate ARIMA_PLUS; external-regressor (XREG) multivariate forecasting is best driven via SQL `CREATE MODEL`. (No dedicated `ARIMAPlusXReg` class — treat as "use SQL.")

**Repo example (tested):** `bigquery-ml/models/arima_plus_xreg/` — from-scratch build on Citi Bike daily trips using native `time_series_id_col` from the start, on the same 5 stations and TEST window as `models/arima_plus/` so the two are directly comparable on forecast accuracy. Uses `holiday_region=['GLOBAL','US']` and 3 covariates (a `capacity` covariate was dropped — it needed a join and was NULL for some stations). Covers `ML.ARIMA_COEFFICIENTS` (regressor weights), `ML.FEATURE_INFO`, `ML.TRAINING_INFO`, `ML.EVALUATE`, `ML.ARIMA_EVALUATE`, `ML.HOLIDAY_INFO`, `ML.FORECAST` (covariates supplied for the horizon), `ML.EXPLAIN_FORECAST` (including the `attribution_*` columns), `ML.DETECT_ANOMALIES`, and custom SQL MAPE/MAE/pMAE/MSE/RMSE/pRMSE.

Several cross-model-type differences from plain `ARIMA_PLUS` were verified here: no `mean_absolute_scaled_error` in the metrics; `forecast_limit_lower_bound` is rejected outright rather than merely breaking `ML.EXPLAIN_FORECAST`; and `ML.FORECAST` / `ML.EXPLAIN_FORECAST` both strictly require the 3-argument covariate form. Note that multi-series XREG once required a workaround (one model per series via an `EXECUTE IMMEDIATE FOR..IN` loop or async client jobs) — `time_series_id_col` is GA for XREG now and a single model replaces it.


---
