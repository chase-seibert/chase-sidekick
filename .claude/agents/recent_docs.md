---
name: recent_docs
description: Generate categorized summary of recent Paper and Confluence docs from Chrome history
argument-hint: [days]
allowed-tools: Bash, Read
---

# Recent Docs Agent

Generate a categorized summary of Paper and Confluence documents visited in the last 7 days.

## Overview

This agent helps you:
1. Fetch Paper and Confluence URLs from Chrome browsing history (last 7 days)
2. Categorize documents by theme (1:1s, meetings, projects, planning, technical, other)
3. Generate a clean Markdown report with linked URLs organized by category. Combine Paper and Confluence docs in the output. Order sections by most visited. 
4. Save the report to memory for future reference

## Prerequisites

- Chrome browsing history accessible
- No configuration needed (Chrome client works automatically)

## Usage Pattern

### Step 1: Calculate Date Range

Determine the start date (7 days ago from today):

```bash
# Calculate date 7 days ago
START_DATE=$(date -v-7d +%Y-%m-%d)  # macOS
# Or for Linux:
# START_DATE=$(date -d "7 days ago" +%Y-%m-%d)

echo "Fetching docs from: $START_DATE"
```

### Step 2: Fetch Recent Documents

Get Paper and Confluence URLs visited in the last 7 days:

```bash
# Create temporary directory for intermediate files
TMP_DIR=/tmp/recent_docs_$$
mkdir -p $TMP_DIR

# Fetch Confluence pages
python3 -m sidekick.clients.chrome list-confluence \
    --start-date $START_DATE \
    --max-results 200 > $TMP_DIR/confluence.txt

# Fetch Paper docs
python3 -m sidekick.clients.chrome list-paper \
    --start-date $START_DATE \
    --max-results 200 > $TMP_DIR/paper.txt
```

### Step 3: Extract and Deduplicate URLs

Extract unique URLs from the output:

```bash
# Extract Confluence URLs
grep -oE 'https://[^ ]+atlassian.net/wiki[^ ]+' $TMP_DIR/confluence.txt | \
    sort -u > $TMP_DIR/confluence_urls.txt

# Extract Paper URLs
grep -oE 'https://[^ ]+dropbox.com/[^ ]+paper[^ ]+' $TMP_DIR/paper.txt | \
    grep -E '(scl/fi/|paper/doc/)' | \
    sort -u > $TMP_DIR/paper_urls.txt

# Count documents found
CONFLUENCE_COUNT=$(wc -l < $TMP_DIR/confluence_urls.txt | tr -d ' ')
PAPER_COUNT=$(wc -l < $TMP_DIR/paper_urls.txt | tr -d ' ')

echo "Found $CONFLUENCE_COUNT Confluence pages and $PAPER_COUNT Paper docs"
```

### Step 4: Categorize Documents

Read the full output (with titles) and categorize each document based on patterns in URL and title:

**1:1 Meeting Docs**
- URLs or titles containing: "1:1", "1-1", "11", "one-on-one"
- Common patterns: "Alice-[Name]-11", "[Manager]-[Direct Report]"

**Other Meetings**
- URLs or titles containing: "Meeting", "Notes", "Vibe Check", "Stand-Up", "Standup", "Review", "Demo", "LT", "XLT", "Sync"
- Exclude 1:1s already categorized

**Projects**
- URLs or titles containing: project codes (C1, DBX-, PROJ-), "Project Brief", "Epic", "Initiative", "Roadmap"
- Common patterns: "C1.1", "DBX-1234", project names

**Planning**
- URLs or titles containing: "Roadmap", "Planning", "OKR", "QBR", "H1", "H2", "Q1", "Q2", "Strategy", "Goals", "Path to Flat"
- Planning-related keywords

**Technical**
- URLs or titles containing: "Tech Spec", "Technical", "API", "Design Doc", "Architecture", "Implementation", "Engineering"
- Technical keywords and specs

**Other**
- Everything else that doesn't fit the above categories

### Step 5: Generate Report

Create a Markdown report with categorized links:

