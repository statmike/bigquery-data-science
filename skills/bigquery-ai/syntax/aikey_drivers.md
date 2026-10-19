# `AI.KEY_DRIVERS`

> **Source:** [`bigquery-ai/reference/augmented-analytics.md#aikey_drivers`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/augmented-analytics.md#aikey_drivers)

- **Description:** (GA) Table-valued function that identifies segments of data causing statistically significant changes to a summable metric between an interest set and a reference set (key driver / contribution analysis). No `CREATE MODEL` step, connection, or endpoint required — it operates directly on a table or subquery.
- **Use cases:** Explaining why a metric moved between two periods (e.g., this month vs last), comparing test vs control groups, attributing revenue/usage changes to customer segments, geographies, or product categories, root-cause analysis for KPI shifts.
- [documentation](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-key-drivers)
- **Type:** Table-valued function — GA

**Syntax:**
```sql
AI.KEY_DRIVERS(
  { TABLE TABLE_NAME | (QUERY_STATEMENT) },
  metric_col => 'METRIC_COL',
  dimension_cols => DIMENSION_COLS,
  interest_label_col => 'INTEREST_LABEL_COL'
  [, min_apriori_support => MIN_APRIORI_SUPPORT ]
  [, top_k => TOP_K ]
  [, enable_pruning => ENABLE_PRUNING ]
);
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `TABLE` / `(QUERY_STATEMENT)` | Table or subquery | Required | -- | The interest and reference data to analyze. Must contain a summable metric column, a BOOL interest/reference column, and one or more dimension columns. |
| `metric_col` | STRING (named parameter) | Required | -- | A summable metric, expressed as `SUM(column_name)` or `column_name` (both are equivalent and case-insensitive). No additional computation allowed in the expression (e.g., no `SUM(AVG(...))`); do extra math in `QUERY_STATEMENT` instead. |
| `dimension_cols` | ARRAY<STRING> (named parameter) | Required | -- | Names of the columns to use as dimensions when summarizing the metric. Must be `INT64`, `BOOL`, or `STRING`. Provide **between 1 and 12** columns. Cannot reuse the `metric_col` or `interest_label_col`. |
| `interest_label_col` | STRING (named parameter) | Required | -- | Name of a `BOOL` column. `TRUE` rows are the interest (test) group; `FALSE` rows are the reference (control) group. |
| `min_apriori_support` | FLOAT64 (named parameter) | Optional | 0.1 | Minimum apriori support threshold in `[0,1]` for including segments. Segments below the threshold are excluded. **Mutually exclusive with `top_k`.** |
| `top_k` | INT64 (named parameter) | Optional | -- | Between 1 and 1,000,000. Returns the insights with the highest apriori support and prunes the rest, reducing runtime. **Mutually exclusive with `min_apriori_support`.** If neither is set, a `min_apriori_support` of 0.1 is applied. |
| `enable_pruning` | BOOL (named parameter) | Optional | TRUE | When `TRUE`, redundant insights are omitted (a row whose dimensions/values are a subset of another row with an equal metric is pruned, keeping the more descriptive row). The `["all"]` row is never pruned. When `FALSE`, all insights pass through except those filtered by support thresholds. |

**Outputs:** Returns the following columns in addition to the dimension columns:

| Column | Type | Description |
|--------|------|-------------|
| `drivers` | ARRAY<STRING> | The dimension values describing the segment (e.g., `["usertype=Subscriber","gender=male"]`). The other columns in the row apply to this segment. The whole-population row is `["all"]`. |
| `metric_interest` | NUMERIC | Sum of the metric in the interest set for the segment. |
| `metric_reference` | NUMERIC | Sum of the metric in the reference set for the segment. |
| `difference` | NUMERIC | `metric_interest - metric_reference`. |
| `relative_difference` | NUMERIC | `difference / metric_reference`. |
| `unexpected_difference` | NUMERIC | Difference between the segment's actual and *expected* `metric_interest`, where the expectation is derived from the change ratio of all other segments. Highlights segments changing differently than the overall trend. |
| `relative_unexpected_difference` | NUMERIC | `unexpected_difference / expected_metric_interest`. |
| `apriori_support` | NUMERIC | `GREATEST(metric_interest / total_interest, metric_reference / total_reference)` — how large the segment is relative to the population. |
| `contribution` | NUMERIC | `ABS(difference)` — magnitude of the segment's contribution to the overall change. |

**Input data requirements:** A single table containing both the interest (test) and reference (control) rows, distinguished by the BOOL `interest_label_col`. For best results, use roughly equal numbers of interest and reference rows to avoid biased results. Typical interest/reference splits: two time periods, two geographies, two product types, or two campaigns.

**Best practices:**
- Build the BOOL interest/reference column inside `QUERY_STATEMENT` (e.g., `(EXTRACT(YEAR FROM ts) = 2017) AS is_interest`).
- Use `top_k` for fast, ranked top insights; use `min_apriori_support => 0` to see every segment.
- Sort the output by `contribution` (largest absolute movers) or `unexpected_difference` (segments defying the overall trend).
- Keep `enable_pruning => TRUE` (default) for a concise insight set; set `FALSE` when you need the full unpruned breakdown.

**Limitations:**
- Supports a **maximum of 12 dimensions**.
- Supports **summable metrics only** (contribution analysis models additionally support summable-by-ratio and summable-by-category metrics).
- `min_apriori_support` and `top_k` cannot be used together.

**Locations:** The reference page no longer carries a Locations section. Measured 2026-10-09: a call against a dataset in `asia-northeast1` succeeds, so the earlier US/EU multi-region restriction has lifted.

**Provisioned throughput:** Not specified.

**BigFrames API:** No direct equivalent. Use `%%bigquery` magics or `session.read_gbq_query()` to execute AI.KEY_DRIVERS SQL from BigFrames.

**Relationship to contribution analysis models / ML.GET_INSIGHTS:** Calling `AI.KEY_DRIVERS` is similar to first creating a contribution analysis model and then calling `ML.GET_INSIGHTS` on it. For most applications, `AI.KEY_DRIVERS` is recommended — simpler syntax, faster results, and automatic pruning. Use a contribution analysis model when you need more than 12 dimensions or non-summable metrics — see [`../bigquery-ml/RESOURCES.md`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/RESOURCES.md)'s `CONTRIBUTION_ANALYSIS` entry and [`../bigquery-ml/models/contribution_analysis/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/contribution_analysis), which uses this exact dataset and interest/reference split for a direct side-by-side comparison, and verifies both differentiators (ratio/category metrics, >12 dimensions) live, plus a finding not covered here: `ML.GET_INSIGHTS`'s output schema differs by metric type (summable vs. ratio vs. category each return different derived-statistic columns).

| | AI.KEY_DRIVERS | Contribution analysis model + ML.GET_INSIGHTS |
|---|----------------|------------------------------------------------|
| **Dimensions** | Maximum 12 | More than 12 |
| **Metric types** | Summable only | Summable, summable by ratio, summable by category |
| **Pruning** | Prunes redundant insights by default | Returns all insights by default |
| **Segment column** | `drivers` | `contributors` |
| **Model management** | None required | Create and manage a model |
