# Changelog

All notable changes to `bigquery-data-science` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.12.0] - 2026-11-13

### Added
- **GA Scalar `AI.PARSE_DOCUMENT` (`31/31` Active BigQuery AI Functions, `0` Retired Functions):**
  - Rewrote and live-executed **`bigquery-ai/functions/ai_parse_document/`** (`.ipynb` + `.sql` + Lens 3 `aiparse_document.md` + Lens 4 narrative) for the relaunched GA scalar `AI.PARSE_DOCUMENT` function (`2026-11-02`, `bigqueryml-syntax-ai-parse-document`).
  - Covers all 4 input shapes (`'gs://...'` URI with End-User Credentials or `connection_id`, `OBJ.MAKE_REF`, `FROM OBJ.LIST('gs://.../*.pdf')`, and Object Table `ref`), both output schemas (`layout-v1` default flat reading-order blocks with HTML `<table>` strings and normalized `[min_y, min_x, max_y, max_x]` bounding boxes vs `raw-docai` nested Document AI layout tree), multi-format extraction (`.pdf`, `.html`, `.docx`, `.xlsx`), per-row `$.errors` handling (`INVALID_ARGUMENT` / `NOT_FOUND` vs SQL `NULL`), and 4-way selection criteria (`AI.PARSE_DOCUMENT` vs `AI.CHUNK_DOCUMENT` vs `AI.GENERATE` vs `ML.PROCESS_DOCUMENT`).
- **`AI.CHUNK_DOCUMENT` 4th Input Shape (`parsed_document` JSON — "Parse Once, Chunk Many Times"):**
  - Updated **`bigquery-ai/functions/ai_chunk_document/`** (`.ipynb` + `.sql` + `aichunk_document.md` + narrative), **`bigquery-ai/workflows/document_rag/`** (`.ipynb` + narrative), and `document-processing.md` with Shape D: passing a table or `(SELECT ..., AI.PARSE_DOCUMENT(ref, options => JSON '{"schema": "raw-docai"}') AS parsed_document FROM ...)` subquery directly to `AI.CHUNK_DOCUMENT` to re-chunk materialized `raw-docai` output at multiple `chunk_size` values (`150`, `250`, `500` tokens) without re-calling Document AI, plus the empirical gotcha that passing default `layout-v1` JSON returns per-row `INVALID_ARGUMENT: Unsupported document schema: layout-v1`.
- **GA `gemini-4-hydrogen` (`2026-11-12`) & `gemini-4-carbon` (`2026-11-10`) Support:**
  - Added `"gemini-4-hydrogen"` and `"gemini-4-carbon"` to `skills/pinned-models.json` (`allowed_models` across all 9 Gemini text/multimodal functions while keeping `gemini-3.8-flash` and `gemini-4-argon` as default cost-efficient endpoints), `bigquery-ai/reference/general-purpose-functions.md`, `bigquery-ai/RESOURCES.md`, and live-executed `ai_generate` and `ai_count_tokens` notebooks and `.sql` companions (including `thinking_level` `"LOW"` / `"MEDIUM"` / `"HIGH"` validation and ignored `temperature` / `top_p` / `top_k` sampling parameters on Gemini 4).
- **New `review-sql` Diagnostics & `bigquery-mlops` Operational Updates:**
  - Added `LEGACY_PARSE_DOCUMENT_TVF` (catches legacy `FROM AI.PARSE_DOCUMENT(TABLE ...)` or `endpoint =>` syntax), `PARSE_DOCUMENT_CHUNK_SCHEMA` (catches chaining `AI.PARSE_DOCUMENT` into `AI.CHUNK_DOCUMENT` without `options => JSON '{"schema": "raw-docai"}'`), and expanded `GEMINI_4_THINKING_BUDGET` across `gemini-4-argon`, `gemini-4-carbon`, and `gemini-4-hydrogen` in `src/bigquery_data_science/catalog.py`.
  - Documented BQML custom Organization Policies (`2026-11-06`, Preview), BigQuery Pipelines & Dataform workflow/action concurrency limits (`2026-11-09`, GA), and automatic Dataplex Universal Catalog / Knowledge Catalog table-level lineage (`2026-11-12`, GA) in `skills/bigquery-mlops/`, and updated 8 renamed upstream documentation URLs across `bigquery-ai/` and `bigquery-ml/`.

