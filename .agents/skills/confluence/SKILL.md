---
name: confluence
description: Manage Confluence pages with search, read, and write operations
argument-hint: <operation> [args]
allowed-tools: Bash, Read
---

# Confluence Skill

Manage Confluence pages with search, read, and write operations.

When invoked, use the Confluence client to handle the request: $ARGUMENTS

**Note:** Confluence commands return Markdown by default. Use `--html` flag only if you need raw HTML for content manipulation.

## Available Commands

### Search for Pages
```bash
python3 -m sidekick.clients.confluence search "query" [--space SPACE] [--limit N]
```

### Get Page Details
```bash
python3 -m sidekick.clients.confluence get-page PAGE_ID_OR_URL
python3 -m sidekick.clients.confluence get-page-from-link "CONFLUENCE_URL"
```

### Get Page by Title
```bash
python3 -m sidekick.clients.confluence get-page-by-title "Title" SPACE
```

### Read Page Content
```bash
# Prefer this when the user provides a Confluence URL.
# Supports full page URLs and tiny URLs:
# - https://domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Title
# - https://domain.atlassian.net/wiki/x/SHORTID
python3 -m sidekick.clients.confluence get-content-from-link "CONFLUENCE_URL"

# For raw HTML from a URL (content manipulation)
python3 -m sidekick.clients.confluence get-content-from-link "CONFLUENCE_URL" --html

# Read by page ID or URL; returns Markdown by default
python3 -m sidekick.clients.confluence read-page PAGE_ID_OR_URL

# For raw HTML (content manipulation)
python3 -m sidekick.clients.confluence read-page PAGE_ID_OR_URL --html
```

### Create New Page
```bash
python3 -m sidekick.clients.confluence create-page SPACE "Title" content.html [--parent PARENT_ID]
```

### Update Page
```bash
python3 -m sidekick.clients.confluence update-page PAGE_ID content.html [--title "New Title"]
```

For meeting-note agenda updates, use the `confluence-meeting-notes-update`
skill. It performs safe raw-storage HTML edits with target-range validation.
For creating or preparing the next meeting notes section, use the
`confluence-meeting-notes-create-next` skill.

## Search Cache

The Confluence client automatically caches search query to page mappings for faster repeated searches.

**Cache Management:**
```bash
python3 -m sidekick.clients.confluence cache-show
python3 -m sidekick.clients.confluence cache-clear
```

## Example Usage

When the user asks to:
- "Search for API documentation in Confluence" - Use search command
- "Read the contents of my 1:1 doc with Bob" - Search for the doc and read it
- "Read this Confluence URL" - Use get-content-from-link; it accepts both full page URLs and /wiki/x tiny URLs
- "Add a topic to my 1:1 with Alice" - Use the confluence-meeting-notes-update skill
- "Create the next section for this meeting doc" - Use the confluence-meeting-notes-create-next skill
- "Update the team wiki page" - Use update-page command

For full documentation, see the detailed Confluence skill documentation in this folder.
