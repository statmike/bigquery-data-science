# `DNN_LINEAR_COMBINED_CLASSIFIER` / `DNN_LINEAR_COMBINED_REGRESSOR`  (Wide-and-Deep)

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#dnn_linear_combined_classifier--dnn_linear_combined_regressor--wide-and-deep`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#dnn_linear_combined_classifier--dnn_linear_combined_regressor--wide-and-deep)

- **Description:** Jointly trained neural network combining a *wide* linear model (memorizes feature interactions / sparse categorical patterns) with a *deep* DNN (generalizes). Built on TensorFlow inside BigQuery ML. `DNN_LINEAR_COMBINED_CLASSIFIER` handles binary and multiclass classification; `DNN_LINEAR_COMBINED_REGRESSOR` handles regression.
- **When to use:**
  - Large, sparse categorical features (high-cardinality IDs) common in ranking and recommendation problems.
  - You want both memorization of specific feature combinations and generalization to unseen ones.
  - Tabular problems where a plain DNN underfits sparse signals but linear-only underfits interactions.
  - You need a TensorFlow SavedModel artifact (exportable, deployable to Vertex AI) trained from SQL.
- **Category:** supervised-classification | supervised-regression.
- **Connection required:** No (training/eval/predict run natively in BigQuery). A connection is only needed for unrelated remote/imported models, not for this type. Vertex AI Model Registry registration and `EXPORT MODEL` to GCS need the usual IAM, not a BigQuery connection.
- **Status:** GA.
- **documentation:** [CREATE MODEL for Wide-and-Deep models](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-wnd-models) · journey: [E2E user journey for models](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-e2e-journey) · [XAI overview](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-xai-overview) · [Hyperparameter tuning](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-hyperparameter-tuning)

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
[TRANSFORM(...)]
OPTIONS(
  model_type = 'DNN_LINEAR_COMBINED_CLASSIFIER',   -- or DNN_LINEAR_COMBINED_REGRESSOR
  input_label_cols = ['label'],
  hidden_units = [64, 32],
  activation_fn = 'RELU',
  batch_size = 100,
  dropout = 0.05,
  optimizer = 'ADAGRAD',
  learn_rate = 0.001,
  max_iterations = 10,
  early_stop = FALSE,
  enable_global_explain = TRUE,
  data_split_method = 'AUTO_SPLIT'
) AS
SELECT * FROM `PROJECT_ID.DATASET.TABLE`;
```

**Options (model-specific):**

| Option | Type | Required | Default | Range / Values | Description |
|--------|------|----------|---------|----------------|-------------|
| `model_type` | string | Yes | — | `DNN_LINEAR_COMBINED_CLASSIFIER` \| `DNN_LINEAR_COMBINED_REGRESSOR` | Selects classifier vs regressor. |
| `input_label_cols` | array\<string\> | No | `['label']` | column name(s) | Label column(s); one label required. |
| `hidden_units` | array\<int64\> | No | single layer `min(128, num_samples/(10*(num_in+num_out)))` | e.g. `[64,32]` | Deep-side hidden layer sizes. Tunable via `HPARAM_CANDIDATES`. |
| `activation_fn` | string | No | `RELU` | `RELU`,`RELU6`,`CRELU`,`ELU`,`SELU`,`SIGMOID`,`TANH` | Deep-side activation. |
| `batch_size` | int64 | No | auto (\<=1024) | \>0 | Mini-batch size. Tunable. |
| `dropout` | float64 | No | auto | `[0,1)` | Dropout probability on deep units. Tunable. |
| `optimizer` | array\<struct\> or string | No | `[STRUCT('dnn','ADAM'), STRUCT('linear','FTRL')]` | `ADAGRAD`,`ADAM`,`FTRL`,`RMSPROP`,`SGD` | Training optimizer. Can be set per model part, e.g. `[STRUCT('dnn','ADAGRAD'), STRUCT('linear','SGD')]`. **NOT tunable** (verified — see gotcha below; the generic "Tunable" claim that applies to plain `DNN_*` does not hold here). |
| `learn_rate` | array\<struct\> or float64 | No | `0.001` (both parts) | \>0 | Learning rate. Settable per part, e.g. `[STRUCT('dnn',0.001), STRUCT('linear',0.01)]`. **NOT tunable** (verified — `CREATE MODEL` errors immediately with `"Unsupported hyperparameter learn_rate for model_type DNN_LINEAR_COMBINED_CLASSIFIER"` when passed `HPARAM_RANGE`; see gotcha below). |
| `l1_reg` / `l2_reg` | float64 | No | `0` | \>=0 | L1 / L2 regularization. Tunable. |
| `max_iterations` | int64 | No | `20` | \>=1 | Max training iterations (epochs). |
| `early_stop` | bool | No | `TRUE` | — | Stop when relative loss gain \< `min_rel_progress`. |
| `min_rel_progress` | float64 | No | `0.01` | — | Min relative loss improvement to continue when `early_stop=TRUE`. |
| `warm_start` | bool | No | `FALSE` | — | Continue training from an existing model. |
| `auto_class_weights` | bool | No | `FALSE` | classifier only | Balance class weights inversely to frequency. |
| `class_weights` | array\<struct\> | No | — | classifier only | Manual per-class weights (mutually exclusive with `auto_class_weights`). |
| `data_split_method` | string | No | `AUTO_SPLIT` | `AUTO_SPLIT`,`RANDOM`,`CUSTOM`,`SEQ`,`NO_SPLIT` | Train/eval split strategy. |
| `data_split_col` | string | No | — | column name | With `CUSTOM`: `FALSE`=train, `TRUE`=eval. With `SEQ`: ordering column. |
| `data_split_eval_fraction` | float64 | No | `0.2` | `[0,1)` | Eval fraction for `RANDOM`/`SEQ`. |
| `enable_global_explain` | bool | No | `FALSE` | — | Must be `TRUE` to enable `ML.GLOBAL_EXPLAIN` / `ML.EXPLAIN_PREDICT` (integrated gradients). |
| `integrated_gradients_num_steps` | int64 | No | `25` | \>=1 | Steps for integrated-gradients attribution. |
| `num_trials` | int64 | No | — | \>=1 | Enables hyperparameter tuning; max trials to run. |
| `max_parallel_trials` | int64 | No | `1` | — | Concurrent HP-tuning trials. |
| `hparam_tuning_objectives` | array\<string\> | No | classifier `ROC_AUC`, regressor `R2_SCORE` | one objective | Metric optimized during tuning. |
| `model_registry` / `vertex_ai_model_id` / `vertex_ai_model_version_aliases` | string/array | No | — | — | Auto-register the model in Vertex AI Model Registry. |

**Supported lifecycle functions:** `ML.PREDICT`, `ML.EVALUATE`, `ML.TRAINING_INFO`, `ML.FEATURE_INFO`, `ML.EXPLAIN_PREDICT` (local attributions), `ML.GLOBAL_EXPLAIN` (needs `enable_global_explain=TRUE`), `EXPORT MODEL`. Classifier also: `ML.CONFUSION_MATRIX`, `ML.ROC_CURVE` (binary). Not supported: `ML.WEIGHTS`/`ML.ADVANCED_WEIGHTS` (no linear-coefficient export for this type) and `ML.FEATURE_IMPORTANCE` (that is tree-model only — use `ML.GLOBAL_EXPLAIN` instead).

**ML.EVALUATE output metrics (this type):**
- Classifier: `precision`, `recall`, `accuracy`, `f1_score`, `log_loss`, `roc_auc` (tested, see repo example). Adds `trial_id` when HP tuning was used.
- Regressor: `mean_absolute_error`, `mean_squared_error`, `mean_squared_log_error`, `median_absolute_error`, `r2_score`, `explained_variance`. Adds `trial_id` when HP tuning was used.

**Preprocessing support:** automatic (BQML auto-encodes numeric standardization and categorical encoding) | manual feature engineering | `TRANSFORM` clause supported (preprocessing is saved with the model and reapplied at predict time).

**Hyperparameter tuning:** Supported. Set `num_trials` (rule of thumb \>= 10 * num_hyperparameters). **Verified tunable:** `hidden_units` (via `HPARAM_CANDIDATES([STRUCT([64,32]), STRUCT([32,16])])` — same nested-STRUCT syntax as plain `DNN_*`), `dropout`, `batch_size`, `l1_reg`, `l2_reg` via `HPARAM_RANGE(...)`. **Verified NOT tunable (gotcha, contradicts a naive reading of the per-option "Tunable" docs, which describe plain `DNN_*` behavior):** `learn_rate` and `optimizer` both fail immediately with `"Unsupported hyperparameter <name> for model_type DNN_LINEAR_COMBINED_CLASSIFIER"` when given `HPARAM_RANGE`/`HPARAM_CANDIDATES`. If you need a specific learn rate, set it as a fixed literal (`learn_rate = 0.05`) alongside tuning the options that ARE tunable. Default objective: classifier `ROC_AUC`, regressor `R2_SCORE`.

**Explainability / weights:** Use `ML.EXPLAIN_PREDICT` (per-row integrated-gradients attributions, `STRUCT(k AS top_k_features)`) and `ML.GLOBAL_EXPLAIN` (aggregate feature influence). Both require `enable_global_explain=TRUE` at CREATE time. `ML.WEIGHTS`, `ML.ADVANCED_WEIGHTS`, and `ML.FEATURE_IMPORTANCE` do **not** apply.

**Best practices:**
- Set `enable_global_explain=TRUE` at training time — it cannot be added afterward without retraining.
- For imbalanced classification (e.g. fraud), prefer `auto_class_weights=TRUE` or explicit `class_weights`; the repo example trains on a 0.17%-positive fraud set.
- Training is relatively expensive (TensorFlow): repo run took ~967s over ~24 GB processed for [64,32] on ~256k rows. Start small (few layers, modest `max_iterations`) before tuning.
- Use `data_split_method='CUSTOM'` with a boolean split column to align eval data with your own TRAIN/VALIDATE/TEST scheme.

**Limitations:**
- No coefficient/weights extraction (`ML.WEIGHTS` unsupported) — explainability is attribution-based only.
- Slower and costlier to train than `LINEAR_REG`/`LOGISTIC_REG` or boosted trees for similar tabular tasks.
- `auto_class_weights` and `class_weights` are mutually exclusive and classifier-only.
- **Same small-dataset convergence failure as `DNN_REGRESSOR` (verified, `models/wide_and_deep_regressor/`):** on a 333-row regression dataset, unscaled numeric features + the default `learn_rate=0.001` + `early_stop=TRUE` produced a badly broken model (`r2_score≈-27.4`, 2 iterations) — same fix works (scale + raise `learn_rate` to 0.05): `r2_score≈0.79` untuned with `hidden_units=[64,32]`, notably lower than `DNN_REGRESSOR`'s ~0.86 with the equivalent fix on the identical data — hyperparameter tuning (below) closes most of the gap, finding `hidden_units=[32,16]` reaches `r2_score≈0.87`. Unlike `DNN_REGRESSOR`, `learn_rate` cannot be tuned here (see the tuning gotcha above), so if the default doesn't converge on your data you must set a higher `learn_rate` as a fixed literal — you can't discover a better one via `HPARAM_RANGE`.
- `learn_rate` and `optimizer` are not tunable (see Hyperparameter tuning above) — a real gap relative to plain `DNN_CLASSIFIER`/`DNN_REGRESSOR`, where both are tunable.

**Locations:** Available in all BigQuery ML regions/multi-regions; for Vertex AI registration / endpoint serving keep model and Vertex resources co-located (repo uses `us-central1`).

**BigFrames API:** Verified (checked the live BigFrames API reference across every `bigframes.ml` module) — **no first-class wide-and-deep class exists anywhere in `bigframes.ml`**, same permanent gap as `DNN_CLASSIFIER`/`DNN_REGRESSOR`. Use the SQL `CREATE MODEL` interface directly.

**Repo example (tested):** `bigquery-ml/models/wide_and_deep_classifier/` and `bigquery-ml/models/wide_and_deep_regressor/` — from-scratch, fully pre-validated builds on the same comparison datasets every other model type in this project uses (`census_adult_income` and `penguins`/`body_mass_g`), which is what makes the wide-and-deep result readable against the plain DNN directly above it. Between them they cover `ML.FEATURE_INFO`, `ML.TRAINING_INFO`, `ML.EVALUATE` (precision/recall/accuracy/f1_score/log_loss/roc_auc), `ML.CONFUSION_MATRIX`, `ML.ROC_CURVE`, `ML.PREDICT`, `ML.EXPLAIN_PREDICT`, `ML.GLOBAL_EXPLAIN`, `ML.FEATURE_IMPORTANCE`, `ML.ADVANCED_WEIGHTS`, and HP tuning, with `auto_class_weights`, `enable_global_explain`, and an explicit `data_split_method`. `EXPORT MODEL` produces a TensorFlow SavedModel — see `bigquery-ml/models/export/`, and `bigquery-ml/models/remote/` for Endpoint deployment.


---
