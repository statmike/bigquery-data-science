# Point-in-Time Feature Store, Temporal Joins & Training/Serving Skew Audits

Contents: [1. Two SQL TVFs that replace a dedicated feature store for batch & training](#1-two-sql-tvfs-that-replace-a-dedicated-feature-store-for-batch--training) · [2. Table shape decides `ignore_feature_nulls` (`TRUE` vs `FALSE`)](#2-table-shape-decides-ignore_feature_nulls-true-vs-false) · [3. The 3-arm training/serving skew audit](#3-the-3-arm-trainingserving-skew-audit) · [4. Syncing BigQuery feature tables to Vertex AI Feature Store for online serving](#4-syncing-bigquery-feature-tables-to-vertex-ai-feature-store-for-online-serving) · [5. Verified empirical gotchas](#5-verified-empirical-gotchas) · [6. Canonical snippets](#6-canonical-snippets) · [7. Go deeper (Lens 3 & Lens 4)](#7-go-deeper-lens-3--lens-4)

A feature store exists to solve two problems: **point-in-time correctness during training** (preventing future feature values from leaking into historical labeled events) and **offline/online parity during serving** (computing training and serving vectors from the exact same feature table). BigQuery solves both natively in SQL via `ML.ENTITY_FEATURES_AT_TIME` and `ML.FEATURES_AT_TIME`, and pairs directly with **Vertex AI Feature Store** when sub-10ms online key-value lookups are required outside BigQuery.

---

## 1. Two SQL TVFs that replace a dedicated feature store for batch & training

Both functions require the feature history table to have a `STRING` column named **`entity_id`** and a `TIMESTAMP` column named **`feature_timestamp`** (names are case-insensitive; types are strictly enforced):

| Function | Status | Cutoff Timestamp | Primary Use Case | Key Contract & Limits |
| --- | --- | --- | --- | --- |
| **`ML.ENTITY_FEATURES_AT_TIME`** | GA | **One timestamp per entity row**, supplied by a second `entity_table` relation (`entity_id STRING`, `time TIMESTAMP`) | **Assembling leak-free training sets** where every labeled event occurred at its own historical instant | `entity_table` is capped at **100 MB**; drops extra columns from `entity_table` (re-join your label on `(entity_id, feature_timestamp)`); acts as an **INNER join** (cold-start entities with no history at or before `time` are omitted). |
| **`ML.FEATURES_AT_TIME`** | GA | **One shared scalar `time` `TIMESTAMP`** across all entities (defaults to `CURRENT_TIMESTAMP()`) | **Batch serving** or single-date backtest snapshots | Rejects `ARRAY<TIMESTAMP>`; returns every entity that has at least one row at or before `time`. |

---

## 2. Table shape decides `ignore_feature_nulls` (`TRUE` vs `FALSE`)

`ignore_feature_nulls` is **not** a hyperparameter to tune — it is a declaration of how your feature history table is structured. Picking the wrong setting neither errors nor warns, yet silently corrupts thousands of rows (verified live on 26,979 customers in [`feature_store.md`](../../bigquery-ml/narrative/feature_store.md)):

| Feature Table Shape | What One Row Represents | What `NULL` Means | Required `ignore_feature_nulls` Setting | Measured Impact on 26,979 Customers |
| --- | --- | --- | --- | --- |
| **Sparse Event Stream** | A single event update touching only 1–2 features (e.g., a shipment row leaves `lifetime_orders` `NULL`) | "This event did not update this feature — carry forward the latest non-null value" | **`ignore_feature_nulls => TRUE`** | **Repaired 17,440 entities** whose latest event was a shipment/delivery rather than an order placement. |
| **Dense Snapshot Table** | A complete state snapshot at `feature_timestamp` | "This feature is genuinely unknown or not yet applicable at this timestamp" (e.g., `delivery_days` on an order still in transit) | **`ignore_feature_nulls => FALSE`** *(default)* | Setting `TRUE` on a dense table **fabricated delivery durations for 1,572 customers** whose latest order was cancelled or still in transit by pulling an earlier order's delivery duration! |
| **Entity-Attribute-Value (EAV)** | `(entity_id, feature_timestamp, feature_name, feature_value)` | Feature was not emitted at that timestamp | Pivot to wide format first, then set **`ignore_feature_nulls => TRUE`** | Verified to round-trip bit-identically to the sparse wide table answer. |

---

## 3. The 3-arm training/serving skew audit

When a team joins labeled events to a `GROUP BY entity_id` "latest feature row" view instead of `ML.ENTITY_FEATURES_AT_TIME`, future events leak into training features. Neither `CREATE MODEL` nor `ML.EVALUATE` warns you — in fact, the leaky model reports a **much higher offline metric** (`roc_auc` **0.9387** vs the honest point-in-time model's **0.5194** in [`feature_store_workflow.md`](../../bigquery-ml/narrative/feature_store_workflow.md)).

To prove whether an existing pipeline suffers from temporal feature leakage, run the **3-Arm Skew Audit** on a shared deterministic `FARM_FINGERPRINT` split (`data_split_method = 'NO_SPLIT'`):

1. **Arm A (Leaky Offline Eval)**: Train on latest-row `GROUP BY` features, evaluate on latest-row holdout (`roc_auc = 0.9387` — illusory lift).
2. **Arm B (Honest Point-in-Time Eval)**: Train on `ML.ENTITY_FEATURES_AT_TIME` features, evaluate on point-in-time holdout (`roc_auc = 0.5194` — true historical signal).
3. **Arm C (Production Reality Check — Leaky Model Scored on Point-in-Time Features)**: Run `ML.EVALUATE(MODEL arm_a_leaky_model, TABLE arm_b_point_in_time_eval_features)`. When fed the point-in-time features that production actually has at prediction time, Arm A's `roc_auc` **collapses from `0.9387` to `0.5299`**, proving that 100% of the apparent advantage was future leakage.

---

## 4. Syncing BigQuery feature tables to Vertex AI Feature Store for online serving

When an application outside BigQuery (such as a real-time checkout service or a Vertex AI Endpoint) needs millisecond key-value feature lookups for a single `entity_id`:

- **Keep BigQuery as the single source of truth**: Author your feature table or view in BigQuery (including `AI.EMBED` vectors or `ML.*` engineered features) with `entity_id STRING` and `feature_timestamp TIMESTAMP`.
- **Use `ML.ENTITY_FEATURES_AT_TIME` in BigQuery for offline training**, and register the same BigQuery table/view as a **Vertex AI Feature View** backed by a Vertex AI Feature Online Store (Bigtable or Optimized online serving) for low-latency online retrieval.
- **Always tear down Online Store nodes** in non-production environments when finished testing (`feature_online_store.delete(force=True)`), as online serving nodes bill continuously by the hour.

---

## 5. Verified empirical gotchas

- **`ML.ENTITY_FEATURES_AT_TIME` drops extra columns from `entity_table` and performs an INNER join**:
  - Only `entity_id`, `feature_timestamp` (renamed from `entity_table.time`), and the feature columns are returned — your label column and event ID must be joined back on `(entity_id, feature_timestamp)`.
  - If an entity has **no feature row at or before its requested `time`** (a cold-start entity), `ML.ENTITY_FEATURES_AT_TIME` **drops the row entirely** rather than returning `NULL` features (verified live: 26,979 requests placed 1 day before each customer's first event returned `0` rows). If cold-start entities matter at serving time, `LEFT JOIN` your `entity_table` onto the `ML.ENTITY_FEATURES_AT_TIME` result.
- **Hand-written `QUALIFY ROW_NUMBER()` temporal joins suffer from an alias-shadowing trap**:
  - Writing `SELECT ..., TIMESTAMP '2025-01-01' AS feature_timestamp FROM features WHERE feature_timestamp <= TIMESTAMP '2025-01-01' QUALIFY ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY feature_timestamp DESC) = 1` resolves `feature_timestamp` inside `QUALIFY` to the **SELECT-list constant alias**, making every row tie and returning an arbitrary historical row for ~46% of entities! Always use `ML.FEATURES_AT_TIME` or alias the constant to a distinct column name (`as_of_time`).
- **Simultaneous `(entity_id, feature_timestamp)` rows break determinism**:
  - If two updates for the same `entity_id` share the exact same `feature_timestamp`, tie-breaking is arbitrary across runs. Pre-aggregate feature updates to one row per `(entity_id, feature_timestamp)` before calling either function.
- **Shared deterministic split (`FARM_FINGERPRINT`) is mandatory when comparing feature arms**:
  - Never use `data_split_method = 'RANDOM'` or `'AUTO_SPLIT'` when comparing two feature-engineering arms, as each model receives a different holdout set. Materialize `MOD(ABS(FARM_FINGERPRINT(CONCAT(entity_id, CAST(event_time AS STRING)))), 10) >= 8 AS is_eval` once and train both models with `data_split_method = 'NO_SPLIT'` (or `data_split_col = 'is_eval'`, `data_split_method = 'CUSTOM'`).

---

## 6. Canonical snippets

### A. Leak-Free Training Set Assembly (`ML.ENTITY_FEATURES_AT_TIME`) + Cold-Start-Safe Label Join

```sql
-- Assemble point-in-time features for each labeled event and preserve cold-start rows via LEFT JOIN
WITH entity_events AS (
  SELECT
    order_id,
    CAST(user_id AS STRING) AS entity_id,
    created_at AS time,
    will_repurchase_30d AS label
  FROM `bq_ml.labeled_order_events`
),
pit_features AS (
  SELECT *
  FROM ML.ENTITY_FEATURES_AT_TIME(
    TABLE `bq_ml.customer_feature_history`,
    TABLE entity_events,
    num_rows => 1,
    ignore_feature_nulls => TRUE
  )
)
SELECT
  e.order_id,
  e.entity_id,
  e.time AS event_timestamp,
  e.label,
  p.lifetime_orders,
  p.rolling_90d_spend,
  p.days_since_prev_order
FROM entity_events AS e
LEFT JOIN pit_features AS p
  ON e.entity_id = p.entity_id
 AND e.time = p.feature_timestamp;
```

### B. Online / Batch Serving Vector Retrieval (`ML.FEATURES_AT_TIME` + `ML.PREDICT`)

```sql
SELECT
  entity_id,
  predicted_label,
  predicted_label_probs
FROM ML.PREDICT(
  MODEL `bq_ml.repurchase_classifier`,
  (
    SELECT *
    FROM ML.FEATURES_AT_TIME(
      TABLE `bq_ml.customer_feature_history`,
      time => CURRENT_TIMESTAMP(),
      num_rows => 1,
      ignore_feature_nulls => TRUE
    )
  )
);
```

---

## 7. Go deeper (Lens 3 & Lens 4)

- **Lens 4 — Worked Walkthroughs (`../../bigquery-ml/narrative/`)**:
  - [`feature_store.md`](../../bigquery-ml/narrative/feature_store.md) (`bigquery-ml/functions/feature_store/`) — `ML.FEATURES_AT_TIME` and `ML.ENTITY_FEATURES_AT_TIME` across dense, sparse, and EAV tables, the `ignore_feature_nulls` proof in both directions, the `QUALIFY` alias-shadowing trap, and the cold-start inner-join proof
  - [`feature_store_workflow.md`](../../bigquery-ml/narrative/feature_store_workflow.md) (`bigquery-ml/workflows/feature_store/`) — End-to-end 3-arm training/serving skew audit (`0.9387` leaky → `0.5299` collapse vs `0.5194` honest) and query-cache trap proof
- **Lens 3 — Syntax Cards (`../../bigquery-ml/syntax/`)**:
  - [`7-point-in-time-feature-retrieval-which-of-the-two.md`](../../bigquery-ml/syntax/7-point-in-time-feature-retrieval-which-of-the-two.md) · [`point-in-time-feature-retrieval-mlfeatures_at_time-mlentity_features_at_time.md`](../../bigquery-ml/syntax/point-in-time-feature-retrieval-mlfeatures_at_time-mlentity_features_at_time.md) · [`mlentity_features_at_time.md`](../../bigquery-ml/syntax/mlentity_features_at_time.md) · [`mlfeatures_at_time.md`](../../bigquery-ml/syntax/mlfeatures_at_time.md)
