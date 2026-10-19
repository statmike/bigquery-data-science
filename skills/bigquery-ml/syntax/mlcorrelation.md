# `ML.CORRELATION`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mlcorrelation`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlcorrelation)

- **Description:** Computes the correlation between one target column and one or more numeric correlation columns, optionally sliced by dimension columns. Three methods: `PEARSON`, `SPEARMAN`, `KENDALL`. With `dimension_cols`, the output is a full `GROUP BY CUBE` over those dimensions. **Preview.**
- **Use cases:**
  - Rank candidate features against a target before feature selection.
  - Detect **Simpson's-paradox-shaped** structure: the whole-table coefficient versus the same coefficient inside every segment, in one query.
  - Compare linear (`PEARSON`) against monotone (`SPEARMAN`) association to find non-linear-but-ordered relationships.
  - Produce a correlation matrix over a wide table without writing one `CORR()` per pair.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-correlation
- **Type:** Table-valued function. One row per (correlation column × cube cell).
- **Applies to models:** None — model-free utility.

**Syntax:**
```sql
ML.CORRELATION(
  { TABLE `PROJECT_ID.DATASET.TABLE_NAME` | (QUERY_STATEMENT) },
  target_col              => 'target',
  target_correlation_cols => 'metric' | ['metric_1', 'metric_2', ...]
  [, dimension_cols       => 'dim'    | ['dim_1', 'dim_2', ...] ]
  [, method               => 'PEARSON' | 'SPEARMAN' | 'KENDALL' ]
)
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| input data | `TABLE` reference or `(QUERY_STATEMENT)` | Yes | — | Data to correlate. |
| `target_col` | `STRING` | Yes | — | Name of the numeric target column. |
| `target_correlation_cols` | `STRING` or `ARRAY<STRING>` | Yes | — | Numeric column(s) to correlate against the target. |
| `dimension_cols` | `STRING` or `ARRAY<STRING>` | No | none | Groupable column(s) to slice by. **Maximum 12.** |
| `method` | `STRING` | No | `'PEARSON'` | `'PEARSON'`, `'SPEARMAN'`, or `'KENDALL'`. |

**Outputs:**

| Column | Type | Description |
|--------|------|-------------|
| `target_col` | `STRING` | Echo of the target column name. |
| `corr_col` | `STRING` | Which correlation column this row is for. |
| `correlation` | `FLOAT64` | The coefficient. `NULL` for degenerate segments (a single row) — those rows are **not** dropped. |
| `segment_size` | `INT64` | Rows in the segment. **Not** the pairwise *n* the coefficient used. |
| `segment_proportion` | `FLOAT64` | `segment_size` as a fraction of the whole input. |
| `segment` | `ARRAY<STRUCT<dimension_col STRING, dimension_value JSON>>` | Which dimensions this row is *not* rolled up over, and their values. Empty array on the global row. |
| one column per `dimension_cols` entry | source type | The dimension value, or `NULL` — for either of two reasons; see below. |

**Best practices:**
- **Round before comparing.** Never compare `correlation` across queries with `=`.
- **Use `segment` to disambiguate `NULL`.** A dimension column is `NULL` both when the row is a rollup over that dimension and when the segment *is* the genuine-`NULL` group. The rolled-up dimension is **absent** from `segment`; the genuine-`NULL` group is **present** in `segment` with `dimension_value` = JSON `null`. `NOT EXISTS (SELECT 1 FROM UNNEST(segment) s WHERE s.dimension_col = 'col')` is the rollup test.
- **Bucketize continuous columns before using them as dimensions** — see [`ML.QUANTILE_BUCKETIZE`](mlquantile_bucketize.md) and [`functions/bucketizing/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/bucketizing).
- **Filter by `segment_size`** to keep the cube readable, but treat it as an upper bound on evidence, not a sample size.
- Run [`ML.DESCRIBE_DATA`](mldescribe_data.md) first — it tells you the `NULL` rates that make `segment_size` misleading, and catches placeholder-encoded nulls before they become a segment.

