---
name: dropbox
description: Manage Dropbox files and Paper docs
argument-hint: <operation> [args]
allowed-tools: Bash, Read
---

# Dropbox Skill

Command-line interface for Dropbox file and Paper doc operations.

When invoked, use the Dropbox client to handle the request: $ARGUMENTS

## Available Commands

### Get File Contents
```bash
python -m sidekick.clients.dropbox get-file-contents /path/to/file.txt
```

### Export from Shared Link

Download file content directly from a shared link. **Primary use: accessing team space files you don't own.**

This is the ONLY way to get Paper doc content you don't own. However, for Paper docs, the returned HTML includes extensive CSS/formatting. Use `get-paper-contents` for Paper docs you own when doing read-write workflows.

```bash
# Team space Paper doc (read-only)
python -m sidekick.clients.dropbox export-shared-link "https://www.dropbox.com/s/abc123/file.txt?dl=0"
```

For a specific file in a shared folder:

```bash
python -m sidekick.clients.dropbox export-shared-link "https://www.dropbox.com/sh/xyz789/folder" --path "/subfolder/file.txt"
```

For password-protected links:

```bash
python -m sidekick.clients.dropbox export-shared-link "https://www.dropbox.com/s/abc123/file.txt?dl=0" --password "secret"
```

### Get Metadata
```bash
python -m sidekick.clients.dropbox get-metadata /path/to/file
```

### Get Paper Doc Contents
```bash
python -m sidekick.clients.dropbox get-paper-contents /Paper/Doc.paper [--format html|markdown]
```

### Get Paper Doc from Share Link
```bash
python -m sidekick.clients.dropbox get-paper-contents-from-link "https://paper.dropbox.com/doc/..."
```

### Create Paper Doc
```bash
python -m sidekick.clients.dropbox create-paper-contents /Paper/NewDoc.paper [--content "text"] [--format html|markdown]
```

### Update Paper Doc
```bash
python -m sidekick.clients.dropbox update-paper-contents /Paper/Doc.paper [--content "text"] [--format html|markdown]
```

## Example Usage

When the user asks to:
- "Read my meeting notes from Dropbox Paper" - Use get-paper-contents with the doc path
- "Download a file from this Dropbox link" - Use export-shared-link
- "Update my 1:1 doc with Bob" - Use update-paper-contents
- "Create a new Paper doc" - Use create-paper-contents

## Path Format

All Dropbox paths must:
- Start with a forward slash `/`
- Use forward slashes for directories
- Be case-sensitive

Examples:
- `/Documents/notes.txt`
- `/Paper/MyDoc.paper`

For full documentation, see the detailed Dropbox skill documentation in this folder.
