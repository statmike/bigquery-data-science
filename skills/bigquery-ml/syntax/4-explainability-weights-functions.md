# 4. Explainability / weights functions

> **Source:** [`bigquery-ml/reference/comparison-tables.md#4-explainability--weights-functions`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/comparison-tables.md#4-explainability--weights-functions)

| Function | Scope | Applies to | Key output | Pre-req |
|---|---|---|---|---|
| `ML.EXPLAIN_PREDICT` | Per-row (local) | linear, logistic, tree, DNN, WnD, AutoML | `top_feature_attributions` | input table |
| `ML.GLOBAL_EXPLAIN` | Model-level | same supervised types | `feature`, `attribution` | `enable_global_explain = TRUE` |
| `ML.FEATURE_IMPORTANCE` | Model-level (tree splits) | boosted-tree, random-forest, imported XGBOOST | `importance_weight/gain/cover` | none |
| `ML.WEIGHTS` | Coefficients | `LINEAR_REG`, `LOGISTIC_REG`, `MATRIX_FACTORIZATION` | `weight` / `factor_weights` | none |
| `ML.ADVANCED_WEIGHTS` | Coefficients + stats | `LINEAR_REG`, binary `LOGISTIC_REG` | `standard_error`, `p_value` | `calculate_p_values=TRUE`, `DUMMY_ENCODING`, `l1_reg=0` |
| `ML.CENTROIDS` | Cluster centers | `KMEANS` | per-feature centroid values | none |
| `ML.PRINCIPAL_COMPONENTS` / `_INFO` | Loadings / variance | `PCA` | eigenvectors / eigenvalues | none |
| `ML.ARIMA_COEFFICIENTS` | AR/MA coefficients | `ARIMA_PLUS`, `_XREG` | `ar_coefficients`, `ma_coefficients` | none |