## [0.11.0] - 2026-11-02

### Added
- **2 New GA BigQuery AI SQL Functions (`AI.CHUNK_DOCUMENT` & `AI.TRANSLATE`):**
  - **`bigquery-ai/functions/ai_chunk_document/`** (`.sql` + live-executed `.ipynb` + Lens 3 `aichunk_document.md` + Lens 4 narrative): Layout-aware table-valued function that chunks unstructured documents in Cloud Storage (`PDF`, `HTML`, `DOCX`, `PPTX`, `XLSX`, `XLSM`) via direct `'gs://...'` URI literals/wildcards (`13` output columns), `TABLE project.dataset.object_table` (`13` output columns), or `(SELECT ..., OBJ.MAKE_REF(uri) AS ref FROM ...)` subqueries (`5 + N` output columns) with configurable `chunk_size` (`[1, 2000]` tokens, default `1000`), 1-indexed PDF page spans (`start_page`, `end_page`), ancestor section headings prepended, and zero `CREATE MODEL` or manual Document AI processor provisioning.
  - **`bigquery-ai/functions/ai_translate/`** (`.sql` + live-executed `.ipynb` + Lens 3 `aitranslate.md` + Lens 4 narrative): Zero-DDL Cloud Translation Advanced scalar function (`model => 'nmt'` default or `'translation-llm'`) running under caller end-user credentials with dynamic per-row `target_language` and `source_language` column expressions and `return_details => TRUE` diagnostic `STRUCT<result STRING, status STRING, details JSON>` output (`status = 'OK'` on success; `$.detected_language_code`).
- **Unblocked & Rebuilt `bigquery-ai/workflows/document_rag/` (`14/14` AI Workflows Live):**
  - Replaced the retired `AI.PARSE_DOCUMENT` step with `AI.CHUNK_DOCUMENT` $\to$ `AI.EMBED` $\to$ `VECTOR_SEARCH` $\to$ `AI.GENERATE`, restoring full end-to-end execution with page-level provenance citations (`0` blocked workflows remain across all `32` repository workflows).
- **GoogleSQL Reusable Column Aliases, VPC Service Controls `ObjectRef` & Open Embedding `CREATE MODEL` Documentation:**
  - Documented GoogleSQL reusable column aliases (`reusable_column_aliases_mode`, 5-tier resolution precedence, and `|> EXTEND` portable pipe alternative) in `bigquery-ai/reference/general-purpose-functions.md` and `bigquery-ai/overview.ipynb`, VPC Service Controls limitations for `ObjectRef` in `bigquery-ai/setup/README.md` and `bigquery-ai/reference/unstructured-data-infrastructure.md`, and `CREATE MODEL` syntax for open-source Vertex AI embedding models (`bigqueryml-syntax-create-remote-model-embedding-maas`).

### Changed
- **6 BigQuery AI Functions Promoted from Preview to GA:**
  - Promoted `AI.COUNT_TOKENS` (text-only `STRING` signature re-verified at GA), `AI.IF`, `AI.SCORE`, `AI.CLASSIFY` (`optimization_mode` distilled mode remains Preview), `AI.EMBED`, and `AI.SIMILARITY` (built-in `model => 'embeddinggemma-300m'` remains Preview) across reference guides, READMEs, `namespace-matrix.md`, and all 4 Agent Skills with 3-way `check-status-labels` parity.
