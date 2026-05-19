---
name: pto-block
description: Block calendar for PTO, offsites, conferences, travel days, and other out-of-office periods while handling conflicting meetings
argument-hint: <start-date> <end-date> [reason] [--dry-run]
auto-approve: true
---

# Calendar Blocking Agent

Automates calendar management for PTO, offsites, conferences, travel days, and other out-of-office periods by:
- Creating calendar blocks for work hours (9am-5pm Pacific time)
- Declining conflicting meetings with explanations
- Removing personal habit/focus blocks
- Preserving important meetings, travel itineraries, and offsite anchor events

## Purpose

When you are unavailable for PTO, an offsite, conference, or travel day, manual calendar cleanup is tedious:
- Block every day individually
- Go through each meeting to decline
- Remember which meetings to preserve
- Avoid deleting useful travel and agenda events
- Clean up focus/habit blocks that no longer apply

This agent handles it systematically with optional dry-run preview.

## Usage

**Dry run (recommended first)**:
```
"Run pto-block agent for 2026-04-15 to 2026-04-20 for Vacation with --dry-run"
```

**Live execution**:
```
"Run pto-block agent for 2026-04-15 to 2026-04-20 for Vacation"
```

**Custom reason**:
```
"Run pto-block agent for 2026-05-01 to 2026-05-03 for Conference"
```

**Work offsite or travel day**:
```
"Run pto-block agent for 2026-06-01 to 2026-06-04 for Leadership Offsite with --dry-run"
"Run pto-block agent for 2026-06-04 to 2026-06-04 for Travel Day"
```

## Email Notifications

By default, this agent uses the `--no-notify` flag when declining meetings and deleting events. This means:
- ✅ **No email notifications** are sent to meeting organizers or attendees
- ✅ Your calendar shows you as declined, but people don't get notified
- ✅ Events are silently removed without alerting others

**Why no notifications?**
- Reduces email spam for colleagues during your absence
- Prevents dozens of "declined" emails flooding people's inboxes
- Your out-of-office auto-reply can handle meeting requests
- People can see your declined status when they check the calendar

**To send notifications instead:**
- Remove the `--no-notify` flag from the commands in Phase 5
- Meeting organizers will receive decline notifications with your message
- Attendees will be notified when events are deleted

## Workflow

### Phase 1: Parse & Validate Arguments

1. **Extract arguments from user request**:
   - `start_date`: YYYY-MM-DD format (required)
   - `end_date`: YYYY-MM-DD format (required)
   - `reason`: Text description (default: "PTO")
   - `--dry-run`: Flag to preview without executing

2. **Normalize absence type and labels**:
   - Treat requests containing "PTO", "vacation", "personal day", "sick", or "time off" as PTO/time-off.
   - Treat requests containing "offsite", "conference", "summit", "travel", "travel day", "business trip", or "onsite" as work travel/out-of-office.
   - For PTO/time-off, use block title `PTO - {reason}` unless the reason is exactly "PTO", then use `PTO`.
   - For work travel/out-of-office, use block title `OOO - {reason}`. Do not include "PTO" in these block titles.
   - Use decline message `Out of office - {reason}` for all absence types unless the user provides a custom message.

3. **Validate date range**:
   - Dates in YYYY-MM-DD format
   - Start date <= end date
   - Reasonable duration (warn if > 4 weeks)
   - At least 1 business day in range

4. **Generate business day list**:
   - Skip weekends (Saturday, Sunday)
   - Include only Mon-Fri
   - Store list for later block creation

5. **Load user context from @AGENTS.override.md**:
   - Get current user
   - Get current users's boss and their boss

### Phase 2: Query Calendar Events

1. **Determine timezone offset for the date range**:
   - April-October typically uses PDT (Pacific Daylight Time): `-07:00`
   - November-March typically uses PST (Pacific Standard Time): `-08:00`
   - Use Python to check DST for the specific dates:
     ```python
     from datetime import datetime
     import time
     dt = datetime.strptime("2026-04-15", "%Y-%m-%d")
     is_dst = time.localtime(dt.timestamp()).tm_isdst
     offset = "-07:00" if is_dst else "-08:00"
     ```

