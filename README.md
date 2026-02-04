# Chase Sidekick

Engineering manager task automation toolkit.

## Overview

Chase Sidekick automates engineering manager tasks by providing:
- **Clients**: Single-file Python interfaces to services (JIRA, Confluence, Dropbox, OmniFocus, etc.)
- **Skills**: Markdown documentation for command-line usage
- **Agents**: Multi-step workflows coordinating multiple clients for complex tasks

## Quick Start

### Setup

```bash
# Create configuration file
cp .env.example .env
# Edit .env with your credentials
# - ATLASSIAN_URL, ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN (required for JIRA/Confluence)
# - USER_NAME, USER_EMAIL (required for Confluence 1:1 docs)
# - DROPBOX_ACCESS_TOKEN (required for Dropbox)
# Get Atlassian API token: https://id.atlassian.com/manage-profile/security/api-tokens
# Get Dropbox access token: https://www.dropbox.com/developers/apps
```

### Example Prompts

Here are natural language prompts you can use with each skill:

**JIRA Prompts:**
```
"Find roadmap items nested under PROJ-1735 in the PROJ Project"
"Show me the hierarchy for PROJ-500"
"What issues are linked to TEAM-100?"
"Get all Story issues under EPIC-200 in the EPIC project"
"Find all issues under PROJ-1735 across all projects"
"Query issues with status Open in the PROJ project"
"Show me all backend issues in PROJ"
"Add label 'needs-review' to PROJ-123"
"Remove label 'blocked' from PROJ-456"
```

**Confluence Prompts:**
```
"Search for pages about API documentation"
"Add 'Discuss Q1 planning' to my 1:1 doc with Nandan"
"Add 'Review PR-456' to my 1:1 with Bob in the Next section"
"Read the content of page 123456789"
"Search for 'Team Guidelines' in the TEAM space"
"Show me all pages with 'meeting notes' in the title"
"Create a new page called 'Sprint Planning' in the DEV space"
```

**OmniFocus Prompts (macOS only):**
```
"Show me all my inbox tasks"
"Create a task 'Review documentation'"
"Show me flagged tasks"
"List tasks in the Work project"
"Show tasks due this week"
"Complete the task 'Send report'"
"Show all my projects"
"List tasks tagged with 'urgent'"
```

**Dropbox Prompts:**
```
"Get the contents of /Documents/notes.txt"
"Download file from https://www.dropbox.com/s/abc123/file.txt"
"Write 'Hello World' to /Documents/test.txt"
"Show metadata for /Paper/MyDoc.paper"
"Get Paper doc content from /Paper/Planning.paper"
"Get Paper doc as HTML from /Paper/Specs.paper"
"Create a new Paper doc at /Paper/NewDoc.paper with content 'Title'"
"Update Paper doc at /Paper/MyDoc.paper"
```

**Gmail Prompts:**
```
"Search for emails from boss@example.com"
"Show me unread emails from last week"
"Read email MESSAGE_ID"
"Create a draft email to team@example.com"
"Search for emails with subject 'meeting'"
```

**Google Calendar Prompts:**
```
"List my calendar events for this week"
"Show events between 2024-01-01 and 2024-01-31"
"Create a meeting tomorrow at 2pm"
"Update event EVENT_ID with new title"
"Delete event EVENT_ID"
```

**Google Sheets Prompts:**
```
"List all my spreadsheets"
"List first 20 spreadsheets"
"Get info for spreadsheet URL https://docs.google.com/..."
"Download spreadsheet SHEET_ID as CSV"
"Download spreadsheet from URL https://docs.google.com/..."
"Upload data.csv to a new spreadsheet"
"Replace sheet in SHEET_ID with data.csv"
```

**Output Management Prompts:**
```
"List all saved JIRA outputs"
"Find outputs about PROJ-1735"
"Show me recent Confluence outputs"
"List all saved command outputs"
```

### Command Line Usage

Configuration is automatically loaded from `.env` file.

#### JIRA Commands

