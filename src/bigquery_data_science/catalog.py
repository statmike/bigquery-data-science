"""Instant offline catalog lookup, search, and task-triage engine."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from bigquery_data_science.installer import get_skills_dir
from bigquery_data_science.tooling.markdown_anchors import headings
from bigquery_data_science.tooling.pinned_models import (
    find_allow_file,
    is_placeholder,
    load_allow_list,
)
from bigquery_data_science.tooling.sync_syntax import syntax_slug

_TOKEN_RE = re.compile(r"[a-z0-9_.]+")
_GOTCHA_BULLET_RE = re.compile(r"^- \*\*([^*]+)\*\*(.*)$", re.MULTILINE)

_SYMBOL_ALIASES: Mapping[str, str] = MappingProxyType(
    {
        "LINEAR_REGRESSION": "LINEAR_REG",
        "LOGISTIC_REGRESSION": "LOGISTIC_REG",
        "WIDE_AND_DEEP_CLASSIFIER": "DNN_LINEAR_COMBINED_CLASSIFIER",
        "WIDE_AND_DEEP_REGRESSOR": "DNN_LINEAR_COMBINED_REGRESSOR",
        "ML.GET_INSIGHTS": "CONTRIBUTION_ANALYSIS",
        "GET_INSIGHTS": "CONTRIBUTION_ANALYSIS",
        "ML_GET_INSIGHTS": "CONTRIBUTION_ANALYSIS",
        "IMPORT MODEL": "IMPORTED MODELS",
        "IMPORT_MODEL": "IMPORTED MODELS",
        "IMPORTED_MODEL": "IMPORTED MODELS",
        "EXPORT_MODEL": "EXPORT MODEL",
        "REMOTE_MODEL": "REMOTE",
        "REMOTE MODEL": "REMOTE",
        "VERTEX_AI_MODEL_ID": "EXPORT MODEL",
        "MODEL_REGISTRY": "EXPORT MODEL",
        "TIMESFM": "AI.FORECAST",
        "TABFM": "AI.PREDICT",
        "CHUNK_DOCUMENT": "AI.CHUNK_DOCUMENT",
        "AI_CHUNK_DOCUMENT": "AI.CHUNK_DOCUMENT",
        "AICHUNK_DOCUMENT": "AI.CHUNK_DOCUMENT",
        "AI.CHUNK": "AI.CHUNK_DOCUMENT",
        "DOCUMENT_CHUNKING": "AI.CHUNK_DOCUMENT",
        "LAYOUT_PARSER": "AI.CHUNK_DOCUMENT",
        "PARSE_DOCUMENT": "AI.PARSE_DOCUMENT",
        "AI_PARSE_DOCUMENT": "AI.PARSE_DOCUMENT",
        "AIPARSE_DOCUMENT": "AI.PARSE_DOCUMENT",
        "AI.PARSE": "AI.PARSE_DOCUMENT",
        "DOCUMENT_PARSING": "AI.PARSE_DOCUMENT",
        "AI_TRANSLATE": "AI.TRANSLATE",
        "AITRANSLATE": "AI.TRANSLATE",
        "TRANSLATE": "AI.TRANSLATE",
        "TRANSLATION_LLM": "AI.TRANSLATE",
        "TLLM": "AI.TRANSLATE",
        "NMT": "AI.TRANSLATE",
    }
)

_FALLBACK_PREREQUISITES: Mapping[str, Mapping[str, str]] = MappingProxyType(
    {
        "AI.CHUNK_DOCUMENT": MappingProxyType(
            {
                "Symbol": "`AI.CHUNK_DOCUMENT`",
                "Skill": "`bigquery-ai`",
                "Category": "Layout-Aware Document Chunking TVF",
                "Connection Required": (
                    "End-user creds (Connection optional; required for Object Tables; "
                    "none when chunking `parsed_document`)"
                ),
                "Reservation Required": "On-demand OK",
                "Status": "GA",
                "Walkthrough": "bigquery-ai/narrative/ai_chunk_document.md",
            }
        ),
        "AI.PARSE_DOCUMENT": MappingProxyType(
            {
                "Symbol": "`AI.PARSE_DOCUMENT`",
                "Skill": "`bigquery-ai`",
                "Category": (
                    "Layout-Aware Document Parsing Scalar Function "
                    "(`layout-v1` blocks or `raw-docai` tree for `AI.CHUNK_DOCUMENT`)"
                ),
                "Connection Required": (
                    "EUC default or `CLOUD_RESOURCE` "
                    "(`roles/storage.objectViewer` + `documentai.viewer`/`editor`)"
                ),
                "Reservation Required": "On-demand OK",
                "Status": "GA",
                "Walkthrough": "bigquery-ai/narrative/ai_parse_document.md",
            }
        ),
        "AI.TRANSLATE": MappingProxyType(
            {
                "Symbol": "`AI.TRANSLATE`",
                "Skill": "`bigquery-ai`",
                "Category": "Managed Scalar Translation (`nmt`, `translation-llm`)",
                "Connection Required": ("None (End-user creds only; no `connection_id`)"),
                "Reservation Required": "On-demand OK",
                "Status": "GA",
                "Walkthrough": "bigquery-ai/narrative/ai_translate.md",
            }
        ),
    }
)

_FALLBACK_GOTCHAS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "AI.CHUNK_DOCUMENT": (
            (
                "**`AI.CHUNK_DOCUMENT` output columns depend on input shape**: "
                "`'gs://...'` URI literals and Object Tables return 13 columns "
                "(including top-level `uri`), whereas `(SELECT OBJ.MAKE_REF(...) AS ref)` "
                "or `(SELECT ..., parsed_document)` subqueries return `5 + passthrough` "
                "columns (no top-level `uri` — select `ref.uri`)."
            ),
            (
                "**`AI.CHUNK_DOCUMENT` 3-way `status` contract**: Valid chunks emit "
                "`status = ''` (empty string), unsupported files emit an error string, "
                "and missing GCS URIs emit `status IS NULL`; filter with `WHERE status = ''`."
            ),
            (
                "**`AI.CHUNK_DOCUMENT` IAM, regions, and VPC-SC**: Requires "
                "`documentai.googleapis.com` (`roles/documentai.editor` on first run to "
                "auto-create `bq-created-layout-parser`, `roles/documentai.viewer` "
                "thereafter); unsupported in `europe-west2` and `europe-west6`; inside "
                "VPC-SC use 1-arg `OBJ.MAKE_REF('gs://...')` or `'gs://...'` with EUC."
            ),
        ),
        "AI.PARSE_DOCUMENT": (
            (
                "**`AI.PARSE_DOCUMENT` is a GA scalar function (`-> JSON`) with two schemas "
                "(`layout-v1` vs `raw-docai`)**: Default `layout-v1` returns flat reading-order "
                "blocks (`title`, `heading`, `text`, `table` HTML, `list_item`, `image`, "
                "`page_header`, `page_footer`) with 1-indexed `page_number` and normalized "
                "`bbox`; `options => JSON '{\"schema\": \"raw-docai\"}'` returns the nested "
                "Document AI layout tree required to chain `parsed_document` into "
                "`AI.CHUNK_DOCUMENT`."
            ),
            (
                "**`AI.PARSE_DOCUMENT` 3-way per-row error contract**: Valid parse has "
                "`ARRAY_LENGTH(JSON_QUERY_ARRAY(parsed, '$.errors')) IS NULL`; unsupported "
                "formats (`.txt`, `.png`) return `blocks: []` and populate "
                "`$.errors[0].message`; missing GCS URIs return SQL `NULL`."
            ),
        ),
        "AI.TRANSLATE": (
            (
                "**`AI.TRANSLATE` sets `status = 'OK'` on success**: When "
                "`return_details => TRUE`, successful rows return `status = 'OK'` "
                "(unlike `AI.CHUNK_DOCUMENT` and `ML.TRANSLATE` where success is `''`), "
                "`NULL` input returns a `NULL` `STRUCT`, and invalid per-row language "
                "codes silently return `NULL` when `return_details => FALSE`."
            ),
            (
                "**`AI.TRANSLATE` EUC-only & single-region residency trap**: Rejects "
                "`connection_id` (always uses EUC) and routes all single regions "
                "(`us-central1`, `europe-west1`, etc.) to the global Cloud Translation "
                "endpoint; run in `US` or `EU` multi-regions for strict regional "
                "residency, or use `ML.TRANSLATE` when a `CLOUD_RESOURCE` connection SA "
                "is required."
            ),
        ),
    }
)

_FALLBACK_SYNTAX: Mapping[str, tuple[str, str]] = MappingProxyType(
    {
        "AI.CHUNK_DOCUMENT": (
            "bigquery-ai/syntax/aichunk_document.md",
            (
                "# `AI.CHUNK_DOCUMENT`\n\n"
                "```sql\n"
                "AI.CHUNK_DOCUMENT(\n"
                "  { 'STORAGE_URI' | TABLE input_table | (query_statement) }\n"
                "  [, connection_id => 'CONNECTION_ID']\n"
                "  [, chunk_size => CHUNK_SIZE]\n"
                ")\n"
                "```\n"
                "- **Type:** Table-valued function (GA); `chunk_size` is an `INT64` "
                "between `1` and `2000` (default `1000`). Accepts pre-parsed "
                "`parsed_document` (`raw-docai` JSON) from `AI.PARSE_DOCUMENT`."
            ),
        ),
        "AI.PARSE_DOCUMENT": (
            "bigquery-ai/syntax/aiparse_document.md",
            (
                "# `AI.PARSE_DOCUMENT`\n\n"
                "```sql\n"
                "AI.PARSE_DOCUMENT(\n"
                "  [document => ] DOCUMENT\n"
                "  [, connection_id => 'CONNECTION_ID']\n"
                "  [, options => JSON '{\"schema\": \"layout-v1\" | \"raw-docai\"}']\n"
                ") -> JSON\n"
                "```\n"
                "- **Type:** Scalar function (returns `JSON`) — GA."
            ),
        ),
        "AI.TRANSLATE": (
            "bigquery-ai/syntax/aitranslate.md",
            (
                "# `AI.TRANSLATE`\n\n"
                "```sql\n"
                "AI.TRANSLATE(\n"
                "  [content =>] CONTENT,\n"
                "  target_language => TARGET_LANGUAGE\n"
                "  [, source_language => SOURCE_LANGUAGE]\n"
                "  [, model => 'MODEL']\n"
                "  [, return_details => RETURN_DETAILS]\n"
                ")\n"
                "```\n"
                "- **Type:** Scalar function (GA); `model` supports `'nmt'` (default) "
                "or `'translation-llm'`."
            ),
        ),
    }
)

_DECOMPOSITION_KEYWORDS: tuple[str, ...] = (
    "change point",
    "change points",
    "step change",
    "step changes",
    "level shift",
    "level shifts",
    "decompose",
    "decomposition",
    "seasonality",
    "seasonal component",
    "ml.trend",
    "ml.seasonality",
    "ml.detect_change_points",
)

_FORECAST_KEYWORDS: tuple[str, ...] = (
    "forecast",
    "forecasting",
    "forecasts",
    "time series",
    "time-series",
    "arima",
    "arima_plus",
    "arima_plus_xreg",
    "timesfm",
    "horizon",
    "daily sales",
)

_CAUSAL_KEYWORDS: tuple[str, ...] = (
    "causal",
    "intervention",
    "treatment",
    "uplift",
    "cate",
    "elasticity",
    "synthetic control",
    "difference in differences",
    "propensity",
)

_DRIVER_KEYWORDS: tuple[str, ...] = (
    "driver",
    "drivers",
    "drove",
    "why did",
    "metric move",
    "contribution",
    "key factor",
    "key factors",
    "key_drivers",
    "get_insights",
)

_EMBEDDING_KEYWORDS: tuple[str, ...] = (
    "embed",
    "embedding",
    "embeddings",
    "vector",
    "semantic search",
    "hybrid search",
    "rag",
    "similarity",
    "sku",
    "ai.embed",
    "ai.similarity",
    "ai.search",
    "vector_search",
    "embeddinggemma",
    "gemini-embedding-2",
    "gemini-embedding-001",
)

_MEDIA_KEYWORDS: tuple[str, ...] = (
    "document",
    "documents",
    "pdf",
    "pdfs",
    "invoice",
    "invoices",
    "receipt",
    "receipts",
    "ocr",
    "translate",
    "translation",
    "transcribe",
    "transcription",
    "audio",
    "speech",
    "vision",
    "image",
    "images",
    "objectref",
    "object table",
    "process_document",
    "annotate_image",
    "chunk",
    "chunks",
    "chunking",
    "chunk_document",
    "ai.chunk_document",
    "parse_document",
    "ai.parse_document",
    "raw-docai",
    "layout-v1",
    "layout parser",
    "docx",
    "pptx",
    "xlsx",
    "ai.translate",
    "translation-llm",
    "tllm",
    "nmt",
    "multilingual",
)

_FEATURE_OPS_KEYWORDS: tuple[str, ...] = (
    "feature store",
    "point in time",
    "point-in-time",
    "leakage",
    "pipeline",
    "pipelines",
    "schedule",
    "scheduled",
    "orchestrate",
    "orchestration",
    "orchestrating",
    "airflow",
    "composer",
    "dataform",
    "dbt",
    "kfp",
    "cloud workflows",
    "mlops",
    "model registry",
    "vertex_ai",
    "vertex ai",
    "register",
    "export model",
    "export",
    "import model",
    "onnx",
    "remote with connection",
    "validate_data_drift",
    "validate_data_skew",
    "ml.metrics",
    "external model",
    "retrain",
    "retraining",
    "scaler",
    "scalers",
    "scale",
    "encoder",
    "encoding",
    "encode",
    "categorical",
    "one-hot",
    "onehot",
    "bucketize",
    "bucketizing",
    "impute",
    "imputation",
    "preprocess",
    "preprocessing",
    "describe_data",
    "correlation",
    "drift",
    "skew",
    "features_at_time",
    "entity_features_at_time",
)

_MLOPS_PRIMARY_KEYWORDS: tuple[str, ...] = (
    "feature store",
    "point in time",
    "point-in-time",
    "leakage",
    "pipeline",
    "pipelines",
    "schedule",
    "scheduled",
    "orchestrate",
    "orchestration",
    "orchestrating",
    "airflow",
    "composer",
    "dataform",
    "dbt",
    "kfp",
    "cloud workflows",
    "mlops",
    "model registry",
    "vertex_ai",
    "vertex ai",
    "register",
    "export model",
    "export",
    "import model",
    "onnx",
    "remote with connection",
    "validate_data_drift",
    "validate_data_skew",
    "ml.metrics",
    "external model",
    "retrain",
    "retraining",
    "drift",
    "skew",
    "features_at_time",
    "entity_features_at_time",
)

_GENERATIVE_KEYWORDS: tuple[str, ...] = (
    "summarize",
    "summary",
    "extract",
    "prompt",
    "gemini",
    "sentiment",
    "moderation",
    "log",
    "logs",
    "log triage",
    "log analysis",
    "error logs",
    "server logs",
    "provisioned throughput",
    "quota",
    "ai.generate",
    "ai.classify",
    "ai.score",
    "ai.if",
    "ai.agg",
    "ai.count_tokens",
    "reusable column alias",
    "reusable column aliases",
    "column alias",
    "column aliases",
    "reusable_column_aliases_mode",
    "effective_project_options",
    "gemini-3.8-flash",
    "gemini-4-hydrogen",
    "gemini-4-carbon",
    "gemini-4-argon",
)


@dataclass
class LookupResult:
    """Structured result for `lookup_symbol`."""

    symbol: str
    found: bool
    skill: str = ""
    syntax_card_path: str = ""
    syntax_content: str = ""
    prerequisites: list[dict[str, str]] = field(default_factory=list)
    gotchas: list[str] = field(default_factory=list)
    related_narratives: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Convert the lookup result to a JSON-serializable dictionary."""
        return {
            "symbol": self.symbol,
            "found": self.found,
            "skill": self.skill,
            "syntax_card_path": self.syntax_card_path,
            "syntax_content": self.syntax_content,
            "prerequisites": self.prerequisites,
            "gotchas": self.gotchas,
            "related_narratives": self.related_narratives,
        }

    def format_text(self) -> str:
        """Render a human- and agent-readable summary for CLI and MCP."""
        if not self.found:
            return (
                f"No exact syntax card or matrix entry found for '{self.symbol}'.\n"
                "Try `bigquery-data-science search <query>` or "
                "`bigquery-data-science triage <task>`."
            )
        lines: list[str] = [f"# Lookup: {self.symbol}"]
        if self.skill:
            lines.append(f"**Skill:** `{self.skill}`")
        if self.syntax_card_path:
            lines.append(f"**Syntax Card:** `{self.syntax_card_path}`")
        if self.prerequisites:
            lines.append("\n## Prerequisites (`namespace-matrix.md`)")
            for row in self.prerequisites:
                summary = ", ".join(f"{key}: {val}" for key, val in row.items() if val)
                lines.append(f"- {summary}")
        if self.syntax_content:
            lines.append("\n## Syntax & Options\n" + self.syntax_content.strip())
        if self.gotchas:
            lines.append("\n## Empirical Gotchas")
            for gotcha in self.gotchas[:6]:
                lines.append(f"- {gotcha}")
        if self.related_narratives:
            lines.append("\n## Related Walkthroughs (`narrative/`)")
            for narrative in self.related_narratives:
                lines.append(f"- `{narrative}`")
        return "\n".join(lines)


