---
name: jira-roadmap
description: Explore JIRA roadmap hierarchies recursively
argument-hint: <root-issue> [project] [issue-type]
allowed-tools: Bash, Read
---

# JIRA Roadmap Skill

Find and visualize roadmap initiatives by recursively exploring issue hierarchies.

When invoked, use Atlassian Rovo MCP first to handle the request: $ARGUMENTS

## Primary Path: Atlassian Rovo MCP

- Fetch the root issue with Rovo search/JQL and then fetch details by returned Atlassian resource ID when available.
- Use Rovo JQL searches for children, for example `parent = PROJ-123`, scoped by project or issue type when requested.
- Repeat child queries until the requested hierarchy depth is covered, tracking visited issue keys to avoid loops.
- For writes such as labeling or parent changes, use Rovo update tools after the normal remote-write confirmation rule is satisfied.

Use the local roadmap commands only when Rovo is unavailable, lacks the needed hierarchy detail, local streaming tree output is specifically useful, debugging the local client, or the user explicitly asks for the local client.

## Sidekick CLI Fallback Commands

### Roadmap Hierarchy
```bash
python3 -m sidekick.clients.jira roadmap-hierarchy <root-issue> [project] [issue-type]
```

Recursively fetch and display an issue hierarchy tree.

**Arguments:**
- `<root-issue>` - Starting issue key (e.g., `PROJ-123`)
- `[project]` - Optional: Project key to filter by (e.g., `PROJ`)
- `[issue-type]` - Optional: Filter by issue type (e.g., `Story`, `Epic`)

### Label Roadmap
```bash
python3 -m sidekick.clients.jira label-roadmap <root-issue> [project] [--dry-run] [--limit N]
```

Automatically label issues in a roadmap hierarchy based on their prefix ancestry.

## Example Usage

When the user asks to:
- "Show me the roadmap for PROJ-100" - Use roadmap-hierarchy PROJ-100 PROJ
- "Find all stories under EPIC-200" - Use roadmap-hierarchy EPIC-200 PROJ Story
- "What's the hierarchy for this initiative?" - Use roadmap-hierarchy with the issue key
- "Label the roadmap issues" - Use label-roadmap with appropriate options

## Features

- **Streaming Results**: Iterator yields results as they're fetched
- **Recursive Traversal**: Automatically finds children at all nesting levels
- **Link Following**: Follows issue links (blocks, relates to, depends on, etc.)
- **Loop Prevention**: Tracks visited issues to prevent infinite loops
- **Project Scoping**: Stays within specified project
- **Type Filtering**: Optional filtering by issue type
- **Tree Visualization**: Clear hierarchical tree structure

For full documentation, see the detailed JIRA Roadmap skill documentation in this folder.
