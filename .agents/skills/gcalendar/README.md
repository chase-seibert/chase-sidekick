# Google Calendar Skill

Manage Google Calendar events from the command line.

## Setup

### Quick Setup (Recommended)

Use the provided helper script to set up Gmail, Google Calendar, and Google Sheets with one OAuth token:

```bash
python3 tools/get_google_refresh_token.py
```

This interactive script will guide you through the entire setup process and generate the credentials you need.

### Manual Setup (Alternative)

#### 1. Create OAuth2 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable Google Calendar API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click "Enable"
4. Create OAuth2 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Desktop app"
   - Name it (e.g., "My Sidekick App")
   - Download the credentials JSON

#### 2. Get Refresh Token

Use this Python script to obtain a refresh token:

```python
from urllib.parse import urlencode
import webbrowser

client_id = "YOUR_CLIENT_ID"
redirect_uri = "http://localhost"
scope = "https://www.googleapis.com/auth/calendar"

auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
    "client_id": client_id,
    "redirect_uri": redirect_uri,
    "response_type": "code",
    "scope": scope,
    "access_type": "offline",
    "prompt": "consent"
})

print("Visit this URL:")
print(auth_url)
webbrowser.open(auth_url)

# After authorizing, copy the 'code' from the redirect URL
code = input("Enter the authorization code: ")

# Exchange code for tokens
import urllib.request
import json

token_url = "https://oauth2.googleapis.com/token"
data = urlencode({
    "client_id": client_id,
    "client_secret": "YOUR_CLIENT_SECRET",
    "code": code,
    "redirect_uri": redirect_uri,
    "grant_type": "authorization_code"
}).encode()

req = urllib.request.Request(token_url, data=data)
with urllib.request.urlopen(req) as response:
    tokens = json.loads(response.read().decode())
    print("\nRefresh token:")
    print(tokens["refresh_token"])
```

### 3. Configure .env

Add to your `.env` file:

```bash
GOOGLE_CALENDAR_CLIENT_ID=your_client_id_here
GOOGLE_CALENDAR_CLIENT_SECRET=your_client_secret_here
GOOGLE_CALENDAR_REFRESH_TOKEN=your_refresh_token_here
```

## Commands

### List Events

List calendar events within a date range:

```bash
# List next 10 events
python -m sidekick.clients.gcalendar list

# List events in specific date range
python -m sidekick.clients.gcalendar list "2024-01-01T00:00:00Z" "2024-01-31T23:59:59Z"

# List up to 20 events
python -m sidekick.clients.gcalendar list "2024-01-01T00:00:00Z" "2024-01-31T23:59:59Z" 20
```

**Date format:** RFC3339 timestamp (e.g., `2024-01-15T14:00:00Z`)

**Output format** (one line per event):
```
abc123def456: Team Meeting
  2024-01-15 14:00 @ Conference Room A

xyz789ghi012: Lunch with Client
  2024-01-16 12:00 @ Downtown Cafe
```

### Get Event Details

Get full details of a specific event:

```bash
python -m sidekick.clients.gcalendar get EVENT_ID
```

**Output:**
```
Event ID: abc123def456
Summary: Team Meeting
Start: 2024-01-15T14:00:00Z
End: 2024-01-15T15:00:00Z
Description: Discuss Q1 planning
Location: Conference Room A
Attendees: john@example.com, jane@example.com
Link: https://calendar.google.com/calendar/event?eid=...
```

### Create Event

Create a new calendar event:

```bash
# Timed event (with specific hours)
python -m sidekick.clients.gcalendar create "Team Meeting" "2024-01-15T14:00:00Z" "2024-01-15T15:00:00Z"

# All-day event (date only, no time)
python -m sidekick.clients.gcalendar create "Company Holiday" "2024-12-25" "2024-12-26"
```

**Output:**
```
Event created successfully!
Event ID: abc123def456
Summary: Team Meeting
Start: 2024-01-15T14:00:00Z
End: 2024-01-15T15:00:00Z
Link: https://calendar.google.com/calendar/event?eid=...
```

### Update Event

Update specific fields of an existing event:

