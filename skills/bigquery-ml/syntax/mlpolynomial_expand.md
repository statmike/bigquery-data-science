# `ML.POLYNOMIAL_EXPAND`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mlpolynomial_expand`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlpolynomial_expand)

- **Description:** Given a `STRUCT` of numerical features, returns a `STRUCT` of all polynomial combinations (including the originals) up to `degree`. Field names concatenate the source feature names (e.g. `x1`, `x1_x1`, `x1_x2`, `x2`, `x2_x2`).
- **Use cases:**
  - Add squared/cubic and interaction terms so linear models can fit curvature.
  - Quick polynomial feature generation without manual `col*col` expressions.
- **documentation:** <https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-polynomial-expand>
- **Type:** Scalar (no `OVER()`).
- **Category:** Numerical manual preprocessing.
- **Applies to models:** Any model type. **Not exportable** in `TRANSFORM`.

**Syntax:**
```sql
ML.POLYNOMIAL_EXPAND(struct_numerical_features [, degree])
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `struct_numerical_features` | `STRUCT` of numeric | Yes | — | Named numeric features (`STRUCT(col1, col2, ...)`); **≤ 10** features, no duplicates, all named. |
| `degree` | `INT64` | No | `2` | Highest combination degree; range `[1, 4]`. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| (result) | `STRUCT<FLOAT64>` | All polynomial combinations up to `degree`, including the original terms. |

**Best practices:** Combine with `ML.IMPUTER`/scaling first; wrap an imputed (analytic) column inside the `STRUCT` since `ML.POLYNOMIAL_EXPAND` is scalar and can take an analytic argument.
**Limitations:** ≤ 10 input features, no unnamed/duplicate features; `degree` ≤ 4. **Not exportable** in `TRANSFORM`, same verified failure mode as `ML.FEATURE_CROSS` above (`EXPORT MODEL` rejects it with "Model TRANSFORM contains unsupported function for exporting" — training/`ML.PREDICT` are unaffected).
**BigFrames API:** `bigframes.ml.preprocessing.PolynomialFeatures`.
**Repo example (tested):** [`functions/feature_engineering/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/feature_engineering) — Example 5 expands `penguins`' `culmen_length_mm`/`culmen_depth_mm` at `degree = 2`, yielding e.g. `{'length':36.6,'depth':18.4,'length_length':1339.56,'length_depth':673.44,'depth_depth':338.56}`. Example 6 shows the **compounded** pattern (impute → expand), which works because a scalar function may take an analytic function's result as an argument:
```sql
SELECT
  body_mass_g,
  ML.POLYNOMIAL_EXPAND(
    STRUCT(ML.IMPUTER(body_mass_g, 'mean') OVER() AS mass_imputed),
    2
  ) AS expanded
FROM `bigquery-public-data.ml_datasets.penguins`
ORDER BY body_mass_g IS NULL DESC;
```

---
