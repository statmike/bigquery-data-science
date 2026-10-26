# BigQuery Data Science Namespace & Prerequisite Matrix

Contents:
- [Why Namespace Prefix != Skill Folder](#why-namespace-prefix--skill-folder)
- [BigQuery Edition Reservation Requirements](#bigquery-edition-reservation-requirements)
- [Trained Models (`CREATE MODEL` in `bigquery-ml`)](#trained-models-create-model-in-bigquery-ml)
- [Model Lifecycle & Model-Free Functions (`ML.*` in `bigquery-ml`)](#model-lifecycle--model-free-functions-ml-in-bigquery-ml)
- [Generative, Foundation & Managed Functions (`AI.*` & `VECTOR_SEARCH` in `bigquery-ai`)](#generative-foundation--managed-functions-ai--vector_search-in-bigquery-ai)
- [Pre-Trained Cloud AI Service Models & Object Infrastructure (`bigquery-ai`)](#pre-trained-cloud-ai-service-models--object-infrastructure-bigquery-ai)
- [Production MLOps, Registry, Monitoring & Feature Store (`bigquery-mlops`)](#production-mlops-registry-monitoring--feature-store-bigquery-mlops)

## Why Namespace Prefix != Skill Folder

BigQuery's SQL prefix (`ML.*` vs `AI.*`) reflects when a feature was introduced and whether a `MODEL` DDL handle exists — **not** whether a model is trained or which operational skill governs it:

- **Cross-prefix placement in [`bigquery-ml`](../../bigquery-ml/SKILL.md)**: `AI.CAUSAL_EFFECT` uses the `AI.*` prefix (model-free interrupted time-series counterfactual TVF) but is documented in `bigquery-ml` alongside `ARIMA_PLUS` and the econometric causal inference workflows (`difference_in_differences`, `synthetic_control`, `propensity_score_matching`, `price_elasticity_dml`, `uplift_cate`).
- **Cross-prefix placement in [`bigquery-ai`](../../bigquery-ai/SKILL.md)**: `ML.PROCESS_DOCUMENT`, `ML.TRANSLATE`, `ML.UNDERSTAND_TEXT`, `ML.ANNOTATE_IMAGE`, and `ML.TRANSCRIBE` use `CREATE MODEL ... OPTIONS(REMOTE_SERVICE_TYPE = '...')` and `ML.*` TVFs, plus legacy `ML.GENERATE_TEXT` and `ML.GENERATE_EMBEDDING`, and are documented in `bigquery-ai`.
- **Cross-domain operationalization in [`bigquery-mlops`](../../bigquery-mlops/SKILL.md)**: `EXPORT MODEL`, imported models (`ONNX`, `XGBOOST`, `TENSORFLOW`, `TENSORFLOW_LITE`), `REMOTE WITH CONNECTION` (`endpoint = 'https://...'`), `TRANSFORM_ONLY`, `ML.VALIDATE_DATA_DRIFT`, `ML.VALIDATE_DATA_SKEW`, `ML.METRICS`, `ML.ENTITY_FEATURES_AT_TIME`, `ML.FEATURES_AT_TIME`, and the 8 production orchestrators apply across native BQML models, `AI.*` foundation workflows, and external models logging to BigQuery. See [`cross-skill-playbooks.md`](cross-skill-playbooks.md) for multi-skill composition patterns.

## BigQuery Edition Reservation Requirements

Most BigQuery ML and BigQuery AI features run on standard on-demand pricing, **except** three surfaces that strictly require a BigQuery **`ENTERPRISE` (or `ENTERPRISE_PLUS`) Edition reservation**:

1. **`MATRIX_FACTORIZATION` (`CREATE MODEL` in `bigquery-ml`)** — requires a `QUERY` assignment on an `ENTERPRISE` reservation.
2. **SQL Image Preprocessing (`ML.DECODE_IMAGE`, `ML.RESIZE_IMAGE`, `ML.CONVERT_COLOR_SPACE`, `ML.CONVERT_IMAGE_TYPE` in `bigquery-ml`)** — all four functions fail on on-demand pricing even on inline `FROM_BASE64` bytes; require an `ENTERPRISE` reservation.
3. **Vector Index Background Maintenance (`ALTER VECTOR INDEX` in `bigquery-ai`)** — requires a `BACKGROUND` assignment on an `ENTERPRISE` reservation in the dataset's region.

## Trained Models (`CREATE MODEL` in `bigquery-ml`)

| Symbol | Skill | Category | Connection Required | Reservation Required | Status | Walkthrough |
| --- | --- | --- | --- | --- | --- | --- |
| `LINEAR_REG` | `bigquery-ml` | Regression | None | On-demand OK | GA | `bigquery-ml/narrative/linear_regression.md` |
| `LOGISTIC_REG` | `bigquery-ml` | Classification | None | On-demand OK | GA | `bigquery-ml/narrative/logistic_regression.md` |
| `BOOSTED_TREE_CLASSIFIER` | `bigquery-ml` | Classification (XGBoost) | None | On-demand OK | GA | `bigquery-ml/narrative/boosted_tree_classifier.md` |
| `BOOSTED_TREE_REGRESSOR` | `bigquery-ml` | Regression (XGBoost) | None | On-demand OK | GA | `bigquery-ml/narrative/boosted_tree_regressor.md` |
| `RANDOM_FOREST_CLASSIFIER` | `bigquery-ml` | Classification | None | On-demand OK | GA | `bigquery-ml/narrative/random_forest_classifier.md` |
| `RANDOM_FOREST_REGRESSOR` | `bigquery-ml` | Regression | None | On-demand OK | GA | `bigquery-ml/narrative/random_forest_regressor.md` |
| `DNN_CLASSIFIER` | `bigquery-ml` | Deep Neural Network | None | On-demand OK | GA | `bigquery-ml/narrative/dnn_classifier.md` |
| `DNN_REGRESSOR` | `bigquery-ml` | Deep Neural Network | None | On-demand OK | GA | `bigquery-ml/narrative/dnn_regressor.md` |
| `WIDE_AND_DEEP_CLASSIFIER` / `DNN_LINEAR_COMBINED_CLASSIFIER` | `bigquery-ml` | Wide & Deep Network | None | On-demand OK | GA | `bigquery-ml/narrative/wide_and_deep_classifier.md` |
| `WIDE_AND_DEEP_REGRESSOR` / `DNN_LINEAR_COMBINED_REGRESSOR` | `bigquery-ml` | Wide & Deep Network | None | On-demand OK | GA | `bigquery-ml/narrative/wide_and_deep_regressor.md` |
| `AUTOML_CLASSIFIER` | `bigquery-ml` | AutoML Tabular | None | On-demand OK | GA | `bigquery-ml/narrative/automl_classifier.md` |
| `AUTOML_REGRESSOR` | `bigquery-ml` | AutoML Tabular | None | On-demand OK | GA | `bigquery-ml/narrative/automl_regressor.md` |
| `ARIMA_PLUS` | `bigquery-ml` | Univariate Forecasting (`TIME_SERIES_TIMESTAMP_COL`, `TIME_SERIES_DATA_COL`) | None | On-demand OK | GA | `bigquery-ml/narrative/arima_plus.md` |
| `ARIMA_PLUS_XREG` | `bigquery-ml` | Covariate Forecasting (`TIME_SERIES_TIMESTAMP_COL`, `TIME_SERIES_DATA_COL`) | None | On-demand OK | GA | `bigquery-ml/narrative/arima_plus_xreg.md` |
| `KMEANS` | `bigquery-ml` | Clustering | None | On-demand OK | GA | `bigquery-ml/narrative/kmeans.md` |
| `PCA` | `bigquery-ml` | Dimensionality Reduction | None | On-demand OK | GA | `bigquery-ml/narrative/pca.md` |
| `AUTOENCODER` | `bigquery-ml` | Representation / Anomaly | None | On-demand OK | GA | `bigquery-ml/narrative/autoencoder.md` |
| `MATRIX_FACTORIZATION` | `bigquery-ml` | Collaborative Filtering | None | **Enterprise Reservation (`QUERY`)** | GA | `bigquery-ml/narrative/matrix_factorization.md` |
| `CONTRIBUTION_ANALYSIS` | `bigquery-ml` | Driver Attribution | None | On-demand OK | GA | `bigquery-ml/narrative/contribution_analysis.md` |
| `TRANSFORM_ONLY` | `bigquery-ml` | Reusable Feature Pipeline | None | On-demand OK | GA | `bigquery-ml/narrative/transform_only.md` |
| `TENSORFLOW` / `ONNX` / `XGBOOST` / `TENSORFLOW_LITE` | `bigquery-ml` | Imported GCS Models | Optional (for Object Tables) | On-demand OK | GA | `bigquery-ml/narrative/imported.md` |
| `REMOTE` / `REMOTE WITH CONNECTION` (`endpoint`) | `bigquery-ml` | Vertex AI Endpoint | `CLOUD_RESOURCE` (`roles/aiplatform.user`) | On-demand OK | GA | `bigquery-ml/narrative/remote.md` |

## Model Lifecycle & Model-Free Functions (`ML.*` in `bigquery-ml`)

| Symbol | Skill | Category | Connection Required | Reservation Required | Status | Walkthrough |
| --- | --- | --- | --- | --- | --- | --- |
| `ML.PREDICT` | `bigquery-ml` | Batch Inference | Only for remote models | On-demand OK | GA | `bigquery-ml/narrative/logistic_regression.md` |
| `ML.EVALUATE` | `bigquery-ml` | Model / Prediction Eval | None | On-demand OK | GA | `bigquery-ml/narrative/evaluation.md` |
| `ML.METRICS` | `bigquery-ml` | Model-Free Eval | None | On-demand OK | Preview | `bigquery-ml/narrative/evaluation.md` |
| `ML.ROC_CURVE` / `ML.CONFUSION_MATRIX` | `bigquery-ml` | Classification Eval | None | On-demand OK | GA | `bigquery-ml/narrative/evaluation.md` |
| `ML.FORECAST` / `ML.EXPLAIN_FORECAST` | `bigquery-ml` | Time-Series Inference | None | On-demand OK | GA | `bigquery-ml/narrative/arima_plus.md` |
| `ML.ARIMA_EVALUATE` / `ML.ARIMA_COEFFICIENTS` | `bigquery-ml` | Time-Series Diagnostics | None | On-demand OK | GA | `bigquery-ml/narrative/arima_plus.md` |
| `ML.TREND` / `ML.SEASONALITY` / `ML.DETECT_CHANGE_POINTS` | `bigquery-ml` | Model-Free Time-Series TVFs | None | On-demand OK | Preview | `bigquery-ml/narrative/time_series.md` |
| `AI.CAUSAL_EFFECT` | `bigquery-ml` | Interrupted Time-Series Causal TVF | None | On-demand OK | Preview | `bigquery-ml/narrative/causal_effect.md` |
| `ML.DETECT_ANOMALIES` | `bigquery-ml` | Model-Based Anomaly Detection | None | On-demand OK | GA | `bigquery-ml/narrative/anomaly_fraud_detection.md` |
| `ML.RECOMMEND` | `bigquery-ml` | Collaborative Filtering Eval | None | On-demand OK | GA | `bigquery-ml/narrative/matrix_factorization.md` |
| `ML.GET_INSIGHTS` | `bigquery-ml` | Contribution Analysis Output | None | On-demand OK | GA | `bigquery-ml/narrative/contribution_analysis.md` |
| `ML.EXPLAIN_PREDICT` / `ML.GLOBAL_EXPLAIN` / `ML.FEATURE_IMPORTANCE` / `ML.WEIGHTS` / `ML.ADVANCED_WEIGHTS` | `bigquery-ml` | Explainability & Weights | None | On-demand OK | GA | `bigquery-ml/narrative/evaluation.md` |
| `ML.FEATURES_AT_TIME` / `ML.ENTITY_FEATURES_AT_TIME` | `bigquery-ml` | Point-in-Time Feature Store | None | On-demand OK | GA | `bigquery-ml/narrative/feature_store.md` |
| `ML.DESCRIBE_DATA` / `ML.CORRELATION` | `bigquery-ml` | Exploratory Data Analysis | None | On-demand OK | GA / Preview | `bigquery-ml/narrative/exploration.md` |
| `ML.TF_IDF` / `ML.NGRAMS` / `ML.BAG_OF_WORDS` | `bigquery-ml` | Text Feature Extraction | None | On-demand OK | GA | `bigquery-ml/narrative/text.md` |
| `ML.STANDARD_SCALER` / `ML.MIN_MAX_SCALER` / `ML.ROBUST_SCALER` / `ML.MAX_ABS_SCALER` / `ML.NORMALIZER` | `bigquery-ml` | Numerical Scaling | None | On-demand OK | GA | `bigquery-ml/narrative/scalers.md` |
| `ML.ONE_HOT_ENCODER` / `ML.LABEL_ENCODER` / `ML.MULTI_HOT_ENCODER` | `bigquery-ml` | Categorical Encoding | None | On-demand OK | GA | `bigquery-ml/narrative/encoding.md` |
| `ML.BUCKETIZE` / `ML.QUANTILE_BUCKETIZE` / `ML.HASH_BUCKETIZE` / `ML.IMPUTER` / `ML.POLYNOMIAL_EXPAND` / `ML.FEATURE_CROSS` | `bigquery-ml` | Bucketizing & Feature Crosses | None | On-demand OK | GA | `bigquery-ml/narrative/bucketizing.md` |
| `ML.LP_NORM` / `ML.DISTANCE` / `ML.COSINE_DISTANCE` / `ML.EUCLIDEAN_DISTANCE` / `ML.MANHATTAN_DISTANCE` / `ML.EDIT_DISTANCE` | `bigquery-ml` | Vector & String Distances | None | On-demand OK | GA | `bigquery-ml/narrative/distance.md` |
| `ML.DECODE_IMAGE` / `ML.RESIZE_IMAGE` / `ML.CONVERT_COLOR_SPACE` / `ML.CONVERT_IMAGE_TYPE` | `bigquery-ml` | SQL Image Preprocessing | Optional (Object Table) | **Enterprise Reservation (`QUERY`)** | GA | `bigquery-ml/narrative/image.md` |
| `ML.VALIDATE_DATA_DRIFT` / `ML.VALIDATE_DATA_SKEW` / `ML.TFDV_DESCRIBE` / `ML.TFDV_VALIDATE` | `bigquery-ml` | Data Drift & Skew Monitoring | None | On-demand OK | GA | `bigquery-ml/narrative/model_monitoring.md` |

## Generative, Foundation & Managed Functions (`AI.*` & `VECTOR_SEARCH` in `bigquery-ai`)

| Symbol | Skill | Category | Connection Required | Reservation Required | Status | Walkthrough |
| --- | --- | --- | --- | --- | --- | --- |
| `AI.GENERATE` | `bigquery-ai` | General-Purpose Scalar Gen / Schema | End-user creds (Connection optional) | On-demand OK | GA | `bigquery-ai/narrative/ai_generate.md` |
| `AI.GENERATE_BOOL` / `AI.GENERATE_DOUBLE` / `AI.GENERATE_INT` | `bigquery-ai` | Typed Scalar Generation | End-user creds (Connection optional) | On-demand OK | Preview | `bigquery-ai/narrative/ai_generate_bool.md` |
| `AI.GENERATE_TABLE` | `bigquery-ai` | Structured TVF Generation | `CLOUD_RESOURCE` (`roles/aiplatform.user`) | On-demand OK | GA | `bigquery-ai/narrative/ai_generate_table.md` |
| `AI.GENERATE_TEXT` / `ML.GENERATE_TEXT` | `bigquery-ai` | Remote Model Text TVF | `CLOUD_RESOURCE` (`roles/aiplatform.user`) | On-demand OK | GA | `bigquery-ai/narrative/ai_generate_text.md` |
| `AI.COUNT_TOKENS` | `bigquery-ai` | Local Token Estimator | None | On-demand OK | Preview | `bigquery-ai/narrative/ai_count_tokens.md` |
| `AI.IF` | `bigquery-ai` | Managed Boolean Filter | End-user creds (Connection optional) | On-demand OK | Preview | `bigquery-ai/narrative/ai_if.md` |
| `AI.SCORE` | `bigquery-ai` | Managed Numeric Rubric Scorer | End-user creds (Connection optional) | On-demand OK | Preview | `bigquery-ai/narrative/ai_score.md` |
| `AI.CLASSIFY` | `bigquery-ai` | Managed Category Classifier | End-user creds (Connection optional) | On-demand OK | Preview | `bigquery-ai/narrative/ai_classify.md` |
| `AI.AGG` | `bigquery-ai` | Managed Aggregate Synthesis | End-user creds (Connection optional) | On-demand OK | GA | `bigquery-ai/narrative/ai_agg.md` |
| `AI.EMBED` | `bigquery-ai` | Scalar Text / Multimodal Embedding | None for `embeddinggemma-300m`; Connection for multimodal | On-demand OK | Preview | `bigquery-ai/narrative/ai_embed.md` |
| `AI.GENERATE_EMBEDDING` / `ML.GENERATE_EMBEDDING` | `bigquery-ai` | Remote Model Embedding TVF | `CLOUD_RESOURCE` (`roles/aiplatform.user`) | On-demand OK | GA | `bigquery-ai/narrative/ai_generate_embedding.md` |
| `AI.SIMILARITY` | `bigquery-ai` | Scalar Pairwise Semantic Similarity | None for `embeddinggemma-300m`; Connection for multimodal | On-demand OK | Preview | `bigquery-ai/narrative/ai_similarity.md` |
| `VECTOR_SEARCH` | `bigquery-ai` | Vector & Hybrid RRF Search TVF | Only when query embedding uses remote model | On-demand OK (`ALTER VECTOR INDEX` needs Enterprise `BACKGROUND`) | GA / Preview (hybrid) | `bigquery-ai/narrative/vector_search.md` |
| `AI.SEARCH` | `bigquery-ai` | Simplified Autonomous Search TVF | None (autonomous embedding column) | On-demand OK | GA (`mode` Preview) | `bigquery-ai/narrative/ai_search.md` |
| `AI.FORECAST` | `bigquery-ai` | Zero-Training TimesFM Forecasting | None | On-demand OK | GA (2.5) / Preview (3.0) | `bigquery-ai/narrative/ai_forecast.md` |
| `AI.DETECT_ANOMALIES` | `bigquery-ai` | Zero-Training TimesFM Anomalies | None | On-demand OK | GA | `bigquery-ai/narrative/ai_detect_anomalies.md` |
| `AI.EVALUATE` | `bigquery-ai` | Zero-Training TimesFM / TabFM Eval | None | On-demand OK | GA (TS) / Preview (TabFM) | `bigquery-ai/narrative/ai_evaluate.md` |
| `AI.PREDICT` | `bigquery-ai` | Zero-Training TabFM Prediction | None | On-demand OK | Preview | `bigquery-ai/narrative/ai_predict.md` |
| `AI.KEY_DRIVERS` | `bigquery-ai` | Model-Free Driver Analysis TVF | None | On-demand OK | GA | `bigquery-ai/narrative/ai_key_drivers.md` |
| `AI.PARSE_DOCUMENT` | `bigquery-ai` | **RETIRED (Offline 2026-06-01)** | Replaced by `ML.PROCESS_DOCUMENT` | N/A | Retired | `bigquery-ai/narrative/ai_parse_document.md` |

## Pre-Trained Cloud AI Service Models & Object Infrastructure (`bigquery-ai`)

| Symbol | Skill | Category | Connection Required | Reservation Required | Status | Walkthrough |
| --- | --- | --- | --- | --- | --- | --- |
| `ML.PROCESS_DOCUMENT` | `bigquery-ai` | Document AI (`CLOUD_AI_DOCUMENT_V1`) | `CLOUD_RESOURCE` (`roles/documentai.apiUser` + `serviceUsageConsumer`) | On-demand OK | GA | `bigquery-ai/narrative/ml_process_document.md` |
| `ML.TRANSLATE` | `bigquery-ai` | Cloud Translation (`CLOUD_AI_TRANSLATE_V3`) | `CLOUD_RESOURCE` (`roles/cloudtranslate.user` + `serviceUsageConsumer`) | On-demand OK | GA | `bigquery-ai/narrative/ml_translate.md` |
| `ML.UNDERSTAND_TEXT` | `bigquery-ai` | Cloud Natural Language (`CLOUD_AI_NATURAL_LANGUAGE_V1`) | `CLOUD_RESOURCE` (`roles/serviceusage.serviceUsageConsumer`) | On-demand OK | GA | `bigquery-ai/narrative/ml_understand_text.md` |
| `ML.ANNOTATE_IMAGE` | `bigquery-ai` | Cloud Vision (`CLOUD_AI_VISION_V1`) | `CLOUD_RESOURCE` (`roles/serviceusage.serviceUsageConsumer`) | On-demand OK | GA | `bigquery-ai/narrative/ml_annotate_image.md` |
| `ML.TRANSCRIBE` | `bigquery-ai` | Cloud Speech-to-Text (`CLOUD_AI_SPEECH_V1`) | `CLOUD_RESOURCE` (`roles/speech.client` + `serviceUsageConsumer` + Recon SA grant) | On-demand OK | GA | `bigquery-ai/narrative/ml_transcribe.md` |
| `OBJ.MAKE_REF` / `OBJ.FETCH_METADATA` / `OBJ.GET_ACCESS_URL` / `OBJ.LIST` / `OBJ.READ` | `bigquery-ai` | Unstructured `ObjectRef` Functions | `CLOUD_RESOURCE` (`roles/storage.objectViewer`) | On-demand OK (Object Table + remote model joins may require Enterprise) | GA / Preview | `bigquery-ai/narrative/multimodal_analysis.md` |

## Production MLOps, Registry, Monitoring & Feature Store (`bigquery-mlops`)

For production operationalization across both `bigquery-ml` and `bigquery-ai` (as well as external models served in Vertex AI, Cloud Run, or GKE that log inference tables to BigQuery), consult **[`bigquery-mlops`](../../bigquery-mlops/SKILL.md)**:

| Operational Pillar | Key SQL / Control-Plane Surfaces | Guide in `bigquery-mlops` |
| --- | --- | --- |
| **1. Production Orchestration (8 Engines)** | `sql_scripting`, `scheduled_queries`, `dataform`, `cloud_workflows`, `dbt`, `vertex_kfp`, `composer_airflow`, `airflow_with_kfp` (`useQueryCache: false` / `'false'`) | [`orchestration-and-pipelines.md`](../../bigquery-mlops/reference/orchestration-and-pipelines.md) |
| **2. Model Registry, Export, Import & Hybrid Serving** | `model_registry='VERTEX_AI'`, `EXPORT MODEL` (`xgboost_version='2.1'`), `IMPORT MODEL` (`ONNX`, `XGBOOST`, `TENSORFLOW`, `TENSORFLOW_LITE`), `REMOTE WITH CONNECTION` (`endpoint='https://...'`), `TRANSFORM_ONLY` | [`model-registry-export-and-serving.md`](../../bigquery-mlops/reference/model-registry-export-and-serving.md) |
| **3 & 4. Universal Drift Monitoring & Model-Free Evaluation** | 3-arg `ML.VALIDATE_DATA_DRIFT`, `ML.VALIDATE_DATA_SKEW`, `ML.DESCRIBE_DATA`, `ML.METRICS`, `ML.EVALUATE`, `AI.EVALUATE` | [`monitoring-drift-and-evaluation.md`](../../bigquery-mlops/reference/monitoring-drift-and-evaluation.md) |
| **5. Point-in-Time Feature Store & Skew Audits** | `ML.ENTITY_FEATURES_AT_TIME`, `ML.FEATURES_AT_TIME`, `ignore_feature_nulls`, 3-arm skew audit, Vertex AI Feature Store sync | [`feature-store-and-temporal-joins.md`](../../bigquery-mlops/reference/feature-store-and-temporal-joins.md) |
