# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chase Sidekick is an engineering manager task automation toolkit. The project provides:

- **Clients**: Single-file Python interfaces to external services (JIRA, Slack, etc.)
- **Skills**: Markdown documentation showing command-line usage patterns
- **Agents**: (Future) Scripts that coordinate multiple clients for complex workflows

### Design Philosophy

1. **Zero Dependencies**: Use Python stdlib only (no external packages)
2. **Single-File Clients**: Each service client is one .py file (e.g., jira.py, slack.py)
3. **CLI Built-In**: Each client has a `main()` function for command-line usage via `python3 -m`
4. **Skills as Docs**: Skills are markdown files documenting how to use clients
5. **Simple Config**: Environment variables only, no config files

## Development Commands

### Setup

```bash
# Create .env file with credentials
cp .env.example .env
# Edit .env with your actual credentials
```

### Running JIRA Client

Configuration is automatically loaded from `.env` file. Output uses a readable microformat:

```bash
# Get issue (detailed view)
python -m sidekick.clients.jira get-issue PROJ-123
# PROJ-123: Fix login bug
#   Status: In Progress
#   Assignee: John Doe

# Query issues (one-line per issue)
python -m sidekick.clients.jira query "project = PROJ"
# Found 42 issues (showing 50):
# PROJ-123: Fix login bug [In Progress] (John Doe) [backend, bug]
# PROJ-124: Add dark mode [To Do] (Jane Smith) [frontend]

# Query by parent
python -m sidekick.clients.jira query-by-parent PROJ-100

# Query by label
python -m sidekick.clients.jira query-by-label backend

# Get roadmap hierarchy (recursive children + linked issues)
python -m sidekick.clients.jira roadmap-hierarchy PROJ-100 PROJ
python -m sidekick.clients.jira roadmap-hierarchy PROJ-100 PROJ Story

# Update issue
python -m sidekick.clients.jira update-issue PROJ-123 '{"summary": "New"}'

# Add label to issue
python -m sidekick.clients.jira add-label PROJ-123 needs-review

# Remove label from issue
python -m sidekick.clients.jira remove-label PROJ-123 needs-review
```

### Python Module Usage

```python
from sidekick.clients.jira import JiraClient

client = JiraClient(
    base_url="https://company.atlassian.net",
    email="you@company.com",
    api_token="your-token"
)

# Get single issue (returns all fields)
issue = client.get_issue("PROJ-123")

# Query with default fields
result = client.query_issues("project = PROJ")

# Query with custom fields
result = client.query_issues(
    "project = PROJ",
    fields=["key", "summary", "priority"]
)

# Add a label to an issue
client.add_label("PROJ-123", "needs-review")

# Remove a label from an issue
client.remove_label("PROJ-123", "needs-review")
```

**Note**: `query_issues` and related methods accept a `fields` parameter to specify which fields to return from the API. Default fields are: `key`, `summary`, `status`, `assignee`, `labels`, `issuetype`, `description`.

## Architecture

```
sidekick/
├── config.py          # Configuration from .env file
├── clients/           # Service clients (single-file implementations)
│   └── jira.py       # JIRA client with CLI
├── skills/           # Usage documentation (markdown)
│   └── jira.md       # JIRA skill documentation
└── agents/           # Future: Multi-client coordination scripts
```

### Key Patterns

- **Configuration**: Use `config.py` to load from `.env` file (with fallback to environment variables)
- **Direct Script Execution**: Run clients directly with `python -m sidekick.clients.jira` - no module installation needed
- **Standard Exceptions**: Use built-in Python exceptions (ValueError, RuntimeError, ConnectionError)
- **Dictionary Returns**: Return dicts instead of custom classes for simplicity
- **Inline Auth**: Auth logic in the client class, no separate auth module

### Adding New Clients

When adding a new service client (e.g., Slack, GitHub):

1. Create single-file client in `sidekick/clients/{service}.py`
2. Implement client class with service API methods
3. Add `main()` function for CLI usage
4. Create skill documentation in `sidekick/skills/{service}.md`
5. Add config function to `config.py` if needed
6. Update README.md with new service
