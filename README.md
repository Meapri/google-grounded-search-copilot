# Google Grounded Search Copilot

Codex personal plugin that adds a Google-grounded search MCP tool backed by
Hermes Google Antigravity.

The plugin does not use a Google API key. Login, account selection, OAuth token
refresh, and token storage are delegated to the existing Hermes
`google-antigravity` provider:

```bash
hermes auth add google-antigravity
```

Search calls force Gemini native Google Search grounding through Hermes by
setting:

```text
HERMES_GOOGLE_GROUNDING_SEARCH_ENABLED=true
HERMES_ANTIGRAVITY_GOOGLE_GROUNDING=always
HERMES_ANTIGRAVITY_GROUNDING_SUPPRESS_EXTERNAL_SEARCH_TOOLS=true
HERMES_ANTIGRAVITY_GROUNDING_SUPPRESS_FUNCTION_TOOLS=true
```

That means the tool should not route through DuckDuckGo, Brave, Tavily, browser
search, or code-based scraping for the same facts.

## What Is Included

- `skills/google-grounded-search/SKILL.md`: routing guidance for Codex
- `.mcp.json`: plugin MCP server registration
- `scripts/google_grounded_search_mcp.py`: stdio MCP server exposing:
  - `google_grounded_search`
  - `google_antigravity_auth_status`

## Usage

Fresh Codex sessions with this plugin installed expose a `google_grounded_search`
MCP tool. Use it for current facts, latest news, source-backed answers, claim
verification, prices, schedules, official-source checks, and similar questions.

Typical tool arguments:

```json
{
  "query": "오늘 기준 Gemini 최신 소식 하나를 출처와 함께 요약해줘",
  "freshness": "today",
  "max_sources": 3,
  "language": "ko"
}
```

The tool returns the answer text plus structured metadata identifying:

- provider: `google-antigravity`
- grounding: `native_google_search`
- model used
- tool suppression policy
- `sources`: extracted source URLs with Google grounding redirects resolved to
  final URLs when possible
- `quality_signals`: source count, official-source count, unresolved redirect
  count, and whether any source was resolved
- `numeric_claims`: extracted numeric/spec/date claims for quick manual review

Codex should still review the result before answering the user.

For verification-heavy answers, prefer `structuredContent.sources[].resolved_url`
over the raw Vertex grounding redirect. Source types are classified as
`official`, `academic`, `community`, `media_or_web`, `grounding_redirect`, or
`unknown`.

## Local Smoke Test

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"google_antigravity_auth_status","arguments":{}}}' \
  | python3 scripts/google_grounded_search_mcp.py
```

Full grounded search smoke:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"google_grounded_search","arguments":{"query":"오늘 기준 Gemini 최신 소식 하나를 출처와 함께 요약해줘","freshness":"today","max_sources":2,"language":"ko"}}}' \
  | python3 scripts/google_grounded_search_mcp.py
```

## Configuration

Environment variables:

- `GOOGLE_GROUNDED_SEARCH_HERMES_BIN`: optional explicit path to `hermes`

The default model is `gemini-3.5-flash-high`; callers can override the `model`
tool argument when needed.

## Security

Do not print or commit OAuth token files, cookies, client secrets, or raw auth
headers. The MCP server redacts common secret patterns from error messages and
auth status output, but callers should still avoid inspecting credential files.
