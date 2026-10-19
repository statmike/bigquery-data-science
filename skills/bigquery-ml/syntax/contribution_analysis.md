# `CONTRIBUTION_ANALYSIS`

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#contribution_analysis`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#contribution_analysis)

- **Description:** Trains a contribution analysis (a.k.a. key-driver) model that detects which segments of multi-dimensional data most explain a change in a summable metric, by comparing a **test** set against a **control** set. It is not a predictive model — there is no `ML.PREDICT`; you create the model and then read insights from it with `ML.GET_INSIGHTS`.
- **When to use:**
  - Explain *why* a metric moved (e.g., revenue, conversions) across two periods or two cohorts.
  - Surface the specific dimension combinations (segments) driving the largest / most-unexpected changes.
  - You need capabilities beyond the model-free `AI.KEY_DRIVERS` — i.e., **summable-by-ratio** or **summable-by-category** metrics, or more dimensions than `AI.KEY_DRIVERS` supports.
- **Category:** unsupervised (insight/segment analysis).
- **Connection required:** No.
- **Status:** GA (GA announced 2025-05-12; Preview since 2024-09).
- **documentation:** [CREATE MODEL for contribution analysis](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-contribution-analysis) · [Contribution analysis overview](https://cloud.google.com/bigquery/docs/contribution-analysis) · [Get insights (summable)](https://cloud.google.com/bigquery/docs/get-contribution-analysis-insights)

> **SCOPE / CROSS-LINK:** The simplified, model-free equivalent — `AI.KEY_DRIVERS` (a single TVF, no `CREATE MODEL`) — is OWNED by `../bigquery-ai/RESOURCES.md` (`AI.KEY_DRIVERS` entry, incl. inputs/outputs and the "model vs. function" comparison table). For most key-driver use cases that function is recommended (simpler, faster, auto-pruning). Reach for the `CONTRIBUTION_ANALYSIS` **model** documented here only when you need summable-by-ratio / summable-by-category metrics or more dimensions than `AI.KEY_DRIVERS` allows. **Do not duplicate the AI.KEY_DRIVERS reference here.**

**CREATE MODEL syntax:**
```sql
CREATE OR REPLACE MODEL `PROJECT_ID.DATASET.MODEL_NAME`
OPTIONS(
  model_type = 'CONTRIBUTION_ANALYSIS',
  contribution_metric = 'SUM(sales)/COUNT(DISTINCT user_id)',
  dimension_id_cols = ['device_category', 'country', 'site_traffic_source'],
  is_test_col = 'is_test',
  top_k_insights_by_apriori_support = 15,
  pruning_method = 'PRUNE_REDUNDANT_INSIGHTS'
) AS
SELECT * FROM `PROJECT_ID.DATASET.input_data`;
```
The input query must contain **exactly** the columns referenced in `contribution_metric`, `dimension_id_cols`, and `is_test_col`.

**Options (model-specific):**

| Option | Type | Required | Default | Range / Values | Description |
|--------|------|----------|---------|----------------|-------------|
| `model_type` | STRING | Yes | — | `'CONTRIBUTION_ANALYSIS'` | Selects the contribution analysis model. |
| `contribution_metric` | STRING | Yes | — | `SUM(x)` (summable); `SUM(num)/SUM(den)` (summable-ratio); `SUM(x)/COUNT(DISTINCT cat)` (summable-by-category) | Metric to analyze. Metric column values must be non-negative unless `min_apriori_support = 0`. |
| `dimension_id_cols` | ARRAY\<STRING\> | No | all non-metric / non-test cols | columns of type INT64, BOOL, or STRING | Dimension columns used to form segments. Rows with NULL dimension values are dropped. |
| `is_test_col` | STRING | Yes | — | a BOOL column | Flags each row as test (`TRUE`) vs. control (`FALSE`). |
| `min_apriori_support` | FLOAT64 | No | `0.1` | `[0, 1]` | Min segment-size support to include a segment. Mutually exclusive with `top_k_insights_by_apriori_support`. |
| `top_k_insights_by_apriori_support` | INT64 | No | — | positive integer | Return the top-K insights by apriori support; model sets the threshold automatically. Mutually exclusive with `min_apriori_support`. |
| `pruning_method` | STRING | No | `'NO_PRUNING'` | `'NO_PRUNING'` \| `'PRUNE_REDUNDANT_INSIGHTS'` | `PRUNE_REDUNDANT_INSIGHTS` drops a segment whose dimensions are a subset of a more descriptive segment with an equal metric value (the `all` row is never pruned). |

**Supported lifecycle functions:** `ML.GET_INSIGHTS` (the only insight-retrieval function for this type). Standard model-management applies (`ML.MODEL_INFO` via `INFORMATION_SCHEMA`, drop/rename). **Not supported:** `ML.PREDICT`, `ML.EVALUATE`, `ML.WEIGHTS`, `ML.GLOBAL_EXPLAIN`, `ML.FEATURE_IMPORTANCE`, hyperparameter tuning, `TRANSFORM`.

**ML.GET_INSIGHTS output metrics (this type):**

**Verified: the output schema is NOT fixed — it differs by `contribution_metric` type.** This is not called out in the official reference at the time this was tested; confirmed directly by training all three metric forms on identical data/dimensions.

*Summable metric* (`SUM(x)`):

| Column | Description |
|--------|-------------|
| `contributors` | The dimension segment, e.g. `vendor_name=SAZERAC COMPANY INC`; `all` for the overall row. |
| `metric_test` | Metric value over the test set. |
| `metric_control` | Metric value over the control set. |
| `difference` | Raw change (`metric_test` − `metric_control`). |
| `relative_difference` | Proportional change. |
| `unexpected_difference` | Change beyond what the overall growth rate predicts. |
| `relative_unexpected_difference` | `unexpected_difference` as a proportion. |
| `apriori_support` | Segment-size support (`1.0` for the `all` row). |
| `contribution` | `ABS(difference)`; output is sorted by this descending. |

*Summable-ratio metric* (`SUM(a)/SUM(b)`) — verified DIFFERENT columns:

| Column | Description |
|--------|-------------|
| `metric_test_over_metric_control` | Ratio of test to control metric for the segment. |
| `metric_test_over_complement` | Segment's test metric relative to the rest of the test set. |
| `metric_control_over_complement` | Segment's control metric relative to the rest of the control set. |
| `aumann_shapley_attribution` | Shapley-value-based attribution of the overall ratio change to this segment. |
| `contribution` | **Equals `ABS(aumann_shapley_attribution)`** here, NOT `ABS(difference)` — `difference`/`relative_difference`/`unexpected_difference`/`relative_unexpected_difference` don't appear at all for this metric type. |

*Summable-by-category metric* (`SUM(a)/COUNT(DISTINCT b)`) — verified a THIRD schema:

| Column | Description |
|--------|-------------|
| `difference`, `relative_difference` | Same meaning as the summable case. |
| `metric_test_over_population` | Segment's test metric as a share of the full test population's metric. |
| `metric_control_over_population` | Segment's control metric as a share of the full control population's metric. |
| `contribution` | `ABS(difference)` again (like summable) — but `unexpected_difference`/`relative_unexpected_difference` are absent, replaced by the `_over_population` columns. |

All three forms also return each dimension broken out into its own column (e.g. `usertype`, `gender`), and `apriori_support`.

**Preprocessing support:** N/A — no `TRANSFORM` clause (verified: errors immediately with `"Transform clause is not supported for the model type CONTRIBUTION_ANALYSIS"`); the input query columns are consumed directly.

**Hyperparameter tuning:** Not supported.

**Explainability / weights:** N/A — the model *is* the explanation; insights come from `ML.GET_INSIGHTS`, not from the `ML.WEIGHTS` / `ML.GLOBAL_EXPLAIN` family.

**Best practices:**
- Prefer `top_k_insights_by_apriori_support` for predictable runtime/output size; it lets the model auto-tune the apriori threshold.
- Use `PRUNE_REDUNDANT_INSIGHTS` to remove subset-redundant segments and keep the most descriptive rows — **verified dramatic effect**: `NO_PRUNING` + `min_apriori_support=0.001` on a 3-dimension model returned 1,559 insight rows; `PRUNE_REDUNDANT_INSIGHTS` + `top_k=15` on the identical data returned exactly 15.
- Sort/filter insights by `contribution` (biggest movers) or `unexpected_difference` (segments defying the overall trend, summable/category metrics only — ratio metrics have no such column, see above).
- For straightforward summable-metric key-driver questions, evaluate `AI.KEY_DRIVERS` first (see cross-link) — it skips the `CREATE MODEL` step.
- **Verified: more than 12 dimensions works** (beyond `AI.KEY_DRIVERS`' cap) — 13 low-cardinality dimensions trained successfully, though it took ~13 minutes vs. ~5 seconds for a 3-dimension model on the same data. Keep per-dimension cardinality low when using many dimensions: a separate attempt with 13 dimensions where several were high-cardinality (raw station IDs, individual bike/user IDs) ran over 18 minutes and then failed with a generic internal-error message (framed by BigQuery as "usually a transient issue") rather than a clean validation error.

**Limitations:**
- Metric column values must be non-negative unless `min_apriori_support = 0`.
- `min_apriori_support` and `top_k_insights_by_apriori_support` are mutually exclusive — verified: specifying both errors immediately (`"Please specify only one of the MIN_APRIORI_SUPPORT or TOP_K_INSIGHTS_BY_APRIORI_SUPPORT options."`).
- Dimension columns must be INT64, BOOL, or STRING; NULL-dimension rows are removed.
- No `ML.PREDICT` / `ML.EVALUATE`; produces insights only. **Verified: the actual error messages don't clearly say "not supported for this model type"** — `ML.PREDICT` complains a `contributors` column is missing from the input; `ML.EVALUATE` progressively asks for input data, then a `label` column, neither of which this model type has.
- **Verified: the training query may contain ONLY the columns referenced by `contribution_metric`, `dimension_id_cols`, and `is_test_col`** — any extra column errors immediately (`"Only is_test, dimension id, and contribution metric columns are allowed as input columns for CONTRIBUTION_ANALYSIS models"`), unlike most other model types which tolerate extra passthrough columns.
- Ratio/category `contribution_metric` syntax is strict: `"aliases in the query statement are not supported, please use column names directly"` — reference real columns, not `SELECT ... AS alias` names.

**Locations:** Standard BigQuery ML region/multi-region support; no external connection or endpoint involved.

**BigFrames API:** No dedicated class — verified by listing every submodule of the live installed `bigframes.ml` package (`cluster`, `decomposition`, `ensemble`, `forecasting`, `linear_model`, `remote`, etc. — no contribution-analysis module). Run the `CREATE MODEL` / `ML.GET_INSIGHTS` SQL via `session.read_gbq_query()` or `%%bigquery` magics.

**Repo example (tested):** `models/contribution_analysis/` (this project) — full lifecycle on `bigquery-public-data.new_york_citibike.citibike_trips`, using the same test/control split as the `AI.KEY_DRIVERS` sibling notebook (`../bigquery-ai/functions/ai_key_drivers/`) for direct comparison, plus all three metric-type schemas, the >12-dimension test, and the pruning/mutual-exclusivity options.


---
