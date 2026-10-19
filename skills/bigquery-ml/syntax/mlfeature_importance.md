# `ML.FEATURE_IMPORTANCE`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlfeature_importance`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlfeature_importance)

- **Description:** Returns XGBoost split-based feature importance (weight, gain, cover) for tree-ensemble models. Reflects how the trees actually used each feature during training — distinct from attribution-based explanations.
- **Use cases:**
  - Rank features for boosted-tree / random-forest models.
  - Feature selection / pruning based on gain.
  - Cross-check tree usage against `ML.GLOBAL_EXPLAIN` attributions.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-importance
- **Type:** Table-valued function.
- **Applies to models:** `BOOSTED_TREE_CLASSIFIER`, `BOOSTED_TREE_REGRESSOR`, `RANDOM_FOREST_CLASSIFIER`, `RANDOM_FOREST_REGRESSOR` only. Does NOT require `enable_global_explain`.

**Syntax:**
```sql
ML.FEATURE_IMPORTANCE(MODEL `PROJECT_ID.DATASET.MODEL_NAME`)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| MODEL | model | Yes | — | A boosted-tree or random-forest model. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| feature | STRING | Input feature name. |
| importance_weight | FLOAT64 | Number of splits the feature was used in across all trees. |
| importance_gain | FLOAT64 | Improvement in accuracy from splits using the feature (usually the most informative). |
| importance_cover | FLOAT64 | Number of data rows covered by splits using the feature. |

**Best practices:**
- Prefer `importance_gain` for judging predictive value; `weight`/`cover` describe usage frequency/coverage.
- Use alongside `ML.GLOBAL_EXPLAIN` (attribution-based) for a fuller picture.

**Limitations:**
- Tree-ensemble models only — not valid for linear, DNN, or unsupervised models (use `ML.WEIGHTS` or `ML.GLOBAL_EXPLAIN` instead).

**BigFrames API:** Tree-ensemble estimators expose `model.feature_importances_` in `bigframes.ml`.

**Repo example (tested):**
- `bigquery-ml/models/boosted_tree_classifier/boosted_tree_classifier.sql` (Example 7) — `ML.FEATURE_IMPORTANCE(MODEL ...) ORDER BY importance_gain DESC` on a `BOOSTED_TREE_CLASSIFIER`, paired with `ML.GLOBAL_EXPLAIN` in the same example. The other three supported types carry it too: `models/boosted_tree_regressor/`, `models/random_forest_classifier/`, `models/random_forest_regressor/`.
- `bigquery-ml/workflows/churn_retention/churn_retention.sql` (Step 4) — verified live, the two rankings genuinely disagree: `return_rate` is 8th-of-9 by `ML.GLOBAL_EXPLAIN` attribution but 3rd by `importance_gain`. Gain measures how useful a feature is *when* the trees split on it, so a rarely-used feature can still score high; attribution measures typical contribution across all predictions, split frequency included. Neither ranking is "more correct."

---
