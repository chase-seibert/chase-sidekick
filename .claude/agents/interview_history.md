---
name: interview_history
description: Generate all-time interview count report from Google Calendar
argument-hint: <years-back>
allowed-tools: Bash, Read, Write
auto-approve: true
---

# Interview History Agent

Generate comprehensive interview count reports from Google Calendar history.

## Purpose

This agent analyzes your Google Calendar to count and categorize all interview-related events over a specified time period. It provides:
- Total interview count with yearly/monthly breakdowns
- Response status distribution (accepted, declined, tentative)
- Interview type classification (Phone Screen, Technical Screen, Onsite, etc.)
- Trend analysis and insights
- CSV export with all interview details

The agent handles pagination to query complete calendar history and deduplicates recurring events.

## Prerequisites

- **Google Calendar credentials** configured in `.env` file or via OAuth
- Valid Google Calendar API access via `sidekick.clients.gcalendar`

## Usage

```
"Get my all-time interview count"
"Count my interviews from the last 3 years"
"Export all interviews to CSV from 2018"
```

Optional argument: Number of years to go back (default: 5)

## Workflow

The agent performs the following steps:

### Phase 1: Setup and Date Range Configuration
- Creates temporary working directory
- Parses the requested time period (default: 5 years back)
- Sets up date range for calendar queries

### Phase 2: Calendar Query with Pagination
- Queries Google Calendar API in monthly chunks to handle large date ranges
- Implements pagination to fetch all events (handles >250 events per month)
- Uses `singleEvents: true` to expand recurring events into individual instances
- Stores all calendar events temporarily for processing

### Phase 3: Interview Detection and Filtering
- Searches calendar events for interview-related keywords:
  - "interview", "phone screen", "technical screen", "screen:"
  - "candidate", "hiring", "onsite interview", "onsite", "debrief"
- Filters out non-interviews:
  - Prep meetings ("Prep phone screen", "Prep debrief", etc.)
  - Weekly syncs ("Weekly Hiring Sync", "Hiring sync")
  - Cancelled events
  - All-day events
- Deduplicates recurring events by event ID
- Categorizes each interview as: interview, phone screen, debrief, or other

### Phase 4: Aggregation and Analysis
- Aggregates interview counts by:
  - Year, quarter, and month
  - Response status (accepted, declined, tentative, no response)
  - Interview type (Phone Screen, Technical Screen, Onsite, Debrief, General)
- Calculates statistics:
  - Average interviews per year and per month
  - Busiest periods (year, quarter, month)
  - Acceptance and decline rates
- Extracts recent interviews (last 10)

### Phase 5: Report Generation
- Generates markdown report with:
  - Executive summary with totals and averages
  - Year-by-year breakdown table with status distribution
  - Response status percentages
  - Interview type distribution
  - Recent interviews list with status indicators
  - Insights section highlighting busiest periods and rates
- Generates CSV export with columns:
  - date, time, year, summary, category, status
  - attendee_count, organizer, description_preview, event_id
- Saves both files to `memory/interview_history/` directory

### Phase 6: Output Summary
- Displays quick summary statistics
- Provides file paths for generated reports

## Output Files

**Markdown Report:**
- Location: `memory/interview_history/interview-history-{timestamp}.md`
- Contains: Executive summary, tables, statistics, and insights
- Format: Markdown with YAML front matter

**CSV Export:**
- Location: `memory/interview_history/interviews-{start-year}-{end-year}.csv`
- Contains: All interview records with detailed metadata
- Format: CSV with headers

## Interview Categories

- **interview**: General interviews, hiring manager screens, technical screens, onsites
- **debrief**: Post-interview debrief meetings
- **phone screen**: Initial phone screening interviews
- **other**: Related hiring activities (HC meetings, onboarding, orientation)

## Edge Cases Handled

- **Pagination**: Queries calendar in monthly chunks and handles `nextPageToken` for months with >250 events
- **Recurring events**: Automatically expanded and deduplicated by event ID
- **All-day events**: Excluded (no `dateTime` field)
- **Cancelled events**: Excluded via status check
- **Prep meetings**: Filtered out using exclusion patterns
- **Missing attendees**: Still counts interview if keywords match
- **Invalid dates**: Gracefully handled with error recovery
- **Empty results**: Exits early with helpful message

## Example Output

```
📊 INTERVIEW SUMMARY (2018-2026)

Total Interviews: 764

By Category:
  interview           :  526 ( 68.8%)
  debrief             :  161 ( 21.1%)
  other               :   60 (  7.9%)
  phone screen        :   17 (  2.2%)

By Response Status:
  Accepted            :  623 ( 81.5%)
  No Response         :   85 ( 11.1%)
  Declined            :   53 (  6.9%)
  Tentative           :    3 (  0.4%)
```
