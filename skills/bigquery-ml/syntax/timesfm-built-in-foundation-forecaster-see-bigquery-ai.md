# TimesFM (built-in foundation forecaster) — see `bigquery-ai`

> **Source:** [`bigquery-ml/reference/create-model-model-types.md#timesfm-built-in-foundation-forecaster--see-bigquery-ai`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ml/reference/create-model-model-types.md#timesfm-built-in-foundation-forecaster--see-bigquery-ai)

> **Cross-link only.** The TimesFM forecaster is a *pretrained* foundation model invoked through the `AI.*` function family, which is owned by the sibling project. For the full entry (syntax, options, inputs/outputs, status), see **[`../bigquery-ai/RESOURCES.md`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/RESOURCES.md)** → `AI.FORECAST`, `AI.EVALUATE`, `AI.DETECT_ANOMALIES`.

- **What it is:** A built-in, pretrained univariate time-series foundation model ([Google Research TimesFM](https://docs.cloud.google.com/bigquery/docs/timesfm-model)). Unlike `ARIMA_PLUS` / `ARIMA_PLUS_XREG`, there is **no `CREATE MODEL` step** — you call `AI.FORECAST` directly on a table or query. Supported model versions: TimesFM 2.5 (default) and TimesFM 3.0 (Preview). **TimesFM 3.0 adds multivariate forecasting with covariates** — `target_cols`, `past_covariate_cols`, `future_covariate_cols` — so "I have external regressors" no longer routes to `ARIMA_PLUS_XREG` by itself; the differences that remain are listed in the table below.
- **Category:** time-series (foundation model). Belongs to the `AI.*` family, **not** the BQML `CREATE MODEL` + `ML.*` lifecycle documented in this project.
- **Connection required:** No.
- **Status:** `AI.FORECAST`, `AI.EVALUATE` and `AI.DETECT_ANOMALIES` — **GA**; multivariate `AI.FORECAST` and the TimesFM 3.0 model option — **Preview**.

**Why it lives in `bigquery-ai`, not here:** TimesFM is not a `model_type` you train with `CREATE MODEL`, and it does **not** use the `ML.*` lifecycle functions (`ML.FORECAST`, `ML.EVALUATE`, `ML.EXPLAIN_FORECAST`, `ML.DETECT_ANOMALIES`). It has no feature preprocessing, no hyperparameter tuning, no model weights, and AI-explanation is N/A. Those `ML.*` lifecycle functions ARE in scope here, but only for the trainable forecasters below.

**In-scope alternative in this project — the trainable forecasters:**

| If you want… | Use (in this project) | Notes |
|---|---|---|
| Zero-training forecast, no `CREATE MODEL` | TimesFM via `AI.FORECAST` → cross-link out | foundation model; `AI.*` family |
| Trained univariate model, full `ML.*` lifecycle + explainability | `ARIMA_PLUS` | supports `ML.FORECAST`, `ML.EVALUATE`, `ML.EXPLAIN_FORECAST`, `ML.DETECT_ANOMALIES` |
| Trained model with external regressors (covariates) | `ARIMA_PLUS_XREG` | adds side features to the ARIMA_PLUS workflow. The zero-training counterpart is `AI.FORECAST` with `model => 'TimesFM 3.0'` (Preview): same idea, no training, no `ML.EXPLAIN_FORECAST`-style per-regressor attribution, no custom holidays, horizon capped at 1,024 and context at 2,048 points, and the future covariates must be supplied as input rows with the target NULL |

**documentation:**
- End-to-end forecasting journey: <https://docs.cloud.google.com/bigquery/docs/e2e-journey-forecast>
- TimesFM model: <https://docs.cloud.google.com/bigquery/docs/timesfm-model>
- `AI.FORECAST` reference: <https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-forecast>
- Forecasting overview (model-type comparison): <https://docs.cloud.google.com/bigquery/docs/forecasting-overview>

**Repo example (tested):** None found in the repo scout — no tested TimesFM/`AI.FORECAST` example exists in `bigquery-ml/` yet.