- **Repository-Wide Model-Currency Modernization (`gemini-3.8-flash`, `gemini-4-argon`, `gemini-3.5-flash-lite`, `gemini-embedding-2`):**
  - Standardized all explicit Flash (`gemini-3.8-flash`), Pro/reasoning (`gemini-4-argon`), Flash-Lite (`gemini-3.5-flash-lite`), and Embedding (`gemini-embedding-2`, 3,072 default dimensions; `outputDimensionality: 768` on `CREATE MODEL`, `AI.GENERATE_EMBEDDING`, and `ML.GENERATE_EMBEDDING`) endpoints across 29 live re-executed notebooks (`0` errors), 2 static notebooks (`generate.ipynb` with `google_search_retrieval` retirement note and `data_enrichment.ipynb`), 19 `.sql` companions, reference guides, and all 4 Agent Skills (`bigquery-data-science`, `bigquery-ml`, `bigquery-ai`, `bigquery-mlops`).
  - Added `preferred_defaults` and `legacy_models` enforcement to `skills/pinned-models.json` and `check-pinned-models` (blocking legacy endpoints outside explicit model-comparison contexts), added a static `review-sql` warning when `task_type` or `title` is used with `gemini-embedding-2` on `AI.EMBED` or `AI.SIMILARITY`, and routed BigFrames LLM/embedding sections through `bigframes.bigquery.ai.*` (`bbq.ai.*`) where `bigframes.ml.llm` client-side allowlists lag behind live BigQuery endpoints.
- **Typed `AI.AGG(..., output_schema => ...)` Across 4 Multi-Function Workflows + `bigquery-ai/overview.ipynb`:**
  - Upgraded and re-executed `log_analysis`, `content_analysis`, `content_moderation`, and `document_intelligence` to synthesize structured `STRUCT` rollups inside `GROUP BY` aggregations, and updated `bigquery-ai/overview.ipynb` with runnable `AI.TRANSLATE`, `AI.CHUNK_DOCUMENT`, and reusable column alias examples.
- **Model Endpoint Allow-List, TabFM Pricing Date, `ML.METRICS` Cross-Links & BigFrames `2.51.0` Parity:**
  - Registered `"nmt"` and `"translation-llm"` in `skills/pinned-models.json`; updated TabFM (`AI.PREDICT` / `AI.EVALUATE`) token billing effective date to `2026-11-17` (`$0.50 / 1M` tokens); added bidirectional cross-links between `ML.METRICS` (`bigquery-ml/functions/evaluation/`) and `AI.PREDICT` (`bigquery-ai/functions/ai_predict/`, `workflows/tabular_prediction/`); documented Dataform `preserveGovernanceControls` GA in `bigquery-mlops` and `bigframes` `2.51.0` wrappers (`bbq.ai.predict`, `bbq.ai.evaluate`, `bbq.ai.embed`, `bbq.ai.similarity`).
- **4-Lens Catalog, CLI/MCP & GitHub Actions Node 24 Modernization:**
  - Resynchronized all `139` Lens 3 syntax cards (`93` ML + `46` AI) and `106` Lens 4 worked narratives (`61` ML + `45` AI; `109` total `.ipynb`, `89` `.sql` scripts), expanded `catalog.py` routing/aliases and `review-sql` static diagnostics, and upgraded `.github/workflows/{ci,release}.yml` to native Node 24 actions (`actions/checkout@v7`, `astral-sh/setup-uv@v10.3.3`, `actions/upload-artifact@v7`, `actions/download-artifact@v8`) removing `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24`.

## [0.10.0] - 2026-10-26

