# Chrome Skill

Command-line interface for querying Chrome browsing history.

## Configuration

No configuration needed! The Chrome client automatically detects your Chrome profile location based on your operating system.

**Default Profile Locations:**
- **macOS:** `~/Library/Application Support/Google/Chrome/Default`
- **Linux:** `~/.config/google-chrome/Default`
- **Windows:** `%LOCALAPPDATA%\Google\Chrome\User Data\Default`

**Using Custom Profiles:**
```bash
# Use a different Chrome profile
python3 -m sidekick.clients.chrome list-history --profile "Profile 1"

# Use a custom profile path
python3 -m sidekick.clients.chrome list-history --profile "/path/to/chrome/profile"
```

## Commands

All commands use the module form (`python3 -m sidekick.clients.chrome`).

**Note:** All date arguments are **optional**. If not specified, the command will query all available history.

### List History

```bash
# List recent history (no date filter)
python3 -m sidekick.clients.chrome list-history --max-results 50

# List history for a specific date
python3 -m sidekick.clients.chrome list-history --start-date 2026-02-04

# List history within a date range
python3 -m sidekick.clients.chrome list-history \
    --start-date 2026-02-01 \
    --end-date 2026-02-04 \
    --max-results 100
```

Output format:
```
Found 42 history entries:

2026-02-04 14:30:00 PST | DBX-1234: Fix login bug | https://company.atlassian.net/browse/DBX-1234 (visited 5 times)
2026-02-04 13:15:00 PST | Project Review Doc | https://example.com/docs/xyz/project-review (visited 2 times)
2026-02-04 12:00:00 PST | Google Search: python sqlite3 | https://google.com/search?q=python+sqlite3 (visited 1 time)
```

### Search History

```bash
# Search for URLs or page titles containing a keyword
python3 -m sidekick.clients.chrome search "jira"
python3 -m sidekick.clients.chrome search "api design"
python3 -m sidekick.clients.chrome search "confluence"
```

Output format:
```
Found 15 matching entries:

2026-02-04 14:30:00 PST | DBX-1234: Fix login bug | https://company.atlassian.net/browse/DBX-1234 (visited 5 times)
2026-02-04 10:15:00 PST | JIRA Dashboard | https://company.atlassian.net/jira/dashboards (visited 12 times)
...
```

### List Confluence Pages

```bash
# List all Confluence pages
python3 -m sidekick.clients.chrome list-confluence

# List Confluence pages visited within a date range
python3 -m sidekick.clients.chrome list-confluence \
    --start-date 2026-02-01 \
    --end-date 2026-02-04
```

Filters URLs containing `atlassian.net/wiki`.

Output format:
```
Found 8 Confluence pages:

2026-02-04 14:00:00 PST | Technical Design Doc | https://company.atlassian.net/wiki/spaces/ENG/pages/123456 (visited 3 times)
2026-02-03 16:30:00 PST | Team Roadmap | https://company.atlassian.net/wiki/spaces/TEAM/pages/789012 (visited 2 times)
...
```

### List Dropbox Paper Docs

```bash
# List all Paper docs
python3 -m sidekick.clients.chrome list-paper

# List Paper docs from the last week
python3 -m sidekick.clients.chrome list-paper --start-date 2026-01-28
```

Filters URLs containing `dropbox.com/scl/fi` or `paper`.

Output format:
```
Found 5 Paper docs:

2026-02-04 11:00:00 PST | Alice & Dan 1:1 | https://example.com/docs/xyz/alice-dan-11 (visited 4 times)
2026-02-03 14:00:00 PST | Project Brief | https://example.com/docs/abc/project-brief (visited 2 times)
...
```

### List JIRA Issues

```bash
# List all JIRA issues
python3 -m sidekick.clients.chrome list-jira

# List JIRA issues visited today
python3 -m sidekick.clients.chrome list-jira --start-date 2026-02-04
```

Filters URLs containing `atlassian.net/browse/`.

Output format:
```
Found 12 JIRA issues:

2026-02-04 14:30:00 PST | DBX-1234: Fix login bug | https://company.atlassian.net/browse/DBX-1234 (visited 5 times)
2026-02-04 10:00:00 PST | DBX-5678: Add feature | https://company.atlassian.net/browse/DBX-5678 (visited 2 times)
...
```

### List Google Sheets

```bash
# List all Google Sheets
python3 -m sidekick.clients.chrome list-sheets

# List Google Sheets from this month
python3 -m sidekick.clients.chrome list-sheets --start-date 2026-02-01
```

Filters URLs containing `docs.google.com/spreadsheets`.

Output format:
```
Found 7 Google Sheets:

2026-02-04 15:00:00 PST | Team Metrics Q1 2026 | https://docs.google.com/spreadsheets/d/abc123/edit (visited 8 times)
2026-02-03 09:00:00 PST | Budget Planning | https://docs.google.com/spreadsheets/d/xyz789/edit (visited 3 times)
...
```

### List Google Searches

```bash
# List all Google searches
python3 -m sidekick.clients.chrome list-searches

# List Google searches from yesterday
python3 -m sidekick.clients.chrome list-searches --start-date 2026-02-03
```

Filters URLs containing `google.*/search`.

Output format:
```
Found 20 Google searches:

2026-02-04 16:00:00 PST | chrome history sqlite python - Google Search | https://www.google.com/search?q=chrome+history+sqlite+python (visited 1 time)
2026-02-04 14:00:00 PST | python datetime timezone - Google Search | https://www.google.com/search?q=python+datetime+timezone (visited 1 time)
...
```