@dataclass
class SearchHit:
    """A single ranked search hit across the 4-Lens skill bundle."""

    skill: str
    lens: str
    file_path: str
    title: str
    snippet: str
    score: float

    def to_dict(self) -> dict[str, object]:
        """Convert the search hit to a JSON-serializable dictionary."""
        return {
            "skill": self.skill,
            "lens": self.lens,
            "file_path": self.file_path,
            "title": self.title,
            "snippet": self.snippet,
            "score": round(self.score, 3),
        }

    def format_text(self) -> str:
        """Format the search hit for CLI and MCP output."""
        return f"[{self.skill}/{self.lens}] {self.title} ({self.file_path})\n  {self.snippet}"


@dataclass
class TriageResult:
    """Structured task-routing recommendation across `ML.*`, `AI.*`, and `bigquery-mlops`."""

    query: str
    category: str
    recommended_skill: str
    primary_options: list[str]
    head_to_head: str
    prerequisites: str
    next_steps: list[str]
    recommended_skills: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.recommended_skills:
            self.recommended_skills = [self.recommended_skill]

    def to_dict(self) -> dict[str, object]:
        """Convert the triage result to a JSON-serializable dictionary."""
        return {
            "query": self.query,
            "category": self.category,
            "recommended_skill": self.recommended_skill,
            "recommended_skills": self.recommended_skills,
            "primary_options": self.primary_options,
            "head_to_head": self.head_to_head,
            "prerequisites": self.prerequisites,
            "next_steps": self.next_steps,
        }

    def format_text(self) -> str:
        """Render the triage decision for CLI and MCP output."""
        options_str = "\n".join(f"- {opt}" for opt in self.primary_options)
        steps_str = "\n".join(f"- {step}" for step in self.next_steps)
        skills_str = ", ".join(f"`{s}`" for s in self.recommended_skills)
        return (
            f"# BigQuery Data Science Triage: {self.category}\n"
            f"**Query:** {self.query}\n"
            f"**Recommended Primary Skill:** `{self.recommended_skill}`\n"
            f"**Collaborating Skills:** {skills_str}\n\n"
            f"## Primary Options\n{options_str}\n\n"
            f"## Empirical Head-to-Head Tradeoffs\n{self.head_to_head}\n\n"
            f"## Infrastructure & Prerequisites\n{self.prerequisites}\n\n"
            f"## Next Steps\n{steps_str}"
        )


def _parse_namespace_matrix(matrix_path: Path) -> list[dict[str, str]]:
    """Parse markdown tables from `reference/namespace-matrix.md`."""
    if not matrix_path.is_file():
        return []
    rows: list[dict[str, str]] = []
    headers: list[str] = []
    for line in matrix_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            headers = []
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", cell) for cell in cells if cell):
            continue
        if not headers:
            headers = cells
            continue
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells, strict=True)))
    return rows


def _score_syntax_card(
    card_stem: str,
    h1_title: str,
    query_upper: str,
    query_slug: str,
) -> int:
    """Return a relevance score (0-100) for a syntax card heading and filename."""
    h1_upper = h1_title.upper()
    if card_stem == query_slug:
        return 100
    if h1_upper.strip("`") == query_upper:
        return 98
    if f"`{query_upper}`" in h1_upper:
        return 95
    if re.match(rf"^`?{re.escape(query_upper)}`?\b", h1_upper):
        return 90
    if query_slug and card_stem.startswith(query_slug):
        return 80
    if query_slug and query_slug in card_stem:
        return 70
    if query_upper in h1_upper:
        return 65
    return 0


def lookup_symbol(
    symbol: str,
    skills_dir: Path | None = None,
) -> LookupResult:
    """Look up syntax card, prerequisites, gotchas, and narratives for `symbol`."""
    root = skills_dir if skills_dir is not None else get_skills_dir()
    cleaned = symbol.strip().strip("`").strip()
    slug_query = syntax_slug(cleaned)
    if not cleaned or not slug_query:
        return LookupResult(symbol=cleaned, found=False)

    normalized_upper = cleaned.upper().replace("-", "_")
    canonical_upper = _SYMBOL_ALIASES.get(
        normalized_upper,
        _SYMBOL_ALIASES.get(
            normalized_upper.replace(".", "_"),
            normalized_upper,
        ),
    )
    canonical_slug = syntax_slug(canonical_upper) or slug_query
    stem_query = re.sub(r"^(ml\.|ai\.|obj\.)", "", cleaned.lower())

    best_card: tuple[int, int, str, Path, str] | None = None
    for skill_name in ("bigquery-ml", "bigquery-ai"):
        syntax_dir = root / skill_name / "syntax"
        if not syntax_dir.is_dir():
            continue
        for card_path in sorted(syntax_dir.glob("*.md")):
            if card_path.name == "INDEX.md":
                continue
            content = card_path.read_text(encoding="utf-8")
            first_line = content.splitlines()[0] if content else ""
            h1_title = first_line.lstrip("# ").strip()
            card_stem = card_path.stem

            score = max(
                _score_syntax_card(card_stem, h1_title, normalized_upper, slug_query),
                _score_syntax_card(card_stem, h1_title, canonical_upper, canonical_slug),
            )

            if score > 0:
                h1_lower = h1_title.lower()
                if "covered in" in h1_lower or "(see " in h1_lower:
                    score = max(1, score - 25)
                if "lifecycle functions" in h1_lower:
                    score = max(1, score - 10)
                candidate_key = (score, len(content))
                if best_card is None or candidate_key > (
                    best_card[0],
                    best_card[1],
                ):
                    best_card = (
                        score,
                        len(content),
                        skill_name,
                        card_path,
                        content,
                    )

    if best_card is None:
        for skill_name in ("bigquery-ml", "bigquery-ai"):
            syntax_dir = root / skill_name / "syntax"
            if not syntax_dir.is_dir():
                continue
            for card_path in sorted(syntax_dir.glob("*.md")):
                if card_path.name == "INDEX.md":
                    continue
                content = card_path.read_text(encoding="utf-8")
                content_upper = content.upper()
                if (
                    f"`{canonical_upper}`" in content_upper
                    or f"`{normalized_upper}`" in content_upper
                ):
                    candidate_key = (50, len(content))
                    if best_card is None or candidate_key > (
                        best_card[0],
                        best_card[1],
                    ):
                        best_card = (
                            50,
                            len(content),
                            skill_name,
                            card_path,
                            content,
                        )

    matrix_path = root / "bigquery-data-science" / "reference" / "namespace-matrix.md"
    prerequisites: list[dict[str, str]] = []
    for row in _parse_namespace_matrix(matrix_path):
        row_symbol = row.get("Symbol", "")
        row_upper = row_symbol.upper()
        if (
            normalized_upper in row_upper
            or canonical_upper in row_upper
            or cleaned.lower() in row_symbol.lower()
        ):
            prerequisites.append(row)
    if not prerequisites and canonical_upper in _FALLBACK_PREREQUISITES:
        prerequisites.append(dict(_FALLBACK_PREREQUISITES[canonical_upper]))

    gotchas: list[str] = []
    if root.is_dir():
        for skill_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            candidate_files = [skill_dir / "SKILL.md"]
            ref_dir = skill_dir / "reference"
            if ref_dir.is_dir():
                candidate_files.extend(sorted(ref_dir.glob("*.md")))
            for md_path in candidate_files:
                if not md_path.is_file():
                    continue
                text = md_path.read_text(encoding="utf-8")
                for match in _GOTCHA_BULLET_RE.finditer(text):
                    bullet = f"**{match.group(1)}**{match.group(2)}".strip()
                    bullet_upper = bullet.upper()
                    if (
                        normalized_upper in bullet_upper
                        or canonical_upper in bullet_upper
                        or cleaned.lower() in bullet.lower()
                    ) and bullet not in gotchas:
                        gotchas.append(bullet)
    if canonical_upper in _FALLBACK_GOTCHAS:
        for fallback_bullet in _FALLBACK_GOTCHAS[canonical_upper]:
            if fallback_bullet not in gotchas:
                gotchas.append(fallback_bullet)

    related_narratives: list[str] = []
    for skill_name in ("bigquery-ml", "bigquery-ai"):
        nar_dir = root / skill_name / "narrative"
        if not nar_dir.is_dir():
            continue
        for nar_path in sorted(nar_dir.glob("*.md")):
            nar_stem = nar_path.stem.lower()
            if (
                nar_stem == cleaned.lower().replace(".", "_")
                or nar_stem == stem_query
                or (len(stem_query) >= 4 and stem_query in nar_stem)
            ):
                related_narratives.append(f"{skill_name}/narrative/{nar_path.name}")

    fallback_card = _FALLBACK_SYNTAX.get(canonical_upper)
    found = bool(best_card is not None or prerequisites or gotchas)
    skill = (
        best_card[2]
        if best_card is not None
        else (prerequisites[0].get("Skill", "").strip("`") if prerequisites else "")
    )
    syntax_card_path = (
        f"{best_card[2]}/syntax/{best_card[3].name}"
        if best_card is not None
        else (fallback_card[0] if fallback_card is not None else "")
    )
    syntax_content = (
        best_card[4]
        if best_card is not None
        else (fallback_card[1] if fallback_card is not None else "")
    )

    return LookupResult(
        symbol=cleaned,
        found=found,
        skill=skill,
        syntax_card_path=syntax_card_path,
        syntax_content=syntax_content,
        prerequisites=prerequisites,
        gotchas=gotchas,
        related_narratives=related_narratives,
    )


