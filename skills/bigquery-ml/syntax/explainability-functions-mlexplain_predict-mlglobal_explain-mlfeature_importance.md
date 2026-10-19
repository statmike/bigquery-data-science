# Explainability functions: `ML.EXPLAIN_PREDICT`, `ML.GLOBAL_EXPLAIN`, `ML.FEATURE_IMPORTANCE`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#explainability-functions-mlexplain_predict-mlglobal_explain-mlfeature_importance`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#explainability-functions-mlexplain_predict-mlglobal_explain-mlfeature_importance)

Three lifecycle functions for model interpretability. `ML.EXPLAIN_PREDICT` gives **local** (per-row) feature attributions; `ML.GLOBAL_EXPLAIN` gives **model-level** (aggregated) attributions; `ML.FEATURE_IMPORTANCE` gives **tree-specific** split-based importance for boosted-tree / random-forest models. For the underlying concepts see the [BigQuery Explainable AI overview](https://cloud.google.com/bigquery/docs/xai-overview). For the model-coefficient view (`ML.WEIGHTS` / `ML.ADVANCED_WEIGHTS`), see the weights entry; this entry covers attributions/importance only.

---
