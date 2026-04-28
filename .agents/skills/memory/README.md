# Memory Skill

Manage command memory files with prompt metadata and auto-generated filenames.

## Overview

The Memory Skill provides a systematic way to save command results with:
- **Prompt metadata**: Original prompt text stored in file header
- **Timestamps**: Creation and last updated timestamps
- **Auto-generated filenames**: Slugified prompts as filenames
- **Refresh capability**: Update existing files while preserving creation time
- **Search**: Find files by prompt text

## Example Prompts

Natural language prompts that work with this skill:

```
"Save the roadmap for PROJ-1735 in the PROJ project"
"Refresh the PROJ-1735 roadmap memory"
"Show me all saved JIRA memories"
"Find saved memories mentioning PROJ-1735"
```

## Output File Format

Files are saved with YAML frontmatter containing metadata:

```
---
prompt: Find roadmap items nested under PROJ-1735 in the PROJ Project
client: jira
command: roadmap-hierarchy PROJ-1735 PROJ
created: 2025-01-27 14:30:22
updated: 2025-01-27 15:45:10
---

[actual command output here]
```

## Filename Generation

Filenames are auto-generated from prompts using slug format:

- `"Find roadmap items nested under PROJ-1735 in the PROJ Project"` → `dbx-1735-roadmap-items.txt`
- `"Show me the hierarchy for PROJ-500"` → `proj-500-hierarchy.txt`
- `"Get all Story issues under EPIC-200"` → `epic-200-story-issues.txt`
- `"Meeting prep for C1 review"` (with --md) → `meeting-prep-c1-review.md`

**Rules:**
- Lowercase
- Extract issue keys (PROJ-1735, PROJ-500, etc.)
- Remove common words (the, in, for, and, etc.)
- Replace spaces with hyphens
- Limit to ~50 characters
- Remove special characters
- Default extension is .txt, use --md flag for .md extension

## Commands

### Write Memory (with pipe)

Save command output with prompt metadata:

```bash
# Auto-generated filename
python -m sidekick.clients.jira roadmap-hierarchy PROJ-1735 PROJ | \
  python -m sidekick.clients.memory write \
    "Find roadmap items nested under PROJ-1735 in the PROJ Project" \
    jira \
    "roadmap-hierarchy PROJ-1735 PROJ"

# Custom filename
python -m sidekick.clients.jira query "project = PROJ" | \
  python -m sidekick.clients.memory write \
    "Query all PROJ issues" \
    jira \
    "query project = PROJ" \
    proj-all-issues

# Refresh existing file (preserves creation timestamp)
python -m sidekick.clients.jira roadmap-hierarchy PROJ-1735 PROJ | \
  python -m sidekick.clients.memory write \
    "Find roadmap items nested under PROJ-1735 in the PROJ Project" \
    jira \
    "roadmap-hierarchy PROJ-1735 PROJ" \
    --refresh

# Save as Markdown file (for formatted reports)
cat meeting-prep-report.md | \
  python -m sidekick.clients.memory write \
    "Meeting prep for C1 review" \
    meeting-prep \
    "meeting-prep" \
    --md
```

**Arguments:**
- `<prompt>`: The prompt text (in quotes)
- `<client>`: Client name (jira, slack, github, meeting-prep, etc.)
- `<command>`: The command that was executed
- `[filename]`: Optional custom filename (without extension)
- `[--refresh]`: Preserve creation timestamp from existing file
- `[--md]`: Save as Markdown (.md) instead of plain text (.txt)

### List Outputs

List all saved memories for a client:

```bash
python -m sidekick.clients.memory list jira
```

Output:
```
Memories for jira (3 files):

dbx-1735-roadmap-items.txt
  Prompt: Find roadmap items nested under PROJ-1735 in the PROJ Project
  Updated: 2025-01-27 15:45:10

proj-500-hierarchy.txt
  Prompt: Show me the hierarchy for PROJ-500
  Updated: 2025-01-27 14:20:33

epic-200-story-issues.txt
  Prompt: Get all Story issues under EPIC-200
  Updated: 2025-01-27 13:15:22
```

### Find Memories

Find memories by searching prompt text:

```bash
python -m sidekick.clients.memory find jira "PROJ-1735"
python -m sidekick.clients.memory find jira "roadmap"
python -m sidekick.clients.memory find jira "Story issues"
```

### Generate Slug (for testing)

Test slug generation from a prompt:

```bash
python -m sidekick.clients.memory slug "Find roadmap items nested under PROJ-1735"
# Output: dbx-1735-roadmap-items
```

## Use Cases

### 1. Save and Track Roadmap Snapshots

