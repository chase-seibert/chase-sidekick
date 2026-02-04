# Dropbox Skill

Command-line interface for Dropbox file and Paper doc operations.

## Configuration

Configuration is automatically loaded from `.env` file in project root.

Create a `.env` file:
```bash
DROPBOX_ACCESS_TOKEN=your_dropbox_access_token
```

Get your Dropbox access token:
1. Go to https://www.dropbox.com/developers/apps
2. Create a new app with "Full Dropbox" access
3. Go to Permissions tab and enable: `files.content.read`, `files.content.write`, `sharing.read`
4. Generate access token in Settings tab

**Note**: Configuration can also be set via environment variables if `.env` file is not present.

## Commands

All commands use the module form (`python -m sidekick.clients.dropbox`).

### Get File Contents

```bash
python -m sidekick.clients.dropbox get-file-contents /Documents/notes.txt
```

Outputs file content to stdout (binary safe). You can redirect to a file:

```bash
python -m sidekick.clients.dropbox get-file-contents /Documents/notes.txt > local-copy.txt
```

### Get Metadata

```bash
python -m sidekick.clients.dropbox get-metadata /Documents/notes.txt
```

Displays file or folder metadata:
```
notes.txt
  Type: file
  Size: 1.5 KB
  Modified: 2026-01-15 10:30:00
```

For Paper docs:
```bash
python -m sidekick.clients.dropbox get-metadata /Paper/MyDoc.paper
```

Output:
```
MyDoc.paper
  Type: paper
  Size: 3.2 KB
  Modified: 2026-01-20 14:45:00
```

### Get Paper Doc Contents

```bash
# As markdown (default)
python -m sidekick.clients.dropbox get-paper-contents /Paper/MyDoc.paper

# As HTML
python -m sidekick.clients.dropbox get-paper-contents /Paper/MyDoc.paper --format html
```

Exports Paper doc content to stdout in the specified format. Supports `markdown` (default) and `html`.

### Get Paper Doc Contents from Share Link

```bash
python -m sidekick.clients.dropbox get-paper-contents-from-link "https://paper.dropbox.com/doc/Title-abc123"
```

Get Paper doc content using a Paper share link. Optional `--format` flag works the same as `get-paper-contents`.

### Export from Shared Link

Export content directly from a shared link. **Primary use case: accessing files in team space that you don't own.**

This is the **ONLY way** to get content of a Paper doc you don't own (e.g., team space documents).

```bash
# Team space Paper doc or file you don't own
python -m sidekick.clients.dropbox export-shared-link "https://www.dropbox.com/s/abc123/document.pdf?dl=0"

# Export specific file from shared folder
python -m sidekick.clients.dropbox export-shared-link \
  "https://www.dropbox.com/sh/xyz789/Photos" \
  --path "/vacation/IMG_001.jpg"

# Password-protected link
python -m sidekick.clients.dropbox export-shared-link \
  "https://www.dropbox.com/s/protected123/secrets.txt?dl=0" \
  --password "mypassword"

# Internal use: override download restriction
python -m sidekick.clients.dropbox export-shared-link \
  "https://www.dropbox.com/s/abc123/file.txt?dl=0" \
  --override-download
```

**IMPORTANT for Paper docs:**
- The returned HTML includes **extensive CSS, styling, and formatting** not present in `get-paper-contents`
- This makes the HTML unsuitable for read-write workflows (too complex to parse and write back)
- **Use `get-paper-contents` for Paper docs you own** when you need to read and write back
- **Use `export-shared-link` for Paper docs you don't own** (read-only team space access)

**Key features:**
- Works with password-protected links
- Can access specific files in shared folders
- Supports download-restricted links (with override flag)
- Accesses team space files you don't own

### Create Paper Doc

