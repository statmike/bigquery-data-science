# `ML.FEATURE_INFO`

> **Source:** [`bigquery-ml/reference/model-lifecycle-functions.md#mlfeature_info`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-lifecycle-functions.md#mlfeature_info)

- **Description:** Returns summary statistics for each input feature column the model saw during training — conceptually the model's equivalent of pandas `describe()`.
- **Use cases:**
  - Sanity-check the data a model actually trained on (ranges, nulls, cardinality).
  - Verify preprocessing worked (e.g. `null_count = 0` after `ML.IMPUTER`).
  - Document feature distributions for model cards / governance.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-feature
- **Type:** Table-valued.
- **Applies to models:** Almost all trained model types (LINEAR_REG, LOGISTIC_REG, BOOSTED_TREE_*, RANDOM_FOREST_*, DNN_*, KMEANS, PCA, AUTOENCODER, MATRIX_FACTORIZATION, ARIMA_PLUS, etc.). **Not** supported on imported TensorFlow models. Remote models have no local features.

**Syntax:**
```sql
SELECT * FROM ML.FEATURE_INFO(MODEL `PROJECT_ID.DATASET.MODEL_NAME`);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL` | model ref | Yes | — | The trained model to introspect. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `input` | STRING | Name of the feature column. |
| `min` | FLOAT64 | Minimum value; NULL for non-numeric inputs. |
| `max` | FLOAT64 | Maximum value; NULL for non-numeric inputs. |
| `mean` | FLOAT64 | Average value; NULL for non-numeric inputs. |
| `median` | FLOAT64 | Median value; NULL for non-numeric inputs. |
| `stddev` | FLOAT64 | Standard deviation; NULL for non-numeric inputs. |
| `category_count` | INT64 | Number of distinct categories; NULL for non-categorical columns. |
| `null_count` | INT64 | Number of NULL values in the input column. |
| `dimension` | INT64 | For ARRAY-type feature columns, the array dimension. |

**Best practices:**
- Run it right after `CREATE MODEL` as a data-quality gate before trusting metrics.
- With a `TRANSFORM` clause, output describes the **pre-transform** columns from the `query_statement` — pair it with `ML.FEATURE_IMPORTANCE`/`ML.WEIGHTS` to see post-transform behavior.

**Limitations:**
- No imported-TensorFlow support.
- Stats are point-in-time from training; they do not reflect new serving data.

**BigFrames API:** No direct equivalent (inspect the model object / run the SQL via `bigframes`).
**Repo example (tested):** `bigquery-ml/models/logistic_regression/logistic_regression.sql` (Example 8). The same call shape appears in every model family under `models/` — GLM (`linear_regression/`, `logistic_regression/`), tree ensembles (`boosted_tree_classifier/`, `boosted_tree_regressor/`, `random_forest_classifier/`, `random_forest_regressor/`), neural (`dnn_classifier/`, `dnn_regressor/`, `wide_and_deep_classifier/`, `wide_and_deep_regressor/`), unsupervised (`kmeans/`, `pca/`, `autoencoder/`, `matrix_factorization/`), forecasting (`arima_plus/`, `arima_plus_xreg/`), and `automl_classifier/`, `automl_regressor/`, `imported/`, `remote/`, `transform_only/` — 21 files in all, which is what makes it the cheapest first look at any model.

---