## Common Use Cases

### Find What You Were Working On

```bash
# What did I look at yesterday?
python3 -m sidekick.clients.chrome list-history --start-date 2026-02-03 --end-date 2026-02-03

# What JIRA issues did I review this week?
python3 -m sidekick.clients.chrome list-jira --start-date 2026-02-01

# What Confluence docs have I accessed this month?
python3 -m sidekick.clients.chrome list-confluence --start-date 2026-02-01
```

### Research Context Recovery

```bash
# Find that doc about API design I was reading
python3 -m sidekick.clients.chrome search "api design"

# What did I search for when debugging that issue?
python3 -m sidekick.clients.chrome list-searches --start-date 2026-02-03
```

### Meeting Preparation

```bash
# What resources did I review before today's meeting?
python3 -m sidekick.clients.chrome list-history \
    --start-date 2026-02-04 \
    --max-results 50
```

### Work Pattern Analysis

```bash
# How many JIRA issues have I reviewed this sprint?
python3 -m sidekick.clients.chrome list-jira --start-date 2026-01-20 --max-results 100

# What Paper docs did I access during project planning?
python3 -m sidekick.clients.chrome list-paper --start-date 2026-01-15 --end-date 2026-01-30
```

## Python Usage

```python
from sidekick.clients.chrome import ChromeClient

# Initialize client with default profile
client = ChromeClient()

# Or use a custom profile
client = ChromeClient(profile_path="/path/to/chrome/profile")

# List history within date range
history = client.list_history(
    start_date="2026-02-01",
    end_date="2026-02-04",
    max_results=100
)

for entry in history:
    print(f"{entry['last_visit_time']}: {entry['title']}")
    print(f"  URL: {entry['url']}")
    print(f"  Visited: {entry['visit_count']} times")

# Search history
results = client.search_history("jira", max_results=50)
for entry in results:
    print(f"{entry['title']}: {entry['url']}")

# Convenience filters
confluence_pages = client.list_confluence_pages(start_date="2026-02-01")
paper_docs = client.list_paper_docs(start_date="2026-02-01")
jira_issues = client.list_jira_issues(start_date="2026-02-01")
sheets = client.list_google_sheets(start_date="2026-02-01")
searches = client.list_google_searches(start_date="2026-02-01")
```

### Result Dictionary Format

All methods return a list of dictionaries with the following keys:

```python
{
    'url': 'https://example.com/page',
    'title': 'Page Title',
    'visit_count': 5,
    'last_visit_time': '2026-02-04 14:30:00 PST',  # Human-readable local time
    'last_visit_iso': '2026-02-04T14:30:00-08:00',  # ISO 8601 format
    'last_visit_chrome': 13374321000000  # Raw Chrome timestamp
}
```

## Technical Details

### Chrome History Database

Chrome stores browsing history in a SQLite database at:
- `{Profile}/History`

The database contains a `urls` table with:
- `url` - The URL
- `title` - Page title
- `visit_count` - Number of visits
- `last_visit_time` - Chrome timestamp (microseconds since 1601-01-01)
- `hidden` - Whether the URL is hidden (0 or 1)

### Timestamp Format

Chrome uses **WebKit epoch**: microseconds since 1601-01-01 00:00:00 UTC.

The client automatically converts these to human-readable local time:
- Input: `13374321000000` (Chrome timestamp)
- Output: `2026-02-04 14:30:00 PST` (local time)

### Database Locking

Chrome locks the History database while running. The client automatically handles this by:
1. Copying the database to a temporary location
2. Querying the copy
3. Cleaning up the temporary file

This ensures the client works even while Chrome is running.

### Date Handling

- All dates use ISO format: `YYYY-MM-DD` (e.g., `2026-02-04`)
- Dates are treated as midnight UTC for the specified day
- End dates are inclusive (entire end day is included)
- All output times are converted to your local timezone

## Limitations

### V1 Limitations

- **No open tabs support**: Currently only queries history, not currently open tabs (planned for V2)
- **No bookmarks**: Only browsing history, not bookmarks (planned for V2)
- **Single profile at a time**: Can only query one Chrome profile per command
- **No download history**: Only page visits, not file downloads (planned for V2)

### Known Caveats

- **Incognito mode**: Chrome doesn't save incognito browsing to the History database
- **Sync conflicts**: If Chrome is syncing history, there may be brief delays
- **Custom installations**: Non-standard Chrome installations may require `--profile` flag
- **Performance**: Large history databases (100k+ entries) may be slower to query

## Troubleshooting

### Chrome profile not found

```
Error: Chrome profile not found at: /path/to/chrome/profile
```

**Solution:** Specify your Chrome profile path:
```bash
python3 -m sidekick.clients.chrome list-history --profile "/path/to/your/profile"
```

### History database not found

```
Error: Chrome History database not found: /path/to/History
```

**Solution:** Make sure Chrome has been run at least once and browsing history is enabled in Chrome settings.

### Invalid date format

```
Error: Invalid date format: 02-04-2026
Use ISO format: YYYY-MM-DD (e.g., 2026-02-04)
```

**Solution:** Use ISO date format (YYYY-MM-DD):
```bash
python3 -m sidekick.clients.chrome list-history --start-date 2026-02-04
```

## Related Skills

- **Memory** (`memory`) - Save Chrome history queries to command memory files
- **JIRA** (`jira`) - Cross-reference JIRA issues with Chrome browsing history
- **Confluence** (`confluence`) - Find and read Confluence pages you've visited
- **Dropbox** (`dropbox`) - Access Paper docs you've viewed
