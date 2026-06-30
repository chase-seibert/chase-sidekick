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
- Codex plug-in / connector: Slack
- Codex plug-in: Atlassian Rovo

Diagnostic fallback for Slack:
- Dash MCP Slack connector

What to do
0. Pick ONE representative instance of each file type. They may be specified in `@AGENTS.override.md`.
1. Verify critical integration existence and authentication before content validation:
   - Confirm `dropbox-mcp` tools are available, then authenticate by calling `paper_read_document` on the representative Paper doc.
   - Confirm Slack plug-in / connector tools are available, then authenticate by reading or searching the representative Slack channel.
   - Confirm Atlassian Rovo plug-in tools are available, then authenticate by reading or searching the representative Confluence doc.
   - If `dropbox-mcp` or Atlassian Rovo is missing, unavailable, unauthenticated, expired, or returns an auth/permission error, stop and output an error message for that integration. Do not use a fallback to hide a critical integration failure.
   - If the Slack plug-in / connector is missing, unavailable, unauthenticated, expired, lacks the needed read operation, or returns an auth/permission error, report the primary Slack integration failure clearly, then try the Dash MCP Slack connector as the Slack content fallback. Do not present the Slack plug-in / connector as healthy when Dash is the path that worked.
2. Try the preferred access path for each source: Dropbox MCP (`dropbox-mcp`) `paper_read_document` for Paper, Atlassian Rovo for Confluence, and the Codex Slack plug-in / connector for Slack.
3. Read the contents.
4. For Paper/Confluence docs: read just the top ~500 lines. For Slack: read messages from last 10 days using Slack search/read parameters or Slack date filters such as `after:YYYY-MM-DD`; calculate the cutoff with `date -v-10d`.
5. Convert to Markdown. For Slack, use the Slack plug-in / connector's Markdown-style message output when available.
6. Use `/dropbox`, `sidekick.clients.dropbox`, `/confluence`, `/jira`, `/slack`, Dash MCP, or Sidekick clients only as diagnostic fallbacks after the required critical integration checks have already passed or after you have reported the primary integration failure. For Slack specifically, prefer Dash MCP before `/slack` or Sidekick clients when the Codex Slack plug-in / connector is not working.
7. When using Dash MCP for Slack, call `dash_get_sources`, find the `slack` connection with `connection_status: connected`, verify `supports_actions: true`, then use Slack search actions such as `slack_search_messages` and, when needed, `slack_get_conversation_context`. Preserve the fact that this was a fallback in the output.

What to output
- A checkbox or stop sign emoji for each critical integration: `dropbox-mcp`, Slack plug-in / connector, and Atlassian Rovo plug-in. Include whether the integration existed and whether auth succeeded.
- If Slack succeeded through Dash MCP after the primary Slack path failed, show the Slack plug-in / connector as failed and the Slack content type as successful via Dash MCP.
- A checkbox or stop sign emoji for whether you were ultimately successful by content type: Paper, Confluence, and Slack.
- A TL;DR of the Markdown to show that you did read it successfully.
- A short description of HOW you were able to successfully access each file, i.e. what MCP server, plug-in, or fallback you used and how you converted to Markdown.

What else to keep in mind
- Don't launch the Finder, i.e. "open" folders or files to show me intermediate tmp files
- Prefer the Codex Slack plug-in / connector for reading Slack channels efficiently; if it is unavailable or failing, use Dash MCP's Slack connector as the first Slack fallback. Use `/slack` only after Dash MCP is unavailable, insufficient, or local-client debugging is needed.
- Prefer Atlassian Rovo for Confluence and JIRA. Use `/confluence`, `/jira`, and Sidekick clients only as fallbacks or for raw Confluence storage HTML workflows.
- These docs are likely to be restricted, meaning that access is not open to everyone; likely locked down to myself and a small number of other folks
