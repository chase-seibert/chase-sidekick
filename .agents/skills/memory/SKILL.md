---
name: memory
description: Manage command memory files with prompt metadata and auto-generated filenames
argument-hint: <operation> [args]
allowed-tools: Bash, Read, Write
---

# Memory Skill

Manage command memory files with prompt metadata and auto-generated filenames.

When invoked, use the Memory manager to handle the request: $ARGUMENTS

## Available Commands

### Write Output (with pipe)
```bash
command | python -m sidekick.clients.memory write "prompt text" CLIENT "command" [filename] [--refresh]
```

### List Outputs
```bash
python -m sidekick.clients.memory list CLIENT
```

### Find Outputs
```bash
python -m sidekick.clients.memory find CLIENT "search term"
```

### Generate Slug (for testing)
```bash
python -m sidekick.clients.memory slug "prompt text"
```

## Output File Format

Files are saved with YAML frontmatter containing metadata:

```
---
prompt: Find roadmap items nested under PROJ-1735
client: jira
command: roadmap-hierarchy PROJ-1735 PROJ
created: 2025-01-27 14:30:22
updated: 2025-01-27 15:45:10
---

[actual command output here]
```

## Filename Generation

Filenames are auto-generated from prompts using slug format:
- Lowercase
- Extract issue keys
- Remove common words
- Replace spaces with hyphens
- Limit to ~50 characters

## Example Usage

When the user asks to:
- "Save the roadmap for PROJ-1735" - Pipe command output to memory write
- "Show me all saved JIRA memories" - Use list jira
- "Find memories mentioning PROJ-1735" - Use find jira "PROJ-1735"
- "Refresh the PROJ-1735 roadmap memory" - Use write with --refresh flag

## Benefits

- **Searchable**: Find memories by prompt text
- **Traceable**: Know when memories were created and updated
- **Reproducible**: Command is stored for easy re-execution
- **Organized**: Auto-generated filenames follow consistent pattern
- **Refreshable**: Update memories while preserving creation time

For full documentation, see the detailed Memory skill documentation in this folder.
