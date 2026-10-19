# `DNN_CLASSIFIER` / `DNN_REGRESSOR`

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#dnn_classifier--dnn_regressor`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#dnn_classifier--dnn_regressor)

- **Description:** Deep neural network models trained with TensorFlow inside BigQuery. Fully-connected feed-forward networks with one or more hidden layers, capturing non-linear relationships between features and the label. `DNN_CLASSIFIER` does binary or multiclass classification; `DNN_REGRESSOR` predicts a continuous numeric value.
- **When to use:**
  - Non-linear feature/label relationships that linear or tree models underfit.
  - Medium-to-large structured/tabular data where extra capacity (depth/width) helps.
  - You want built-in feature attributions (Integrated Gradients) and easy Vertex AI Model Registry export for online serving.
  - Prefer Boosted Tree or AutoML first for most tabular tasks; reach for DNN when you specifically want a neural net or need TensorFlow export artifacts.
- **Category:** supervised-classification | supervised-regression.
- **Connection required:** No (in-BigQuery training). A connection is only relevant for downstream `EXPORT MODEL` to GCS or Vertex AI serving, not for training/eval/predict.
- **Status:** GA.
- **documentation:** [CREATE MODEL for DNN models](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-dnn-models) · journey-page group: [E2E model journey](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-e2e-journey), [XAI overview](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-xai-overview), [HP tuning](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-hp-tuning-overview).

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
[TRANSFORM(ML.STANDARD_SCALER(Amount) OVER() AS Amount, * EXCEPT(Amount))]
OPTIONS(
  model_type = 'DNN_CLASSIFIER',         -- or 'DNN_REGRESSOR'
  input_label_cols = ['label'],
  hidden_units = [64, 32],
  activation_fn = 'RELU',
  optimizer = 'ADAGRAD',
  learn_rate = 0.01,
  batch_size = 100,
  dropout = 0.15,
  max_iterations = 20,
  early_stop = TRUE,
  auto_class_weights = FALSE,            -- classifier only
  enable_global_explain = TRUE,
  integrated_gradients_num_steps = 30,
  data_split_method = 'AUTO_SPLIT'
) AS
SELECT * EXCEPT(id) FROM `PROJECT_ID.DATASET.TRAINING_TABLE`;
```

**Options (model-specific):**

| Option | Type | Required | Default | Range / Values | Description |
|--------|------|----------|---------|----------------|-------------|
| `model_type` | STRING | Yes | — | `DNN_CLASSIFIER`, `DNN_REGRESSOR` | Algorithm to train. |
| `input_label_cols` | ARRAY\<STRING\> | No | `['label']` | column name(s) | Label column(s). |
| `hidden_units` | ARRAY\<INT64\> | No | single layer, auto-sized (\<=128 units) | e.g. `[128,64,32]` | Units per fully-connected hidden layer; array length = number of layers. Tunable via `HPARAM_CANDIDATES` only (`ARRAY<STRUCT<ARRAY<INT64>>>`). |
| `activation_fn` | STRING | No | `RELU` | `RELU`,`RELU6`,`CRELU`,`ELU`,`SELU`,`SIGMOID`,`TANH` | Hidden-layer activation. Tunable (`HPARAM_CANDIDATES`). |
| `optimizer` | STRING | No | `ADAM` | `ADAGRAD`,`ADAM`,`FTRL`,`RMSPROP`,`SGD` | Gradient optimizer. Tunable (`HPARAM_CANDIDATES`). |
| `learn_rate` | FLOAT64 | No | `0.001` | \>0 | Step size. Tunable (`HPARAM_RANGE`/`HPARAM_CANDIDATES`). |
| `batch_size` | INT64 | No | auto (\<=1024) | \>0 | Mini-batch size. Tunable. |
| `dropout` | FLOAT64 | No | `0` | [0,1) | Per-coordinate drop probability (regularization). Tunable. |
| `max_iterations` | INT64 | No | `20` | \>0 | Max training iterations (epochs). Tunable. |
| `early_stop` | BOOL | No | `TRUE` | TRUE/FALSE | Stop when `min_rel_progress` not met. |
| `min_rel_progress` | FLOAT64 | No | `0.01` | \>0 | Min relative loss improvement to continue when `early_stop=TRUE`. |
| `l1_reg` | FLOAT64 | No | `0` | \>=0 | L1 regularization. Tunable. |
| `l2_reg` | FLOAT64 | No | `0` | \>=0 | L2 regularization. Tunable. |
| `warm_start` | BOOL | No | `FALSE` | TRUE/FALSE | Retrain from existing weights (same feature schema). |
| `auto_class_weights` | BOOL | No | `FALSE` | TRUE/FALSE | Classifier only: balance classes by inverse frequency. |
| `class_weights` | STRUCT array | No | — | per-label weights | Classifier only: manual class weights (mutually exclusive with `auto_class_weights`). |
| `data_split_method` | STRING | No | `AUTO_SPLIT` | `AUTO_SPLIT`,`RANDOM`,`CUSTOM`,`SEQ`,`NO_SPLIT` | Train/eval split strategy. |
| `data_split_col` | STRING | No | — | column name | With `CUSTOM` (BOOL: TRUE=eval) or `SEQ`; column excluded from features. |
| `data_split_eval_fraction` | FLOAT64 | No | `0.2` | [0,1) | Eval fraction for `RANDOM`/`SEQ`. |
| `enable_global_explain` | BOOL | No | `FALSE` | TRUE/FALSE | Required to use `ML.GLOBAL_EXPLAIN`; enables Integrated Gradients attributions. |
| `integrated_gradients_num_steps` | INT64 | No | `25` | \>0 | Steps for Integrated Gradients attribution. |
| `num_trials` | INT64 | No | — | \<=100 | Enables HP tuning (max trials). |
| `max_parallel_trials` | INT64 | No | `1` | — | Trials run concurrently. |
| `hparam_tuning_algorithm` | STRING | No | `VIZIER_DEFAULT` | `VIZIER_DEFAULT`,`RANDOM_SEARCH`,`GRID_SEARCH` | Search strategy for tuning. |
| `hparam_tuning_objectives` | ARRAY\<STRING\> | No | classifier `ROC_AUC`, regressor `R2_SCORE` | metric names | Objective(s) to optimize during tuning. |
| `model_registry` | STRING | No | — | `VERTEX_AI` | Auto-register to Vertex AI Model Registry. |
| `vertex_ai_model_id` / `vertex_ai_model_version_aliases` | STRING / ARRAY\<STRING\> | No | — | — | Registry model id / version aliases. |

**Supported lifecycle functions:** `ML.EVALUATE`, `ML.PREDICT`, `ML.TRAINING_INFO`, `ML.FEATURE_INFO`, `ML.EXPLAIN_PREDICT` (local attributions), `ML.GLOBAL_EXPLAIN` (requires `enable_global_explain=TRUE`), `ML.CONFUSION_MATRIX` (classifier only), `ML.ROC_CURVE` (binary classifier only), `EXPORT MODEL` (TensorFlow SavedModel). With HP tuning: `ML.TRIAL_INFO`. NOT supported: `ML.WEIGHTS`/`ML.ADVANCED_WEIGHTS` (no coefficient weights for DNNs — use the explain functions), `ML.FEATURE_IMPORTANCE` (tree-only).

**ML.EVALUATE output metrics:**
- **DNN_CLASSIFIER:** `precision`, `recall`, `accuracy`, `f1_score`, `log_loss`, `roc_auc` (verified in [`models/dnn_classifier/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/dnn_classifier)).
- **DNN_REGRESSOR:** `mean_absolute_error`, `mean_squared_error`, `mean_squared_log_error`, `median_absolute_error`, `r2_score`, `explained_variance`.

