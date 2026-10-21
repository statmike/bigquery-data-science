---
name: bigquery-ml
description: Use when training, evaluating, deploying, or monitoring a machine learning model in BigQuery with SQL (CREATE MODEL and ML.* functions) — picking a model type, choosing a preprocessing function, point-in-time feature retrieval, causal inference (including AI.CAUSAL_EFFECT), or production retraining pipelines across 23 model types, 49 functions, 18 workflows, and 8 pipelines.
metadata:
  version: "0.9.1"
---

# BigQuery ML (`bigquery-ml`)

BigQuery ML trains and serves models with SQL and Python (`bigframes.ml`): `CREATE MODEL` selects an algorithm via `model_type`, and `ML.*` functions evaluate, predict, explain, and monitor it — no data leaves BigQuery.

This skill packages a verified, field-tested 4-Lens reference distilled from live-executing all 23 model types, 49 functions, 18 workflows, and 8 orchestration pipelines in `bigquery-ml/`.

## Decision Tree (Lens 1 → Lens 2)

1. **Do you have a labeled target to predict?**
   - Categorical label → see [`reference/classification.md`](reference/classification.md)
   - Continuous numeric label → see [`reference/regression.md`](reference/regression.md)
   - No label (clustering, dimensionality reduction, recommendations, `ARIMA_PLUS`/`ARIMA_PLUS_XREG` forecasting, model-free `ML.TREND`/`ML.SEASONALITY`/`ML.DETECT_CHANGE_POINTS`, or `CONTRIBUTION_ANALYSIS`) → see [`reference/unsupervised-and-specialized.md`](reference/unsupervised-and-specialized.md)
2. **Are you managing, deploying, or monitoring an existing model** (importing TF/TFLite/ONNX/XGBoost, calling a Vertex AI Endpoint via `REMOTE WITH CONNECTION`, exporting a BQML model, or checking drift/skew) → see [`reference/model-management.md`](reference/model-management.md)
   - **`REMOTE WITH CONNECTION` builds two different things:** `OPTIONS(endpoint = 'https://...')` is your deployed Vertex AI Endpoint consumed with `ML.PREDICT` ([`reference/model-management.md`](reference/model-management.md)). `OPTIONS(REMOTE_SERVICE_TYPE = '...')` is a handle to a pre-trained Google Cloud AI service (`ML.TRANSLATE`, `ML.UNDERSTAND_TEXT`, `ML.ANNOTATE_IMAGE`, `ML.TRANSCRIBE`, `ML.PROCESS_DOCUMENT`) documented in [`../bigquery-ai/reference/cloud-ai-service-models.md`](../bigquery-ai/reference/cloud-ai-service-models.md).
3. **Are you exploring or preprocessing data independent of any model type** (`ML.DESCRIBE_DATA`, `ML.CORRELATION`, scalers, bucketizers, encoders, `ML.IMPUTER`, `ML.FEATURES_AT_TIME` / `ML.ENTITY_FEATURES_AT_TIME`, text, distance, or SQL image preprocessing) → see [`reference/preprocessing-functions.md`](reference/preprocessing-functions.md)
   - **Image tensor functions (`ML.DECODE_IMAGE`, `ML.RESIZE_IMAGE`, `ML.CONVERT_COLOR_SPACE`, `ML.CONVERT_IMAGE_TYPE`)** require a BigQuery `ENTERPRISE` Edition reservation and fail on on-demand pricing.
4. **Are you composing an end-to-end workflow or scheduling a production pipeline** (drift-check → conditional retrain → score across 8 orchestrators) → see [`reference/workflows-and-pipelines.md`](reference/workflows-and-pipelines.md)
5. **Are you estimating the causal effect of an intervention or treatment?** → see the causal cluster in [`reference/workflows-and-pipelines.md`](reference/workflows-and-pipelines.md): `propensity_score_matching`, `price_elasticity_dml`, `uplift_cate`, `difference_in_differences`, `synthetic_control`, and `causal_effect` (`AI.CAUSAL_EFFECT`, documented in `bigquery-ml` so all causal estimators live side by side).
6. **Do you already have saved predictions and just need evaluation metrics?** → `ML.METRICS` requires no model object; see [`reference/regression.md`](reference/regression.md) and [`reference/classification.md`](reference/classification.md).
7. **Are you joining historical features to labeled events?** → use `ML.ENTITY_FEATURES_AT_TIME` / `ML.FEATURES_AT_TIME` in [`reference/preprocessing-functions.md`](reference/preprocessing-functions.md) and the `feature_store_workflow` narrative in [`narrative/feature_store_workflow.md`](narrative/feature_store_workflow.md).

