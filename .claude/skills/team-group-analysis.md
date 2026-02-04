# Group Analysis

Analyze completed work across multiple JIRA projects organized into "groups" with automatic theme categorization.

## Overview

This skill helps engineering managers understand what their teams have accomplished by:
- Querying multiple JIRA projects as a logical group
- Filtering for specific work types (e.g., issues not in Epics)
- Categorizing work into themes automatically
- Generating counts per theme and per team

## Configuration

Groups are configured in your `.env` file (not checked into git) to keep team structure private.

### Setup

Add group configuration to `.env`:

```bash
# Define a group called "myteam" with three projects
MYTEAM_GROUP_PROJECTS=PROJ1,PROJ2,PROJ3
MYTEAM_GROUP_JQL=project IN ("PROJ1", "PROJ2", "PROJ3")

# Optional: Define additional groups
BACKEND_GROUP_PROJECTS=API,CORE,DATA
FRONTEND_GROUP_PROJECTS=WEB,MOBILE
```

**Format:**
- `<GROUPNAME>_GROUP_PROJECTS`: Comma-separated list of JIRA project keys
- `<GROUPNAME>_GROUP_JQL`: (Optional) Custom JQL snippet for the group
  - If not provided, automatically generated from project list

### Example Configurations

**Single Project:**
```bash
MOBILE_GROUP_PROJECTS=MOBILE
# Auto-generates: project = "MOBILE"
```

**Multiple Projects:**
```bash
PLATFORM_GROUP_PROJECTS=API,INFRA,TOOLS
# Auto-generates: project IN ("API", "INFRA", "TOOLS")
```

**Custom JQL:**
```bash
CRITICAL_GROUP_PROJECTS=PROD,OPS
CRITICAL_GROUP_JQL=project IN ("PROD", "OPS") AND priority = Highest
```

## Usage

### Step 1: Query Issues

Query completed issues from your group:

```bash
# Issues completed in last 90 days that are NOT in an Epic
python3 -m sidekick.clients.jira query \
  'project IN ("PROJ1", "PROJ2", "PROJ3") AND resolved >= -90d AND parent is EMPTY' \
  > team_completed_90days.txt

# Or use other filters:
# Last 30 days
python3 -m sidekick.clients.jira query \
  'project IN ("PROJ1", "PROJ2", "PROJ3") AND resolved >= -30d AND parent is EMPTY' \
  > team_completed_30days.txt

# Specific date range
python3 -m sidekick.clients.jira query \
  'project IN ("PROJ1", "PROJ2", "PROJ3") AND resolved >= "2024-01-01" AND resolved <= "2024-03-31" AND parent is EMPTY' \
  > team_q1_2024.txt

# All work (including Epic children)
python3 -m sidekick.clients.jira query \
  'project IN ("PROJ1", "PROJ2", "PROJ3") AND resolved >= -90d' \
  > team_all_work_90days.txt
```

**Common JQL Patterns:**
- `resolved >= -90d` - Last 90 days
- `resolved >= -30d` - Last 30 days
- `parent is EMPTY` - Exclude issues in Epics
- `status = Done` - Only "Done" status
- `assignee was currentUser()` - Your work

### Step 2: Analyze Themes

Create an analysis script to categorize work into themes:

```python
#!/usr/bin/env python3
"""Analyze group issues and categorize into themes."""
import re
from collections import defaultdict

def categorize_issue(issue):
    """Categorize based on summary and labels."""
    summary_lower = issue['summary'].lower()
    labels = [l.lower() for l in issue['labels']]

    # Check labels first
    if 'quarantine' in labels:
        return 'Test Fixes & Quarantine'
    if 'sprites' in labels or 'sprites' in summary_lower:
        return 'Sprites & Reviews'
    if 'cx-escalations' in labels:
        return 'CX Escalations'

    # Check summary patterns
    if 'oncall' in summary_lower:
        return 'Oncall Support'
    if any(word in summary_lower for word in ['onboarding', 'training']):
        return 'Onboarding & Training'
    if any(word in summary_lower for word in ['spike', 'docs', 'documentation']):
        return 'Documentation & Spikes'
    if any(word in summary_lower for word in ['bug', 'fix', 'error']):
        return 'Bug Fixes'
    if 'sev' in summary_lower:
        return 'Severity Issues'

    return 'Feature Work'

# Parse and analyze...
```

See `analyze_themes.py` in the project root for a complete example.

### Step 3: Run Analysis

```bash
python3 analyze_themes.py
```

**Example Output:**