**Limitations:**
- **Preview.**
- **`SPEARMAN` is not the textbook Spearman.** BigQuery computes it as `CORR()` over SQL `RANK()` — **competition (min) ranks**, where every tied observation gets the smallest rank in its group. SciPy, R, and pandas' default use **mid-ranks** (the average of the ranks the tie spans). On tied data the two disagree in the second decimal place: on `census_adult_income`, `education_num` vs `hours_per_week` reads `0.172612` from `ML.CORRELATION` and `0.167215` from `scipy.stats.spearmanr`. Reproduce BigQuery's number with `pandas.Series.rank(method='min')` or a pure-SQL `CORR()` over `RANK()`; on tie-free data all conventions agree. Not documented.
- **`KENDALL` *is* tie-corrected — it is tau-b.** So within one function, Kendall corrects for ties and Spearman does not. Matched against `scipy.stats.kendalltau(variant='b')` to floating-point noise; `variant='c'` does not match.
- **`KENDALL` is O(n²) and the constant is not small.** Measured on a synthetic table with the cache off, every doubling of rows multiplies slot time several-fold and the fitted exponent lands near 2, while `PEARSON` and `SPEARMAN` show no size dependence at all across the same range and return a million rows in about a second. A `KENDALL` on 100,000 rows of that shape did not finish inside 12 minutes. Sample or segment before using it.
- **Projecting the `segment` column changes `correlation`** in its last three digits, reproducibly, with the query cache off. Column pruning changes the physical plan, which changes the float summation order. Every projection that includes `segment` returns one value; every projection that omits it returns another. The gap lands in the sixteenth decimal place.
- **`PEARSON` matches `CORR()` but is not bit-identical** — agreement to ~15 significant digits, residual ~4e-16, float summation order again.
- **`segment_size` is the segment's row count, not the pairwise *n*.** Correlation is computed pairwise: for each correlation column, rows where either that column or the target is `NULL` are dropped. Two `corr_col` rows in the same segment can rest on different sample sizes and nothing in the output says so. `WHERE segment_size >= 30` does not guarantee 30 usable pairs.
- **`dimension_cols` accepts any groupable type, including `INT64`.** Passing a continuous numeric column silently produces one segment per distinct value (73 distinct ages → 74 output rows, no error).
- **Maximum 12 `dimension_cols`** — a 13th fails with an explicit error. Output row count is the full CUBE cell count, including degenerate single-row cells, so it grows fast: three dimensions on `census_adult_income` produce 134 rows.

**Related — three ways to correlate in BigQuery:**

| You want | Use | Notes |
|---|---|---|
| One pair, Pearson | `CORR(x, y)` | Aggregate function; matches `ML.CORRELATION` `PEARSON` to ~15 digits |
| One target vs many columns, optionally sliced | `ML.CORRELATION` | Three methods, CUBE slicing, one query |
| Which features *drive* an outcome, not just co-move | [`AI.KEY_DRIVERS`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/augmented-analytics.md) / [`AI.CAUSAL_EFFECT`](aicausal_effect.md) | Correlation is symmetric and pairwise; these are neither |

**BigFrames API:** No wrapper. `bigframes.pandas.DataFrame.corr()` is a pandas-shaped equivalent compiled to BigQuery SQL — Pearson only, no dimension slicing, and a matrix rather than a target-vs-columns shape. Reach the SQL function via `bigframes.pandas.read_gbq`.

**Repo example (tested):** [`functions/exploration/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/exploration) — establishes `PEARSON` == `CORR()`, reproduces the `SPEARMAN` min-rank convention three ways (pandas, pure SQL, and a tie-free control), confirms `KENDALL` is tau-b against SciPy, measures the Kendall cost curve, matches the `dimension_cols` output row count against `GROUP BY CUBE` exactly, separates the two kinds of dimension `NULL`, and shows `segment_size` overstating the pairwise *n*.

---