```bash
# Get single issue (detailed view)
python -m sidekick.clients.jira get-issue PROJ-123
# Output:
# PROJ-123: Fix login bug
#   Status: In Progress
#   Assignee: John Doe
#   Labels: backend, bug
#   Type: Bug

# Query issues (one per line)
python -m sidekick.clients.jira query "project = PROJ AND status = Open"
# Output:
# Found 42 issues (showing 50):
# PROJ-123: Fix login bug [In Progress] (John Doe) [backend, bug]
# PROJ-124: Add dark mode [To Do] (Jane Smith) [frontend]
# ...

# Query by parent (subtasks)
python -m sidekick.clients.jira query-by-parent PROJ-100

# Query by label
python -m sidekick.clients.jira query-by-label backend

# Get roadmap hierarchy (recursively find all children and linked issues)
python -m sidekick.clients.jira roadmap-hierarchy PROJ-100 PROJ
python -m sidekick.clients.jira roadmap-hierarchy PROJ-100 PROJ Story
python -m sidekick.clients.jira roadmap-hierarchy PROJ-100  # All projects

# Add/remove labels
python -m sidekick.clients.jira add-label PROJ-123 needs-review
python -m sidekick.clients.jira remove-label PROJ-123 blocked

# Update issue
python -m sidekick.clients.jira update-issue PROJ-123 '{"summary": "New title"}'
```

#### Confluence Commands

```bash
# Search for pages
python -m sidekick.clients.confluence search "API Documentation"
python -m sidekick.clients.confluence search "meeting notes" --space TEAM --limit 10

# Get page details
python -m sidekick.clients.confluence get-page 123456789
python -m sidekick.clients.confluence get-page-by-title "Home" DEV

# Read page content
python -m sidekick.clients.confluence read-page 123456789 > page.html

# Add topic to 1:1 doc
python -m sidekick.clients.confluence add-topic-to-oneonone Nandan "Discuss Q1 planning"
python -m sidekick.clients.confluence add-topic-to-oneonone Bob "Review PR-456" --section "Feb 5"

# Create new page
echo "<h1>New Page</h1><p>Content</p>" > content.html
python -m sidekick.clients.confluence create-page DEV "Sprint Planning" content.html

# Update existing page
python -m sidekick.clients.confluence update-page 123456789 updated-content.html
python -m sidekick.clients.confluence update-page 123456789 content.html --title "New Title"

# Cache management
python -m sidekick.clients.confluence cache-show
python -m sidekick.clients.confluence cache-clear
```

#### OmniFocus Commands (macOS only)

```bash
# Query tasks
python -m sidekick.clients.omnifocus query  # All inbox tasks
python -m sidekick.clients.omnifocus query --project Work
python -m sidekick.clients.omnifocus query --tag urgent
python -m sidekick.clients.omnifocus query --flagged
python -m sidekick.clients.omnifocus query --due-before 2026-02-10

# Get single task
python -m sidekick.clients.omnifocus get-task n--Q40q4juK

# Create task
python -m sidekick.clients.omnifocus create-task "Review documentation"
python -m sidekick.clients.omnifocus create-task "Send report" --note "Include Q1 metrics"
python -m sidekick.clients.omnifocus create-task "Team meeting" --due 2026-02-10 --flag

# Update task
python -m sidekick.clients.omnifocus update-task n--Q40q4juK --name "Updated title"
python -m sidekick.clients.omnifocus update-task n--Q40q4juK --flag
python -m sidekick.clients.omnifocus update-task n--Q40q4juK --due 2026-02-15

# Complete task
python -m sidekick.clients.omnifocus complete-task n--Q40q4juK

# Delete task
python -m sidekick.clients.omnifocus delete-task n--Q40q4juK

# List projects and tags
python -m sidekick.clients.omnifocus list-projects
python -m sidekick.clients.omnifocus list-tags
```

#### Dropbox Commands

```bash
# Get file contents
python -m sidekick.clients.dropbox get-file-contents /Documents/notes.txt
python -m sidekick.clients.dropbox get-file-contents-from-link "https://www.dropbox.com/s/abc123/file.txt"

# Write file contents
echo "Hello, World!" | python -m sidekick.clients.dropbox write-file-contents /Documents/notes.txt
python -m sidekick.clients.dropbox write-file-contents /Documents/notes.txt --content "Hello, World!"

# Get metadata
python -m sidekick.clients.dropbox get-metadata /Documents/notes.txt

# Get Paper doc contents
python -m sidekick.clients.dropbox get-paper-contents /Paper/MyDoc.paper
python -m sidekick.clients.dropbox get-paper-contents /Paper/MyDoc.paper --format html
python -m sidekick.clients.dropbox get-paper-contents-from-link "https://paper.dropbox.com/doc/Title-abc123"

# Create/update Paper docs
echo "# My Document" | python -m sidekick.clients.dropbox create-paper-contents /Paper/NewDoc.paper
python -m sidekick.clients.dropbox create-paper-contents /Paper/NewDoc.paper --content "# Title"
python -m sidekick.clients.dropbox update-paper-contents /Paper/MyDoc.paper --content "# Updated"
```

