# OmniFocus Skill

Command-line interface for OmniFocus task management.

**Default Behavior**: Focuses on inbox tasks only and automatically excludes completed tasks.

## Platform Requirements

**macOS only** - OmniFocus is a macOS/iOS application. This client requires:
- macOS operating system
- OmniFocus 3+ installed
- Automation permissions granted

## Setup

### 1. Install OmniFocus

Download from: https://www.omnigroup.com/omnifocus

### 2. Grant Automation Permissions

When you first run a command, macOS will prompt for automation permissions. Grant access in:

**System Settings > Privacy & Security > Automation**

Enable automation for Terminal (or your terminal app) to control OmniFocus.

## Configuration

Configuration is **optional**. By default, tasks are created in the inbox with no tags or project.

If you want to set defaults, create a `.env` file in project root:
```bash
# OmniFocus Configuration (optional - leave commented for inbox-only workflow)
# OMNIFOCUS_DEFAULT_PROJECT=Work
# OMNIFOCUS_DEFAULT_TAG=from-cli
```

**Recommendation**: Leave these commented out for the simplest workflow (inbox-only).

## Key Features

- **Inbox-Focused**: Defaults to working with inbox tasks only
- **Duplicate Prevention**: Automatically prevents creating duplicate tasks with the same name
- **Smart Date Handling**: Only shows dates that are actually set (no placeholder dates)
- **Non-Completed Default**: All queries exclude completed tasks unless explicitly requested

## Commands

All commands use the module form (`python -m sidekick.clients.omnifocus`).

### Get Single Task

```bash
python -m sidekick.clients.omnifocus get-task <task-id>
```

Example:
```bash
python -m sidekick.clients.omnifocus get-task n--Q40q4juK
```

Displays task details in readable format:
```
n--Q40q4juK: Review documentation
  Status: Active
  Project: Work
  Tags: urgent, review
  Flagged: Yes
  Due: 2026-02-10
  Defer: 2026-02-05
  Note: Review the new API documentation and provide feedback...
```

### Query Tasks

Query tasks with flexible filters (defaults to inbox, non-completed tasks):

```bash
python -m sidekick.clients.omnifocus query [OPTIONS]
```

**Default Behavior**: Queries inbox tasks only, automatically excludes completed tasks.

**Options:**
- `--status inbox|active|completed|all` - Filter by status (default: inbox)
- `--project NAME` - Filter by project name
- `--tag NAME` - Filter by tag name
- `--flagged` - Show only flagged tasks
- `--due-before YYYY-MM-DD` - Tasks due before date
- `--due-after YYYY-MM-DD` - Tasks due after date
- `--limit N` - Maximum results (default: 50)

**Examples:**

```bash
# All inbox tasks (default)
python -m sidekick.clients.omnifocus query

# Tasks in specific project (non-completed)
python -m sidekick.clients.omnifocus query --status active --project Work

# Flagged tasks due this week
python -m sidekick.clients.omnifocus query --flagged --due-before 2026-02-07

# Tasks with specific tag
python -m sidekick.clients.omnifocus query --tag urgent

# Completed tasks (must explicitly request)
python -m sidekick.clients.omnifocus query --status completed --limit 10
```

Output format:
```
Found 3 tasks:
n--Q40q4juK: Review documentation [Flagged] [Work] [urgent, review] [due: 2026-02-10]
m-0P9ja3kL: Update tests [Active] [Work] [testing]
p-8Xjd02mN: Write report [Active] [Work] [due: 2026-02-15]
```

### Inbox Tasks

Get tasks in your inbox (not assigned to any project):

```bash
python -m sidekick.clients.omnifocus inbox
python -m sidekick.clients.omnifocus inbox --limit 10
```

Output:
```
Inbox tasks (5):
n--Q40q4juK: Process emails [Active]
m-0P9ja3kL: Call dentist [Active]
...
```

### Flagged Tasks

Get all flagged tasks:

```bash
python -m sidekick.clients.omnifocus flagged
python -m sidekick.clients.omnifocus flagged --limit 10
```

