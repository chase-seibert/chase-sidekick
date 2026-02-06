---
name: kudos
description: Generate kudos for team members from recent 1:1 and meeting notes
argument-hint: [weeks]
allowed-tools: Bash, Read, Grep
---

# Kudos Skill

Generate kudos for team members from recent 1:1 and meeting notes, with proper Slack formatting.

## Overview

This skill helps you:
1. Review recent notes from all your 1:1 and recurring meeting docs
2. Extract kudos, wins, and accomplishments for specific people
3. Format kudos with Slack mentions (@username format)
4. Include references to source documents

## Prerequisites

- `CLAUDE.local.md` file with your 1:1 and meeting doc links
- Configured Dropbox and Atlassian credentials in `.env`
- `memory/people.json` file for email to Slack username mapping

## Usage Pattern

When invoked with: `/kudos [weeks]`

### Step 1: Create Output Directory

```bash
mkdir -p memory/kudos
```

### Step 2: Fetch Recent Content

For each document in `CLAUDE.local.md`, fetch the content:

**For Confluence pages:**
```bash
python3 -m sidekick.clients.confluence get-content-from-link "<CONFLUENCE_URL>" > memory/kudos/doc_name.html
```

**For Dropbox Paper docs:**
```bash
python3 -m sidekick.clients.dropbox get-paper-contents-from-link "<PAPER_URL>" > memory/kudos/doc_name.md
```

Keep track of docs that error out to report at the end.

### Step 3: Review and Extract Kudos

Look for recent mentions of:
- Accomplishments and wins
- Project launches and completions
- Promotions and performance ratings
- Going above and beyond
- Specific impact attributable to individuals

**Important:** Only extract kudos from recent date headers (within target time period).

### Step 4: Format Kudos with Slack Mentions

For each kudos item:
1. Identify the person(s) involved
2. Look up their Slack username:
   - Extract email from context or CLAUDE.local.md
   - Slack username = first part of email before @dropbox.com
   - Format as: `@username`
3. Format kudos with:
   - Clear description of accomplishment
   - Context and impact
   - Slack mentions for all people involved
   - Reference link to source doc

**Slack Mention Format:**
- Email: `alice@dropbox.com` → Slack: `@alice`
- Email: `bob.smith@dropbox.com` → Slack: `@bob.smith`

### Step 5: Generate Output

Create a markdown file with:

```markdown
## Kudos - [Date Range]

### [Category/Project Name]
[Description with impact and context]

**People:** @username1, @username2, @username3

[[ref]](source-doc-url)

---
```

**Categories might include:**
- Performance & Promotions
- Project Launches
- Technical Excellence
- Cross-team Collaboration
- Going Above and Beyond

### Step 6: Report Errors

Print a list of documents that errored during retrieval.

## Tips

- **Default Time Period**: Last 7 days, adjust based on argument
- **Be Specific**: Include concrete details about what was accomplished
- **Show Impact**: Explain why it matters, not just what was done
- **Group Related**: Combine related kudos for the same project/initiative
- **Verify Usernames**: Double-check Slack username format matches email prefix
- **Include Context**: Help readers understand the significance

## Common Use Cases

- Weekly team shoutouts
- Post-launch celebrations
- Performance cycle recognitions
- Quarterly team updates
- Manager upward feedback preparation
