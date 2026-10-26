# Universal Table-Native Model Monitoring, Drift Detection & Model-Free Evaluation

Contents: [1. One observability plane for three model populations](#1-one-observability-plane-for-three-model-populations) · [2. Choosing a monitoring or profiling function](#2-choosing-a-monitoring-or-profiling-function) · [3. Choosing an evaluation function (`ML.METRICS` vs `ML.EVALUATE` vs `AI.EVALUATE`)](#3-choosing-an-evaluation-function-mlmetrics-vs-mlevaluate-vs-aievaluate) · [4. Monitoring external Vertex AI / Cloud Run / GKE models logging to BigQuery](#4-monitoring-external-vertex-ai--cloud-run--gke-models-logging-to-bigquery) · [5. Verified empirical gotchas](#5-verified-empirical-gotchas) · [6. Canonical snippets](#6-canonical-snippets) · [7. Go deeper (Lens 3 & Lens 4)](#7-go-deeper-lens-3--lens-4)

Because BigQuery's drift monitoring (`ML.VALIDATE_DATA_DRIFT`), dataset profiling (`ML.DESCRIBE_DATA`), and model-free evaluation (`ML.METRICS`) operate directly on **BigQuery tables with no `MODEL` DDL handle required**, they monitor and score **any model whose inputs and predictions land in BigQuery** — whether that model lives in BigQuery ML, calls a Gemini/TimesFM/TabFM foundation endpoint, or runs outside BigQuery on a Vertex AI Endpoint, Cloud Run service, GKE cluster, or third-party API.

---

## 1. One observability plane for three model populations

| Model Population | Where Inference Runs | How Inputs & Predictions Reach BigQuery | Drift & Skew Check | Accuracy / Quality Check |
| --- | --- | --- | --- | --- |
| **1. Native BQML Models** (`LOGISTIC_REG`, `BOOSTED_TREE_*`, `ARIMA_PLUS`, etc.) | Inside BigQuery (`ML.PREDICT`, `ML.FORECAST`) | Materialized serving tables in BigQuery | `ML.VALIDATE_DATA_SKEW(MODEL ..., TABLE ...)` or 3-arg `ML.VALIDATE_DATA_DRIFT(TABLE base, TABLE serve, ...)` | `ML.EVALUATE(MODEL ..., TABLE ...)` or model-free `ML.METRICS(TABLE ...)` |
| **2. BigQuery AI Foundation Models** (`AI.CLASSIFY`, `AI.SCORE`, `AI.PREDICT`, `AI.FORECAST`, `AI.EMBED`) | Managed Vertex AI foundation endpoints called from SQL | Materialized `AI.*` output tables and `ARRAY<FLOAT64>` embedding columns | 3-arg `ML.VALIDATE_DATA_DRIFT` on input features, output categories, and `ARRAY<FLOAT64>` embedding norm/element distributions | `ML.METRICS` on saved `AI.CLASSIFY` / `AI.PREDICT` / `AI.SCORE` outputs; `AI.EVALUATE` for TimesFM / TabFM |
| **3. External Models (Vertex AI Endpoints, Cloud Run, GKE, Vendor APIs)** | Outside BigQuery | Vertex AI Request-Response Logging to BigQuery, Pub/Sub → BigQuery streaming, or application log export | 3-arg `ML.VALIDATE_DATA_DRIFT(TABLE baseline_logs, TABLE recent_logs, ...)` + `ML.DESCRIBE_DATA` | `ML.METRICS` joining the request-response log table against delayed ground-truth labels on `prediction_id` / `entity_id` |

---

## 2. Choosing a monitoring or profiling function

| Function | Status | Inputs | Requires `MODEL`? | When to Use It |
| --- | --- | --- | --- | --- |
| **`ML.VALIDATE_DATA_DRIFT`** | GA | `TABLE baseline`, `TABLE comparison`, `STRUCT(...)` options *(optional 4th `MODEL` arg only adds a Vertex AI UI link)* | **No** (use the 3-arg form) | **Primary production drift gate.** Compares two arbitrary tables or subqueries (e.g., training baseline vs last 24h serving logs, or last week vs this week) across numeric, categorical, and `ARRAY<FLOAT64>` embedding columns. |
| **`ML.VALIDATE_DATA_SKEW`** | GA | `MODEL model_name`, `TABLE serving_data`, `STRUCT(...)` options | **Yes** (trained BQML model) | Compares new serving data against the training statistics stored inside a BQML model object when the original training table is no longer available. |
| **`ML.TFDV_DESCRIBE` / `ML.TFDV_VALIDATE`** | GA | `TABLE data` (or two proto JSON strings) | **No** | Emits raw TensorFlow Data Validation (`DatasetFeatureStatisticsList` / `Anomalies`) protocol-buffer JSON strings for teams integrating with external TFDV / TFX tools. |
| **`ML.DESCRIBE_DATA`** | GA | `TABLE data` (or subquery), optional `STRUCT(top_k, num_quantiles)` | **No** | **Single-table profiler.** Returns 1 row per column with `num_rows`, `num_nulls`, `min`, `max`, `mean`, `stddev` (not `stdev`), `median`, `quantiles`, `unique`, `top_values`, and array-length stats. Always pair with numeric drift checks. |

---

## 3. Choosing an evaluation function (`ML.METRICS` vs `ML.EVALUATE` vs `AI.EVALUATE`)

| Function | Status | Requires `MODEL`? | Deterministic on Saved Predictions? | Best Fit When... |
| --- | --- | --- | --- | --- |
| **`ML.METRICS`** | Preview | **No** (operates on a `TABLE` with actual and predicted columns) | **Yes** — matches `ML.EVALUATE` to 13+ significant digits and survives `DROP MODEL` | Scoring saved predictions from **external Vertex AI / Cloud Run models**, materialized **`AI.PREDICT` / `AI.CLASSIFY`** outputs, ensembles, or BQML models that have been replaced/deleted. |
| **`ML.EVALUATE`** | GA | **Yes** (or `(MODEL ..., TABLE ...)` with labels) | **Yes** | Standard evaluation of a live BQML `CREATE MODEL` artifact (`LOGISTIC_REG`, `BOOSTED_TREE_*`, `ARIMA_PLUS`, etc.). |
| **`AI.EVALUATE`** | GA (TimesFM) / Preview (TabFM) | **No** | **TimesFM: Yes** (when `model` pinned). **TabFM: No** (runs a fresh internal TabFM pass rather than scoring saved `AI.PREDICT` rows). | Backtesting zero-shot `AI.FORECAST` (`TimesFM 2.5` / `3.0`) or running a quick zero-shot TabFM accuracy check on `<= 50` features. To score *already materialized* `AI.PREDICT` rows deterministically, use **`ML.METRICS`** instead. |

---

## 4. Monitoring external Vertex AI / Cloud Run / GKE models logging to BigQuery

When a model is served outside BigQuery (for example, on a Vertex AI Online Prediction Endpoint with BigQuery Request-Response Logging enabled, or a Cloud Run microservice streaming JSON payloads to BigQuery):

1. **Unpack the Logged Payload into a Typed View or Table**:
   - Extract the request features, `prediction_timestamp`, `entity_id` (or `request_id`), and predicted output (`predicted_label`, `predicted_score`, or `predicted_value`) from the raw JSON/STRUCT log table.
2. **Run Feature & Prediction Distribution Drift (`ML.VALIDATE_DATA_DRIFT`)**:
   - Compare the external model's training baseline table against the unpacked serving log window using the 3-argument `ML.VALIDATE_DATA_DRIFT` call.
3. **Score Delayed Ground-Truth Accuracy (`ML.METRICS`)**:
   - Once ground-truth outcomes arrive in BigQuery (e.g., actual conversion, fraud chargeback, or 30-day churn), join the external model's logged predictions to the actual outcomes into a materialized table and call `ML.METRICS`.
4. **Synthesize Drift & Accuracy Alerts (`AI.AGG`)**:
   - Optionally feed the drifted column rows and `ML.METRICS` summary into `AI.AGG(..., output_schema => ...)` to generate a structured human-readable root-cause brief for on-call engineers.

---

## 5. Verified empirical gotchas

- **Numeric `ML.VALIDATE_DATA_DRIFT` is a 10-bucket per-table histogram JSD, so a single extreme value can multiply reported drift by 4.5x**:
  - Verified live in [`model_monitoring.md`](../../bigquery-ml/narrative/model_monitoring.md): categorical columns (`L_INFTY`, `JENSEN_SHANNON_DIVERGENCE`) compare exact category proportions, but numeric columns build two independent **10-bucket equal-width histograms** over each input table's own `[min, max]`, align them by overlap width, and compute base-2 JSD.
  - Because `education_num` started at `1` in the baseline table and `2` in a 1,116-row comparison slice, the bucket edges were offset and reported JSD `0.181256` (`is_anomaly = TRUE`). Appending **one row** with `education_num = 1` re-aligned the grid and dropped JSD to `0.036175` (`is_anomaly = FALSE`).
  - **Production Fix**: Always inspect `ML.DESCRIBE_DATA`'s `min` and `max` alongside numeric JSD, or discretize numeric features with fixed domain cut-points via `ML.BUCKETIZE` and monitor the resulting bin string as a categorical column.
- **Unordered `LIMIT` sampling manufactures false skew/drift alarms**:
  - Running `SELECT * FROM table LIMIT 5000` (with no `ORDER BY`) grabs physically co-located storage blocks rather than a random sample, triggering false-positive skew alerts (`JSD ~ 0.65`) even when sampling from the model's own training table. Always filter by time window or sample with `WHERE RAND() < p`.
- **`categorical_metric_type` changes which columns trigger alerts**:
  - At the same numeric threshold, `L_INFTY` (max absolute proportion gap) and `JENSEN_SHANNON_DIVERGENCE` flag different categorical columns; pick `L_INFTY` when you want a direct "no category share shifted by more than X percentage points" contract.
- **`ML.METRICS` (and `AI.EVALUATE`) silently change classification math based on `BOOL` vs `STRING` column types**:
  - Verified live in [`evaluation.md`](../../bigquery-ml/narrative/evaluation.md): passing binary actual/predicted columns typed as `BOOL` computes **positive-class binary** precision/recall/F1 (`precision = 0.5238` on 62 test rows), whereas casting those exact same 62 rows to `STRING` (`'true'` / `'false'`) computes **2-class macro-averaged** precision/recall/F1 (`precision = 0.7497`). Always cast to `BOOL` when you want positive-class binary metrics.
- **`ML.METRICS` on an inline `(QUERY)` can fail with internal error `80038528` — always materialize to a `TABLE` first**:
  - Verified live in [`evaluation.md`](../../bigquery-ml/narrative/evaluation.md): passing a `(SELECT ...)` subquery directly to `ML.METRICS` intermittently raises BigQuery internal error `80038528`, whereas materializing the predictions to a table (`CREATE TEMP TABLE` or dataset table) and calling `ML.METRICS(TABLE ...)` succeeds reliably every time.

---

## 6. Canonical snippets

### A. Universal Drift Check on External Model Logs or BQML Serving Tables (No `MODEL` Required)

```sql
-- 1. Compare baseline vs recent serving logs (random sample or time window, never bare LIMIT)
SELECT
  input_feature_name,
  metric,
  value AS drift_score,
  threshold,
  is_anomaly
FROM ML.VALIDATE_DATA_DRIFT(
  (SELECT age, education_num, hours_per_week, workclass FROM `bq_ml.baseline_features`),
  (
    SELECT age, education_num, hours_per_week, workclass
    FROM `bq_ml.external_vertex_request_logs`
    WHERE log_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  ),
  STRUCT(
    0.10 AS categorical_default_threshold,
    0.10 AS numerical_default_threshold,
    'L_INFTY' AS categorical_metric_type
  )
)
ORDER BY is_anomaly DESC, drift_score DESC;
```

### B. Model-Free Evaluation (`ML.METRICS`) on Materialized Predictions (`BOOL` Positive-Class Contract)

```sql
-- 1. Materialize joined actuals + predictions (from BQML, AI.PREDICT, or an external Vertex AI log)
CREATE OR REPLACE TABLE `bq_ml.scored_predictions_eval` AS
SELECT
  CAST(actual_churned AS BOOL) AS actual_label,
  CAST(predicted_churned AS BOOL) AS predicted_label,
  CAST(predicted_probability AS FLOAT64) AS predicted_score
FROM `bq_ml.external_model_predictions_with_labels`;

-- 2. Score with ML.METRICS using the TABLE input form (avoids subquery error 80038528)
SELECT *
FROM ML.METRICS(
  TABLE `bq_ml.scored_predictions_eval`,
  STRUCT(
    'actual_label' AS actual_label_col,
    'predicted_label' AS predicted_label_col,
    'predicted_score' AS predicted_score_col
  )
);
```

---

## 7. Go deeper (Lens 3 & Lens 4)

- **Lens 4 — Worked Walkthroughs (`../../bigquery-ml/narrative/` & `../../bigquery-ai/narrative/`)**:
  - [`model_monitoring.md`](../../bigquery-ml/narrative/model_monitoring.md) (`bigquery-ml/functions/model_monitoring/`) — `ML.VALIDATE_DATA_SKEW`, `ML.VALIDATE_DATA_DRIFT`, `ML.TFDV_DESCRIBE`, `ML.TFDV_VALIDATE`, and the 10-bucket numeric JSD proof
  - [`evaluation.md`](../../bigquery-ml/narrative/evaluation.md) (`bigquery-ml/functions/evaluation/`) — Model-free `ML.METRICS` vs `ML.EVALUATE`, the `BOOL` vs `STRING` precision proof, and the `TABLE` workaround for error `80038528`
  - [`exploration.md`](../../bigquery-ml/narrative/exploration.md) (`bigquery-ml/functions/exploration/`) — `ML.DESCRIBE_DATA` and `ML.CORRELATION` dataset profiling
  - [`ai_evaluate.md`](../../bigquery-ai/narrative/ai_evaluate.md) (`bigquery-ai/functions/ai_evaluate/`) — `AI.EVALUATE` on TimesFM and TabFM
- **Lens 3 — Syntax Cards (`../../bigquery-ml/syntax/` & `../../bigquery-ai/syntax/`)**:
  - [`mlvalidate_data_drift.md`](../../bigquery-ml/syntax/mlvalidate_data_drift.md) · [`mlvalidate_data_skew.md`](../../bigquery-ml/syntax/mlvalidate_data_skew.md) · [`mltfdv_describe.md`](../../bigquery-ml/syntax/mltfdv_describe.md) · [`mltfdv_validate.md`](../../bigquery-ml/syntax/mltfdv_validate.md) · [`mlmetrics.md`](../../bigquery-ml/syntax/mlmetrics.md) · [`mlevaluate.md`](../../bigquery-ml/syntax/mlevaluate.md) · [`mldescribe_data.md`](../../bigquery-ml/syntax/mldescribe_data.md) · [`aievaluate.md`](../../bigquery-ai/syntax/aievaluate.md)
