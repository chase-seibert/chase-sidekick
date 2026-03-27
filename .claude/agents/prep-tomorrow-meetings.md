# Prep Tomorrow Meetings Agent

Opens all meeting docs in Chrome for the next business day.

## Purpose

Quickly prepare for upcoming meetings by opening all attached meeting docs (Confluence pages, Paper docs, etc.) in Chrome tabs.

## Workflow

1. **Calculate next business day**
   - If today is Friday, Saturday, or Sunday → next business day is Monday
   - Otherwise → next business day is tomorrow
   - Use Python to calculate the date

2. **List calendar events**
   ```bash
   python3 -m sidekick.clients.gcalendar list <start_time> <end_time> 50
   ```
   - Use RFC3339 format: `YYYY-MM-DDTHH:MM:SSZ`
   - Start time: `00:00:00Z` of target date
   - End time: `23:59:59Z` of target date

3. **Get details for each meeting**
   ```bash
   python3 -m sidekick.clients.gcalendar get <event_id>
   ```
   - Run in parallel for all events
   - Extract meeting docs from `Description` field
   - Look for Confluence URLs (atlassian.net/wiki)
   - Look for Paper docs (dropbox.com/scl/fi)
   - Look for Google Docs (docs.google.com)

4. **Open docs in Chrome**
   ```bash
   open -a "Google Chrome" <url1> <url2> <url3> ...
   ```
   - Open all doc URLs in a single command
   - Each URL opens as a new tab

5. **Report results**
   - List each meeting with its time and doc link
   - Confirm how many docs were opened

## Example Usage

**User request:**
> "Open my meeting docs for the next business day"

**Agent response:**
```
Found 4 meetings on Monday, March 30:

9:00 AM - Alice / Bob 1:1
- Doc: Alice Bob 1:1 (Confluence)

9:30 AM - Engineering Execution Review
- Doc: Engineering Execution Review (Confluence)

10:00 AM - Team Stand-Up
- Doc: Team Stand-Up Deep Dives (Paper)

12:00 PM - Alice / Carol
- Doc: Alice Carol 1:1 (Confluence)

Opened 4 meeting docs in Chrome.
```

## Calculating Next Business Day

Use Python inline calculation:

```python
from datetime import datetime, timedelta

def next_business_day():
    today = datetime.now()
    # Monday=0, Sunday=6
    if today.weekday() >= 4:  # Friday, Saturday, Sunday
        days_ahead = 7 - today.weekday()  # Days until Monday
    else:
        days_ahead = 1  # Tomorrow

    next_day = today + timedelta(days=days_ahead)
    return next_day.strftime("%Y-%m-%d")

# For calendar API (UTC timestamps)
def next_business_day_range():
    date = next_business_day()
    return (f"{date}T00:00:00Z", f"{date}T23:59:59Z")
```

## Extracting Doc URLs

Meeting docs are embedded in HTML descriptions. Common patterns:

**Confluence:**
```html
<a href="https://company.atlassian.net/wiki/spaces/...">...</a>
```

**Paper:**
```html
<a href="https://www.dropbox.com/scl/fi/...">Link</a>
```

**Google Docs:**
```html
<a href="https://docs.google.com/document/d/...">...</a>
```

Extract using regex or simple string parsing for `href=` attributes.

## Edge Cases

- **No meetings**: Report "No meetings found for [date]"
- **Meeting without docs**: Skip, only open meetings with actual doc links
- **All-day events**: Include in list but typically don't have docs
- **Recurring habits** (Gym, Lunch): Skip these, focus on actual meetings with other people
- **Token expired**: Prompt user to run `! python3 tools/get_google_refresh_token.py`

## Filter for Real Meetings

Skip calendar events that are:
- Habits (🚶‍♂️, 📖, 💪, etc.)
- DNS/Focus time blocks
- All-day events without attendees
- Events without description or links

Focus on:
- Events with multiple attendees
- Events with Zoom links
- Events with doc URLs in description

## Integration

This agent uses:
- **gcalendar skill**: For listing and getting event details
- **Chrome**: For opening URLs (macOS `open` command)
- **Python**: For date calculations

## Troubleshooting

**Calendar token expired:**
```bash
! python3 tools/get_google_refresh_token.py
```

**Chrome not opening:**
- Verify Chrome is installed at `/Applications/Google Chrome.app`
- Try: `open -a "Google Chrome" <url>` manually
- Alternative: `open <url>` (uses default browser)

**No docs found:**
- Some meetings may not have attached docs
- Check event description manually in Google Calendar
- Docs may be in meeting chat or email instead
