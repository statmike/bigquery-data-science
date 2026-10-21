"""BigQuery Data Science Agent Skills, CLI, and MCP Server."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("bigquery-data-science")
except PackageNotFoundError:
    __version__ = "0.9.0"

from bigquery_data_science.adk import get_bigquery_tools
from bigquery_data_science.catalog import (
    LookupResult,
    ReviewFinding,
    SearchHit,
    SqlReviewResult,
    TriageResult,
    get_walkthrough,
    lookup,
    lookup_symbol,
    review,
    review_sql,
    search,
    search_catalog,
    triage,
    triage_task,
)
from bigquery_data_science.installer import (
    available_skills,
    bundled_skills_root,
    discover_federated_skill_dirs,
    get_skill_path,
    get_skills_dir,
    install_kernel,
    install_mcp_config,
    install_skills,
    list_bundled_skills,
)

list_skills = list_bundled_skills

__all__ = [
    "LookupResult",
    "ReviewFinding",
    "SearchHit",
    "SqlReviewResult",
    "TriageResult",
    "__version__",
    "available_skills",
    "bundled_skills_root",
    "discover_federated_skill_dirs",
    "get_bigquery_tools",
    "get_skill_path",
    "get_skills_dir",
    "get_walkthrough",
    "install_kernel",
    "install_mcp_config",
    "install_skills",
    "list_bundled_skills",
    "list_skills",
    "lookup",
    "lookup_symbol",
    "review",
    "review_sql",
    "search",
    "search_catalog",
    "triage",
    "triage_task",
]