### Added
- **4th Bundled Agent Skill (`skills/bigquery-mlops/`) (`P5.1`):**
  - Added `bigquery-mlops` (`SKILL.md`, `skill.manifest.json`, and 4 Lens 2 operational reference guides under `skills/bigquery-mlops/reference/`) covering the complete operational lifecycle for `CREATE MODEL` (`bigquery-ml`), zero-training `AI.*` (`bigquery-ai`), and external models served on Vertex AI, Cloud Run, or GKE that log features and predictions to BigQuery:
    - `orchestration-and-pipelines.md`: 8 GCP orchestration patterns (Scheduled Queries, Dataform SQLX, Cloud Workflows, Cloud Composer / Managed Airflow Gen 3, Vertex AI Pipelines / KFP, Vertex AI Model Registry, Online Serving, and Feature Store) with `useQueryCache: false` and `xgboost_version = '2.1'` guardrails.
    - `model-registry-export-and-serving.md`: `model_registry = 'VERTEX_AI'`, `EXPORT MODEL` to GCS, `IMPORT MODEL` (`ONNX`, `XGBOOST`, `TENSORFLOW`, `TENSORFLOW_LITE`), `REMOTE WITH CONNECTION`, and `TRANSFORM_ONLY` feature-serving models.
    - `monitoring-drift-and-evaluation.md`: Model-agnostic drift and skew monitoring (`ML.VALIDATE_DATA_DRIFT`, `ML.VALIDATE_DATA_SKEW`, `ML.DESCRIBE_DATA`, `ML.TFDV_DESCRIBE`) and table-based evaluation (`ML.METRICS`, `ML.EVALUATE`, `AI.EVALUATE`) across BQML, `AI.*`, and external models logging to BigQuery.
    - `feature-store-and-temporal-joins.md`: Point-in-time feature retrieval (`ML.ENTITY_FEATURES_AT_TIME`, `ML.FEATURES_AT_TIME`), the `ignore_feature_nulls` table-shape rule, 3-arm training-serving skew audits, and Vertex AI Feature Store synchronization.
- **Multi-Skill Composition Playbooks & 7-Stage Problem-First Navigator (`P5.2` & `P5.3`):**
  - Added `skills/bigquery-data-science/reference/cross-skill-playbooks.md` with 6 concrete multi-skill SQL choreography playbooks (`bigquery-ml` + `bigquery-ai` + `bigquery-mlops`) and a unified 7-stage problem-first index across all 32 workflows and 8 pipelines.
  - Added bidirectional *Composing With Sister Skills* sections to `skills/bigquery-ml/SKILL.md` and `skills/bigquery-ai/SKILL.md` and added the 7-stage problem-first navigator table to `README.md`.
- **Multi-Skill Task Triage (`recommended_skills: list[str]`) (`P5.4`):**
  - Extended `TriageResult` in `src/bigquery_data_science/catalog.py` with `recommended_skills: list[str]` (while preserving `recommended_skill: str` for 100% backward compatibility) and added production MLOps routing to `bigquery-mlops`.
  - Updated `src/bigquery_data_science/installer.py` (`SKILL_NAMES`), `mcp_server.py`, `adk.py`, `plugin.json`, and `.claude-plugin/marketplace.json` to bundle and expose all 4 skills (`bigquery-data-science`, `bigquery-ml`, `bigquery-ai`, `bigquery-mlops`).

## [0.9.1] - 2026-10-21

### Added
- **Notebook-Led `.ipynb` $\to$ `.sql` Companion Parity & Self-Audit Gate (`P4.2` & `P4.3`):**
  - Added `src/bigquery_data_science/tooling/sql_companions.py` and the `bigquery-data-science check-sql-companions` CLI subcommand (integrated into `bigquery-data-science sweep` Stage 7) to verify that every function/model notebook has a paired `.sql` companion covering its primary SQL symbols and that all 87 `.sql` files in `bigquery-ml/` and `bigquery-ai/` pass `review-sql` with zero unexpected errors.
  - Added `sanitize_notebook_outputs` and automatic `.env` loading to `src/bigquery_data_science/tooling/run_notebook.py` so `bigquery-data-science run-notebook` automatically detects the local GCP project from `.env`, `GOOGLE_CLOUD_PROJECT`, or ADC while scrubbing runtime project IDs back to `'your-gcp-project-id'` in saved cell outputs.