Output:
```
Flagged tasks (3):
n--Q40q4juK: Review documentation [Flagged] [Work] [urgent, review] [due: 2026-02-10]
m-0P9ja3kL: Submit report [Flagged] [Work] [due: 2026-02-08]
...
```

### Tasks by Project

Get all tasks in a specific project:

```bash
python -m sidekick.clients.omnifocus by-project <project-name>
python -m sidekick.clients.omnifocus by-project Work --limit 20
```

Example:
```bash
python -m sidekick.clients.omnifocus by-project "Work"
```

Output:
```
Tasks in 'Work' (8):
n--Q40q4juK: Review documentation [Flagged] [Work] [urgent, review] [due: 2026-02-10]
m-0P9ja3kL: Update tests [Active] [Work] [testing]
...
```

### Tasks by Tag

Get all tasks with a specific tag:

```bash
python -m sidekick.clients.omnifocus by-tag <tag-name>
python -m sidekick.clients.omnifocus by-tag urgent --limit 20
```

Example:
```bash
python -m sidekick.clients.omnifocus by-tag urgent
```

Output:
```
Tasks with tag 'urgent' (4):
n--Q40q4juK: Review documentation [Flagged] [Work] [urgent, review] [due: 2026-02-10]
p-8Xjd02mN: Fix bug [Active] [Work] [urgent, bug]
...
```

### Create Task

Create a new task in your inbox:

```bash
python -m sidekick.clients.omnifocus create <name> [OPTIONS]
```

**Duplicate Prevention**: Automatically checks if a task with the same name already exists and prevents creating duplicates.

**Options:**
- `--note TEXT` - Task note/description
- `--project NAME` - Assign to project
- `--due YYYY-MM-DD` - Due date
- `--defer YYYY-MM-DD` - Defer date (start date)
- `--tag NAME` - Add tag (can be used multiple times)
- `--flagged` - Flag the task

**Examples:**

```bash
# Simple task in inbox
python -m sidekick.clients.omnifocus create "Review documentation"

# Task with project and due date
python -m sidekick.clients.omnifocus create "Submit report" \
  --project Work \
  --due 2026-02-15 \
  --flagged

# Task with all options
python -m sidekick.clients.omnifocus create "Prepare presentation" \
  --note "Include Q4 metrics and projections" \
  --project Work \
  --due 2026-02-20 \
  --defer 2026-02-15 \
  --tag urgent \
  --tag presentation \
  --flagged
```

Output:
```
Created task: n--Q40q4juK: Submit report
```

**Note**: If you have `OMNIFOCUS_DEFAULT_PROJECT` or `OMNIFOCUS_DEFAULT_TAG` set in `.env`, they will be automatically applied unless you override with `--project` or `--tag`.

### Update Task

Update an existing task:

```bash
python -m sidekick.clients.omnifocus update <task-id> [OPTIONS]
```

**Options:**
- `--name TEXT` - Change task name
- `--note TEXT` - Change task note
- `--project NAME` - Move to different project
- `--due YYYY-MM-DD` - Change due date
- `--defer YYYY-MM-DD` - Change defer date
- `--flagged yes|no` - Change flagged status

**Examples:**

```bash
# Change task name
python -m sidekick.clients.omnifocus update n--Q40q4juK --name "Review API documentation"

# Update due date
python -m sidekick.clients.omnifocus update n--Q40q4juK --due 2026-02-15

# Move to different project and flag
python -m sidekick.clients.omnifocus update n--Q40q4juK \
  --project "Personal" \
  --flagged yes

# Update multiple properties
python -m sidekick.clients.omnifocus update n--Q40q4juK \
  --name "Complete report" \
  --note "Include all sections" \
  --due 2026-02-20
```

Output:
```
Updated task: n--Q40q4juK
```

### Complete Task

Mark a task as complete:

```bash
python -m sidekick.clients.omnifocus complete <task-id>
```

Example:
```bash
python -m sidekick.clients.omnifocus complete n--Q40q4juK
```

Output:
```
Completed task: n--Q40q4juK
```

### Delete Task

Delete (drop) a task:

```bash
python -m sidekick.clients.omnifocus delete <task-id>
```

Example:
```bash
python -m sidekick.clients.omnifocus delete n--Q40q4juK
```

