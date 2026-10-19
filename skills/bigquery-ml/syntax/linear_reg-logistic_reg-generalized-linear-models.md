# `LINEAR_REG` / `LOGISTIC_REG`  (Generalized Linear Models)

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#linear_reg--logistic_reg--generalized-linear-models`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#linear_reg--logistic_reg--generalized-linear-models)

- **Description:** BigQuery ML's generalized linear models. `LINEAR_REG` fits a linear-regression model for predicting a continuous numeric label. `LOGISTIC_REG` fits a logistic-regression model that estimates class probabilities (via the logit / log-odds link) for **binary or multiclass** classification. Both share one `CREATE MODEL` reference page because they are the same GLM family with different link functions.
- **When to use:**
  - Fast, interpretable baseline before reaching for trees/AutoML — weights and p-values are directly readable.
  - `LINEAR_REG`: continuous targets (revenue, weight, demand). Also the workhorse for **regression-based forecasting** (lagged-feature design matrix).
  - `LOGISTIC_REG`: yes/no, churn, fraud, multiclass labels; need calibrated class probabilities.
  - Wide, mostly-linear feature relationships; when explainability/statistical inference (standard errors, p-values) matters.
- **Category:** supervised-regression (`LINEAR_REG`) | supervised-classification (`LOGISTIC_REG`).
- **Connection required:** No. (A connection is only needed for the optional `EXPORT MODEL` to GCS or remote/imported models — not for GLM training.)
- **Status:** GA.
- **documentation:** [CREATE MODEL for GLMs](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-glm) · journey links: [ML.EVALUATE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-evaluate), [ML.PREDICT](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-predict), [ML.WEIGHTS](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-weights), [ML.ADVANCED_WEIGHTS](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-advanced-weights), [ML.GLOBAL_EXPLAIN](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-global-explain), [ML.EXPLAIN_PREDICT](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-explain-predict), [ML.CONFUSION_MATRIX](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-confusion), [ML.ROC_CURVE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-roc), [HP tuning](https://cloud.google.com/bigquery/docs/hp-tuning-overview).

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
[TRANSFORM(...)]
OPTIONS(
  model_type = 'LOGISTIC_REG',          -- or 'LINEAR_REG'
  input_label_cols = ['label_col'],
  auto_class_weights = TRUE,            -- LOGISTIC_REG only; balances classes
  calculate_p_values = TRUE,           -- enables ML.ADVANCED_WEIGHTS (see gotchas)
  category_encoding_method = 'DUMMY_ENCODING',
  enable_global_explain = TRUE,        -- required for ML.GLOBAL_EXPLAIN
  data_split_method = 'AUTO_SPLIT'
) AS
SELECT feature1, feature2, ..., label_col
FROM `PROJECT_ID.DATASET.training_table`;
```

**Options (model-specific):**

| Option | Type | Required | Default | Range / Values | Description |
|--------|------|----------|---------|----------------|-------------|
| `model_type` | STRING | Yes | — | `LINEAR_REG`, `LOGISTIC_REG` | Selects the GLM family. |
| `input_label_cols` | ARRAY\<STRING\> | No | `['label']` | column name(s) | Label column. If absent, a column named `label` must exist. |
| `optimize_strategy` | STRING | No | `AUTO_STRATEGY` | `AUTO_STRATEGY`, `BATCH_GRADIENT_DESCENT`, `NORMAL_EQUATION` | Training solver. AUTO picks NORMAL_EQUATION for small/unregularized problems, else BATCH_GRADIENT_DESCENT (e.g. when `l1_reg` set, `warm_start`=TRUE, feature cardinality \> 10,000, or over-fitting risk). |
| `l1_reg` | FLOAT64 | No | `0` (none) | \>= 0 | L1 regularization. **Tunable** (`HPARAM_RANGE`/`HPARAM_CANDIDATES`). |
| `l2_reg` | FLOAT64 | No | `0` (none) | \>= 0 | L2 regularization. **Tunable**. |
| `max_iterations` | INT64 | No | `20` | \>= 1 | Max gradient-descent steps. **Tunable**. |
| `learn_rate_strategy` | STRING | No | `LINE_SEARCH` | `LINE_SEARCH`, `CONSTANT` | How learning rate is set (gradient descent only). **Tunable**. |
| `learn_rate` | FLOAT64 | No | `0.1` | \> 0 | Used when strategy is `CONSTANT`. **Tunable**. |
| `ls_init_learn_rate` | FLOAT64 | No | `0.1` | \> 0 | Initial rate for `LINE_SEARCH`. **Tunable**. |
| `early_stop` | BOOL | No | `TRUE` | TRUE/FALSE | Stop when improvement \< `min_rel_progress`. |
| `min_rel_progress` | FLOAT64 | No | `0.01` | \> 0 | Min relative loss improvement to continue. |
| `data_split_method` | STRING | No | `AUTO_SPLIT` | `AUTO_SPLIT`, `RANDOM`, `CUSTOM`, `SEQ`, `NO_SPLIT` | How eval data is held out. |
| `data_split_eval_fraction` | FLOAT64 | No | `0.2` | 0–1 | Eval fraction for RANDOM/SEQ. |
| `data_split_col` | STRING | No | — | column name | With `CUSTOM`: BOOL col, `TRUE`=eval, `FALSE`=train (excluded from features). |
| `auto_class_weights` | BOOL | No | `FALSE` | TRUE/FALSE | `LOGISTIC_REG` only — balance classes inversely to frequency. |
| `class_weights` | ARRAY\<STRUCT\> | No | — | (label, weight) | `LOGISTIC_REG` only — manual per-class weights (mutually exclusive with `auto_class_weights`). |
| `calculate_p_values` | BOOL | No | `FALSE` | TRUE/FALSE | Compute standard errors + p-values (read via `ML.ADVANCED_WEIGHTS`). See gotchas. |
| `fit_intercept` | BOOL | No | `TRUE` | TRUE/FALSE | Include the `__INTERCEPT__` term. |
| `category_encoding_method` | STRING | No | `ONE_HOT_ENCODING` | `ONE_HOT_ENCODING`, `DUMMY_ENCODING` | Categorical encoding. `DUMMY_ENCODING` required for p-values; also recommended whenever reading `ML.WEIGHTS` (see best practices below). With `DUMMY_ENCODING`, the dropped baseline category (pinned `weight: 0.0`) is not user-configurable — **observed** (2 runs, `models/linear_regression/`, different random `AUTO_SPLIT`s each time) to be deterministic per dataset and to consistently pick the most-frequent category, not the alphabetically-first one (e.g. `sex`: `MALE` (168 rows) was the baseline both times, not `FEMALE` (165 rows), despite `FEMALE` < `MALE` alphabetically). |
| `enable_global_explain` | BOOL | No | `FALSE` | TRUE/FALSE | Must be TRUE to later call `ML.GLOBAL_EXPLAIN`. |
| `warm_start` | BOOL | No | `FALSE` | TRUE/FALSE | Continue training an existing model with new data/options. |
| `num_trials` / `max_parallel_trials` / `hparam_tuning_objectives` | — | No | — | — | Enable hyperparameter tuning (see below). |

**Supported lifecycle functions:** `ML.EVALUATE`, `ML.PREDICT`, `ML.WEIGHTS`, `ML.ADVANCED_WEIGHTS`, `ML.GLOBAL_EXPLAIN`, `ML.EXPLAIN_PREDICT`, `ML.FEATURE_INFO`, `ML.TRAINING_INFO`, `ML.TRIAL_INFO` (when tuned), `EXPORT MODEL`. **Classification-only:** `ML.CONFUSION_MATRIX`; **binary-classification-only:** `ML.ROC_CURVE`. (`ML.FEATURE_IMPORTANCE` is for tree/forest models, not GLMs — use `ML.WEIGHTS`/`ML.GLOBAL_EXPLAIN`.)

**ML.EVALUATE output metrics (this type):**
- `LINEAR_REG` (regression): `mean_absolute_error`, `mean_squared_error`, `mean_squared_log_error`, `median_absolute_error`, `r2_score`, `explained_variance`.
- `LOGISTIC_REG` (classification): `precision`, `recall`, `accuracy`, `f1_score`, `log_loss`, `roc_auc`.

**Preprocessing support:** automatic (BQML auto-standardizes numeric features and encodes categoricals) **or** explicit via the `TRANSFORM` clause — preprocessing (e.g. `ML.STANDARD_SCALER`, `ML.BUCKETIZE`, `ML.QUANTILE_BUCKETIZE`) is saved with the model and reapplied automatically at `ML.PREDICT`/`ML.EVALUATE` time.

**Hyperparameter tuning:** Supported. Set `num_trials` (+ optional `max_parallel_trials`, `hparam_tuning_objectives`). Tunable options: `l1_reg`, `l2_reg`, `learn_rate`, `learn_rate_strategy`, `ls_init_learn_rate`, `max_iterations`, `dropout`-n/a. Use `HPARAM_RANGE(lo, hi)` or `HPARAM_CANDIDATES([...])`. Default tuning objective: `r2_score` (LINEAR_REG), `roc_auc` (LOGISTIC_REG). Inspect with `ML.TRIAL_INFO`.

**Explainability / weights:**
- `ML.WEIGHTS` — model coefficients (incl. `__INTERCEPT__`; `category_weights` array for categoricals).
- `ML.ADVANCED_WEIGHTS` — superset adding `standard_error` and `p_value`, one flat row per coefficient (requires `calculate_p_values = TRUE` + `DUMMY_ENCODING` + `l1_reg = 0`, all at train time). This is the only way to learn that a weight is indistinguishable from zero; `ML.WEIGHTS` and `ML.GLOBAL_EXPLAIN` will happily report a confident-looking number for a coefficient the model cannot defend.
- `ML.GLOBAL_EXPLAIN` — overall feature attributions (requires `enable_global_explain = TRUE` at train time).
- `ML.EXPLAIN_PREDICT` — per-row feature attributions (`STRUCT(k AS top_k_features)`).

**Best practices:**
- Set `enable_global_explain = TRUE` at train time if you'll want global attributions — it cannot be added afterward.
- For imbalanced classification (e.g. fraud), use `auto_class_weights = TRUE`.
- Use `data_split_method = 'CUSTOM'` with a BOOL split column to reproduce TRAIN/VALIDATE/TEST exactly.
- `NORMAL_EQUATION` (auto-selected for small unregularized problems) trains in one pass — no iterations to tune; `ML.TRAINING_INFO` returns a single row with `eval_loss = NULL` (no per-iteration eval curve like gradient descent produces).
- **Use `category_encoding_method = 'DUMMY_ENCODING'` whenever you plan to read `ML.WEIGHTS` or `ML.ADVANCED_WEIGHTS`** (the latter requires it outright). With the default `ONE_HOT_ENCODING`, every category is one-hot encoded *and* the model keeps an intercept, so the design matrix is collinear (rank-deficient) for any categorical feature — the individual `category_weights` are not uniquely identified. **Verified by training the same model twice** (`models/linear_regression/`, `penguins`/`body_mass_g`, identical `SELECT`, only `AUTO_SPLIT`'s random draw differing): an `island` category's weight swung from **+305 / +353 / +340 in one run to −39 / −4 / +8.6 in another** — different scale, different sign — while `ML.PREDICT` and `ML.EVALUATE` stayed effectively unchanged. `DUMMY_ENCODING` drops one baseline category per feature (pinned to `weight: 0.0`) and makes every other category's weight a stable, well-defined delta from it.

**Limitations:**
- `ML.ADVANCED_WEIGHTS` p-values require **all** of: `calculate_p_values = TRUE`, `category_encoding_method = 'DUMMY_ENCODING'`, `l1_reg = 0`, **and** total feature cardinality \< 1,000. Only linear and **binary** logistic regression are supported (not multiclass). None of this is retrofittable — the statistics are computed during training, so a model trained without `calculate_p_values` must be retrained, and three of the four preconditions fail at `CREATE MODEL` time rather than when you call the TVF. See that function's entry for the verified error text of each.
- `ML.ROC_CURVE` is binary-only; `ML.CONFUSION_MATRIX` is classification-only.
- Linear models capture only linear relationships — engineer interaction/polynomial features (via `TRANSFORM`) for nonlinearity, or use boosted trees.
- `ML.WEIGHTS`/`ML.GLOBAL_EXPLAIN` attributions for a given category can shift materially between training runs when using `ONE_HOT_ENCODING` (see the `DUMMY_ENCODING` best practice above) — don't treat one run's per-category numbers as ground truth unless trained with `DUMMY_ENCODING`.

**Locations:** Available in all BigQuery ML regions/multi-regions. `EXPORT MODEL` (to GCS, TensorFlow SavedModel format) and Vertex AI Model Registry registration are supported.

**BigFrames API:** `bigframes.ml.linear_model.LinearRegression()` and `bigframes.ml.linear_model.LogisticRegression()` — `.fit(X, y)` / `.predict()` / `.score()`.

**Repo example (tested):**
- `bigquery-ml/models/logistic_regression/logistic_regression.sql` — progressive LOGISTIC_REG lifecycle on `census_adult_income`: create → ML.EVALUATE → ML.CONFUSION_MATRIX → ML.ROC_CURVE → ML.PREDICT → ML.EXPLAIN_PREDICT → ML.GLOBAL_EXPLAIN → **ML.ADVANCED_WEIGHTS** → ML.FEATURE_INFO/TRAINING_INFO → TRANSFORM → HP tuning. Trained with `calculate_p_values`/`DUMMY_ENCODING`/`l1_reg = 0` so the significance read is available; Example 8 finds 54 of 97 testable coefficients insignificant at p > 0.05.
- `bigquery-ml/models/linear_regression/linear_regression.sql` — progressive LINEAR_REG lifecycle on `penguins`/`body_mass_g`: create (with `DUMMY_ENCODING`) → ML.EVALUATE → ML.PREDICT → ML.EXPLAIN_PREDICT → ML.GLOBAL_EXPLAIN → **ML.WEIGHTS** → **ML.ADVANCED_WEIGHTS** → ML.FEATURE_INFO/TRAINING_INFO → TRANSFORM → HP tuning. Confirmed the `NORMAL_EQUATION` single-pass behavior and the `ONE_HOT_ENCODING` category-weight instability documented above. Example 7 pairs `ML.WEIGHTS` with `ML.ADVANCED_WEIGHTS` on the same model, including the `STRUCT(TRUE AS standardize)` variant, and shows `island` failing significance once `species` is present.
- `bigquery-ml/workflows/regression_based_forecasting/regression_based_forecasting.ipynb` — `LINEAR_REG` used for forecasting via a lagged-feature design matrix; shows the regression `ML.EVALUATE` columns and recursive vs. direct multi-step prediction, benchmarked against `ARIMA_PLUS` on the same series.
- `bigquery-ml/workflows/cross_validation/cross_validation.sql` and `bigquery-ml/workflows/ensembling/ensembling.sql` — `LOGISTIC_REG` reused as a fold-level and base-learner model respectively; `bigquery-ml/workflows/propensity_score_matching/` and `bigquery-ml/workflows/survival_analysis/` use the same mechanics for causal and hazard estimation rather than prediction.
- Options this section documents that the lifecycles above cover elsewhere: registry registration, `EXPORT MODEL`, and endpoint serving are covered end-to-end in `bigquery-ml/models/export/` and `bigquery-ml/models/remote/`.


---
