# `ML.CONFUSION_MATRIX`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlconfusion_matrix`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlconfusion_matrix)

- **Description:** Returns a confusion matrix for a trained classification model — rows of actual (expected) labels vs. counts of predicted labels — computed over evaluation/input data.
- **Use cases:**
  - Inspect per-class correct vs. incorrect predictions beyond a single accuracy number.
  - Diagnose class imbalance and which classes a model confuses (multiclass).
  - Validate the effect of a custom decision `threshold` on binary classifiers.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-confusion
- **Type:** Table-valued function (TVF).
- **Applies to models:** Classification models only — `LOGISTIC_REG` (binary + multiclass), `BOOSTED_TREE_CLASSIFIER`, `RANDOM_FOREST_CLASSIFIER`, `DNN_CLASSIFIER`, `DNN_LINEAR_COMBINED_CLASSIFIER` (wide-and-deep), and `AUTOML_CLASSIFIER`. Does **not** support imported TensorFlow models, regression, clustering, MF, PCA, autoencoder, ARIMA_PLUS, or remote/LLM models.

**Syntax:**
```sql
ML.CONFUSION_MATRIX(
  MODEL `PROJECT_ID.DATASET.MODEL_NAME`
  [, { TABLE `PROJECT_ID.DATASET.TABLE` | (QUERY_STATEMENT) }]
  [, STRUCT([THRESHOLD AS threshold] [, TRIAL_ID AS trial_id])]
)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model ref | Yes | — | A trained classification model. |
| `TABLE` / `QUERY_STATEMENT` | table or query | No\* | eval/training split | Input data whose columns match the model's features plus the label column. If omitted, uses the held-out eval split (or the full training data if no split). \*Required for some models, and required if you set `threshold`. |
| `threshold` | FLOAT64 (in STRUCT) | No | 0.5 | Custom positive-class cutoff. **Binary only** — error if used on a multiclass model. Requires TABLE/QUERY also be supplied. |
| `trial_id` | INT64 (in STRUCT) | No | optimal trial | Select a specific hyperparameter-tuning trial; defaults to the optimal trial. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `expected_label` | (label type) | Actual label value; one row per class. Exact value/type as passed in the label column. |
| \<one column per class\> | INT64 | Count of rows with that actual label predicted as this class. Column name is the class label (if it conforms to BigQuery column-naming rules). |

**Best practices:**
- Call without input args right after training to use the held-out eval split; pass your own TABLE for an independent test set.
- For binary models, sweep `threshold` (e.g. 0.3 / 0.5 / 0.7) to see precision/recall trade-offs as integer counts.
- Pair with `ML.EVALUATE` (scalar metrics) and `ML.ROC_CURVE` (threshold curve) for a complete classification picture.

**Limitations:**
- Classification models only; no regression/clustering/imported-TF.
- `threshold` is binary-only and requires explicit input data.
- Column names derive from class labels; labels not matching column-naming rules get sanitized names.

**BigFrames API:** `model.confusion_matrix(X, y)` on a `bigframes.ml` classifier (e.g. `LogisticRegression`, `XGBoostClassifier`).
**Repo example (tested):**
- `bigquery-ml/models/logistic_regression/logistic_regression.sql` (Example 3) — `SELECT * FROM ML.CONFUSION_MATRIX(MODEL ...)` on the census income binary classifier.
- `bigquery-ml/models/boosted_tree_classifier/boosted_tree_classifier.sql` (Example 3) — the same call on a `BOOSTED_TREE_CLASSIFIER`; `models/random_forest_classifier/`, `models/dnn_classifier/`, `models/wide_and_deep_classifier/`, and `models/automl_classifier/` each carry it too, so the matrix is directly comparable across classifier types on one dataset.
- `bigquery-ml/workflows/churn_retention/churn_retention.sql` (Step 3) — uses the matrix to settle *which class* a metric describes: the `expected_label = true` row (FALSE=1997, TRUE=3059) confirms `ML.EVALUATE`'s `recall = 0.605` is recall on the churned class, not the retained one.
- `bigquery-ml/workflows/cross_validation/cross_validation.sql` — the motivating case for k-fold: a held-out eval split with only ~15 real fraud cases (TP=13, FN=2), where a metric estimated from 15 positives is exactly the high-variance situation cross-validation exists to quantify.

---