**Preprocessing support:** Automatic (standardization of numeric features, one-hot of categoricals) happens internally; `TRANSFORM` clause IS supported and recommended for explicit feature engineering (e.g. `ML.STANDARD_SCALER`). Normalizing numeric inputs materially helps gradient-based training.

**Hyperparameter tuning:** Supported. Tunable options: `hidden_units` (HPARAM_CANDIDATES only — `ARRAY<STRUCT<ARRAY<INT64>>>`), `activation_fn`, `optimizer` (HPARAM_CANDIDATES), and `learn_rate`, `batch_size`, `dropout`, `l1_reg`, `l2_reg`, `max_iterations` (HPARAM_RANGE or HPARAM_CANDIDATES). Set `num_trials` to enable; tune objective via `hparam_tuning_objectives`.

**Explainability / weights:** `ML.EXPLAIN_PREDICT` (per-row Integrated Gradients attributions, `top_k_features` STRUCT param) and `ML.GLOBAL_EXPLAIN` (model-wide attributions; needs `enable_global_explain=TRUE`). `ML.WEIGHTS`/`ML.ADVANCED_WEIGHTS` and `ML.FEATURE_IMPORTANCE` do NOT apply.

**Best practices:**
- Set `enable_global_explain=TRUE` at train time — it cannot be added later without retraining.
- Normalize numeric features (TRANSFORM + `ML.STANDARD_SCALER`) — good general practice, but verified **not sufficient on its own** for small datasets (see the limitation below); don't assume scaling alone fixes a badly-converging small-data DNN.
- For imbalanced classification use `auto_class_weights=TRUE` (or `class_weights`); the repo fraud example trains with it FALSE and still achieves strong ROC AUC. Verified separately: even with unscaled numeric inputs and no scaling, a `DNN_CLASSIFIER` can still reach a competitive `roc_auc` — classification loss surfaces tolerate unscaled features far better than regression does.
- Training is expensive: the repo run trained ~937s over ~16.7 GB processed for `[64,32]` / 10 iterations — start small and use `early_stop`. Verified independently in `models/dnn_classifier/`/`models/dnn_regressor/`: a single `CREATE MODEL` took 12-46 minutes even on small training sets (~32K and 333 rows) — the per-iteration cost itself is small (~20-45s), so most of this is fixed DNN-worker startup overhead, not data volume.
- Wrapping `TRANSFORM` keeps preprocessing baked into `ML.PREDICT`/serving so inference matches training.
- `hidden_units` HP tuning syntax, verified working: `hidden_units = HPARAM_CANDIDATES([STRUCT([64, 32]), STRUCT([32, 16])])` — each candidate is a `STRUCT` wrapping a whole layer-sizes array.

