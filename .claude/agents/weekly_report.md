---
name: weekly_report
description: Generate summary of 1:1 and meeting notes organized by audience
argument-hint: [weeks]
allowed-tools: Bash, Read
auto-approve: true
---

# Weekly Report Agent

Generate a summary of notes from your 1:1 and meeting docs for the past week(s), organized by audience.

## Overview

This agent helps you:
1. Review recent notes from all your 1:1 and recurring meeting docs
2. Identify key topics that need communication
3. Categorize items by audience (leadership, direct reports, everyone)

## Prerequisites

- `CLAUDE.local.md` file with your 1:1 and meeting doc links
- Configured Dropbox and Atlassian credentials in `.env`

## Usage Pattern

### Step 1: List Your Documents

Get all 1:1 docs and meeting docs from `CLAUDE.local.md`
These may be Confluence pages or Dropbox Paper docs

### Step 2: Fetch Recent Content

For each document, fetch the content:

Create output directory first:
```bash
mkdir -p memory/weekly_report
```

**For Confluence pages:**
```bash
python -m sidekick.clients.confluence get-content-from-link "<CONFLUENCE_URL>" > memory/weekly_report/doc_name.html
```

**For Dropbox Paper docs:**
```bash
python -m sidekick.clients.dropbox get-paper-contents-from-link "<PAPER_URL>" > memory/weekly_report/doc_name.md
```

The fetched documents will be saved in `memory/weekly_report/` for review and won't be deleted. Keep track of docs that error out so we can print them out at the end. 

### Step 3: Review and Extract Notes

Manually review each document for notes from the target time period (e.g., last week).

Look for:
- Date headers (e.g., "January 31, 2026", "Week of 1/27")
- Bullet points under recent dates
- Action items or discussion topics

**Important:** Ignore content that appears under date headers that are not recent (older than your target time period). Only extract notes from the sections with recent dates.

### Step 4: Categorize Notes

Sort extracted notes into the following categories. Each category should be a bullet list of notes. Each note should include a `[ref]` link to the source document URL from CLAUDE.local.md. 

**Format example:**
```markdown
- Your note text here [[ref]](https://document-url-from-claude-local-md)
```

#### Things to Communicate to Leadership
Items that require escalation, alignment, or visibility at leadership level:
- Roadmap changes or delays
- Cross-team dependencies or blockers
- Resource needs (headcount, budget)
- Strategic decisions needed
- Risk escalations
- Organizational topics
- Business wins
- Recognition and wins to share

#### Things to Communicate to Direct Reports
Items relevant to your team members:
- Feedback from leadership
- Changes to team priorities or roadmap
- Process updates
- Career development opportunities
- Team resource changes
- Kudos from leadership 

#### Things to Communicate to Everyone
Items for broad communication:
- Product launches or milestones
- Company announcements
- Cross-org initiatives
- Demos or show-and-tells
- Policy or process changes
- Team wins worth celebrating

#### Kudos
Thank yous for specific people: 
- Person went above and beyond
- Any impact attributable to a person 

### Step 5: Categorize Notes

Print a list of documents that errored out trying to retrieve the contents. 


## Example Workflow

```bash
# Create output directory
mkdir -p memory/weekly_report

# Fetch all Paper docs from your CLAUDE.local.md
for url in \
  "<PAPER_URL_1>" \
  "<PAPER_URL_2>" \
  "<PAPER_URL_3>"
  # ... add all your Paper doc URLs
do
  python -m sidekick.clients.dropbox get-paper-contents-from-link "$url" >> memory/weekly_report/all_docs.md
  echo "\n\n---\n\n" >> memory/weekly_report/all_docs.md
done

# Fetch Confluence pages from your CLAUDE.local.md
for url in \
  "<CONFLUENCE_URL_1>" \
  "<CONFLUENCE_URL_2>"
  # ... add all your Confluence URLs
do
  python -m sidekick.clients.confluence get-content-from-link "$url" >> memory/weekly_report/all_docs.html
  echo "\n\n---\n\n" >> memory/weekly_report/all_docs.html
done

# Review memory/weekly_report/all_docs.md and memory/weekly_report/all_docs.html
# Extract and categorize recent notes manually
# Files are preserved in memory/weekly_report/ for future reference
```

## Tips

- **Time Period**: Default to last 7 days, adjust based on your reporting cadence
- **Date Parsing**: Look for date headers in various formats:
  - "January 31, 2026"
  - "2026-01-31"
  - "Week of 1/27"
  - "1/31"
- **Bullet Points**: Most notes are in bullet format under date headers
- **References**: Each note should end with `[[ref]](URL)` linking to the source doc URL from CLAUDE.local.md
- **Deduplication**: Same topic might appear in multiple docs - consolidate but keep all references
- **Prioritization**: Within each category, order by importance/urgency
- **File Preservation**: Documents are saved in `memory/weekly_report/` and not deleted, allowing for iterative refinement

