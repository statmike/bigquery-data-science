"""Zero-dependency stdio MCP server exposing the 4-Lens BigQuery Data Science catalog.

Implements the Model Context Protocol (JSON-RPC 2.0 over stdio, supporting both
newline-delimited JSON and `Content-Length` framed messages) with:

- **5 Tools**:
  - ``triage_bigquery_task``: route a task across ``bigquery-ml`` and ``bigquery-ai``
  - ``lookup_bigquery_syntax``: look up syntax cards, prerequisites, and gotchas
  - ``search_bigquery_gotchas``: search empirical gotchas and reference documentation
  - ``get_bigquery_walkthrough``: retrieve a full worked walkthrough from ``narrative/*.md``
  - ``review_bigquery_sql``: statically audit a SQL query for prerequisites and gotchas
- **Resources & URI Templates** (`bqds://skill/...`, `bqds://reference/...`,
  `bqds://syntax/...`, `bqds://narrative/...`)
- **Prompts** (`design_bigquery_pipeline`, `audit_bigquery_sql`, `compare_ml_vs_ai`,
  `prevent_feature_leakage`)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, BinaryIO

from bigquery_data_science import __version__
from bigquery_data_science.catalog import (
    get_walkthrough,
    lookup_symbol,
    review_sql,
    search_catalog,
    triage_task,
)
from bigquery_data_science.installer import SKILL_NAMES, get_skills_dir

MCP_SERVER_NAME = "bigquery-data-science"
SUPPORTED_PROTOCOL_VERSION = "2024-11-05"
DEFAULT_SEARCH_LIMIT = 10

TOOLS: tuple[dict[str, Any], ...] = (
    {
        "name": "triage_bigquery_task",
        "description": (
            "Arbitrate between BigQuery ML (CREATE MODEL / ML.*) and BigQuery AI "
            "(AI.* / remote models) for a data science task, returning empirical "
            "tradeoffs, prerequisites, and recommended next steps."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Natural-language task description "
                        "(e.g. 'forecast daily sales')."
                    ),
                },
                "task": {
                    "type": "string",
                    "description": "Alias for 'query'.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "lookup_bigquery_syntax",
        "description": (
            "Look up the Lens 3 syntax card (< 25 KB), prerequisites from "
            "namespace-matrix.md, empirical gotchas, and related walkthroughs "
            "for a BigQuery ML or BigQuery AI model type or SQL function."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": (
                        "SQL function or model_type name "
                        "(e.g. 'ARIMA_PLUS', 'AI.FORECAST', 'VECTOR_SEARCH')."
                    ),
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_bigquery_gotchas",
        "description": (
            "Search empirical gotchas, decision guides, syntax cards, and "
            "walkthroughs across the bundled BigQuery skills."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Keyword or phrase to search for "
                        "(e.g. 'reservation', 'xgboost_version')."
                    ),
                },
                "skill": {
                    "type": "string",
                    "description": (
                        "Optional skill filter ('bigquery-data-science', "
                        "'bigquery-ml', or 'bigquery-ai')."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 10).",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_bigquery_walkthrough",
        "description": (
            "Retrieve the complete Lens 4 narrative walkthrough markdown "
            "(with clickable GitHub provenance links to the source .ipynb and .sql) "
            "for a specific topic."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": (
                        "Walkthrough topic name (e.g. 'arima_plus', 'ai_forecast', "
                        "'feature_store', 'feature_store_workflow')."
                    ),
                },
            },
            "required": ["topic"],
            "additionalProperties": False,
        },
    },
    {
        "name": "review_bigquery_sql",
        "description": (
            "Statically audit a BigQuery ML or BigQuery AI SQL query for required "
            "connections, Enterprise reservations, unpinned foundation models, "
            "retired functions, and empirical gotchas."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "GoogleSQL query string to review.",
                },
            },
            "required": ["sql"],
            "additionalProperties": False,
        },
    },
)

RESOURCE_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "uriTemplate": "bqds://skill/{skill}",
        "name": "BigQuery Skill Router & Guardrails (Lens 1)",
        "description": (
            "Read SKILL.md for 'bigquery-data-science', 'bigquery-ml', or 'bigquery-ai'."
        ),
        "mimeType": "text/markdown",
    },
    {
        "uriTemplate": "bqds://reference/{skill}/{name}",
        "name": "BigQuery Domain Reference & Decision Guide (Lens 2)",
        "description": (
            "Read a domain reference markdown file (e.g. "
            "bqds://reference/bigquery-data-science/namespace-matrix)."
        ),
        "mimeType": "text/markdown",
    },
    {
        "uriTemplate": "bqds://syntax/{skill}/{slug}",
        "name": "BigQuery Surgical Syntax Card (Lens 3)",
        "description": (
            "Read a < 25 KB syntax card (e.g. bqds://syntax/bigquery-ai/aiforecast "
            "or bqds://syntax/bigquery-ml/arima-plus)."
        ),
        "mimeType": "text/markdown",
    },
    {
        "uriTemplate": "bqds://narrative/{skill}/{topic}",
        "name": "BigQuery Live-Verified Walkthrough Narrative (Lens 4)",
        "description": (
            "Read a complete notebook walkthrough (e.g. "
            "bqds://narrative/bigquery-ai/ai_agg)."
        ),
        "mimeType": "text/markdown",
    },
)

PROMPTS: tuple[dict[str, Any], ...] = (
    {
        "name": "design_bigquery_pipeline",
        "description": (
            "Design an end-to-end BigQuery ML or BigQuery AI SQL workflow for a "
            "business problem with pinned models and verified prerequisites."
        ),
        "arguments": [
            {
                "name": "goal",
                "description": "Business or data-science goal (e.g. 'forecast daily store sales').",
                "required": True,
            },
            {
                "name": "constraints",
                "description": "Optional table schema, latency, or governance constraints.",
                "required": False,
            },
        ],
    },
    {
        "name": "audit_bigquery_sql",
        "description": (
            "Audit a BigQuery ML or BigQuery AI SQL query for connections, "
            "reservations, unpinned endpoints, and empirical gotchas."
        ),
        "arguments": [
            {
                "name": "sql",
                "description": "BigQuery SQL query to audit.",
                "required": True,
            },
        ],
    },
    {
        "name": "compare_ml_vs_ai",
        "description": (
            "Compare trained BigQuery ML (CREATE MODEL) against zero-shot "
            "BigQuery AI (AI.*) for a specific modeling task."
        ),
        "arguments": [
            {
                "name": "task",
                "description": "Modeling task to compare (e.g. 'churn classification').",
                "required": True,
            },
        ],
    },
    {
        "name": "prevent_feature_leakage",
        "description": (
            "Design a point-in-time feature join using ML.ENTITY_FEATURES_AT_TIME "
            "and ML.FEATURES_AT_TIME without future label leakage."
        ),
        "arguments": [
            {
                "name": "entity_table",
                "description": "Optional entity/label table name.",
                "required": False,
            },
            {
                "name": "feature_table",
                "description": "Optional time-stamped feature table name.",
                "required": False,
            },
        ],
    },
)


def _list_resources(skills_dir: Path | None = None) -> list[dict[str, Any]]:
    """Return all Lens 1 (`skill`) and Lens 2 (`reference`) MCP resources."""
    root = skills_dir if skills_dir is not None else get_skills_dir()
    resources: list[dict[str, Any]] = []
    for skill_name in SKILL_NAMES:
        skill_dir = root / skill_name
        skill_md = skill_dir / "SKILL.md"
        if skill_md.is_file():
            resources.append(
                {
                    "uri": f"bqds://skill/{skill_name}",
                    "name": f"{skill_name} — SKILL.md (Lens 1 Router)",
                    "description": f"Lens 1 router and guardrails for {skill_name}.",
                    "mimeType": "text/markdown",
                }
            )
        ref_dir = skill_dir / "reference"
        if ref_dir.is_dir():
            for ref_path in sorted(ref_dir.glob("*.md")):
                resources.append(
                    {
                        "uri": f"bqds://reference/{skill_name}/{ref_path.stem}",
                        "name": f"{skill_name}/reference/{ref_path.name}",
                        "description": (
                            f"Lens 2 decision guide and reference for {skill_name} "
                            f"({ref_path.stem})."
                        ),
                        "mimeType": "text/markdown",
                    }
                )
    return resources


def _read_resource(uri: str, skills_dir: Path | None = None) -> str:
    """Resolve and read a `bqds://` resource URI."""
    root = (skills_dir if skills_dir is not None else get_skills_dir()).resolve()
    cleaned = uri.strip()
    if not cleaned.startswith("bqds://"):
        raise ValueError(
            f"Unsupported resource URI scheme in '{cleaned}' (expected 'bqds://')."
        )
    path_part = cleaned[len("bqds://") :].strip("/")
    parts = [p for p in path_part.split("/") if p]
    if any(p in ("..", ".") for p in parts) or len(parts) < 2:
        raise ValueError(f"Invalid resource URI '{cleaned}'.")

    lens = parts[0]
    if lens == "skill" and len(parts) == 2:
        skill_name = parts[1]
        target = (root / skill_name / "SKILL.md").resolve()
        if target.is_file() and root in target.parents:
            return target.read_text(encoding="utf-8")
        raise ValueError(f"Skill resource not found: '{cleaned}'.")

    if lens in ("reference", "syntax", "narrative"):
        if len(parts) == 3:
            skill_name, item_name = parts[1], parts[2]
            stem = item_name[:-3] if item_name.endswith(".md") else item_name
            target = (root / skill_name / lens / f"{stem}.md").resolve()
            if target.is_file() and root in target.parents:
                return target.read_text(encoding="utf-8")
        elif len(parts) == 2 and lens == "syntax":
            lookup_res = lookup_symbol(parts[1], skills_dir=root)
            if lookup_res.found:
                return lookup_res.format_text()
        elif len(parts) == 2 and lens == "narrative":
            wt = get_walkthrough(parts[1], skills_dir=root)
            if wt.get("found"):
                return str(wt["content"])
        raise ValueError(f"Resource not found: '{cleaned}'.")

    raise ValueError(f"Unknown resource lens '{lens}' in URI '{cleaned}'.")


def _get_prompt(
    name: str,
    arguments: dict[str, Any],
    skills_dir: Path | None = None,
) -> dict[str, Any]:
    """Build the MCP `prompts/get` payload for `name`."""
    root = skills_dir if skills_dir is not None else get_skills_dir()

    if name == "design_bigquery_pipeline":
        goal = str(arguments.get("goal") or "").strip()
        if not goal:
            raise ValueError("Prompt 'design_bigquery_pipeline' requires 'goal'.")
        constraints = str(arguments.get("constraints") or "").strip()
        triage = triage_task(goal, skills_dir=root).format_text()
        constraint_line = f"\nConstraints: {constraints}\n" if constraints else ""
        prompt_text = (
            f"Design a production-ready BigQuery data science solution for: {goal}\n"
            f"{constraint_line}\n"
            "Use the empirical triage guidance below to pick the right BigQuery ML "
            "or BigQuery AI surface, state required connections/reservations, and "
            "write complete GoogleSQL with pinned model endpoints:\n\n"
            f"{triage}"
        )
        return {
            "description": f"BigQuery pipeline design for: {goal}",
            "messages": [
                {
                    "role": "user",
                    "content": {"type": "text", "text": prompt_text},
                }
            ],
        }

    if name == "audit_bigquery_sql":
        sql = str(arguments.get("sql") or "").strip()
        if not sql:
            raise ValueError("Prompt 'audit_bigquery_sql' requires 'sql'.")
        report = review_sql(sql, skills_dir=root).format_text()
        prompt_text = (
            "Review the following BigQuery SQL query against our static analysis "
            "report, explain any prerequisites or gotchas, and provide a corrected "
            "query if any findings were raised:\n\n"
            f"```sql\n{sql}\n```\n\n"
            f"{report}"
        )
        return {
            "description": "Static BigQuery ML / AI SQL audit and remediation",
            "messages": [
                {
                    "role": "user",
                    "content": {"type": "text", "text": prompt_text},
                }
            ],
        }

    if name == "compare_ml_vs_ai":
        task = str(arguments.get("task") or "").strip()
        if not task:
            raise ValueError("Prompt 'compare_ml_vs_ai' requires 'task'.")
        triage = triage_task(task, skills_dir=root).format_text()
        prompt_text = (
            f"Compare a trained BigQuery ML (`CREATE MODEL`) approach against a "
            f"zero-training BigQuery AI (`AI.*`) approach for: {task}\n\n"
            "Summarize reproducibility, latency, scale limits, cost/reservations, "
            "and provide side-by-side SQL templates grounded in:\n\n"
            f"{triage}"
        )
        return {
            "description": f"BigQuery ML vs BigQuery AI comparison for: {task}",
            "messages": [
                {
                    "role": "user",
                    "content": {"type": "text", "text": prompt_text},
                }
            ],
        }

    if name == "prevent_feature_leakage":
        entity_table = str(arguments.get("entity_table") or "project.dataset.entities").strip()
        feature_table = str(arguments.get("feature_table") or "project.dataset.features").strip()
        card = lookup_symbol("ML.ENTITY_FEATURES_AT_TIME", skills_dir=root).format_text()
        prompt_text = (
            f"Write a leak-free point-in-time feature retrieval query joining "
            f"entity table `{entity_table}` with feature table `{feature_table}` "
            "using `ML.ENTITY_FEATURES_AT_TIME` (and explain when to set "
            "`ignore_feature_nulls => TRUE` vs `FALSE`):\n\n"
            f"{card}"
        )
        return {
            "description": "Point-in-time feature store join with ML.ENTITY_FEATURES_AT_TIME",
            "messages": [
                {
                    "role": "user",
                    "content": {"type": "text", "text": prompt_text},
                }
            ],
        }

    raise ValueError(f"Unknown prompt '{name}'.")


def _call_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Execute one MCP tool call and return the formatted text payload."""
    if tool_name == "triage_bigquery_task":
        raw_query = str(
            arguments.get("query") or arguments.get("task") or ""
        ).strip()
        if not raw_query:
            raise ValueError(
                "triage_bigquery_task requires a non-empty 'query' or 'task' string."
            )
        return triage_task(raw_query).format_text()

    if tool_name == "lookup_bigquery_syntax":
        symbol = str(arguments.get("symbol") or "").strip().strip("`").strip()
        if not symbol:
            raise ValueError(
                "lookup_bigquery_syntax requires a non-empty 'symbol' string."
            )
        result = lookup_symbol(symbol)
        if not result.found:
            raise ValueError(result.format_text())
        return result.format_text()

    if tool_name == "search_bigquery_gotchas":
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError(
                "search_bigquery_gotchas requires a non-empty 'query' string."
            )
        skill = arguments.get("skill")
        skill_filter = str(skill).strip() if skill else None
        limit_raw = arguments.get("limit")
        limit = (
            int(limit_raw)
            if isinstance(limit_raw, int)
            and not isinstance(limit_raw, bool)
            and limit_raw > 0
            else DEFAULT_SEARCH_LIMIT
        )
        hits = search_catalog(
            query=query,
            skill_filter=skill_filter,
            limit=limit,
        )
        if not hits:
            return f"No matches found for '{query}'."
        return "\n\n".join(hit.format_text() for hit in hits)

    if tool_name == "get_bigquery_walkthrough":
        topic = str(arguments.get("topic") or "").strip()
        if not topic:
            raise ValueError(
                "get_bigquery_walkthrough requires a non-empty 'topic' string."
            )
        wt = get_walkthrough(topic)
        if not wt.get("found"):
            raise ValueError(str(wt.get("content", f"Walkthrough '{topic}' not found.")))
        return str(wt["content"])

    if tool_name == "review_bigquery_sql":
        sql = str(arguments.get("sql") or "").strip()
        if not sql:
            raise ValueError(
                "review_bigquery_sql requires a non-empty 'sql' string."
            )
        return review_sql(sql).format_text()

    raise ValueError(f"Unknown tool '{tool_name}'.")