### Changed
- **Auto-Detected `PROJECT_ID` Across All 107 Notebooks & 104 Narratives (`P4.1`):**
  - Updated all 107 `.ipynb` setup cells to leave `PROJECT_ID = 'your-gcp-project-id'` in git and auto-detect the active project at runtime from `.env`, `GOOGLE_CLOUD_PROJECT`, or `google.auth.default()[1]`.
  - Updated 61 `%%bigquery --project {PROJECT_ID}` magic cells to use two-part `bq_ml.*` and `bq_ai_functions.*` table/model identifiers (and `@@project_id` in `EXPORT MODEL`), scrubbed all 259 rendered cell outputs to `'your-gcp-project-id'`, and regenerated all 104 `skills/*/narrative/*.md` files.
- **Single-Source `skills/pinned-models.json` & Comment-Aware `review_sql` (`P4.3` & `P4.4`):**
  - Removed the duplicate `_DEFAULT_ALLOWED_MODELS` set from `src/bigquery_data_science/catalog.py` so `review_sql` reads directly from `skills/pinned-models.json` (`_skills/pinned-models.json` in wheels).
  - Updated `review_sql` to strip `--` and `/* ... */` SQL comments before scanning and ignore syntax placeholders and Vertex/Document AI resource paths (`projects/...`, `https://...`).

## [0.9.0] - 2026-10-21

### Added
- **CLI, Catalog, MCP Server & Google ADK Rollout (`P3.1`–`P3.5`):**
  - **MCP `resources` & `prompts` Protocol Support (`P3.1`):** Extended `bigquery-data-science mcp` (`src/bigquery_data_science/mcp_server.py`) with `resources/list`, `resources/templates/list`, and `resources/read` (`bqds://skill/{skill}`, `bqds://reference/{skill}/{name}`, `bqds://syntax/{skill}/{slug}`, `bqds://narrative/{skill}/{topic}`), plus `prompts/list` and `prompts/get` (`design_bigquery_pipeline`, `audit_bigquery_sql`, `compare_ml_vs_ai`, `prevent_feature_leakage`).
  - **Static SQL Query Reviewer (`P3.2`):** Added `review_sql` / `review` in `src/bigquery_data_science/catalog.py`, `bigquery-data-science review-sql <sql_or_file>` CLI command, and the 5th MCP tool `review_bigquery_sql` to statically audit BigQuery SQL queries against `namespace-matrix.md`, `pinned-models.json`, and empirical guardrails (retired functions, nonexistent `HYBRID_SEARCH`, unpinned foundation models, `TimesFM` covariate version requirements, unnecessary `OBJ.GET_ACCESS_URL`, `xgboost_version`, Enterprise reservation requirements, `ignore_feature_nulls`, and `ML.METRICS` `BOOL` semantics).
  - **Opt-In `--json` Output Flag (`P3.3`):** Added `--json` across `list`, `lookup`, `search`, `triage`, and `review-sql` while preserving default human-readable text output.
  - **Opt-In MCP Client Config Registration (`P3.4`):** Added `install_mcp_config` in `src/bigquery_data_science/installer.py` and `bigquery-data-science install --mcp` to non-destructively register the `bigquery-data-science mcp` stdio server in project `.mcp.json` or global `~/.claude.json` / `~/.gemini/settings.json`.
  - **Google ADK Toolset Wrapper (`P3.5`):** Added `src/bigquery_data_science/adk.py` exporting `get_bigquery_tools()` and typed Python tool functions (`triage_bigquery_task`, `lookup_bigquery_syntax`, `search_bigquery_gotchas`, `get_bigquery_walkthrough`, `review_bigquery_sql`) ready for `google.adk.Agent(tools=get_bigquery_tools())`.

## [0.8.2] - 2026-10-21

