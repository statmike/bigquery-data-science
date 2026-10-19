# Model-free time series decomposition: `ML.TREND`, `ML.SEASONALITY`, `ML.DETECT_CHANGE_POINTS`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#model-free-time-series-decomposition-mltrend-mlseasonality-mldetect_change_points`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#model-free-time-series-decomposition-mltrend-mlseasonality-mldetect_change_points)

- **Description:** Three **table-valued functions** that decompose a time series without training a model. `ML.TREND` returns the trend component, `ML.SEASONALITY` returns per-period seasonal components, and `ML.DETECT_CHANGE_POINTS` returns sustained structural shifts as time windows. No `CREATE MODEL`, no model object, no connection — the first argument is a relation (a `TABLE` reference or a parenthesized subquery) and the column names are passed as `STRING` named arguments.
- **Use cases:**
  - Get a series' underlying direction or seasonal shape without committing to a model artifact you then have to manage, version, and retrain.
  - Extract seasonal components that are **bit-identical** to an `ARIMA_PLUS` model's (measured below) at a fraction of the setup.
  - Detect sustained level shifts — the gap between row-level anomaly detection and dataset-level drift monitoring, which nothing else in this project covers.
  - Exploratory decomposition across many series at once via `id_cols`, before deciding whether a model is warranted at all.
- **documentation:** [ML.TREND](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-trend) · [ML.SEASONALITY](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-seasonality) · [ML.DETECT_CHANGE_POINTS](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-detect-change-points)
- **Type:** Table-valued (TVF).
- **Applies to models:** None — model-free. `ML.TREND`/`ML.SEASONALITY` run the `ARIMA_PLUS` decomposition without materializing a model.
- **Status:** **Preview** as of 2026-08-20. **Connection required:** No.

**Syntax** (as the server enumerates it when handed a bad argument):
```sql
ML.TREND(TABLE, timestamp_col => STRING, data_col => STRING,
         [id_cols => ARRAY<STRING>], [horizon => INT64],
         [smoothing_window_size => INT64], [adjust_step_changes => BOOL])

ML.SEASONALITY(TABLE, timestamp_col => STRING, data_col => STRING,
               [id_cols => ARRAY<STRING>], [SEASONALITIES => ARRAY<STRING>],
               [horizon => INT64])

ML.DETECT_CHANGE_POINTS(TABLE, timestamp_col => STRING, data_col => STRING,
                        [id_cols => ARRAY<STRING>])
```

**Inputs:**

| Parameter | Type | Required | Default | Applies to | Description |
|-----------|------|----------|---------|-----------|-------------|
| (first argument) | relation | Yes | — | all three | A `TABLE` reference or parenthesized subquery. Not a string. |
| `timestamp_col` | `STRING` | Yes | — | all three | Name of the time column. |
| `data_col` | `STRING` | Yes | — | all three | Name of the value column. |
| `id_cols` | `ARRAY<STRING>` | No | — | all three | Decompose each series independently in one pass, like `ARIMA_PLUS`'s `time_series_id_col`. Echoed in the output. |
| `horizon` | `INT64` | No | — | `TREND`, `SEASONALITY` | **Extends** the series into the future; not a row limit. See limitations. |
| `smoothing_window_size` | `INT64` | No | unspecified | `TREND` | Widens the trend smoothing window. |
| `adjust_step_changes` | `BOOL` | No | **`FALSE`** | `TREND` | Adjusts for step changes. **Differs from the `ARIMA_PLUS` default** — see limitations. |
| `SEASONALITIES` | `ARRAY<STRING>` | No | auto | `SEASONALITY` | Restricts fitted periods. Accepted: `DAILY`, `WEEKLY`, `MONTHLY`, `QUARTERLY`, `YEARLY` (values are case-insensitive). |

Argument **names** are case-insensitive and order-independent among named arguments.

**Outputs:**

