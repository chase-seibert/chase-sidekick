# Chase Sidekick

Engineering manager task automation toolkit.

## Overview

Chase Sidekick automates engineering manager tasks by providing:
- **Clients**: Single-file Python interfaces to services (JIRA, Slack, etc.)
- **Skills**: Markdown documentation for command-line usage
- **Agents**: (Future) Scripts coordinating multiple clients for complex workflows

## Quick Start

### Setup

```bash
# Create configuration file
cp .env.example .env
# Edit .env with your JIRA credentials
# Get API token: https://id.atlassian.com/manage-profile/security/api-tokens
```

### Example Prompts

Here are some natural language prompts you can use:

```
"Find roadmap items nested under PROJ-1735 in the PROJ Project"
"Show me the hierarchy for PROJ-500"
"What issues are linked to TEAM-100?"
"Get all Story issues under EPIC-200 in the EPIC project"
"Find all issues under PROJ-1735 across all projects"
"Query issues with status Open in the PROJ project"
"Show me all backend issues in PROJ"
```

### Command Line Usage

Configuration is automatically loaded from `.env` file:

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

# Update issue
python -m sidekick.clients.jira update-issue PROJ-123 '{"summary": "New title"}'
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

See `sidekick/skills/output.md` for detailed documentation.

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

## Configuration

Configuration is loaded from `.env` file (with fallback to environment variables).

Create a `.env` file in the project root (see `.env.example`):

```bash
# Works for both JIRA and Confluence (same authentication)
ATLASSIAN_URL=https://your-company.atlassian.net
ATLASSIAN_EMAIL=your-email@company.com
ATLASSIAN_API_TOKEN=your_api_token
```

**Get API Token**: https://id.atlassian.com/manage-profile/security/api-tokens

Configuration priority:
1. `.env` file (preferred)
2. System environment variables (fallback)

**Note**: Legacy `JIRA_*` variables are still supported for backward compatibility.

## Project Structure

```
chase-sidekick/
├── sidekick/
│   ├── config.py          # Configuration from .env
│   ├── clients/           # Service clients (single files)
│   │   ├── jira.py       # JIRA client with CLI
│   │   ├── confluence.py # Confluence client with CLI
│   │   └── output.py     # Output manager with CLI
│   ├── skills/           # Usage documentation
│   │   ├── jira.md       # JIRA skill docs
│   │   ├── jira-roadmap.md  # JIRA roadmap skill docs
│   │   ├── confluence.md # Confluence skill docs
│   │   └── output.md     # Output management skill docs
│   └── agents/           # Future: Multi-client scripts
├── output/                # Saved command outputs (not in git)
│   ├── jira/             # JIRA outputs
│   ├── confluence/       # Confluence outputs
│   └── README.md         # Output guidelines
├── .env                   # Your credentials (not in git)
├── .env.example          # Example configuration
└── README.md
```

## Available Skills

- **JIRA** (`sidekick/skills/jira.md`) - Query and manage JIRA issues
- **JIRA Roadmap** (`sidekick/skills/jira-roadmap.md`) - Explore roadmap hierarchies and initiative breakdowns
  - Depth-first traversal with children appearing immediately under parents
  - Streams results as they're fetched for immediate feedback
- **Confluence** (`sidekick/skills/confluence.md`) - Manage Confluence pages
  - Search pages by title or CQL queries
  - Read and write page content
  - Create page hierarchies with automatic version handling
- **Output** (`sidekick/skills/output.md`) - Save command output with prompt metadata
  - Auto-generates filenames from prompts
  - Stores prompt text, command, and timestamps in file headers
  - Searchable and refreshable outputs

## Roadmap

- [x] JIRA client with CLI
- [x] Confluence client with CLI
- [ ] Slack client with CLI
- [ ] GitHub client with CLI
- [ ] Google Calendar client with CLI
- [ ] Zoom client with CLI
- [ ] OmniFocus client with CLI
- [ ] Apple Notes client with CLI