### Added
- **Maintainer Verification & Execution Gates (`P2.1`–`P2.5`):**
  - `bigquery-data-science check-status-labels`: Verifies `Preview` vs `GA` status label consistency across `bigquery-ai/README.md`, `bigquery-ml/README.md`, `<domain>/reference/*.md`, and `skills/bigquery-data-science/reference/namespace-matrix.md`.
  - `bigquery-data-science check-crossrefs`: Verifies bidirectional link symmetry between workflow notebooks (`**Functions/Models used:**`) and function/model notebooks (`**Featured in:**`).
  - `bigquery-data-science run-notebook`: Headless Jupyter notebook runner wrapping `jupyter_client` and `nbformat` with automatic working-directory resolution, mTLS certificate configuration, `bigquery-data-science` kernelspec stamping, and optional `--sync-narratives`.
  - `bigquery-data-science check-notebook-claims`: Audits high-precision decimal claims in notebook markdown prose against code cells and rendered cell outputs.
  - `bigquery-data-science check-markdown`: Verifies balanced code fences, GFM table column consistency (including zero unescaped `|` pipes inside inline code in table cells), and vertical-first `flowchart TD` Mermaid diagram layout ($\le 3$ parallel horizontal nodes per rank).
  - Integrated `check-status-labels`, `check-crossrefs`, `check-notebook-claims`, and `check-markdown` into `bigquery-data-science sweep` (Stage 7).

### Changed
- **Vertical-First Mermaid Diagram Refactor (`README.md` & `bigquery-ml/README.md`):**
  - Refactored `README.md` architecture diagram from `flowchart LR` to vertical `flowchart TD` and updated `pyproject.toml` `hatch-fancy-pypi-readme` pattern.
  - Refactored `bigquery-ml/README.md` lifecycle diagram to stack `SCORE` (`Evaluate & Score`) and `EXPLAIN` (`Explainability, Weights & Training Metadata`) vertically (`<= 3` nodes wide per rank) for maximum font legibility on GitHub.
- **Status Label & Table Alignment (`namespace-matrix.md`, `managed-functions.md`, `preprocessing-functions.md`):**
  - Synchronized `AI.AGG`, `AI.IF`, `AI.SCORE`, `AI.CLASSIFY`, `AI.EMBED`, `AI.SIMILARITY`, `AI.SEARCH`, and `ML.DECODE_IMAGE` family status labels in `skills/bigquery-data-science/reference/namespace-matrix.md`.
  - Replaced unescaped `||vector||_p` pipe syntax inside the `ML.NORMALIZER` GFM table row in `skills/bigquery-ml/reference/preprocessing-functions.md` with `ML.LP_NORM(vector, p)`.

## [0.8.1] - 2026-10-21

### Added
- **Lockstep Version Stamper (`bigquery-data-science bump-version`):**
  - Added `src/bigquery_data_science/tooling/bump_version.py` and the `bigquery-data-science bump-version [<version>] [--check]` CLI command to stamp or verify Semantic Version parity across `pyproject.toml`, `src/bigquery_data_science/__init__.py`, `CITATION.cff`, `plugin.json`, `.claude-plugin/marketplace.json`, `skills/*/SKILL.md`, `skills/*/skill.manifest.json`, and `tests/test_packaging.py` in a single step.
  - Integrated `check_version_lockstep` into `bigquery-data-science sweep`.
- **Authoring, Readability & Visual Standards (`CONTRIBUTING.md` & `skills/PLANS.md`):**
  - Codified the 100% additive/backward-compatible contract, simple Python/SQL and plain-English guidelines, vertical-first `flowchart TD` Mermaid diagram layout rules ($\le 3$ columns wide), and clean Markdown/table compilation standards.

### Changed
- **GitHub Actions Runner & Node 24 Modernization (`.github/workflows/ci.yml` & `release.yml`):**
  - Pinned `runs-on: ubuntu-24.04` and enabled `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"` across CI and Release workflows.
- **Pre-Commit Hook & Version Fallback Hygiene:**
  - Updated `.pre-commit-config.yaml` to use generic internal-domain regex detection.
  - Replaced hardcoded `"0.7.0"` fallback strings in `src/bigquery_data_science/installer.py` and `src/bigquery_data_science/tooling/manifest.py` with `bigquery_data_science.__version__`.

## [0.8.0] - 2026-10-20

