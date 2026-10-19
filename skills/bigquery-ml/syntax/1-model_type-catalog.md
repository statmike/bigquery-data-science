# 1. `model_type` catalog

> **Source:** [`bigquery-ml/reference/comparison-tables.md#1-model_type-catalog`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/comparison-tables.md#1-model_type-catalog)

| model_type | Category | Lifecycle entry | Connection? | Status |
|-----------|----------|-----------------|-------------|--------|
| `LINEAR_REG` | Supervised (regression) | `ML.PREDICT` | No | GA |
| `LOGISTIC_REG` | Supervised (classification) | `ML.PREDICT` | No | GA |
| `BOOSTED_TREE_CLASSIFIER` / `_REGRESSOR` | Supervised (XGBoost) | `ML.PREDICT` | No | GA |
| `RANDOM_FOREST_CLASSIFIER` / `_REGRESSOR` | Supervised (XGBoost) | `ML.PREDICT` | No | GA |
| `DNN_CLASSIFIER` / `_REGRESSOR` | Supervised (neural net) | `ML.PREDICT` | No | GA |
| `DNN_LINEAR_COMBINED_CLASSIFIER` / `_REGRESSOR` | Supervised (wide-and-deep) | `ML.PREDICT` | No | GA |
| `AUTOML_CLASSIFIER` / `_REGRESSOR` | Supervised (AutoML Tables) | `ML.PREDICT` | No* | GA |
| `KMEANS` | Unsupervised (clustering) | `ML.PREDICT` / `ML.CENTROIDS` | No | GA |
| `PCA` | Unsupervised (dim. reduction) | `ML.PREDICT` / `ML.PRINCIPAL_COMPONENTS` | No | GA |
| `AUTOENCODER` | Unsupervised | `ML.PREDICT` / `ML.RECONSTRUCTION_LOSS` | No | GA |
| `MATRIX_FACTORIZATION` | Recommendation | `ML.RECOMMEND` | No** | GA |
| `ARIMA_PLUS` | Time series (univariate) | `ML.FORECAST` | No | GA |
| `ARIMA_PLUS_XREG` | Time series (+ regressors) | `ML.FORECAST` | No | GA |
| `CONTRIBUTION_ANALYSIS` | Insight / key drivers | `ML.GET_INSIGHTS` | No | GA |
| `TENSORFLOW` / `TENSORFLOW_LITE` / `ONNX` / `XGBOOST` | Imported (from GCS) | `ML.PREDICT` | No*** | GA |
| Remote model (custom endpoint) | Remote (Vertex AI endpoint) | `ML.PREDICT` | **Yes** | GA |
| `TRANSFORM_ONLY` | Preprocessing-only | `ML.TRANSFORM` | No | GA |
| TimesFM (built-in) → `AI.FORECAST` | Time series (foundation) | `AI.FORECAST` | No | GA — see [bigquery-ai](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md) |

\* AutoML trains via an `ML_EXTERNAL` Vertex AI job but needs no `CREATE CONNECTION` object. \*\* Matrix factorization needs reservation/Editions (capacity) slots, not on-demand pricing — but no connection. \*\*\* The imported model itself needs no connection; the **object table** it is served over does (its service account needs `roles/storage.objectViewer` on the bucket), and the `ML.DECODE_IMAGE` family that prepares object-table images needs a **reservation** — two separate requirements, verified live in [`functions/image/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/image).

**Reservation (Editions) required, not just recommended:** `MATRIX_FACTORIZATION` and the four image-preprocessing functions (`ML.DECODE_IMAGE`, `ML.RESIZE_IMAGE`, `ML.CONVERT_COLOR_SPACE`, `ML.CONVERT_IMAGE_TYPE`) are the only things in this project that fail outright under on-demand pricing. Everything else in these tables runs on-demand. Neither requirement needs a *commitment* — a small `ENTERPRISE` autoscale reservation with 0 baseline slots is enough, and both [`models/matrix_factorization/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/matrix_factorization) and [`functions/image/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/image) create one in Setup and delete it in Cleanup.
