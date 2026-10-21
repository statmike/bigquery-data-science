---
name: bigquery-data-science
description: "Use FIRST when someone wants to predict, classify, forecast, embed, search, extract, or explain data in BigQuery and needs to choose between a trained model (bigquery-ml — CREATE MODEL + ML.*), a zero-training generative or foundation model function (bigquery-ai — AI.* + TimesFM + TabFM), or a pre-trained Google Cloud AI service model (ML.PROCESS_DOCUMENT, ML.TRANSLATE, ML.UNDERSTAND_TEXT, ML.ANNOTATE_IMAGE, ML.TRANSCRIBE)."
metadata:
  version: "0.9.0"
---

# BigQuery Data Science — Umbrella Router & Triage (`bigquery-data-science`)

BigQuery provides three distinct, composable surfaces for machine learning and AI in SQL and Python (`bigframes`):

1. **Trained Models & Feature Engineering ([`bigquery-ml`](../bigquery-ml/SKILL.md))** — `CREATE MODEL` + `ML.*` across 23 model types, 49 model-free/lifecycle functions (including `ML.ENTITY_FEATURES_AT_TIME` and `ML.DECODE_IMAGE`), 18 end-to-end workflows (including `AI.CAUSAL_EFFECT` and econometric causal inference), and 8 production orchestration pipelines.
2. **Foundation Models & Generative SQL ([`bigquery-ai`](../bigquery-ai/SKILL.md))** — zero-training per-row and table-valued foundation model functions (`AI.GENERATE*`, `AI.IF`, `AI.SCORE`, `AI.CLASSIFY`, `AI.AGG`, `AI.EMBED`, `AI.SEARCH`, `VECTOR_SEARCH`, `AI.FORECAST` on TimesFM, `AI.DETECT_ANOMALIES`, `AI.KEY_DRIVERS`, `AI.PREDICT` + `AI.EVALUATE` on TabFM).
3. **Pre-Trained Cloud AI Service Models ([`bigquery-ai`](../bigquery-ai/SKILL.md))** — `CREATE MODEL ... OPTIONS(REMOTE_SERVICE_TYPE = '...')` consumed via `ML.PROCESS_DOCUMENT`, `ML.TRANSLATE`, `ML.UNDERSTAND_TEXT`, `ML.ANNOTATE_IMAGE`, and `ML.TRANSCRIBE`.

Before writing SQL or Python, check the [Namespace & Prerequisite Matrix (`reference/namespace-matrix.md`)](reference/namespace-matrix.md) to verify whether a symbol requires a Cloud Resource Connection, IAM role, or BigQuery Enterprise Edition reservation.

## 5 Canonical Skill Patterns

1. **Router Pattern (Triage First)** — Run through the 9 diagnostic questions below to route the task to [`bigquery-ml`](../bigquery-ml/SKILL.md), [`bigquery-ai`](../bigquery-ai/SKILL.md), or a composed pipeline of both.
2. **Inversion Pattern (Ask Before Guessing)** — When a user's request is underspecified (e.g., "forecast sales" without specifying horizon, covariates, holiday calendars, or reproducibility requirements), present 2–3 concrete options with their measured tradeoffs rather than silently picking one.
3. **Tool Wrapper Pattern (Dual SQL & `bigframes`)** — Pair BigQuery SQL with the matching `bigframes.ml` / `bigframes.bigquery.ai` Python wrapper when a notebook or DataFrame workflow is requested, and use `bigquery-data-science lookup <SYMBOL>` or MCP `lookup_bigquery_syntax` to fetch exact option signatures.
4. **Generator Pattern (Idempotent Templates)** — Emit self-contained SQL/Python templates with explicit model/endpoint pins (checked against `skills/pinned-models.json`), deterministic splits (`FARM_FINGERPRINT`), and point-in-time feature joins (`ML.ENTITY_FEATURES_AT_TIME`).
5. **Reviewer Pattern (Verification Rubric)** — Audit generated queries against the cross-domain gotchas below (no retired `AI.PARSE_DOCUMENT`, no unpinned `endpoint`, no leaky `GROUP BY` feature joins, no missing reservation warnings for `MATRIX_FACTORIZATION` or `ML.DECODE_IMAGE`).

## 9 Triage Questions — Ask Yourself (or the User) First

1. **Do you have labeled historical data, and do you want a model that improves as data grows and retrains on a schedule?**
   - Yes → [`bigquery-ml`](../bigquery-ml/SKILL.md).
   - No / zero-setup baseline → [`bigquery-ai`](../bigquery-ai/SKILL.md).