### Added
- **`AI.AGG` Structured Output & Error Tolerance Support:**
  - Added coverage for GA `output_schema` parameter emitting typed `STRUCT` records directly from aggregation via SQL DDL schema strings.
  - Added coverage for GA `max_error_ratio` parameter for fault-tolerant aggregation.
  - Added Section 11 (`output_schema`) and Section 12 (`max_error_ratio`) to `bigquery-ai/functions/ai_agg/ai_agg.ipynb` and matching Examples 9 & 10 to `bigquery-ai/functions/ai_agg/ai_agg.sql`.
- **`gemini-4-argon` Foundation Model Support:**
  - Added `gemini-4-argon` to `skills/pinned-models.json`, `bigquery-ai/RESOURCES.md`, and `bigquery-ai/reference/general-purpose-functions.md`. Verified live via BigQuery.
- **GoogleSQL Reusable Column Aliases GA:**
  - Documented GoogleSQL GA support for referencing `SELECT` aliases inside expressions and `WHERE` clauses.

### Changed
- **`AI.AGG` Status Transition:**
  - Graduated `AI.AGG` from Preview to GA in `bigquery-ai/README.md`, `bigquery-ai/reference/managed-functions.md`, and `skills/bigquery-ai/reference/managed-functions.md`.
- **Skill Progressive Lenses Re-synchronized:**
  - Lens 3 (`skills/bigquery-ai/syntax/aiagg.md`): Regenerated surgical syntax card with `output_schema` and `max_error_ratio` signatures.
  - Lens 4 (`skills/bigquery-ai/narrative/ai_agg.md`): Regenerated textbook narrative from the executed `ai_agg.ipynb`.
  - Refreshed manifests across all 3 agent skills (`bigquery-data-science`, `bigquery-ml`, `bigquery-ai`).

## [0.7.0] - 2026-10-19

### Added
- **Standalone Repository & 1:1 Domain Normalization (`bigquery-ml/` and `bigquery-ai/`):**
  - Extracted and normalized all 61 BigQuery ML notebooks (`bigquery-ml/`) and 43 BigQuery AI notebooks (`bigquery-ai/`) with companion `.sql` scripts, exhaustive `reference/*.md` documentation, and unified `bigquery-data-science` Jupyter kernel metadata.
- **Hybrid 3-Skill Hierarchy & 4-Lens Progressive Disclosure (`skills/`):**
  - `skills/bigquery-data-science/`: Umbrella task router, 10 head-to-head empirical comparisons, cross-namespace composition guide, reviewer rubric, and `reference/namespace-matrix.md` prerequisite matrix.
  - `skills/bigquery-ml/` and `skills/bigquery-ai/`: 4-Lens architecture — Lens 1 (`SKILL.md` routing & cross-cutting gotchas), Lens 2 (`reference/*.md` use-case decision guides), Lens 3 (`syntax/*.md` surgical H2-sliced per-model/per-function syntax cards + `syntax/INDEX.md`), and Lens 4 (`narrative/*.md` 104 boilerplate-stripped textbook walkthroughs with GitHub provenance banners).
- **Zero-Dependency Python Package, CLI & Stdio MCP Server (`src/bigquery_data_science/`):**
  - Skill & kernel installer (`bigquery-data-science install`, `list`, `path`, `kernel`) and federated `statmike.agent_skills` entry point.
  - Instant offline catalog engine (`bigquery-data-science lookup`, `search`, `triage`).
  - Zero-dependency JSON-RPC stdio MCP server (`bigquery-data-science mcp`) exposing `triage_bigquery_task`, `lookup_bigquery_syntax`, `search_bigquery_gotchas`, and `get_bigquery_walkthrough`.
  - Maintainer verification suite (`sweep`, `validate`, `check-links`, `check-reference`, `check-syntax-sync`, `check-pinned-models`, `check-narratives`, `sync-syntax`, `convert-notebook`, `manifest`).
- **Unified Packaging & Layered `uv` Extras (`pyproject.toml` & `uv.lock`):**
  - Zero-dependency `< 1.5 MB` PyPI wheel bundling `skills/`, with optional extras `[notebooks]`, `[pipelines]`, `[workflows]`, and `[all]`.
