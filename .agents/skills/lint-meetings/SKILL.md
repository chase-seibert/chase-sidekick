---
name: lint-meetings
description: Lint upcoming Google Calendar meetings for required Zoom links, agenda docs, and date-specific agenda sections, grouped by meetings owned by the user versus other owners.
---

# Lint Meetings

Use this skill when asked to audit, lint, check, or clean up meeting hygiene for calendar meetings. It checks real meetings for Zoom links, agenda docs, and date-specific agenda sections, then reports issues grouped by meetings owned by the current user and meetings owned by others.

By default, lint tomorrow's calendar in the user's local timezone. If the user gives an explicit date or range, use that instead. Output the result in chat only unless the user asks for a report file.

## Definition

A real meeting is a non-canceled calendar event with more than one human attendee. Skip solo holds, focus time, PTO, holidays, reminders, and other events that have only the current user as an attendee.

A passing meeting has all of:

- A Zoom link in conference entry points, location, description, or attachments. Google Meet or another video link does not satisfy this requirement.
- An agenda doc link in the event description, location, or attachments.
- A section in the agenda doc for this specific meeting date instance.

Classify a meeting as owned by the current user when Google Calendar marks the organizer or creator as self, or when the organizer or creator email matches the current user's email from local context or Calendar profile.

## Commands

Use `python3`:

```bash
python3 -m sidekick.clients.gcalendar list <time-min> <time-max> <max-results>
python3 -m sidekick.clients.gcalendar get <event-id>
python3 -m sidekick.clients.confluence get-page-from-link "<confluence-url>"
python3 -m sidekick.clients.confluence read-page <page-id>
python3 -m sidekick.clients.confluence read-page <page-id> --html
```

Prefer the Confluence client for Confluence links. Prefer Dash MCP for reading Paper or Dropbox docs by link.

For Slack context, use the `/slack` skill. Do not send Slack messages or create Slack drafts as part of this skill. Only draft message text in the Codex response unless the user separately asks to send or draft in Slack.

## Workflow

1. Determine the date window.
   - Default to tomorrow from `00:00:00` through `23:59:59` in `America/Los_Angeles`.
   - For explicit dates, use the user's requested local date range.
   - Use RFC3339 timestamps with timezone offsets for Calendar commands.
2. List events for the window, then fetch full details for candidate events with attendees.
3. Filter to real meetings.
   - Exclude canceled events.
   - Exclude events where the attendee list is empty or only the current user.
   - Treat resource calendars and rooms as non-human attendees when deciding whether the meeting has more than just the user.
4. For each real meeting, check required hygiene.
   - Zoom: find a `zoom.us` URL in video entry points, location, description, or attachments.
   - Agenda doc: find the first Confluence, Paper, or Dropbox document URL. If multiple plausible agenda docs exist, inspect the most agenda-like link first and report ambiguity if confidence is low.
   - Date section: inspect the linked agenda doc for an H1/H2 date heading, Confluence `<time datetime="YYYY-MM-DD">`, or a clearly labeled section matching the meeting's local date.
5. For owned meetings only, if a Confluence agenda doc exists but no date-specific section exists, use the `$confluence-meeting-notes-create-next` skill to attempt creating the next section. Report whether it created a section, stopped because one already existed, or refused because the doc shape was ambiguous.
6. For meetings owned by others, do not modify docs or calendar events. Draft a Codex-only Slack message asking the owner to update the missing items.
7. Output results in Markdown.

## Output Format

Use emoji status cells. Do not include a separate status field. Use:

- ✅ present, passing, or owned by the current user
- ❌ missing or failing
- ⚠️ ambiguous, unreadable, or not confidently checked
- ➖ not applicable

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

## Slack Draft Guidance

For meetings owned by someone else, write a short owner-facing draft in the response only. Be specific about what is missing:

```text
Hi <owner>, could you update <meeting title> before our <date> instance? I could not find <missing items>. Thanks!
```

If several meetings have the same owner, combine them into one concise draft with bullets.

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
