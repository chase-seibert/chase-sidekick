# Confluence Skill

Manage Confluence pages with search, read, and write operations.

## Overview

This skill provides command-line access to Confluence with:
- Search for pages by title or CQL queries
- Read page content and metadata
- Create new pages with optional parent hierarchy
- Update existing pages with automatic version handling

## Setup

Configuration is automatically loaded from `.env` file (same credentials as JIRA).

## Configuration

Uses the same `.env` configuration as JIRA. See project README for setup instructions.

Example `.env`:
```bash
ATLASSIAN_URL=https://your-company.atlassian.net
ATLASSIAN_EMAIL=your-email@company.com
ATLASSIAN_API_TOKEN=your_api_token_here
```

Get API token at: https://id.atlassian.com/manage-profile/security/api-tokens

## Commands

### Search for Pages

Search pages by title or using CQL (Confluence Query Language):

```bash
# Simple search by title
python -m sidekick.clients.confluence search "API Documentation"

# Search in specific space
python -m sidekick.clients.confluence search "API" --space DEV

# Limit results
python -m sidekick.clients.confluence search "Documentation" --space TEAM --limit 10

# Advanced CQL query
python -m sidekick.clients.confluence search "title~'API' AND lastModified > '2024-01-01'" --space DEV
```

**Memory format** (one per line):
```
123456789: API Documentation [DEV] (v5)
987654321: Team Guidelines [TEAM] (v12)
```

### Search Cache

The Confluence client automatically caches search query to page mappings for faster repeated searches.

**How it works:**
1. When you search for a term (e.g., "Bob 1:1"), the first result is automatically cached
2. Next time you search for the same term, the cached page is returned immediately (no API call)

**Cache file:** `memory/confluence/confluence_search_cache.yaml`

**Example workflow:**
```bash
# First search - performs API call and caches first result
python -m sidekick.clients.confluence search "Bob 1:1"
# Output: Found 5 pages (showing 5):...
# [Cached 'Bob 1:1' -> 123456789]

# Search again - uses cache
python -m sidekick.clients.confluence search "Bob 1:1"
# Output: [Using cached result for 'Bob 1:1']
# Returns page 123456789 immediately
```

**Cache management:**
```bash
# View cache contents
python -m sidekick.clients.confluence cache-show

# Clear cache
python -m sidekick.clients.confluence cache-clear
```

**Manual editing:**

The cache is a simple YAML file that you can manually edit:

```bash
# Edit cache file directly
vi memory/confluence/confluence_search_cache.yaml
```

Example cache file:
```yaml
# Confluence Search Cache
# Maps search queries to page IDs
# Edit this file to add or correct search term mappings

bob 1:1:
  page_id: "123456789"
  title: "Alice / Bob 1:1"
  space: "TNC"
  last_used: "2026-02-02 10:30:15"

api documentation:
  page_id: "1234567890"
  title: "API Reference Guide"
  space: "DEV"
  last_used: "2026-02-01 15:20:00"
```

**Notes:**
- First search result is automatically cached for each query
- Cache has no expiry - entries persist until manually removed
- Queries are normalized (lowercase, trimmed) for consistent matching
- Cache is stored in `memory/` directory (excluded from git)
- If a cached page no longer exists, search falls back to normal API call

### Get Page Details

Get detailed information about a page by ID:

```bash
python -m sidekick.clients.confluence get-page 123456789
```

**Output:**
```
123456789: API Documentation
  Space: DEV (Development)
  Version: 5 (updated 2025-02-01)
  Status: current
  URL: https://company.atlassian.net/wiki/spaces/DEV/pages/123456789
  Content preview: <h1>API Overview</h1><p>This document...
```

### Get Page by Title

Find and display a page by exact title in a space:

```bash
python -m sidekick.clients.confluence get-page-by-title "API Documentation" DEV
```

### Read Page Content

Get the raw HTML content of a page (storage format):

```bash
python -m sidekick.clients.confluence read-page 123456789

# Save to file
python -m sidekick.clients.confluence read-page 123456789 > api-docs.html
```

### Create New Page

Create a new Confluence page from an HTML file:

```bash
# Create simple page
echo "<h1>Test Page</h1><p>Content here</p>" > content.html
python -m sidekick.clients.confluence create-page DEV "Test Page" content.html

# Create page with parent (child page)
python -m sidekick.clients.confluence create-page DEV "Child Page" content.html --parent 123456789
```

**Output:**
```
Created page: 999888777: Test Page [DEV] (v1)
  URL: https://company.atlassian.net/wiki/spaces/DEV/pages/999888777
```

### Update Existing Page

Update a page's content (automatically handles version conflicts):

