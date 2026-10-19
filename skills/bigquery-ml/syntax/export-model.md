# `EXPORT MODEL`

> **Source:** [`bigquery-ml/reference/model-management-monitoring.md#export-model`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/model-management-monitoring.md#export-model)

- **Description:** Statement that copies a trained BigQuery ML model out of BigQuery into a Cloud Storage folder so it can be served outside of BigQuery (locally, in a container, or on Vertex AI Prediction / Agent Platform). The automatic preprocessing learned at training time (standardization, label/one-hot encoding, imputation, etc.) is baked into the exported artifact, so no manual preprocessing is needed before inference on the exported model.
- **Use cases:**
  - Serve a BQML-trained model outside BigQuery (custom container, edge, online endpoint).
  - Hand a model to a downstream team in a portable format (TensorFlow SavedModel or XGBoost Booster).
  - Promote a specific hyperparameter-tuning trial to production (via `TRIAL_ID`).
- **documentation:** [EXPORT MODEL statement](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-export-model) · [Exporting models](https://cloud.google.com/bigquery/docs/exporting-models)
- **Type:** DDL-style statement (model management). Equivalent CLI/API: `bq extract --model` / an extract job.
- **Applies to models:** Most natively-trained model types (see export-format table below). NOT remote models (`REMOTE WITH CONNECTION`), and ARIMA_PLUS / time-series, ONNX-imported, and TFLite-imported models are not exportable. Imported `TENSORFLOW` models export back the exact files that were imported.

**Syntax:**
```sql
EXPORT MODEL `PROJECT_ID.DATASET.MODEL_NAME`
OPTIONS (
  URI = 'gs://BUCKET/path/to/model',   -- destination folder; must match dataset location
  TRIAL_ID = 2                          -- optional; HP-tuning models only
);
```

CLI equivalents:
```bash
# TensorFlow SavedModel (default)
bq extract --model 'DATASET.MODEL_NAME' gs://BUCKET/model_folder
# XGBoost Booster
bq extract --model --destination_format ML_XGBOOST_BOOSTER 'DATASET.MODEL_NAME' gs://BUCKET/model_folder
```

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `MODEL_NAME` | identifier | Yes | — | Backtick-qualified model (`project.dataset.model`). |
| `URI` | STRING | Yes | — | Cloud Storage destination folder, `gs://bucket/folder`. Bucket must be in the same location as the dataset. |
| `TRIAL_ID` | INT64 | No | optimal trial | For HP-tuning models, the trial to export. If omitted, the optimal trial is exported. |
| `--destination_format` (CLI) | enum | No | `ML_TF_SAVED_MODEL` | `ML_TF_SAVED_MODEL` or `ML_XGBOOST_BOOSTER`. Not set in SQL — format is chosen by model type. |

**Outputs:** No result rows. Writes model artifact files to the `URI` folder in GCS. Export format by model type:

| Model type(s) | Export format |
|---|---|
| `LINEAR_REGRESSOR`, `LOGISTIC_REG`, `KMEANS`, `PCA`, `MATRIX_FACTORIZATION`, `AUTOENCODER`, `DNN_*`, `DNN_LINEAR_COMBINED_*`, `TRANSFORM_ONLY` | TensorFlow SavedModel (TF 1.15+) |
| `AUTOML_CLASSIFIER`, `AUTOML_REGRESSOR` | TensorFlow SavedModel (TF 2.1.0) |
| `BOOSTED_TREE_CLASSIFIER`, `BOOSTED_TREE_REGRESSOR`, `RANDOM_FOREST_CLASSIFIER`, `RANDOM_FOREST_REGRESSOR` | XGBoost Booster — **format depends on the training-time `xgboost_version`**: `model.bst` (legacy binary) at the `0.9` default, `model.ubj` (UBJSON) at `2.1`. See the version gotcha below. |
| `TENSORFLOW` (imported) | TensorFlow SavedModel — the exact imported files |

> Note: ONNX is an **import**-only format (`CREATE MODEL ... model_type='ONNX'`), not an EXPORT MODEL output format. EXPORT MODEL produces only TensorFlow SavedModel or XGBoost Booster. See the import-model entries for ONNX.

> TRANSFORM clause: when a model is trained with a `TRANSFORM` clause, the preprocessing model is exported **separately** as a TensorFlow SavedModel (TF 2.5+) under a `transform/` subdirectory of the export folder, alongside the main model artifact (which may itself be XGBoost Booster). Both must be served together for end-to-end inference.

**Status:** GA.
**Connection required:** No (writer needs GCS write permission, not a BigQuery connection).

**Inference-on-exported-model notes:**
- All numerical values in the exported signatures are cast to `FLOAT64`.
- `STRUCT` fields must be flattened: field `f1` in `STRUCT f2` becomes a separate column `f2_f1`.
- All exported models support batch (multi-row) prediction.
- If the model's `TRANSFORM` clause uses Date/Datetime/Time/Timestamp functions, the serving container must include the `bigquery-ml-utils` library (not needed when deploying via Vertex AI Model Registry).

**Best practices:**
- Version exports by writing to a timestamped folder (e.g. `.../models/{TIMESTAMP}/model`) so each export is immutable and reproducible.
- For HP-tuning models, export the chosen `TRIAL_ID` explicitly rather than relying on the implicit optimal trial when you need a pinned, auditable artifact.
- Keep dataset and bucket co-located to avoid the cross-location error — in practice a `US` multi-region dataset **is** compatible with a `US-CENTRAL1` (or other US-region) bucket (verified: export succeeded across that pairing).
- **To visualize a boosted-tree/random-forest ensemble** (`EXPORT MODEL` → XGBoost Booster, `model.bst` or `model.ubj` depending on `xgboost_version`): download it and load with `xgboost.Booster().load_model(...)`, then `xgboost.plot_tree(booster, tree_idx=0)` (the older `num_trees=` keyword still works but emits a `FutureWarning` on xgboost 2.1+). See the gotchas below — they are load-bearing, not optional.
- **If the model exists only to be exported and read back in Python, train it with `xgboost_version = '2.1'`.** It turns a pinned-dependency problem into a plain file read. It is not free, though: on a `BOOSTED_TREE_*` model that trains more than 10 iterations, `'2.1'` also empties `ML.TRAINING_INFO` (measured — see that function's gotcha). `RANDOM_FOREST_*` is single-pass and pays nothing. So set it freely on random forests and on any tree model whose loss curve you don't need; on a boosted tree you're choosing between the modern export and the training history.

**Limitations:**
- Dataset and destination bucket must be in the **same location**.
- Not supported if `ARRAY`, `TIMESTAMP`, or `GEOGRAPHY` feature types were used in input/post-transform data; post-transformed data also cannot be `ARRAY<STRUCT<INT64, FLOAT64>>`.
- `MATRIX_FACTORIZATION` exports have a ~1 GB size cap (reduce `num_factors` if too large).
- AutoML model exports do not support Agent Platform online prediction.
- Models trained with `TRANSFORM` before 2023-09-18 must be retrained for Model Registry online prediction.
- Remote models and ARIMA_PLUS/time-series models cannot be exported.
- **Verified gotcha — XGBoost version compatibility, and how to avoid it entirely:** at the **default** `xgboost_version = '0.9'`, `BOOSTED_TREE_*`/`RANDOM_FOREST_*` exports use a **legacy binary format**. Modern `xgboost` (2.0+, the current `pip install xgboost` default) **cannot load `model.bst`** — `xgb.Booster().load_model(...)` raises `Check failed: str[0] == '{'`. Pin an older release to load/visualize it locally (verified working: `xgboost==1.7.6`, which emits only a compatibility warning). **Training with `xgboost_version = '2.1'` removes the problem at the source:** the export becomes `model.ubj` (UBJSON) instead of `model.bst`, and it loads cleanly in current `xgboost` with no pin and no warning at all (verified end-to-end against `xgboost` 3.3.0, classifier and regressor). The filename changes too, so any download step that hard-codes `model.bst` has to branch on the version. `2.1` reached GA on 2026-08-27 and is opt-in only — the default did not move.
- **Verified gotcha — feature names are not preserved, at either version:** the loaded booster's `feature_names` comes back `None` (generic `f0`, `f1`, ... in `get_dump()`/plots). Set `booster.feature_names` manually to the training query's non-label `SELECT` column order — this 1:1 mapping held up when checked against a model's actual split thresholds (`num_features()` matched the raw column count exactly, with no expansion for categoricals). Verified for both `BOOSTED_TREE_CLASSIFIER` and `BOOSTED_TREE_REGRESSOR`, and re-verified on a `2.1` export — **this one is not fixed by the newer library**, unlike the format gotcha above.
- **`BOOSTED_TREE_REGRESSOR`-specific, and version-dependent:** at the `0.9` default, loading the exported booster also prints `reg:linear is now deprecated in favor of reg:squarederror` — a harmless legacy-objective-name warning (in addition to the `XGBoost < 1.0.0` compatibility warning above), not an error. At `xgboost_version = '2.1'` the objective is written as `reg:squarederror` and the load is silent (verified: zero warnings captured).

**Locations:** Dataset region must equal the GCS bucket region/multi-region.

**BigFrames API:** `bigframes.ml` estimators expose `model.to_gbq(...)` for persistence in BigQuery; GCS export is performed via the SQL `EXPORT MODEL` statement or `bq extract --model`. No dedicated one-call BigFrames GCS-export helper.

**Repo example (tested):**
- `bigquery-ml/models/export/export.ipynb` — the dedicated general-purpose `EXPORT MODEL` notebook: a `LOGISTIC_REG` (→ TF SavedModel, downloaded and run with `tf.saved_model.load()` + `infer(...)` entirely outside BigQuery) and a small `BOOSTED_TREE_CLASSIFIER` (trained with `xgboost_version = '2.1'`, so the export is a `model.ubj` → downloaded and scored locally with an **unpinned** `xgboost` via `booster.get_score(importance_type='gain')`; the `feature_names` gotcha below still applies and is reproduced here independently). Also demonstrates `model_registry='VERTEX_AI'` as a `CREATE MODEL`-time alternative to export (registry storage only, no live serving cost) and the `bq extract --model --destination_format=...` CLI equivalent. **Verified finding:** dropping a model registered via `model_registry='VERTEX_AI'` also cascade-deletes its Vertex AI Model Registry entry — no separate `aiplatform`/`gcloud` deletion step needed.
- `bigquery-ml/models/boosted_tree_classifier/boosted_tree_classifier.sql` (Example 9) and the companion notebook (Step 7) — `xgboost_version = '2.1'` → `EXPORT MODEL` → download `model.ubj` → unpinned `xgboost` → `booster.feature_names` reassigned manually → `xgboost.plot_tree()`. Both gotchas above were caught and verified here, at both `xgboost_version` values.
- The same `EXPORT MODEL ... OPTIONS(URI = 'gs://.../model')` pattern in its other tested homes: [`models/random_forest_classifier/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/random_forest_classifier) (Example 9) and [`models/random_forest_regressor/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/random_forest_regressor) (Example 7) — XGBoost Booster format, tree visualization; [`models/boosted_tree_regressor/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/boosted_tree_regressor) (Example 7); [`models/automl_classifier/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/automl_classifier) (Example 7) and [`models/automl_regressor/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/automl_regressor) (Example 6); [`models/transform_only/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/transform_only) (Example 4) — a transform-only model exports too; [`models/remote/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/remote) (Example 1) — export as the first hop of the train-in-BQML → deploy-to-a-Vertex-endpoint → call-back-as-a-remote-model round trip.
- `PCA` and `AUTOENCODER` export as TensorFlow SavedModel by the same default path as GLMs, DNNs, `KMEANS`, and `TRANSFORM_ONLY` — see [`models/export/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/export) Example 2, which records the verified signature shape (one named input tensor **per feature column**, not one packed array, plus `{label}_probs` / `{label}_values` / `predicted_{label}` outputs and categorical vocabularies written as separate asset files).
- Inverse direction (importing a TF SavedModel back into BQML for serving): [`models/imported/`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/models/imported) — `CREATE MODEL ... model_type = 'TENSORFLOW'`, which the file explicitly cross-references against `EXPORT MODEL`'s quirks in the other direction.


---