2. **Do you need coefficient-level interpretability, p-values, feature attribution, or a deterministic audit trail?**
   - Yes → [`bigquery-ml`](../bigquery-ml/SKILL.md) (`ML.WEIGHTS`, `ML.ADVANCED_WEIGHTS`, `ML.GLOBAL_EXPLAIN`, `ML.FEATURE_IMPORTANCE`, `ML.EXPLAIN_PREDICT`).
3. **Is the task naturally expressed as a natural-language instruction or schema extraction** ("is this compliant?", "extract line items", "score 1–10", "summarize per category")?
   - Yes → [`bigquery-ai`](../bigquery-ai/SKILL.md) (`AI.IF`, `AI.SCORE`, `AI.CLASSIFY`, `AI.AGG`, `AI.GENERATE`, `AI.GENERATE_TABLE`).
4. **For tabular regression or classification, do you need reproducible predictions, > 50 feature columns, or > 10 classes?**
   - Yes → [`bigquery-ml`](../bigquery-ml/SKILL.md) (`LINEAR_REG`, `LOGISTIC_REG`, `BOOSTED_TREE_CLASSIFIER`, `BOOSTED_TREE_REGRESSOR`).
   - No, and you want a zero-training baseline on a small table (<= 50 features, <= 10 classes) → `AI.PREDICT` + `AI.EVALUATE` (TabFM in [`bigquery-ai`](../bigquery-ai/SKILL.md)).
5. **For time series, are you forecasting the future or decomposing the past?**
   - **Forecasting with custom holidays, hierarchy, `ML.EXPLAIN_FORECAST` decomposition, or horizon > 1,024** → `ARIMA_PLUS` / `ARIMA_PLUS_XREG` ([`bigquery-ml`](../bigquery-ml/SKILL.md)).
   - **Forecasting with zero training (univariate or multivariate/covariates up to 1,024 steps)** → `AI.FORECAST` with `model => 'TimesFM 2.5'` or `'TimesFM 3.0'` ([`bigquery-ai`](../bigquery-ai/SKILL.md)).
   - **Decomposing past trend, seasonality, or structural level shifts with no forecast** → `ML.TREND`, `ML.SEASONALITY`, `ML.DETECT_CHANGE_POINTS` ([`bigquery-ml`](../bigquery-ml/SKILL.md)).
6. **For root-cause metric attribution ("why did conversion drop?"), do you have > 12 dimensions or a ratio/category metric?**
   - Yes → `CONTRIBUTION_ANALYSIS` + `ML.GET_INSIGHTS` ([`bigquery-ml`](../bigquery-ml/SKILL.md)).
   - No (<= 12 dimensions, summable metric) → `AI.KEY_DRIVERS` ([`bigquery-ai`](../bigquery-ai/SKILL.md)).
7. **Is the input unstructured text, PDFs, images, or audio needing embeddings, semantic/hybrid search, or multimodal generation?**
   - Yes → [`bigquery-ai`](../bigquery-ai/SKILL.md) (`AI.EMBED`, `VECTOR_SEARCH`, `AI.SEARCH`, `AI.GENERATE*` over `ObjectRef`).
8. **Is the task solved by a pre-trained Google Cloud AI API where you need a versioned schema and per-row status column?**
   - Yes → Cloud AI service models in [`bigquery-ai`](../bigquery-ai/SKILL.md) (`ML.PROCESS_DOCUMENT`, `ML.TRANSLATE`, `ML.UNDERSTAND_TEXT`, `ML.ANNOTATE_IMAGE`, `ML.TRANSCRIBE`).
9. **Do you need causal treatment-effect estimation or production MLOps retraining & drift monitoring?**
   - Yes → [`bigquery-ml`](../bigquery-ml/SKILL.md) (`AI.CAUSAL_EFFECT`, `difference_in_differences`, `synthetic_control`, `propensity_score_matching`, `price_elasticity_dml`, `uplift_cate`, `ML.VALIDATE_DATA_DRIFT`, and 8 orchestration pipelines).

## 10 Empirical Head-to-Head Comparisons

