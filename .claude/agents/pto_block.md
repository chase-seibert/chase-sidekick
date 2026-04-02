---
name: pto_block
description: Block calendar for PTO and handle conflicting meetings
argument-hint: <start-date> <end-date> [reason] [--dry-run]
allowed-tools: Bash, Read, Write
auto-approve: false
---

# PTO Calendar Blocking Agent

Automates calendar management for PTO and out-of-office periods by:
- Creating calendar blocks for work hours (9am-5pm PST)
- Declining conflicting meetings with explanations
- Removing personal habit/focus blocks
- Preserving important meetings (interviews, senior leadership)

## Purpose

When you take time off, manual calendar cleanup is tedious:
- Block every day individually
- Go through each meeting to decline
- Remember which meetings to preserve
- Clean up focus/habit blocks that no longer apply

This agent handles it systematically with optional dry-run preview.

## Usage

**Dry run (recommended first)**:
```
"Run pto_block agent for 2026-04-15 to 2026-04-20 for Vacation with --dry-run"
```

**Live execution**:
```
"Run pto_block agent for 2026-04-15 to 2026-04-20 for Vacation"
```

**Custom reason**:
```
"Run pto_block agent for 2026-05-01 to 2026-05-03 for Conference"
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

2. **Validate date range**:
   - Dates in YYYY-MM-DD format
   - Start date <= end date
   - Reasonable duration (warn if > 4 weeks)
   - At least 1 business day in range

3. **Generate business day list**:
   - Skip weekends (Saturday, Sunday)
   - Include only Mon-Fri
   - Store list for later block creation

4. **Load user context from CLAUDE.local.md**:
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
   - Attendees list
   - Organizer email
   - Description

### Phase 3: Categorize Events

For each event, determine its category and action:

#### 1. DNS/Focus/Habit Blocks → DELETE

**Detection**: Summary contains any of these keywords:
- Keywords: "DNS", "Flexible", "Heads Down", "Focus", "Gym", "Lunch", "Walking", "Reading"

**Action**: Delete from calendar
```bash
python3 -m sidekick.clients.gcalendar delete <event_id> --no-notify
```

**Reference**: See `tools/prep_tomorrow_meetings.py:119-127` for skip_keywords list

#### 2. Meetings Where User is Organizer → FLAG FOR MANUAL REVIEW

**Detection**: `organizer.email` == user's email address

**Action**: Report for manual handling
- Cannot decline your own meeting via API
- User must cancel or delegate manually
- Include in "Manual Action Required" section of report

#### 3. Boss's Boss Meetings → DECLINE but KEEP

**Detection**: Attendees list includes boss's boss's email

**Action**: Decline with message, DO NOT delete
```bash
python3 -m sidekick.clients.gcalendar decline <event_id> "Out of office - {reason}" --no-notify
```

#### 4. Interview Meetings → DECLINE but KEEP

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

#### 5. Regular Meetings → DECLINE and DELETE

**Detection**: Everything else with attendees (count > 1)

**Action**: Decline, then delete
```bash
python3 -m sidekick.clients.gcalendar decline <event_id> "Out of office - {reason}" --no-notify
python3 -m sidekick.clients.gcalendar delete <event_id> --no-notify
```

### Phase 4: Generate Action Plan

Build structured report showing all planned actions:

**Sections**:
1. PTO blocks to create (business days only)
2. Focus/Habit blocks to delete
3. Meetings to decline & delete
4. Special meetings to decline only (keep on calendar)
5. Manual action required (organizer meetings)

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

**Step 1: Create PTO blocks** (one per business day)
```bash
python3 -m sidekick.clients.gcalendar create \
  "🏖️ PTO - {reason}" \
  "{date}T09:00:00-07:00" \
  "{date}T17:00:00-07:00"
```
**CRITICAL**: Always include the timezone offset in datetime strings:
- Use `-07:00` for PDT (typically April-October)
- Use `-08:00` for PST (typically November-March)
- Without the offset, times default to UTC and will be 7-8 hours off!

**Step 2: Delete DNS/Focus/Habit blocks**
```bash
for event_id in habit_blocks:
    python3 -m sidekick.clients.gcalendar delete {event_id} --no-notify
```

**Step 3: Decline and delete regular meetings**
```bash
for event_id in regular_meetings:
    python3 -m sidekick.clients.gcalendar decline {event_id} "Out of office - {reason}" --no-notify
    python3 -m sidekick.clients.gcalendar delete {event_id} --no-notify
```

**Step 4: Decline only (keep) special meetings**
```bash
for event_id in special_meetings:
    python3 -m sidekick.clients.gcalendar decline {event_id} "Out of office - {reason}. Regrets!" --no-notify
```

**Note**: The `--no-notify` flag prevents email notifications from being sent to meeting organizers and attendees. Remove this flag if you want people to be notified of your decline/absence.

**Step 5: Generate summary report**

Write final report to:
```
memory/pto-block-summary-{start_date}-to-{end_date}.md
```

## Report Format

### Dry Run Report

```markdown
# PTO Blocking Preview: {start_date} to {end_date}
**Reason**: {reason}
**Mode**: DRY RUN (no changes will be made)

