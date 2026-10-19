# `ML.ENTITY_FEATURES_AT_TIME`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mlentity_features_at_time`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlentity_features_at_time)

- **Description:** Model-free table-valued function returning each entity's most recent feature row(s) as of **its own** requested point in time, supplied by a second relation. This is the training-set builder: one row per labeled event, features as of that event's instant. **GA.**
- **Use cases:**
  - Assembling a leakage-free training set where every row's features predate its own label window.
  - Backfilling features for an arbitrary set of `(entity, moment)` pairs — an audit sample, a set of support tickets, a batch of decisions to review.
  - Reconstructing what a scoring system would have seen at each historical decision point.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-entity-feature-time
- **Type:** Table-valued function.
- **Applies to models:** None — model-free utility.

**Syntax:**
```sql
ML.ENTITY_FEATURES_AT_TIME(
  { TABLE `project.dataset.feature_table`     | (FEATURE_QUERY_STATEMENT) },
  { TABLE `project.dataset.entity_time_table` | (ENTITY_TIME_QUERY_STATEMENT) }
  [, num_rows => INT64]
  [, ignore_feature_nulls => BOOL])
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| feature relation | `TABLE` reference or `(QUERY_STATEMENT)` | Yes | — | Same contract as `ML.FEATURES_AT_TIME`: `entity_id STRING`, `feature_timestamp TIMESTAMP`, wide. |
| entity time relation | `TABLE` reference or `(QUERY_STATEMENT)` | Yes | — | Needs `entity_id STRING` and a `TIMESTAMP` column named **`time`** — *not* `feature_timestamp`. Must be **no larger than 100 MB** (documented). |
| `num_rows` | `INT64` | No | `1` | Rows returned per row of the entity time table. |
| `ignore_feature_nulls` | `BOOL` | No | `FALSE` | Same per-column walk-back as `ML.FEATURES_AT_TIME`. |

**Outputs:** `entity_id`, `feature_timestamp` (**the requested instant**, i.e. the entity table's `time`), and the feature columns. Nothing else.

**Best practices:**
- **Join the label back on `(entity_id, feature_timestamp)`.** The requested instant comes back under the feature table's name for it, which makes the join natural once you expect it.
- **Assert the row count against the entity table before training.** One line, and it is the only thing standing between you and a silently truncated training set.
- **`LEFT JOIN` the entity table back on** if cold-start entities matter, and decide explicitly what a missing vector means (a `0`, a global default, or exclusion by choice rather than by accident).

**Limitations:**
- **There is no `time` argument** — the entity table *is* the time argument. The naming asymmetry (`time` here, `feature_timestamp` there) is the most common first mistake.
- **The entity table's extra columns are dropped.** Only `entity_id` and the requested time come back. Your label is exactly such a column.
- **It is an INNER join.** An entity with no feature row at or before its requested instant is **omitted**, not returned with `NULL` features. Verified: 26,979 requests placed one day before each customer's first event returned **0** rows. The dropped rows are not a random sample — they are precisely the cold-start cases (new customers, new products, the first weeks of any entity's life). Dropping them makes a training set look cleaner and a model look better while removing the population it will most often be asked about.
- **100 MB cap on the entity time relation.** Documented, and a real constraint for large training sets — `entity_id` plus `time` for tens of millions of rows will exceed it. Partition the build by time window or entity range and `UNION ALL` the results.
- The output `feature_timestamp` carries the same loss of provenance described under `ML.FEATURES_AT_TIME`.

**Related — choosing between the two:**

| You need | Function |
|---|---|
| One shared cutoff for every entity (serving *now*, or one snapshot date) | [`ML.FEATURES_AT_TIME`](mlfeatures_at_time.md) |
| A different cutoff per entity (a training set, an audit sample) | `ML.ENTITY_FEATURES_AT_TIME` |
| Both, against one feature table | That is offline/online parity — see [`workflows/feature_store/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/feature_store) |

**BigFrames API:** No wrapper. Reach the SQL function via `bigframes.pandas.read_gbq`.

**Repo example (tested):** [`functions/feature_store/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/feature_store) covers the mechanics — dropped columns, the inner-join cold-start check, and the `time`/`feature_timestamp` asymmetry. [`workflows/feature_store/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/feature_store) measures what it is worth: the same feature history queried with a naive `GROUP BY entity_id` versus point-in-time, on a shared hash split, reports `roc_auc` **0.9387** against **0.5194** — and the leaky model, fed the point-in-time features production can actually supply, collapses to **0.5299**, where the honest model already was.
