# `BOOSTED_TREE_CLASSIFIER` / `BOOSTED_TREE_REGRESSOR`

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#boosted_tree_classifier--boosted_tree_regressor`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#boosted_tree_classifier--boosted_tree_regressor)

- **Description:** Gradient-boosted decision tree ensembles trained with the [XGBoost](https://xgboost.readthedocs.io/) library. `BOOSTED_TREE_CLASSIFIER` handles binary and multiclass classification; `BOOSTED_TREE_REGRESSOR` handles regression. Boosting trains a sequence of trees where each tree learns the residual error of the prior ensemble. Setting `num_parallel_tree > 1` turns the model into a boosted random forest.
- **When to use:**
  - Structured/tabular data where high accuracy matters more than interpretability of a single equation.
  - Non-linear feature interactions that a linear/logistic model can't capture.
  - You want built-in per-prediction (local) and per-model (global) feature attributions for a tree model.
  - You want to export an XGBoost Booster artifact (`.bst`, or `.ubj` when trained with `xgboost_version = '2.1'`) or auto-register the model to Vertex AI for online serving.
- **Category:** supervised-classification | supervised-regression.
- **Connection required:** No for training/eval/predict. A Cloud Storage URI (not a connection) is needed only for `EXPORT MODEL`; Vertex AI registration uses `MODEL_REGISTRY`/`VERTEX_AI_MODEL_ID` options, not a connection.
- **Status:** GA.
- **documentation:** [CREATE MODEL for boosted trees](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-boosted-tree). Journey-page group: [E2E user journey](https://cloud.google.com/bigquery/docs/e2e-journey) · [ML.EVALUATE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-evaluate) · [ML.PREDICT](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-predict) · [ML.EXPLAIN_PREDICT](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-explain-predict) · [ML.GLOBAL_EXPLAIN](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-global-explain) · [ML.FEATURE_IMPORTANCE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-importance).

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
[TRANSFORM(...)]
OPTIONS(
  model_type = 'BOOSTED_TREE_CLASSIFIER',   -- or 'BOOSTED_TREE_REGRESSOR'
  input_label_cols = ['label_col'],
  booster_type = 'GBTREE',                  -- 'GBTREE' | 'DART'
  num_parallel_tree = 1,                    -- >1 => boosted random forest
  max_iterations = 30,
  tree_method = 'HIST',
  subsample = 0.85,
  early_stop = TRUE,
  min_rel_progress = 0.01,
  enable_global_explain = TRUE,
  auto_class_weights = TRUE                  -- classifier only
) AS
SELECT * EXCEPT(id_col) FROM `PROJECT_ID.DATASET.TABLE`;
```

**Options (model-specific):**

| Option | Type | Required | Default | Range / Values | Description |
|--------|------|----------|---------|----------------|-------------|
| `model_type` | STRING | Yes | — | `BOOSTED_TREE_CLASSIFIER`, `BOOSTED_TREE_REGRESSOR` | Selects classifier vs regressor. |
| `input_label_cols` | ARRAY\<STRING\> | No | `['label']` | column name(s) | Label column. Boosted trees support exactly one label column. |
| `booster_type` | STRING | No | `GBTREE` | `GBTREE`, `DART` | Booster. `HPARAM_CANDIDATES` eligible. |
| `num_parallel_tree` | INT64 | No | `1` | `>= 1` (`>=2` for forest) | Trees built per iteration; `>1` => boosted random forest. HP-tunable. |
| `dart_normalize_type` | STRING | No | `TREE` | `TREE`, `FOREST` | DART normalization; only valid when `booster_type='DART'`. Conditional HP candidate. |
| `dropout` | FLOAT64 | No | `0.0` | `[0.0, 1.0]` | DART dropout rate; only with `booster_type='DART'`. HP-tunable (conditional on DART). |
| `tree_method` | STRING | No | `AUTO` | `AUTO`, `EXACT`, `APPROX`, `HIST` | Tree construction algorithm. `AUTO` is the default (`HIST` is recommended for large data — fastest). |
| `max_iterations` | INT64 | No | `20` | `>= 1` | Max boosting rounds. HP-tunable (`HPARAM_RANGE`). |
| `max_tree_depth` | INT64 | No | `6` | `>= 1` | Max depth per tree. HP-tunable. |
| `min_tree_child_weight` | INT64 | No | `1` | `>= 0` | Min sum of instance weight in a child. HP-tunable. |
| `min_split_loss` | FLOAT64 | No | `0.0` | `>= 0` | Min loss reduction to split (gamma). HP-tunable. |
| `subsample` | FLOAT64 | No | `1.0` | `(0, 1]` | Row subsample ratio per tree. HP-tunable. |
| `colsample_bytree` | FLOAT64 | No | `1.0` | `(0, 1]` | Column subsample per tree. HP-tunable. |
| `colsample_bylevel` | FLOAT64 | No | `1.0` | `(0, 1]` | Column subsample per level. HP-tunable. |
| `colsample_bynode` | FLOAT64 | No | `1.0` | `(0, 1]` | Column subsample per node. HP-tunable. |
| `learn_rate` | FLOAT64 | No | `0.3` | `[0, 1]` | Boosting shrinkage/step size. HP-tunable. |
| `l1_reg` | FLOAT64 | No | `0.0` | `>= 0` | L1 regularization. HP-tunable. |
| `l2_reg` | FLOAT64 | No | `1.0` | `>= 0` | L2 regularization. HP-tunable. |
| `early_stop` | BOOL | No | `TRUE` | `TRUE`/`FALSE` | Stop when `min_rel_progress` not met. |
| `min_rel_progress` | FLOAT64 | No | `0.01` | `>= 0` | Min relative loss improvement to continue when `early_stop=TRUE`. |
| `auto_class_weights` | BOOL | No | `FALSE` | `TRUE`/`FALSE` | Classifier only. Balance class weights inversely to frequency (useful for imbalanced data). |
| `class_weights` | ARRAY\<STRUCT\<STRING,FLOAT64\>\> | No | — | per-class weights | Classifier only. Mutually exclusive with `auto_class_weights`. |
| `instance_weight_col` | STRING | No | — | column name | Per-row weight column. |
| `enable_global_explain` | BOOL | No | `FALSE` | `TRUE`/`FALSE` | Must be `TRUE` at training time to use `ML.GLOBAL_EXPLAIN`. |
| `approx_global_feature_contrib` | BOOL | No | TRUE when `enable_global_explain`=TRUE and `num_parallel_tree`\>=10, else FALSE | `TRUE`/`FALSE` | Use fast approximate global feature contributions (XGBoost passthrough); relevant for boosted random forests (`num_parallel_tree`\>1). |
| `xgboost_version` | STRING | No | `0.9` | `0.9`, `1.1`, `2.1` | XGBoost library version used for training. `2.1` added 2026-08-27. **The default is still `0.9`** — a 2019 release — and it is what you get when you omit the option (verified: the option comes back as `xgboostVersion: "0.9"` in a model's training options even when never specified). The value list above is the error message's own enumeration, read back by passing an unsupported value. This option changes the `EXPORT MODEL` artifact — see the [EXPORT MODEL](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-management-monitoring.md#export-model) gotchas. **It also costs you `ML.TRAINING_INFO`:** at `'2.1'`, that function returns zero rows once training runs more than 10 iterations (measured; see the [`ML.TRAINING_INFO` gotcha](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mltraining_info)). Every other lifecycle function is unaffected. |
| `data_split_method` | STRING | No | `AUTO_SPLIT` | `AUTO_SPLIT`, `RANDOM`, `CUSTOM`, `SEQ`, `NO_SPLIT` | How to split train/eval data. |
| `data_split_col` | STRING | No | — | column name | With `CUSTOM`: `TRUE` rows => eval, `FALSE` => train. With `SEQ`: ordering column. |
| `num_trials` | INT64 | No | — | `1`–`100` | Enables hyperparameter tuning; total trials to run. |
| `max_parallel_trials` | INT64 | No | `1` | `1`–`5` | Concurrent tuning trials. |
| `hparam_tuning_objectives` | ARRAY\<STRING\> | No | type default | e.g. `ROC_AUC`, `R2_SCORE` | Metric(s) optimized during tuning. |
| `model_registry` | STRING | No | — | `VERTEX_AI` | Auto-register trained model to Vertex AI Model Registry. |
| `vertex_ai_model_id` / `vertex_ai_model_version_aliases` | STRING / ARRAY | No | — | — | Vertex AI model id and version aliases. |

(HP-tuning-eligible options accept `HPARAM_RANGE(min, max)` for numeric ranges or `HPARAM_CANDIDATES([...])` for discrete sets; `dart_normalize_type`/`dropout` are conditional on `booster_type` candidates including `DART`.)

**Supported lifecycle functions:** `ML.EVALUATE`, `ML.PREDICT`, `ML.EXPLAIN_PREDICT`, `ML.GLOBAL_EXPLAIN`, `ML.FEATURE_IMPORTANCE`, `ML.FEATURE_INFO`, `ML.TRAINING_INFO`, `EXPORT MODEL`. Classifier additionally: `ML.CONFUSION_MATRIX` and (binary) `ML.ROC_CURVE`. With `num_trials`: `ML.TRIAL_INFO`. Note: `ML.WEIGHTS`/`ML.ADVANCED_WEIGHTS` do **not** apply (tree models have no linear coefficients — use `ML.FEATURE_IMPORTANCE` instead).

**ML.EVALUATE output metrics (this type):**
- Classifier: `precision`, `recall`, `accuracy`, `f1_score`, `log_loss`, `roc_auc`.
- Regressor: `mean_absolute_error`, `mean_squared_error`, `mean_squared_log_error`, `median_absolute_error`, `r2_score`, `explained_variance`.

**Preprocessing support:** automatic by default; manual via the `TRANSFORM` clause (e.g. `ML.LABEL_ENCODER`, `ML.STANDARD_SCALER`, `ML.MIN_MAX_SCALER`, `ML.ROBUST_SCALER`, `ML.MAX_ABS_SCALER`, plus `EXTRACT()` on dates). `TRANSFORM` logic travels with the exported/registered model (preventing training-serving skew).

**Hyperparameter tuning:** Supported. Set `num_trials` (and optionally `max_parallel_trials`, `hparam_tuning_objectives`). Tunable options include `learn_rate`, `max_tree_depth`, `subsample`, `colsample_bytree`/`bylevel`/`bynode`, `min_split_loss`, `min_tree_child_weight`, `l1_reg`, `l2_reg`, `max_iterations`, `num_parallel_tree`, `booster_type`, and (conditional on DART) `dart_normalize_type`/`dropout`.

**Explainability / weights:** `ML.EXPLAIN_PREDICT` (local, per-row top feature attributions — tree SHAP based), `ML.GLOBAL_EXPLAIN` (requires `enable_global_explain=TRUE` at training), and `ML.FEATURE_IMPORTANCE` (XGBoost `importance_weight`/`importance_gain`/`importance_cover`). `ML.WEIGHTS`/`ML.ADVANCED_WEIGHTS` are N/A.

**Best practices:**
- Use `tree_method='HIST'` for large datasets (much faster).
- For imbalanced classification set `auto_class_weights=TRUE` (the fraud notebook uses it on a ~0.17% positive class).
- Keep `early_stop=TRUE` with a sensible `min_rel_progress` to avoid over-training and wasted slots.
- Set `enable_global_explain=TRUE` at training if you'll need global attributions — it can't be added afterward.
- Watch cost: boosted-tree training scans/processes data per iteration (the fraud run processed ~16.8 GB); HP tuning multiplies this by `num_trials`.

**Limitations:**
- Exactly one label column; no multi-label.
- `ML.WEIGHTS`/`ML.ADVANCED_WEIGHTS` unavailable (no linear coefficients).
- DART-only options (`dart_normalize_type`, `dropout`) are ignored unless `booster_type='DART'`.
- Training is not available in every region — see Locations.
- **GOTCHA (verified):** a single `BOOSTED_TREE_REGRESSOR` model trains in **~2.5–4.5 minutes even on a training table with fewer than 1,000 rows** — a large, fixed overhead compared to `LINEAR_REG` on the same data (~15 seconds). Verified directly this is not something tunable away: lowering `max_iterations` and setting `early_stop=FALSE` made a model take *longer*, not shorter, and training the identical model under a temporary BigQuery Editions autoscale reservation made no measurable difference (the job's own query plan showed it actively consuming slot-time throughout, not queued waiting for capacity). Appears to be a fixed cost of this model type's training path in BigQuery ML. Matters most for any workflow that trains many small `BOOSTED_TREE_REGRESSOR` models in a loop (e.g. one per forecast horizon day) — see `workflows/regression_based_forecasting/`, which works around it by submitting distinctly-named `CREATE MODEL` jobs concurrently (verified live: BigQuery runs them in true parallel from one client, so a batch finishes in roughly one model's training time, not the sum).
- **This fixed overhead is a floor, not a ceiling — real training time still scales with data/feature size once both grow substantially.** Verified with `BOOSTED_TREE_CLASSIFIER` on a genuinely large table (~1M rows, up to 771 features including two `ARRAY<FLOAT64>` embedding columns): training took **19–40 minutes per model**, not the ~270s floor seen on trivial data. Three models submitted concurrently still finished in the time of the slowest one (~40 min), not the sum (~75 min) — see `workflows/embeddings_classification/`.
- **`ARRAY<FLOAT64>` columns can be passed directly to `CREATE MODEL` as feature columns for `BOOSTED_TREE_CLASSIFIER`/`REGRESSOR`** — verified live; no need to unnest an embedding vector into individual `col_0, col_1, ...` columns first. `ML.FEATURE_INFO` reports a `dimension` value for these columns. Confirmed at 256- and 512-dimension embedding columns in `workflows/embeddings_classification/`. (Elementwise arithmetic between two same-length arrays, e.g. an absolute-difference feature, still has no native operator — compute it via `UNNEST(a) WITH OFFSET` joined to `UNNEST(b) WITH OFFSET` on position, reaggregated with `ARRAY(...)`.)

**Locations:** Boosted-tree training is not supported in all BigQuery ML regions/multi-regions; check the [BigQuery ML locations](https://cloud.google.com/bigquery/docs/locations) list. Vertex AI registration defaults to the region matching the BQ location (e.g. `EU` multi-region maps to `europe-west4`).

**BigFrames API:** `bigframes.ml.ensemble.XGBClassifier` / `bigframes.ml.ensemble.XGBRegressor` — `model = XGBClassifier(); model.fit(X, y); model.predict(X)`. **Verified: the constructor has no `class_weight`/`auto_class_weights` parameter** (checked the installed signature directly — `n_estimators`, `booster`, `max_depth`, `learning_rate`, `reg_alpha`/`reg_lambda`, etc., but no class-weighting option), unlike `bigframes.ml.linear_model.LogisticRegression` which exposes sklearn-style `class_weight`. A BigFrames `XGBClassifier` trained on an imbalanced label with no manual reweighting will not match a SQL `BOOSTED_TREE_CLASSIFIER` trained with `auto_class_weights = TRUE` — expect higher precision / lower recall from the unweighted BigFrames model, not a bug.

**Repo example (tested):**
- `bigquery-ml/models/boosted_tree_classifier/boosted_tree_classifier.sql` + notebook — `BOOSTED_TREE_CLASSIFIER` on `census_adult_income` (same data/label as `models/logistic_regression/`, for direct technique comparison), with the full lifecycle incl. the tree-visualization step (`EXPORT MODEL` → `xgboost.plot_tree()`).
- `bigquery-ml/models/boosted_tree_regressor/boosted_tree_regressor.sql` + notebook — `BOOSTED_TREE_REGRESSOR` on `penguins`/`body_mass_g` (same data/label as `models/linear_regression/`); `r2_score` 0.983 vs. `RANDOM_FOREST_REGRESSOR`'s 0.922 and linear regression's 0.875 on identical data. `TRANSFORM` uses `ML.LABEL_ENCODER`. Same tree-visualization step; the `reg:linear` deprecation warning on load is a `0.9`-era artifact and is gone at `xgboost_version = '2.1'` (see gotcha above).
- `bigquery-ml/workflows/regression_based_forecasting/regression_based_forecasting.ipynb` — 28 `BOOSTED_TREE_REGRESSOR` models (one per forecast horizon day, direct multi-step forecasting) trained concurrently in batches to work around the per-model training-time GOTCHA above; got the best MAPE of any technique in that notebook's comparison, including the `ARIMA_PLUS` reference, despite a worse MAE/RMSE.
- `bigquery-ml/workflows/embeddings_classification/embeddings_classification.ipynb` — 3 `BOOSTED_TREE_CLASSIFIER` models trained on a ~1M-row (product × hierarchy-node) table with `AI.EMBED`-generated 256-dim embeddings passed as `ARRAY<FLOAT64>` feature columns directly (verified: no unnesting needed); demonstrates the real-data-scale training-time finding above (19-40 min/model, not the ~270s trivial-data floor) and that raw `ML.EVALUATE` metrics don't always rank models the same way as an applied top-1 resolution accuracy computed via `ML.PREDICT` + `UNNEST`/`QUALIFY`. Also includes two baselines that outperform this whole pairwise approach: a direct multiclass `BOOSTED_TREE_CLASSIFIER` (no cross-join, trains in minutes not tens of minutes, ~69-70% category accuracy vs. the pairwise approach's ~42-48%) and a zero-training `VECTOR_SEARCH` lookup (~52% category accuracy) — **verified `VECTOR_SEARCH` needs no vector index at small scale (38 hierarchy nodes)**, it silently falls back to an exact brute-force scan; a two-stage hierarchical resolution pattern (nearest department first, then nearest category filtered to that department's children via `WHERE base.hierarchy_node_parent = query.pred_department`) mirrors the `ML.PREDICT`-based resolution used for the classifiers, but with zero training cost. A real gotcha hit while building this: `top_k` on the second-stage `VECTOR_SEARCH` call must cover *all* candidate nodes (not just a small top-k like 5), since filtering by parent happens *after* `top_k` truncation — a small `top_k` can silently drop products whose true category isn't among the globally-nearest few before the parent filter ever runs.
- `bigquery-ml/workflows/anomaly_fraud_detection/anomaly_fraud_detection.ipynb` — `BOOSTED_TREE_CLASSIFIER` with `auto_class_weights` on genuinely imbalanced data (`bigquery-public-data.ml_datasets.ulb_fraud_detection`, 492 fraud cases), the setting that option exists for; scored against the unsupervised `PCA` and `AUTOENCODER` detectors on the same table.
- `bigquery-ml/models/export/export.sql` — `EXPORT MODEL` on a `BOOSTED_TREE_CLASSIFIER`, which exports as an XGBoost Booster (`model.bst`) rather than the TensorFlow SavedModel the GLMs/DNNs produce; `bigquery-ml/models/remote/` then deploys to a Vertex AI Endpoint. Note that when the model carries a `TRANSFORM` clause the preprocessing travels with it, landing beside the model as a separate `/model/transform` artifact so the exported model reapplies it at serving time.


---