```markdown
---
generated_date: "YYYY-MM-DD HH:MM:SS"
date_range: "YYYY-MM-DD to YYYY-MM-DD (7 days)"
total_confluence_pages: N
total_paper_docs: N
---

# Recent Documents (Last 7 Days)

Report generated: YYYY-MM-DD HH:MM:SS
Date range: YYYY-MM-DD to YYYY-MM-DD

---

## 1:1 Meeting Notes

- [Alice & Nandan 1:1](https://example.com/scl/fi/.../Alice-Nandan-11.paper)
- [Alice & Dan 1:1](https://example.com/scl/fi/.../Alice-Dan-11.paper)
- [Alice & Nitin 1:1 - Confluence](https://company.atlassian.net/wiki/spaces/TNC/pages/.../Alice+Nitin+1+1)

## Other Meetings

- [Teams & Sharing LT Vibe Check](https://example.com/scl/fi/.../Teams-Sharing-Vibe-Check.paper)
- [Core Eng LT Meeting](https://example.com/scl/fi/.../Core-Eng-LT.paper)
- [C1 Teams DRI Stand-Up](https://example.com/scl/fi/.../C1-Meeting-Notes.paper)
- [Teams Demos - Confluence](https://company.atlassian.net/wiki/spaces/TeamsGroup/pages/.../Teams+Sharing+Demos)

## Projects

- [C1: Unblock Team Growth](https://example.com/scl/fi/.../C1-Unblock-Team-Growth.paper)
- [Basic Gating Project Brief](https://example.com/scl/fi/.../Team-Formation-Converting-Basic.paper)
- [DBX-1734 - Confluence](https://company.atlassian.net/wiki/spaces/.../DBX-1734)

## Planning & Strategy

- [Teams Path to Flat 1H 2026](https://example.com/scl/fi/.../Teams-Path-to-Flat-1H-20.paper)
- [Q4'25 QBR](https://example.com/scl/fi/.../Q425-QBR-Core-FSS.paper)
- [RtB Monthly Pillar Update](https://example.com/scl/fi/.../RtB-Monthly-Pillar-Update.paper)

## Technical Documentation

- [CoWork Tech Stack Notes - Confluence](https://company.atlassian.net/wiki/spaces/Core/pages/.../CoWork+Tech+Stack+Notes)
- [API v2 List Links Support](https://example.com/scl/fi/.../APIv2-List-Links-Support.paper)
- [Technical Design - Confluence](https://company.atlassian.net/wiki/spaces/ERP/pages/.../Technical+Design)

## Other Documents

- [DX Survey Analysis](https://example.com/scl/fi/.../DX-Survey-Analysis-Jan-2.paper)
- [Experiment Guide - Confluence](https://company.atlassian.net/wiki/spaces/TEXP/pages/.../Experiment+Guide)
- [Misc Document](https://example.com/scl/fi/.../document.paper)

---

**Summary:**
- **Total Documents**: N
- **Confluence Pages**: N
- **Paper Docs**: N
- **1:1s**: N
- **Meetings**: N
- **Projects**: N
- **Planning**: N
- **Technical**: N
- **Other**: N
```

**Save the report as:**

```bash
# Generate timestamp for filename
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Save report
mkdir -p memory/recent_docs
cat > memory/recent_docs/recent-docs-$TIMESTAMP.md << 'EOF'
[Generated report content here]
EOF

echo "Report saved to: memory/recent_docs/recent-docs-$TIMESTAMP.md"
```

### Step 6: Clean Up

Remove temporary files:

```bash
rm -rf $TMP_DIR
```

## Categorization Logic

### Pattern Matching Rules

**1:1s:**
- URL contains: `11`, `1-1`, `1_1`
- Title contains (case-insensitive): "1:1", "1-1", "11", "one-on-one"
- Pattern: `[Name]-[Name]-11` or `[Name] & [Name] 1:1`

