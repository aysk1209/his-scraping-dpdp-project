# Recorded AI-agent decisions (field names and manifest choices only; no personal data). Written by scripts/record_ai_agents.py.

One file per provider × model × briefing: `<provider>--<model>--<briefing>.json`. Each file's `sampling` field
says how its samples were drawn.

Every model is recorded to the same depth: three briefings (`unaided`, `informed`, `policy`) × 8 tasks × 5 samples.

- `gemini--gemini-3.1-flash-lite--*`: the Gemini API, free tier (recorded 2026-09-18).
- `claude-code--claude-haiku-4-5--*`, `claude-code--claude-sonnet-5-5--*`, `claude-code--claude-opus-5-5--*`: Claude
  through the Claude Code CLI on a subscription sign-in (`--provider claude-code`; no API key), recorded
  2026-10-05/06. Each call ran headless from an empty directory, with our brief as the whole system prompt, no
  tools, no MCP servers, no skills, and effort pinned to `high`. Sonnet 5.5 replaced Sonnet 5 (whose partial
  recordings, 1–3 samples per task, were deleted); Haiku's earlier samples were kept and extended, being
  recorded under the same brief.
