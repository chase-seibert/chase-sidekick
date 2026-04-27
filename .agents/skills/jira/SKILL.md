---
name: jira
description: Query and manage JIRA issues
argument-hint: <operation> [args]
allowed-tools: Bash, Read
---

# JIRA Skill

Command-line interface for JIRA operations.

When invoked, use the JIRA client to handle the request: $ARGUMENTS

## Available Commands

### Query Issues
```bash
python -m sidekick.clients.jira query "JQL query" [max_results]
```

### Get Single Issue
```bash
python -m sidekick.clients.jira get-issue ISSUE-KEY
```

### Get Multiple Issues
```bash
python -m sidekick.clients.jira get-issues-bulk ISSUE-1 ISSUE-2 ISSUE-3
```

### Query by Parent
```bash
python -m sidekick.clients.jira query-by-parent PARENT-ISSUE [max_results]
```

### Query by Label
```bash
python -m sidekick.clients.jira query-by-label LABEL [project] [max_results]
```

### Update Issue
```bash
python -m sidekick.clients.jira update-issue ISSUE-KEY '{"field": "value"}'
```

### Add Label
```bash
python -m sidekick.clients.jira add-label ISSUE-KEY label-name
```

### Remove Label
```bash
python -m sidekick.clients.jira remove-label ISSUE-KEY label-name
```

## Common JQL Examples

- `project = PROJ` - All issues in project
- `status = Open` - All open issues
- `assignee = currentUser()` - Assigned to you
- `project = PROJ AND status = "In Progress"` - Specific project and status
- `labels = backend` - Issues with specific label
- `parent = PROJ-100` - Child issues of parent

## Example Usage

When the user asks to:
- "Show me my JIRA tickets" - Use query with assignee = currentUser()
- "Get details on PROJ-123" - Use get-issue
- "Find all bugs in the project" - Use query with issuetype = Bug
- "Add label 'needs-review' to PROJ-456" - Use add-label

For full documentation, see the detailed JIRA skill documentation in this folder.
