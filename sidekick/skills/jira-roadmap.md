# JIRA Roadmap Skill

Find and visualize roadmap initiatives by recursively exploring issue hierarchies.

## Overview

This skill helps you explore JIRA roadmap initiatives by starting from a root issue and recursively finding all children, nested children, linked issues, and descendants within a project. Perfect for understanding Epic hierarchies, Initiative breakdowns, nested Story structures, and cross-issue dependencies.

## Configuration

Uses the same `.env` configuration as the main JIRA skill. See `jira.md` for setup instructions.

## Command

### Roadmap Hierarchy

Recursively fetch and display an issue hierarchy tree.

```bash
python3 sidekick/clients/jira.py roadmap-hierarchy <root-issue> <project> [issue-type]
```

**Arguments:**
- `<root-issue>` - Starting issue key (e.g., `DBX-123`)
- `<project>` - Project key to stay within (e.g., `DBX`)
- `[issue-type]` - Optional: Filter results by issue type (e.g., `Story`, `Epic`, `Task`)

**Examples:**

```bash
# Get all issues under DBX-100 in the DBX project
python3 sidekick/clients/jira.py roadmap-hierarchy DBX-100 DBX

# Get only Story issues in the hierarchy
python3 sidekick/clients/jira.py roadmap-hierarchy DBX-100 DBX Story

# Get only Epic issues in the hierarchy
python3 sidekick/clients/jira.py roadmap-hierarchy DBX-100 DBX Epic
```

**Output format:**

Results stream as they're fetched:

```
Roadmap hierarchy for DBX-100 in DBX:

DBX-100: Q1 Platform Improvements [In Progress] (John Doe) [platform]
├─ DBX-101: API Performance [In Progress] (Jane Smith) [backend, api]
├─ DBX-102: Optimize database queries [Done] (Bob Johnson) [backend]
├─ DBX-103: Add caching layer [In Progress] (Alice Brown) [backend]
├─ DBX-104: Frontend Refactor [To Do] (Jane Smith) [frontend]
├─ DBX-105: Update component library [To Do] (Carol White) [frontend]
├─ DBX-106: Improve state management [To Do] (Dave Black) [frontend]
├~> DBX-150: Security audit [In Progress] (Bob Johnson) [security]
├─ DBX-107: Documentation Updates [Done] (Unassigned) [docs]
├─ DBX-108: API documentation [Done] (Eve Green) [docs]

Total: 10 issues
```

**Legend:**
- `├─` / `└─` - Parent-child relationship (subtask, child issue)
- `├~>` / `└~>` - Linked issue relationship (blocks, relates to, etc.)

## Use Cases

### 1. Roadmap Planning

Visualize your roadmap structure:

```bash
python3 sidekick/clients/jira.py roadmap-hierarchy DBX-1000 DBX
```

This shows the complete initiative breakdown from the root issue down through all Epics, Stories, and Subtasks.

### 2. Epic Breakdown Review

See all Stories under an Epic:

```bash
python3 sidekick/clients/jira.py roadmap-hierarchy DBX-500 DBX Story
```

This filters to only show Story-type issues in the hierarchy, giving you a clear view of the Epic's Story breakdown.

### 3. Initiative Tracking

Track a large initiative with multiple levels:

```bash
python3 sidekick/clients/jira.py roadmap-hierarchy DBX-2000 DBX
```

Shows the full tree of the initiative, including nested Epics, Stories, and Subtasks.

### 4. Cross-Team Coordination

When multiple teams work on related issues:

```bash
# See all issues under a shared parent
python3 sidekick/clients/jira.py roadmap-hierarchy DBX-3000 DBX
```

Useful for understanding dependencies and relationships across teams working in the same project.

## Features

- **Streaming Results**: Iterator yields results as they're fetched for immediate feedback
- **Recursive Traversal**: Automatically finds children at all nesting levels
- **Link Following**: Follows issue links (blocks, relates to, depends on, etc.)
- **Loop Prevention**: Tracks visited issues to prevent infinite loops
- **Project Scoping**: Stays within the specified project (e.g., only DBX issues)
- **Type Filtering**: Optional filtering by issue type (Story, Epic, Task, Bug, etc.)
- **Tree Visualization**: Clear hierarchical tree structure with visual connectors
- **Live Counting**: Shows issue count as they're discovered
- **Status Display**: Shows status, assignee, and labels for each issue

