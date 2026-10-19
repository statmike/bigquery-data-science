# Quick comparison

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#quick-comparison`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#quick-comparison)

| | `ML.EXPLAIN_PREDICT` | `ML.GLOBAL_EXPLAIN` | `ML.FEATURE_IMPORTANCE` |
|---|---|---|---|
| Scope | Per-row (local) | Model-level (aggregated) | Model-level (tree split stats) |
| Models | linear, logistic, tree, DNN, WnD, AutoML | same, **+ `enable_global_explain=TRUE`** | boosted-tree, random-forest only |
| Needs eval/predict input | Yes (input table) | No | No |
| Key output | `top_feature_attributions` | `feature`, `attribution` | `importance_weight/gain/cover` |
| Pre-req option | none | `enable_global_explain = TRUE` | none |


---
