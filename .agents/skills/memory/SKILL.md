---
name: memory
description: Manage command memory files with prompt metadata and auto-generated filenames
argument-hint: <operation> [args]
allowed-tools: Bash, Read, Write
---

# Memory Skill

Manage command memory files with prompt metadata and auto-generated filenames.
Write every memory file directly under the root `memory/` directory. Do not create
client or skill subdirectories; the memory manager prefixes filenames with the
client name instead.

When invoked, use the Memory manager to handle the request: $ARGUMENTS

## Available Commands

### Write Output (with pipe)
```bash
command | python3 -m sidekick.clients.memory write "prompt text" CLIENT "command" [filename] [--refresh]
```

### List Outputs
```bash
python3 -m sidekick.clients.memory list CLIENT
```

### Find Outputs
```bash
python3 -m sidekick.clients.memory find CLIENT "search term"
```

### Generate Slug (for testing)
```bash
python3 -m sidekick.clients.memory slug "prompt text"
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

This report generated using [chase-sidekick](https://github.com/chase-seibert/chase-sidekick) and the [memory skill](https://github.com/chase-seibert/chase-sidekick/tree/main/.agents/skills/memory).
```

The standard report footer belongs at the bottom of the file body, not in the YAML frontmatter. If another skill generated the report content, link that primary skill instead of `memory`.

## Filename Generation

Filenames are auto-generated from prompts using slug format:
- Prefix with the client name, for example `jira-proj-1735-roadmap-items.txt`
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