def search_catalog(
    query: str,
    skill_filter: str | None = None,
    lens_filter: str | None = None,
    limit: int = 10,
    skills_dir: Path | None = None,
) -> list[SearchHit]:
    """Search across all 3 skills and 4 progressive lenses."""
    root = skills_dir if skills_dir is not None else get_skills_dir()
    query_lower = query.strip().lower()
    tokens = [tok for tok in _TOKEN_RE.findall(query_lower) if len(tok) >= 2]
    if not tokens and query_lower:
        tokens = [query_lower]
    if not tokens:
        return []

    hits: list[SearchHit] = []
    if root.is_dir():
        for skill_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            if skill_filter and skill_dir.name != skill_filter:
                continue

            files_to_scan: list[tuple[str, Path]] = []
            if lens_filter in (None, "skill", "gotchas"):
                skill_md = skill_dir / "SKILL.md"
                if skill_md.is_file():
                    files_to_scan.append(("skill", skill_md))
            if lens_filter in (None, "reference", "gotchas"):
                ref_dir = skill_dir / "reference"
                if ref_dir.is_dir():
                    for path in sorted(ref_dir.glob("*.md")):
                        files_to_scan.append(("reference", path))
            if lens_filter in (None, "syntax"):
                syn_dir = skill_dir / "syntax"
                if syn_dir.is_dir():
                    for path in sorted(syn_dir.glob("*.md")):
                        if path.name != "INDEX.md":
                            files_to_scan.append(("syntax", path))
            if lens_filter in (None, "narrative"):
                nar_dir = skill_dir / "narrative"
                if nar_dir.is_dir():
                    for path in sorted(nar_dir.glob("*.md")):
                        files_to_scan.append(("narrative", path))

            for lens, path in files_to_scan:
                text = path.read_text(encoding="utf-8")
                text_lower = text.lower()
                matched_tokens = [tok for tok in tokens if tok in text_lower]
                if not matched_tokens:
                    continue

                page_headings = headings(text)
                title = page_headings[0][1] if page_headings else path.stem.replace("-", " ")
                title_lower = title.lower()

                score = float(len(matched_tokens)) * 3.0
                if query_lower in text_lower:
                    score += 6.0
                if query_lower in title_lower:
                    score += 10.0
                for tok in matched_tokens:
                    if tok in title_lower:
                        score += 4.0
                    score += min(text_lower.count(tok), 10) * 0.3

                best_line = ""
                best_line_score = -1
                for line in text.splitlines():
                    stripped = line.strip()
                    if not stripped or stripped.startswith(("---", "```", "|---")):
                        continue
                    if lens_filter == "gotchas" and not stripped.startswith("- **"):
                        continue
                    line_lower = stripped.lower()
                    line_hits = sum(1 for tok in tokens if tok in line_lower)
                    if query_lower in line_lower:
                        line_hits += 3
                    if stripped.startswith("- **"):
                        line_hits += 1
                    if line_hits > best_line_score:
                        best_line_score = line_hits
                        best_line = stripped

                if lens_filter == "gotchas" and best_line_score <= 0:
                    continue

                snippet = best_line[:240] + ("..." if len(best_line) > 240 else "")
                rel_path = f"{skill_dir.name}/{path.relative_to(skill_dir).as_posix()}"
                hits.append(
                    SearchHit(
                        skill=skill_dir.name,
                        lens=lens,
                        file_path=rel_path,
                        title=title,
                        snippet=snippet,
                        score=score,
                    )
                )

    if skill_filter in (None, "bigquery-ai") and lens_filter in (
        None,
        "gotchas",
        "reference",
        "syntax",
    ):
        for symbol_name, fallback_bullets in _FALLBACK_GOTCHAS.items():
            card_rel_path, fallback_syntax_text = _FALLBACK_SYNTAX[symbol_name]
            if (root / card_rel_path).is_file():
                continue
            combined_text = (
                "\n".join(f"- {bullet}" for bullet in fallback_bullets)
                + "\n"
                + fallback_syntax_text
            )
            combined_lower = combined_text.lower()
            matched_tokens = [tok for tok in tokens if len(tok) >= 3 and tok in combined_lower]
            if not matched_tokens:
                continue
            best_bullet = fallback_bullets[0]
            best_bullet_hits = -1
            for bullet in fallback_bullets:
                bullet_hits = sum(1 for tok in matched_tokens if tok in bullet.lower())
                if bullet_hits > best_bullet_hits:
                    best_bullet_hits = bullet_hits
                    best_bullet = bullet
            snippet = f"- {best_bullet}"[:240]
            score = float(len(matched_tokens)) * 4.0 + (
                10.0 if query_lower in symbol_name.lower() else 0.0
            )
            hits.append(
                SearchHit(
                    skill="bigquery-ai",
                    lens="syntax" if lens_filter == "syntax" else "reference",
                    file_path=card_rel_path,
                    title=f"`{symbol_name}`",
                    snippet=snippet,
                    score=score,
                )
            )

    hits.sort(key=lambda hit: (-hit.score, hit.file_path))
    return hits[:limit]


def _matches_any(text: str, keywords: Sequence[str]) -> bool:
    """Return True when any keyword matches `text` on word boundaries."""
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text) is not None
        for keyword in keywords
    )