Output:
```
Deleted task: n--Q40q4juK
```

### List Projects

List all projects:

```bash
python -m sidekick.clients.omnifocus list-projects
```

Output:
```
Projects (5):
  Work [active]
  Personal [active]
  Learning [active]
  Archive [on hold]
  Someday [dropped]
```

### List Tags

List all tags:

```bash
python -m sidekick.clients.omnifocus list-tags
```

Output:
```
Tags (8):
  urgent
  review
  waiting
  meeting
  email
  phone
  errands
  from-cli
```

## Task IDs

OmniFocus uses persistent IDs like `n--Q40q4juK` to identify tasks. These IDs are stable and won't change even if you rename or move the task.

**Getting Task IDs:**
- Use any query command (inbox, flagged, by-project, by-tag, query)
- Task ID is the first part of the output line before the colon

Example:
```bash
# Get inbox tasks to see their IDs
python -m sidekick.clients.omnifocus inbox

# Output shows IDs:
# n--Q40q4juK: Review documentation [Active]
# m-0P9ja3kL: Call dentist [Active]
```

Copy the ID (e.g., `n--Q40q4juK`) to use with get-task, update, complete, or delete commands.

## Python Usage

Use the OmniFocus client in your Python scripts:

```python
from sidekick.clients.omnifocus import OmniFocusClient

# Initialize client (with optional defaults)
client = OmniFocusClient(
    default_project="Work",
    default_tag="from-script"
)

# Get single task
task = client.get_task("n--Q40q4juK")
print(f"Task: {task['name']}")
print(f"Due: {task['dueDate']}")

# Query tasks
tasks = client.query_tasks(
    status="active",
    project="Work",
    flagged=True,
    limit=10
)
for task in tasks:
    print(f"{task['id']}: {task['name']}")

# Get inbox tasks
inbox = client.get_inbox_tasks(limit=20)
print(f"Inbox has {len(inbox)} tasks")

# Get flagged tasks
flagged = client.get_flagged_tasks()

# Get tasks by project
work_tasks = client.get_tasks_by_project("Work", limit=50)

# Get tasks by tag
urgent = client.get_tasks_by_tag("urgent")

# Create task
new_task = client.create_task(
    name="Review pull request",
    note="PR #123 - Update authentication",
    project="Work",
    due_date="2026-02-15",
    tags=["review", "urgent"],
    flagged=True
)
print(f"Created: {new_task['id']}")

# Update task
client.update_task(
    "n--Q40q4juK",
    name="Updated task name",
    due_date="2026-02-20",
    flagged=False
)

# Complete task
client.complete_task("n--Q40q4juK")

# Delete task
client.delete_task("m-0P9ja3kL")

# List projects
projects = client.list_projects()
for project in projects:
    print(f"{project['name']} [{project['status']}]")

# List tags
tags = client.list_tags()
for tag in tags:
    print(tag['name'])
```

## Common Use Cases

### 1. Daily Inbox Review

Process inbox tasks and categorize them:

```bash
# See what's in inbox
python -m sidekick.clients.omnifocus inbox

# Move task to Work project
python -m sidekick.clients.omnifocus update n--Q40q4juK --project Work

# Add tags
python -m sidekick.clients.omnifocus update n--Q40q4juK --tag urgent

# Complete processed task
python -m sidekick.clients.omnifocus complete n--Q40q4juK
```

### 2. Check Today's Work

See what's due soon:

```bash
# Flagged tasks (your focus items)
python -m sidekick.clients.omnifocus flagged

# Tasks due this week
python -m sidekick.clients.omnifocus query --due-before 2026-02-07

# Work project tasks
python -m sidekick.clients.omnifocus by-project Work
```

### 3. Quick Task Capture

Add tasks quickly from command line:

```bash
# Quick inbox task
python -m sidekick.clients.omnifocus create "Call customer about feedback"

# Task with context
python -m sidekick.clients.omnifocus create "Review PR-456" \
  --project Work \
  --tag review \
  --due 2026-02-10
```

### 4. Batch Processing

Use Python for batch operations:

