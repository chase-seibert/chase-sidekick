---
name: jira-roadmap
description: Explore JIRA roadmap hierarchies recursively
argument-hint: <root-issue> [project] [issue-type]
allowed-tools: Bash, Read
---

# JIRA Roadmap Skill

Find and visualize roadmap initiatives by recursively exploring issue hierarchies.

When invoked, use the JIRA roadmap commands to handle the request: $ARGUMENTS

## Available Commands

### Roadmap Hierarchy
```bash
python -m sidekick.clients.jira roadmap-hierarchy <root-issue> [project] [issue-type]
```

Recursively fetch and display an issue hierarchy tree.

**Arguments:**
- `<root-issue>` - Starting issue key (e.g., `PROJ-123`)
- `[project]` - Optional: Project key to filter by (e.g., `PROJ`)
- `[issue-type]` - Optional: Filter by issue type (e.g., `Story`, `Epic`)

### Label Roadmap
```bash
python -m sidekick.clients.jira label-roadmap <root-issue> [project] [--dry-run] [--limit N]
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
