# `ML.FEATURES_AT_TIME`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#mlfeatures_at_time`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlfeatures_at_time)

- **Description:** Model-free table-valued function returning each entity's most recent feature row(s) as of a single shared point in time. Retrieval only — no model, no connection, no training. **GA.**
- **Use cases:**
  - Building the online serving vector for every entity at `CURRENT_TIMESTAMP()`, with the same feature definitions used for training.
  - Materializing a "state of the world as of date X" snapshot for backtesting or reporting.
  - Aggregating each entity's last N updates (`num_rows > 1`) into recency features.
- **documentation:** https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-feature-time
- **Type:** Table-valued function.
- **Applies to models:** None — model-free utility.

**Syntax:**
```sql
ML.FEATURES_AT_TIME(
  { TABLE `project.dataset.feature_table` | (QUERY_STATEMENT) }
  [, time => TIMESTAMP]
  [, num_rows => INT64]
  [, ignore_feature_nulls => BOOL])
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| feature relation | `TABLE` reference or `(QUERY_STATEMENT)` | Yes | — | Must satisfy the contract above. The query form is how you pivot an EAV table on the way in. |
| `time` | `TIMESTAMP` | No | `CURRENT_TIMESTAMP()` | The cutoff. Only rows with `feature_timestamp <= time` are considered. **A single timestamp — not a list.** |
| `num_rows` | `INT64` | No | `1` | Rows returned per entity, most recent first. |
| `ignore_feature_nulls` | `BOOL` | No | `FALSE` | Per feature column, walk back to the most recent row where *that* column is non-`NULL`, independently of the others. |

**Outputs:** `entity_id`, `feature_timestamp`, and every feature column of the input, **in the input's column order** (verified — see below). One row per entity, or `num_rows` per entity.

**Best practices:**
- **Decide `ignore_feature_nulls` from the table's shape, not from the output's appearance.** See the table above. This is the single highest-value decision in using either function.
- **Collapse simultaneous events on write.** Duplicate `(entity_id, feature_timestamp)` pairs make "the most recent row" ambiguous and the tie is broken arbitrarily — a small, silent source of run-to-run variation. A `GROUP BY entity_id, feature_timestamp` in the feature table's build fixes it structurally.
- **Carry a copy of the event time as an ordinary feature column** if you need provenance; see the limitation below.
- Prefer the function to a hand-written `QUALIFY` window even though they are provably equivalent — the hand-written form has a trap the function cannot have (below).

**Limitations:**
- **`time` takes one timestamp, not a list.** `time => [TIMESTAMP '2023-01-01', TIMESTAMP '2024-01-01']` fails with `Unable to coerce type ARRAY<TIMESTAMP> to expected type TIMESTAMP`. For many cutoffs, use `ML.ENTITY_FEATURES_AT_TIME` or `UNION ALL` the calls.
- **The output `feature_timestamp` is the time you asked for, not the time the source row was written.** Provenance is discarded on every row. With `ignore_feature_nulls => TRUE` the returned row is assembled from several source rows at different instants, so no single source time would even be correct — but you also cannot recover when any value was true.
- **`num_rows > 1` returns more history and erases which row is which.** All returned rows carry the same requested `feature_timestamp` and nothing else distinguishes them, so there is nothing to `ORDER BY`. It supports *aggregating* recent history; it cannot support *sequencing* it.
- **The `QUALIFY` equivalent has an alias-shadowing trap.** The default call is exactly `QUALIFY ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY feature_timestamp DESC) = 1` followed by overwriting the timestamp — verified with a two-way `EXCEPT DISTINCT` returning 0 and 0. But BigQuery resolves `QUALIFY` **after** the SELECT list, so writing `TIMESTAMP '2024-01-01' AS feature_timestamp` in that same SELECT makes the window's `ORDER BY feature_timestamp DESC` order by the **constant**. Every row ties, `ROW_NUMBER` picks arbitrarily, and roughly **46%** of 26,979 entities get a different — wrong — vector from a query that runs cleanly and reads correctly. The exact count *moves between runs*, which is the tell. The function has no select list to shadow anything with.
- **Not a gotcha, but easy to get backwards: output column order is preserved.** Several clients sort field names when rendering a row as JSON — including `bq --format=json` — which makes the output look alphabetized. Read the order off the schema, not off a serialized row.

**BigFrames API:** No wrapper. Reach the SQL function via `bigframes.pandas.read_gbq`.

**Repo example (tested):** [`functions/feature_store/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/feature_store) — builds all three table shapes from `thelook_ecommerce` order/shipment/delivery events, captures the three contract errors, proves the `QUALIFY` equivalence and then breaks it with alias shadowing, measures `ignore_feature_nulls` in both directions (repairing 17,440 on sparse, fabricating 1,572 on dense), traces one entity's vector being assembled from three different source rows, and round-trips the EAV pivot to the sparse answer exactly. Used end to end in [`workflows/feature_store/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/feature_store).

---