#### Gmail Commands

```bash
# Search messages
python -m sidekick.clients.gmail search "from:someone@example.com"
python -m sidekick.clients.gmail search "is:unread" 20

# Get message
python -m sidekick.clients.gmail get MESSAGE_ID

# Create draft
python -m sidekick.clients.gmail create-draft "user@example.com" "Subject" "Body text"
```

**Python Usage:**
```python
from sidekick.clients.gmail import GmailClient
from sidekick.config import get_google_config

config = get_google_config()
client = GmailClient(**config)

# Search messages
messages = client.search_messages("from:boss@example.com", max_results=5)
for msg in messages:
    headers = client.get_message_headers(msg)
    print(f"{headers['from']}: {headers['subject']}")

# Read message body
message = client.get_message("MESSAGE_ID")
body = client.get_message_body(message)

# Create draft
draft = client.create_draft(
    to="recipient@example.com",
    subject="Hello",
    body="This is a draft",
    cc="cc@example.com"
)
```

#### Google Calendar Commands

```bash
# List events
python -m sidekick.clients.gcalendar list "2024-01-01T00:00:00Z" "2024-01-31T23:59:59Z"

# Get event
python -m sidekick.clients.gcalendar get EVENT_ID

# Create event
python -m sidekick.clients.gcalendar create "Team Meeting" "2024-01-15T14:00:00Z" "2024-01-15T15:00:00Z"

# Update event
python -m sidekick.clients.gcalendar update EVENT_ID summary "New Title"

# Delete event
python -m sidekick.clients.gcalendar delete EVENT_ID
```

#### Google Sheets Commands

```bash
# List spreadsheets
python -m sidekick.clients.gsheets list 20

# Get spreadsheet info (by ID or URL)
python -m sidekick.clients.gsheets get "SPREADSHEET_ID"
python -m sidekick.clients.gsheets get-url "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit"

# Download as CSV (by ID or URL)
python -m sidekick.clients.gsheets download "SPREADSHEET_ID" "Sheet1" output.csv
python -m sidekick.clients.gsheets download-url "https://docs.google.com/.../edit" "Sheet1" output.csv

# Upload CSV
python -m sidekick.clients.gsheets upload data.csv "My Spreadsheet"

# Replace sheet with CSV
python -m sidekick.clients.gsheets replace "SPREADSHEET_ID" data.csv "Sheet1"
```

**Python Usage:**
```python
from sidekick.clients.gsheets import GSheetsClient
from sidekick.config import get_google_config

config = get_google_config()
client = GSheetsClient(**config)

# List spreadsheets
spreadsheets = client.list_spreadsheets(max_results=20)
for sheet in spreadsheets:
    print(f"{sheet['name']}: {sheet['id']}")

# Get by URL
url = "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit"
spreadsheet = client.get_spreadsheet_by_url(url)

# Extract ID from URL
spreadsheet_id = GSheetsClient.extract_spreadsheet_id(url)

# Download as CSV
csv_content = client.download_as_csv(
    spreadsheet_id="SPREADSHEET_ID",
    sheet_name="Sheet1",
    output_path="output.csv"
)

# Upload CSV
spreadsheet = client.upload_csv(
    csv_path="data.csv",
    title="My Spreadsheet"
)

# Replace sheet
client.replace_sheet_with_csv(
    spreadsheet_id="SPREADSHEET_ID",
    csv_path="data.csv",
    sheet_name="Sheet1"
)

# Get values
values = client.get_values("SPREADSHEET_ID", "Sheet1!A1:D10")
```

## Saving Output with Prompts

Save command output with prompt metadata for easy tracking and refreshing:

```bash
# Save with auto-generated filename from prompt
python -m sidekick.clients.jira roadmap-hierarchy PROJ-1735 PROJ | \
  python -m sidekick.clients.output write \
    "Find roadmap items nested under PROJ-1735 in the PROJ Project" \
    jira \
    "roadmap-hierarchy PROJ-1735 PROJ"
# Saves to: output/jira/proj-1735-roadmap-items.txt

# Refresh existing output (preserves creation timestamp)
python -m sidekick.clients.jira roadmap-hierarchy PROJ-1735 PROJ | \
  python -m sidekick.clients.output write \
    "Find roadmap items nested under PROJ-1735 in the PROJ Project" \
    jira \
    "roadmap-hierarchy PROJ-1735 PROJ" \
    --refresh

# List saved outputs
python -m sidekick.clients.output list jira

# Find outputs by prompt text
python -m sidekick.clients.output find jira "PROJ-1735"
```