If the task is ambiguous between trained models (`bigquery-ml`) and zero-training foundation models (`bigquery-ai`), consult [`../bigquery-data-science/SKILL.md`](../bigquery-data-science/SKILL.md) first.

## Tool Wrapper & Generator Rules (SQL + `bigframes.ml`)

- **Dual Surface Generation**: When generating code for notebooks or Python pipelines, pair the canonical `CREATE OR REPLACE MODEL` + `ML.*` SQL with the equivalent `bigframes.ml` estimator (`bigframes.ml.linear_model`, `bigframes.ml.ensemble`, `bigframes.ml.forecasting`, `bigframes.ml.cluster`, `bigframes.ml.decomposition`) when a `bigframes` wrapper exists.
- **Per-Statement Syntax Lookup (Lens 3)**: Before emitting unfamiliar `CREATE MODEL` options or `ML.*` TVF signatures, inspect [`syntax/INDEX.md`](syntax/INDEX.md) (or run `bigquery-data-science lookup <SYMBOL>`) to read the exact `< 25 KB` syntax card in `syntax/*.md`.
- **Transform & Export Discipline**: Wrap preprocessing functions (`ML.STANDARD_SCALER`, `ML.ONE_HOT_ENCODER`, `ML.IMPUTER`) inside a `TRANSFORM(...)` clause so `ML.PREDICT` applies identical train-time statistics at serving time. Pin `xgboost_version = '2.1'` when exporting `BOOSTED_TREE_*` or `RANDOM_FOREST_*` models to GCS (`EXPORT MODEL`).

## Reviewer Verification Checklist & Rubric

Before returning any `bigquery-ml` SQL or Python code, verify against this checklist:

- [ ] **No Future Feature Leakage**: Historical event joins against time-varying feature tables use `ML.ENTITY_FEATURES_AT_TIME` (never a `GROUP BY` or `ROW_NUMBER()` latest-row join) and set `ignore_feature_nulls` deliberately (`TRUE` for sparse/EAV updates, `FALSE` for dense snapshots).
- [ ] **Reservation Gate Disclosed**: Queries using `MATRIX_FACTORIZATION` or `ML.DECODE_IMAGE` / `ML.RESIZE_IMAGE` / `ML.CONVERT_COLOR_SPACE` / `ML.CONVERT_IMAGE_TYPE` explicitly note the BigQuery `ENTERPRISE` Edition reservation requirement.
- [ ] **Interpretable GLM Encoding**: `LINEAR_REG` and `LOGISTIC_REG` models intended for `ML.WEIGHTS` or `ML.ADVANCED_WEIGHTS` set `category_encoding_method = 'DUMMY_ENCODING'`, `calculate_p_values = TRUE`, and `l1_reg = 0` at `CREATE MODEL` time.
- [ ] **Classification Metric Type Parity**: `ML.METRICS` and `ML.EVALUATE` callers cast `BOOL` vs `STRING` label/prediction columns deliberately (binary positive-class vs macro-averaged multiclass).
- [ ] **Cache Bypass After Retrain**: Orchestration pipelines disable the query cache (`useQueryCache: false` or `'false'` in KFP components) on `ML.EVALUATE` / `ML.PREDICT` jobs immediately following `CREATE OR REPLACE MODEL`.

## Cross-Cutting Gotchas (Apply Across Model Types)

