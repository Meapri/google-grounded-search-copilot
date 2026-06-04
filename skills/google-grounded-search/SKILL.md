---
name: google-grounded-search
description: "Default-first search route for modern products, companies, models, hardware/software releases, current facts, latest news, source-backed answers, verification, prices, schedules, official-source checks, or any request where Codex should prefer Google-grounded search over DuckDuckGo or generic web search. Uses Hermes google-antigravity OAuth and Gemini native Google Search grounding."
---

# Google Grounded Search

Use this skill when the user asks for current, source-backed, or verification-heavy information.
When in doubt, use it before answering.

## When To Use

Use `google_grounded_search` for:

- latest or current information
- modern named products, chips, GPUs, phones, laptops, apps, services, companies,
  model names, release names, or newly announced technologies
- source URLs, citations, or official-source checks
- fact checking and claim verification
- prices, schedules, releases, versions, policies, or anything likely to change
- broad Korean prompts like `<product/company/model>에 대해 알려줘`, because the
  user usually expects current facts even when `최신` or `검색` is not explicit
- Korean requests that mention `검색`, `최신`, `출처`, `근거`, `확인`, or `팩트체크`

Do not use it for pure coding, local file work, stable background knowledge,
creative writing, personal preference questions, or user requests that
explicitly say not to search.

## Tool Preference

Prefer the `google_grounded_search` MCP tool from this plugin when available.
For any modern entity with a meaningful chance of recent changes, call the tool
first, then synthesize. Do not answer from memory first and search afterward.
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

When available, inspect `structuredContent.sources` before citing. Prefer
`resolved_url` over raw `vertexaisearch.cloud.google.com` redirects. Treat
`quality_signals.official_source_count` and `unresolved_redirect_count` as
verification hints, not absolute truth. Use `resolved_source_summary` for a
quick review pass, but cite the resolved URLs themselves. If
`quality_signals.needs_manual_source_check` is true, say that the sources are
thin or unresolved instead of presenting the answer as fully verified. For
numbers, dates, specs, prices, and release schedules, review `numeric_claims`
and verify the important ones against official or primary sources before
publishing. If `retry_attempted` is true, check whether the retry produced
better URLs before citing.
