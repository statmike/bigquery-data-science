# `ML.HOLIDAY_INFO`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlholiday_info`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlholiday_info)

- **Description:** Lists the holidays modeled by an ARIMA_PLUS model and the holiday effects it detected, expanded by date across the modeled range.
- **Use cases:** Audit which holidays/regions the model accounts for; align holiday windows with observed effects.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-holiday-info
- **Type:** Table-valued. **Applies to models:** `ARIMA_PLUS`, `ARIMA_PLUS_XREG` trained with `holiday_region`. **Status:** GA.

**Syntax:**
```sql
SELECT *
FROM ML.HOLIDAY_INFO(MODEL `PROJECT_ID.DATASET.MODEL_NAME`);
```

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `region` | STRING | Holiday region from `CREATE MODEL` `holiday_region` (e.g. `GLOBAL`, `US`). |
| `holiday_name` | STRING | Name of the holiday with a modeled/detected effect. |
| `primary_date` | DATE | Calendar date of that holiday occurrence. |
| `preholiday_days` | INT64 | Days before `primary_date` included in the holiday window. |
| `postholiday_days` | INT64 | Days after `primary_date` included in the holiday window. |

**Best practices:** Requires `holiday_region` (one or many, e.g. `['GLOBAL','US']`) at `CREATE MODEL`. Output spans many years/holidays — aggregate or filter by `region`/`holiday_name` for review.
**Limitations:** Empty if the model was trained without `holiday_region`. Returns the holiday calendar/windows, not the numeric effect (use `ML.EXPLAIN_FORECAST` `holiday_effect_*` columns for magnitudes).
**BigFrames API:** No direct equivalent.
**Repo example (tested):**
- `bigquery-ml/models/arima_plus/arima_plus.sql` (Example 9) — filtered to `region = 'US'` over a bounded `primary_date` range, which is the practical shape given how many rows the unfiltered output spans.
- Example 10 in the same file registers a **custom holiday** via the `holiday_region`/custom-holiday input and then reads it back with `WHERE holiday_name = 'NYCMarathon'` — the way to confirm a custom calendar entry was actually accepted by the model.

---

### Forecast `ML.EVALUATE` metrics (ARIMA_PLUS)
When `ML.EVALUATE` is called on an ARIMA_PLUS model **with** test data and `perform_aggregation=TRUE`,
it returns per-series: `mean_absolute_error`, `mean_squared_error`, `root_mean_squared_error`,
`mean_absolute_percentage_error`, `symmetric_mean_absolute_percentage_error`,
`mean_absolute_scaled_error`. With
`perform_aggregation=FALSE` it returns per-timestamp metrics; with no input data it returns the
in-training ARIMA metrics (see `ML.ARIMA_EVALUATE`). Anomaly detection on the same model uses
[`ML.DETECT_ANOMALIES`](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-detect-anomalies)
with `anomaly_prob_threshold` (repo example: same notebook, cell 57).


---
