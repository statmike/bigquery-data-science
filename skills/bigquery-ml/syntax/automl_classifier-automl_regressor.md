# `AUTOML_CLASSIFIER` / `AUTOML_REGRESSOR`

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#automl_classifier--automl_regressor`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#automl_classifier--automl_regressor)

- **Description:** BigQuery ML wrappers that train a [Vertex AI AutoML Tables](https://cloud.google.com/vertex-ai/docs/tabular-data/overview) model directly from SQL. The AutoML service searches multiple model architectures, performs its own feature engineering and hyperparameter tuning, and ensembles candidates to produce a single tabular classification (`AUTOML_CLASSIFIER`) or regression (`AUTOML_REGRESSOR`) model. The user supplies training data and a time budget; AutoML does the rest.
- **When to use:**
  - You want a strong tabular baseline without choosing/tuning the algorithm yourself.
  - You can trade longer, higher-cost training (1–72 hours) for accuracy.
  - You want a model you can export and serve on Vertex AI endpoints.
  - You do NOT need fast, iterative, in-BigQuery retraining (use `BOOSTED_TREE_*` / `DNN_*` / `LINEAR_REG`/`LOGISTIC_REG` for that).
- **Category:** automl (supervised-classification / supervised-regression).
- **Connection required:** No. Training runs as a BigQuery `ML_EXTERNAL` job that invokes Vertex AI on your behalf — no `CREATE CONNECTION` object is needed (unlike remote/imported models). The Vertex AI API must be enabled in the project.
- **Status:** GA.
- **documentation:** [CREATE MODEL for AutoML models](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-automl) · journey links: [E2E user journey for models](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-e2e-journey) · [Vertex AI tabular classification/regression overview](https://cloud.google.com/vertex-ai/docs/tabular-data/classification-regression/overview) · [Manage BQML models in Vertex AI](https://cloud.google.com/bigquery/docs/managing-models-vertex) · [Export BQML models](https://cloud.google.com/bigquery/docs/exporting-models).

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
OPTIONS(
  model_type = 'AUTOML_CLASSIFIER',          -- or 'AUTOML_REGRESSOR'
  input_label_cols = ['label_column'],
  budget_hours = 1.0,
  optimization_objective = 'MAXIMIZE_AU_PRC', -- classifier objective (see below)
  data_split_col = 'splits'
) AS
SELECT * EXCEPT(id_column)
FROM `PROJECT_ID.DATASET.TRAINING_TABLE`;
```

**Options (model-specific):**

| Option | Type | Required | Default | Range / Values | Description |
|--------|------|----------|---------|----------------|-------------|
| `model_type` | STRING | Yes | — | `'AUTOML_CLASSIFIER'` \| `'AUTOML_REGRESSOR'` | Selects AutoML Tables classification or regression. |
| `input_label_cols` | ARRAY\<STRING\> | No | `['label']` | one column name | Label column. Classifier label may be STRING or numeric; regressor label is numeric. |
| `budget_hours` | FLOAT64 | No | `1.0` | `1.0`–`72.0` | Training time budget in hours. Model compression after training can add up to ~50% more wall-clock time, which is NOT counted against the budget. |
| `optimization_objective` | STRING or STRUCT | No | task default | see values below | Objective AutoML optimizes. Binary classification may use a STRUCT to set a recall/precision target. |
| `data_split_col` | STRING | No | — | column name | Column that assigns each row to a split. Values map to AutoML splits (e.g. `TRAIN`/`VALIDATE`/`TEST`). |
| `data_split_method` | STRING | No | AutoML auto-split | — | AutoML manages splitting; prefer `data_split_col` for explicit control. |
| `kms_key_name` | STRING | No | — | KMS key resource name | CMEK for the model. |
| `vertex_ai_model_id` | STRING | No | — | model id | Registers the trained model in the Vertex AI Model Registry at creation time. |
| `vertex_ai_model_version_aliases` | ARRAY\<STRING\> | No | — | alias strings | Version aliases applied in the Vertex AI Model Registry. |

`optimization_objective` values:
- **`AUTOML_CLASSIFIER`:** `MAXIMIZE_AU_ROC` (default), `MINIMIZE_LOG_LOSS`, `MAXIMIZE_AU_PRC`, and (binary only) `MAXIMIZE_PRECISION_AT_RECALL` / `MAXIMIZE_RECALL_AT_PRECISION` via a STRUCT supplying the target value.
- **`AUTOML_REGRESSOR`:** `MINIMIZE_RMSE` (default), `MINIMIZE_MAE`, `MINIMIZE_RMSLE`.

**Supported lifecycle functions:** `ML.PREDICT`, `ML.EVALUATE`, `ML.GLOBAL_EXPLAIN` (model-level only; requires no `enable_global_explain` option — AutoML produces attributions automatically), `ML.FEATURE_INFO`, `ML.TRAINING_INFO`. Classification additionally supports `ML.CONFUSION_MATRIX` and (binary) `ML.ROC_CURVE`. `EXPORT MODEL` is supported (TensorFlow SavedModel / XGBoost). NOT supported: `ML.WEIGHTS` / `ML.ADVANCED_WEIGHTS`, `ML.FEATURE_IMPORTANCE`, `ML.EXPLAIN_PREDICT` (AutoML is an opaque ensemble; use `ML.GLOBAL_EXPLAIN` for feature attributions).

**GOTCHA (verified): the zero-argument form of `ML.CONFUSION_MATRIX` — `ML.CONFUSION_MATRIX(MODEL ...)`, relying on AutoML's own internal held-out eval split — fails immediately and consistently with a generic internal error (`Error: 21631273`, "This is usually caused by a transient issue") on an `AUTOML_CLASSIFIER` model.** Reproduced on 100+ consecutive attempts via both the `bq` CLI and the Python client — it is NOT actually transient, and the `google-cloud-bigquery` client's default retry logic treats it as retryable, so a `client.query(...).result()` call appears to hang for a very long time instead of failing fast. **`ML.EVALUATE` and `ML.ROC_CURVE`'s zero-argument forms both work fine on the identical model** — this is isolated specifically to `ML.CONFUSION_MATRIX`. **Fix: always pass an explicit data argument** — `ML.CONFUSION_MATRIX(MODEL ..., (SELECT ...))` — which works normally (confirmed in seconds against the model's own training table). If a notebook/script hits this, interrupt/cancel the call rather than waiting — it will not resolve on its own.

**GOTCHA (verified): the zero-argument `ML.EVALUATE` aggregate for AutoML model types contains at least one field that does not reduce to a straightforward, reconcilable statistic.** For `AUTOML_CLASSIFIER`, `accuracy=0.5` was returned alongside `roc_auc=0.930` — the model's own metadata (`bq show --model`) confirmed evaluation ran against a class-balanced ~6,416-row internal eval set (3,208 per class, not the natural class distribution), but `accuracy=0.5`/`precision`/`recall` didn't match ANY of the model's 203 confidence-threshold rows in its own `binaryConfusionMatrixList` (whose threshold=0.5 row shows `accuracy=0.844`, not `0.5`) — the exact Vertex AI methodology behind the aggregate isn't visible from BigQuery's side. For `AUTOML_REGRESSOR`, `median_absolute_error` and `explained_variance` both returned exactly `0.0` while `mean_absolute_error`/`mean_squared_error`/`r2_score` looked genuine and self-consistent (`mean_squared_error` matched `ML.TRAINING_INFO`'s `eval_loss` exactly) — this couldn't be root-caused as deeply since the model had already been dropped by the time it was reviewed. **Fix/workaround for both:** pass an explicit data argument — `ML.EVALUATE(MODEL ..., (SELECT ...))` — which returns standard, reconcilable metrics (confirmed for the classifier: `accuracy=0.8508` against the training table, matching a directly-computed confusion matrix exactly). Prefer `roc_auc`/`log_loss` (classifier) or `mean_squared_error`/`r2_score` (regressor) — both threshold-independent and verified trustworthy — over the zero-argument `accuracy`/`median_absolute_error`/`explained_variance` fields for this model type.

**ML.EVALUATE output metrics (this type):**
- **`AUTOML_CLASSIFIER`:** `precision`, `recall`, `accuracy`, `f1_score`, `log_loss`, `roc_auc`.
- **`AUTOML_REGRESSOR`:** `mean_absolute_error`, `mean_squared_error`, `mean_squared_log_error`, `median_absolute_error`, `r2_score`, `explained_variance`.

**Preprocessing support:** automatic (AutoML standardizes numeric columns, one-hot encodes categoricals, and extracts components from timestamps internally). The `TRANSFORM` clause is NOT supported for AutoML model types — do any custom feature engineering in the training `SELECT`.

**Hyperparameter tuning:** Not user-configurable via `NUM_TRIALS` / `HPARAM_RANGE` / `HPARAM_CANDIDATES`. AutoML performs its own architecture search and hyperparameter tuning internally; the user lever is `budget_hours`.

**Explainability / weights:** `ML.GLOBAL_EXPLAIN` only, returning model-level mean absolute feature attributions (columns `feature`, `attribution`). For AutoML, `class_level_explain` is ignored — only model-level importance is available for both classifier and regressor. `ML.WEIGHTS`, `ML.ADVANCED_WEIGHTS`, and `ML.EXPLAIN_PREDICT` do not apply.

**Best practices:**
- Budget cost vs. accuracy: start at `budget_hours = 1.0` to validate the pipeline, then raise toward 72.0 only if the lift justifies the cost.
- Use `data_split_col` with a pre-computed split column for reproducible, leakage-free TRAIN/VALIDATE/TEST partitioning.
- For imbalanced classification (e.g. fraud), prefer `MAXIMIZE_AU_PRC` over `MAXIMIZE_AU_ROC`.
- Register to Vertex AI at training time via `vertex_ai_model_id` instead of exporting/uploading separately.

**Limitations:**
- **Verified: training data must contain at least 1,000 rows.** `CREATE MODEL` fails immediately with `"Input data contains N rows. The minimum number of input rows for AutoML Tables models is 1000."` if fewer — this applies regardless of `budget_hours` and is not called out in the official reference. Small demo datasets used elsewhere in this project (e.g. `penguins`, ~333 rows) cannot train an AutoML model at all; see `models/automl_regressor/` for a real example of hitting this and switching datasets.
- Trains as an `ML_EXTERNAL` job on Vertex AI (not in-BigQuery `QUERY`); on flat-rate/reservations the project must accommodate `ML_EXTERNAL`. Evaluation/prediction run as standard `QUERY` jobs.
- Classifier label cardinality is capped at 1,000 unique classes (contact bqml-feedback@google.com for more).
- Feature column names must be 125 characters or fewer.
- Default max 5 concurrent AutoML training jobs per project (raising Vertex AI quota does not change this; submit a request to raise it).
- Wall-clock time exceeds `budget_hours` because of model compression and data movement to/from AutoML.
- No `TRANSFORM`, no `ML.WEIGHTS`, no `ML.EXPLAIN_PREDICT`, no user HP-tuning.

**Locations:** AutoML model availability differs by region/multi-region; check [BigQuery ML locations](https://cloud.google.com/bigquery/docs/locations). Training data, model, and the Vertex AI region must be compatible.

**BigFrames API:** Verified (checked the live BigFrames API reference across every `bigframes.ml` module: `linear_model`, `ensemble`, `cluster`, `decomposition`, `forecasting`, `imported`, `llm`) — **no first-class AutoML estimator class exists anywhere in `bigframes.ml`**, the same permanent gap as `DNN_CLASSIFIER`/`DNN_REGRESSOR`/wide-and-deep. Use the SQL `CREATE MODEL` interface directly.

**Repo example (tested):** `bigquery-ml/models/automl_classifier/` (same `census_adult_income` data as the other classifiers) and `bigquery-ml/models/automl_regressor/` (a real `bigquery-public-data.samples.natality` regression, NOT the usual `penguins` — see the minimum-row-count limitation above). Between them they cover `ML.FEATURE_INFO`, `ML.TRAINING_INFO`, `ML.EVALUATE` (`precision`/`recall`/`accuracy`/`f1_score`/`log_loss`/`roc_auc`), `ML.CONFUSION_MATRIX`, `ML.ROC_CURVE`, `ML.PREDICT`, `ML.EXPLAIN_PREDICT`, `ML.GLOBAL_EXPLAIN`, and `ML.WEIGHTS`. Both were validated via `bq query --dry_run` (free syntax check) rather than a throwaway paid pre-validation run, given this model type's real dollar cost (~$21.25/node-hour).

**Budget the wall-clock at 2-3× the stated budget.** `budget_hours = 1.0` produced **2.63 hours** wall-clock for the classifier and **2.25 hours** for the regressor, both verified via `ML.TRAINING_INFO`'s `duration_ms`. The overhead is not a small fixed margin on top of the budget — it more than doubled it in both measured runs, so a "1-hour" AutoML job should be planned as a 2-3 hour job.


---
