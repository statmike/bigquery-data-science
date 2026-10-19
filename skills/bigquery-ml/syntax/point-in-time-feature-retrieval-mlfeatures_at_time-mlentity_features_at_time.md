# Point-in-time feature retrieval: `ML.FEATURES_AT_TIME`, `ML.ENTITY_FEATURES_AT_TIME`

> **Source:** [`bigquery-ml/reference/model-free-functions.md#point-in-time-feature-retrieval-mlfeatures_at_time-mlentity_features_at_time`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#point-in-time-feature-retrieval-mlfeatures_at_time-mlentity_features_at_time)

Two model-free table-valued functions that answer *"what did we know about this entity at this moment?"* — the question a feature store exists to answer. `ML.FEATURES_AT_TIME` retrieves every entity's vector as of **one shared timestamp** (the online-serving shape); `ML.ENTITY_FEATURES_AT_TIME` retrieves each entity's vector as of **its own timestamp** (the training-set shape, and what prevents label leakage). Neither trains a model, neither needs a connection, and neither creates an object to clean up. There is no feature store to provision — the feature table is an ordinary BigQuery table.

Both take the same **feature table contract**: a `STRING` column named `entity_id`, a `TIMESTAMP` column named `feature_timestamp`, and one column per feature (wide format). Column names are **case-insensitive** — verified live, `Entity_ID` and `Feature_TimeStamp` are accepted and the original casing is preserved in the output — but the *types* are not negotiable, and all three violations fail at planning time:

| Violation | Error |
|---|---|
| `entity_id` is `INT64` | `feature_table column 'entity_id' can only be String type but found INT64` |
| `feature_timestamp` is `DATE` | `feature_table column 'feature_timestamp' can only be Timestamp type but found DATE` |
| `feature_timestamp` absent | `feature_table must include a 'feature_timestamp' column` |

**The one thing to carry away:** `ignore_feature_nulls` is a statement about your table's **shape**, not a tuning knob. It is *required* on a sparse history and *harmful* on a dense one, with no error and no visibly wrong output either way.

| Feature table shape | One row is… | A `NULL` means… | `ignore_feature_nulls => TRUE` |
|---|---|---|---|
| **Sparse** (assembled from independent event streams) | one *update* touching a subset of features | this update had nothing to say about that feature | **Required** — reassembles the vector |
| **Dense** (one row per complete observation) | a complete observation | genuinely unknown or not applicable — a *fact* | **Harmful** — fabricates values |
| **EAV** (`entity_key, feature_timestamp, feature_name, feature_value STRUCT<…>`) | one *observation* of one feature | absent rather than `NULL` | Pivots to the sparse shape, so **required** |

Measured on `thelook_ecommerce` at a fixed 2024-01-01 cutoff over 26,979 customers: on the sparse table the flag repaired **17,440** entities whose `lifetime_orders` came back `NULL` only because their most recent row was a shipment or a delivery (down to **0**, with the genuine absences surviving). On the dense table the identical flag invented a delivery duration for **1,572** customers whose latest order was cancelled, processing, or shipped-but-not-arrived — a real measurement of a *different, earlier* order.

---
