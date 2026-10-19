# `RANDOM_FOREST_CLASSIFIER` / `RANDOM_FOREST_REGRESSOR`

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#random_forest_classifier--random_forest_regressor`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#random_forest_classifier--random_forest_regressor)

- **Description:** Bagged ensemble of decision trees, trained with the XGBoost library (a "boosted random forest": `num_parallel_tree` trees built in parallel per iteration, on row + column subsamples drawn with replacement). `RANDOM_FOREST_CLASSIFIER` predicts a categorical label (binary or multiclass); `RANDOM_FOREST_REGRESSOR` predicts a numeric value. Distinct from `BOOSTED_TREE_*` (which sequentially boosts) — random forest sets `num_parallel_tree >= 2` and trains a single iteration.
- **When to use:**
  - Tabular classification/regression where you want a robust, low-tuning ensemble that resists overfitting via bagging.
  - When you need built-in feature attributions (`ML.GLOBAL_EXPLAIN`, `ML.EXPLAIN_PREDICT`) and XGBoost feature importances.
  - Mixed numeric + categorical features with automatic preprocessing, or custom preprocessing via `TRANSFORM`.
  - As a variance-reduction alternative to a single tree or to `BOOSTED_TREE_*` when boosting overfits.
- **Category:** supervised-classification | supervised-regression.
- **Connection required:** No. (A Cloud connection is only needed for the optional `MODEL_REGISTRY = 'VERTEX_AI'` registration / online serving step, not for training, evaluation, or `ML.PREDICT`.)
- **Status:** GA.
- **documentation:** [CREATE MODEL for random forest models](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-random-forest) · related: [boosted tree CREATE MODEL](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-boosted-tree) (shared XGBoost option set) · [XAI overview](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-xai-overview) · [HP tuning overview](https://cloud.google.com/bigquery/docs/hp-tuning-overview)

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
[TRANSFORM(
  ML.STANDARD_SCALER(feature1) OVER() AS feature1,
  ML.IMPUTER(cat_feature, 'most_frequent') OVER() AS cat_feature,
  label_col
)]
OPTIONS(
  model_type = 'RANDOM_FOREST_CLASSIFIER',   -- or 'RANDOM_FOREST_REGRESSOR'
  input_label_cols = ['label_col'],
  num_parallel_tree = 100,                    -- >= 2 for random forest
  tree_method = 'HIST',
  subsample = 0.85,
  colsample_bytree = 0.9,
  auto_class_weights = TRUE,                  -- classifier only
  enable_global_explain = TRUE,
  data_split_method = 'AUTO_SPLIT'
) AS
SELECT * EXCEPT(id_col)
FROM `PROJECT_ID.DATASET.TRAINING_TABLE`;
```

**Options (model-specific):**

| Option | Type | Required | Default | Range / Values | Description |
|--------|------|----------|---------|----------------|-------------|
| `model_type` | STRING | Yes | — | `RANDOM_FOREST_CLASSIFIER`, `RANDOM_FOREST_REGRESSOR` | Selects classification vs regression. |
| `input_label_cols` | ARRAY\<STRING\> | No | `['label']` | column name(s) | Label column(s) in the training query. |
| `num_parallel_tree` | INT64 | No | 100 | \>= 2 (or `HPARAM_RANGE`/`HPARAM_CANDIDATES`) | Trees built in parallel per iteration; this is what makes it a forest. |
| `tree_method` | STRING | No | `AUTO` | `AUTO`, `EXACT`, `APPROX`, `HIST` | XGBoost split-finding algorithm; `HIST` is fastest on large data. |
| `subsample` | FLOAT64 | No | 0.8 (RF) | (0, 1.0] (or HP range) | Row subsample ratio per tree (bagging). |
| `colsample_bytree` | FLOAT64 | No | 1.0 | [0, 1.0] (or HP range) | Column subsample ratio per tree. |
| `colsample_bylevel` | FLOAT64 | No | 1.0 | [0, 1.0] (or HP range) | Column subsample ratio per depth level. |
| `colsample_bynode` | FLOAT64 | No | 0.8 (RF) | [0, 1.0] (or HP range) | Column subsample ratio per split node. |
| `max_tree_depth` | INT64 | No | 6 | (or `HPARAM_RANGE`/`HPARAM_CANDIDATES`) | Max depth of each tree. |
| `min_tree_child_weight` | INT64 | No | 1 | \>= 0 (or HP) | Min sum of instance weight in a child to keep splitting. |
| `min_split_loss` | FLOAT64 | No | 0 | \>= 0 (or HP) | Min loss reduction (gamma) required to split. |
| `l1_reg` | FLOAT64 | No | 0 | \>= 0 (or HP) | L1 regularization on weights. |
| `l2_reg` | FLOAT64 | No | 1.0 | \>= 0 (or HP) | L2 regularization on weights. |
| `auto_class_weights` | BOOL | No | FALSE | TRUE / FALSE | Classifier only: balance classes by inverse frequency. |
| `class_weights` | ARRAY\<STRUCT\<STRING,FLOAT64\>\> | No | — | per-class weights | Classifier only; mutually exclusive with `auto_class_weights`. |
| `instance_weight_col` | STRING | No | — | column name | Per-row weight column. |
| `enable_global_explain` | BOOL | No | FALSE | TRUE / FALSE | Required to use `ML.GLOBAL_EXPLAIN` / `ML.EXPLAIN_PREDICT`. |
| `approx_global_feature_contrib` | BOOL | No | TRUE when `enable_global_explain`=TRUE and `num_parallel_tree`\>=10, else FALSE | TRUE / FALSE | Fast approximate feature contributions (XGBoost passthrough). |
| `category_encoding_method` | STRING | No | `LABEL_ENCODING` | `LABEL_ENCODING`, `DUMMY_ENCODING` | Encoding for non-numeric features. |
| `xgboost_version` | STRING | No | `0.9` | `0.9`, `1.1`, `2.1` | XGBoost library version used for training — random forests accept it on the same terms as `BOOSTED_TREE_*` (verified live on both `RANDOM_FOREST_CLASSIFIER` and `RANDOM_FOREST_REGRESSOR`; the default reads back as `0.9`). Changes the `EXPORT MODEL` artifact — see the [`BOOSTED_TREE_*` entry](boosted_tree_classifier-boosted_tree_regressor.md) and the [EXPORT MODEL](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-management-monitoring.md#export-model) gotchas. Unlike `BOOSTED_TREE_*`, random forests pay no `ML.TRAINING_INFO` penalty for `'2.1'` — training is single-pass, so it never crosses the 10-iteration boundary where that function goes empty (measured; see the [`ML.TRAINING_INFO` gotcha](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mltraining_info)). |
| `data_split_method` | STRING | No | `AUTO_SPLIT` | `AUTO_SPLIT`, `RANDOM`, `CUSTOM`, `SEQ`, `NO_SPLIT` | How eval data is held out. |
| `data_split_col` | STRING | No | — | column name | With `CUSTOM`: BOOL col (TRUE=eval); with `SEQ`: ordering col. |
| `data_split_eval_fraction` | FLOAT64 | No | 0.2 | [0, 1.0] | Eval fraction for `RANDOM`/`SEQ`. |
| `early_stop` | BOOL | No | TRUE | TRUE / FALSE | Stop early on small relative progress. |
| `min_rel_progress` | FLOAT64 | No | 0.01 | \>= 0 | Min relative loss improvement when `early_stop`=TRUE. |
| `num_trials` | INT64 | No | — | \>= 1 | Enables hyperparameter tuning (number of trials). |
| `model_registry` | STRING | No | — | `VERTEX_AI` | Register the trained model in Vertex AI Model Registry. |

(HP-tuning-eligible options accept `HPARAM_RANGE(min, max)` or `HPARAM_CANDIDATES([...])`: `num_parallel_tree`, `tree_method`, `subsample`, `colsample_bytree`/`bylevel`/`bynode`, `max_tree_depth`, `min_tree_child_weight`, `min_split_loss`, `l1_reg`, `l2_reg`.)

**Supported lifecycle functions:** `ML.PREDICT`, `ML.EVALUATE`, `ML.CONFUSION_MATRIX` (classifier), `ML.ROC_CURVE` (binary classifier), `ML.EXPLAIN_PREDICT` (needs `enable_global_explain`), `ML.GLOBAL_EXPLAIN` (needs `enable_global_explain`), `ML.FEATURE_IMPORTANCE`, `ML.FEATURE_INFO`, `ML.TRAINING_INFO`, `ML.TRIAL_INFO` (when `num_trials` set), `EXPORT MODEL`, `ALTER MODEL`, `ML.VALIDATE_DATA_SKEW` / `ML.VALIDATE_DATA_DRIFT` (monitoring). Note: `ML.WEIGHTS` / `ML.ADVANCED_WEIGHTS` do **not** apply (tree model, not linear) — use `ML.FEATURE_IMPORTANCE` / `ML.GLOBAL_EXPLAIN` instead.

**ML.EVALUATE output metrics (this type):**
- Classifier: `precision`, `recall`, `accuracy`, `f1_score`, `log_loss`, `roc_auc`.
- Regressor: `mean_absolute_error`, `mean_squared_error`, `mean_squared_log_error`, `median_absolute_error`, `r2_score`, `explained_variance`.

**Preprocessing support:** automatic (BQML auto-preprocessing for numeric + categorical) | manual | `TRANSFORM` supported (preprocessing baked into the model so it is reapplied at predict time — see monitoring SQL example using `ML.ROBUST_SCALER`, `ML.STANDARD_SCALER`, `ML.QUANTILE_BUCKETIZE`, `ML.IMPUTER`).

**Hyperparameter tuning:** Supported. Set `num_trials` (and optionally `max_parallel_trials`, `hparam_tuning_algorithm`, `hparam_tuning_objectives`). Tunable options listed above. Default tuning objective: `roc_auc` (classifier), `r2_score` (regressor). Inspect trials with `ML.TRIAL_INFO`.

**Explainability / weights:** `ML.GLOBAL_EXPLAIN` (global feature attributions) and `ML.EXPLAIN_PREDICT` (per-row attributions) — both require `enable_global_explain = TRUE` at training time. `ML.FEATURE_IMPORTANCE` returns XGBoost `importance_weight` (split count), `importance_gain` (accuracy gain), `importance_cover` (rows covered) and needs no special option. `ML.WEIGHTS` / `ML.ADVANCED_WEIGHTS` are N/A for tree models.

**Best practices:**
- With `enable_global_explain=TRUE`, forests of `num_parallel_tree` >= 10 automatically use fast approximate global feature contributions (`approx_global_feature_contrib`); larger forests reduce variance at higher train cost/time.
- Use `tree_method = 'HIST'` for large tables (the repo fraud example trained 200 trees on ~9.4 GB in ~25 min).
- For imbalanced classification (e.g. fraud), set `auto_class_weights = TRUE`.
- Use `subsample` + `colsample_*` < 1.0 to strengthen bagging and generalization.
- Bake preprocessing into `TRANSFORM` so serving and monitoring reuse identical logic.
- **For tree visualization (`EXPORT MODEL` → `xgboost.plot_tree()`), train a small, separate illustrative forest** (e.g. `num_parallel_tree=10`, `max_tree_depth=3`) rather than trying to render a tree from your full-power model — see the limitation below.
- **Set `xgboost_version = '2.1'` explicitly on any random forest.** The default is `0.9`, and on the regressor that default measurably under-grows the forest — see the limitation below. At `2.1`, `RANDOM_FOREST_REGRESSOR` on `penguins`/`body_mass_g` (333 rows) reaches `r2_score` ≈ 0.922, against `BOOSTED_TREE_REGRESSOR`'s ≈ 0.983 and `LINEAR_REG`'s ≈ 0.875 on identical data — second of the three, and it gets there untuned (the best of six tuning trials, ≈ 0.917, did not beat the default). Boosting still leads on this data; the margin is narrow, not the wide gap the `0.9` default suggests.

**Limitations:**
- Random forest training is **not available in all regions** — check BigQuery ML locations before choosing a dataset region.
- `ML.WEIGHTS` does not apply (no linear coefficients).
- Explainability functions require `enable_global_explain = TRUE` set at training; cannot be added afterward without retraining.
- `ML.ROC_CURVE` is binary-classification only.
- **Verified: `max_iterations` is not a valid option for `RANDOM_FOREST_CLASSIFIER`/`RANDOM_FOREST_REGRESSOR` at all** — `CREATE MODEL` errors immediately with `Option(s) MAX_ITERATIONS are not supported for RANDOM_FOREST_* model training` if you set it (unlike `BOOSTED_TREE_*`, where `max_iterations` is a central hyperparameter). This is a hard API-level guarantee that random forest training is single-pass, not just a documented convention — there is no way to accidentally train a "boosted random forest" via this option; `num_parallel_tree` alone defines the forest. Confirmed by `ML.TRAINING_INFO`: always exactly one row (`iteration = 1`), `learning_rate = 1.0`.
- **Verified gotcha — trees are too dense to visualize at default settings.** Unlike a `BOOSTED_TREE_*` tree (a shallow stage fit on residuals), *every* `RANDOM_FOREST_*` tree is a complete, independently-trained tree. A default-settings forest's tree 0 (`num_parallel_tree=50`, `max_tree_depth=6`) had 2,435 dump lines and depth 15 — `xgboost.plot_tree()` triggers `graph is too large for cairo-renderer bitmaps` and produces an illegible image (confirmed even with SVG output, which sidesteps the bitmap-size limit but is still too dense to read at a glance). Fix: train a dedicated shallow illustrative forest for the diagram only (see best practices above).
- **GOTCHA (measured, undocumented): `RANDOM_FOREST_REGRESSOR` accuracy jumps sharply at `xgboost_version = '2.1'`.** Single-variable sweep on `penguins`/`body_mass_g` (333 rows, `num_parallel_tree = 50`, `tree_method = 'HIST'`, `AUTO_SPLIT`, nothing else changed):

  | `xgboost_version` | `r2_score` | summed `importance_weight` (all 6 features) |
  |---|---|---|
  | `0.9` (default) | 0.7314, 0.7413 | 82 splits |
  | `1.1` | 0.7442 | — |
  | `2.1` | 0.9212, 0.9207 | 2,482 splits |

  The split count is the mechanism signature: at the `0.9` default the forest is drastically under-grown, and at that size two of the six features (`island`, `culmen_length_mm`) come back at exactly **zero** `ML.FEATURE_IMPORTANCE`/`ML.GLOBAL_EXPLAIN` — at `2.1` every feature is non-zero (`island` lowest at `importance_weight` 245). Hyperparameter tuning does not close the gap at `0.9` (best tuned trial ≈ 0.755); at `2.1` all six trials land ≈ 0.907–0.917. `RANDOM_FOREST_CLASSIFIER` shows no comparable shift (`roc_auc` 0.883998 at `0.9` vs. 0.884439 at `2.1`), nor does `BOOSTED_TREE_CLASSIFIER` (0.888965 vs. 0.888313). Treat any zero-importance feature on a `0.9` random forest as a symptom of an under-grown forest, not as evidence the feature carries no signal.
- **Verified: retraining an identical `RANDOM_FOREST_*` model (same query, same options) is genuinely non-deterministic** — unlike `BOOSTED_TREE_*` (which reproduced predictions/loss curves essentially bit-for-bit across separate runs in testing, since it doesn't subsample by default), random forest always bags row/column subsamples (`subsample`/`colsample_bynode` default to 0.8, not 1.0), and there is no exposed random seed. Observed on `penguins`: two separate trainings of the same `RANDOM_FOREST_REGRESSOR` config produced visibly different tree structures, predictions, and `ML.GLOBAL_EXPLAIN` rankings (though `r2_score` stayed in a similar range within a fixed `xgboost_version` — ~0.73–0.75 at the `0.9` default, ~0.921 at `2.1`). Don't expect exact reproducibility run-to-run the way GLMs or boosted trees (mostly) provide.

**Locations:** Subject to region restrictions (random forest not supported in every BQML region/multi-region); see [BigQuery ML locations](https://cloud.google.com/bigquery/docs/locations).

**BigFrames API:** `bigframes.ml.ensemble.RandomForestClassifier` / `bigframes.ml.ensemble.RandomForestRegressor` — `.fit(X, y)` / `.predict()` / `.score()`; integrates with `bigframes.ml.pipeline` for TRANSFORM-equivalent preprocessing. **Verified: `RandomForestClassifier` has no `class_weight`/`auto_class_weights` parameter** (checked the installed signature directly — same gap as `XGBClassifier`), unlike `LogisticRegression`. A BigFrames comparison against a SQL model trained with `auto_class_weights = TRUE` is not apples-to-apples.

**Repo example (tested):**
- `bigquery-ml/models/random_forest_classifier/random_forest_classifier.sql` + notebook — `RANDOM_FOREST_CLASSIFIER` on `census_adult_income` (same data/label as `logistic_regression`/`boosted_tree_classifier`, for a three-way technique comparison), incl. a dedicated shallow illustrative forest for tree visualization.
- `bigquery-ml/models/random_forest_regressor/random_forest_regressor.sql` + notebook — `RANDOM_FOREST_REGRESSOR` on `penguins`/`body_mass_g` (same data/label as `linear_regression`/`boosted_tree_regressor`); the `xgboost_version` sensitivity (`r2_score` ≈ 0.92 at `2.1` vs. ≈ 0.74 at the `0.9` default, 2,482 vs. 82 splits) is measured and discussed directly in the notebook.
- `bigquery-ml/workflows/ensembling/ensembling.sql` — `RANDOM_FOREST_CLASSIFIER` as one of three base learners (with `LOGISTIC_REG` and `BOOSTED_TREE_CLASSIFIER`) on the same `census_adult_income` data, so the forest's standalone metrics above can be read against its contribution in an ensemble.
- To put a tree ensemble behind a monitoring/retraining loop: `bigquery-ml/functions/model_monitoring/` covers `ML.VALIDATE_DATA_SKEW` and `ML.VALIDATE_DATA_DRIFT` against a training baseline, and `bigquery-ml/pipelines/sql_scripting/` wires drift-check → conditional `CREATE OR REPLACE MODEL` → `ML.EVALUATE` into a single scheduled script (on a `BOOSTED_TREE_CLASSIFIER`; the pattern is model-type-agnostic).


---
