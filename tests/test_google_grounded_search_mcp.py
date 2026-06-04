from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
import unittest
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def load_mcp():
    spec = importlib.util.spec_from_file_location(
        "_test_google_grounded_search_mcp",
        PLUGIN_ROOT / "scripts" / "google_grounded_search_mcp.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GoogleGroundedSearchMcpTests(unittest.TestCase):
    def test_prompt_forces_native_google_grounding(self):
        mcp = load_mcp()

        prompt = mcp.build_grounded_prompt(
            {"query": "최신 Gemini 소식", "freshness": "today", "max_sources": 2, "language": "ko"}
        )

        self.assertIn("native Google Search grounding", prompt)
        self.assertIn("Do not use DuckDuckGo", prompt)
        self.assertIn("Question: 최신 Gemini 소식", prompt)

    def test_grounded_env_forces_hermes_antigravity_grounding(self):
        mcp = load_mcp()

        env = mcp.grounded_env()

        self.assertEqual(env["HERMES_GOOGLE_GROUNDING_SEARCH_ENABLED"], "true")
        self.assertEqual(env["HERMES_ANTIGRAVITY_GOOGLE_GROUNDING"], "always")
        self.assertEqual(env["HERMES_ANTIGRAVITY_GROUNDING_SUPPRESS_EXTERNAL_SEARCH_TOOLS"], "true")
        self.assertEqual(env["HERMES_ANTIGRAVITY_GROUNDING_SUPPRESS_FUNCTION_TOOLS"], "true")

    def test_tools_call_invokes_hermes_chat(self):
        mcp = load_mcp()
        completed = subprocess.CompletedProcess(
            args=["hermes"],
            returncode=0,
            stdout="Answer with https://example.com\nSession: hidden\n",
            stderr="",
        )

        with mock.patch.object(mcp, "hermes_binary", return_value="/usr/local/bin/hermes"):
            with mock.patch.object(mcp.subprocess, "run", return_value=completed) as run_mock:
                response = mcp.handle_request(
                    {
                        "jsonrpc": "2.0",
                        "id": 7,
                        "method": "tools/call",
                        "params": {
                            "name": "google_grounded_search",
                            "arguments": {"query": "latest Gemini news"},
                        },
                    }
                )

        self.assertEqual(response["id"], 7)
        self.assertIn("Answer with https://example.com", response["result"]["content"][0]["text"])
        command = run_mock.call_args.args[0]
        self.assertEqual(command[:5], ["/usr/local/bin/hermes", "chat", "--provider", "google-antigravity", "-m"])
        self.assertIn("gemini-3.5-flash-high", command)

    def test_auth_status_redacts_secret_like_output(self):
        mcp = load_mcp()
        completed = subprocess.CompletedProcess(
            args=["hermes"],
            returncode=0,
            stdout="google-antigravity: logged in\naccess_token=secret-value\n",
            stderr="",
        )

        with mock.patch.object(mcp, "hermes_binary", return_value="/usr/local/bin/hermes"):
            with mock.patch.object(mcp.subprocess, "run", return_value=completed):
                result = mcp.run_auth_status({})

        text = result["content"][0]["text"]
        self.assertIn("logged in", text)
        self.assertNotIn("secret-value", text)
        self.assertTrue(result["structuredContent"]["logged_in"])

    def test_clean_output_prefers_hermes_box_body(self):
        mcp = load_mcp()
        raw = "\n".join(
            [
                "Query: do this",
                "wrapped prompt line",
                "╭─ ⚕ Hermes ─╮",
                "│ Answer line │",
                "│ https://example.com │",
                "╰─────────────╯",
                "Resume this session with:",
                "  hermes --resume hidden",
            ]
        )

        cleaned = mcp.clean_output(raw)

        self.assertEqual(cleaned, "Answer line\nhttps://example.com")

    def test_evidence_extracts_sources_and_numeric_claims(self):
        mcp = load_mcp()
        answer = (
            "RTX Spark has 6,144 CUDA cores, up to 128GB memory, and ships in 2026년 가을. "
            "Source: https://nvidianews.nvidia.com/news/nvidia-microsoft-windows-pcs-agents-rtx-spark"
        )

        evidence = mcp.build_evidence(answer, resolve_sources=False)

        self.assertEqual(evidence["sources"][0]["source_type"], "official")
        self.assertIn("6,144 CUDA", evidence["numeric_claims"])
        self.assertIn("128GB", evidence["numeric_claims"])
        self.assertIn("2026년", evidence["numeric_claims"])
        self.assertEqual(evidence["official_source_count"], 1)

    def test_resolve_url_follows_vertex_redirect(self):
        mcp = load_mcp()

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def geturl(self):
                return "https://nvidianews.nvidia.com/news/example"

        with mock.patch.object(mcp.urllib.request.OpenerDirector, "open", return_value=Response()):
            source = mcp.resolve_url("https://vertexaisearch.cloud.google.com/grounding-api-redirect/example")

        self.assertTrue(source["redirect_resolved"])
        self.assertEqual(source["resolved_url"], "https://nvidianews.nvidia.com/news/example")
        self.assertEqual(source["source_type"], "official")

    def test_unresolved_vertex_url_is_not_treated_as_official_source(self):
        mcp = load_mcp()

        with mock.patch.object(mcp.urllib.request.OpenerDirector, "open", side_effect=TimeoutError("timeout")):
            source = mcp.resolve_url("https://vertexaisearch.cloud.google.com/grounding-api-redirect/example", timeout_sec=1)

        self.assertEqual(source["source_type"], "grounding_redirect")


if __name__ == "__main__":
    unittest.main()
