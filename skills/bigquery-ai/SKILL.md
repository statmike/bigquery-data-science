---
name: bigquery-ai
description: Use when calling Gemini, TimesFM, TabFM, or pre-trained Cloud AI services from BigQuery SQL or BigFrames — generation (AI.GENERATE*, AI.COUNT_TOKENS), managed scoring/classification (AI.IF, AI.SCORE, AI.CLASSIFY, AI.AGG), embeddings and vector/hybrid search (AI.EMBED, VECTOR_SEARCH, AI.SEARCH), forecasting/prediction (AI.FORECAST, AI.PREDICT, AI.KEY_DRIVERS), and Cloud AI service models (ML.PROCESS_DOCUMENT, ML.TRANSLATE, ML.TRANSCRIBE).
metadata:
  version: "0.7.0"
---

# BigQuery AI (`bigquery-ai`)

BigQuery AI brings foundation models (Gemini, TimesFM, TabFM, EmbeddingGemma, Text/Multimodal Embeddings) and pre-trained Google Cloud AI services directly into SQL and Python (`bigframes.bigquery.ai`) with zero model training.

This skill packages a verified, field-tested 4-Lens reference distilled from live-executing all 29 functions and 14 composed workflows in `bigquery-ai/`.

## Decision Tree (Lens 1 → Lens 2)

1. **Do you want free-form or structured schema output per row** (summaries, multi-field JSON/STRUCT extraction, typed scalars, token counting)? → see [`reference/general-purpose-generation.md`](reference/general-purpose-generation.md)
2. **Do you want a managed, zero-config judgment per row or group** (boolean filter `AI.IF`, numeric rating `AI.SCORE`, fixed-category label `AI.CLASSIFY`, or group synthesis `AI.AGG`)? → see [`reference/managed-functions.md`](reference/managed-functions.md)
3. **Do you need to embed text/multimodal content, compute pairwise similarity, or run vector/hybrid RRF search?** → see [`reference/embeddings-and-search.md`](reference/embeddings-and-search.md)
4. **Do you need zero-training predictions** — forecast a time series (`AI.FORECAST` on TimesFM 2.5 / 3.0), detect anomalies (`AI.DETECT_ANOMALIES`), or predict tabular targets without training (`AI.PREDICT` + `AI.EVALUATE` on TabFM)? → see [`reference/predictive-ai.md`](reference/predictive-ai.md)
5. **Do you need to explain why a summable metric moved (`AI.KEY_DRIVERS`), or estimate the causal impact of an intervention (`AI.CAUSAL_EFFECT`)?** → see [`reference/augmented-analytics.md`](reference/augmented-analytics.md) (which also routes `AI.CAUSAL_EFFECT` to [`../bigquery-ml/reference/workflows-and-pipelines.md`](../bigquery-ml/reference/workflows-and-pipelines.md))
6. **Are you extracting structured records from PDFs/images or passing `ObjectRef` media into `AI.*` functions?** → see [`reference/document-processing.md`](reference/document-processing.md)
7. **Do you need a pre-trained Cloud AI service (`REMOTE_SERVICE_TYPE`) with a fixed API schema and per-row status column** (`ML.TRANSLATE`, `ML.UNDERSTAND_TEXT`, `ML.ANNOTATE_IMAGE`, `ML.TRANSCRIBE`, `ML.PROCESS_DOCUMENT`)? → see [`reference/cloud-ai-service-models.md`](reference/cloud-ai-service-models.md)
8. **Are you composing multiple capabilities into an end-to-end application** (RAG, hybrid catalog search, document intelligence, log triage, content moderation, metric diagnostics)? → see [`reference/workflows.md`](reference/workflows.md)

If the task is ambiguous between zero-training foundation functions (`bigquery-ai`) and trained models (`bigquery-ml`), consult [`../bigquery-data-science/SKILL.md`](../bigquery-data-science/SKILL.md) first.

## Tool Wrapper & Generator Rules (SQL + `bigframes.bigquery.ai`)

