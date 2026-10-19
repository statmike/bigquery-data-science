# `ML.ADVANCED_WEIGHTS`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mladvanced_weights`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mladvanced_weights)

- **Description:** Extended version of `ML.WEIGHTS` for **linear regression** and **binary logistic regression** models. Returns the same weights plus per-weight **standard errors** and **p-values** (statistical significance). Its output is a superset of `ML.WEIGHTS`.
- **Use cases:**
  - Statistical inference on coefficients (significance testing) for econometric / explanatory modeling.
  - Identify which features have weights statistically distinguishable from zero.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-advanced-weights
- **Type:** Table-valued function.
- **Applies to models:** `LINEAR_REG` and **binary** `LOGISTIC_REG` only. Multiclass logistic regression and matrix factorization are NOT supported. Model must be trained with `CALCULATE_P_VALUES = TRUE`, `CATEGORY_ENCODING_METHOD = 'DUMMY_ENCODING'`, and `L1_REG = 0`.

**Syntax:**
```sql
SELECT *
FROM ML.ADVANCED_WEIGHTS(MODEL `PROJECT_ID.DATASET.MODEL_NAME`
                         [, STRUCT(TRUE AS standardize)]);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model ref | Yes | — | Linear or binary logistic regression model trained with the required options above. |
| `STANDARDIZE` | BOOL (in STRUCT) | No | `FALSE` | Standardize weights (mean 0 / std 1). Set TRUE to obtain a standard error and p-value for the intercept. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `processed_input` | STRING | Feature input column name. |
| `weight` | FLOAT64 | Weight for a numeric feature; NULL for categorical (see `category`). |
| `category` | STRING | Category name for non-numeric/dummy-encoded inputs (NULL for numeric). |
| `standard_error` | FLOAT64 | Standard error of the weight. `NULL` for the intercept unless `standardize=TRUE`; **`0.0`** (not `NaN`) for a dropped dummy category. |
| `p_value` | FLOAT64 | p-value of the weight. `NULL` for the intercept unless `standardize=TRUE`; **`NaN`** for a dropped dummy category. |

The intercept arrives as a final row with `processed_input = '__INTERCEPT__'` and `category = NULL`. Note the two sentinel values differ: a baseline row is `weight = 0.0`, `standard_error = 0.0`, `p_value = NaN`, so `NOT IS_NAN(p_value)` is the reliable filter — reading `standard_error = 0.0` as a measured value will silently corrupt any average.

**Best practices:**
- Train with `CALCULATE_P_VALUES = TRUE` up front — p-values/standard errors are computed at CREATE MODEL time and cannot be added later.
- Set `STANDARDIZE => TRUE` when you need inference statistics for the intercept.

**Limitations:**
- Not available for multiclass logistic regression, matrix factorization, or any non-GLM model.
- Requires `L1_REG = 0` and `DUMMY_ENCODING`; incompatible with L1 regularization.
- Dropped dummy categories report `weight = 0.0` and `standard_error = 0.0` with a `NaN` p-value.

**Gotchas (verified live):**
- **Each precondition fails differently, and three of the four fail at `CREATE MODEL` time, not at query time.** Verified error text:

  | What you got wrong | Where it fails | Message |
  |---|---|---|
  | `calculate_p_values` omitted | the TVF | `Model is not supported by ML.ADVANCED_WEIGHTS because it was not trained with calculate_p_values = true.` |
  | left the default `ONE_HOT_ENCODING` | `CREATE MODEL` | `Please specify CATEGORY_ENCODING_METHOD=DUMMY_ENCODING to enable p_values calculation.` |
  | `l1_reg > 0` | `CREATE MODEL` | `L1_REG must be zero if CALCULATE_P_VALUES=TRUE.` |
  | multiclass label | `CREATE MODEL` | `Option(s) calculate_p_values are found. P-values can only be calculated for linear regression and binary logistic regression models.` |

- **A model with categorical features emits a warning at `CREATE MODEL` time:** `Since model contains categorical values, regression statistics will not be calculated for unstandardized intercept.` This is expected, not a failure — it is why `__INTERCEPT__` returns `NULL` statistics and why `STRUCT(TRUE AS standardize)` exists.
- **The dropped `DUMMY_ENCODING` baseline is the most frequent category, not the first alphabetically.** On `penguins` the baselines are Adelie (146 rows), Biscoe (163), and `MALE` (168) — `MALE` wins despite `FEMALE` sorting earlier.
- **`standardize` does not change any p-value.** It scales `weight` and `standard_error` by the same factor, so the t-statistic is invariant. Use it to compare effect sizes on a common scale, never to change which coefficients are significant.
- **The standardized intercept is not the label mean.** Categorical features stay dummy-coded rather than centered, so it is the prediction at mean numeric features *and* baseline categories. On `penguins` it is 4110.72 while mean `body_mass_g` is 4207.06.
- **`p_value` bottoms out near `1e-15`** (double-precision floor). Below that, differences are numerical noise — do not rank features by p-value down there.
- **`category` values inherit whatever is in the data, including leading whitespace.** `census_adult_income` returns `' White'` and `' Female'`; `category = 'White'` matches nothing. Use `TRIM(category)`.

**BigFrames API:** No dedicated wrapper; call the TVF via SQL / `read_gbq`.

**Repo example (tested):** `bigquery-ml/models/linear_regression/` (Example 7) and `bigquery-ml/models/logistic_regression/` (Example 8) — the two model types that satisfy the constraint, each training its main model with `calculate_p_values = TRUE`, `DUMMY_ENCODING`, and `l1_reg = 0` from the start, since the options cannot be added later.

The linear example is the clean statistical read: on `penguins`, `island` is the only feature whose categories are insignificant (p ≈ 0.82 and 0.42) because Gentoo appears only on Biscoe and Chinstrap only on Dream, so `island` merely restates `species`. `ML.WEIGHTS` reports non-zero island weights and gives you no way to see this. It also runs the `STRUCT(TRUE AS standardize)` variant to recover intercept statistics and to show that `flipper_length_mm` moves from 16.24 g/mm to 227.60 g per standard deviation while its p-value is unchanged at 2.6e-06.

The logistic example is the scale read: on `census_adult_income` the model expands to 106 rows (105 coefficients plus `__INTERCEPT__`); eight are dropped baselines, leaving 97 real tests, and **54 of those come back with p > 0.05**. Verified breakdown — `native_country` 38/41 insignificant, `education` 5/15, `workclass` 4/8, `occupation` 4/14, `race` 2/4, `marital_status` 1/6, and every numeric feature significant. More than half of what a 32k-row model learned is undefendable, concentrated almost entirely in one sparse high-cardinality column, and neither `ML.WEIGHTS` nor `ML.GLOBAL_EXPLAIN` would surface it.

> Note: For boosted trees / random forest see `ML.FEATURE_IMPORTANCE` and `ML.GLOBAL_EXPLAIN`; for k-means see `ML.CENTROIDS`; for PCA/autoencoder see `ML.PRINCIPAL_COMPONENTS` / `ML.PRINCIPAL_COMPONENT_INFO`; for ARIMA_PLUS see `ML.ARIMA_COEFFICIENTS`. The tree, clustering, and forecasting model files (`models/boosted_tree_classifier/`, `models/pca/`, `models/kmeans/`, `models/autoencoder/`, `models/arima_plus/`) do NOT use `ML.WEIGHTS`. Neither do the DNN and wide-and-deep types — `models/dnn_classifier/` (Example 7) records why: no coefficients exist, so Integrated Gradients via `ML.GLOBAL_EXPLAIN` is the only mechanism available there.


---