2. **Build date range query**:
   - Start: `{start_date}T00:00:00{offset}` (Pacific time with offset)
   - End: `{end_date}T23:59:59{offset}`
   - Max results: 250

3. **List all events in range**:
   ```bash
   python3 -m sidekick.clients.gcalendar list \
     "2026-04-15T00:00:00-07:00" \
     "2026-04-20T23:59:59-07:00" \
     250
   ```
   Note: Use the calculated offset (-07:00 for PDT or -08:00 for PST)

4. **Get full details for each event** (parallel):
   ```bash
   python3 -m sidekick.clients.gcalendar get <event_id>
   ```
   Extract from each event:
   - Event ID
   - Summary (title)
   - Start time
   - End time
   - All-day vs timed event
   - Attendees list
   - Organizer email
   - Description
   - Location

### Phase 3: Categorize Events

For each event, determine its category and action:

#### 1. All-Day Events -> KEEP AS-IS

**Detection**: Event has `start.date` instead of `start.dateTime`.

**Action**: Keep unchanged and include in the report as preserved all-day context.

#### 2. Existing Calendar Blocks -> KEEP OR RENAME

**Detection**: Event is a timed, no-attendee availability block that overlaps most of the target work-hours block and has a title like "PTO", "OOO", "Out of office", or the requested `reason`.

**Action**:
- If the title already matches `block_title`, keep it.
- If this is a non-PTO request and an existing block says "PTO", rename the block to `block_title`.
- If the event has attendees, is short like a flight, or is not clearly a personal availability block, do not rename it.

```bash
python3 -m sidekick.clients.gcalendar update <event_id> summary "{block_title}"
```

#### 3. Travel, Itinerary, and Offsite Anchor Events -> KEEP AS-IS

**Detection**: Summary, description, or location contains travel/offsite signals such as:
- Travel: "flight", "airline", "airport", "boarding", "departure", "arrival", "route:", "booking confirmation", "reservation", "itinerary", "trip:", "Navan", "hotel", "lodging", "rental car", "train", "Amtrak", "Uber", "Lyft"
- Route pattern: three-letter airport code to three-letter airport code, such as `OAK to LAX`
- Work event: "offsite", "conference", "summit", "retreat", "travel day", or the requested `reason` phrase when it appears in the event text

**Action**: Keep unchanged. Do not decline or delete these events, even if they overlap the calendar block or have attendees. Report them under "Travel/Offsite Events Kept".

**Example**: For a leadership offsite with flight events like "Flight WN 1234: OAK to LAX" and descriptions containing "Trip: Leadership Offsite", preserve the flight events.

#### 4. DNS/Focus/Habit Blocks -> DELETE

**Detection**: Summary contains any of these keywords:
- Keywords: "DNS", "Flexible", "Heads Down", "Focus", "Gym", "Lunch", "Walking", "Reading"

**Action**: Delete from calendar
```bash
python3 -m sidekick.clients.gcalendar delete <event_id> --no-notify
```

**Reference**: See `tools/prep_tomorrow_meetings.py:119-127` for skip_keywords list

#### 5. Meetings Where User is Organizer -> FLAG FOR MANUAL REVIEW

**Detection**: `organizer.email` == user's email address

**Action**: Report for manual handling
- Cannot decline your own meeting via API
- User must cancel or delegate manually
- **IMPORTANT**: If delegating to someone else to run the meeting, do NOT delete the event - deleting will break the Zoom/meeting link
- Include in "Manual Action Required" section of report

#### 6. Boss's Boss Meetings -> DECLINE but KEEP

**Detection**: Attendees list includes boss's boss's email

**Action**: Decline with message, DO NOT delete
```bash
python3 -m sidekick.clients.gcalendar decline <event_id> "Out of office - {reason}" --no-notify
```

#### 7. Interview Meetings -> DECLINE but KEEP

**Detection**: Summary or description contains:
- "Interview"
- "Phone Screen"
- "Technical Screen"
- "Screen:"
- "Candidate"
- "Hiring"
- "Onsite Interview"
- "Onsite"
- "Debrief" (in interview context)

**Action**: Decline with message, DO NOT delete
```bash
python3 -m sidekick.clients.gcalendar decline <event_id> "Out of office - {reason}" --no-notify
```

#### 8. Regular Meetings -> DECLINE and DELETE

