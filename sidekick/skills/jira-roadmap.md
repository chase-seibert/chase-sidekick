# JIRA Roadmap Skill

Find and visualize roadmap initiatives by recursively exploring issue hierarchies.

## Overview

This skill helps you explore JIRA roadmap initiatives by starting from a root issue and recursively finding all children, nested children, linked issues, and descendants within a project. Perfect for understanding Epic hierarchies, Initiative breakdowns, nested Story structures, and cross-issue dependencies.

## Setup

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## Configuration

Uses the same `.env` configuration as the main JIRA skill. See `jira.md` for setup instructions.

## Example Prompts

Natural language prompts that work with this skill:

```
"Find roadmap items nested under DBX-1735 in the DBX Project"
"Show me the hierarchy for PROJ-500 in PROJ"
"What issues are linked to TEAM-100 in the TEAM project?"
"Get all Story issues under EPIC-200 in EPIC"
"Find all issues under DBX-1735 across all projects"
"Show me the complete hierarchy for PROJ-500 without project filtering"
```

## Command

### Roadmap Hierarchy

Recursively fetch and display an issue hierarchy tree.

```bash
python -m sidekick.clients.jira roadmap-hierarchy <root-issue> [project] [issue-type]
```

**Arguments:**
- `<root-issue>` - Starting issue key (e.g., `DBX-123`)
- `[project]` - Optional: Project key to filter by (e.g., `DBX`). If omitted or "None", traverses across all projects.
- `[issue-type]` - Optional: Filter results by issue type (e.g., `Story`, `Epic`, `Task`)

**Examples:**

```bash
# Get all issues under DBX-100 in the DBX project
python -m sidekick.clients.jira roadmap-hierarchy DBX-100 DBX

# Get only Story issues in the hierarchy within DBX project
python -m sidekick.clients.jira roadmap-hierarchy DBX-100 DBX Story

# Get only Epic issues in the hierarchy within DBX project
python -m sidekick.clients.jira roadmap-hierarchy DBX-100 DBX Epic

# Get all issues under DBX-100 across all projects
python -m sidekick.clients.jira roadmap-hierarchy DBX-100

# Get all issues across all projects (use "None" to skip project param but specify issue type)
python -m sidekick.clients.jira roadmap-hierarchy DBX-100 None Story
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
python -m sidekick.clients.jira roadmap-hierarchy DBX-1000 DBX
```

This shows the complete initiative breakdown from the root issue down through all Epics, Stories, and Subtasks.

### 2. Epic Breakdown Review

See all Stories under an Epic:

```bash
python -m sidekick.clients.jira roadmap-hierarchy DBX-500 DBX Story
```

This filters to only show Story-type issues in the hierarchy, giving you a clear view of the Epic's Story breakdown.

### 3. Initiative Tracking

Track a large initiative with multiple levels:

```bash
python -m sidekick.clients.jira roadmap-hierarchy DBX-2000 DBX
```

Shows the full tree of the initiative, including nested Epics, Stories, and Subtasks.

### 4. Cross-Team Coordination

When multiple teams work on related issues:

```bash
# See all issues under a shared parent
python -m sidekick.clients.jira roadmap-hierarchy DBX-3000 DBX
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

# Iterate through hierarchy within a project - results stream as they're fetched
count = 0
for item in client.get_issue_hierarchy("DBX-100", project="DBX"):
    issue = item["issue"]
    depth = item["depth"]
    relationship = item["relationship"]  # "root", "child", or "linked"

    indent = "  " * depth
    print(f"{indent}{issue['key']}: {issue['fields']['summary']}")
    count += 1

print(f"\nTotal: {count} issues")

# Traverse across all projects (no project filter)
for item in client.get_issue_hierarchy("DBX-100"):
    print(f"{item['issue']['key']} at depth {item['depth']}")

# Filter by issue type within a project
for item in client.get_issue_hierarchy("DBX-100", project="DBX", issue_type="Story"):
    print(f"{item['issue']['key']} at depth {item['depth']}")

# Collect all issues into a list (if needed)
all_items = list(client.get_issue_hierarchy("DBX-100", project="DBX"))
print(f"Collected {len(all_items)} issues")

# Process only root and first-level children
for item in client.get_issue_hierarchy("DBX-100", project="DBX"):
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
- **Memory efficient**: Uses generators, doesn't build large in-memory tree
- **Depth-first ordering**: Children appear directly under their parent in output
- **Early termination**: Can stop iteration early if you find what you need
- **Progress feedback**: Can show progress indicators as you iterate

### Traversal Approach

The implementation uses depth-first traversal with recursive descent:
1. **Depth-First**: Processes each issue and immediately traverses its descendants before moving to siblings
2. **Correct Nesting**: Children appear immediately under their parent in the output
3. **Streaming Results**: Issues are yielded as they're discovered
4. **Per-Issue Queries**: Fetches each issue individually, then queries for its children
5. **Memory Efficient**: Uses generators and doesn't build the entire tree in memory

## Limitations

- **Max Depth**: Recursion is limited to 10 levels deep to prevent infinite loops
- **Project Boundary**: If project is specified, only searches within that project. If omitted, traverses across all projects.
- **Max Results**: Fetches up to 100 children per parent issue
- **Link Types**: Follows all JIRA link types (blocks, relates to, depends on, etc.)

## Performance Notes

- **Streaming**: Results appear immediately as they're fetched from the API
- **Depth-First Traversal**: Children appear immediately under their parent in the output
- **Iterator Pattern**: Yields results as discovered, memory efficient
- **API Calls**: Approximately 2 calls per issue (1 to fetch issue, 1 to query children)
  - For N issues: ~2N API calls
  - Trade-off: Correct parent-child nesting vs batching optimization
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
