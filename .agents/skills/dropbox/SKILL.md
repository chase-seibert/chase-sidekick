---
name: dropbox
description: Manage Dropbox files and Paper docs
argument-hint: <operation> [args]
allowed-tools: Bash, Read
---

# Dropbox Skill

Final fallback command-line interface for Dropbox file and Paper doc operations.

Prefer Dropbox MCP (`dropbox-mcp`) for Paper reads, edits, comments, and thread resolution when it is available:

- Use `paper_read_document` for Paper reads by URL, file ID, or pad ID.
- Use `paper_resolve_doc_ref` only when a canonical ID is needed without reading the full document.
- For Paper edits or comments, call `paper_read_document` first and pass returned receipts to Dropbox MCP write tools.

## Paper Access Precedence

For Dropbox Paper reads and writes, use this fallback order:

1. Dropbox MCP (`dropbox-mcp`) when it can perform the needed read or write.
2. Chrome plugin/live Paper editor when Dropbox MCP is unavailable, lacks the needed operation, or browser-authenticated Paper access is the safer path.
3. This skill and `sidekick.clients.dropbox` only when Dropbox MCP and Chrome plugin paths are unavailable or unsuitable and `DROPBOX_ACCESS_TOKEN` is set.

Use this skill and `sidekick.clients.dropbox` only when the fallback order above permits it, standalone local-client execution is specifically needed, debugging the local client, or the user explicitly asks for the local client.

When invoked, use the Dropbox client to handle the request: $ARGUMENTS

**Note:** Dropbox commands return Markdown by default for Paper documents. Use `--html` flag only if you need raw HTML for content manipulation.
**Write caution:** `update-paper-contents` replaces the full Paper doc body. Prefer Dropbox MCP receipts or the Chrome plugin/live editor for targeted Paper edits.

## Available Commands

### Get File Contents
```bash
python -m sidekick.clients.dropbox get-file-contents /path/to/file.txt
```

### Export from Shared Link

Download file content directly from a shared link. **Primary use: accessing team space files you don't own.**

This is the ONLY way to get Paper doc content you don't own.

**For Paper docs:** Returns Markdown by default. Use `--html` flag only if you need raw HTML for content manipulation.

Example:
```bash
# Export Paper doc (returns Markdown by default)
python -m sidekick.clients.dropbox export-shared-link "https://www.dropbox.com/s/abc123/Doc.paper?dl=0"

# For HTML (content manipulation):
python -m sidekick.clients.dropbox export-shared-link "https://www.dropbox.com/s/abc123/Doc.paper?dl=0" --html
```

Use `get-paper-contents` for Paper docs you own when doing read-write workflows.

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