```
Total Issues: 50

Theme Breakdown:
  Feature Work                          9 ( 18.0%)
  Sprites & Reviews                     8 ( 16.0%)
  Documentation & Spikes                6 ( 12.0%)
  Test Fixes & Quarantine               6 ( 12.0%)
  Onboarding & Training                 5 ( 10.0%)
  Oncall Support                        5 ( 10.0%)
  CX Escalations                        3 (  6.0%)
```

## Python API Usage

```python
from sidekick.config import get_group, get_groups
from sidekick.clients.jira import JiraClient

# Get all configured groups
groups = get_groups()
print(groups)
# {'myteam': {'projects': ['PROJ1', 'PROJ2', 'PROJ3'], 'jql': 'project IN ("PROJ1", "PROJ2", "PROJ3")'}}

# Get specific group
myteam_config = get_group('myteam')
print(myteam_config['jql'])
# 'project IN ("PROJ1", "PROJ2", "PROJ3")'

# Use in queries
client = JiraClient(...)
jql = f"{myteam_config['jql']} AND resolved >= -90d AND parent is EMPTY"
result = client.query_issues(jql)
```

## Analysis Patterns

### Theme Categories

Common theme categories to track:

1. **Feature Work** - New functionality and enhancements
2. **Bug Fixes** - Defect resolution
3. **Test Fixes & Quarantine** - Flaky test resolution
4. **Oncall Support** - Incident response and support rotations
5. **CX Escalations** - Customer-facing issues
6. **Documentation & Spikes** - Research and documentation
7. **Onboarding & Training** - Team development
8. **Technical Debt** - Refactoring and cleanup
9. **Sprites & Reviews** - Code reviews and peer feedback
10. **Infrastructure** - DevOps and tooling

### Categorization Logic

Use a hierarchy of checks:

1. **Labels first** - Most explicit signal (e.g., `cx-escalations`)
2. **Keywords in summary** - Next best signal
3. **Issue type** - Story vs Bug vs Task
4. **Default category** - Catch-all for uncategorized

### Per-Team Metrics

Track themes by individual project to understand:
- Which teams focus on which work types
- Balance between feature work and maintenance
- Oncall burden distribution
- Customer escalation load

## Use Cases

### 1. Sprint/Quarter Retrospectives

**What did we accomplish this quarter?**

```bash
python3 -m sidekick.clients.jira query \
  'project IN ("PROJ1", "PROJ2", "PROJ3") AND resolved >= -90d AND parent is EMPTY' \
  | python3 analyze_themes.py
```

### 2. Team Balance Analysis

**Are we spending too much time on maintenance vs features?**

Look at theme percentages per team to identify:
- High test fix burden (technical debt)
- Excessive oncall load
- Imbalanced CX escalation distribution

### 3. Work Visibility

**Show non-Epic work that's "invisible" in roadmaps**

Many teams complete valuable work outside of Epics:
- Bug fixes
- Customer escalations
- Oncall support
- Test maintenance

This skill makes that work visible.

### 4. Capacity Planning

**How much capacity goes to unplanned work?**

Compare:
- Planned work (Epic children)
- Unplanned work (no parent)

Helps with future sprint planning and capacity allocation.

## Tips

### Exclude Noise

Adjust your JQL to exclude placeholder tickets:

```bash
'project IN ("X", "Y") AND resolved >= -90d AND parent is EMPTY AND summary !~ "placeholder"'
```

### Focus on Specific Work Types

```bash
# Only bugs
'... AND issuetype = Bug'

# Only stories and tasks
'... AND issuetype in (Story, Task)'

# Exclude cancelled work
'... AND status != Cancelled'
```

### Customize Themes

Modify `categorize_issue()` to match your team's work patterns:

```python
def categorize_issue(issue):
    # Add custom labels
    if 'security' in issue['labels']:
        return 'Security'

    # Add custom keywords
    if 'migration' in issue['summary'].lower():
        return 'Migrations'

    # Your existing logic...
```

### Compare Time Periods

```bash
# Q1 vs Q2
python3 -m sidekick.clients.jira query 'X AND resolved >= "2024-01-01" AND resolved <= "2024-03-31"' > q1.txt
python3 -m sidekick.clients.jira query 'X AND resolved >= "2024-04-01" AND resolved <= "2024-06-30"' > q2.txt
```

## Related Skills

- [JIRA Query](jira.md) - Basic JIRA querying
- [JIRA Roadmap](jira-roadmap.md) - Roadmap hierarchy analysis

## Why Groups?

**Problem:** Team structure and project mapping is often:
- Company-specific and confidential
- Changes over time
- Shouldn't be checked into public repos

**Solution:** Configure groups in `.env`:
- ✅ Not checked into git
- ✅ Easy to update as teams change
- ✅ Supports multiple group definitions
- ✅ Reusable across skills and scripts
