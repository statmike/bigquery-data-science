"""Zero-dependency stdio MCP server exposing the 4-Lens BigQuery Data Science catalog.

Implements the Model Context Protocol (JSON-RPC 2.0 over stdio, supporting both
newline-delimited JSON and `Content-Length` framed messages) with four tools:

- ``triage_bigquery_task``: route a task across ``bigquery-ml`` and ``bigquery-ai``
- ``lookup_bigquery_syntax``: look up syntax cards, prerequisites, and gotchas
- ``search_bigquery_gotchas``: search empirical gotchas and reference documentation
- ``get_bigquery_walkthrough``: retrieve a full worked walkthrough from ``narrative/*.md``
"""

from __future__ import annotations

import json
import sys
from typing import Any, BinaryIO

from bigquery_data_science import __version__
from bigquery_data_science.catalog import (
    get_walkthrough,
    lookup_symbol,
    search_catalog,
    triage_task,
)

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
)


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
                "capabilities": {"tools": {}},
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