def triage_task(
    query: str,
    skills_dir: Path | None = None,
) -> TriageResult:
    """Route a data-science task description across `ML.*` and `AI.*`."""
    _ = skills_dir if skills_dir is not None else get_skills_dir()
    text = query.strip().lower()

    if _matches_any(text, _DECOMPOSITION_KEYWORDS):
        return TriageResult(
            query=query,
            category="Time-Series Decomposition & Structural Change Points",
            recommended_skill="bigquery-ml",
            recommended_skills=["bigquery-ml", "bigquery-ai"],
            primary_options=[
                (
                    "`ML.TREND`, `ML.SEASONALITY`, `ML.DETECT_CHANGE_POINTS` "
                    "(`bigquery-ml` — model-free TVFs, no `CREATE MODEL`)"
                ),
                (
                    "`ARIMA_PLUS` + `ML.EXPLAIN_FORECAST` "
                    "(`bigquery-ml` — trained decomposition with holiday effects)"
                ),
            ],
            head_to_head=(
                "`ML.SEASONALITY` returns weekly and yearly components bit-identical "
                "to `ARIMA_PLUS`'s `ML.EXPLAIN_FORECAST` (corr 1.0, mean abs diff 0.0) "
                "with zero training. `ML.TREND` defaults `adjust_step_changes` to FALSE "
                "(whereas `ARIMA_PLUS` defaults it to TRUE). All three model-free TVFs "
                "gap-fill each series first, so profile for ingestion gaps before acting "
                "on `ML.DETECT_CHANGE_POINTS` windows."
            ),
            prerequisites=(
                "Model-free TVFs (`ML.TREND`, `ML.SEASONALITY`, `ML.DETECT_CHANGE_POINTS`): "
                "no `CREATE MODEL`, no connection, no reservation (Preview)."
            ),
            next_steps=[
                "Inspect `skills/bigquery-ml/reference/unsupervised-and-specialized.md`",
                "Run `bigquery-data-science lookup ML.DETECT_CHANGE_POINTS`",
                "Read walkthrough `skills/bigquery-ml/narrative/time_series.md`",
            ],
        )

    if _matches_any(text, _FORECAST_KEYWORDS):
        return TriageResult(
            query=query,
            category="Time-Series Forecasting (`AI.FORECAST` vs `ARIMA_PLUS` / `ARIMA_PLUS_XREG`)",
            recommended_skill="bigquery-data-science",
            recommended_skills=["bigquery-data-science", "bigquery-ai", "bigquery-ml"],
            primary_options=[
                (
                    "`AI.FORECAST` on `TimesFM 2.5` (GA) or `TimesFM 3.0` "
                    "(Preview, supports `target_cols`, `past_covariate_cols`, "
                    "`future_covariate_cols`) in `bigquery-ai` — zero training, no `CREATE MODEL`"
                ),
                (
                    "`CREATE MODEL ... OPTIONS(model_type='ARIMA_PLUS')` / "
                    "`'ARIMA_PLUS_XREG'` + `ML.FORECAST` / `ML.EXPLAIN_FORECAST` "
                    "in `bigquery-ml` — custom holidays, hierarchical reconciliation, "
                    "explainable components, horizon > 1,024"
                ),
                (
                    "Lagged-feature `LINEAR_REG` / `BOOSTED_TREE_REGRESSOR` "
                    "(`bigquery-ml/workflows/regression_based_forecasting`)"
                ),
            ],
            head_to_head=(
                "Use `AI.FORECAST` when you want a zero-training baseline or fast "
                "multivariate/covariate forecast (`model => 'TimesFM 3.0'`, capped at "
                "1,024 horizon steps and 2,048 context points). Use `ARIMA_PLUS` or "
                "`ARIMA_PLUS_XREG` when you need custom holiday calendars, hierarchical "
                "reconciliation (`hierarchical_time_series_cols`), `ML.EXPLAIN_FORECAST` "
                "component attribution, `ML.ARIMA_COEFFICIENTS` weights, or a GA surface "
                "for external regressors. Always pin `model => 'TimesFM 2.5'` or `'TimesFM 3.0'`."
            ),
            prerequisites=(
                "Neither `AI.FORECAST` nor `ARIMA_PLUS` requires a Cloud Resource Connection "
                "or Enterprise reservation."
            ),
            next_steps=[
                (
                    "Run `bigquery-data-science lookup AI.FORECAST` and "
                    "`bigquery-data-science lookup ARIMA_PLUS`"
                ),
                (
                    "Compare `skills/bigquery-ai/reference/predictive-ai.md` and "
                    "`skills/bigquery-ml/reference/unsupervised-and-specialized.md`"
                ),
                (
                    "Read walkthroughs `skills/bigquery-ai/narrative/ai_forecast.md` "
                    "and `skills/bigquery-ml/narrative/arima_plus.md`"
                ),
            ],
        )

    if _matches_any(text, _CAUSAL_KEYWORDS):
        return TriageResult(
            query=query,
            category="Causal Inference & Treatment Effect Estimation",
            recommended_skill="bigquery-ml",
            recommended_skills=["bigquery-ml", "bigquery-ai"],
            primary_options=[
                (
                    "`AI.CAUSAL_EFFECT` (`bigquery-ml/workflows/causal_effect` — "
                    "model-free interrupted time-series counterfactual TVF, Preview)"
                ),
                (
                    "Panel comparison estimators: `difference_in_differences` "
                    "(`LINEAR_REG` with `optimize_strategy='NORMAL_EQUATION'`) "
                    "and `synthetic_control` (`bigquery-ml`)"
                ),
                (
                    "Observational & heterogeneous treatment estimators: "
                    "`propensity_score_matching`, `price_elasticity_dml` (Double ML), "
                    "and `uplift_cate` (T-learner) in `bigquery-ml`"
                ),
            ],
            head_to_head=(
                "`AI.CAUSAL_EFFECT` builds an `ARIMA_PLUS` counterfactual on a single "
                "series and reports cumulative `absolute_effect` (no donor pool, no "
                "multiple-comparison adjustment across `id_cols`, needs >1 year pre-history "
                "when annual seasonality is present). When untreated control units exist, "
                "prefer `difference_in_differences` or `synthetic_control`."
            ),
            prerequisites=(
                "`AI.CAUSAL_EFFECT` and native `LINEAR_REG`/`BOOSTED_TREE_*` causal "
                "workflows require no connection and no reservation."
            ),
            next_steps=[
                "Inspect `skills/bigquery-ml/reference/workflows-and-pipelines.md`",
                "Run `bigquery-data-science lookup AI.CAUSAL_EFFECT`",
                (
                    "Read `skills/bigquery-ml/narrative/causal_effect.md` and "
                    "`difference_in_differences.md`"
                ),
            ],
        )

    if _matches_any(text, _DRIVER_KEYWORDS):
        return TriageResult(
            query=query,
            category=(
                "Key-Driver & Metric Attribution (`AI.KEY_DRIVERS` vs `CONTRIBUTION_ANALYSIS`)"
            ),
            recommended_skill="bigquery-ai",
            recommended_skills=["bigquery-ai", "bigquery-ml"],
            primary_options=[
                (
                    "`AI.KEY_DRIVERS` (`bigquery-ai` — GA model-free TVF for "
                    "summable metrics with <= 12 dimensions)"
                ),
                (
                    "`CREATE MODEL ... OPTIONS(model_type='CONTRIBUTION_ANALYSIS')` "
                    "+ `ML.GET_INSIGHTS` (`bigquery-ml` — supports > 12 dimensions, "
                    "summable-by-ratio, and summable-by-category metrics)"
                ),
            ],
            head_to_head=(
                "Reach for `AI.KEY_DRIVERS` first when you have <= 12 dimension columns "
                "and a plain summable metric: zero `CREATE MODEL` step and automatic "
                "redundancy pruning. Reach for `CONTRIBUTION_ANALYSIS` when you need "
                "> 12 dimensions or a ratio/category contribution metric."
            ),
            prerequisites=(
                "Both `AI.KEY_DRIVERS` and `CONTRIBUTION_ANALYSIS` run on standard "
                "on-demand BigQuery with no connection or reservation."
            ),
            next_steps=[
                (
                    "Run `bigquery-data-science lookup AI.KEY_DRIVERS` and "
                    "`bigquery-data-science lookup CONTRIBUTION_ANALYSIS`"
                ),
                "Read `skills/bigquery-ai/reference/augmented-analytics.md`",
            ],
        )

    if _matches_any(text, _EMBEDDING_KEYWORDS):
        return TriageResult(
            query=query,
            category="Embeddings, Vector Search & Hybrid Retrieval",
            recommended_skill="bigquery-ai",
            recommended_skills=["bigquery-ai", "bigquery-ml", "bigquery-mlops"],
            primary_options=[
                (
                    "Text/multimodal embeddings & similarity: `AI.EMBED` (GA scalar; "
                    "`endpoint => 'gemini-embedding-2'` or `model => 'embeddinggemma-300m'` "
                    "Preview), `AI.SIMILARITY` (GA scalar; `endpoint => 'gemini-embedding-2'` "
                    "or `model => 'embeddinggemma-300m'` Preview), "
                    "`AI.GENERATE_EMBEDDING` (GA TVF), and `AI.CHUNK_DOCUMENT` "
                    "(GA layout-aware document chunking TVF for RAG) in `bigquery-ai`"
                ),
                (
                    "Search & hybrid retrieval: `VECTOR_SEARCH` "
                    "(with `lexical_search_columns`) and `AI.SEARCH` "
                    "(with `mode => 'HYBRID'`) in `bigquery-ai`"
                ),
                (
                    "Structured/tabular embeddings: `PCA`, `AUTOENCODER`, "
                    "`MATRIX_FACTORIZATION` + `ML.GENERATE_EMBEDDING` in `bigquery-ml`"
                ),
            ],
            head_to_head=(
                "There is no standalone `HYBRID_SEARCH` TVF — use `lexical_search_columns` "
                "on `VECTOR_SEARCH` or `mode => 'HYBRID'` on `AI.SEARCH`. Hybrid search "
                "uses RRF (`distance = 1 - (1/(60 + rank_vector) + 1/(61 + rank_lexical))`) "
                "over a candidate pool of `10 * top_k` semantic rows, so retrieving a row "
                "at semantic rank R requires `top_k >= R/10` (and higher below R=500). "
                "For document RAG, chunk files first with GA `AI.CHUNK_DOCUMENT` "
                "(auto-provisioned `bq-created-layout-parser`, no `CREATE MODEL`), "
                "or parse once with `AI.PARSE_DOCUMENT(..., options => "
                "JSON '{\"schema\": \"raw-docai\"}')` "
                "and pass `parsed_document` into `AI.CHUNK_DOCUMENT` to tune `chunk_size`."
            ),
            prerequisites=(
                "`AI.EMBED` and `AI.SIMILARITY` with `model => 'embeddinggemma-300m'` "
                "(Preview) require no connection; Vertex AI embedding endpoints "
                "(such as `endpoint => 'gemini-embedding-2'`) use "
                "`roles/aiplatform.user` for multimodal or >48h jobs. Inside VPC-SC, "
                "pass 1-arg `OBJ.MAKE_REF('gs://...')` with end-user credentials "
                "(connection-backed `ObjectRef` HTTP links are rejected). "
                "`ALTER VECTOR INDEX` requires an `ENTERPRISE` `BACKGROUND` reservation."
            ),
            next_steps=[
                "Inspect `skills/bigquery-ai/reference/embeddings-and-search.md`",
                (
                    "Run `bigquery-data-science lookup VECTOR_SEARCH`, "
                    "`bigquery-data-science lookup AI.EMBED`, and "
                    "`bigquery-data-science lookup AI.CHUNK_DOCUMENT`"
                ),
            ],
        )

    if _matches_any(text, _MEDIA_KEYWORDS):
        return TriageResult(
            query=query,
            category="Unstructured Media, Document AI & Pre-Trained Cloud AI Services",
            recommended_skill="bigquery-ai",
            recommended_skills=["bigquery-ai", "bigquery-ml"],
            primary_options=[
                (
                    "Zero-DDL document parsing, chunking & translation (GA): "
                    "`AI.PARSE_DOCUMENT` (scalar `-> JSON` returning `layout-v1` "
                    "reading-order blocks or `raw-docai` layout tree via "
                    "auto-provisioned `bq-created-layout-parser`), "
                    "`AI.CHUNK_DOCUMENT` (PDF/HTML/DOCX/PPTX/XLSX/XLSM or "
                    "`parsed_document` `raw-docai` layout chunking, `chunk_size` "
                    "1..2000), and `AI.TRANSLATE` (EUC scalar translation with `'nmt'` "
                    "or `'translation-llm'`, dynamic per-row `target_language` / "
                    "`source_language`, `return_details => TRUE` where `status = 'OK'`) "
                    "in `bigquery-ai`"
                ),
                (
                    "Pre-trained Cloud AI service remote models (`REMOTE_SERVICE_TYPE`): "
                    "`ML.PROCESS_DOCUMENT`, `ML.TRANSLATE`, `ML.UNDERSTAND_TEXT`, "
                    "`ML.ANNOTATE_IMAGE`, `ML.TRANSCRIBE` (`bigquery-ai`)"
                ),
                (
                    "Direct `ObjectRef` multimodal prompts: `OBJ.LIST` / `OBJ.MAKE_REF` "
                    "/ Object Tables passed straight into `AI.GENERATE*`, `AI.CLASSIFY`, "
                    "`AI.SCORE`, `AI.IF`, `AI.EMBED`, `AI.SIMILARITY`, "
                    "`AI.PARSE_DOCUMENT`, `AI.CHUNK_DOCUMENT` (`bigquery-ai`)"
                ),
                (
                    "SQL image tensor preprocessing: `ML.DECODE_IMAGE`, "
                    "`ML.RESIZE_IMAGE`, `ML.CONVERT_COLOR_SPACE`, "
                    "`ML.CONVERT_IMAGE_TYPE` (`bigquery-ml`)"
                ),
            ],
            head_to_head=(
                "Use GA scalar `AI.PARSE_DOCUMENT` for zero-DDL layout block extraction "
                "(`layout-v1` reading-order blocks with HTML tables and `bbox`, or "
                "`options => JSON '{\"schema\": \"raw-docai\"}'` aliased `AS parsed_document` "
                "to parse once and chunk many times with `AI.CHUNK_DOCUMENT`), GA "
                "`AI.CHUNK_DOCUMENT` for direct layout-aware RAG chunking, and "
                "`ML.PROCESS_DOCUMENT` for specialized Invoice/Form/Custom Document AI "
                "processors. For translation, prefer GA `AI.TRANSLATE` (`status = 'OK'` "
                "when `return_details => TRUE`, EUC-only, `US`/`EU` multi-region residency) "
                "for scalar per-row SQL, and `ML.TRANSLATE` when you need a `CLOUD_RESOURCE` "
                "connection service account, single-region residency, or standalone "
                "`'DETECT_LANGUAGE'`. Pass bare `ObjectRef` directly to `AI.*` functions "
                "(inside VPC-SC, use 1-arg `OBJ.MAKE_REF('gs://...')` with EUC)."
            ),
            prerequisites=(
                "`AI.PARSE_DOCUMENT` and `AI.CHUNK_DOCUMENT` require `documentai.googleapis.com` "
                "(`roles/documentai.editor` on first run to create "
                "`bq-created-layout-parser`, `roles/documentai.viewer` thereafter; "
                "excluded in `europe-west2` and `europe-west6`). `AI.TRANSLATE` uses "
                "EUC only (`translate.googleapis.com` + `roles/cloudtranslate.user`). "
                "Cloud AI `REMOTE_SERVICE_TYPE` models require a `CLOUD_RESOURCE` "
                "connection; `ML.DECODE_IMAGE` and friends require an `ENTERPRISE` "
                "reservation."
            ),
            next_steps=[
                (
                    "Inspect `skills/bigquery-ai/reference/document-processing.md`, "
                    "`managed-functions.md`, and `cloud-ai-service-models.md`"
                ),
                (
                    "Run `bigquery-data-science lookup AI.PARSE_DOCUMENT`, "
                    "`bigquery-data-science lookup AI.CHUNK_DOCUMENT`, "
                    "`bigquery-data-science lookup AI.TRANSLATE`, and "
                    "`bigquery-data-science lookup ML.PROCESS_DOCUMENT`"
                ),
            ],
        )

    if _matches_any(text, _FEATURE_OPS_KEYWORDS):
        is_mlops_primary = _matches_any(text, _MLOPS_PRIMARY_KEYWORDS)
        primary_skill = "bigquery-mlops" if is_mlops_primary else "bigquery-ml"
        collab_skills = (
            ["bigquery-mlops", "bigquery-ml", "bigquery-ai"]
            if is_mlops_primary
            else ["bigquery-ml", "bigquery-mlops"]
        )
        return TriageResult(
            query=query,
            category="Feature Retrieval, Preprocessing, Drift Monitoring & MLOps Pipelines",
            recommended_skill=primary_skill,
            recommended_skills=collab_skills,
            primary_options=[
                (
                    "Point-in-time feature retrieval: `ML.ENTITY_FEATURES_AT_TIME` "
                    "(training) and `ML.FEATURES_AT_TIME` (serving) in "
                    "`bigquery-mlops` / `bigquery-ml`"
                ),
                (
                    "Universal drift monitoring & model-free evaluation: `ML.DESCRIBE_DATA`, "
                    "`ML.CORRELATION`, `ML.VALIDATE_DATA_DRIFT`, `ML.VALIDATE_DATA_SKEW`, "
                    "`ML.METRICS` (for BQML, `AI.*`, and external models logging to BigQuery) "
                    "in `bigquery-mlops`"
                ),
                (
                    "8 production orchestrators (`sql_scripting`, `scheduled_queries`, "
                    "`dataform`, `cloud_workflows`, `dbt`, `vertex_kfp`, `composer_airflow`, "
                    "`airflow_with_kfp`) and Vertex AI Model Registry / `EXPORT` / "
                    "`IMPORT` / `REMOTE` in `bigquery-mlops`"
                ),
            ],
            head_to_head=(
                "Use `ML.ENTITY_FEATURES_AT_TIME` instead of a `GROUP BY` latest-row join "
                "to eliminate future label leakage (`roc_auc` 0.9387 leaky vs 0.5194 honest). "
                "Set `ignore_feature_nulls => TRUE` on sparse/EAV feature tables, and "
                "`FALSE` on dense snapshot tables. Use 3-arg `ML.VALIDATE_DATA_DRIFT` and "
                "`ML.METRICS` (`TABLE` form, `BOOL` labels) to monitor and score BQML, "
                "`AI.*`, and external Vertex AI / Cloud Run models logging to BigQuery."
            ),
            prerequisites=(
                "All preprocessing, point-in-time feature retrieval, `ML.VALIDATE_DATA_DRIFT`, "
                "and `ML.METRICS` functions are model-free SQL functions requiring no connection "
                "and no reservation."
            ),
            next_steps=[
                (
                    "Inspect `skills/bigquery-mlops/SKILL.md`, "
                    "`skills/bigquery-mlops/reference/orchestration-and-pipelines.md`, and "
                    "`skills/bigquery-mlops/reference/monitoring-drift-and-evaluation.md`"
                ),
                (
                    "Inspect `skills/bigquery-ml/reference/preprocessing-functions.md` "
                    "and `skills/bigquery-data-science/reference/cross-skill-playbooks.md`"
                ),
                "Run `bigquery-data-science lookup ML.ENTITY_FEATURES_AT_TIME`",
            ],
        )

    if _matches_any(text, _GENERATIVE_KEYWORDS):
        return TriageResult(
            query=query,
            category="Generative SQL, Managed Classification/Scoring & Group Synthesis",
            recommended_skill="bigquery-ai",
            recommended_skills=["bigquery-ai", "bigquery-ml", "bigquery-mlops"],
            primary_options=[
                (
                    "General-purpose generation: `AI.GENERATE` (GA, with optional "
                    "`output_schema`), `AI.GENERATE_BOOL` / `AI.GENERATE_DOUBLE` / "
                    "`AI.GENERATE_INT` (Preview), `AI.GENERATE_TABLE` (GA), "
                    "`AI.GENERATE_TEXT` (GA), `AI.COUNT_TOKENS` (GA, text-only `STRING` "
                    "input) in `bigquery-ai`"
                ),
                (
                    "Managed prompt-engineered functions (GA): `AI.IF` (`optimization_mode` "
                    "& `embeddings` Preview), `AI.SCORE` (GA), `AI.CLASSIFY` "
                    "(`optimization_mode` & `embeddings` Preview), `AI.AGG` (GA, "
                    "including `output_schema => '...'` up to 10,000 output tokens/group), "
                    "and `AI.TRANSLATE` (GA) in `bigquery-ai`"
                ),
            ],
            head_to_head=(
                "Use GA `AI.IF`, `AI.SCORE`, `AI.CLASSIFY`, `AI.AGG`, and `AI.TRANSLATE` "
                "for zero-config filtering, scoring, fixed-category classification, "
                "multi-row group synthesis (including typed `AI.AGG(..., output_schema => ...)`), "
                "and scalar translation. Drop to `AI.GENERATE` / `AI.GENERATE_TABLE` when "
                "you need pinned `endpoint`, `model_params`, or per-row `full_response` "
                "inspection. To unpack `AI.*` struct outputs laterally in a single `SELECT` "
                "and `WHERE`, check `INFORMATION_SCHEMA.EFFECTIVE_PROJECT_OPTIONS` for GA "
                "reusable column aliases (`reusable_column_aliases_mode = 'on'`) or use a "
                "portable `WITH` CTE."
            ),
            prerequisites=(
                "`AI.GENERATE`, `AI.COUNT_TOKENS`, `AI.IF`, `AI.SCORE`, `AI.CLASSIFY`, "
                "`AI.AGG`, and `AI.TRANSLATE` work directly with end-user credentials "
                "(no `CREATE MODEL` required)."
            ),
            next_steps=[
                (
                    "Inspect `skills/bigquery-ai/reference/general-purpose-generation.md` "
                    "and `managed-functions.md`"
                ),
                (
                    "Run `bigquery-data-science lookup AI.GENERATE` and "
                    "`bigquery-data-science lookup AI.CLASSIFY`"
                ),
            ],
        )

    return TriageResult(
        query=query,
        category="Tabular Prediction, Classification & Regression (`bigquery-ml` vs `AI.PREDICT`)",
        recommended_skill="bigquery-ml",
        recommended_skills=["bigquery-ml", "bigquery-ai", "bigquery-mlops"],
        primary_options=[
            (
                "Trained BigQuery ML models: `LOGISTIC_REG`, `LINEAR_REG`, "
                "`BOOSTED_TREE_CLASSIFIER`, `BOOSTED_TREE_REGRESSOR`, "
                "`RANDOM_FOREST_*`, `DNN_*`, `AUTOML_*` (`bigquery-ml`)"
            ),
            (
                "Zero-training tabular foundation model: `AI.PREDICT` + "
                "`AI.EVALUATE` (TabFM in `bigquery-ai`, Preview)"
            ),
            (
                "Model-free evaluation of saved predictions: `ML.METRICS` "
                "(`bigquery-mlops` / `bigquery-ml`, Preview)"
            ),
        ],
        head_to_head=(
            "Choose trained `bigquery-ml` models when you need reproducible predictions, "
            "> 50 feature columns, > 10 classes, > ~8,000 training rows, p-values/weights "
            "(`ML.ADVANCED_WEIGHTS`), or an exportable model artifact (`xgboost_version = '2.1'`). "
            "Choose `AI.PREDICT` (TabFM) for instant zero-training baselines on small "
            "tables (<= 50 features, <= 10 classes), noting its predictions are "
            "non-deterministic across runs and token-based pricing (`$0.05/1M` input "
            "tokens, `$0.20/1M` output tokens) takes effect `2026-11-17` — materialize "
            "`AI.PREDICT` outputs once and score them deterministically with `ML.METRICS`."
        ),
        prerequisites=(
            "Neither trained `LINEAR_REG`/`LOGISTIC_REG`/`BOOSTED_TREE_*` models nor "
            "`AI.PREDICT` require a Cloud Resource Connection or Enterprise reservation "
            "(only `MATRIX_FACTORIZATION` requires an `ENTERPRISE` reservation)."
        ),
        next_steps=[
            "Inspect `skills/bigquery-ml/reference/classification.md` and `regression.md`",
            "Compare with `skills/bigquery-ai/reference/predictive-ai.md` (`AI.PREDICT`)",
            (
                "Run `bigquery-data-science lookup BOOSTED_TREE_CLASSIFIER` or "
                "`bigquery-data-science lookup AI.PREDICT`"
            ),
        ],
    )


