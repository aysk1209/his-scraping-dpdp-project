# Recorded AI-agent decisions (field names and manifest choices only; no personal data). Written by scripts/record_ai_agents.py.

One file per provider × model × briefing: `<provider>--<model>--<briefing>.json`. Each file's `sampling` field
says how its samples were drawn.

- `gemini--gemini-3.1-flash-lite--*`: the Gemini API, free tier; three briefings × 8 tasks × 5 samples.
- `claude-code--claude-haiku-4-5--*`, `claude-code--claude-sonnet-5--*`: Claude through the Claude Code CLI on a
  subscription sign-in (`--provider claude-code`; no API key). Each call ran headless from an empty directory,
  with our brief as the whole system prompt, no tools, no MCP servers, no skills, and effort pinned to `high`.
  Recorded to the minimum the tables need: `policy`, 2 samples per task (one to enter the tables, a second to
  measure whether the model repeats itself); `unaided`, 1 sample per task.