```bash
# Update content only (keeps existing title)
python -m sidekick.clients.confluence update-page 123456789 new-content.html

# Update content and title
python -m sidekick.clients.confluence update-page 123456789 new-content.html --title "New Title"
```

**Output:**
```
Updated page: 123456789: API Documentation [DEV] (v6)
  URL: https://company.atlassian.net/wiki/spaces/DEV/pages/123456789
```

**Note**: The update command automatically fetches the current version before updating, so you don't need to worry about version conflicts.

### Add Topic to 1:1 Doc

Add a topic to your 1:1 meeting doc with another person. The command automatically:
- Searches for the 1:1 doc (e.g., "Alice / Bob" or "Bob / Alice 1:1")
- Validates it matches the expected title format
- Checks access restrictions (should be locked to 2 people)
- Adds the topic to the specified section (default: "Next")
- Creates the section and/or bullet list if needed
- Adds the topic to the top of the existing bullet list

**Requirements:**
- Configure `USER_NAME` and `USER_EMAIL` in `.env` file
- 1:1 doc must follow naming convention:
  - "Alice / Bob"
  - "Alice / Bob 1:1"
  - "Bob / Alice"
  - "Bob / Alice 1:1"

**Expected 1:1 Doc Format:**
- Single page per person
- Headers are dates (e.g., "Feb 1", "2026-02-02") or "Next" for upcoming topics
- Sections ordered most recent at top
- Under each header is a bullet list of topics
- Never reorders existing sections

**Usage:**

```bash
# Add topic to Next section (default)
python -m sidekick.clients.confluence add-topic-to-oneonone Bob "Discuss Q1 planning"

# Add topic to specific date section
python -m sidekick.clients.confluence add-topic-to-oneonone Bob "Review feedback" --section "Feb 5"

# Add topic with spaces
python -m sidekick.clients.confluence add-topic-to-oneonone "Jane Smith" "API design review"
```

**Output:**
```
Found 1:1 doc: 123456789: Alice / Bob 1:1
Added topic to Next section

Updated 1:1 doc: 123456789: Alice / Bob 1:1 (v23)
  URL: https://company.atlassian.net/wiki/spaces/TNC/pages/123456789
```

**Features:**
- **Duplicate Prevention**: Won't add a topic if it already exists in the doc
- **Smart Search**: Uses search cache for faster repeated access
- **Section Creation**: Creates "Next" section if it doesn't exist
- **List Management**: Creates bullet list if section has none
- **Access Validation**: Warns if page isn't restricted to exactly 2 people
- **Title Validation**: Ensures page matches expected 1:1 doc naming format

**Example Workflow:**

```bash
# Before your 1:1 meeting, add discussion topics
python -m sidekick.clients.confluence add-topic-to-oneonone Bob "Review sprint goals"
python -m sidekick.clients.confluence add-topic-to-oneonone Bob "Discuss promotion timeline"
python -m sidekick.clients.confluence add-topic-to-oneonone Bob "Team outing ideas"

# After the meeting, topics remain in "Next" until you manually move them
# or create a dated section for meeting notes
```

**Configuration:**

Add to your `.env` file:
```bash
# User Configuration (for 1:1 docs)
USER_NAME=Alice
USER_EMAIL=alice@example.com
```

### Content Update Best Practices

When updating Confluence pages, follow these guidelines for managing sections:

**1. Never Add Duplicate Items**

Before adding content to a section, check if the item already exists to avoid duplicates:

```html
<!-- CORRECT: Check and add only if not present -->
<h1>Next</h1>
<ul>
  <li>Review PR-123</li>
  <li>Update documentation</li>
  <!-- Only add "this was added using AI" if it's not already in the list -->
</ul>

<!-- INCORRECT: Adding duplicate item -->
<h1>Next</h1>
<ul>
  <li>Review PR-123</li>
  <li>this was added using AI</li>
  <li>this was added using AI</li>  <!-- Duplicate! -->
</ul>
```

**2. Reuse Existing "Next" Sections**

Always update content within existing "Next" sections rather than creating new sections:

```html
<!-- CORRECT: Update existing Next section -->
<h1>Next</h1>
<p>New content goes here, replacing old content in the existing section</p>

<!-- INCORRECT: Don't create a second Next section -->
<h1>Next</h1>
<p>Old content</p>
<h1>Next</h1>
<p>New content</p>
```

**3. Only Create Sections for "Next" or Dates**

Only create new section headers if they are:
- `<h1>Next</h1>` - for upcoming items or action items
- `<h1>2026-02-02</h1>` - for dated entries (use YYYY-MM-DD format)

