---
name: gcalendar
description: Manage Google Calendar events
argument-hint: <operation> [args]
allowed-tools: Bash, Read
---

# Google Calendar Skill

Manage Google Calendar events from the command line.

When invoked, use the Google Calendar client to handle the request: $ARGUMENTS

## Available Commands

### List Events
```bash
python -m sidekick.clients.gcalendar list [start_time] [end_time] [max_results]
```

### Get Event Details
```bash
python -m sidekick.clients.gcalendar get EVENT_ID
```

### Create Event
```bash
python -m sidekick.clients.gcalendar create "Title" "start_time" "end_time"
```

### Update Event
```bash
python -m sidekick.clients.gcalendar update EVENT_ID <field> <value>
```

Fields: summary, description, location, start_time, end_time

### Delete Event
```bash
python -m sidekick.clients.gcalendar delete EVENT_ID
```

## Date/Time Formats

**RFC3339 Timestamp (Timed Events):**
- Format: `YYYY-MM-DDTHH:MM:SSZ`
- Example: `2024-01-15T14:00:00Z` (2:00 PM UTC)

**Date Only (All-Day Events):**
- Format: `YYYY-MM-DD`
- Example: `2024-01-15`

## Example Usage

When the user asks to:
- "What's on my calendar today?" - Use list with appropriate date range
- "Create a meeting for tomorrow at 2pm" - Use create with RFC3339 timestamp
- "Cancel the 3pm meeting" - Search for the event and delete it
- "Update the meeting title" - Use update with EVENT_ID and new summary

For full documentation, see the detailed Google Calendar skill documentation in this folder.