**Meetings:**
- Title contains: "Meeting", "Notes", "Vibe Check", "Stand-Up", "Standup", "Sync", "Review", "Demo", "LT", "XLT", "Weekly"
- URL space names: "Meeting", "Notes"
- Exclude if already categorized as 1:1

**Projects:**
- Title contains: project codes like "C1", "C1.1", "DBX-", "TEXP-", "PROJ-"
- Title contains: "Project Brief", "Project Review", "Epic", "Initiative"
- URL contains: `/browse/` (JIRA links)

**Planning:**
- Title contains: "Roadmap", "Planning", "OKR", "QBR", "Strategy", "Goals", "Q1", "Q2", "Q3", "Q4", "H1", "H2", "FY", "Path to Flat"
- Keywords: "Monthly", "Quarterly", "Annual"

**Technical:**
- Title contains: "Tech Spec", "Technical", "API", "Design Doc", "Architecture", "Implementation", "Engineering", "RFC"
- URL space names: "Engineering", "Tech", "API"

**Other:**
- Everything that doesn't match above patterns

### Prioritization

If a document matches multiple categories, use this priority order:
1. 1:1s (highest priority)
2. Projects (if contains project codes)
3. Technical (if clearly technical content)
4. Planning (if strategic/planning content)
5. Meetings (if meeting notes)
6. Other (default/fallback)

## Tips

- **Date Calculation**: Use appropriate date command for your OS (macOS uses `-v`, Linux uses `-d`)
- **Title Extraction**: Parse the full Chrome output to get both URLs and titles for better categorization
- **Deduplication**: Some documents appear with multiple URL formats (e.g., tinyurl vs full URL) - deduplicate by title if needed
- **Link Formatting**: Clean up URLs by removing query parameters that aren't essential (auth tokens can stay)
- **Missing Categories**: If a category has no documents, still include the header with a note: "No documents in this category"
- **Long Titles**: Truncate very long document titles to ~80 characters for readability
- **Sorting**: Within each category, sort documents by most recently visited (already sorted from Chrome output)
- **Empty Results**: If no documents found, create a minimal report noting this

## Example Workflow

```bash
# Calculate start date (7 days ago)
START_DATE=$(date -v-7d +%Y-%m-%d)
TODAY=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Create temp directory
TMP_DIR=/tmp/recent_docs_$$
mkdir -p $TMP_DIR

# Fetch documents from Chrome history
echo "Fetching Confluence pages from $START_DATE to $TODAY..."
python3 -m sidekick.clients.chrome list-confluence \
    --start-date $START_DATE \
    --max-results 200 > $TMP_DIR/confluence_raw.txt

echo "Fetching Paper docs from $START_DATE to $TODAY..."
python3 -m sidekick.clients.chrome list-paper \
    --start-date $START_DATE \
    --max-results 200 > $TMP_DIR/paper_raw.txt

# Analyze output and categorize documents
# Generate Markdown report with categorized sections
# Save to memory/recent_docs/recent-docs-$TIMESTAMP.md

# Clean up
rm -rf $TMP_DIR

echo "Report generated: memory/recent_docs/recent-docs-$TIMESTAMP.md"
```

## Output Structure

Final output is saved to `memory/recent_docs/`:
- `recent-docs-YYYYMMDD-HHMMSS.md` - The categorized report

Intermediate artifacts are stored in `/tmp/recent_docs_$$/` during generation:
- `confluence_raw.txt` - Raw Chrome output for Confluence
- `paper_raw.txt` - Raw Chrome output for Paper
- `confluence_urls.txt` - Extracted Confluence URLs
- `paper_urls.txt` - Extracted Paper URLs

These temporary files are deleted after the report is generated.

## Updating the Report

To generate a fresh report with current data:

```bash
# Simply run the agent again - it will create a new timestamped file
# Old reports remain in memory/recent_docs/ for historical reference
```

## Error Handling

- **No Chrome history**: Note in report that Chrome history couldn't be accessed
- **Empty results**: Create minimal report noting no documents found in date range
- **Chrome not found**: Provide helpful error about Chrome client requirements
- **Date calculation errors**: Fall back to 7-day offset if date command fails