Never create arbitrary section headers like "Updates" or "New Information".

**4. Add New Sections Above Previous Sections**

When creating a new dated section, place it at the top (after any "Next" section):

```html
<!-- CORRECT: New sections go above old ones -->
<h1>Next</h1>
<p>Action items</p>

<h1>2026-02-02</h1>
<p>Today's meeting notes</p>

<h1>2026-02-01</h1>
<p>Yesterday's meeting notes</p>

<!-- INCORRECT: Don't append to the end -->
<h1>Next</h1>
<p>Action items</p>

<h1>2026-02-01</h1>
<p>Yesterday's meeting notes</p>

<h1>2026-02-02</h1>
<p>Today's meeting notes - this should be at the top!</p>
```

**Example Update Workflow**

```bash
# 1. Read current page content
python -m sidekick.clients.confluence read-page 123456789 > current.html

# 2. Edit the file to update the "Next" section (don't create a new one)
# Or add a new dated section at the top
vi current.html

# 3. Update the page
python -m sidekick.clients.confluence update-page 123456789 current.html
```

**Why This Matters**

- **No Duplicates**: Prevents confusion from repeated items in the same section
- **Consistency**: Documents maintain a predictable structure
- **History**: Dated sections create a chronological record (newest first)
- **Clarity**: Reusing "Next" keeps action items in one place
- **Navigation**: Users know where to find current vs. historical information

## Python Usage

```python
from sidekick.clients.confluence import ConfluenceClient
from sidekick.config import get_atlassian_config

# Initialize client
config = get_atlassian_config()
client = ConfluenceClient(
    base_url=config["url"],
    email=config["email"],
    api_token=config["api_token"]
)

# Search for pages
result = client.search_pages("API Documentation", space="DEV")
pages = result.get("results", [])
for page in pages:
    print(f"{page['id']}: {page['title']}")

# Get page details
page = client.get_page("123456789")
print(f"Title: {page['title']}")
print(f"Version: {page['version']['number']}")

# Get page content
content = client.get_page_content("123456789")
print(content)

# Get page by title
page = client.get_page_by_title("Home", "DEV")
if page:
    print(f"Found: {page['id']}")

# Create new page
new_page = client.create_page(
    space="DEV",
    title="New Page",
    content="<h1>Title</h1><p>Content</p>"
)
print(f"Created: {new_page['id']}")

# Create child page
child = client.create_page(
    space="DEV",
    title="Child Page",
    content="<p>Child content</p>",
    parent_id="123456789"
)

# Update page (manual version)
page = client.get_page("123456789", expand=['version'])
current_version = page['version']['number']
updated = client.update_page(
    "123456789",
    "Updated Title",
    "<p>New content</p>",
    current_version
)

# Update page (automatic version handling - recommended)
updated = client.update_page_safely(
    "123456789",
    "Updated Title",
    "<p>New content</p>"
)
print(f"Updated to version {updated['version']['number']}")
```

## Content Format

Confluence uses "storage format" which is HTML with special macros:

### Basic HTML
```html
<h1>Heading</h1>
<p>Paragraph with <strong>bold</strong> and <em>italic</em>.</p>
<ul>
  <li>List item 1</li>
  <li>List item 2</li>
</ul>
```

### Confluence Macros
```html
<!-- Info panel -->
<ac:structured-macro ac:name="info">
  <ac:rich-text-body>
    <p>This is an info panel</p>
  </ac:rich-text-body>
</ac:structured-macro>

<!-- Code block -->
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">python</ac:parameter>
  <ac:plain-text-body><![CDATA[
def hello():
    print("Hello, World!")
  ]]></ac:plain-text-body>
</ac:structured-macro>
```

## CQL (Confluence Query Language)

Advanced search queries using CQL:

### Common Patterns

```bash
# Pages by type and space
python -m sidekick.clients.confluence search "type=page AND space=DEV"

# Pages modified recently
python -m sidekick.clients.confluence search "lastModified > '2024-01-01'"

# Pages by creator
python -m sidekick.clients.confluence search "creator='john.doe@company.com'"

# Title contains text
python -m sidekick.clients.confluence search "title~'API'"

# Combine conditions
python -m sidekick.clients.confluence search "type=page AND space=DEV AND title~'Documentation'" --limit 20
```

### CQL Operators

- `=` - Equals
- `~` - Contains (fuzzy match)
- `>`, `<` - Greater than, less than (for dates)
- `AND`, `OR` - Logical operators
- `IN` - Match multiple values

## Common Use Cases

### 1. Backup Page Content

```bash
# Save page content to file
python -m sidekick.clients.confluence read-page 123456789 > backup.html

# Later restore from backup
python -m sidekick.clients.confluence update-page 123456789 backup.html
```

