---
name: capture-work-todos
description: Capture missing TODOs from recent work context. Use when Codex needs to scan the user's Slack DMs with their manager or direct reports, manager/direct-report 1:1 docs, and leadership meeting notes for direct asks or action items assigned to the user, deduplicate against the user's configured todo app, and create missing tasks with source links and searchable metadata.
---

# Capture Work Todos

## Overview

Create TODOs for work asks that would otherwise fall through the cracks. Stay bounded to the last 14 days, preserve links to the source evidence, and add enough metadata to find these auto-created tasks later.

## Scope

- Use a maximum lookback window of 14 days. If the user asks for a longer period, cap it at 14 days unless they explicitly override this skill's default.
- Read `AGENTS.override.md` for the user's preferred TODO app and action-item owner aliases.
- Use `python3` for date calculations and local helper scripts.
- Read the active repo instructions first, then use these local index files:
  - `local/one-on-ones.md` for manager and direct-report 1:1 docs.
  - `local/meetings.md` for leadership meeting docs.
  - `local/slack-channels.md` for Slack DM links and leadership channels.
- Derive the relevant people from `AGENTS.override.md` and `local/one-on-ones.md`: direct manager plus direct reports. Re-read these files each run so changes in reporting relationships are picked up.

## Source Workflow

1. Calculate the start date:

```bash
python3 - <<'PY'
from datetime import date, timedelta
print((date.today() - timedelta(days=14)).isoformat())
PY
```

2. Gather Slack DMs:
   - Prefer the Codex Slack plugin for reads and searches.
   - Search the user's DMs with their manager and direct reports after the start date.
   - Preserve message permalinks, sender, timestamp, and enough nearby context to decide whether the ask is still open.
   - Include only direct asks to the user or commitments by the user that imply follow-up.

3. Gather 1:1 docs:
   - Use Atlassian Rovo MCP first for Confluence pages.
   - Use Dropbox MCP `paper_read_document` first for Dropbox Paper docs.
   - Fall back according to the local `confluence` and `dropbox` skills only when the preferred connector is unavailable or unsuitable.
   - Read only recent dated sections in the lookback window, plus unresolved older follow-ups explicitly carried forward into those sections.
   - Include the manager 1:1 and direct-report 1:1 docs. Do not include skip-level, peer, or collaborator docs unless the user asks.

4. Gather leadership meetings:
   - Use `local/meetings.md` and include docs whose title or description clearly marks them as leadership forums, such as engineering leadership team notes, LT/XLT vibe checks, manager staff meetings, and leader-plus-manager forums.
   - Use the same Confluence/Paper precedence as 1:1 docs.
   - If docs cannot be read, inspect recent leadership-meeting summaries in `memory/miclog.txt`, `memory/other_meetings_notes.txt`, or `local/miclog-summaries.md` only for entries inside the lookback window.
   - Skip project status docs and broad all-hands style docs unless they contain an explicit action assigned to the user.

## Extraction Rules

Create a TODO candidate only when there is concrete evidence that the user owns the next action.

Strong signals:

- Explicit owners: the user's name, email handle, or action-item owner aliases from `AGENTS.override.md`, such as `owner: <user>`, `AI: <user>`, `[ ] <user>`, or `<user> to ...`.
- Direct DM asks: "can you", "could you", "please", "do you mind", "will you", "can we get you to", or equivalent language from the manager or a direct report.
- User commitments: "I'll", "I will", "I can", "let me", "I'll follow up", when the commitment appears unresolved.
- Meeting/doc action items assigned to the user, or clear follow-ups from manager/direct-report 1:1 notes where the user is the actor.

Skip:

- Tasks assigned to the manager, a direct report, or the whole group unless the user has an explicit follow-up role.
- FYIs, status updates, kudos, brainstorming, or decisions with no next action.
- Items marked done, closed, resolved, shipped, or superseded.
- Vague "we should" ideas unless paired with a named user action.
- Existing TODOs already present in the configured TODO app.

Use concise, imperative task titles. Prefer "Send rollout risk summary to manager" over "Follow up on Slack thread".

## Deduplication

Before creating anything, inspect the configured TODO app using the appropriate subsection under `Todo Apps`.

Treat a candidate as already captured if an active, inbox, or recently completed task has:

- The same source URL in the note.
- The same normalized title.
- A title that clearly covers the same ask, even if phrased differently.

When uncertain, do not create a near-duplicate. Report the ambiguity in the final summary.

## Todo Apps

Read `AGENTS.override.md` to determine the user's preferred TODO app. Use the matching subsection below.

TODO: Document additional TODO apps here as they become supported.

### OmniFocus

Use this subsection when `AGENTS.override.md` says the preferred TODO app is OmniFocus.

Before creating anything, inspect OmniFocus:

```bash
python3 -m sidekick.clients.omnifocus query --status active --limit 500
python3 -m sidekick.clients.omnifocus inbox --limit 500
python3 -m sidekick.clients.omnifocus query --status completed --limit 200
python3 -m sidekick.clients.omnifocus by-tag sidekick-auto-todo --limit 500
```

Use the bundled helper so tags are created if missing and source metadata is consistent:

```bash
python3 .agents/skills/capture-work-todos/scripts/add_omnifocus_todo.py \
  --title "Send rollout risk summary to manager" \
  --source-url "https://dropbox.enterprise.slack.com/archives/..." \
  --source-type slack-dm \
  --source-person "Manager Name" \
  --source-date 2026-05-29 \
  --evidence "The manager asked the user to send a concise risk summary before the leadership discussion." \
  --tag manager-ask \
  --tag source-slack
```

Use `--dry-run` before the first real create in a run if the extracted candidate list is large or uncertain.

Default metadata:

- Tags always include `sidekick-auto-todo` and `capture-work-todos`.
- Add source tags such as `source-slack`, `source-oneonone`, and `source-leadership-meeting`.
- Add relationship tags such as `manager-ask`, `direct-report-ask`, or `leadership-ask` when applicable.
- Notes include `skill`, `source_type`, `source_person`, `source_date`, `source_url`, `captured_at`, and the evidence excerpt/summary.

## Final Output

Report:

- Date window scanned.
- Sources attempted and sources that failed.
- TODOs created, with task IDs or app-specific identifiers and source links.
- Candidates skipped because they already existed.
- Ambiguous candidates not created and why.

Keep the final summary concise and do not paste long source excerpts.