```python
from sidekick.clients.omnifocus import OmniFocusClient

client = OmniFocusClient()

# Get all overdue tasks
import datetime
today = datetime.date.today().isoformat()

overdue = client.query_tasks(
    status="active",
    due_before=today,
    limit=100
)

# Flag all overdue tasks
for task in overdue:
    client.update_task(task['id'], flagged=True)
    print(f"Flagged: {task['name']}")
```

### 5. Project Review

Check project health:

```bash
# List all projects
python -m sidekick.clients.omnifocus list-projects

# Review tasks in specific project
python -m sidekick.clients.omnifocus by-project "Q1 Goals"

# Get completed tasks for project
python -m sidekick.clients.omnifocus query \
  --status completed \
  --project "Q1 Goals" \
  --limit 20
```

## Tips

### Finding Task IDs

Always start with a query to get task IDs:

```bash
# List tasks to find ID
python -m sidekick.clients.omnifocus by-project Work

# Then use ID for operations
python -m sidekick.clients.omnifocus complete n--Q40q4juK
```

### Date Format

All dates use ISO format: `YYYY-MM-DD`
- Valid: `2026-02-15`
- Invalid: `02/15/2026`, `15-Feb-2026`

### Project and Tag Names

Use exact names (case-sensitive):
- Project name: `Work` not `work`
- Tag name: `urgent` not `Urgent`

Use quotes if names contain spaces:
```bash
python -m sidekick.clients.omnifocus by-project "Q1 Goals"
```

### Default Configuration

Set defaults in `.env` to speed up task creation:

```bash
OMNIFOCUS_DEFAULT_PROJECT=Work
OMNIFOCUS_DEFAULT_TAG=from-cli
```

Then creating tasks is simpler:
```bash
# This task will automatically go to Work project with from-cli tag
python -m sidekick.clients.omnifocus create "Review documentation"
```

### Automation Permissions

If you get "permission denied" errors:
1. Open **System Settings > Privacy & Security > Automation**
2. Find your terminal app (Terminal, iTerm, etc.)
3. Enable "OmniFocus" checkbox
4. Retry the command

## Troubleshooting

### "OmniFocus not available"

**Problem**: OmniFocus app is not installed or not accessible.

**Solution**:
- Install OmniFocus from https://www.omnigroup.com/omnifocus
- Ensure OmniFocus is not restricted by parental controls

### "Permission denied" or "not allowed"

**Problem**: macOS automation permissions not granted.

**Solution**:
1. Open **System Settings > Privacy & Security > Automation**
2. Enable your terminal app to control OmniFocus
3. Restart terminal and try again

### "osascript command not found"

**Problem**: Not running on macOS (osascript is macOS-only).

**Solution**: This client only works on macOS. OmniFocus is not available on other platforms.

### "Task not found"

**Problem**: Task ID is incorrect or task was deleted.

**Solution**:
- Run a query to get current task IDs
- Verify you copied the full task ID (e.g., `n--Q40q4juK`)

### "Project not found" / "Tag not found"

**Problem**: Project or tag name doesn't match exactly.

**Solution**:
- List projects: `python -m sidekick.clients.omnifocus list-projects`
- List tags: `python -m sidekick.clients.omnifocus list-tags`
- Use exact name (case-sensitive)

### "Invalid date format"

**Problem**: Date not in YYYY-MM-DD format.

**Solution**: Use ISO format, e.g., `2026-02-15`

## Limitations

- **macOS only** - OmniFocus is not available on other platforms
- **Local only** - Accesses local OmniFocus database, not OmniSync
- **No perspectives** - Cannot access custom perspectives (use query with filters instead)
- **No attachments** - Cannot read or add file attachments
- **Tag limitations** - Tags replace existing tags (doesn't append)

## Related Tools

- [JIRA Skill](jira.md) - Task tracking in JIRA
- [Confluence Skill](confluence.md) - Documentation management

## API Reference

This client uses JXA (JavaScript for Automation) and AppleScript to communicate with OmniFocus:
- **JXA**: Primary interface for reading and creating tasks
- **AppleScript**: Used for completing tasks (better compatibility)
- **osascript**: Command-line tool for executing scripts

No external dependencies required - uses only Python stdlib.
