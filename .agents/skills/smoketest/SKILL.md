---
name: smoketest
description: Check that core Sidekick integrations can authenticate and read common restricted files
auto-approve: true
---

You are an agent that checks whether Codex can authenticate with critical integrations and read the contents of these:
- Paper docs by URL
- Confluence docs by URL
- Slack channels

Critical integrations to verify:
- MCP server: `dropbox-mcp`
- Codex plug-in: Slack
- Codex plug-in: Atlassian Rovo

What to do
0. Pick ONE representative instance of each file type. They may be specified in `@AGENTS.override.md`.
1. Verify critical integration existence and authentication before content validation:
   - Confirm `dropbox-mcp` tools are available, then authenticate by calling `paper_read_document` on the representative Paper doc.
   - Confirm Slack plug-in tools are available, then authenticate by reading or searching the representative Slack channel.
   - Confirm Atlassian Rovo plug-in tools are available, then authenticate by reading or searching the representative Confluence doc.
   - If any critical integration is missing, unavailable, unauthenticated, expired, or returns an auth/permission error, stop and output an error message for that integration. Do not use a fallback to hide a critical integration failure.
2. Try the preferred access path for each source: Dropbox MCP (`dropbox-mcp`) `paper_read_document` for Paper, Atlassian Rovo for Confluence, and the Codex Slack plug-in for Slack.
3. Read the contents.
4. For Paper/Confluence docs: read just the top ~500 lines. For Slack: read messages from last 10 days using Slack search/read parameters or Slack date filters such as `after:YYYY-MM-DD`; calculate the cutoff with `date -v-10d`.
5. Convert to Markdown. For Slack, use the Slack plug-in's Markdown-style message output when available.
6. Use `/dropbox`, `sidekick.clients.dropbox`, `/confluence`, `/jira`, `/slack`, Dash MCP, or Sidekick clients only as diagnostic fallbacks after the required critical integration checks have already passed or after you have reported the primary integration failure.

What to output
- A checkbox or stop sign emoji for each critical integration: `dropbox-mcp`, Slack plug-in, and Atlassian Rovo plug-in. Include whether the integration existed and whether auth succeeded.
- A checkbox or stop sign emoji for whether you were ultimately successful by content type: Paper, Confluence, and Slack.
- A TL;DR of the Markdown to show that you did read it successfully.
- A short description of HOW you were able to successfully access each file, i.e. what MCP server, plug-in, or fallback you used and how you converted to Markdown.

What else to keep in mind
- Don't launch the Finder, i.e. "open" folders or files to show me intermediate tmp files
- Prefer the Codex Slack plug-in for reading Slack channels efficiently; use `/slack` only as a fallback or for local-client debugging.
- Prefer Atlassian Rovo for Confluence and JIRA. Use `/confluence`, `/jira`, and Sidekick clients only as fallbacks or for raw Confluence storage HTML workflows.
- These docs are likely to be restricted, meaning that access is not open to everyone; likely locked down to myself and a small number of other folks
