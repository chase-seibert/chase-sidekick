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

### Command Line Usage

Configuration is automatically loaded from `.env` file:

```bash
# Get single issue (detailed view)
python3 sidekick/clients/jira.py get-issue PROJ-123
# Output:
# PROJ-123: Fix login bug
#   Status: In Progress
#   Assignee: John Doe
#   Labels: backend, bug
#   Type: Bug

# Query issues (one per line)
python3 sidekick/clients/jira.py query "project = PROJ AND status = Open"
# Output:
# Found 42 issues (showing 50):
# PROJ-123: Fix login bug [In Progress] (John Doe) [backend, bug]
# PROJ-124: Add dark mode [To Do] (Jane Smith) [frontend]
# ...

# Query by parent (subtasks)
python3 sidekick/clients/jira.py query-by-parent PROJ-100

# Query by label
python3 sidekick/clients/jira.py query-by-label backend

# Get roadmap hierarchy (recursively find all children and linked issues)
python3 sidekick/clients/jira.py roadmap-hierarchy DBX-100 DBX
python3 sidekick/clients/jira.py roadmap-hierarchy DBX-100 DBX Story

# Update issue
python3 sidekick/clients/jira.py update-issue PROJ-123 '{"summary": "New title"}'
```

## Configuration

Configuration is loaded from `.env` file (with fallback to environment variables).

Create a `.env` file in the project root (see `.env.example`):

```bash
JIRA_URL=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your_api_token
```

**Get JIRA API Token**: https://id.atlassian.com/manage-profile/security/api-tokens

Configuration priority:
1. `.env` file (preferred)
2. System environment variables (fallback)

## Project Structure

```
chase-sidekick/
├── sidekick/
│   ├── config.py          # Configuration from .env
│   ├── clients/           # Service clients (single files)
│   │   └── jira.py       # JIRA client with CLI
│   ├── skills/           # Usage documentation
│   │   └── jira.md       # JIRA skill docs
│   └── agents/           # Future: Multi-client scripts
├── .env                   # Your credentials (not in git)
├── .env.example          # Example configuration
└── README.md
```

## Available Skills

- **JIRA** (`sidekick/skills/jira.md`) - Query and manage JIRA issues
- **JIRA Roadmap** (`sidekick/skills/jira-roadmap.md`) - Explore roadmap hierarchies and initiative breakdowns
  - Uses optimized batched queries (2L API calls vs 2N, where L=depth, N=issues)
  - Streams results as they're fetched for immediate feedback

## Roadmap

- [x] JIRA client with CLI
- [ ] Slack client with CLI
- [ ] GitHub client with CLI
- [ ] Google Calendar client with CLI
- [ ] Sprint planning agent
- [ ] Team metrics agent