**Detection**: Everything else with attendees (count > 1)

**Action**: Decline, then delete
```bash
python3 -m sidekick.clients.gcalendar decline <event_id> "Out of office - {reason}" --no-notify
python3 -m sidekick.clients.gcalendar delete <event_id> --no-notify
```

### Phase 4: Generate Action Plan

Build structured report showing all planned actions:

**Sections**:
1. Calendar blocks to create or keep (business days only, using `block_title`)
2. Existing blocks to rename
3. Travel/offsite events and all-day events to keep as-is
4. Focus/Habit blocks to delete
5. Meetings to decline & delete
6. Special meetings to decline only (keep on calendar)
7. Manual action required (organizer meetings)

**Format**: See "Report Format" section below

### Phase 5: Execute or Dry Run

#### If `--dry-run` flag present:

Write preview report to:
```
memory/pto-dry-run-{start_date}-to-{end_date}.md
```

Output message:
```
Dry run complete. No changes made.
Report saved to: memory/pto-dry-run-2026-04-15-to-2026-04-20.md
```

#### If live run (no --dry-run):

**Step 1: Create missing calendar blocks** (one per business day, using `block_title`)
```bash
python3 -m sidekick.clients.gcalendar create \
  "{block_title}" \
  "{date}T09:00:00-07:00" \
  "{date}T17:00:00-07:00"
```
For PTO, `block_title` should look like `PTO - Vacation` or `PTO`. For offsites and travel days, it should look like `OOO - Leadership Offsite` or `OOO - Travel Day`; do not create `PTO`-titled blocks for work travel.

**CRITICAL**: Always include the timezone offset in datetime strings:
- Use `-07:00` for PDT (typically April-October)
- Use `-08:00` for PST (typically November-March)
- Without the offset, times default to UTC and will be 7-8 hours off!

**Step 2: Rename mislabeled existing blocks**
```bash
for event_id in blocks_to_rename:
    python3 -m sidekick.clients.gcalendar update {event_id} summary "{block_title}"
```

Only rename clear personal availability blocks. If a non-PTO request already has a block titled `PTO`, rename it to the non-PTO `block_title`.

**Step 3: Keep travel/offsite and all-day events unchanged**

Do not call `decline`, `delete`, or `update` for preserved travel itinerary events, offsite anchor events, or all-day events unless the user explicitly asks.

**Step 4: Delete DNS/Focus/Habit blocks**
```bash
for event_id in habit_blocks:
    python3 -m sidekick.clients.gcalendar delete {event_id} --no-notify
```

**Step 5: Decline and delete regular meetings**
```bash
for event_id in regular_meetings:
    python3 -m sidekick.clients.gcalendar decline {event_id} "Out of office - {reason}" --no-notify
    python3 -m sidekick.clients.gcalendar delete {event_id} --no-notify
```

**Step 6: Decline only (keep) special meetings**
```bash
for event_id in special_meetings:
    python3 -m sidekick.clients.gcalendar decline {event_id} "Out of office - {reason}. Regrets!" --no-notify
```

**Note**: The `--no-notify` flag prevents email notifications from being sent to meeting organizers and attendees. Remove this flag if you want people to be notified of your decline/absence.

**Step 7: Generate summary report**

Write final report to:
```
memory/pto-block-summary-{start_date}-to-{end_date}.md
```

## Report Format

Use the same sections for dry runs and live summaries. Dry runs should say no changes were made; live summaries should include execution timestamp and actual counts.