```bash
# Initial save
python -m sidekick.clients.jira roadmap-hierarchy PROJ-1735 PROJ | \
  python -m sidekick.clients.memory write \
    "PROJ-1735 roadmap snapshot" \
    jira \
    "roadmap-hierarchy PROJ-1735 PROJ"

# Refresh after changes
python -m sidekick.clients.jira roadmap-hierarchy PROJ-1735 PROJ | \
  python -m sidekick.clients.memory write \
    "PROJ-1735 roadmap snapshot" \
    jira \
    "roadmap-hierarchy PROJ-1735 PROJ" \
    --refresh

# Compare versions
diff memory/jira/dbx-1735-roadmap-snapshot.txt memory/jira/dbx-1735-roadmap-snapshot.txt.bak
```

### 2. Save Query Results

```bash
# Save open issues
python -m sidekick.clients.jira query "project = PROJ AND status = Open" | \
  python -m sidekick.clients.memory write \
    "PROJ open issues" \
    jira \
    "query project = PROJ AND status = Open"

# Save backend issues
python -m sidekick.clients.jira query-by-label backend PROJ | \
  python -m sidekick.clients.memory write \
    "PROJ backend issues" \
    jira \
    "query-by-label backend PROJ"
```

### 3. Periodic Updates

```bash
# Daily roadmap refresh script
#!/bin/bash
TODAY=$(date +%Y-%m-%d)
python -m sidekick.clients.jira roadmap-hierarchy PROJ-1735 PROJ | \
  python -m sidekick.clients.memory write \
    "PROJ-1735 roadmap $TODAY" \
    jira \
    "roadmap-hierarchy PROJ-1735 PROJ"
```

### 4. Search and Review

```bash
# Find all memories about a specific issue
python -m sidekick.clients.memory find jira "PROJ-1735"

# List recent memories
python -m sidekick.clients.memory list jira | head -20

# View specific memory
cat memory/jira/dbx-1735-roadmap-items.txt
```

## Python Usage

```python
from sidekick.clients.memory import MemoryManager

manager = MemoryManager()

# Write output
content = "Issue output content..."
file_path = manager.write_memory(
    prompt="Find roadmap items nested under PROJ-1735",
    client="jira",
    command="roadmap-hierarchy PROJ-1735 PROJ",
    content=content
)
print(f"Saved to: {file_path}")

# Refresh existing file
file_path = manager.write_memory(
    prompt="Find roadmap items nested under PROJ-1735",
    client="jira",
    command="roadmap-hierarchy PROJ-1735 PROJ",
    content=updated_content,
    refresh=True  # Preserves creation timestamp
)

# List memories
memories = manager.list_memories("jira")
for file_path, metadata in memories:
    print(f"{file_path.name}: {metadata.get('prompt')}")

# Find by prompt
matches = manager.find_by_prompt("jira", "PROJ-1735")
for file_path in matches:
    print(f"Found: {file_path}")

# Generate slug
slug = manager.generate_slug("Find roadmap items nested under PROJ-1735")
print(f"Slug: {slug}")  # dbx-1735-roadmap-items
```

## Shell Helpers

Add to your `.bashrc` or `.zshrc` for easier usage:

```bash
# Save JIRA memory with prompt
jira-save() {
    local prompt="$1"
    local cmd="$2"
    shift 2
    python -m sidekick.clients.jira $cmd "$@" | \
      python -m sidekick.clients.memory write "$prompt" jira "$cmd $*"
}

# Refresh JIRA memory
jira-refresh() {
    local prompt="$1"
    local cmd="$2"
    shift 2
    python -m sidekick.clients.jira $cmd "$@" | \
      python -m sidekick.clients.memory write "$prompt" jira "$cmd $*" --refresh
}

# Usage:
# jira-save "PROJ-1735 roadmap" roadmap-hierarchy PROJ-1735 PROJ
# jira-refresh "PROJ-1735 roadmap" roadmap-hierarchy PROJ-1735 PROJ
```

## File Organization

```
memory/
├── jira/
│   ├── dbx-1735-roadmap-items.txt
│   ├── proj-500-hierarchy.txt
│   ├── epic-200-story-issues.txt
│   └── proj-open-issues.txt
├── slack/        # Future
└── github/       # Future
```

## Benefits

1. **Searchable**: Find memories by prompt text
2. **Traceable**: Know when memories were created and last updated
3. **Reproducible**: Command is stored in metadata for easy re-execution
4. **Organized**: Auto-generated filenames follow consistent pattern
5. **Refreshable**: Update memories while preserving creation time
6. **Diffable**: Compare different versions to track changes

## Tips

1. **Be descriptive in prompts**: The prompt becomes your search key
2. **Use refresh for periodic updates**: Preserve creation timestamp
3. **Custom filenames for important memories**: Override auto-generation when needed
4. **Search before creating**: Check if similar memory already exists
5. **Regular cleanup**: Archive or delete old memories you no longer need
