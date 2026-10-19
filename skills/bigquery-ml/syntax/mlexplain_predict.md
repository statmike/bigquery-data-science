# `ML.EXPLAIN_PREDICT`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlexplain_predict`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlexplain_predict)

- **Description:** An extended `ML.PREDICT` that returns, for each input row, the prediction plus the top-k feature attributions explaining how each feature pushed the prediction away from a baseline.
- **Use cases:**
  - Explain an individual prediction ("why did this customer get scored as churn?").
  - Debug surprising predictions by inspecting per-row contributions.
  - Surface row-level reason codes for downstream apps.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-explain-predict
- **Type:** Table-valued function.
- **Applies to models:** `LINEAR_REG`, `LOGISTIC_REG`, `BOOSTED_TREE_*`, `RANDOM_FOREST_*`, `DNN_*`, `WIDE_AND_DEEP_*`, and AutoML Tables models. Attribution method varies by type: exact (Shapley/tree) where `baseline_prediction_value + sum(attributions) = prediction_value` (linear, tree models), and integrated gradients (approximate) for DNN / Wide-and-Deep. Does NOT apply to unsupervised models (k-means, PCA, autoencoder, matrix factorization) or ARIMA_PLUS.

**Syntax:**
```sql
ML.EXPLAIN_PREDICT(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`,
  { TABLE `PROJECT_ID.DATASET.TABLE` | (QUERY_STATEMENT) },
  STRUCT(
    [<top_k_features> AS top_k_features]
    [, <threshold> AS threshold]
    [, <integrated_gradients_num_steps> AS integrated_gradients_num_steps]
    [, <approx_feature_contrib> AS approx_feature_contrib]
  )
)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| MODEL | model | Yes | — | The trained model to explain. |
| TABLE / QUERY_STATEMENT | table/query | Yes | — | Rows to predict and explain (must contain the model's feature columns). |
| top_k_features | INT64 | No | 5 | Number of top features (by absolute attribution) returned per row. If larger than the feature count, all features are returned. |
| threshold | FLOAT64 | No | 0.5 | Binary-classification cutoff (0.0–1.0); predictions above are positive. Attributions returned for the predicted label. |
| integrated_gradients_num_steps | INT64 | No | 25 | Steps sampled between the example and its baseline for integrated-gradients attribution (DNN / Wide-and-Deep). Higher = more precise but slower. |
| approx_feature_contrib | BOOL | No | FALSE | Use XGBoost's approximate feature-contribution method. Boosted-tree / random-forest models only. |

**Outputs:** (passthrough input columns, plus)

| Column | Type | Description |
|--------|------|-------------|
| predicted_\<label\> | STRING/numeric | Predicted label class (classification) or value (regression). |
| probability | FLOAT64 | Probability of the predicted class (classification models only). |
| top_feature_attributions | ARRAY\<STRUCT\<feature STRING, attribution FLOAT64\>\> | Top-k features and their signed contribution to the prediction. |
| baseline_prediction_value | FLOAT64 | The baseline (expected) prediction the attributions are measured against. |
| prediction_value | FLOAT64 | The raw prediction value being explained. |
| approximation_error | FLOAT64 | 0 for exact methods (linear/tree); \>0 for integrated gradients (DNN). |

**Best practices:**
- Keep `top_k_features` small for readability; raise only when you need the full attribution vector.
- For DNN/WnD, increase `integrated_gradients_num_steps` if `approximation_error` is large.
- Run on a sampled/`LIMIT`ed input — it is per-row and can be expensive over large tables.

**Limitations:**
- Not available for unsupervised or ARIMA_PLUS models.
- `approx_feature_contrib` applies only to tree ensembles; `integrated_gradients_num_steps` only to DNN/WnD.

**BigFrames API:** `model.predict_explain(X, top_k_features=...)` on supported supervised estimators in `bigframes.ml`.

**Repo example (tested):**
- `bigquery-ml/models/logistic_regression/logistic_regression.sql` (Example 6) — `STRUCT(5 AS top_k_features)`, selecting `top_feature_attributions`.
- `bigquery-ml/models/boosted_tree_classifier/boosted_tree_classifier.sql` (Example 6) — the same call on a `BOOSTED_TREE_CLASSIFIER`, with a `LIMIT 10` input query showing the sample-the-input best practice above.
- `bigquery-ml/workflows/churn_retention/churn_retention.sql` (Step 5) — `STRUCT(3 AS top_k_features)` for per-customer driver attribution, i.e. the per-row counterpart to the model-level ranking in its Step 4.

---