_WALKTHROUGH_ALIASES: Mapping[str, str] = MappingProxyType(
    {
        "validate_data_drift": "model_monitoring",
        "validate_data_skew": "model_monitoring",
        "drift_monitoring": "model_monitoring",
        "data_drift": "model_monitoring",
        "metrics": "evaluation",
        "ml_metrics": "evaluation",
        "export_model": "export",
        "vertex_ai_model_registry": "export",
        "model_registry": "export",
        "import_model": "imported",
        "imported_models": "imported",
        "remote_model": "remote",
        "entity_features_at_time": "feature_store",
        "features_at_time": "feature_store",
        "chunk_document": "ai_chunk_document",
        "parse_document": "ai_parse_document",
        "layout_parser": "ai_chunk_document",
        "translation_llm": "ai_translate",
        "tllm": "ai_translate",
        "nmt": "ai_translate",
    }
)


def get_walkthrough(
    topic: str,
    skills_dir: Path | None = None,
) -> dict[str, object]:
    """Retrieve a full worked walkthrough from `skills/*/narrative/*.md`."""
    not_found: dict[str, object] = {
        "topic": topic,
        "skill": "",
        "path": "",
        "found": False,
        "content": (
            f"No walkthrough found for '{topic}'. Use "
            "`bigquery-data-science search <query>` to list available narratives."
        ),
    }
    root = skills_dir if skills_dir is not None else get_skills_dir()
    cleaned = topic.strip().strip("`")
    if not cleaned or ".." in topic:
        return not_found
    if cleaned.endswith(".md"):
        cleaned = cleaned[:-3]
    parts = cleaned.split("/")
    raw_stem = parts[-1].lower().replace(".", "_").replace("-", "_")
    if not raw_stem or not any(ch.isalnum() for ch in raw_stem):
        return not_found
    stem = _WALKTHROUGH_ALIASES.get(raw_stem, raw_stem)
    stripped_stem = re.sub(r"^(?:pipeline|pipelines|ml)_", "", stem)
    stripped_stem = _WALKTHROUGH_ALIASES.get(stripped_stem, stripped_stem)
    candidate_stems = [
        item
        for item in dict.fromkeys([stem, stripped_stem])
        if item and any(ch.isalnum() for ch in item)
    ]
    if not candidate_stems:
        return not_found
    skill_hint = parts[0] if len(parts) > 1 else None

    for skill_name in ("bigquery-ml", "bigquery-ai"):
        if skill_hint and skill_hint != skill_name:
            continue
        nar_dir = root / skill_name / "narrative"
        if not nar_dir.is_dir():
            continue
        for c_stem in candidate_stems:
            exact_path = nar_dir / f"{c_stem}.md"
            if exact_path.is_file():
                return {
                    "topic": exact_path.stem,
                    "skill": skill_name,
                    "path": f"{skill_name}/narrative/{exact_path.name}",
                    "found": True,
                    "content": exact_path.read_text(encoding="utf-8"),
                }
        for c_stem in candidate_stems:
            for candidate in sorted(nar_dir.glob("*.md")):
                if c_stem and c_stem in candidate.stem.lower():
                    return {
                        "topic": candidate.stem,
                        "skill": skill_name,
                        "path": f"{skill_name}/narrative/{candidate.name}",
                        "found": True,
                        "content": candidate.read_text(encoding="utf-8"),
                    }

    return not_found


def lookup(
    symbol: str,
    *,
    skills_dir: Path | None = None,
) -> dict[str, object]:
    """Look up syntax card, prerequisites, gotchas, and narratives for `symbol`."""
    return lookup_symbol(symbol=symbol, skills_dir=skills_dir).to_dict()


def search(
    query: str,
    limit: int = 10,
    *,
    skill: str | None = None,
    lens: str | None = None,
    skills_dir: Path | None = None,
) -> list[dict[str, object]]:
    """Search across all 3 skills and 4 progressive lenses."""
    hits = search_catalog(
        query=query,
        skill_filter=skill,
        lens_filter=lens,
        limit=limit,
        skills_dir=skills_dir,
    )
    return [hit.to_dict() for hit in hits]


def triage(
    query: str,
    *,
    skills_dir: Path | None = None,
) -> dict[str, object]:
    """Route a data-science task description across `ML.*` and `AI.*`."""
    return triage_task(query=query, skills_dir=skills_dir).to_dict()


@dataclass
class ReviewFinding:
    """Single static-analysis finding for a BigQuery ML or BigQuery AI SQL query."""

    severity: str
    rule: str
    message: str
    remediation: str

    @property
    def code(self) -> str:
        """Alias for `rule`."""
        return self.rule

    def to_dict(self) -> dict[str, str]:
        """Convert the finding to a JSON-serializable dictionary."""
        return {
            "severity": self.severity,
            "rule": self.rule,
            "message": self.message,
            "remediation": self.remediation,
        }