```bash
# Update summary (title)
python -m sidekick.clients.gcalendar update EVENT_ID summary "Updated Meeting Title"

# Update description
python -m sidekick.clients.gcalendar update EVENT_ID description "New meeting notes"

# Update location
python -m sidekick.clients.gcalendar update EVENT_ID location "Room 202"

# Update start time
python -m sidekick.clients.gcalendar update EVENT_ID start_time "2024-01-15T15:00:00Z"

# Update end time
python -m sidekick.clients.gcalendar update EVENT_ID end_time "2024-01-15T16:00:00Z"
```

**Output:**
```
Event updated successfully!
Event ID: abc123def456
Summary: Updated Meeting Title
...
```

### Delete Event

Delete a calendar event:

```bash
python -m sidekick.clients.gcalendar delete EVENT_ID
```

**Output:**
```
Event deleted successfully: abc123def456
```

## Python Usage

```python
from sidekick.clients.gcalendar import GCalendarClient

client = GCalendarClient(
    client_id="your_client_id",
    client_secret="your_client_secret",
    refresh_token="your_refresh_token"
)

# List events
events = client.list_events(
    time_min="2024-01-01T00:00:00Z",
    time_max="2024-01-31T23:59:59Z",
    max_results=20
)
for event in events:
    print(f"{event['summary']}: {event['start']}")

# Get specific event
event = client.get_event("EVENT_ID")
print(event["summary"])

# Create event
event = client.create_event(
    summary="Team Meeting",
    start_time="2024-01-15T14:00:00Z",
    end_time="2024-01-15T15:00:00Z",
    description="Quarterly planning",
    location="Conference Room A",
    attendees=["john@example.com", "jane@example.com"]
)
print(f"Created: {event['id']}")

# Update event
event = client.update_event(
    event_id="EVENT_ID",
    summary="Updated Title",
    start_time="2024-01-15T15:00:00Z"
)

# Delete event
client.delete_event("EVENT_ID")
```

## Date/Time Formats

### RFC3339 Timestamp (Timed Events)

Format: `YYYY-MM-DDTHH:MM:SSZ`

Examples:
- `2024-01-15T14:00:00Z` - 2:00 PM UTC
- `2024-12-25T09:30:00Z` - 9:30 AM UTC

Use `Z` suffix for UTC timezone, or specify timezone:
- `2024-01-15T14:00:00-08:00` - 2:00 PM Pacific Time

### Date Only (All-Day Events)

Format: `YYYY-MM-DD`

Examples:
- `2024-01-15` - January 15, 2024
- `2024-12-25` - December 25, 2024

Note: All-day events use date only (no time component).

## Tips

### Generate Timestamps

Use Python to generate RFC3339 timestamps:

```python
from datetime import datetime, timedelta, timezone

# Current time
now = datetime.now(timezone.utc).isoformat()

# Tomorrow at 2 PM UTC
tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
tomorrow = tomorrow.replace(hour=14, minute=0, second=0)
print(tomorrow.isoformat())

# Next Monday at 9 AM
import calendar
today = datetime.now(timezone.utc)
days_ahead = 0 - today.weekday()  # Monday is 0
if days_ahead <= 0:
    days_ahead += 7
next_monday = today + timedelta(days=days_ahead)
next_monday = next_monday.replace(hour=9, minute=0, second=0)
print(next_monday.isoformat())
```

### List This Week's Events

```bash
# Using date command (macOS/Linux)
START=$(date -u +"%Y-%m-%dT00:00:00Z")
END=$(date -u -v+7d +"%Y-%m-%dT23:59:59Z")
python -m sidekick.clients.gcalendar list "$START" "$END"
```

### Find Event ID

The event ID is shown when you list or create events. You can also:
1. Open event in Google Calendar web interface
2. Look at the URL: `https://calendar.google.com/calendar/event?eid=...`
3. The event ID is in the URL (after decoding)

## Limitations

- Only works with your primary calendar (can be extended to support multiple calendars)
- Recurring events are expanded to individual instances
- No support for event reminders or notifications
- No support for calendar sharing or permissions

## Troubleshooting

**"Failed to refresh access token"**
- Verify your client_id and client_secret are correct
- Ensure refresh_token is valid (may need to regenerate)
- Check that Calendar API is enabled in Google Cloud Console

**"Resource not found"**
- Verify the event ID is correct
- Event may have been deleted
- You may not have access to this calendar

**"403 Forbidden"**
- Ensure Google Calendar API is enabled for your project
- Check OAuth2 scopes include `calendar` access