def handle_request(message: dict[str, Any]) -> dict[str, Any] | None:
    """Process a single JSON-RPC 2.0 request/notification and return a response dict."""
    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params") or {}

    if "id" not in message or msg_id is None:
        return None

    if method == "initialize":
        protocol_version = params.get("protocolVersion") or SUPPORTED_PROTOCOL_VERSION
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": protocol_version,
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                },
                "serverInfo": {
                    "name": MCP_SERVER_NAME,
                    "version": __version__,
                },
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        tool_name = str(params.get("name") or "")
        raw_args = params.get("arguments")
        args = raw_args if isinstance(raw_args, dict) else {}
        try:
            text = _call_tool(tool_name, args)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": text}],
                    "isError": False,
                },
            }
        except ValueError as exc:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            }

    if method == "resources/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"resources": _list_resources()},
        }

    if method == "resources/templates/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"resourceTemplates": RESOURCE_TEMPLATES},
        }

    if method == "resources/read":
        uri = str(params.get("uri") or "")
        try:
            content = _read_resource(uri)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "text/markdown",
                            "text": content,
                        }
                    ]
                },
            }
        except ValueError as exc:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32602, "message": str(exc)},
            }

    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"prompts": PROMPTS}}

    if method == "prompts/get":
        prompt_name = str(params.get("name") or "")
        raw_args = params.get("arguments")
        args = raw_args if isinstance(raw_args, dict) else {}
        try:
            prompt_payload = _get_prompt(prompt_name, args)
            return {"jsonrpc": "2.0", "id": msg_id, "result": prompt_payload}
        except ValueError as exc:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32602, "message": str(exc)},
            }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}",
        },
    }


