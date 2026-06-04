#!/usr/bin/env python3
"""MCP stdio server for Google-grounded search through Hermes Antigravity."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List


SERVER_NAME = "google-grounded-search-copilot"
SERVER_VERSION = "0.1.0"
DEFAULT_MODEL = "gemini-3.5-flash-high"
DEFAULT_TIMEOUT_SEC = 180

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SECRET_RE = re.compile(
    r"(?i)(authorization|bearer|token|refresh_token|access_token|client_secret|cookie|api[_-]?key)"
    r"([:=]\s*)?[^\s]+"
)


SEARCH_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search or verification question to answer with Google grounding.",
        },
        "model": {
            "type": "string",
            "default": DEFAULT_MODEL,
            "description": "Hermes google-antigravity Gemini model.",
        },
        "max_sources": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "default": 5,
            "description": "Requested maximum number of source URLs in the answer.",
        },
        "freshness": {
            "type": "string",
            "enum": ["auto", "latest", "today", "week", "month", "official"],
            "default": "auto",
            "description": "Freshness emphasis for the grounded query.",
        },
        "language": {
            "type": "string",
            "default": "ko",
            "description": "Preferred response language, such as ko or en.",
        },
        "timeout_sec": {
            "type": "integer",
            "minimum": 20,
            "maximum": 600,
            "default": DEFAULT_TIMEOUT_SEC,
        },
    },
    "required": ["query"],
    "additionalProperties": False,
}


def redact(text: Any) -> str:
    return SECRET_RE.sub(lambda match: f"{match.group(1)}=REDACTED", str(text or ""))


def clean_output(text: str) -> str:
    cleaned = ANSI_RE.sub("", text or "")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    box_lines: List[str] = []
    in_box = False
    for raw_line in cleaned.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("╭"):
            in_box = True
            continue
        if stripped.startswith("╰"):
            in_box = False
            continue
        if in_box:
            if stripped.startswith("│"):
                stripped = stripped.strip("│").strip()
            if stripped:
                box_lines.append(stripped)
    if box_lines:
        return "\n".join(box_lines).strip()

    lines: List[str] = []
    skip_prefixes = (
        "Query:",
        "Initializing agent",
        "Resume this session with:",
        "Session:",
        "Duration:",
        "Messages:",
        "hermes --resume",
    )
    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("╭", "╰", "─", "│")):
            continue
        if any(line.startswith(prefix) for prefix in skip_prefixes):
            continue
        lines.append(raw_line.rstrip())
    return "\n".join(lines).strip()


def hermes_binary() -> str:
    configured = os.environ.get("GOOGLE_GROUNDED_SEARCH_HERMES_BIN", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if path.exists() and os.access(path, os.X_OK):
            return str(path)
        raise RuntimeError(f"Configured Hermes binary is not executable: {configured}")
    found = shutil.which("hermes")
    if not found:
        raise RuntimeError("Hermes CLI was not found. Install Hermes or set GOOGLE_GROUNDED_SEARCH_HERMES_BIN.")
    return found


def grounded_env() -> Dict[str, str]:
    env = os.environ.copy()
    env["HERMES_GOOGLE_GROUNDING_SEARCH_ENABLED"] = "true"
    env["HERMES_ANTIGRAVITY_GOOGLE_GROUNDING"] = "always"
    env["HERMES_ANTIGRAVITY_GROUNDING_SUPPRESS_EXTERNAL_SEARCH_TOOLS"] = "true"
    env["HERMES_ANTIGRAVITY_GROUNDING_SUPPRESS_FUNCTION_TOOLS"] = "true"
    env.setdefault("NO_COLOR", "1")
    return env


def build_grounded_prompt(arguments: Dict[str, Any]) -> str:
    query = str(arguments.get("query") or "").strip()
    if not query:
        raise ValueError("query is required")
    max_sources = int(arguments.get("max_sources") or 5)
    max_sources = max(1, min(max_sources, 10))
    freshness = str(arguments.get("freshness") or "auto").strip()
    language = str(arguments.get("language") or "ko").strip() or "ko"
    return (
        "Use native Google Search grounding for this request. Do not use DuckDuckGo, "
        "Brave, Tavily, browser search, or code-based scraping. Answer in "
        f"{language}. Freshness preference: {freshness}. Include up to {max_sources} "
        "source URLs when available, separate verified facts from inference, and say "
        "when grounding does not find enough evidence.\n\n"
        f"Question: {query}"
    )


def run_google_grounded_search(arguments: Dict[str, Any]) -> Dict[str, Any]:
    model = str(arguments.get("model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    timeout_sec = int(arguments.get("timeout_sec") or DEFAULT_TIMEOUT_SEC)
    prompt = build_grounded_prompt(arguments)
    command = [
        hermes_binary(),
        "chat",
        "--provider",
        "google-antigravity",
        "-m",
        model,
        "-q",
        prompt,
    ]
    proc = subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
        timeout=max(20, min(timeout_sec, 600)),
        env=grounded_env(),
    )
    stdout = clean_output(proc.stdout)
    stderr = redact(proc.stderr)
    if proc.returncode != 0:
        detail = stderr.strip() or stdout or f"exit code {proc.returncode}"
        raise RuntimeError(
            "Hermes google-antigravity grounded search failed. "
            "If auth is missing, run `hermes auth add google-antigravity`. "
            f"Details: {detail}"
        )
    return {
        "content": [{"type": "text", "text": stdout}],
        "structuredContent": {
            "answer": stdout,
            "provider": "google-antigravity",
            "model": model,
            "grounding": "native_google_search",
            "tool_policy": {
                "suppress_external_search_tools": True,
                "suppress_function_tools": True,
            },
            "stderr": stderr.strip(),
        },
        "isError": False,
    }


def run_auth_status(_: Dict[str, Any]) -> Dict[str, Any]:
    command = [hermes_binary(), "auth", "status", "google-antigravity"]
    proc = subprocess.run(command, check=False, text=True, capture_output=True, timeout=30)
    text = redact((proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else ""))
    ok = proc.returncode == 0 and "logged in" in text.lower()
    if not text.strip():
        text = "No auth status output."
    return {
        "content": [{"type": "text", "text": text.strip()}],
        "structuredContent": {
            "logged_in": ok,
            "provider": "google-antigravity",
            "login_command": "hermes auth add google-antigravity",
        },
        "isError": False,
    }


def tool_definitions() -> List[Dict[str, Any]]:
    return [
        {
            "name": "google_grounded_search",
            "description": (
                "Answer current, search, verification, or source-backed questions using "
                "Hermes google-antigravity with Gemini native Google Search grounding."
            ),
            "inputSchema": SEARCH_SCHEMA,
        },
        {
            "name": "google_antigravity_auth_status",
            "description": (
                "Check whether Hermes google-antigravity OAuth login is available. "
                "Never returns tokens or secrets."
            ),
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    ]


def handle_request(message: Dict[str, Any]) -> Dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None:
        return None
    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            }
        elif method == "tools/list":
            result = {"tools": tool_definitions()}
        elif method == "tools/call":
            params = message.get("params") or {}
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if not isinstance(arguments, dict):
                raise ValueError("tool arguments must be an object")
            if name == "google_grounded_search":
                result = run_google_grounded_search(arguments)
            elif name == "google_antigravity_auth_status":
                result = run_auth_status(arguments)
            else:
                raise ValueError(f"unknown tool: {name}")
        else:
            raise ValueError(f"unsupported method: {method}")
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32000, "message": redact(exc)},
        }


def serve() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}
        else:
            response = handle_request(message)
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(serve())