| Function | Columns |
|---|---|
| `ML.TREND` | `<timestamp_col>`, `time_series_type`, `<data_col>`, `trend`, `status` |
| `ML.SEASONALITY` | `<timestamp_col>`, `time_series_type`, `<data_col>`, `yearly`, `quarterly`, `monthly`, `weekly`, `daily`, `status` |
| `ML.DETECT_CHANGE_POINTS` | `begin_timestamp`, `end_timestamp`, `metrics` `STRUCT<avg, count, max, min, stddev>`, `status` |

The timestamp and data columns keep their **original names** — output is not renamed to a generic `time_series_timestamp`/`time_series_data` the way `ML.FORECAST`'s is. The data column comes back `FLOAT64` regardless of input type, because the returned series is gap-filled/preprocessed rather than echoed.

**Measured against `ARIMA_PLUS` on an identical series** (Citi Bike daily trips, Pershing Square North, n = 1,341 history rows; `ML.TREND` called with `adjust_step_changes => TRUE` to match the model default):

| Component | vs. `ML.EXPLAIN_FORECAST` | Correlation |
|---|---|---|
| `weekly` vs `seasonal_period_weekly` | mean abs diff **0.0** | **1.0** |
| `yearly` vs `seasonal_period_yearly` | mean abs diff **0.0** | **1.0** |
| `trend` vs `trend` | mean abs diff 8.337 (median 5.755, p95 25.121, max 58.555) | 0.9955 |

`ML.SEASONALITY` reproduces the model's seasonal decomposition exactly. `ML.TREND` does not quite. Two option differences remain unseparated by that comparison, so no single cause is claimed: the trained model also reports `"cleanSpikesAndDips": true` (`ML.TREND` exposes no equivalent option) and `"trendSmoothingWindowSize": -1` (auto), while `ML.TREND`'s `smoothing_window_size` default is unspecified.

**Best practices:**
- Use `ML.SEASONALITY` as a drop-in for an `ARIMA_PLUS` model's seasonal components — same numbers, no model to manage. Treat `ML.TREND` as very close but not a substitute where a specific model's trend must be reproduced to the digit.
- Detect which periods were actually fitted with a `COUNTIF(<period> IS NULL)` pass. The schema is fixed and tells you nothing.
- Test `status` with `status = ''` or `LENGTH(status) = 0`.
- Range-join on `date BETWEEN begin_timestamp AND end_timestamp` to attribute rows to a change window.
- **Profile a series for data gaps before acting on any change point** — see limitations. On the tested data six of seven change points were gap edges, so the gap profile is not an optional refinement.
- Keep the valid `SEASONALITIES` list to hand rather than relying on the error message to supply it.
- Reach for these before `CREATE MODEL` when the question is descriptive ("what does this series look like?") rather than predictive.