```markdown
# Calendar Blocking Preview: {start_date} to {end_date}
**Reason**: {reason}
**Block title**: {block_title}
**Mode**: DRY RUN (no changes will be made)

## Actions Planned

### Calendar Blocks to Create or Keep ({count})
- **Mon 2026-06-01**: 9:00 AM - 5:00 PM PDT - OOO - Leadership Offsite

### Existing Blocks to Rename ({count})
- **Thu 2026-06-04 9:00 AM**: PTO -> OOO - Leadership Offsite

### Travel/Offsite Events Kept ({count})
- **Mon 2026-06-01 9:15 AM**: Flight WN 1234: OAK to LAX
  - Reason kept: Travel itinerary for Leadership Offsite
  - Action: Keep unchanged; do not decline or delete

### All-Day Events Kept ({count})
- **Mon 2026-06-01**: All-day context event

### Focus/Habit Blocks to Delete ({count})
- **Date Time**: Event title

### Meetings to Decline & Delete ({count})
- **Date Time**: Meeting title
  - Decline reason: "Out of office - {reason}"
  - Action: Decline (no email) then delete

### Special Meetings to Decline Only ({count})
- **Date Time**: Meeting title
  - Reason: Interview / boss's boss meeting
  - Action: Decline (no email) and keep on calendar

### Manual Action Required ({count})
- **Date Time**: Meeting title
  - You are the organizer; cancel or delegate manually.
  - If delegating, do not delete the event because that can break the meeting link.

## Summary
- Calendar blocks created or kept: {count} days
- Existing blocks renamed: {count}
- Travel/offsite events kept: {count}
- Automated actions: {count} events
- Manual review needed: {count} meetings
- Notifications: None - all operations use `--no-notify` where supported

This report generated using [chase-sidekick](https://github.com/chase-seibert/chase-sidekick) and the [pto-block skill](https://github.com/chase-seibert/chase-sidekick/tree/main/.agents/skills/pto-block).
```

## Edge Cases

1. **Weekends**: Automatically skip when generating business day list
2. **User is organizer**: Cannot decline via API - flag for manual handling
3. **Already declined events**: Skip decline step, proceed with deletion if needed
4. **All-day events**: Leave alone (different block type)
5. **Travel/itinerary events**: Keep unchanged even if they overlap the block or contain attendees
6. **Non-PTO requests with existing PTO blocks**: Rename clear personal blocks to the non-PTO `block_title`
7. **Recurring events**: Only handle single instances, not series modifications
8. **Token expiration**: Prompt user to run `python3 tools/get_google_refresh_token.py`
9. **API errors**: Log error, continue with remaining events
10. **Empty date ranges**: Validate at start, error if no business days
11. **Events without attendees**: Do not decline; delete only if habit/focus, preserve if travel/offsite, rename only if clearly an existing availability block
12. **Events where user already responded**: Update response status

## Timezone Handling

**CRITICAL**: Always include explicit timezone offsets in datetime strings to prevent UTC conversion.

- **Input dates**: YYYY-MM-DD format (date only, no time)

- **Determine correct offset**:
  - PDT (Pacific Daylight Time): `-07:00` - approximately mid-March to early November
  - PST (Pacific Standard Time): `-08:00` - approximately early November to mid-March
  - Use Python to verify:
    ```python
    from datetime import datetime
    import time
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    is_dst = time.localtime(dt.timestamp()).tm_isdst
    offset = "-07:00" if is_dst else "-08:00"
    ```

- **Calendar blocks**: Timed events with explicit timezone offset
  - Correct: `2026-04-15T09:00:00-07:00` to `2026-04-15T17:00:00-07:00`
  - **WRONG**: `2026-04-15T09:00:00` (defaults to UTC, creates 2am-10am PST!)

- **Query datetime format**: Include timezone offset
  - Example: `2026-04-15T00:00:00-07:00` to `2026-04-15T23:59:59-07:00`

- **Display**: Format as "9:00 AM - 5:00 PM PST/PDT" in reports

## Destructive Action Safety

Dry run first when the request is ambiguous or broad. For live runs, the skill is approved to make the calendar changes described in the action plan:
- Creating calendar blocks
- Renaming clearly mislabeled personal availability blocks
- Declining meetings
- Deleting focus/habit blocks and declined regular meetings

Never decline or delete travel itinerary events, offsite anchor events, or all-day events unless the user explicitly asks.

## Example Invocations

**Standard PTO**:
```
"Block my calendar for PTO from April 15 to April 20"
```

**With custom reason**:
```
"Block my calendar for a conference from May 1 to May 3"
```

**Leadership offsite**:
```
"Block my calendar for the leadership offsite from June 1 to June 4"
```

**Travel day**:
```
"Block my calendar for June 4 for travel day"
```

**Dry run first**:
```
"Show me what would happen if I blocked my calendar from June 1 to June 5 for vacation"
```

**Single day**:
```
"Block my calendar for tomorrow for a personal day"
```
