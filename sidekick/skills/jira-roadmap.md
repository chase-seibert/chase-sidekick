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

The implementation uses optimized depth-first traversal with smart caching:
1. **Depth-First**: Processes each issue and immediately traverses its descendants before moving to siblings
2. **Correct Nesting**: Children appear immediately under their parent in the output
3. **Streaming Results**: Issues are yielded as they're discovered
4. **Smart Caching**: Children fetched via parent query are cached, avoiding redundant fetches
5. **Batch Fetching**: Linked issues are batch fetched in a single query
6. **Memory Efficient**: Uses generators and doesn't build the entire tree in memory

## Limitations

- **Max Depth**: Recursion is limited to 10 levels deep to prevent infinite loops
- **Project Boundary**: If project is specified, only searches within that project. If omitted, traverses across all projects.
- **Max Results**: Fetches up to 100 children per parent issue
- **Link Types**: Follows all JIRA link types (blocks, relates to, depends on, etc.)

## Performance Notes

- **Streaming**: Results appear immediately as they're fetched from the API
- **Depth-First Traversal**: Children appear immediately under their parent in the output
- **Iterator Pattern**: Yields results as discovered, memory efficient
- **Optimized API Calls**: Smart caching and batching
  - Root: 1 fetch + 1 children query + 1 batch linked fetch = ~3 calls
  - Non-leaf: 0 fetch (cached) + 1 children query + 1 batch linked fetch = ~2 calls
  - Leaf: 0 fetch (cached) + 1 children query (empty) = ~1 call
  - **Average**: ~1.5-2 calls per issue (vs 2 calls without optimization)
  - **Savings**: Children are cached from parent queries, linked issues are batch fetched
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

## Label Roadmap Hierarchy

Automatically label issues in a roadmap hierarchy based on their prefix ancestry (e.g., C1, C1.1, C1.5.1).

### Command

```bash
python -m sidekick.clients.jira label-roadmap <root-issue> [project] [--dry-run] [--limit N]
```

**Arguments:**
- `<root-issue>` - Root issue key (must have valid prefix like C1, T1, etc.)
- `[project]` - Optional: Project key to filter by (e.g., `DBX`)
- `--dry-run` - Preview changes without applying
- `--limit N` - Stop after labeling N issues

### How It Works

The operation traverses the issue hierarchy depth-first and adds labels based on prefix ancestry:

1. **Root Validation**: Ensures root issue has valid prefix (e.g., C1)
2. **Prefix Extraction**:
   - Extracts prefixes from issue summaries using pattern matching
   - Matches: C1, C1.5, C1.5.1, T2, M7, etc.
   - Handles variations: "C1.", "C1 ", "C1: "
   - Issues without prefixes inherit their parent's labels
   - Issues with different prefix families (e.g., M7 in a C1 hierarchy) inherit parent labels plus their own prefix
3. **Label Assignment** based on depth:
   - **Depth 0-2**: All ancestor prefixes (1-3 labels)
   - **Depth 3**: Root + parent + self (3 labels max)
   - **Depth 4+**: Inherits parent's 3 labels (no prefix needed)
4. **Clone Filtering**: Automatically skips linked issues of type "clones"
5. **Optimization**: Skips issues that already have correct labels

### Label Examples

```
Issue Hierarchy:                  Labels Added:
DBX-1734 (C1)                    → [c1]
├─ DBX-1739 (C1.5)              → [c1, c1.5]
   ├─ DBX-3162 (C1.5.1)         → [c1, c1.5, c1.5.1]
      ├─ DBX-3737 (no prefix)   → [c1, c1.5, c1.5.1]      (inherited from parent)
      ├─ DBX-4059 (M7)          → [c1, c1.5, c1.5.1]      (inherited, M7 filtered out)
      ├─ DBX-4060 (C1.5.1.1)    → [c1, c1.5.1, c1.5.1.1]  (root + parent + self)
         ├─ DBX-5000 (no prefix)→ [c1, c1.5.1, c1.5.1.1]  (inherited from parent)
   ├─ DBX-3163 (C1.5.2)         → [c1, c1.5, c1.5.2]
      ├─ DBX-XXXX (no prefix)   → [c1, c1.5, c1.5.2]      (inherited from parent)
```

**Note**: Only prefixes matching the root family are used for labels. Cross-family issues (like M7 in a C1 hierarchy) inherit their parent's labels WITHOUT adding their own prefix.

### Usage Examples

**Preview changes (dry-run):**
```bash
python -m sidekick.clients.jira label-roadmap DBX-1734 DBX --dry-run
```

Output:
```
Labeling roadmap hierarchy for DBX-1734 in DBX (DRY RUN):

DBX-1734: C1. Unblock Team Growth...
  Current labels: []
  Labels to add: [c1]

DBX-1739: C1.5 Simplify Sharing
  Current labels: [c1]
  Labels to add: [c1.5]

DBX-3162: C1.5.1 Deprecate all legacy share modals
  Current labels: []
  Labels to add: [c1, c1.5, c1.5.1]

Summary: Processed 100 issues, labeled 85, skipped 15, 0 errors
```

**Label first 10 issues (incremental approach):**
```bash
python -m sidekick.clients.jira label-roadmap DBX-1734 DBX --limit 10
```

**Label entire hierarchy:**
```bash
python -m sidekick.clients.jira label-roadmap DBX-1734 DBX
```

### Best Practices

1. **Always test with --dry-run first**: Preview changes before applying
2. **Use --limit for large hierarchies**: Start with 10-20 issues to validate
3. **Verify root prefix**: Ensure root issue has valid prefix before running
4. **Monitor API calls**: Watch debug output for rate limiting concerns
5. **Incremental labeling**: Use multiple runs with --limit to gradually apply labels

### Edge Cases

- **Missing prefix at depth 0-3**: Issue skipped with warning
- **Different prefix family**: Issues with different prefix families are skipped (e.g., M7 is skipped when root is C1)
- **Missing prefix at depth 4+**: Inherits parent's labels (normal behavior)
- **Already has labels**: Skips issue (optimization, no API calls)
- **Invalid root prefix**: Exits with error before processing
- **API failures**: Logs error, increments error counter, continues processing

### Performance

- **Dry-run mode**: ~1.5-2 API calls per issue (hierarchy traversal only)
- **Real mode**: ~3.5-4 API calls per issue (traversal + label updates)
- **Large hierarchies**: Use --limit to process in batches

For 100 issues:
- Dry-run: ~150-200 API calls, ~20-30 seconds
- Real mode: ~350-400 API calls, ~45-60 seconds

## Related Commands

- `query-by-parent` - Get direct children only (no recursion)
- `query` - Use JQL for custom queries
- `get-issue` - Get details of a single issue
- `add-label` - Add a single label to an issue
- `remove-label` - Remove a label from an issue