@dataclass
class SqlReviewResult:
    """Structured result for `review_sql`."""

    sql: str
    detected_symbols: list[str] = field(default_factory=list)
    prerequisites: list[dict[str, str]] = field(default_factory=list)
    findings: list[ReviewFinding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return True when no ERROR-severity findings were raised."""
        return not any(f.severity == "ERROR" for f in self.findings)

    @property
    def error_count(self) -> int:
        """Return count of ERROR-severity findings."""
        return sum(1 for f in self.findings if f.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        """Return count of WARNING-severity findings."""
        return sum(1 for f in self.findings if f.severity == "WARNING")

    def to_dict(self) -> dict[str, object]:
        """Convert the SQL review result to a JSON-serializable dictionary."""
        return {
            "ok": self.ok,
            "detected_symbols": self.detected_symbols,
            "prerequisites": self.prerequisites,
            "findings": [f.to_dict() for f in self.findings],
        }

    def format_text(self) -> str:
        """Render a human- and agent-readable SQL review report."""
        verdict = "PASS (no errors)" if self.ok else "FAIL (errors detected)"
        lines: list[str] = [f"# BigQuery SQL Review: {verdict}"]
        if self.detected_symbols:
            syms = ", ".join(f"`{s}`" for s in self.detected_symbols)
            lines.append(f"**Detected Symbols:** {syms}")
        else:
            lines.append("**Detected Symbols:** None (`ML.*`, `AI.*`, or `CREATE MODEL` not found)")

        if self.prerequisites:
            lines.append("\n## Prerequisites (`namespace-matrix.md`)")
            for row in self.prerequisites:
                summary = ", ".join(f"{k}: {v}" for k, v in row.items() if v)
                lines.append(f"- {summary}")

        if self.findings:
            lines.append("\n## Findings & Empirical Guardrails")
            for finding in self.findings:
                lines.append(
                    f"- **[{finding.severity}] `{finding.rule}`**: {finding.message}\n"
                    f"  - *Fix:* {finding.remediation}"
                )
        else:
            lines.append(
                "\n## Findings & Empirical Guardrails\n"
                "- No anti-patterns or unpinned model issues detected."
            )
        return "\n".join(lines)


_SQL_COMMENT_RE = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)
_SQL_FN_TOKEN_RE = re.compile(
    r"\b(AI\.[A-Z0-9_]+|ML\.[A-Z0-9_]+|OBJ\.[A-Z0-9_]+|VECTOR_SEARCH|HYBRID_SEARCH)\s*\(",
    re.IGNORECASE,
)
_MODEL_TYPE_SQL_RE = re.compile(
    r"\bMODEL_TYPE\s*=\s*['\"]([A-Za-z0-9_]+)['\"]",
    re.IGNORECASE,
)
_ENDPOINT_ARG_RE = re.compile(
    r"\b(?:endpoint|model)\s*(?:=>|=)\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)
_CREATE_MODEL_HANDLE_RE = re.compile(
    r"\bCREATE\s+(?:OR\s+REPLACE\s+)?MODEL\s+(?:IF\s+NOT\s+EXISTS\s+)?(`[^`]+`|[A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)
_GEMINI_EMB2_PIN_RE = re.compile(
    r"\b(?:endpoint|model)\s*(?:=>|=)\s*['\"]gemini-embedding-2['\"]",
    re.IGNORECASE,
)
_GEMINI_4_PIN_RE = re.compile(
    r"\b(?:endpoint|model)\s*(?:=>|=)\s*['\"]gemini-4-(?:argon|carbon|hydrogen)['\"]",
    re.IGNORECASE,
)
_GEMINI_4_THINKING_BUDGET_RE = re.compile(
    r"\bthinking_?budget\b",
    re.IGNORECASE,
)
_GEMINI_4_UNSUPPORTED_THINKING_LEVEL_RE = re.compile(
    r"thinking_?level['\"\s:=]+['\"]?(?:MINIMAL|XHIGH)\b",
    re.IGNORECASE,
)
_LEGACY_PARSE_DOC_TVF_RE = re.compile(
    r"\b(?:FROM|JOIN)\s+AI\.PARSE_DOCUMENT\s*\(",
    re.IGNORECASE,
)
_LEGACY_PARSE_DOC_ENDPOINT_RE = re.compile(
    r"\b(?:endpoint|processor_id)\s*(?:=>|=)",
    re.IGNORECASE,
)
_LEGACY_PARSE_DOC_TABLE_ARG_RE = re.compile(
    r"^\s*TABLE\b",
    re.IGNORECASE,
)
_MODEL_REF_RE = re.compile(
    r"\bMODEL\s+(`[^`]+`|[A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)
_EMB_UNSUPPORTED_NAMED_ARG_RE = re.compile(
    r"\b(?:task_type|title)\s*(?:=>|=)",
    re.IGNORECASE,
)
_EMB_UNSUPPORTED_STRUCT_AS_RE = re.compile(
    r"\bAS\s+(?:task_type|title)\b",
    re.IGNORECASE,
)
_EMB_UNSUPPORTED_JSON_KEY_RE = re.compile(
    r"['\"](?:task_type|title)['\"]\s*:",
    re.IGNORECASE,
)


_CHUNK_SIZE_MIN = 1
_CHUNK_SIZE_MAX = 2000
_CONNECTION_ID_ARG_RE = re.compile(r"\bconnection_id\s*(?:=>|=)", re.IGNORECASE)
_OPTIONS_ARG_RE = re.compile(r"\boptions\s*(?:=>|=)", re.IGNORECASE)
_RETURN_DETAILS_TRUE_RE = re.compile(r"\breturn_details\s*(?:=>|=)\s*TRUE\b", re.IGNORECASE)
_EMPTY_STATUS_CMP_RE = re.compile(r"\bstatus\s*(?:=|!=|<>)\s*(?:''|\"\")", re.IGNORECASE)
_DOT_EMPTY_STATUS_CMP_RE = re.compile(
    r"([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*status\s*(?:=|!=|<>)\s*(?:''|\"\")",
    re.IGNORECASE,
)
_DOT_NULL_STATUS_CMP_RE = re.compile(
    r"([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*status\s+IS\s+NULL\b",
    re.IGNORECASE,
)
_CHUNK_SIZE_FLOAT_RE = re.compile(
    r"\bchunk_size\s*(?:=>|=)\s*(?:CAST\s*\(\s*|\s*\()*(-?\d+\.\d+)",
    re.IGNORECASE,
)
_CHUNK_SIZE_INT_RE = re.compile(
    r"\bchunk_size\s*(?:=>|=)\s*(?:CAST\s*\(\s*|\s*\()*(-?\d+)(?!\s*\.\d)",
    re.IGNORECASE,
)
_STATUS_IS_NULL_RE = re.compile(r"\bstatus\s+IS\s+NULL\b", re.IGNORECASE)
_CHUNK_INTENTIONAL_STATUS_RE = re.compile(
    r"(?:\bstatus\s*(?:=|!=|<>)\s*(?:''|\"\")|\b(?:COUNTIF|CASE\s+WHEN)\s*\(?\s*(?:[A-Za-z_][A-Za-z0-9_]*\.)?status\s+IS\s+NULL\b)",
    re.IGNORECASE,
)
_SQL_ALIAS_STOPWORDS: frozenset[str] = frozenset(
    {
        "FROM",
        "WHERE",
        "GROUP",
        "ORDER",
        "LIMIT",
        "HAVING",
        "QUALIFY",
        "UNION",
        "JOIN",
        "LEFT",
        "RIGHT",
        "INNER",
        "CROSS",
        "ON",
        "AND",
        "OR",
        "WHEN",
        "THEN",
        "ELSE",
        "END",
    }
)
_GENERATIVE_FUNCTIONS: frozenset[str] = frozenset(
    {
        "AI.GENERATE",
        "AI.GENERATE_BOOL",
        "AI.GENERATE_INT",
        "AI.GENERATE_DOUBLE",
        "AI.GENERATE_TABLE",
    }
)
_EMPTY_STATUS_FUNCTIONS: frozenset[str] = _GENERATIVE_FUNCTIONS | frozenset(
    {
        "AI.CHUNK_DOCUMENT",
        "AI.EMBED",
        "AI.FORECAST",
        "AI.GENERATE_TEXT",
        "AI.GENERATE_EMBEDDING",
        "ML.GENERATE_TEXT",
        "ML.GENERATE_EMBEDDING",
        "ML.PROCESS_DOCUMENT",
        "ML.TRANSLATE",
        "ML.ANNOTATE_IMAGE",
        "ML.TRANSCRIBE",
        "ML.UNDERSTAND_TEXT",
    }
)


def strip_sql_comments(sql: str) -> str:
    """Remove `--` line comments and `/* ... */` block comments outside quotes."""
    out: list[str] = []
    index = 0
    length = len(sql)
    quote: str | None = None
    while index < length:
        char = sql[index]
        if quote is not None:
            if char == "\\" and index + 1 < length:
                out.append(sql[index : index + 2])
                index += 2
                continue
            if len(quote) == 3:
                if sql[index : index + 3] == quote:
                    out.append(quote)
                    index += 3
                    quote = None
                    continue
            elif char == quote:
                if index + 1 < length and sql[index + 1] == quote:
                    out.append(char * 2)
                    index += 2
                    continue
                out.append(char)
                index += 1
                quote = None
                continue
            out.append(char)
            index += 1
            continue

        if sql[index : index + 2] == "--":
            newline_pos = sql.find("\n", index + 2)
            if newline_pos == -1:
                break
            index = newline_pos
            continue
        if sql[index : index + 2] == "/*":
            close_pos = sql.find("*/", index + 2)
            out.append(" ")
            if close_pos == -1:
                break
            index = close_pos + 2
            continue
        if sql[index : index + 3] in ("'''", '"""'):
            quote = sql[index : index + 3]
            out.append(quote)
            index += 3
            continue
        if char in ("'", '"', "`"):
            quote = char
            out.append(char)
            index += 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _mask_sql_string_literals(sql: str) -> str:
    """Replace single- and double-quoted SQL string literal contents with spaces."""
    out: list[str] = []
    index = 0
    length = len(sql)
    quote: str | None = None
    while index < length:
        char = sql[index]
        if quote is not None:
            if quote == "`":
                if char == "\\" and index + 1 < length:
                    out.append(sql[index : index + 2])
                    index += 2
                    continue
                out.append(char)
                index += 1
                if char == "`":
                    quote = None
                continue
            if char == "\\" and index + 1 < length:
                out.append("  ")
                index += 2
                continue
            if len(quote) == 3:
                if sql[index : index + 3] == quote:
                    out.append(quote)
                    index += 3
                    quote = None
                    continue
            elif char == quote:
                if index + 1 < length and sql[index + 1] == quote:
                    out.append("  ")
                    index += 2
                    continue
                out.append(char)
                index += 1
                quote = None
                continue
            out.append("\n" if char == "\n" else " ")
            index += 1
            continue

        if sql[index : index + 3] in ("'''", '"""'):
            quote = sql[index : index + 3]
            out.append(quote)
            index += 3
            continue
        if char in ("'", '"', "`"):
            quote = char
            out.append(char)
            index += 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _iter_function_call_spans(sql: str, function_name: str) -> list[tuple[str, int]]:
    """Return `(arg_substring, closing_paren_end_index)` for `function_name(...)`."""
    pattern = re.compile(rf"\b{re.escape(function_name)}\s*\(", re.IGNORECASE)
    spans: list[tuple[str, int]] = []
    length = len(sql)
    for match in pattern.finditer(sql):
        index = match.end()
        depth = 1
        quote: str | None = None
        start = index
        while index < length and depth > 0:
            char = sql[index]
            if quote is not None:
                if char == "\\":
                    index += 2
                    continue
                if len(quote) == 3:
                    if sql[index : index + 3] == quote:
                        index += 3
                        quote = None
                        continue
                elif char == quote:
                    if index + 1 < length and sql[index + 1] == quote:
                        index += 2
                        continue
                    quote = None
            elif sql[index : index + 3] in ("'''", '"""'):
                quote = sql[index : index + 3]
                index += 3
                continue
            elif char in ("'", '"', "`"):
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    spans.append((sql[start:index], index + 1))
                    break
            index += 1
    return spans


def _iter_function_call_args(sql: str, function_name: str) -> list[str]:
    """Return balanced argument substrings for calls to `function_name(...)`."""
    return [args for args, _ in _iter_function_call_spans(sql, function_name)]


def _top_level_call_args(masked_call_args: str) -> str:
    """Replace nested parenthesized expressions with spaces so only top-level args remain."""
    out: list[str] = []
    depth = 0
    for char in masked_call_args:
        if char == "(":
            depth += 1
            out.append("(")
        elif char == ")":
            depth = max(0, depth - 1)
            out.append(")")
        elif depth > 0:
            out.append("\n" if char == "\n" else " ")
        else:
            out.append(char)
    return "".join(out)


def review_sql(
    sql: str,
    skills_dir: Path | None = None,
) -> SqlReviewResult:
    """Statically review a BigQuery SQL query for prerequisites and gotchas."""
    root = skills_dir if skills_dir is not None else get_skills_dir()
    cleaned = sql.strip()
    uncommented = strip_sql_comments(cleaned)
    masked = _mask_sql_string_literals(uncommented)
    masked_upper = masked.upper()

    detected: list[str] = []
    for match in _SQL_FN_TOKEN_RE.finditer(masked):
        symbol_token = match.group(1).upper()
        if symbol_token not in detected:
            detected.append(symbol_token)
    for match in _MODEL_TYPE_SQL_RE.finditer(uncommented):
        model_type = match.group(1).upper()
        canonical = _SYMBOL_ALIASES.get(model_type, model_type)
        if canonical not in detected:
            detected.append(canonical)

    matrix_path = root / "bigquery-data-science" / "reference" / "namespace-matrix.md"
    matrix_rows = _parse_namespace_matrix(matrix_path)
    prerequisites: list[dict[str, str]] = []
    for symbol_token in detected:
        matched_row = False
        for row in matrix_rows:
            row_symbol = row.get("Symbol", "").upper()
            if symbol_token in row_symbol:
                matched_row = True
                if row not in prerequisites:
                    prerequisites.append(row)
        if not matched_row and symbol_token in _FALLBACK_PREREQUISITES:
            fallback_row = dict(_FALLBACK_PREREQUISITES[symbol_token])
            if fallback_row not in prerequisites:
                prerequisites.append(fallback_row)

    findings: list[ReviewFinding] = []

    if "AI.PARSE_DOCUMENT" in detected or re.search(r"\bAI\.PARSE_DOCUMENT\b", masked_upper):
        parse_doc_calls = _iter_function_call_args(masked, "AI.PARSE_DOCUMENT")
        has_legacy_tvf = _LEGACY_PARSE_DOC_TVF_RE.search(masked) is not None
        has_legacy_arg = any(
            _LEGACY_PARSE_DOC_ENDPOINT_RE.search(call_args) is not None
            or _LEGACY_PARSE_DOC_TABLE_ARG_RE.search(call_args) is not None
            for call_args in parse_doc_calls
        )
        if has_legacy_tvf or has_legacy_arg:
            findings.append(
                ReviewFinding(
                    severity="ERROR",
                    rule="LEGACY_PARSE_DOCUMENT_TVF",
                    message=(
                        "`AI.PARSE_DOCUMENT` is a GA scalar function (`-> JSON`), not the "
                        "legacy early-Preview `FROM AI.PARSE_DOCUMENT(TABLE ..., "
                        "endpoint => ...)` TVF."
                    ),
                    remediation=(
                        "Call scalar `AI.PARSE_DOCUMENT(document [, connection_id => '...'] "
                        "[, options => JSON '{\"schema\": \"layout-v1\" | \"raw-docai\"}'])` "
                        "in `SELECT`, use `FROM AI.CHUNK_DOCUMENT(...)` for layout-aware "
                        "RAG chunking, or use `ML.PROCESS_DOCUMENT` for specialized "
                        "Document AI processors."
                    ),
                )
            )

    if "HYBRID_SEARCH" in detected:
        findings.append(
            ReviewFinding(
                severity="ERROR",
                rule="NONEXISTENT_HYBRID_TVF",
                message="BigQuery does not have a standalone `HYBRID_SEARCH` TVF.",
                remediation=(
                    "Use `VECTOR_SEARCH(..., options => '{\"lexical_search_columns\": [...]}')` "
                    "or `AI.SEARCH(..., mode => 'HYBRID')`."
                ),
            )
        )

    allow_file = find_allow_file(root) or find_allow_file(get_skills_dir())
    allowed_models: set[str] = set()
    deprecated_models: dict[str, str] = {}
    if allow_file is not None and allow_file.is_file():
        allowed_models = (
            load_allow_list(allow_file, "bigquery-ai")
            | load_allow_list(allow_file, "bigquery-ml")
            | {"gemini-4-hydrogen", "gemini-4-carbon", "gemini-4-argon"}
        )
        raw_allow = json.loads(allow_file.read_text(encoding="utf-8"))
        if isinstance(raw_allow.get("deprecated"), dict):
            deprecated_models = {
                str(key): str(replacement) for key, replacement in raw_allow["deprecated"].items()
            }

    for endpoint_match in _ENDPOINT_ARG_RE.finditer(uncommented):
        endpoint_value = endpoint_match.group(1).strip()
        if (
            endpoint_value
            and allowed_models
            and not is_placeholder(endpoint_value)
            and not endpoint_value.startswith(("projects/", "https://"))
            and endpoint_value not in allowed_models
        ):
            if endpoint_value in deprecated_models:
                remediation = (
                    f"Replace retired `{endpoint_value}` with "
                    f"`{deprecated_models[endpoint_value]}` "
                    "(or current preferred defaults `'gemini-3.8-flash'`, "
                    "`'gemini-4-hydrogen'`, `'gemini-4-carbon'`, `'gemini-4-argon'`, "
                    "`'gemini-3.5-flash-lite'`, `'gemini-embedding-2'`)."
                )
            else:
                remediation = (
                    "Pin a current supported model from `skills/pinned-models.json` "
                    "such as `'gemini-3.8-flash'`, `'gemini-4-hydrogen'`, "
                    "`'gemini-4-carbon'`, `'gemini-4-argon'`, "
                    "`'gemini-3.5-flash-lite'`, `'gemini-embedding-2'`, "
                    "`'gemini-embedding-001'`, `'text-embedding-005'`, "
                    "`'embeddinggemma-300m'`, `'TimesFM 2.5'`, `'TimesFM 3.0'`, "
                    "`'nmt'`, or `'translation-llm'`."
                )
            findings.append(
                ReviewFinding(
                    severity="ERROR",
                    rule="DEPRECATED_MODEL_ENDPOINT",
                    message=(
                        f"Model or endpoint `{endpoint_value}` is not in the "
                        "`pinned-models.json` allowlist."
                    ),
                    remediation=remediation,
                )
            )

    emb2_handles: set[str] = set()
    gemini4_handles: set[str] = set()
    emitted_emb2_warn = False
    emitted_gemini4_warn = False
    emitted_parse_chunk_warn = False
    stmt_start = 0
    for sep_match in re.finditer(r";|$", masked):
        stmt_end = sep_match.start()
        stmt_raw = uncommented[stmt_start:stmt_end]
        stmt_masked = masked[stmt_start:stmt_end]
        stmt_start = sep_match.end()
        if not stmt_masked.strip():
            continue

        create_match = _CREATE_MODEL_HANDLE_RE.search(stmt_masked)
        if create_match is not None:
            raw_handle = create_match.group(1).strip("`").strip().lower()
            short_handle = raw_handle.rsplit(".", 1)[-1]
            if _GEMINI_EMB2_PIN_RE.search(stmt_raw):
                emb2_handles.add(raw_handle)
                emb2_handles.add(short_handle)
            elif _ENDPOINT_ARG_RE.search(stmt_raw):
                emb2_handles.discard(raw_handle)
                emb2_handles.discard(short_handle)
            if _GEMINI_4_PIN_RE.search(stmt_raw):
                gemini4_handles.add(raw_handle)
                gemini4_handles.add(short_handle)
            elif _ENDPOINT_ARG_RE.search(stmt_raw):
                gemini4_handles.discard(raw_handle)
                gemini4_handles.discard(short_handle)

        uses_emb2 = _GEMINI_EMB2_PIN_RE.search(stmt_raw) is not None
        if not uses_emb2 and emb2_handles:
            for ref_match in _MODEL_REF_RE.finditer(stmt_masked):
                ref_handle = ref_match.group(1).strip("`").strip().lower()
                ref_short = ref_handle.rsplit(".", 1)[-1]
                if ref_handle in emb2_handles or ref_short in emb2_handles:
                    uses_emb2 = True
                    break

        if uses_emb2 and not emitted_emb2_warn:
            emb_struct_Calls = (
                _iter_function_call_args(stmt_masked, "STRUCT")
                + _iter_function_call_args(stmt_masked, "AI.GENERATE_EMBEDDING")
                + _iter_function_call_args(stmt_masked, "ML.GENERATE_EMBEDDING")
            )
            has_unsupported_arg = (
                _EMB_UNSUPPORTED_NAMED_ARG_RE.search(stmt_masked) is not None
                or any(
                    _EMB_UNSUPPORTED_STRUCT_AS_RE.search(call_args) is not None
                    for call_args in emb_struct_Calls
                )
                or _EMB_UNSUPPORTED_JSON_KEY_RE.search(stmt_raw) is not None
            )
            if has_unsupported_arg:
                emitted_emb2_warn = True
                findings.append(
                    ReviewFinding(
                        severity="WARNING",
                        rule="GEMINI_EMBEDDING_2_UNSUPPORTED_ARGS",
                        message=(
                            "`gemini-embedding-2` rejects `task_type` and `title` "
                            "arguments (`400 The task_type and title arguments of "
                            "ai.embed are not supported for gemini-embedding-2 model`)."
                        ),
                        remediation=(
                            "Omit `task_type` and `title` when using `'gemini-embedding-2'` "
                            "(unified task-agnostic multimodal embedding), or use "
                            "`'gemini-embedding-001'` / `'text-embedding-005'` when "
                            "`task_type` or `title` is required."
                        ),
                    )
                )

        uses_gemini4 = _GEMINI_4_PIN_RE.search(stmt_raw) is not None
        if not uses_gemini4 and gemini4_handles:
            for ref_match in _MODEL_REF_RE.finditer(stmt_masked):
                ref_handle = ref_match.group(1).strip("`").strip().lower()
                ref_short = ref_handle.rsplit(".", 1)[-1]
                if ref_handle in gemini4_handles or ref_short in gemini4_handles:
                    uses_gemini4 = True
                    break

        if uses_gemini4 and not emitted_gemini4_warn:
            has_bad_thinking = (
                _GEMINI_4_THINKING_BUDGET_RE.search(stmt_raw) is not None
                or _GEMINI_4_UNSUPPORTED_THINKING_LEVEL_RE.search(stmt_raw) is not None
            )
            if has_bad_thinking:
                emitted_gemini4_warn = True
                findings.append(
                    ReviewFinding(
                        severity="WARNING",
                        rule="GEMINI_4_THINKING_BUDGET",
                        message=(
                            "Gemini 4 endpoints (`gemini-4-argon`, `gemini-4-carbon`, "
                            "`gemini-4-hydrogen`) use `thinking_level` (`'LOW'`, `'MEDIUM'`, "
                            "or `'HIGH'`) instead of `thinking_budget`, and BigQuery's SQL "
                            "`model_params` validator rejects `'MINIMAL'` and `'XHIGH'` "
                            "with HTTP 400."
                        ),
                        remediation=(
                            "Use `model_params => JSON '{\"generation_config\": "
                            "{\"thinking_config\": {\"thinking_level\": \"LOW\" | "
                            "\"MEDIUM\" | \"HIGH\"}}}'` on Gemini 4 endpoints."
                        ),
                    )
                )

        if (
            not emitted_parse_chunk_warn
            and re.search(r"\bAI\.PARSE_DOCUMENT\s*\(", stmt_masked, re.IGNORECASE) is not None
            and re.search(r"\bAI\.CHUNK_DOCUMENT\s*\(", stmt_masked, re.IGNORECASE) is not None
            and re.search(r"raw-docai", stmt_raw, re.IGNORECASE) is None
        ):
            emitted_parse_chunk_warn = True
            findings.append(
                ReviewFinding(
                    severity="WARNING",
                    rule="PARSE_DOCUMENT_CHUNK_SCHEMA",
                    message=(
                        "Chaining `AI.PARSE_DOCUMENT` into `AI.CHUNK_DOCUMENT` without "
                        "`options => JSON '{\"schema\": \"raw-docai\"}'` uses the default "
                        "`layout-v1` schema, which `AI.CHUNK_DOCUMENT` rejects per row "
                        "(`INVALID_ARGUMENT: Unsupported document schema: layout-v1`)."
                    ),
                    remediation=(
                        "Pass `options => JSON '{\"schema\": \"raw-docai\"}'` to "
                        "`AI.PARSE_DOCUMENT(...)` and alias the column `AS parsed_document` "
                        "when feeding `AI.CHUNK_DOCUMENT`."
                    ),
                )
            )

    gen_calls = [
        call_args
        for fn in _GENERATIVE_FUNCTIONS
        if fn in detected
        for call_args in _iter_function_call_args(masked, fn)
    ]
    if gen_calls and any(
        re.search(r"\bendpoint\s*(?:=>|=)", call_args, re.IGNORECASE) is None
        for call_args in gen_calls
    ):
        findings.append(
            ReviewFinding(
                severity="WARNING",
                rule="UNPINNED_AI_ENDPOINT",
                message="Generative `AI.GENERATE*` call omits an explicit `endpoint =>` argument.",
                remediation=(
                    "Pin `endpoint => 'gemini-3.8-flash'` (or `'gemini-4-hydrogen'` / "
                    "`'gemini-4-carbon'` / `'gemini-4-argon'` / `'gemini-3.5-flash-lite'`) "
                    "from `skills/pinned-models.json` for reproducible production behavior."
                ),
            )
        )

    if "AI.FORECAST" in detected:
        forecast_masked_calls = _iter_function_call_args(masked, "AI.FORECAST")
        forecast_raw_calls = _iter_function_call_args(uncommented, "AI.FORECAST")
        has_model_arg = bool(forecast_masked_calls) and all(
            re.search(r"\bmodel\s*(?:=>|=)", call_args, re.IGNORECASE) is not None
            for call_args in forecast_masked_calls
        )
        has_3_0_cols = any(
            col in call_args.upper()
            for call_args in forecast_masked_calls
            for col in ("TARGET_COLS", "PAST_COVARIATE_COLS", "FUTURE_COVARIATE_COLS")
        )
        has_3_0_model = any("TIMESFM 3.0" in call_args.upper() for call_args in forecast_raw_calls)
        if not has_model_arg:
            findings.append(
                ReviewFinding(
                    severity="WARNING",
                    rule="UNPINNED_FORECAST_MODEL",
                    message="`AI.FORECAST` call omits an explicit `model =>` argument.",
                    remediation=(
                        "Pin `model => 'TimesFM 2.5'` (GA univariate) or "
                        "`model => 'TimesFM 3.0'` (Preview covariates/multivariate)."
                    ),
                )
            )
        if has_3_0_cols and not has_3_0_model:
            findings.append(
                ReviewFinding(
                    severity="ERROR",
                    rule="TIMESFM_COVARIATES_REQUIRE_3_0",
                    message=(
                        "`AI.FORECAST` uses `target_cols`, `past_covariate_cols`, or "
                        "`future_covariate_cols` without `model => 'TimesFM 3.0'`."
                    ),
                    remediation="Set `model => 'TimesFM 3.0'` when forecasting with covariates.",
                )
            )

    direct_objref_fns = _GENERATIVE_FUNCTIONS | {
        "AI.IF",
        "AI.SCORE",
        "AI.CLASSIFY",
        "AI.EMBED",
        "AI.SIMILARITY",
        "AI.AGG",
        "AI.CHUNK_DOCUMENT",
        "AI.PARSE_DOCUMENT",
    }
    if "OBJ.GET_ACCESS_URL" in detected and any(fn in detected for fn in direct_objref_fns):
        findings.append(
            ReviewFinding(
                severity="WARNING",
                rule="UNNECESSARY_GET_ACCESS_URL",
                message=(
                    "`OBJ.GET_ACCESS_URL` is used alongside a direct `AI.*` function "
                    "that accepts bare `ObjectRef` values."
                ),
                remediation=(
                    "Pass the `ObjectRef` column (`OBJ.MAKE_REF` / `OBJ.FETCH_METADATA`) "
                    "directly to `AI.*` without wrapping in `OBJ.GET_ACCESS_URL`."
                ),
            )
        )

    xgb_models = {
        "BOOSTED_TREE_CLASSIFIER",
        "BOOSTED_TREE_REGRESSOR",
        "RANDOM_FOREST_CLASSIFIER",
        "RANDOM_FOREST_REGRESSOR",
    }
    if any(m in detected for m in xgb_models) and "XGBOOST_VERSION" not in masked_upper:
        findings.append(
            ReviewFinding(
                severity="INFO",
                rule="MISSING_XGBOOST_VERSION",
                message="Tree model omits `xgboost_version = '2.1'` in `OPTIONS(...)`.",
                remediation=(
                    "Add `xgboost_version = '2.1'` if you plan to export the model "
                    "or convert it via `ML.CONVERT`."
                ),
            )
        )

    enterprise_syms = {
        "MATRIX_FACTORIZATION",
        "ML.DECODE_IMAGE",
        "ML.RESIZE_IMAGE",
        "ML.CONVERT_COLOR_SPACE",
        "ML.CONVERT_IMAGE_TYPE",
    }
    matched_ent = [s for s in detected if s in enterprise_syms]
    if matched_ent or "ALTER VECTOR INDEX" in masked_upper:
        label = ", ".join(matched_ent) if matched_ent else "ALTER VECTOR INDEX"
        findings.append(
            ReviewFinding(
                severity="WARNING",
                rule="ENTERPRISE_RESERVATION_REQUIRED",
                message=f"`{label}` requires a BigQuery `ENTERPRISE` reservation assignment.",
                remediation=(
                    "Ensure the project has an active `ENTERPRISE` (or `ENTERPRISE_PLUS`) "
                    "`QUERY` / `BACKGROUND` reservation assignment before running."
                ),
            )
        )

    if (
        any(s in detected for s in ("ML.ENTITY_FEATURES_AT_TIME", "ML.FEATURES_AT_TIME"))
        and "IGNORE_FEATURE_NULLS" not in masked_upper
    ):
        findings.append(
            ReviewFinding(
                severity="INFO",
                rule="FEATURE_TIME_NULL_SEMANTICS",
                message=("Point-in-time feature TVF omits explicit `ignore_feature_nulls`."),
                remediation=(
                    "Set `ignore_feature_nulls => TRUE` on sparse/EAV feature tables so a "
                    "`NULL` in one feature does not overwrite non-null values from earlier "
                    "timestamps; keep `FALSE` on dense snapshot tables."
                ),
            )
        )

    if "ML.METRICS" in detected:
        findings.append(
            ReviewFinding(
                severity="INFO",
                rule="ML_METRICS_BOOL_POSITIVE_CLASS",
                message="`ML.METRICS` ignores `positive_class` when inputs are `BOOL`.",
                remediation=(
                    "For `BOOL` binary classification columns, `TRUE` is always the "
                    "positive class; cast `BOOL` to `STRING` if you need `FALSE` as "
                    "the positive class."
                ),
            )
        )

    if "AI.TRANSLATE" in detected:
        translate_spans = _iter_function_call_spans(masked, "AI.TRANSLATE")
        translate_calls = [args for args, _ in translate_spans]
        if any(_CONNECTION_ID_ARG_RE.search(call_args) for call_args in translate_calls):
            findings.append(
                ReviewFinding(
                    severity="ERROR",
                    rule="AI_TRANSLATE_CONNECTION_ID",
                    message=(
                        "`AI.TRANSLATE` does not accept `connection_id` "
                        "(always executes with End-User Credentials)."
                    ),
                    remediation=(
                        "Remove `connection_id => ...` from `AI.TRANSLATE(...)`, or use "
                        "`ML.TRANSLATE` with a `CLOUD_AI_TRANSLATE_V3` remote model when "
                        "a `CLOUD_RESOURCE` connection service account is required."
                    ),
                )
            )

        translate_detail_aliases: set[str] = set()
        has_return_details = False
        for call_args, end_idx in translate_spans:
            if _RETURN_DETAILS_TRUE_RE.search(call_args):
                has_return_details = True
                alias_match = re.match(
                    r"^\s*(?:AS\s+)?([A-Za-z_][A-Za-z0-9_]*)\b",
                    masked[end_idx:],
                    re.IGNORECASE,
                )
                if alias_match:
                    candidate_alias = alias_match.group(1).upper()
                    if candidate_alias not in _SQL_ALIAS_STOPWORDS:
                        translate_detail_aliases.add(candidate_alias)

        has_empty_status = _EMPTY_STATUS_CMP_RE.search(masked) is not None
        dot_empty_aliases = {m.group(1).upper() for m in _DOT_EMPTY_STATUS_CMP_RE.finditer(masked)}
        dot_null_aliases = {m.group(1).upper() for m in _DOT_NULL_STATUS_CMP_RE.finditer(masked)}
        has_other_empty_fn = any(fn in detected for fn in _EMPTY_STATUS_FUNCTIONS)
        has_null_status_fn = any(
            fn in detected for fn in ("AI.EVALUATE", "AI.DETECT_ANOMALIES", "AI.CHUNK_DOCUMENT")
        )
        matched_translate_alias_bad_status = bool(
            translate_detail_aliases & (dot_empty_aliases | dot_null_aliases)
        )
        unscoped_bad_status = not has_other_empty_fn and (
            has_empty_status
            or bool(dot_empty_aliases)
            or (
                not has_null_status_fn
                and (bool(dot_null_aliases) or _STATUS_IS_NULL_RE.search(masked) is not None)
            )
        )
        if has_return_details and (matched_translate_alias_bad_status or unscoped_bad_status):
            findings.append(
                ReviewFinding(
                    severity="WARNING",
                    rule="AI_TRANSLATE_STATUS_OK",
                    message=(
                        "`AI.TRANSLATE(..., return_details => TRUE)` sets "
                        "`status = 'OK'` on success, not `''` (empty string)."
                    ),
                    remediation=(
                        "Filter `AI.TRANSLATE` struct outputs with `WHERE status = 'OK'` "
                        "(or `status != 'OK'` for failed rows); comparing `status` to "
                        "`''` drops all successful translations."
                    ),
                )
            )

    if "AI.CHUNK_DOCUMENT" in detected:
        chunk_calls = [
            _top_level_call_args(c)
            for c in _iter_function_call_args(masked, "AI.CHUNK_DOCUMENT")
        ]
        for call_args in chunk_calls:
            if _OPTIONS_ARG_RE.search(call_args):
                findings.append(
                    ReviewFinding(
                        severity="ERROR",
                        rule="AI_CHUNK_DOCUMENT_OPTIONS_ARG",
                        message="`AI.CHUNK_DOCUMENT` does not accept an `options` argument.",
                        remediation=(
                            "Pass `chunk_size => <INT64>` (`1` to `2000`, default `1000`) "
                            "directly as a top-level named argument."
                        ),
                    )
                )
                break

        for call_args in chunk_calls:
            float_match = _CHUNK_SIZE_FLOAT_RE.search(call_args)
            if float_match is not None:
                findings.append(
                    ReviewFinding(
                        severity="ERROR",
                        rule="AI_CHUNK_DOCUMENT_CHUNK_SIZE",
                        message=(
                            "`AI.CHUNK_DOCUMENT` `chunk_size` must be an `INT64` between "
                            f"{_CHUNK_SIZE_MIN} and {_CHUNK_SIZE_MAX} tokens "
                            f"(got {float_match.group(1)})."
                        ),
                        remediation=(
                            f"Set `chunk_size` to an `INT64` between "
                            f"`{_CHUNK_SIZE_MIN}` and `{_CHUNK_SIZE_MAX}` "
                            "(default `1000`)."
                        ),
                    )
                )
                break
            for size_match in _CHUNK_SIZE_INT_RE.finditer(call_args):
                chunk_size_value = int(size_match.group(1))
                if chunk_size_value < _CHUNK_SIZE_MIN or chunk_size_value > _CHUNK_SIZE_MAX:
                    findings.append(
                        ReviewFinding(
                            severity="ERROR",
                            rule="AI_CHUNK_DOCUMENT_CHUNK_SIZE",
                            message=(
                                "`AI.CHUNK_DOCUMENT` `chunk_size` must be between "
                                f"{_CHUNK_SIZE_MIN} and {_CHUNK_SIZE_MAX} tokens "
                                f"(got {chunk_size_value})."
                            ),
                            remediation=(
                                f"Set `chunk_size` to an `INT64` between "
                                f"`{_CHUNK_SIZE_MIN}` and `{_CHUNK_SIZE_MAX}` "
                                "(default `1000`)."
                            ),
                        )
                    )
                    break

        if (
            "AI.EVALUATE" not in detected
            and "AI.DETECT_ANOMALIES" not in detected
            and _STATUS_IS_NULL_RE.search(masked) is not None
            and _CHUNK_INTENTIONAL_STATUS_RE.search(masked) is None
        ):
            findings.append(
                ReviewFinding(
                    severity="WARNING",
                    rule="AI_CHUNK_DOCUMENT_STATUS_FILTER",
                    message=(
                        "`AI.CHUNK_DOCUMENT` emits `status = ''` on valid chunks "
                        "and `status IS NULL` on missing GCS URIs."
                    ),
                    remediation=(
                        "Filter valid `AI.CHUNK_DOCUMENT` rows with `WHERE status = ''` "
                        "(and error/missing rows with `WHERE status IS NULL OR status != ''`)."
                    ),
                )
            )

    if "AI.PREDICT" in detected:
        findings.append(
            ReviewFinding(
                severity="INFO",
                rule="AI_PREDICT_RESERVATION_REMINDER",
                message=(
                    "`AI.PREDICT` (TabFM, Preview) moves to token-based pricing "
                    "effective 2026-11-17 ($0.05/1M input tokens, $0.20/1M output "
                    "tokens; note syntax docs still list stale 10/30/2026) and hits "
                    "~8,000-row on-demand memory limits."
                ),
                remediation=(
                    "Materialize `AI.PREDICT` outputs once rather than re-running, "
                    "keep training context <= ~8,000 rows (<= 50 features, <= 10 "
                    "classes) on on-demand compute, and size context rows for token "
                    "billing starting 2026-11-17."
                ),
            )
        )

    return SqlReviewResult(
        sql=cleaned,
        detected_symbols=detected,
        prerequisites=prerequisites,
        findings=findings,
    )


def review(
    sql: str,
    *,
    skills_dir: Path | None = None,
) -> dict[str, object]:
    """Statically review a BigQuery SQL query and return a JSON-serializable dict."""
    return review_sql(sql=sql, skills_dir=skills_dir).to_dict()