```bash
# From stdin
echo "# My Document\nContent here" | python -m sidekick.clients.dropbox create-paper-contents /Paper/NewDoc.paper

# From file via pipe
cat content.md | python -m sidekick.clients.dropbox create-paper-contents /Paper/NewDoc.paper

# Using --content flag
python -m sidekick.clients.dropbox create-paper-contents /Paper/NewDoc.paper --content "# My Document"

# As HTML
python -m sidekick.clients.dropbox create-paper-contents /Paper/NewDoc.paper --content "<h1>Title</h1>" --format html
```

Creates a new Paper doc from markdown or HTML content. The path must end with `.paper` extension.

**Formats:**
- `markdown` (default) - Standard markdown format
- `html` - HTML format

### Update Paper Doc

```bash
# From stdin
echo "# Updated Content" | python -m sidekick.clients.dropbox update-paper-contents /Paper/MyDoc.paper

# Using --content flag
python -m sidekick.clients.dropbox update-paper-contents /Paper/MyDoc.paper --content "# Updated Content"

# As HTML
python -m sidekick.clients.dropbox update-paper-contents /Paper/MyDoc.paper --content "<h1>Updated</h1>" --format html
```

Updates existing Paper doc with new content. Replaces all content (overwrites).

## 1:1 Doc Format Best Practices

When managing 1:1 meeting documents in Dropbox Paper, follow these guidelines for consistent structure:

### Document Structure

**Expected Format:**
- Single Paper doc per person (e.g., "/Paper/Chase-Bob 1:1.paper")
- Headers are dates (e.g., "Feb 1", "2026-02-02") or "Next" for upcoming topics
- Sections ordered most recent at top
- Under each header is a bullet list of topics
- Never reorder existing sections

### HTML Structure Example

```html
<div dir="auto" style="font-weight: 400; font-size: 40px; line-height: 48px; padding-bottom: 25px;color: #1b2733; text-decoration: none;" class="ace-line "><span>Chase / Bob 1:1</span></div>

<div dir="auto" style="font-weight: 400; font-size: 24px; line-height: 32px; padding-bottom: 15px;color: #1b2733; text-decoration: none;" class="ace-line "><span>Next</span></div>
<div dir="auto" style="line-height: 26px;" class="ace-line ">
  <ul class="listtype-bullet listindent1 list-bullet1" style="list-style-type: disc; margin: 0 0 0 1.5em; padding: 0">
    <li style="margin: 0; padding: 0;"><span>Discuss Q1 planning</span></li>
    <li style="margin: 0; padding: 0;"><span>Review sprint goals</span></li>
  </ul>
</div>

<div dir="auto" style="font-weight: 400; font-size: 24px; line-height: 32px; padding-bottom: 15px;color: #1b2733; text-decoration: none;" class="ace-line "><span>2026-02-02</span></div>
<div dir="auto" style="line-height: 26px;" class="ace-line ">
  <ul class="listtype-bullet listindent1 list-bullet1" style="list-style-type: disc; margin: 0 0 0 1.5em; padding: 0">
    <li style="margin: 0; padding: 0;"><span>Reviewed performance feedback</span></li>
    <li style="margin: 0; padding: 0;"><span>Discussed team expansion</span></li>
  </ul>
</div>
```

### Content Update Guidelines

**1. Never Add Duplicate Items**

Before adding content to a section, check if the item already exists:

```html
<!-- CORRECT: Check and add only if not present -->
<ul>
  <li><span>Review PR-123</span></li>
  <li><span>Update documentation</span></li>
  <!-- Only add "Discuss API changes" if it's not already in the list -->
</ul>

<!-- INCORRECT: Adding duplicate item -->
<ul>
  <li><span>Review PR-123</span></li>
  <li><span>Discuss API changes</span></li>
  <li><span>Discuss API changes</span></li>  <!-- Duplicate! -->
</ul>
```

**2. Reuse Existing "Next" Sections**

Always update content within existing "Next" sections rather than creating new sections:

```html
<!-- CORRECT: Update existing Next section -->
<div class="ace-line"><span>Next</span></div>
<ul>
  <li><span>New topic added to existing section</span></li>
  <li><span>Existing topic</span></li>
</ul>

<!-- INCORRECT: Don't create a second Next section -->
<div class="ace-line"><span>Next</span></div>
<ul>
  <li><span>Old topics</span></li>
</ul>
<div class="ace-line"><span>Next</span></div>
<ul>
  <li><span>New topics - should be in first section!</span></li>
</ul>
```

