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

### Get File from Share Link
```bash
python -m sidekick.clients.dropbox get-file-contents-from-link "https://www.dropbox.com/s/..."
```

### Write File Contents
```bash
python -m sidekick.clients.dropbox write-file-contents /path/to/file.txt [--content "text"]
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
- "Download a file from this Dropbox link" - Use get-file-contents-from-link
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