## Python Usage

**Important**: `get_issue_hierarchy()` returns an iterator that yields results as it traverses the hierarchy. This provides immediate feedback and better performance for large hierarchies.

```python
from sidekick.clients.jira import JiraClient

client = JiraClient(
    base_url="https://company.atlassian.net",
    email="you@company.com",
    api_token="your-token"
)

# Iterate through hierarchy - results stream as they're fetched
count = 0
for item in client.get_issue_hierarchy("DBX-100", "DBX"):
    issue = item["issue"]
    depth = item["depth"]
    relationship = item["relationship"]  # "root", "child", or "linked"

    indent = "  " * depth
    print(f"{indent}{issue['key']}: {issue['fields']['summary']}")
    count += 1

print(f"\nTotal: {count} issues")

# Filter by issue type
for item in client.get_issue_hierarchy("DBX-100", "DBX", issue_type="Story"):
    print(f"{item['issue']['key']} at depth {item['depth']}")

# Collect all issues into a list (if needed)
all_items = list(client.get_issue_hierarchy("DBX-100", "DBX"))
print(f"Collected {len(all_items)} issues")

# Process only root and first-level children
for item in client.get_issue_hierarchy("DBX-100", "DBX"):
    if item["depth"] <= 1:
        print(item["issue"]["key"])
```

### Iterator Item Structure

Each yielded item is a dict with:
- `issue`: Full issue data from JIRA API
- `depth`: Integer depth in hierarchy (0 = root)
- `relationship`: String indicating relationship type:
  - `"root"` - The starting issue
  - `"child"` - Parent-child relationship
  - `"linked"` - Issue link relationship
- `parent_key`: Parent issue key (or None for root)

### Performance Benefits

The iterator approach provides:
- **Immediate results**: See issues as they're fetched, no waiting for entire hierarchy
- **Memory efficient**: Processes one level at a time, doesn't build large in-memory tree
- **Batched queries**: Fetches all issues at same level together (major performance win)
- **Early termination**: Can stop iteration early if you find what you need
- **Progress feedback**: Can show progress indicators as you iterate

### Query Optimization

The implementation uses breadth-first traversal with batching:
1. **Level-by-level**: Processes all issues at depth 0, then depth 1, etc.
2. **Batch issue fetch**: `key IN (KEY1, KEY2, ...)` to get multiple issues in one call
3. **Batch children fetch**: `parent IN (KEY1, KEY2, ...)` to get all children in one call
4. **Dramatic reduction**: From 2N API calls to ~2L calls (where L = max depth)

## Limitations

- **Max Depth**: Recursion is limited to 10 levels deep to prevent infinite loops
- **Project Boundary**: Only searches within the specified project
- **Max Results**: Fetches up to 100 children per parent issue
- **Link Types**: Follows all JIRA link types (blocks, relates to, depends on, etc.)

## Performance Notes

- **Streaming**: Results appear immediately as they're fetched from the API
- **Optimized Queries**: Uses breadth-first traversal with batched queries
  - Old approach: 2 API calls per issue (2N total)
  - New approach: 1-2 API calls per hierarchy level (~2L total, where L is depth)
  - Example: 100 issues at depth 5 = ~10 API calls vs 200 calls
- **Batching**: Fetches all issues at the same level in one query, all children in one query
- **Large Hierarchies**: Efficient for 100+ issues due to batching
- **Early Exit**: In Python, you can break from the loop early if you find what you need

## Tips

1. **Start High**: Begin with the highest-level issue (Initiative or Epic) to see the full breakdown
2. **Filter Types**: Use issue type filtering to focus on specific levels (e.g., only Stories)
3. **Project Scope**: Always specify the correct project to avoid missing cross-project links
4. **Status Review**: Use the output to quickly scan status across the entire initiative

## Common Issue Types

- `Epic` - Large feature or initiative
- `Story` - User story or feature requirement
- `Task` - Work item or technical task
- `Bug` - Defect or issue
- `Subtask` - Child task of a Story or Task
- `Initiative` - High-level strategic goal (if enabled in your JIRA)

## Related Commands

- `query-by-parent` - Get direct children only (no recursion)
- `query` - Use JQL for custom queries
- `get-issue` - Get details of a single issue
