---
name: weekly_report
description: Generate summary of 1:1 and meeting notes organized by audience
argument-hint: [weeks]
allowed-tools: Bash, Read
auto-approve: true
---

# Weekly Report Agent

Generate am executive summary of notes from your 1:1 docs, meeting docs, and Slack conversations for the past week(s), organized by audience. With references.

## Overview

This agent helps you:
1. Review recent notes from all your 1:1 and recurring meeting docs, and Slack
2. Identify key topics that need communication
3. Categorize items by audience (leadership, direct reports, everyone)

## Prerequisites

- `CLAUDE.local.md` file with your 1:1 docs, meeting docs, and Slack channels
- Configured Dropbox and Atlassian credentials in `.env`

## Usage Pattern

### Step 1: List Your Documents

Get all 1:1 docs, meeting docs, and Slack channels from `CLAUDE.local.md`
These may be Confluence pages or Dropbox Paper docs

### Step 2: Fetch Recent Content

For each document, fetch the content

For Slacks, use the Dash MCP to read recent channel contents, i.e. last 10 days

The fetched content will be saved in `memory/weekly_report/` for review and won't be deleted. Keep track of docs that error out so we can print them out at the end. 

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

- Print a list of documents and Slack channels were read successfully, and also those that errored out trying to retrieve the contents. 
- Echo the actual executive summary contents in the chat, AND link to a file version if you have it

### Step 6: Write to memory

Write or overwrite file at memory/weekly_report.md with is report contents


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

