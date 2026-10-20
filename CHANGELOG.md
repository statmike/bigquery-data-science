# Changelog

All notable changes to `bigquery-data-science` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
