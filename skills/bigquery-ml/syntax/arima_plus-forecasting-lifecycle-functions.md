# ARIMA_PLUS forecasting lifecycle functions

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#arima_plus-forecasting-lifecycle-functions`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#arima_plus-forecasting-lifecycle-functions)

These five table-valued functions consume a trained `ARIMA_PLUS` (univariate) or `ARIMA_PLUS_XREG`
(multivariate) model. The forecast and time-series decomposition are computed **at `CREATE MODEL`
time**; these functions retrieve the stored results and compute confidence/prediction intervals on
demand. They are **GA**, require **no connection**, and have no foundation-model dependency.

> For the foundation-model forecaster (`AI.FORECAST` / TimesFM, zero training, no `CREATE MODEL`),
> see [`../bigquery-ai/RESOURCES.md` → AI.FORECAST](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md). The
> entries below are the classic, statistical ARIMA_PLUS path that lives in bigquery-ml.

---
