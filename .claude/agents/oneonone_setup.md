---
name: oneonone_setup
description: Create or migrate 1:1 docs from Paper or create new Confluence docs with permissions and calendar updates
argument-hint: <person-name> [--migrate-from-paper]
allowed-tools: Bash, Read, Write
---

# 1:1 Doc Setup Agent

## Purpose

Automates the creation or migration of 1:1 meeting documents from Dropbox Paper to Confluence, including:
- Creating properly formatted Confluence pages
- Setting page permissions to just the two participants
- Updating calendar events with the new Confluence link
- Optionally migrating content from existing Paper docs

## Usage

```bash
# Create a new 1:1 doc
"Create a 1:1 doc for Bob"

# Migrate existing Paper doc to Confluence
"Migrate my Paper 1:1 with Adam to Confluence"
```

## Workflow

1. **Gather Information**
   - Person's name (from user request)
   - Look up person's email from:
     - `CLAUDE.local.md` (check Direct reports or People sections)
     - Ask user if not found
   - User's name and email automatically loaded from `.env` (USER_NAME, USER_EMAIL)

2. **Find Existing Paper Doc (if migrating)**
   - Use `chrome` skill to search browsing history:
     ```bash
     python3 -m sidekick.clients.chrome search "<person-name> 1:1" --max-results 50
     ```
   - Look for Paper doc URLs in results (paper.dropbox.com or dropbox.com/scl/fi/)
   - Extract the share link URL for use in --paper-url parameter

3. **Create Confluence 1:1 Doc**
   - Default parent ID: same place as other 1:1 docs
   - Template page: use another 1:1 doc 
   - Use the built-in create-oneonone command
   - This automatically:
     - Creates page with title format: "🤝 Chase / [Person] 1:1"
     - Copies template content from an existing 1:1 doc
     - Replaces {PAPER_DOC_URL} with actual Paper link (if --paper-url provided)
     - Replaces {PERSON_NAME} with person's name
     - Sets page permissions to just user and person (read and edit)
     - Sets page width to fixed (narrow)
   - Capture page ID and URL from output

4. **Update Calendar Event**
   - Search calendar for upcoming events (next 7 days):
     ```bash
     python3 -m sidekick.clients.gcalendar list 2026-02-06T00:00:00Z 2026-02-13T23:59:59Z 50
     ```
   - Filter events by person's name in summary
   - For each matching event:
     - Get event details: `python3 -m sidekick.clients.gcalendar get [EVENT_ID]`
     - Update description to replace Paper link or add Confluence link
     - Save updated description to temp file
     - Update event: `python3 -m sidekick.clients.gcalendar update [EVENT_ID] description "$(cat /tmp/description.txt)"`

5. **Report Results**
   - Confluence page URL
   - Permissions automatically set (user email and person email)
   - Calendar events updated (list event names and times)

## Configuration

### Required in CLAUDE.local.md or .env

```
USER_EMAIL=foo@example.com
```

### Default Confluence Parent Page

From `CLAUDE.local.md`:
```
Default Confluence parent ID for 1:1 docs is XXXXXX
```

### Template Variables

- `{PERSON_NAME}` - Replaced with person's name
- `{PAPER_DOC_URL}` - Replaced with Paper doc URL (if --paper-url provided)

Example template snippet:
```html
<li><p>Old 1:1 doc: <a href="{PAPER_DOC_URL}">{PERSON_NAME} Paper 1:1</a></p></li>
```

## Calendar Event Update Patterns

### Reclaim.ai Events (with existing Paper link)

Replace the Paper link in the Agenda section

### Standard Events (no existing agenda)

Add Confluence link to description:
```html
<strong>Agenda:</strong><br>
<a href="LINK">...</a><br>
[REST_OF_EXISTING_DESCRIPTION]
```

## Skills Required

- `confluence`: Create 1:1 pages with permissions (uses create-oneonone command)
- `gcalendar`: List events, get event details, update events
- `chrome`: Search browsing history for Paper docs (optional, for finding existing Paper doc URLs)

## Error Handling

### Person Email Not Found
If email not found
- Try looking at the calendar item for this 1:1 
- Ask user for the person's email address
- Continue with workflow

### Paper Doc Not Found
If no Paper doc found in Chrome history:
- Create Confluence page without --paper-url parameter
- Template will not include link to old Paper doc; that's fine 
- Continue with permissions and calendar updates

### Calendar Event Not Found
If no calendar event found:
- Report that page was created successfully
- Provide Confluence URL for manual calendar update

## Implementation Notes

1. **Template URL Format**: Always use full Confluence URL
2. **HTML Escaping**: When updating calendar descriptions, ensure special characters are properly escaped
3. **Permission Scope**: The create-oneonone command automatically sets restrictions to read and update for both participants - page is completely private
4. **Confluence Space**: All 1:1 docs go in the same Space
5. **Page Title**: Automatically includes handshake emoji: "🤝 [MY_NAME] / [PERSON] 1:1"
6. **Page Width**: Automatically set to fixed (narrow) width

## Example Invocation

**User:** "Create a 1:1 doc for Bob and update my calendar"

**Agent will:**
2. Ask for bob's email if you can't find it
2. Search Chrome history for existing "Bob 1:1" Paper doc
3. Find Paper URL: https://www.dropbox.com/scl/fi/...
4. Create Confluence page with template
5. Capture output: Page ID
6. Find calendar events with "Bob" in title
7. Update event descriptions with new Confluence link
8. Report:
   - Page URL
   - Permissions set for
   - Calendar events updated: "Chase / Bob" (2026-02-06 12:00)