**Limitations:**
- Exported/trained model size limit ~256 MB.
- DNN training is NOT available in all regions/multi-regions — check BigQuery ML locations.
- No coefficient weights; rely on Integrated Gradients explanations.
- `hidden_units` tuning only via `HPARAM_CANDIDATES` (not `HPARAM_RANGE`).
- `class_weights` and `auto_class_weights` are mutually exclusive and classifier-only.
- **Small datasets can silently fail to converge (verified, important):** on a 333-row regression dataset, the default `learn_rate=0.001` combined with `early_stop=TRUE` (default) caused training to stop after only **2 iterations**, producing a badly broken model (`r2_score≈-27.5`, far worse than predicting the mean) — with no error, warning, or job failure. Scaling the numeric features with `ML.STANDARD_SCALER` did **not** fix this (`r2_score` still ≈-27.4) — the binding constraint was the learn rate, not feature scale. Raising `learn_rate` well above default (0.05, i.e. 50x) plus more `max_iterations` headroom fixed it (`r2_score≈0.86`, verified reproducible bit-for-bit across separate retrains — see the `ML.TRIAL_INFO` gotcha below on why). Takeaway: always check `ML.TRAINING_INFO` for the actual iteration count on small data — if `early_stop` triggers after only 1-2 iterations, don't trust the resulting metrics without first trying a substantially higher `learn_rate`.
- **DNN training itself — not just HP tuning — reproduces bit-for-bit across separate retrains of the same model name (verified across three full runs of `models/dnn_regressor/`):** the baseline model's `ML.EVALUATE` (`r2_score = -27.351799`) and `ML.TRAINING_INFO` loss curve, the scaled+higher-learn-rate fix model's `ML.EVALUATE` (`r2_score = 0.861626`), and the tuned model's `ML.TRIAL_INFO` (identical sampled `learn_rate` values to 17 significant digits, same optimal trial) all matched exactly across independent `CREATE OR REPLACE MODEL` calls under the same name, with no explicit seed set anywhere. A separate ad-hoc validation model with a *different* name but the identical tuning search-space config (`HPARAM_RANGE(0.001, 0.1)`, `num_trials=4`) explored a completely different, worse set of `learn_rate` values (0.001-0.008) and stayed stuck at the catastrophic `r2_score≈-27` baseline. Practical implication: don't expect variation across reruns of the identical `CREATE OR REPLACE MODEL` statement under a fixed name (evaluation metrics, loss curves, and tuning trials will all reproduce) — but don't assume a result (good or bad) will transfer if you rename or duplicate the statement, since a different model name can follow a different training/search trajectory. The exact mechanism (e.g. a deterministic `AUTO_SPLIT` hash and/or a Vizier study ID derived from the model's resource path) isn't confirmed, only the practical behavior.

**Locations:** Subject to the BigQuery ML locations list for DNN training (more restricted than basic models). Confirm region support before training.

**BigFrames API:** Verified (checked the live BigFrames API reference across every `bigframes.ml` module — `linear_model`, `ensemble`, `cluster`, `decomposition`, `forecasting`, `imported`, `llm`): **no first-class DNN/neural-network class exists anywhere in `bigframes.ml`**. This is a permanent gap, not a version-specific omission. `bigframes.ml.imported.TensorFlowModel` only *serves* an already-trained external TensorFlow model — it does not train a BQML `DNN_CLASSIFIER`/`DNN_REGRESSOR`. Use the SQL `CREATE MODEL` interface directly; there is no BigFrames comparison path for this model type.

**Repo example (tested):** `bigquery-ml/models/dnn_classifier/` and `bigquery-ml/models/dnn_regressor/` — from-scratch, fully pre-validated builds on the same comparison datasets every other model type in this project uses (`census_adult_income` for the classifier, `penguins`/`body_mass_g` for the regressor), so the DNN's metrics can be read directly against the GLM, tree, and wide-and-deep results. Between them they cover `ML.TRAINING_INFO`, `ML.FEATURE_INFO`, `ML.EVALUATE`, `ML.CONFUSION_MATRIX`, `ML.ROC_CURVE`, `ML.PREDICT`, `ML.EXPLAIN_PREDICT`, `ML.GLOBAL_EXPLAIN`, `ML.FEATURE_IMPORTANCE`, `ML.ADVANCED_WEIGHTS`, and HP tuning (`ML.TRIAL_INFO`), with `auto_class_weights`, `enable_global_explain`, and an explicit `data_split_method`. For `EXPORT MODEL` (DNNs export as a TensorFlow SavedModel) and Vertex AI Endpoint serving, see `bigquery-ml/models/export/` and `bigquery-ml/models/remote/`.


---
