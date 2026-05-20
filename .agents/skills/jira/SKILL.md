---
name: jira
description: Query and manage JIRA issues
argument-hint: <operation> [args]
allowed-tools: Bash, Read
---

# JIRA Skill

Rovo-first guide for JIRA operations, with the local Sidekick client kept as a fallback.

When invoked, use Atlassian Rovo MCP first to handle the request: $ARGUMENTS

## Primary Path: Atlassian Rovo MCP

- Natural-language discovery: use Rovo search.
- Explicit JQL: use Rovo JQL search.
- Issue details: fetch by returned Atlassian resource ID when available.
- Issue writes: use Rovo create, edit, transition, worklog, or link tools as appropriate, after the normal remote-write confirmation rule is satisfied.

Use the local Sidekick client only when Rovo is unavailable, lacks the needed operation, local cache/output behavior is specifically useful, debugging the client itself, or the user explicitly asks for the local client.

## Sidekick CLI Fallback Commands

### Query Issues
```bash
python3 -m sidekick.clients.jira query "JQL query" [max_results]
```

### Get Single Issue
```bash
python3 -m sidekick.clients.jira get-issue ISSUE-KEY
```

### Get Multiple Issues
```bash
python3 -m sidekick.clients.jira get-issues-bulk ISSUE-1 ISSUE-2 ISSUE-3
```

### Query by Parent
```bash
python3 -m sidekick.clients.jira query-by-parent PARENT-ISSUE [max_results]
```

### Query by Label
```bash
python3 -m sidekick.clients.jira query-by-label LABEL [project] [max_results]
```

### Update Issue
```bash
python3 -m sidekick.clients.jira update-issue ISSUE-KEY '{"field": "value"}'
```

### Add Label
```bash
python3 -m sidekick.clients.jira add-label ISSUE-KEY label-name
```

### Remove Label
```bash
python3 -m sidekick.clients.jira remove-label ISSUE-KEY label-name
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
