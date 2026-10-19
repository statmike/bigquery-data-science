# `ML.ROC_CURVE`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlroc_curve`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlroc_curve)

- **Description:** Returns ROC-curve points for a **binary** classification model — one row per threshold with recall (true positive rate), false positive rate, and the raw TP/FP/TN/FN counts.
- **Use cases:**
  - Plot the ROC curve and reason about the threshold that best balances recall vs. false positives.
  - Build a precision-recall curve from the returned TP/FP counts.
  - Choose an operating threshold for downstream `ML.PREDICT` decisions.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-roc
- **Type:** Table-valued function (TVF).
- **Applies to models:** **Binary classification only** — `LOGISTIC_REG` (binary), `BOOSTED_TREE_CLASSIFIER` (binary), `RANDOM_FOREST_CLASSIFIER` (binary), `DNN_CLASSIFIER` (binary), wide-and-deep classifier (binary), `AUTOML_CLASSIFIER` (binary). Not for multiclass models, regression, or unsupervised models.

**Syntax:**
```sql
ML.ROC_CURVE(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`
  [, { TABLE `PROJECT_ID.DATASET.TABLE` | (QUERY_STATEMENT) }]
  [, GENERATE_ARRAY(THRESHOLDS)]
  [, STRUCT(TRIAL_ID AS trial_id)]
)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model ref | Yes | — | A trained binary classification model. |
| `TABLE` / `QUERY_STATEMENT` | table or query | No\* | eval/training split | Evaluation data matching the model's features + label column. If omitted, uses the held-out eval split (or full training data if unsplit). \*Required for some models. |
| `GENERATE_ARRAY(THRESHOLDS)` | ARRAY\<FLOAT64\> | No | 100 approx. quantiles | Explicit threshold values to evaluate, e.g. `GENERATE_ARRAY(0.4, 0.6, 0.01)`. If omitted, thresholds are chosen automatically from ~100 quantiles of the prediction scores. |
| `trial_id` | INT64 (in STRUCT) | No | optimal trial | Select a specific hyperparameter-tuning trial. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `threshold` | FLOAT64 | The decision cutoff for this row. |
| `recall` | FLOAT64 | True positive rate at this threshold. |
| `false_positive_rate` | FLOAT64 | FP / (FP + TN) at this threshold (plot vs. recall for the ROC curve). |
| `true_positives` | INT64 | Count of correctly predicted positives. |
| `false_positives` | INT64 | Count of negatives predicted positive. |
| `true_negatives` | INT64 | Count of correctly predicted negatives. |
| `false_negatives` | INT64 | Count of positives predicted negative. |

**Best practices:**
- `ORDER BY threshold` for clean plotting; let thresholds default unless you need a fine sweep over a narrow band (use `GENERATE_ARRAY`).
- Derive precision-recall directly: `true_positives / (true_positives + false_positives) AS precision`.
- The `roc_auc` summary value comes from `ML.EVALUATE`; use `ML.ROC_CURVE` for the full curve / threshold selection.

**Limitations:**
- Binary classification only — no multiclass.
- Some older models require explicit input data or return an error.
- With a TRANSFORM clause, the input query needs only the pre-TRANSFORM input columns.

**BigFrames API:** `model.roc_curve(X, y)` on a `bigframes.ml` binary classifier (returns fpr / tpr / thresholds).
**Repo example (tested):**
- `bigquery-ml/models/logistic_regression/logistic_regression.sql` (Example 4) — selects `threshold, recall, false_positive_rate, true_positives, false_positives, true_negatives, false_negatives FROM ML.ROC_CURVE(...) ORDER BY threshold`.
- `bigquery-ml/models/boosted_tree_classifier/boosted_tree_classifier.sql` (Example 4) — the identical projection on a `BOOSTED_TREE_CLASSIFIER`. `models/random_forest_classifier/`, `models/dnn_classifier/`, `models/wide_and_deep_classifier/`, and `models/automl_classifier/` repeat it, so the curves line up across model types.

> Note: classification eval here covers the model-bound TVFs. For unsupervised anomaly detection (PCA / k-means / autoencoder — see `models/pca/`, `models/kmeans/`, `models/autoencoder/`) and ARIMA_PLUS forecasting eval, see the `ML.DETECT_ANOMALIES`, `ML.RECONSTRUCTION_LOSS`, and forecasting entries — `ML.CONFUSION_MATRIX` / `ML.ROC_CURVE` do not apply to those model types.


---