- **Dual Surface & Pinned Models**: Always pin the explicit `endpoint` or `model` parameter (`'gemini-2.5-flash'`, `'TimesFM 2.5'`, `'TimesFM 3.0'`, `'embeddinggemma-300m'`, `'text-embedding-005'`, `'gemini-embedding-001'`) from `skills/pinned-models.json` so silent default upgrades never shift outputs. Pair SQL calls with `bigframes.bigquery.ai` / `bigframes.ml.llm` wrappers when generating Python notebooks.
- **Per-Statement Syntax Lookup (Lens 3)**: Before emitting `AI.*`, `VECTOR_SEARCH`, or `OBJ.*` calls, inspect [`syntax/INDEX.md`](syntax/INDEX.md) (or run `bigquery-data-science lookup <SYMBOL>`) to read the exact `< 25 KB` syntax card in `syntax/*.md`.
- **Direct `ObjectRef` Input**: Pass `ObjectRef` columns (from an Object Table's `ref` column, `OBJ.LIST(...)`, or `OBJ.MAKE_REF(uri, connection)`) directly into `AI.GENERATE*`, `AI.CLASSIFY`, `AI.SCORE`, `AI.IF`, `AI.AGG`, and `AI.EMBED` without wrapping in `OBJ.GET_ACCESS_URL`.

## Reviewer Verification Checklist & Rubric

Before returning any `bigquery-ai` SQL or Python code, verify against this checklist:

- [ ] **No Retired `AI.PARSE_DOCUMENT`**: Reject any query using `AI.PARSE_DOCUMENT` (offline since 2026-06-01); replace with `ML.PROCESS_DOCUMENT` or `AI.GENERATE` + `output_schema`.
- [ ] **No Non-Existent `HYBRID_SEARCH` TVF**: Use `VECTOR_SEARCH(..., options => '{"lexical_search_columns": [...]}')` or `AI.SEARCH(..., mode => 'HYBRID')` and size `top_k >= R/10` for target semantic rank `R`.
- [ ] **`output_schema` Field Access**: When `output_schema` is passed to `AI.GENERATE` or `AI.GENERATE_TABLE`, select the schema field names directly (never `.result`, which disappears when `output_schema` is specified).
- [ ] **Subquery Sampling Before `LIMIT`**: Materialize or subquery-limit input rows *before* invoking per-row `AI.*` scalar functions so `LIMIT` does not evaluate and bill the entire table.
- [ ] **Per-Row Status Check on Cloud AI TVFs**: Queries calling `ML.PROCESS_DOCUMENT`, `ML.TRANSLATE`, `ML.UNDERSTAND_TEXT`, `ML.ANNOTATE_IMAGE`, or `ML.TRANSCRIBE` inspect `<function>_status` because per-row failures do not fail the BigQuery job.

## Cross-Cutting Gotchas (Apply Across Functions)

- **`AI.PARSE_DOCUMENT` is offline and its documentation has been withdrawn** (since 2026-06-01). Always use `ML.PROCESS_DOCUMENT` (via a `CLOUD_AI_DOCUMENT_V1` remote model) or `AI.GENERATE` over `ObjectRef`.
- **`output_schema` replaces the `result` field entirely** in `AI.GENERATE` and `AI.GENERATE_TABLE`.
- **`LIMIT` / `OFFSET` on an outer `SELECT` does not reduce billed LLM calls** — filter or `LIMIT` inside a CTE/subquery before calling scalar `AI.*` functions.
- **Pass `ObjectRef` directly to multimodal `AI.*` functions** — `OBJ.GET_ACCESS_URL` is only needed when generating short-lived signed URLs (`<= 6` hours; never persist signed URLs).
- **There is no standalone `HYBRID_SEARCH` function** — hybrid RRF retrieval (`distance = 1 - (1/(60 + rank_vector) + 1/(61 + rank_lexical))`) is enabled via `lexical_search_columns` on `VECTOR_SEARCH` or `mode => 'HYBRID'` on `AI.SEARCH` over a `10 * top_k` semantic pool.
- **Pin `TimesFM 2.5` or `TimesFM 3.0` on `AI.FORECAST`, `AI.DETECT_ANOMALIES`, and `AI.EVALUATE`**; materialize `AI.PREDICT` (TabFM) outputs because TabFM has no version pin and is non-deterministic across runs.
- **Use `AI.COUNT_TOKENS` as a free pre-flight check** before running large paid generative batches.
- **Cloud AI service models (`REMOTE_SERVICE_TYPE`) are handles, not trained models**: `CREATE MODEL` does not validate IAM permissions (`roles/serviceusage.serviceUsageConsumer` on the connection's service account is mandatory), `ML.EVALUATE` is rejected, and errors surface per row in `<function>_status`.

## 4-Lens Index

- **Lens 2 — Use-Case Decision Guides (`reference/`)**:
  - [`reference/general-purpose-generation.md`](reference/general-purpose-generation.md) — `AI.GENERATE`, `AI.GENERATE_TEXT`, `AI.GENERATE_TABLE`, `AI.GENERATE_BOOL`, `AI.GENERATE_DOUBLE`, `AI.GENERATE_INT`, `ML.GENERATE_TEXT`, `AI.COUNT_TOKENS`
  - [`reference/managed-functions.md`](reference/managed-functions.md) — `AI.IF`, `AI.SCORE`, `AI.CLASSIFY`, `AI.AGG`
  - [`reference/embeddings-and-search.md`](reference/embeddings-and-search.md) — `AI.EMBED`, `AI.GENERATE_EMBEDDING`, `ML.GENERATE_EMBEDDING`, `AI.SIMILARITY`, `VECTOR_SEARCH`, `AI.SEARCH`, and hybrid RRF search
  - [`reference/predictive-ai.md`](reference/predictive-ai.md) — `AI.FORECAST`, `AI.DETECT_ANOMALIES`, `AI.PREDICT`, `AI.EVALUATE` (TimesFM & TabFM)
  - [`reference/augmented-analytics.md`](reference/augmented-analytics.md) — `AI.KEY_DRIVERS` and routing for `AI.CAUSAL_EFFECT`
  - [`reference/document-processing.md`](reference/document-processing.md) — `ML.PROCESS_DOCUMENT`, `AI.PARSE_DOCUMENT` (retired), Object Tables, `OBJ.LIST`, `OBJ.MAKE_REF`, `OBJ.FETCH_METADATA`, `OBJ.GET_ACCESS_URL`
  - [`reference/cloud-ai-service-models.md`](reference/cloud-ai-service-models.md) — `ML.TRANSLATE`, `ML.UNDERSTAND_TEXT`, `ML.ANNOTATE_IMAGE`, `ML.TRANSCRIBE`, `ML.PROCESS_DOCUMENT`
  - [`reference/workflows.md`](reference/workflows.md) — 14 composed end-to-end workflows (RAG, hybrid catalog search, document intelligence, tabular prediction, etc.)
- **Lens 3 — Per-Statement Syntax Cards (`syntax/`, < 25 KB each)**: [`syntax/INDEX.md`](syntax/INDEX.md) (44 H2-sliced syntax cards)
- **Lens 4 — Worked Walkthroughs (`narrative/`)**: 43 extracted notebook narratives in `narrative/*.md` (e.g., [`narrative/ai_forecast.md`](narrative/ai_forecast.md), [`narrative/ai_generate.md`](narrative/ai_generate.md), [`narrative/catalog_search.md`](narrative/catalog_search.md))
