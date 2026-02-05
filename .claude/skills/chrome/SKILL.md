---
name: chrome
description: Query Chrome browsing history
argument-hint: <operation> [args]
allowed-tools: Bash, Read
---

# Chrome Skill

Command-line interface for Chrome browsing history.

When invoked, use the Chrome client to handle the request: $ARGUMENTS

## Available Commands

### List History
```bash
python3 -m sidekick.clients.chrome list-history [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--max-results N]
```

### Search History
```bash
python3 -m sidekick.clients.chrome search "query" [--max-results N]
```

### List Confluence Pages
```bash
python3 -m sidekick.clients.chrome list-confluence [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--max-results N]
```

### List Dropbox Paper Docs
```bash
python3 -m sidekick.clients.chrome list-paper [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--max-results N]
```

### List JIRA Issues
```bash
python3 -m sidekick.clients.chrome list-jira [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--max-results N]
```

### List Google Sheets
```bash
python3 -m sidekick.clients.chrome list-sheets [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--max-results N]
```

### List Google Searches
```bash
python3 -m sidekick.clients.chrome list-searches [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--max-results N]
```

### Custom Profile
```bash
python3 -m sidekick.clients.chrome list-history --profile "Profile 1"
```

## Date Options

All date arguments are **optional**:
- `--start-date YYYY-MM-DD` - Start date (defaults to beginning of history if omitted)
- `--end-date YYYY-MM-DD` - End date (defaults to now if omitted)
- `--max-results N` - Maximum number of results (default: 100)

## Example Usage

When the user asks to:
- "Show me what I visited today" - Use list-history with --start-date set to today
- "Find all JIRA issues I looked at this week" - Use list-jira with date range for this week
- "What Confluence pages did I open yesterday?" - Use list-confluence with yesterday's date
- "Show my Google searches from last week" - Use list-searches with last week's date range
- "Find Chrome history containing 'api design'" - Use search with query "api design"

## Chrome Profile Paths

Default locations:
- **macOS:** `~/Library/Application Support/Google/Chrome/Default`
- **Linux:** `~/.config/google-chrome/Default`
- **Windows:** `%LOCALAPPDATA%\Google\Chrome\User Data\Default`

Use `--profile` flag to specify custom profile path or profile name.

For full documentation, see the detailed Chrome skill documentation in this folder.
