---
name: lint-meetings
description: Lint upcoming Google Calendar meetings for required Zoom links, agenda docs, and date-specific agenda sections, with general table and email priority output formats.
---

# Lint Meetings

Use this skill when asked to audit, lint, check, or clean up meeting hygiene for calendar meetings. It checks real meetings for Zoom links, agenda docs, and date-specific agenda sections, then reports either a general table view or an email-ready priority view.

By default, lint tomorrow's calendar in the user's local timezone. If the user gives an explicit date or range, use that instead. Output the result in chat only unless the user asks for a report file.

## Definition

A real meeting is a non-canceled calendar event with more than one human attendee. Skip solo holds, focus time, PTO, holidays, reminders, and other events that have only the current user as an attendee.

A passing meeting has all of:

- A Zoom link in conference entry points, location, description, or attachments. Google Meet or another video link does not satisfy this requirement.
- An agenda doc link in the event description, location, or attachments.
- A section in the agenda doc for this specific meeting date instance, unless that instance starts a week or more after the lint run time.

When a meeting instance is a week or more away, a missing date-specific agenda section is acceptable. Treat the Next section result as not applicable, do not classify it as failing or ambiguous, do not ask the owner to add it, and do not create a section for it.

Classify a meeting as owned by the current user when Google Calendar marks the organizer or creator as self, or when the organizer or creator email matches the current user's email from local context or Calendar profile.

## Commands

Use `python3`:

```bash
python3 -m sidekick.clients.gcalendar list <time-min> <time-max> <max-results>
python3 -m sidekick.clients.gcalendar get <event-id>
```

Treat `python3 -m sidekick.clients.gcalendar get <event-id>` as the source of truth for Zoom detection. Some connector or flattened calendar payloads can omit `conferenceData` even when the raw Google Calendar event still contains valid Zoom `entryPoints`. Do not mark Zoom missing until the raw event payload has been checked.

Use Atlassian Rovo MCP first for Confluence links. Fall back to `sidekick.clients.confluence` only when Rovo is unavailable or raw storage HTML is required to verify a date section. Use Dropbox MCP (`dropbox-mcp`) `paper_read_document` first for Paper agenda docs by URL, file ID, or pad ID; fall back to the Chrome plugin/live Paper view second when Dropbox MCP is unavailable or lacks the needed operation; use `/dropbox` or `sidekick.clients.dropbox` only as a final fallback when Chrome is unavailable or unsuitable, `DROPBOX_ACCESS_TOKEN` is set, debugging the local client, running standalone workflows, or the user explicitly asks for the local client.

For Slack context, use the `/slack` skill. Do not send Slack messages or create Slack drafts as part of this skill. Only draft message text in the Codex response unless the user separately asks to send or draft in Slack.

## Workflow

1. Determine the date window.
   - Default to tomorrow from `00:00:00` through `23:59:59` in `America/Los_Angeles`.
   - For explicit dates, use the user's requested local date range.
   - Use RFC3339 timestamps with timezone offsets for Calendar commands.
2. List events for the window, then fetch full raw event details for candidate events with attendees.
   - Use the event list only to find candidates and basic metadata.
   - Before checking Zoom hygiene, hydrate each candidate with `python3 -m sidekick.clients.gcalendar get <event-id>` or an equivalent raw Calendar API read that preserves `conferenceData`.
3. Filter to real meetings.
   - Exclude canceled events.
   - Exclude events where the attendee list is empty or only the current user.
   - Treat resource calendars and rooms as non-human attendees when deciding whether the meeting has more than just the user.
4. For each real meeting, check required hygiene.
   - Zoom: find a `zoom.us` URL in raw-event video entry points first, then location, description, or attachments.
   - If a raw event has `conferenceData.entryPoints`, trust that over connector-specific flattened fields such as `hangoutLink` or abbreviated event summaries.
   - Agenda doc: find the first Confluence, Paper, or Dropbox document URL. If multiple plausible agenda docs exist, inspect the most agenda-like link first and report ambiguity if confidence is low.
   - Date section: if the meeting starts less than a week after the lint run time, inspect the linked agenda doc for an H1/H2 date heading, Confluence `<time datetime="YYYY-MM-DD">`, or a clearly labeled section matching the meeting's local date. If the meeting starts a week or more after the lint run time, skip this check and mark Next section as not applicable.