---

## Actions Planned

### ✅ PTO Blocks to Create ({count})
- **Mon 2026-04-15**: 9:00 AM - 5:00 PM PST - 🏖️ PTO - Vacation
- **Tue 2026-04-16**: 9:00 AM - 5:00 PM PST - 🏖️ PTO - Vacation
- ...

### 🗑️ Focus/Habit Blocks to Delete ({count})
- **Mon 2026-04-15 12:00 PM**: 🥗 Lunch
- **Mon 2026-04-15 3:00 PM**: 🔒 Focus Time
- ...

### 📧 Meetings to Decline & Delete ({count})
- **Mon 2026-04-15 10:00 AM**: Weekly Team Sync
  - Attendees: 5 people
  - Decline reason: "Out of office - Vacation"
  - Action: Decline (no email) then delete
  - **No notification sent** to attendees

### 📌 Special Meetings to Decline Only (Keep on Calendar) ({count})

**Boss's Boss Meeting:**
- **Wed 2026-04-17 3:00 PM**: Executive Staff Review
  - Attendees: Khaled Sedky (boss's boss), 4 others
  - Decline reason: "Out of office - Vacation. Regrets!"
  - Action: Decline (no email) and keep on calendar
  - **No notification sent**

**Interview:**
- **Thu 2026-04-18 10:00 AM**: Phone Screen - Candidate Name
  - Decline reason: "Out of office - Vacation. Please reschedule."
  - Action: Decline (no email) and keep on calendar
  - **No notification sent**

### ⚠️ Manual Action Required ({count})

**Meetings You're Organizing:**
- **Mon 2026-04-15 11:00 AM**: Sprint Planning
  - **You are the organizer** - cannot decline via API
  - Recommendation: Cancel meeting and notify attendees

---

## Summary
- **Total calendar blocks**: {count} days
- **Automated actions**: {count} events
- **Manual review needed**: {count} meetings
- **Notifications**: None - all operations use `--no-notify` flag

**Note**: No email notifications will be sent to meeting organizers or attendees. Your calendar will show declined status, but people won't receive emails about it.

Run without `--dry-run` flag to execute these changes.
```

### Live Run Summary Report

```markdown
# PTO Calendar Blocking - {start_date} to {end_date}
**Reason**: {reason}
**Executed**: {timestamp}

---

## Summary
- PTO blocks created: {count} days
- Meetings declined: {count}
- Meetings deleted: {count}
- Interviews preserved: {count}
- Boss's boss meetings preserved: {count}
- Focus blocks removed: {count}
- **Manual review needed**: {count} meetings where you're the organizer

## Manual Action Required

### Meetings You Organized (Cannot Auto-Decline)
- **Date Time**: Meeting Title
  - Action: Cancel or delegate to someone else

## Calendar Blocks Created
- 2026-04-15 (Mon): 9:00 AM - 5:00 PM PST
- 2026-04-16 (Tue): 9:00 AM - 5:00 PM PST
- ...

## Meetings Declined
- **Date Time**: Meeting Title
  - Status: Declined and deleted (no email sent)
  - Decline reason: "Out of office - Vacation"

## Special Meetings Preserved
- **Date Time**: Meeting Title
  - Status: Declined but kept on calendar (no email sent)
  - Reason: Interview / Boss's boss meeting

## Notifications
- **No email notifications sent** - all operations used `--no-notify` flag
- Your calendar shows declined status, but organizers/attendees were not notified
- Consider setting an out-of-office auto-reply to handle meeting requests
```

## Edge Cases

1. **Weekends**: Automatically skip when generating business day list
2. **User is organizer**: Cannot decline via API - flag for manual handling
3. **Already declined events**: Skip decline step, proceed with deletion if needed
4. **All-day events**: Leave alone (different block type)
5. **Recurring events**: Only handle single instances, not series modifications
6. **Token expiration**: Prompt user to run `python3 tools/get_google_refresh_token.py`
7. **API errors**: Log error, continue with remaining events
8. **Empty date ranges**: Validate at start, error if no business days
9. **Events without attendees**: Skip (likely personal blocks, not meetings)
10. **Events where user already responded**: Update response status

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

## Confirmation for Destructive Actions

Since `auto-approve: false`, Claude will ask for confirmation before:
- Creating PTO calendar blocks
- Declining meetings
- Deleting events from calendar

User can review the dry-run report first, then approve the live run.

## Example Invocations

**Standard PTO**:
```
"Block my calendar for PTO from April 15 to April 20"
```

**With custom reason**:
```
"Block my calendar for a conference from May 1 to May 3"
```

**Dry run first**:
```
"Show me what would happen if I blocked my calendar from June 1 to June 5 for vacation"
```

**Single day**:
```
"Block my calendar for tomorrow for a personal day"
```
