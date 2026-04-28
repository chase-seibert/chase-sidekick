---
name: meeting-attendance-audit
description: Audit Google Calendar recurring meetings by recent attendee RSVP history, recommend attendees to remove, write reports under memory, and guide approved attendee removals one meeting at a time.
---

# Meeting Attendance Audit

Use this skill when asked to audit recurring Google Calendar meetings for attendees who repeatedly decline or do not respond, suggest removals, write the audit report to memory, and apply approved removals. The Markdown report is the only durable state for the workflow.

## Workflow

1. Run the audit and capture the JSON output:

```bash
python3 -m sidekick.clients.gcalendar attendance-audit audit
```

2. Write the Markdown report yourself under `memory/meeting-attendance-audit/meeting-attendance-audit-YYYYMMDD-HHMM.md`. The report is the only durable workflow state. Include:
   - YAML frontmatter with prompt, client `gcalendar`, command `attendance-audit audit`, created, and updated.
   - `## Summary` from the JSON `summary` and `settings`.
   - `## Actual Changes` with `- No calendar changes have been applied yet.`
   - `## Meetings Reviewed` as a simple bullet list from `meetings_reviewed`.
   - `## Recommended Removals`, grouped by owner with meetings owned by the current user first, using `recommended_removals`.

3. Tell the user the relative report path. The report contains only meetings with recommendations in `## Recommended Removals`, while `## Meetings Reviewed` lists all recurring meetings that were inspected.

4. Read the Markdown report directly. Prompt for one meeting at a time from the `## Recommended Removals` section. Present the meeting title, owner, next occurrence, actionability, and `Suggested removal emails`. Offer these responses:
   - `yes` removes all suggested attendees for that meeting.
   - `skip` records that the meeting was skipped in the report's `## Actual Changes` section.
   - `done` stops the approval loop.
   - `prompt: ...` lets the user alter the removal set, for example `prompt: yes, but don't remove person@example.com`.

5. For `yes`, remove all suggested attendees for that meeting and capture the JSON output:

```bash
python3 -m sidekick.clients.gcalendar remove-attendees --event-id <series-id> --calendar-id <calendar-id> --emails <email1,email2> --future-start <next-occurrence>
```

6. After `remove-attendees`, edit the report's `## Actual Changes` section yourself. Replace `- No calendar changes have been applied yet.` with an actual-change bullet. Use the JSON fields:
   - If `status` is `success` and `scope` is `future-instances`: `- Removed <removed_emails> from <updated_instances> future instances of <summary>.`
   - If `status` is `success` and `scope` is `whole-series`: `- Removed <removed_emails> from the whole <summary> series.`
   - If `status` is `noop`: `- No change for <summary>; no requested attendees were removable.`

7. For `skip`, edit the report's `## Actual Changes` section and add a bullet: `- Skipped <meeting title>.`

8. For `prompt: ...`, parse the user's instruction conservatively. If they say not to remove one or more people, remove those emails from the suggested set and run `remove-attendees` with the remaining emails. If the instruction is ambiguous, ask a clarifying question before changing Calendar.

9. When the user says `done`, or after all recommended meetings have been handled, read the report's `## Actual Changes` section and output those bullets to the chat.

## Defaults

- Use Google Calendar only. Do not use Zoom, Google Meet, or inferred attendance data.
- Find upcoming unique recurring meetings first, then query prior instances for each recurring meeting.
- When Google Calendar has split a logical recurring meeting into multiple recurring masters, combine historical instances that share the same base event ID.
- Look back 180 days by default.
- Audit the last 4 completed instances per recurring meeting.
- Suggest attendees whose `declined` plus `needsAction` RSVP rate is at least 50 percent.
- Require at least 4 evaluated instances before suggesting a removal.
- Exclude the organizer, the current user, resource calendars, and attendees no longer present on the recurring master event.
- Apply removals to meetings owned by the current calendar user and to non-owned meetings only when Google Calendar says guests can modify the event.
- Include a meeting in the report only when there is at least one recommended attendee removal.
- Use `sendUpdates=all` for removals.
- Remove approved attendees from future instances of the series, starting at the report's `Next occurrence`. This patches future instances instead of changing past instances or splitting the recurrence into a second series.

## Validation

Run these checks after editing the skill:

```bash
python3 /Users/cseibert/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/meeting-attendance-audit
python3 -m sidekick.clients.gcalendar attendance-audit --help
python3 -m sidekick.clients.gcalendar remove-attendees --help
```