**Features:**
- Auto-generated filenames from prompts (e.g., `proj-1735-roadmap-items.txt`)
- Prompt text and command stored in file header
- Creation and update timestamps
- Searchable by prompt text
- Refresh capability to update existing files

See `.claude/skills/output.md` for detailed documentation.

### Simple Output Redirect

You can also use simple file redirection:

```bash
# Save roadmap hierarchy
python -m sidekick.clients.jira roadmap-hierarchy PROJ-1735 PROJ > output/jira/2025-01-27_PROJ-1735_hierarchy.txt

# Quick command with today's date
TODAY=$(date +%Y-%m-%d)
python -m sidekick.clients.jira roadmap-hierarchy PROJ-100 PROJ > output/jira/${TODAY}_PROJ-100.txt
```

**Output Location:**
- Files are saved in `output/<client>/` directories (e.g., `output/jira/`)
- These files are not checked into git
- See `output/README.md` for naming guidelines

## Running Agents

Agents are multi-step workflows that coordinate multiple clients. Invoke them by asking Claude to execute the agent workflow:

```bash
# Weekly Report Agent - Generate summary from 1:1 and meeting docs
claude code "Run the weekly report agent for the past week"
```

Agents are defined in `.claude/agents/` as markdown files that describe the workflow steps. See `output/README.md` for examples of manual agent invocation.

### Available Agents

- **weekly_report** (`.claude/agents/weekly_report.md`) - Generate weekly summary from 1:1 and meeting docs

## Configuration

Configuration is loaded from `.env` file (with fallback to environment variables).

### Getting Google OAuth2 Credentials

For Gmail, Google Calendar, and Google Sheets, use the provided helper script:

```bash
# Run the interactive token generator
python3 tools/get_google_refresh_token.py
```

This script will:
1. Guide you through creating OAuth2 credentials in Google Cloud Console
2. Open your browser to authorize the app
3. Generate a refresh token that works for all three services (Gmail, Calendar, Sheets)
4. Show you the exact lines to add to your `.env` file

### Configuration File

Create a `.env` file in the project root (see `.env.example`):

```bash
# Atlassian Configuration (works for both JIRA and Confluence)
ATLASSIAN_URL=https://your-company.atlassian.net
ATLASSIAN_EMAIL=your-email@company.com
ATLASSIAN_API_TOKEN=your_api_token

# User Configuration (for 1:1 docs and personalized features)
USER_NAME=Chase
USER_EMAIL=your-email@company.com

# Team Group Configuration (optional)
TEAMS_GROUP_PROJECTS=PROJ1,PROJ2,PROJ3
TEAMS_GROUP_JQL=project IN ("PROJ1", "PROJ2", "PROJ3")

# OmniFocus Configuration (optional, macOS only)
# Leave commented for inbox-only workflow
# OMNIFOCUS_DEFAULT_PROJECT=Work
# OMNIFOCUS_DEFAULT_TAG=from-cli

# Dropbox Configuration
DROPBOX_ACCESS_TOKEN=your_dropbox_access_token

# Google Services Configuration (Gmail, Calendar, Sheets)
# See .env.example for detailed setup instructions
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REFRESH_TOKEN=your_google_refresh_token
```

**Get Atlassian API Token**: https://id.atlassian.com/manage-profile/security/api-tokens
**Get Dropbox Access Token**: https://www.dropbox.com/developers/apps (create app → generate token)
**Get Google OAuth2 Credentials**: Run `python3 tools/get_google_refresh_token.py` (interactive setup)

Configuration priority:
1. `.env` file (preferred)
2. System environment variables (fallback)

**Note**: Legacy `JIRA_*` variables are still supported for backward compatibility.

## Project Structure