- **Query-cache staleness after `CREATE OR REPLACE MODEL`**: Re-running `ML.EVALUATE` right after a retrain can return cached metrics. Pass `useQueryCache: false` (or the string `'false'` in `google_cloud_pipeline_components` KFP ops, whose JSON cleaner strips boolean `False`).
- **Non-determinism is model-type-specific**: `KMEANS` and `RANDOM_FOREST_*` retrain differently every run (no exposed seed), whereas `BOOSTED_TREE_*`, `PCA`, and `DNN_*` reproduce consistently.
- **`ONE_HOT_ENCODING` (GLM default) makes `ML.WEIGHTS` unstable across retrains** due to intercept collinearity — use `category_encoding_method = 'DUMMY_ENCODING'` and `calculate_p_values = TRUE` (`l1_reg = 0`) for `ML.ADVANCED_WEIGHTS`.
- **Encoders and text functions default to `frequency_threshold = 5`** (`ML.ONE_HOT_ENCODER`, `ML.LABEL_ENCODER`, `ML.MULTI_HOT_ENCODER`, `ML.TF_IDF`, `ML.BAG_OF_WORDS`) — categories appearing `< 5` times collapse into the unknown bucket.
- **`MATRIX_FACTORIZATION` and the four image functions (`ML.DECODE_IMAGE`, `ML.RESIZE_IMAGE`, `ML.CONVERT_COLOR_SPACE`, `ML.CONVERT_IMAGE_TYPE`) require an `ENTERPRISE` Edition reservation** and fail on on-demand pricing.
- **Image function struct fields are `dimensions` and `values` (not `shape`)**: `ML.DECODE_IMAGE` always returns 3 channels, `ML.CONVERT_COLOR_SPACE(..., 'GRAYSCALE')` returns 1, `ML.CONVERT_IMAGE_TYPE` is one-way (place it last), and rounding a resize dimension to `0` triggers deterministic error `80038528` (set `job_retry=None`).
- **Joining multiple models' `ML.PREDICT` outputs on raw features fans out duplicate feature rows** — always add a `ROW_NUMBER()` synthetic key before training.
- **`ML.TREND`, `ML.SEASONALITY`, and `ML.DETECT_CHANGE_POINTS` gap-fill series first** — profile for ingestion outages before trusting detected change-point windows.
- **Column type (`BOOL` vs `STRING`) changes `precision`/`recall`/`f1_score` in `ML.METRICS`** (binary positive-class vs macro-averaged 2-class).
- **Latest-row feature joins leak future information (`roc_auc` 0.9387 leaky vs 0.5194 honest)** — always use `ML.ENTITY_FEATURES_AT_TIME`.

## 4-Lens Index

- **Lens 2 — Use-Case Decision Guides (`reference/`)**:
  - [`reference/classification.md`](reference/classification.md) — `LOGISTIC_REG`, `BOOSTED_TREE_CLASSIFIER`, `RANDOM_FOREST_CLASSIFIER`, `DNN_CLASSIFIER`, `DNN_LINEAR_COMBINED_CLASSIFIER`, `AUTOML_CLASSIFIER`
  - [`reference/regression.md`](reference/regression.md) — `LINEAR_REG`, `BOOSTED_TREE_REGRESSOR`, `RANDOM_FOREST_REGRESSOR`, `DNN_REGRESSOR`, `DNN_LINEAR_COMBINED_REGRESSOR`, `AUTOML_REGRESSOR`
  - [`reference/unsupervised-and-specialized.md`](reference/unsupervised-and-specialized.md) — `KMEANS`, `PCA`, `AUTOENCODER`, `MATRIX_FACTORIZATION`, `CONTRIBUTION_ANALYSIS`, `ARIMA_PLUS`, `ARIMA_PLUS_XREG`, `ML.TREND`, `ML.SEASONALITY`, `ML.DETECT_CHANGE_POINTS`
  - [`reference/model-management.md`](reference/model-management.md) — `TRANSFORM_ONLY`, imported models (`TENSORFLOW`, `TENSORFLOW_LITE`, `ONNX`, `XGBOOST`), `REMOTE WITH CONNECTION`, `EXPORT MODEL`, `ML.VALIDATE_DATA_DRIFT`, `ML.VALIDATE_DATA_SKEW`
  - [`reference/preprocessing-functions.md`](reference/preprocessing-functions.md) — `ML.DESCRIBE_DATA`, `ML.CORRELATION`, scalers, bucketizers, encoders, `ML.IMPUTER`, `ML.FEATURES_AT_TIME`, `ML.ENTITY_FEATURES_AT_TIME`, text, distance, image preprocessing
  - [`reference/workflows-and-pipelines.md`](reference/workflows-and-pipelines.md) — 18 composed workflows (including causal inference & `AI.CAUSAL_EFFECT`) and 8 production orchestration pipelines
- **Lens 3 — Per-Statement Syntax Cards (`syntax/`, < 25 KB each)**: [`syntax/INDEX.md`](syntax/INDEX.md) (93 H2-sliced syntax cards)
- **Lens 4 — Worked Walkthroughs (`narrative/`)**: 61 extracted notebook narratives in `narrative/*.md` (e.g., [`narrative/arima_plus.md`](narrative/arima_plus.md), [`narrative/feature_store.md`](narrative/feature_store.md), [`narrative/feature_store_workflow.md`](narrative/feature_store_workflow.md))
