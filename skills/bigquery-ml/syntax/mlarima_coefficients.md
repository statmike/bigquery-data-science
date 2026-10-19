# `ML.ARIMA_COEFFICIENTS`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlarima_coefficients`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlarima_coefficients)

- **Description:** Returns the fitted ARIMA coefficients per time series — the "weights" function for ARIMA_PLUS models.
- **Use cases:** Inspect AR/MA coefficient vectors and the intercept/drift; audit/export fitted model parameters.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-arima-coefficients
- **Type:** Table-valued (model-weights family). **Applies to models:** `ARIMA_PLUS`, `ARIMA_PLUS_XREG`. **Status:** GA.

**Syntax:**
```sql
SELECT *
FROM ML.ARIMA_COEFFICIENTS(MODEL `PROJECT_ID.DATASET.MODEL_NAME`);
```

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `\<time_series_id_col\>` | (varies) | Series id (when trained with `time_series_id_col`). |
| `ar_coefficients` | ARRAY\<FLOAT64\> | Autoregressive (AR) coefficients; length = `non_seasonal_p`. Empty `[]` when p=0. |
| `ma_coefficients` | ARRAY\<FLOAT64\> | Moving-average (MA) coefficients; length = `non_seasonal_q`. Empty `[]` when q=0. |
| `intercept_or_drift` | FLOAT64 | Constant (intercept) or drift term of the model. |

**Best practices:** Join with `ML.ARIMA_EVALUATE` on the series id to pair `(p,d,q)` with the coefficient vectors.
**Limitations:** Output is the ARIMA-specific analog of `ML.WEIGHTS`; standard `ML.WEIGHTS` does not apply to ARIMA_PLUS.
**BigFrames API:** `bigframes.ml.forecasting.ARIMAPlus().coef_` (or `.summary()`).
**Repo example (tested):** `bigquery-ml/models/arima_plus/arima_plus.sql` (Example 8) — per-series `ar_coefficients` / `ma_coefficients` / `intercept_or_drift`, sitting directly after `ML.ARIMA_EVALUATE` (Example 3) so the `(p,d,q)` order and the coefficient vector lengths can be read against each other.

---