**3. Only Create Sections for "Next" or Dates**

Only create new section headers for:
- "Next" - for upcoming items or action items
- Dates in "YYYY-MM-DD" format (e.g., "2026-02-02") or short format (e.g., "Feb 1")

Never create arbitrary section headers like "Updates" or "New Information".

**4. Add New Sections Above Previous Sections**

When creating a new dated section, place it at the top (after any "Next" section):

```html
<!-- CORRECT: New sections go above old ones -->
<div class="ace-line"><span>Next</span></div>
<ul><li><span>Action items</span></li></ul>

<div class="ace-line"><span>2026-02-02</span></div>
<ul><li><span>Today's meeting notes</span></li></ul>

<div class="ace-line"><span>2026-02-01</span></div>
<ul><li><span>Yesterday's meeting notes</span></li></ul>
```

### Example Workflow

```bash
# 1. Get current Paper doc content as HTML
python -m sidekick.clients.dropbox get-paper-contents "/Paper/Chase-Bob 1:1.paper" --format html > current.html

# 2. Edit the HTML to add a new topic to the Next section
# - Find the existing "Next" section
# - Add new bullet item to the existing list
# - Don't create a duplicate "Next" section
# - Don't add duplicate topics

# 3. Update the Paper doc
cat current.html | python -m sidekick.clients.dropbox update-paper-contents "/Paper/Chase-Bob 1:1.paper" --format html

# 4. Clean up
rm current.html
```

### Why This Matters

- **No Duplicates**: Prevents confusion from repeated items in the same section
- **Consistency**: Documents maintain a predictable structure
- **History**: Dated sections create a chronological record (newest first)
- **Clarity**: Reusing "Next" keeps action items in one place
- **Navigation**: Users know where to find current vs. historical information

## Python Module Usage

You can also import and use the client in Python scripts:

```python
from sidekick.clients.dropbox import DropboxClient
from sidekick.config import get_dropbox_config

# Initialize client from config
config = get_dropbox_config()
client = DropboxClient(config["access_token"])

# Get file contents
content = client.get_file_contents("/Documents/notes.txt")
print(f"Downloaded {len(content)} bytes")

# Get metadata
metadata = client.get_metadata("/Documents/notes.txt")
print(f"File: {metadata['name']}, Size: {metadata['size']}")

# Get Paper doc as markdown
paper_content = client.get_paper_contents("/Paper/MyDoc.paper", export_format="markdown")
print(paper_content)

# Create Paper doc
client.create_paper_contents("/Paper/NewDoc.paper", "# Title\nContent", import_format="markdown")

# Update Paper doc
client.update_paper_contents("/Paper/MyDoc.paper", "# Updated", import_format="markdown")

# Resolve share link
link_metadata = client.resolve_share_link("https://www.dropbox.com/s/abc123/file.txt")
print(f"Path: {link_metadata['path_lower']}")

# Export from shared link (for team space files you don't own)
# NOTE: For Paper docs, returns complex HTML with CSS - use for read-only access
content = client.export_shared_link(
    "https://www.dropbox.com/s/abc123/file.txt?dl=0"
)

# Export specific file from shared folder
content = client.export_shared_link(
    url="https://www.dropbox.com/sh/xyz789/Photos",
    path="/vacation/IMG_001.jpg"
)

# Password-protected link
content = client.export_shared_link(
    url="https://www.dropbox.com/s/protected/doc.pdf?dl=0",
    link_password="secret"
)

# IMPORTANT: Paper doc distinction
# - For Paper docs YOU OWN (read-write): use get_paper_contents()
# - For Paper docs you DON'T OWN (team space, read-only): use export_shared_link()
```

## Common Use Cases

### Backup a Paper Doc

