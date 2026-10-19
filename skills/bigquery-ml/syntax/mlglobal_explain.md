# `ML.GLOBAL_EXPLAIN`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlglobal_explain`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlglobal_explain)

- **Description:** Returns model-level feature importance by averaging the absolute local attributions across the evaluation data. Requires the model to have been trained with `enable_global_explain = TRUE`.
- **Use cases:**
  - Rank which features matter most to the model overall.
  - Compare feature influence across model versions.
  - Per-class importance for classification (with `class_level_explain`).
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-global-explain
- **Type:** Table-valued function.
- **Applies to models:** Same supervised types as `ML.EXPLAIN_PREDICT` (`LINEAR_REG`, `LOGISTIC_REG`, `BOOSTED_TREE_*`, `RANDOM_FOREST_*`, `DNN_*`, `WIDE_AND_DEEP_*`) **trained with `enable_global_explain = TRUE`**. Not supported for k-means, PCA, autoencoder, matrix factorization, imported XGBoost, or AutoML models.

**Prerequisite (CREATE MODEL):**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
OPTIONS(
  model_type = 'LOGISTIC_REG',
  input_label_cols = ['label'],
  enable_global_explain = TRUE   -- computed at training time; required here
) AS SELECT ... ;
```

**Syntax:**
```sql
ML.GLOBAL_EXPLAIN(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`
  [, STRUCT(<class_level_explain> AS class_level_explain)]
)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| MODEL | model | Yes | — | Model trained with `enable_global_explain = TRUE`. |
| class_level_explain | BOOL | No | FALSE | If TRUE, return importances per class (non-AutoML classification models only); otherwise one importance per feature for the whole model. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| feature | STRING | Input feature name. |
| attribution | FLOAT64 | Mean absolute attribution of the feature across the evaluation set. |
| class_label | STRING | Class the importance applies to — present only when `class_level_explain = TRUE`. |

**Best practices:**
- Always set `enable_global_explain = TRUE` at `CREATE MODEL` time for supported models — you cannot enable it after training without retraining.
- `ORDER BY attribution DESC` to rank features.

**Limitations:**
- Errors ("input model was not explained when it was created") if `enable_global_explain` was not set at training.
- `class_level_explain` is ignored/invalid for regression and AutoML Tables models.
- Global explanations are computed once at training time, not at call time.

**BigFrames API:** `model.global_explain()` on supported supervised estimators in `bigframes.ml`.

**Repo example (tested):**
- `bigquery-ml/models/logistic_regression/logistic_regression.sql` (Examples 1 & 7) — `enable_global_explain = TRUE` then `ML.GLOBAL_EXPLAIN(...) ORDER BY attribution DESC`.
- `bigquery-ml/models/boosted_tree_classifier/boosted_tree_classifier.sql` (Example 7) — the same pattern on a boosted-tree classifier, run side by side with `ML.FEATURE_IMPORTANCE` to show the two rank features differently by design.
- `bigquery-ml/workflows/churn_retention/churn_retention.sql` (Step 4) — verified live: `tenure_days` dominates (attribution 0.072), ahead of `frequency` (0.028), `recency_days` (0.015), and `age` (0.015) — account age matters more than any single RFM feature.

---