1. **Forecasting (`ARIMA_PLUS` / `ARIMA_PLUS_XREG` vs `AI.FORECAST`)**: `AI.FORECAST` requires no `CREATE MODEL` and with `model => 'TimesFM 3.0'` (Preview) accepts `target_cols`, `past_covariate_cols`, and `future_covariate_cols` (capped at 1,024 horizon steps and 2,048 context points). `ARIMA_PLUS` and `ARIMA_PLUS_XREG` add custom holiday calendars, hierarchical reconciliation, `ML.EXPLAIN_FORECAST` decomposition, and `ML.ARIMA_COEFFICIENTS`.
2. **Time-Series Decomposition (`ML.EXPLAIN_FORECAST` vs `ML.TREND` / `ML.SEASONALITY`)**: Tested on the same Citi Bike series, `ML.SEASONALITY` produces weekly and yearly components **bit-identical** to `ARIMA_PLUS`'s `ML.EXPLAIN_FORECAST` (`corr 1.0`, `mean abs diff 0.0`) with zero model training. `ML.TREND` defaults `adjust_step_changes => FALSE` whereas `ARIMA_PLUS` defaults to `TRUE`.
3. **Change Points vs Anomalies vs Dataset Drift (`ML.DETECT_CHANGE_POINTS` vs `AI.DETECT_ANOMALIES` / `ML.DETECT_ANOMALIES` vs `ML.VALIDATE_DATA_DRIFT`)**: `ML.DETECT_CHANGE_POINTS` detects persistent level shifts (and gap-fills missing dates first — profile for ingestion outages before trusting change points!); `AI.DETECT_ANOMALIES` and `ML.DETECT_ANOMALIES` flag point spikes; `ML.VALIDATE_DATA_DRIFT` compares feature distributions across two tables.
4. **Driver Attribution (`CONTRIBUTION_ANALYSIS` vs `AI.KEY_DRIVERS`)**: `AI.KEY_DRIVERS` (GA) is a single model-free TVF call for summable metrics with `<= 12` dimensions; `CONTRIBUTION_ANALYSIS` handles `> 12` dimensions plus summable-by-ratio and summable-by-category metrics.
5. **Causal Counterfactuals (`AI.CAUSAL_EFFECT` vs Econometric Panel Estimators)**: `AI.CAUSAL_EFFECT` (documented in `bigquery-ml`) is a model-free interrupted time-series counterfactual on a single treated series (needs `> 1` year pre-history when annual seasonality is active). When untreated control units exist, prefer `difference_in_differences` or `synthetic_control`.
6. **Tabular Prediction (`LINEAR_REG` / `BOOSTED_TREE_*` vs `AI.PREDICT` & `ML.EVALUATE` vs `AI.EVALUATE`)**: `AI.PREDICT` (TabFM) needs zero training but caps at 50 features and 10 classes, and its predictions are **non-deterministic** across identical runs. `AI.EVALUATE` scores its own internal pass rather than materialized `AI.PREDICT` outputs, whereas `ML.EVALUATE` and `ML.METRICS` deterministically score saved predictions.
7. **Unstructured Classification (Trained Classifier vs `AI.CLASSIFY`)**: `AI.CLASSIFY` classifies text or `ObjectRef` media into a fixed category list with zero labeled data; `BOOSTED_TREE_CLASSIFIER` or `LOGISTIC_REG` over `AI.EMBED` features (`embeddings_classification`) is cheaper and faster at high row volume once labeled data exists.
8. **Embeddings (`PCA` / `AUTOENCODER` / `MATRIX_FACTORIZATION` vs `AI.EMBED` / `AI.GENERATE_EMBEDDING`)**: Use `bigquery-ml` models for structured/tabular entity embeddings; use `AI.EMBED` (`model => 'embeddinggemma-300m'` or `'gemini-embedding-001'`) for text and multimodal embeddings paired with `VECTOR_SEARCH` or `AI.SEARCH`.
9. **Document Extraction (`ML.PROCESS_DOCUMENT` vs `AI.GENERATE_TABLE` / `AI.GENERATE`)**: Never use `AI.PARSE_DOCUMENT` (retired 2026-06-01). Use `ML.PROCESS_DOCUMENT` with a Document AI processor when you need a deterministic layout/invoice schema and per-row `ml_process_document_status`; use `AI.GENERATE` with `output_schema` over `ObjectRef` when you need custom ad-hoc field extraction without provisioning a processor.
10. **Pre-Trained Cloud AI Services vs Generative Prompts (`ML.TRANSLATE` / `ML.UNDERSTAND_TEXT` / `ML.ANNOTATE_IMAGE` / `ML.TRANSCRIBE` vs `AI.GENERATE`)**: Cloud AI service models provide fixed taxonomies and per-row error reporting (`ML.TRANSCRIBE` is the one non-deterministic member). Combine both by persisting the service output column and running `AI.GENERATE` or `AI.AGG` over it.

## Routing Links

- **Prerequisite & Namespace Matrix (Lens 2)**: [`reference/namespace-matrix.md`](reference/namespace-matrix.md)
- **BigQuery ML Skill (`CREATE MODEL`, `ML.*`, Feature Store, Causal, Pipelines)**: [`../bigquery-ml/SKILL.md`](../bigquery-ml/SKILL.md)
- **BigQuery AI Skill (`AI.*`, Cloud AI Service Models, Vector/Hybrid Search, RAG)**: [`../bigquery-ai/SKILL.md`](../bigquery-ai/SKILL.md)