5. For owned meetings only, if a Confluence agenda doc exists, no date-specific section exists, and the meeting starts less than a week after the lint run time, use the `$confluence-meeting-notes-create-next` skill to attempt creating the next section. Report whether it created a section, stopped because one already existed, or refused because the doc shape was ambiguous.
6. For meetings owned by others, do not modify docs or calendar events. Draft a Codex-only Slack message asking the owner to update the missing items.
7. Choose the output format.
   - Use the general table view by default.
   - Use the email priority view when the user asks for email, email-ready, sendable, or priority-formatted output.
8. Output results in Markdown.

## Output Formats

### General Table View

Use this view by default. Group meetings by meetings owned by the current user and meetings owned by others.

Use emoji status cells. Do not include a separate status field. Use:

- ✅ present, passing, or owned by the current user
- ❌ missing or failing
- ⚠️ ambiguous, unreadable, or not confidently checked
- ➖ not applicable, including a missing date-specific section for a meeting a week or more away

Use this structure:

```markdown
# Meeting Lint

Checked: <date range>
Real meetings checked: <count>

## Meetings I Own

| Time | Meeting / Owner | Zoom | Doc | Next section |
| --- | --- | --- | --- | --- |
| <time> | <meeting title><br>✅ <name/email> | ✅ | ✅ | ✅ |

## Other Meetings

| Time | Meeting / Owner | Zoom | Doc | Next section |
| --- | --- | --- | --- | --- |
| <time> | <meeting title><br><owner name/email> | ✅ | ❌ | ❌ |

## Slack Message Drafts

### <meeting title> -> <owner>
Hi <owner>, could you update <meeting title> before <date/time> with <missing items>? Thanks!
```

If every meeting passes, keep the output short and still use the tables. The table cells should make the all-clear obvious without a separate status column.

### Email Priority View

Use this view when the user asks for an email-specific summary. Do not use tables. Do not include Slack message drafts unless the user separately asks for them. If sending the result by email, send it as rich text or HTML so headings render as headings and bullets render as real bullet lists; do not send raw Markdown markers like `#`, `##`, or `-`.

Separate the output into exactly three priority sections in this order: P0, P1, P2. Each section must be a bullet list. Use `None.` when a priority has no items. Each bullet should include the meeting time, meeting title, owner, missing or ambiguous items, and the requested action.

Assign each meeting to only the highest applicable priority. Do not assign a priority solely because a date-specific section is missing for a meeting a week or more away.

- P0: Owned meetings that still fail hygiene after any allowed Confluence section creation attempt, or any meeting missing a Zoom link or agenda doc.
- P1: Meetings less than a week away with a readable agenda doc but no date-specific section, or meetings owned by others that need owner follow-up for a non-P0 issue.
- P2: Ambiguous, unreadable, or low-confidence checks; informational cleanup; or all-clear notes if the user asked to include passing meetings.

Use emoji status markers in each bullet:

- ❌ for P0 missing or failing items
- ⚠️ for P1/P2 ambiguous, unreadable, or needs-confirmation items
- ✅ for passing or all-clear notes included at the user's request

Use this Markdown structure in chat:

```markdown
# Meeting Lint Email Summary

Checked: <date range>
Real meetings checked: <count>

## P0

- <time> — <meeting title> (<owner>): Missing <items>. <requested action>.

## P1

- <time> — <meeting title> (<owner>): Missing <items>. <requested action>.

## P2

- <time> — <meeting title> (<owner>): <warning or note>. <requested action if any>.
```

When sending by email, render the same content as HTML or rich text:

```html
<h1>Meeting Lint Email Summary</h1>
<p><strong>Checked:</strong> <date range><br>
<strong>Real meetings checked:</strong> <count></p>

<h2>P0</h2>
<ul>
  <li>❌ <strong><time></strong> — <meeting title> (<owner>): Missing <items>. <requested action>.</li>
</ul>
```

## Slack Draft Guidance

For meetings owned by someone else, write a short owner-facing draft in the response only. Be specific about what is missing:

```text
Hi <owner>, could you update <meeting title> before our <date> instance? I could not find <missing items>. Thanks!
```

If several meetings have the same owner, combine them into one concise draft with bullets.

Do not draft owner follow-up solely for a missing date-specific section when the meeting is a week or more away.

## Safety

- Do not change calendar events.
- Do not send Slack messages or create Slack drafts unless the user explicitly asks for that as a separate action.
- Do not update Paper or Dropbox docs.
- Only attempt remote doc writes through `$confluence-meeting-notes-create-next`, and only for meetings owned by the current user with a Confluence agenda doc.
- If the agenda doc cannot be read or the date section convention is ambiguous, report the uncertainty instead of guessing.

## Validation

Run this check after editing the skill:

```bash
python3 /Users/cseibert/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/lint-meetings
```