```
chase-sidekick/
├── .claude/               # Claude Code configuration
│   ├── settings.json     # Claude Code settings
│   ├── settings.local.json  # Local Claude Code settings
│   ├── skills/           # Usage documentation
│   │   ├── jira.md       # JIRA skill docs
│   │   ├── jira-roadmap.md  # JIRA roadmap skill docs
│   │   ├── confluence.md # Confluence skill docs
│   │   ├── omnifocus.md  # OmniFocus skill docs (macOS)
│   │   ├── dropbox.md    # Dropbox skill docs
│   │   ├── gmail.md      # Gmail skill docs
│   │   ├── gcalendar.md  # Google Calendar skill docs
│   │   ├── gsheets.md    # Google Sheets skill docs
│   │   ├── output.md     # Output management skill docs
│   │   └── team-group-analysis.md  # Team analysis skill docs
│   └── agents/           # Multi-step workflows
│       └── weekly_report.md  # Weekly report agent
├── sidekick/
│   ├── config.py          # Configuration from .env
│   └── clients/           # Service clients (single files)
│       ├── jira.py       # JIRA client with CLI
│       ├── confluence.py # Confluence client with CLI
│       ├── omnifocus.py  # OmniFocus client with CLI (macOS)
│       ├── dropbox.py    # Dropbox client with CLI
│       ├── gmail.py      # Gmail client with CLI
│       ├── gcalendar.py  # Google Calendar client with CLI
│       ├── gsheets.py    # Google Sheets client with CLI
│       └── output.py     # Output manager with CLI
├── output/                # Saved command outputs (not in git)
│   ├── jira/             # JIRA outputs
│   ├── confluence/       # Confluence outputs
│   ├── weekly_report/    # Weekly report agent outputs
│   └── README.md         # Output guidelines
├── tools/                 # Helper scripts
│   └── get_google_refresh_token.py  # OAuth2 token generator
├── .env                   # Your credentials (not in git)
├── .env.example          # Example configuration
└── README.md
```

## Available Skills

- **JIRA** (`.claude/skills/jira.md`) - Query and manage JIRA issues
  - Query issues with JQL, by parent, or by label
  - Get detailed issue information
  - Add and remove labels
  - Update issue fields
- **JIRA Roadmap** (`.claude/skills/jira-roadmap.md`) - Explore roadmap hierarchies and initiative breakdowns
  - Depth-first traversal with children appearing immediately under parents
  - Streams results as they're fetched for immediate feedback
  - Recursively finds all children and linked issues
- **Confluence** (`.claude/skills/confluence.md`) - Manage Confluence pages and 1:1 docs
  - Search pages by title or CQL queries
  - Read and write page content
  - Create page hierarchies with automatic version handling
  - **1:1 Doc Management**: Add topics to 1:1 meeting docs with automatic search, validation, and section management
  - Search caching for faster repeated access
- **OmniFocus** (`.claude/skills/omnifocus.md`) - Manage OmniFocus tasks (macOS only)
  - Query and filter tasks by project, tag, due date, and status
  - Create, update, complete, and delete tasks
  - List projects and tags
  - Inbox-focused workflow with duplicate prevention
- **Dropbox** (`.claude/skills/dropbox.md`) - Manage Dropbox files and Paper docs
  - Get and write file contents (any file type)
  - Get file contents via share links
  - Get metadata for files and folders
  - Export Paper docs as markdown or HTML
  - Create and update Paper docs from markdown or HTML
  - Content-focused operations (stdin/stdout, no local file I/O)
- **Gmail** (`.claude/skills/gmail.md`) - Search and manage Gmail messages
  - Search inbox with Gmail query syntax
  - Read full message details and body
  - Create draft emails (does not send)
  - Extract headers and message metadata
- **Google Calendar** (`.claude/skills/gcalendar.md`) - Manage Google Calendar events
  - List events with date range filtering
  - Create, update, and delete calendar events
  - Support for all-day and timed events
  - Manage event attendees and locations
- **Google Sheets** (`.claude/skills/gsheets.md`) - Manage Google Sheets with CSV
  - List all accessible spreadsheets
  - Get spreadsheet info by ID or URL
  - Download sheets as CSV files (by ID or URL)
  - Upload CSV files as new spreadsheets
  - Replace sheet contents with CSV data
  - Read and write cell values programmatically
- **Output** (`.claude/skills/output.md`) - Save command output with prompt metadata
  - Auto-generates filenames from prompts
  - Stores prompt text, command, and timestamps in file headers
  - Searchable and refreshable outputs
  - Organized by client type

## Available Agents

- **Weekly Report** (`.claude/agents/weekly_report.md`) - Generate weekly summary from 1:1 and meeting docs
  - Fetches content from Confluence and Dropbox Paper docs
  - Extracts notes from recent time period
  - Categorizes by audience (leadership, direct reports, everyone, kudos)
  - Preserves outputs in `output/weekly_report/` for review

## Roadmap

- [x] JIRA client with CLI
- [x] Confluence client with CLI
- [x] OmniFocus client with CLI
- [x] Dropbox client with CLI
- [x] Gmail client with CLI
- [x] Google Calendar client with CLI
- [x] Google Sheets client with CLI
- [ ] Slack client with CLI
- [ ] GitHub client with CLI
- [ ] Zoom client with CLI
- [ ] Apple Notes client with CLI