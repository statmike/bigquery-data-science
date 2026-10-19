# 7. Point-in-time feature retrieval: which of the two?

> **Source:** [`bigquery-ml/reference/comparison-tables.md#7-point-in-time-feature-retrieval-which-of-the-two`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/comparison-tables.md#7-point-in-time-feature-retrieval-which-of-the-two)

| You need | Function |
|---|---|
| One shared cutoff for every entity — serving *now*, or one snapshot date | [`ML.FEATURES_AT_TIME`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlfeatures_at_time) |
| A different cutoff per entity — a training set, an audit sample | [`ML.ENTITY_FEATURES_AT_TIME`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-free-functions.md#mlentity_features_at_time) |
| Both against one feature table | That is offline/online parity — see [`workflows/feature_store/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/workflows/feature_store) |

> **`ignore_feature_nulls` is a property of the table's shape, not a default to copy.** On a **sparse** history it repairs entities whose latest row simply did not carry that feature; on a **dense** one it invents a value from an older, different event. Neither call errors and neither output looks wrong — [`functions/feature_store/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/functions/feature_store) measures both directions on the same table.
