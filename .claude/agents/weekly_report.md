---
name: weekly_report
description: Generate summary of 1:1 and meeting notes organized by audience
argument-hint: [weeks]
allowed-tools: Bash, Read, Skill
auto-approve: true
---

# Weekly Report Agent

Generate am executive summary of notes from your 1:1 docs, meeting docs, and Slack conversations for the past week(s), organized by audience. With references. Aim for 20+ total docs or channels.

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

Get all 1:1 docs, meeting docs, and Slack channels and Slack DMs from `CLAUDE.local.md`
These may be Confluence pages or Dropbox Paper docs

### Step 2: Process Documents in Batches

**IMPORTANT: Use batch processing to handle large numbers of documents efficiently.**

Process all documents in batches of 12-15 documents at a time. For each batch:

1. **Fetch documents** for this batch (continue on errors - see Error Handling below)
2. **Immediately extract notes** from recent time period (last 7 days by default)
3. **Categorize extracted notes** into the 4 categories (see Category Definitions below)
4. **Append categorized notes** to `memory/weekly_report/notes_batch_N.md` (where N is batch number)
5. **Discard full document content** from context (only keep extracted notes file)

**Document batching strategy:**
- Batch 1 (12-15 docs): 1:1 docs (prioritize recent/active relationships)
- Batch 2 (12-15 docs): Meeting docs + remaining 1:1s
- Batch 3 (12-15 docs): High-priority Slack channels (P0)
- Batch 4+ (12-15 docs each): Remaining Slack channels and DMs

After completing ALL batches, proceed to Step 3 (consolidation).

**For Slack channels**, use the `/slack` skill to read messages from the last 10 days:
1. Calculate date 10 days ago: `date -v-10d '+%Y-%m-%d'`
2. Use `slack_search_messages` with `after:YYYY-MM-DD in:#channel-name` query and pagination
3. Format results as Markdown (see `/slack` skill for formatting example)

**For Confluence and Paper docs**, use the respective clients to fetch content.

Look for notes from recent time period:
- Date headers (e.g., "January 31, 2026", "Week of 1/27")
- Bullet points under recent dates
- Action items or discussion topics
- **Important:** Ignore content under date headers older than your target time period

#### Error Handling Strategy

When a document fails to fetch:
1. **Log the error** with document name and error type (but DO NOT stop processing)
2. **Continue to the next document** - process all documents in the batch regardless of failures
3. **Track failures** in a list with categories:
   - Auth failures (403/401): Document URL + error message
   - Not found (404): Document URL
   - Rate limits (429): Document URL (client will auto-retry once)
   - Other errors: Document URL + error type
4. **Report all failures** at Step 5 (Document Summary) by category

**Error response format** (to be included in Step 5 output):
```
⚠️ Failed to fetch X documents:

Auth failures (403/401):
- [Doc name](URL) - 403 Forbidden

Not found (404):
- [Doc name](URL) - Document not found

Rate limits (429):
- [Doc name](URL) - Rate limit hit (retried)

Other errors:
- [Doc name](URL) - Error message
```

**IMPORTANT**: Never stop processing due to a single document failure. The goal is to extract as much context as possible from available documents. 

### Step 3: Consolidate Notes from All Batches

After processing all batches:

1. **Read all batch notes files** (`memory/weekly_report/notes_batch_*.md`)
2. **Merge notes by category** (combine all "Leadership" items, all "Direct Reports" items, etc.)
3. **Deduplicate similar notes** across batches:
   - If same topic appears in multiple docs, consolidate into ONE note
   - Keep ALL `[ref]` links from all sources
   - Example: `Topic X happened [[ref1]](url1) [[ref2]](url2)`
4. **Prioritize within each category** by importance/urgency
5. **Write consolidated report** to `memory/weekly_report.md`

### Step 4: Category Definitions

Sort extracted notes into the following categories. Each category should be a bullet list of notes. Each note should include a `[ref]` link to the source document URL from CLAUDE.local.md. 

**Format examples:**
```markdown
- Single source: Your note text here [[ref]](https://document-url-from-claude-local-md)
- Multiple sources: Topic X happened [[ref1]](url1) [[ref2]](url2)
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

### Step 5: Final Output

1. **Print document processing summary:**
   - Total documents attempted
   - Successfully processed by type (1:1s, meetings, Slack)
   - Failed documents with error details (see Error Handling format above)

2. **Write consolidated report** to `memory/weekly_report.md` with:
   - All categorized notes from Step 3
   - Each note with `[ref]` links to source documents
   - Deduplicated entries with multiple references where applicable

3. **Echo the report contents** to chat AND provide relative path to the memory file

**Report structure:**
```markdown
# Weekly Report - [Date Range]

## Things to Communicate to Leadership
- Item 1 [[ref]](url)
- Item 2 [[ref1]](url1) [[ref2]](url2)

## Things to Communicate to Direct Reports
- Item 1 [[ref]](url)

## Things to Communicate to Everyone
- Item 1 [[ref]](url)

## Kudos
- Person X for Y [[ref]](url)
```


## Tips

- **Time Period**: Default to last 7 days, adjust based on your reporting cadence
- **Batch Size**: Keep batches to 12-15 documents to avoid context window issues
- **Date Parsing**: Look for date headers in various formats:
  - "January 31, 2026"
  - "2026-01-31"
  - "Week of 1/27"
  - "1/31"
- **Bullet Points**: Most notes are in bullet format under date headers
- **References**: Each note should end with `[[ref]](URL)` linking to the source doc URL from CLAUDE.local.md
- **Deduplication**: Same topic might appear in multiple docs - consolidate but keep all references
- **Prioritization**: Within each category, order by importance/urgency
- **Context Management**: Discard full document content after extracting notes from each batch to preserve context window
- **Batch Files**: `notes_batch_*.md` files are intermediate artifacts - the final consolidated report goes in `weekly_report.md`