### 2. Bulk Create Pages

```python
from sidekick.clients.confluence import ConfluenceClient
from sidekick.config import get_atlassian_config

config = get_atlassian_config()
client = ConfluenceClient(**config)

pages_to_create = [
    ("Page 1", "<h1>Page 1</h1><p>Content 1</p>"),
    ("Page 2", "<h1>Page 2</h1><p>Content 2</p>"),
    ("Page 3", "<h1>Page 3</h1><p>Content 3</p>"),
]

for title, content in pages_to_create:
    page = client.create_page("DEV", title, content)
    print(f"Created: {page['id']}: {title}")
```

### 3. Search and Update

```python
# Find pages and update them
result = client.search_pages("title~'Old Name'", space="DEV")
for page in result.get("results", []):
    page_id = page["id"]
    title = page["title"].replace("Old Name", "New Name")
    content = client.get_page_content(page_id)

    # Update with new title
    client.update_page_safely(page_id, title, content)
    print(f"Updated: {page_id}")
```

### 4. Create Page Hierarchy

```python
# Create parent page
parent = client.create_page(
    "DEV",
    "Parent Page",
    "<h1>Parent</h1>"
)
parent_id = parent["id"]

# Create children
for i in range(1, 4):
    child = client.create_page(
        "DEV",
        f"Child Page {i}",
        f"<h1>Child {i}</h1><p>Content</p>",
        parent_id=parent_id
    )
    print(f"Created child: {child['id']}")
```

### 5. Export Pages to Files

```bash
# Create export directory
mkdir -p confluence-export

# Search for pages
python -m sidekick.clients.confluence search "type=page" --space DEV --limit 100 > pages.txt

# Extract page IDs and export each
grep -oE '^[0-9]+' pages.txt | while read page_id; do
    python -m sidekick.clients.confluence read-page "$page_id" > "confluence-export/${page_id}.html"
    echo "Exported: $page_id"
done
```

## Error Handling

### Page Not Found (404)
```
Error: Resource not found: .../content/999999999
```
Check that the page ID is correct and you have access.

### Permission Denied (403)
```
Error: Confluence authentication failed (HTTP 403): Permission denied
```
Check your API token and Confluence space permissions.

### Version Conflict (409)
```
Error: Version conflict: Page was modified by another user.
```
This shouldn't happen with `update-page` command (uses auto-retry), but can occur with direct API calls.

### Invalid Credentials (401)
```
Error: Confluence authentication failed (HTTP 401): Authentication failed
Generate a new token at: https://id.atlassian.com/manage-profile/security/api-tokens
```
Verify your ATLASSIAN_EMAIL and ATLASSIAN_API_TOKEN in `.env`.

## Tips

### Content Best Practices

1. **Use storage format HTML**: This is Confluence's native format
2. **Test macros**: Complex macros may need specific structure
3. **Include headers**: Use `<h1>`, `<h2>`, etc. for navigation
4. **Backup before updating**: Save current content first

### Performance

- **Limit search results**: Use `--limit` to reduce API calls
- **Cache page IDs**: Store IDs instead of searching by title repeatedly
- **Batch operations**: Use Python API for bulk updates

### Working with Templates

```bash
# Save a template page
python -m sidekick.clients.confluence read-page TEMPLATE-ID > template.html

# Create new page from template
sed 's/{{TITLE}}/New Page Title/g' template.html > new-page.html
python -m sidekick.clients.confluence create-page DEV "New Page" new-page.html
```

## Related Skills

- [JIRA Query](jira.md) - Query JIRA issues (uses same credentials)
- [Output Management](output.md) - Save command output with metadata

## API Reference

The Confluence client uses Atlassian's REST API v1:
- Base URL: `{base_url}/wiki/rest/api/content`
- Authentication: Same as JIRA (Basic Auth with API token)
- Documentation: https://developer.atlassian.com/cloud/confluence/rest/

## Limitations

- **Storage format only**: View format is read-only
- **Version conflicts**: Rare with auto-retry, but possible under high concurrency
- **Rate limiting**: Atlassian may rate-limit API calls
- **Content size**: Very large pages may be slow to transfer

## Troubleshooting

### "Could not extract content from page"
The page may not have body content expanded. This is handled automatically by the client.

### Search returns no results
- Check space key is correct (case-sensitive)
- Verify you have access to the space
- Try simpler search queries first

### Create page fails with "space not found"
Verify the space key exists and you have permission to create pages in it.

### Update fails even with auto-retry
The page may have been deleted or moved. Check it exists with `get-page` first.