**Limitations:**
- **`adjust_step_changes` defaults to `FALSE` here but `TRUE` in `ARIMA_PLUS`.** A naive `ML.TREND` call does not reproduce a model's trend. Verified by differencing all three variants: default vs `FALSE` summed to exactly `0.0`; default vs `TRUE` summed to 91,344.17 over 1,341 rows.
- **`horizon` extends the series, it does not window it.** Supplying it adds rows with `time_series_type = 'forecast'`. On those rows the **data column carries the forecast value, not `NULL`** — only `time_series_type` distinguishes an actual from a prediction, so an unfiltered aggregate silently mixes the two. `ML.DETECT_CHANGE_POINTS` has no `horizon`.
- **`ML.SEASONALITY`'s period columns are a fixed schema, not a result.** All five are always present; unfitted periods are `NULL` on every row. On a daily series only `weekly` and `yearly` populated — `daily`, `monthly` and `quarterly` were `NULL` across all 1,341 rows.
- **`ML.DETECT_CHANGE_POINTS` returns windows, not per-row flags.** No `is_change_point` boolean, no full-partition output. Two windows on a 1,341-day series.
- **Its `metrics` struct describes the gap-filled series, not your rows**, so it will not tie out against a `GROUP BY` over the same range. Measured on one window: raw `GROUP BY` gave n 3, avg 552.33, min 194; the function reported n 7, avg 346.98, min 192.33879781420765 — fractional, though the input is an integer `COUNT(*)`.
- **All three gap-fill to a regular frequency.** Each series is filled to *its own* span, not a common calendar: five Citi Bike stations with 1,153–1,582 raw rows returned 1,341–1,768 rows. Row counts out will exceed row counts in on any gapped series. This is the third of three different behaviors over the same gap: `ARIMA_PLUS` interpolates a real value across the entire span (measured on the Citi Bike outage: `194.0` -> a constant `~-0.415`/day decline -> `118.0`, day by day, for all ~183 missing days), `ARIMA_PLUS_XREG` returns `NULL` across it, and these TVFs gap-fill. Same data, same gap, three answers.
- **On a gapped series, the gap-filling manufactures the structural break `ML.DETECT_CHANGE_POINTS` then reports — this is the most consequential behavior here.** The Citi Bike table has a dataset-wide ingestion outage (all five stations resume 2017-04-01; four stop 2016-09-30, one 2016-08-22). Labelling each detected window by whether it contains the edge of a ≥3-day gap, **six of the seven windows across the five stations are gap edges**. Only one is not: `West St & Chambers St`, 2016-04-27 → 2016-05-07, all 11 days present, with a genuine level shift across it (averaging raw daily counts: 248.1 trips/day over the 30 days before the window, 210.9 inside it, 373.4 over the 30 days after). The function is not wrong — after interpolation the series really does step down into a flat stretch and back out — but the shift is an artifact of missing data, not of the process being measured. **The practical workflow is two queries: profile the gaps, then keep the change points that do not land on one.** Without that filter, six of seven findings here would be an ingestion story reported as a business story.
- `status` is the empty string on success, never `NULL`; `status IS NULL` matches nothing.
- Bad `SEASONALITIES` values enumerate the valid set for `HOURLY`, `NO_SEASONALITY` and `AUTO`, but return a bare `Invalid seasonality value 'X' in SEASONALITIES.` for anything else (`MINUTELY`, `PER_MINUTE`, `PER_HOUR`, `AUTO_FREQUENCY`, `ANNUAL`, `''`, ordinary typos). Recorded as observed message behavior, not an inferred parser rule.
- **Not a substitute for anomaly detection.** On the same series, `ML.DETECT_ANOMALIES` (`anomaly_prob_threshold` 0.95) flagged 79 rows and `ML.DETECT_CHANGE_POINTS` found 2 windows, with **zero overlap**. Orthogonal detectors, not two sensitivities of one. Note the separation is sharper here than it would generally be, for the reason above: those two windows bracket an interpolated stretch that is smooth by construction and so holds nothing for a row-level detector to flag. The zero shows the two functions answer different questions; it does not measure how far apart their answers usually fall.

**Related — three functions, three questions:**

| Question | Function | Granularity |
|---|---|---|
| Is *this row* an outlier? | [`ML.DETECT_ANOMALIES`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mldetect_anomalies) | Row |
| Did the series *shift* here? | `ML.DETECT_CHANGE_POINTS` | Window |
| Has the *whole dataset* moved? | [`ML.VALIDATE_DATA_DRIFT`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-management-monitoring.md#mlvalidate_data_drift) | Dataset |

For zero-shot (TimesFM) forecasting and anomaly detection with no model *and* no fitted decomposition, see [`AI.FORECAST` / `AI.DETECT_ANOMALIES`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md) in the sibling project.

**BigFrames API:** No equivalent. `bigframes.ml.forecasting.ARIMAPlus` covers the *model* path only; reach these TVFs via `bigframes.pandas.read_gbq` over the SQL.

**Repo example (tested):** `bigquery-ml/functions/time_series/time_series.ipynb` and `time_series.sql` — all three functions on the Citi Bike series shared with `models/arima_plus/`, including the `ARIMA_PLUS` head-to-head, the change-points-vs-anomalies overlap test, and the gap-fill demonstration.

---
