---
name: omnifocus
description: Manage OmniFocus tasks (macOS only)
argument-hint: <operation> [args]
allowed-tools: Bash, Read
---

# OmniFocus Skill

Command-line interface for OmniFocus task management.

**Platform:** macOS only

When invoked, use the OmniFocus client to handle the request: $ARGUMENTS

## Available Commands

### Query Tasks
```bash
python -m sidekick.clients.omnifocus query [--status inbox|active|completed] [--project NAME] [--tag NAME] [--flagged] [--limit N]
```

### Inbox Tasks
```bash
python -m sidekick.clients.omnifocus inbox [--limit N]
```

### Flagged Tasks
```bash
python -m sidekick.clients.omnifocus flagged [--limit N]
```

### Tasks by Project
```bash
python -m sidekick.clients.omnifocus by-project PROJECT_NAME [--limit N]
```

### Tasks by Tag
```bash
python -m sidekick.clients.omnifocus by-tag TAG_NAME [--limit N]
```

### Get Single Task
```bash
python -m sidekick.clients.omnifocus get-task TASK_ID
```

### Create Task
```bash
python -m sidekick.clients.omnifocus create "Task Name" [--note TEXT] [--project NAME] [--due YYYY-MM-DD] [--defer YYYY-MM-DD] [--tag NAME] [--flagged]
```

### Update Task
```bash
python -m sidekick.clients.omnifocus update TASK_ID [--name TEXT] [--note TEXT] [--project NAME] [--due YYYY-MM-DD] [--flagged yes|no]
```

### Complete Task
```bash
python -m sidekick.clients.omnifocus complete TASK_ID
```

### Delete Task
```bash
python -m sidekick.clients.omnifocus delete TASK_ID
```

### List Projects
```bash
python -m sidekick.clients.omnifocus list-projects
```

### List Tags
```bash
python -m sidekick.clients.omnifocus list-tags
```

## Key Features

- **Inbox-Focused**: Defaults to working with inbox tasks only
- **Duplicate Prevention**: Automatically prevents creating duplicate tasks
- **Smart Date Handling**: Only shows dates that are actually set
- **Non-Completed Default**: All queries exclude completed tasks unless explicitly requested

## Example Usage

When the user asks to:
- "Show me my OmniFocus inbox" - Use inbox command
- "What tasks are flagged?" - Use flagged command
- "Create a task to review documentation" - Use create command
- "Complete this task" - Use complete command with task ID

For full documentation, see the detailed OmniFocus skill documentation in this folder.
