---
name: kudos
description: Generate kudos for team members from recent 1:1 and meeting notes
argument-hint: [weeks]
allowed-tools: Bash, Read, Grep
---

# Kudos Skill

Generate kudos for team members from recent 1:1 and meeting notes, with proper Slack formatting.

## Overview

This skill helps you:
1. Review recent notes from all your 1:1 and recurring meeting docs
2. Extract kudos, wins, and accomplishments for specific people
3. Format kudos with real Slack user mentions (`<@U...>` ID format)
4. Include a concise Slack copy/paste version
5. Include references to source documents

## Prerequisites

- `@AGENTS.override.md` file with your 1:1 and meeting doc links
- Configured Dropbox MCP access for Paper and Atlassian Rovo MCP for Confluence/JIRA context
- `memory/people.json` file for person/email data and, when available, Slack user IDs

## Usage Pattern

When invoked with: `/kudos [weeks]`

### Step 1: Create Temporary Directory

```bash
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/kudos.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
```

### Step 2: Fetch Recent Content

For each 1:1 document in `@AGENTS.override.md`, fetch the content
Use Atlassian Rovo MCP for Confluence docs and Dropbox MCP (`dropbox-mcp`) `paper_read_document` for Paper docs. For Paper docs, fall back to the Chrome plugin/live Paper view second when Dropbox MCP is unavailable or lacks the needed operation. Use `/dropbox` or `sidekick.clients.dropbox` only as a final fallback when Chrome is unavailable or unsuitable, `DROPBOX_ACCESS_TOKEN` is set, debugging the local client, running standalone workflows, or the user explicitly asks for the local client.
Also look in recent Slack channels and DMs
Keep track of docs that error out to report at the end

### Step 3: Review and Extract Kudos

Look for recent mentions of:
- Accomplishments and wins
- Project launches and completions
- Promotions and performance ratings
- Going above and beyond
- Specific impact attributable to individuals

**Important:** Only extract kudos from recent date headers (within target time period).

### Step 4: Format Kudos with Slack Mentions

For each kudos item:
1. Identify the person(s) involved
2. Resolve each person to a Slack user ID:
   - Prefer an existing Slack mention found in source context, such as `<@U041F9YQ64Q>`.
   - If the Slack connector is available, use Slack user search/profile lookup by name or email and capture the `U...` user ID.
   - If local data has a Slack user ID, use that.
   - If only an email is available and no Slack ID can be resolved, use plain non-notifying text such as `alice@example.com` or `Alice Smith`; do not pretend it will notify.
3. Format kudos with:
   - Clear description of accomplishment
   - Context and impact
   - Raw Slack mention tokens for all resolved people involved
   - Reference link to source doc

**Slack Mention Format:**
- Correct notifying mention: `<@U041F9YQ64Q>`
- Incorrect: `` `<@U041F9YQ64Q>` `` because inline code prevents Slack from rendering the mention.
- Incorrect: `@alice` or `@bob.smith` because email-prefix usernames are not reliable notifying mentions.
- Never wrap Slack mention tokens in backticks, code fences, quotes, or escaped angle brackets in Slack-ready text.
- If sending or editing the report in Slack, preserve raw `<@U...>` tokens in every message chunk.

### Step 5: Generate Output

Create a markdown file with Slack-ready sections and a concise Slack copy/paste version near the top.

The Slack copy/paste version should:
- Use plain bullets only; do not use a code block.
- Start every bullet with `:raised_hands:`.
- Include raw Slack mention tokens for each resolved person at the start of the bullet, such as `<@U123ABC>`.
- Keep each bullet self-contained and specific enough to paste directly into Slack.
- Avoid source links in the bullets unless the link is essential; keep source links in the categorized report below.
- Use plain non-notifying text for any person whose Slack ID could not be resolved.

Example Slack copy/paste section:

```markdown
## Slack copy/paste version

:raised_hands: <@U123ABC> for driving the launch from ambiguous requirements to a concrete rollout plan, including the dashboard and go/no-go checklist that made the decision easy.

:raised_hands: <@U456DEF> and <@U789GHI> for quickly debugging the regression, ramping the experiment down, and adding instrumentation so the team can separate product impact from telemetry noise.
```

Also include a categorized report with source links. The example below is documentation only; do not wrap generated report text in a code block when sending to Slack.

```markdown
## Kudos - [Date Range]

### [Category/Project Name]
[Description with impact and context]

**People:** <@U123ABC>, <@U456DEF>, <@U789GHI>

[[ref]](source-doc-url)

This report generated using [chase-sidekick](https://github.com/chase-seibert/chase-sidekick) and the [kudos skill](https://github.com/chase-seibert/chase-sidekick/tree/main/.agents/skills/kudos).

---
```

**Categories might include:**
- Performance & Promotions
- Project Launches
- Technical Excellence
- Cross-team Collaboration
- Going Above and Beyond

### Step 6: Report Errors

Print a list of documents that errored during retrieval.

## Tips

- **Default Time Period**: Last 7 days, adjust based on argument
- **Be Specific**: Include concrete details about what was accomplished
- **Show Impact**: Explain why it matters, not just what was done
- **Group Related**: Combine related kudos for the same project/initiative
- **Verify Mentions**: Double-check every Slack-ready mention is a raw `<@U...>` token and not inline code
- **Include Context**: Help readers understand the significance

## Common Use Cases

- Weekly team shoutouts
- Post-launch celebrations
- Performance cycle recognitions
- Quarterly team updates
- Manager upward feedback preparation
