# `ML.DESCRIBE_DATA`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mldescribe_data`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mldescribe_data)

- **Description:** Computes descriptive statistics for every column of a table or subquery in one pass — row/value/null/zero counts, min/max, mean, stddev, median, quantiles, distinct count, top values, and array-length statistics. One row per input column. **GA.**
- **Use cases:**
  - Profile a dataset before writing the first `CREATE MODEL` — types, ranges, cardinality, and missingness in a single query.
  - Find placeholder-encoded nulls (`' ?'`, `'N/A'`, `-1`, `9999`) that `num_nulls` cannot see.
  - Decide which columns are numeric enough to correlate and which need bucketizing or encoding first.
  - Snapshot a profile before/after a pipeline change, as an informal precursor to a formal skew/drift check.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-describe-data
- **Type:** Table-valued function. One row per input column.
- **Applies to models:** None — model-free utility (operates on data, not a model).

**Syntax:**
```sql
ML.DESCRIBE_DATA(
  { TABLE `PROJECT_ID.DATASET.TABLE_NAME` | (QUERY_STATEMENT) }
  [, STRUCT(
       num_quantiles AS num_quantiles,
       num_array_length_quantiles AS num_array_length_quantiles,
       top_k AS top_k
     )]
)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| input data | `TABLE` reference or `(QUERY_STATEMENT)` | Yes | — | Data to profile. |
| `num_quantiles` | `INT64` | No | **2** | Quantiles for numerical columns. Range \[1, 100000\] — measured, the docs say the floor is 2 but `1` is accepted and `0` errors with *must be an integer between [1, 100000]*. The returned `quantiles` array has `num_quantiles + 1` entries (the boundaries), so the default returns min / median / max. |
| `num_array_length_quantiles` | `INT64` | No | 10 | Quantiles for `ARRAY` lengths. Range \[1, 100000\]. Same `+ 1` boundary convention. |
| `top_k` | `INT64` | No | 1 | Top values returned per categorical column. Range \[1, 10000\] — confirmed live; `0` and `100000` both error with the bound quoted. An unrecognized setting name (`topk`) fails with *Found unsupported setting field* rather than being ignored. |

**Outputs:** one row per input column. Columns not applicable to a given input type come back `NULL` (or an empty array).

| Column | Type | Populated for | Description |
|--------|------|---------------|-------------|
| `name` | `STRING` | all | Input column name. |
| `num_rows` | `INT64` | all | Rows in the input. |
| `num_values` | `INT64` | all | Non-null values considered. Differs from `num_rows` for `ARRAY` columns, which are unnested first. |
| `num_nulls` | `INT64` | all | Null count. **Counts SQL `NULL` only** — see the limitation below. |
| `num_zeros` | `INT64` | numeric | Count of exact zeros. |
| `min` / `max` | `STRING` | all | MIN / MAX, rendered as strings regardless of input type. |
| `mean` / `stddev` / `median` | `FLOAT64` | numeric | The docs spell the middle one `stdev`; the actual output column is **`stddev`**. |
| `quantiles` | `ARRAY<FLOAT64>` | numeric | `APPROX_QUANTILES` boundaries, `num_quantiles + 1` of them. |
| `unique` | `INT64` | categorical | `APPROX_COUNT_DISTINCT`. |
| `avg_string_length` | `FLOAT64` | `STRING` | Mean length of the non-null values. |
| `top_values` | `ARRAY<STRUCT<value STRING, count INT64>>` | categorical | `top_k` entries. |
| `min_array_length` / `max_array_length` / `avg_array_length` / `total_array_length` | `INT64` / `FLOAT64` | `ARRAY` | Array-length statistics. |
| `array_length_quantiles` | `ARRAY<INT64>` | `ARRAY` | `num_array_length_quantiles + 1` boundaries. |
| `dimension` | `STRING` | — | Present in the output schema and `NULL` in every call tested; there is no setting that populates it (`dimension_cols` is rejected: *unsupported setting field*). |

**Best practices:**
- **Read `num_nulls` and `min`/`max` together.** A `num_nulls` of 0 next to a `min` of `' ?'` is the signature of string-encoded missingness. On `census_adult_income`, `workclass` reports `num_nulls = 0` while 1,836 rows hold the literal string `' ?'` — repair with `NULLIF(TRIM(col), '?')` before doing anything statistical.
- **Raise `top_k`.** The default of 1 gives you the mode and nothing else; 5–10 is what makes a categorical column legible.
- **Raise `num_quantiles`.** The default of 2 gives min / median / max. `4` or `10` is what shows you the shape. Asking for more pieces than the column has distinct values is not an error — it returns duplicate boundaries, which is itself a reading of the distribution.
- **Choose the argument form deliberately.** `TABLE t` profiles the table as stored: every column, every row. A parenthesized query profiles exactly what it selects, which is how you narrow columns, filter rows, and profile an expression that does not exist in the table yet (`NULLIF(TRIM(workclass), '?')` turns the placeholder into a real `NULL` that `num_nulls` then counts).
- Run on a representative slice (filter by date) rather than the full table to control cost.
- Profile before correlating — [`ML.CORRELATION`](mlcorrelation.md) requires numeric columns, and this tells you which ones are actually numeric and how much of each is missing.

**Limitations:**
- **`num_nulls` counts SQL `NULL` only.** Placeholder encodings are invisible to it, and every downstream statistic (`mean`, `stddev`, `unique`, `top_values`) silently treats the placeholder as a real value.
- The documented output column `stdev` does not exist — selecting it fails with *Unrecognized name: stdev; Did you mean stddev?*
- `min` / `max` are `STRING`, so ordering them in the output is lexicographic, not numeric.
- Quantiles are approximate (`APPROX_QUANTILES`), and `unique` is approximate (`APPROX_COUNT_DISTINCT`). Not just approximate but **unstable**: repeated runs of the identical call against the static public `census_adult_income` have returned both `12.0` and `13.0` for the same interior boundary of `education_num`. Read them as distribution shape; use `PERCENTILE_CONT` where an exact cut point matters.
- `ARRAY` columns are unnested before statistics are computed; `ARRAY<STRUCT<INT64, numerical>>` is treated as a sparse `ARRAY<numerical>`.

**BigFrames API:** No wrapper. `bigframes.pandas.DataFrame.describe()` is a pandas-shaped equivalent compiled to BigQuery SQL — a different implementation with a different output shape (statistics as rows, columns as columns) and no `top_values` or array handling. Reach the SQL function via `bigframes.pandas.read_gbq`.

**Repo example (tested):** [`functions/exploration/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/exploration) — opens with the bare one-line call on the whole table (15 input columns, 20 output columns), then turns `top_k` and `num_quantiles` up to show what the defaults hide (`workclass`'s `' ?'` placeholder sits at rank 4 with 1,836 rows, invisible at `top_k => 1`), probes both settings' bounds live, contrasts the `TABLE` and subquery argument forms, catches the `num_nulls = 0` / `min = ' ?'` contradiction, and demonstrates the `stdev` → `stddev` error live.

---