```bash
# Save Paper doc as markdown
python -m sidekick.clients.dropbox get-paper-contents /Paper/Important.paper > backup.md

# Save as HTML
python -m sidekick.clients.dropbox get-paper-contents /Paper/Important.paper --format html > backup.html
```

### Accessing Team Space Files

Use `export-shared-link` to access files in team space that you don't own:

```bash
# Download a file from a shared link
python -m sidekick.clients.dropbox export-shared-link "https://www.dropbox.com/s/abc123/report.pdf?dl=0" > report.pdf
```

**Python example:**

```python
# Get content from team space Paper doc (read-only)
try:
    content = client.export_shared_link(
        url="https://www.dropbox.com/s/abc123/TeamDoc.paper?dl=0"
    )

    # For Paper docs: HTML includes extensive CSS/formatting
    # Suitable for reading, not for read-write workflows
    html = content.decode('utf-8')

    # Save to local file
    with open("team-doc.html", "w") as f:
        f.write(html)

except ValueError as e:
    if "shared_link_access_denied" in str(e):
        print("Access denied or incorrect password")
    elif "shared_link_not_found" in str(e):
        print("Link expired or invalid")
    else:
        print(f"Error: {e}")
```

**For password-protected links:**

```python
content = client.export_shared_link(
    url="https://www.dropbox.com/s/protected/file.pdf?dl=0",
    link_password="shared_secret"
)
```

**Important distinction:**
- Team space Paper docs you don't own: Use `export-shared-link` (read-only, complex HTML)
- Paper docs you own: Use `get-paper-contents` (cleaner HTML/markdown, supports write-back)

### Create Paper Doc from Markdown File

```bash
cat document.md | python -m sidekick.clients.dropbox create-paper-contents /Paper/FromMarkdown.paper
```

### Edit Paper Doc Locally

```bash
# Download
python -m sidekick.clients.dropbox get-paper-contents /Paper/MyDoc.paper > edit.md

# Edit with your editor
vim edit.md

# Upload changes
cat edit.md | python -m sidekick.clients.dropbox update-paper-contents /Paper/MyDoc.paper
```

## Important Notes

### Path Format

All Dropbox paths must:
- Start with a forward slash `/`
- Use forward slashes for directories (not backslashes)
- Be case-sensitive

Examples:
- ✅ `/Documents/notes.txt`
- ✅ `/Paper/MyDoc.paper`
- ❌ `Documents/notes.txt` (missing leading slash)
- ❌ `\Documents\notes.txt` (backslashes)

### Paper Doc File Extension

Paper docs should have the `.paper` extension in their path, though Dropbox may handle docs without it. For consistency, always use `.paper`.

### Binary vs Text Content

- `get-file-contents` returns binary data (suitable for any file type)
- `get-paper-contents` returns text (markdown or HTML)
- `export-shared-link` returns binary data
- `create-paper-contents` and `update-paper-contents` accept both bytes and strings

### Share Links

Share links can be:
- Regular file links: `https://www.dropbox.com/s/...` or `https://www.dropbox.com/scl/...`
- Paper doc links: `https://paper.dropbox.com/doc/...`

The client automatically detects the type and handles appropriately.

## Troubleshooting

### Authentication Error

```
Error: Dropbox authentication failed (401 Unauthorized)
```

Solution: Check your access token in `.env` file. Generate a new token at https://www.dropbox.com/developers/apps

### Permission Error

```
Error: Dropbox access forbidden (403)
```

Solution: Check your app permissions. Ensure you've enabled `files.content.read`, `files.content.write`, and `sharing.read` in the Permissions tab.

### File Not Found

```
Error: Dropbox API error (409): path/not_found/
```

Solution: Check the file path. Remember paths must start with `/` and are case-sensitive.

### Not a Paper Doc

```
Error: File at /path is not a Paper doc or not exportable
```

Solution: The file is not a Paper doc. Use `get-file-contents` for regular files instead of `get-paper-contents`.

## Related Skills

- [JIRA](jira.md) - JIRA issue management
- [Confluence](confluence.md) - Confluence page operations
