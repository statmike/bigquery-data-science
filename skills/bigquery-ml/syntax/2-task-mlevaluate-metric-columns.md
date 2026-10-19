# 2. Task → `ML.EVALUATE` metric columns

> **Source:** [`bigquery-ml/reference/comparison-tables.md#2-task--mlevaluate-metric-columns`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/comparison-tables.md#2-task--mlevaluate-metric-columns)

| Task / model family | `ML.EVALUATE` metric columns |
|---|---|
| Regression (`LINEAR_REG`, tree/DNN/WnD regressors) | `mean_absolute_error`, `mean_squared_error`, `mean_squared_log_error`, `median_absolute_error`, `r2_score`, `explained_variance` |
| Classification (`LOGISTIC_REG`, tree/DNN/WnD/AutoML classifiers) | `precision`, `recall`, `accuracy`, `f1_score`, `log_loss`, `roc_auc` |
| K-means | `davies_bouldin_index`, `mean_squared_distance` |
| Matrix factorization — explicit | `mean_absolute_error`, `mean_squared_error`, `mean_squared_log_error`, `r2_score`, `explained_variance` |
| Matrix factorization — implicit | `mean_average_precision`, `mean_squared_error`, `normalized_discounted_cumulative_gain`, `average_rank` |
| PCA | `total_explained_variance_ratio` |
| Autoencoder | `mean_absolute_error`, `mean_squared_error`, `mean_squared_log_error` |
| Time series (ARIMA_PLUS, with test data) | `mean_absolute_error`, `mean_squared_error`, `root_mean_squared_error`, `mean_absolute_percentage_error`, `symmetric_mean_absolute_percentage_error`, `mean_absolute_scaled_error` |

A `trial_id` column is prepended for hyperparameter-tuned models.

**Which evaluator?**

| You have | Function | Returns |
|---|---|---|
| A trained model and an eval set | [`ML.EVALUATE`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlevaluate) | The table above, including `log_loss` and `roc_auc` |
| Two columns: actual and predicted (no model) | [`ML.METRICS`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlmetrics) | The regression six, or `precision`/`recall`/`accuracy`/`f1_score`. No `log_loss`, no `roc_auc` |
| Raw data and no model at all | [`AI.EVALUATE`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md) | Same names as `ML.METRICS`, but trains TabFM/TimesFM internally and is not reproducible run to run |

> For `ML.METRICS` and `AI.EVALUATE` alike, `precision`/`recall`/`f1_score` on a **`BOOL`** label describe the positive (`TRUE`) class alone, while the **`STRING`** rendering of the same values is macro-averaged across classes. `accuracy` is identical either way. Measured on one table: precision `0.5238` versus `0.7497`.