handle_message = handle_request


def serve_stdio(
    stdin: BinaryIO | None = None,
    stdout: BinaryIO | None = None,
) -> int:
    """Run the stdio JSON-RPC loop supporting both line-delimited and Content-Length framing."""
    in_stream = stdin if stdin is not None else sys.stdin.buffer
    out_stream = stdout if stdout is not None else sys.stdout.buffer

    while True:
        raw_line = in_stream.readline()
        if not raw_line:
            break
        decoded_line = raw_line.decode("utf-8", errors="replace").strip()
        if not decoded_line:
            continue

        if decoded_line.lower().startswith("content-length:"):
            try:
                content_length = int(decoded_line.split(":", 1)[1].strip())
            except ValueError:
                continue
            # Consume remaining header lines up to the blank separator line
            while True:
                header_line = in_stream.readline()
                if not header_line or not header_line.strip():
                    break
            body_bytes = in_stream.read(content_length)
            if not body_bytes:
                break
            payload_str = body_bytes.decode("utf-8", errors="replace").strip()
        else:
            payload_str = decoded_line

        try:
            message = json.loads(payload_str)
        except json.JSONDecodeError as exc:
            err = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            out_stream.write((json.dumps(err) + "\n").encode("utf-8"))
            out_stream.flush()
            continue

        if not isinstance(message, dict):
            continue

        response = handle_request(message)
        if response is not None:
            out_stream.write((json.dumps(response) + "\n").encode("utf-8"))
            out_stream.flush()

    return 0
