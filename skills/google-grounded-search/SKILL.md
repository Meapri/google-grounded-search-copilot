---
name: google-grounded-search
description: "Use proactively for current facts, latest news, source-backed answers, verification, prices, schedules, official-source checks, or any request where Codex should prefer Google-grounded search over DuckDuckGo or generic web search. Uses Hermes google-antigravity OAuth and Gemini native Google Search grounding."
---

# Google Grounded Search

Use this skill when the user asks for current, source-backed, or verification-heavy information.

## When To Use

Use `google_grounded_search` for:

- latest or current information
- source URLs, citations, or official-source checks
- fact checking and claim verification
- prices, schedules, releases, versions, policies, or anything likely to change
- Korean requests that mention `검색`, `최신`, `출처`, `근거`, `확인`, or `팩트체크`

Do not use it for pure coding, local file work, stable background knowledge, or user requests that explicitly say not to search.

## Tool Preference

Prefer the `google_grounded_search` MCP tool from this plugin when available.
It delegates to Hermes `google-antigravity` and forces Gemini native Google
Search grounding with external web-search/function tools suppressed.

Use arguments like:

```json
{
  "query": "오늘 기준 Gemini 최신 소식 하나를 출처와 함께 요약해줘",
  "freshness": "today",
  "max_sources": 3,
  "language": "ko"
}
```

If the tool reports auth failure, tell the user that Hermes Google Antigravity
login is needed and run or suggest:

```bash
hermes auth add google-antigravity
```

Never print OAuth tokens, cookies, client secrets, or raw credential files.

## Answer Handling

Treat the tool output as source-backed search evidence, not as final prose that
must be copied verbatim. Codex remains responsible for:

- explaining uncertainty
- separating verified facts from inference
- avoiding overclaiming when sources are thin
- preserving the user's requested tone and format
- saying if Google grounding did not provide enough evidence

Prefer source URLs from the tool result over generic search snippets. If the
answer involves substantial spending, legal, medical, financial, or safety
stakes, be explicit about limits and encourage primary-source confirmation.
