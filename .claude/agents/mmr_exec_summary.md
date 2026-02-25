---
name: mmr_exec_summary
description: Generate executive summary from MMR (Monthly Metric Review) Confluence pages
argument-hint: <confluence-page-url>
allowed-tools: Bash, Read
auto-approve: true
---

# MMR Executive Summary Agent

Generate structured executive summaries from Monthly Metric Review (MMR) Confluence pages.

## Purpose

Monthly Metric Reviews (MMRs) are comprehensive Confluence documents (often 7000+ lines) that track operational metrics, severity incidents, and action items for engineering teams. These documents contain detailed tables and extensive data, making it time-consuming to extract executive-level insights.

This agent automates the generation of concise executive summaries by:
- Extracting severity incident counts (SEV 0/1 and SEV 2/3)
- Identifying completed action items from the MMR AIs section
- Analyzing critical metrics from Key Concerns with JIRA context
- Recognizing team contributions from Key Improvements
- Enriching JIRA issues with status and resolution details

The output follows a consistent template format suitable for executive communication.

## Prerequisites

- **pandoc** installed: `brew install pandoc`
- **Configured credentials** in `.env` file:
  - `ATLASSIAN_EMAIL` and `ATLASSIAN_API_TOKEN` for Confluence and JIRA access
- Valid Confluence URL to an MMR page

## Usage

The agent is invoked through Claude Code by providing an MMR Confluence URL:

```
"Create an executive summary for the MMR at https://company.atlassian.net/wiki/spaces/Core/pages/..."
```

The agent will:
1. Fetch the Confluence page HTML
2. Convert to markdown for parsing
3. Extract and enrich JIRA issues
4. Generate a structured executive summary
5. Save to `memory/mmr_exec_summary/[slug].md`

**Note**: This agent runs with `auto-approve: true`, meaning all commands execute without user confirmation for streamlined processing.

## Workflow

### Phase 1: Setup and Fetch Confluence Content

```bash
# Create temporary working directory
TMP_DIR=/tmp/mmr_exec_summary_$$
mkdir -p $TMP_DIR

# Set up cleanup trap
trap "rm -rf $TMP_DIR" EXIT

# Validate prerequisites
if ! command -v pandoc &> /dev/null; then
  echo "Error: pandoc not found. Install with: brew install pandoc" >&2
  exit 1
fi

# Extract Confluence URL from user argument
CONFLUENCE_URL="$1"
if [ -z "$CONFLUENCE_URL" ]; then
  echo "Error: Confluence URL required" >&2
  echo "Usage: Generate executive summary from <confluence-url>" >&2
  exit 1
fi

echo "Fetching MMR document from Confluence..."

# Fetch Confluence content as HTML
python3 -m sidekick.clients.confluence get-content-from-link "$CONFLUENCE_URL" > $TMP_DIR/mmr.html 2>&1
if [ $? -ne 0 ]; then
  echo "Error: Failed to fetch Confluence page" >&2
  cat $TMP_DIR/mmr.html >&2
  exit 1
fi

echo "✓ Fetched $(wc -l < $TMP_DIR/mmr.html | tr -d ' ') lines of HTML"

# Convert HTML to Markdown using pandoc
python3 -m sidekick.clients.markdown from-html $TMP_DIR/mmr.html $TMP_DIR/mmr.md
if [ $? -ne 0 ]; then
  echo "Error: Failed to convert HTML to markdown" >&2
  exit 1
fi

echo "✓ Converted to $(wc -l < $TMP_DIR/mmr.md | tr -d ' ') lines of markdown"
```

### Phase 2: Extract and Fetch JIRA Issues

```bash
# Extract all JIRA issue keys using pattern: PROJECT-NUMBER
# Common patterns: PROJ-1234, ENG-5678, TEAM-123, WORK-456
# Note: Confluence HTML embeds extra characters (UUIDs), limit to 1-4 digits to catch most real issues
# Use word boundary \b to stop at non-word characters
grep -Eo '\b[A-Z][A-Z0-9]+-[0-9]{1,4}\b' $TMP_DIR/mmr.md | sort -u > $TMP_DIR/jira_keys.txt

ISSUE_COUNT=$(wc -l < $TMP_DIR/jira_keys.txt | tr -d ' ')
echo "Found $ISSUE_COUNT unique JIRA issues in MMR document"

# Fetch each JIRA issue sequentially
# If a fetch fails (404), try removing the last digit and retry
# Continue on individual failures - some issues may not exist
if [ -s $TMP_DIR/jira_keys.txt ]; then
  echo "Fetching JIRA issue details..."

  FETCH_SUCCESS=0
  FETCH_FAILED=0

  while IFS= read -r issue_key; do
    # Try fetching the issue as-is first
    if python3 -m sidekick.clients.jira get-issue "$issue_key" > "$TMP_DIR/jira_${issue_key}.json" 2>/dev/null; then
      FETCH_SUCCESS=$((FETCH_SUCCESS + 1))
      continue
    fi

    # If that failed and the issue has more than 1 digit, try removing the last digit
    project=$(echo "$issue_key" | cut -d"-" -f1)
    number=$(echo "$issue_key" | cut -d"-" -f2)

    if [ ${#number} -gt 1 ]; then
      shorter_number=${number%?}
      retry_key="${project}-${shorter_number}"
      if python3 -m sidekick.clients.jira get-issue "$retry_key" > "$TMP_DIR/jira_${retry_key}.json" 2>/dev/null; then
        echo "  Retried: $issue_key → $retry_key (success)"
        FETCH_SUCCESS=$((FETCH_SUCCESS + 1))
        continue
      fi
    fi

    echo "  Warning: Could not fetch $issue_key"
    FETCH_FAILED=$((FETCH_FAILED + 1))
  done < $TMP_DIR/jira_keys.txt

  echo "✓ Successfully fetched $FETCH_SUCCESS JIRA issues ($FETCH_FAILED failed)"
fi
```

### Phase 3: Parse MMR Content Structure

```bash
echo "Parsing MMR sections..."

# Extract Summary section (between "# Summary" and next "# " header)
# This contains Key Improvements and Key Concerns - the executive view
sed -n '/^# Summary/,/^# [A-Z]/p' $TMP_DIR/mmr.md | head -n -1 > $TMP_DIR/summary_section.txt

if [ ! -s $TMP_DIR/summary_section.txt ]; then
  echo "Warning: Could not find Summary section in MMR" >&2
fi

# Extract Key Improvements subsection
sed -n '/### Key Improvements/,/### Key Concerns/p' $TMP_DIR/summary_section.txt 2>/dev/null | head -n -1 > $TMP_DIR/key_improvements.txt

# Extract Key Concerns subsection
sed -n '/### Key Concerns/,/^summary$/p' $TMP_DIR/summary_section.txt 2>/dev/null | head -n -1 > $TMP_DIR/key_concerns.txt

# If the above pattern doesn't work, try extracting until the table starts
if [ ! -s $TMP_DIR/key_concerns.txt ]; then
  sed -n '/### Key Concerns/,/^\*\*Quality Dimension\*\*/p' $TMP_DIR/summary_section.txt 2>/dev/null | head -n -1 > $TMP_DIR/key_concerns.txt
fi

echo "✓ Extracted Key Improvements ($(wc -l < $TMP_DIR/key_improvements.txt | tr -d ' ') lines)"
echo "✓ Extracted Key Concerns ($(wc -l < $TMP_DIR/key_concerns.txt | tr -d ' ') lines)"

# Extract SEV counts from summary table
# Look for "SEV 0/1" or "SEV 2/3" followed by count values with color styling
grep -A 20 "^\*\*SEVs\*\*" $TMP_DIR/summary_section.txt | grep -E "SEV 0/1|SEV 2/3|style=\"color:" > $TMP_DIR/sev_section.txt 2>/dev/null

# Extract MMR AIs section
# This contains the list of MMR action items
sed -n '/^# MMR AIs/,/^# [A-Z]/p' $TMP_DIR/mmr.md 2>/dev/null | head -n -1 > $TMP_DIR/mmr_ais_section.txt

echo "✓ Parsed MMR structure"
```

### Phase 4: Generate Executive Summary

```bash
echo "Generating executive summary..."

# Get JIRA base URL for links
JIRA_BASE_URL=$(python3 -c "from sidekick.config import load_jira_config; cfg=load_jira_config(); print(cfg['base_url'])" 2>/dev/null || echo "https://company.atlassian.net")

# Helper function to get JIRA field from JSON
get_jira_field() {
  local issue_key=$1
  local field_path=$2
  local json_file="$TMP_DIR/jira_${issue_key}.json"

  if [ ! -f "$json_file" ]; then
    echo "N/A"
    return
  fi

  python3 -c "
import json
import sys
try:
    with open('$json_file') as f:
        data = json.load(f)
    result = data$field_path
    print(result if result else 'N/A')
except:
    print('N/A')
" 2>/dev/null
}

# Helper function to format JIRA link
jira_link() {
  echo "[$1]($JIRA_BASE_URL/browse/$1)"
}

# Start building the summary
cat > $TMP_DIR/summary.md << 'EOF_HEADER'
# Exec Summary

EOF_HEADER

# Section 1: Severity Incidents
echo "### **Severity Incidents:**" >> $TMP_DIR/summary.md
echo "" >> $TMP_DIR/summary.md

# Parse SEV counts from the extracted section
# Look for the Jan (current) column which should have the current counts
# Format: [0]{style="color: rgb(54,179,126);"} for green (no incidents)
SEV01_COUNT=$(grep -A 3 "SEV 0/1" $TMP_DIR/sev_section.txt 2>/dev/null | grep -Eo '\[[0-9]+\]' | tail -1 | tr -d '[]' || echo "0")
SEV23_COUNT=$(grep -A 3 "SEV 2/3" $TMP_DIR/sev_section.txt 2>/dev/null | grep -Eo '\[[0-9]+\]' | tail -1 | tr -d '[]' || echo "0")

# Get details from SEVs section if there were incidents
SEV_DETAILS=""
if [ "$SEV01_COUNT" != "0" ]; then
  # Extract brief description from SEVs section
  SEV_DETAILS=$(sed -n '/^# SEVs/,/^# [A-Z]/p' $TMP_DIR/mmr.md 2>/dev/null | head -50 | grep -A 2 "SEV-" | head -5 | sed 's/^/    /')
fi

if [ "$SEV01_COUNT" != "0" ] && [ -n "$SEV_DETAILS" ]; then
  echo "- **SEV 0/1**: $SEV01_COUNT incident(s)" >> $TMP_DIR/summary.md
else
  echo "- **SEV 0/1**: $SEV01_COUNT incidents" >> $TMP_DIR/summary.md
fi

echo "" >> $TMP_DIR/summary.md
echo "- **SEV 2/3**: $SEV23_COUNT incidents" >> $TMP_DIR/summary.md
echo "" >> $TMP_DIR/summary.md

# Section 2: Completed MMR AIs
echo "### **Completed MMR AIs:**" >> $TMP_DIR/summary.md
echo "" >> $TMP_DIR/summary.md

# Extract JIRA keys from MMR AIs section
MMR_AI_KEYS=$(grep -Eo '\b[A-Z][A-Z0-9]+-[0-9]{1,4}\b' $TMP_DIR/mmr_ais_section.txt 2>/dev/null | sort -u)

if [ -n "$MMR_AI_KEYS" ]; then
  # Check status of each MMR AI
  for issue_key in $MMR_AI_KEYS; do
    status=$(get_jira_field "$issue_key" "['fields']['status']['name']")
    if [ "$status" = "Done" ] || [ "$status" = "Resolved" ] || [ "$status" = "Closed" ]; then
      echo "- $(jira_link $issue_key)" >> $TMP_DIR/summary.md
    fi
  done
else
  echo "- None found in MMR AIs section" >> $TMP_DIR/summary.md
fi

echo "" >> $TMP_DIR/summary.md

# Section 3: Critical Metrics (Key Concerns)
echo "### **Critical Metrics (Red items with non-zero counts):**" >> $TMP_DIR/summary.md
echo "" >> $TMP_DIR/summary.md

# Extract JIRA keys from Key Concerns section
CONCERN_KEYS=$(grep -Eo '\b[A-Z][A-Z0-9]+-[0-9]{1,4}\b' $TMP_DIR/key_concerns.txt 2>/dev/null | sort -u)

# Count done vs total
TOTAL_CONCERNS=0
DONE_CONCERNS=0

if [ -n "$CONCERN_KEYS" ]; then
  for issue_key in $CONCERN_KEYS; do
    status=$(get_jira_field "$issue_key" "['fields']['status']['name']")
    if [ "$status" != "N/A" ]; then
      TOTAL_CONCERNS=$((TOTAL_CONCERNS + 1))
      if [ "$status" = "Done" ] || [ "$status" = "Resolved" ] || [ "$status" = "Closed" ]; then
        DONE_CONCERNS=$((DONE_CONCERNS + 1))
      fi
    fi
  done

  echo "Issues identified in Key Concerns section -- $DONE_CONCERNS/$TOTAL_CONCERNS are marked done" >> $TMP_DIR/summary.md
  echo "" >> $TMP_DIR/summary.md

  # Detail each concern issue
  ISSUE_NUM=1
  for issue_key in $CONCERN_KEYS; do
    json_file="$TMP_DIR/jira_${issue_key}.json"
    if [ ! -f "$json_file" ]; then
      continue
    fi

    summary=$(get_jira_field "$issue_key" "['fields']['summary']")
    status=$(get_jira_field "$issue_key" "['fields']['status']['name']")
    description=$(get_jira_field "$issue_key" "['fields']['description']")

    echo "#### Issue $ISSUE_NUM: $(jira_link $issue_key)" >> $TMP_DIR/summary.md
    echo "" >> $TMP_DIR/summary.md

    # Extract the concern description from Key Concerns section
    concern_text=$(grep -A 5 "$issue_key" $TMP_DIR/key_concerns.txt 2>/dev/null | head -10)

    if [ -n "$concern_text" ]; then
      # Extract metric/issue description (first line of concern)
      metric_desc=$(echo "$concern_text" | head -1 | sed 's/^[*-] //' | sed 's/\*\*//g')
      echo "- **Context**: $metric_desc" >> $TMP_DIR/summary.md
    fi

    # Extract findings from JIRA description
    echo "- **Findings**:" >> $TMP_DIR/summary.md
    if [ "$description" != "N/A" ] && [ -n "$description" ]; then
      # Try to extract numbered or bulleted list items
      echo "$description" | grep -E '^\s*[-*•]|^[0-9]+\.' | head -3 | sed 's/^/  /' >> $TMP_DIR/summary.md
      if [ $(echo "$description" | grep -E '^\s*[-*•]|^[0-9]+\.' | wc -l) -eq 0 ]; then
        # No list found, just show first line of description
        echo "$description" | head -1 | sed 's/^/  - /' >> $TMP_DIR/summary.md
      fi
    else
      echo "  - See JIRA issue for details" >> $TMP_DIR/summary.md
    fi

    # Show fix status
    echo "- **Status**: $status" >> $TMP_DIR/summary.md
    echo "" >> $TMP_DIR/summary.md

    ISSUE_NUM=$((ISSUE_NUM + 1))
  done
else
  echo "No critical metric issues found in Key Concerns" >> $TMP_DIR/summary.md
  echo "" >> $TMP_DIR/summary.md
fi

# Section 4: Other JIRA Issues
echo "### **Other JIRA issues created:**" >> $TMP_DIR/summary.md
echo "" >> $TMP_DIR/summary.md

# Find issues not already mentioned
OTHER_ISSUES=""
for issue_key in $(cat $TMP_DIR/jira_keys.txt); do
  # Skip if already in concerns or MMR AIs
  if echo "$CONCERN_KEYS" | grep -q "$issue_key"; then
    continue
  fi
  if echo "$MMR_AI_KEYS" | grep -q "$issue_key"; then
    continue
  fi

  json_file="$TMP_DIR/jira_${issue_key}.json"
  if [ ! -f "$json_file" ]; then
    continue
  fi

  summary=$(get_jira_field "$issue_key" "['fields']['summary']")
  status=$(get_jira_field "$issue_key" "['fields']['status']['name']")

  if [ "$summary" != "N/A" ]; then
    echo "- $(jira_link $issue_key): $summary [$status]" >> $TMP_DIR/summary.md
    OTHER_ISSUES="yes"
  fi
done

if [ -z "$OTHER_ISSUES" ]; then
  echo "- None" >> $TMP_DIR/summary.md
fi

echo "" >> $TMP_DIR/summary.md

# Section 5: Other Notes (Key Improvements + Kudos)
echo "## Other Notes" >> $TMP_DIR/summary.md
echo "" >> $TMP_DIR/summary.md

if [ -s $TMP_DIR/key_improvements.txt ]; then
  echo "### Key Improvements" >> $TMP_DIR/summary.md
  echo "" >> $TMP_DIR/summary.md
  # Extract the bullet points from Key Improvements
  cat $TMP_DIR/key_improvements.txt | grep -E '^- ' | head -10 >> $TMP_DIR/summary.md
  echo "" >> $TMP_DIR/summary.md
fi

# Extract assignees from completed issues for kudos
echo "### Kudos" >> $TMP_DIR/summary.md
echo "" >> $TMP_DIR/summary.md

KUDOS_FOUND=""
for issue_key in $(cat $TMP_DIR/jira_keys.txt); do
  status=$(get_jira_field "$issue_key" "['fields']['status']['name']")
  if [ "$status" = "Done" ] || [ "$status" = "Resolved" ]; then
    assignee=$(get_jira_field "$issue_key" "['fields']['assignee']['displayName']")
    if [ "$assignee" != "N/A" ] && [ -n "$assignee" ]; then
      summary=$(get_jira_field "$issue_key" "['fields']['summary']")
      echo "- **$assignee**: Completed $(jira_link $issue_key) - $summary" >> $TMP_DIR/summary.md
      KUDOS_FOUND="yes"
    fi
  fi
done

if [ -z "$KUDOS_FOUND" ]; then
  echo "- Team continues to make progress on operational excellence" >> $TMP_DIR/summary.md
fi

echo "" >> $TMP_DIR/summary.md
echo "✓ Generated executive summary"
```

### Phase 5: Save and Cleanup

```bash
# Create output directory
mkdir -p memory/mmr_exec_summary

# Generate filename slug from page title
TITLE=$(grep -o '<title>[^<]*</title>' $TMP_DIR/mmr.html | sed 's/<[^>]*>//g' | sed 's/ - Confluence$//' | sed 's/ - [A-Za-z]* Confluence$//')

# Convert to slug: lowercase, spaces to hyphens, remove special chars
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//')

# Default to timestamp if slug generation fails
if [ -z "$SLUG" ] || [ "$SLUG" = "-" ]; then
  SLUG="mmr-exec-summary-$(date +%Y%m%d-%H%M%S)"
fi

OUTPUT_FILE="memory/mmr_exec_summary/${SLUG}.md"

# Copy summary to output location
cp $TMP_DIR/summary.md "$OUTPUT_FILE"

# Clean up temporary files (trap will handle this)
# rm -rf $TMP_DIR

# Report completion
echo ""
echo "✓ Executive summary saved to: $OUTPUT_FILE"
echo ""
echo "Summary contains:"
echo "  - Severity incidents: SEV 0/1 ($SEV01_COUNT) and SEV 2/3 ($SEV23_COUNT)"
echo "  - Critical metrics: $TOTAL_CONCERNS issues identified, $DONE_CONCERNS completed"
echo "  - Other improvements and team contributions"
```

## Parsing Strategy

### MMR Document Structure

MMRs follow a consistent structure validated with real documents:

1. **Legend** (line 1) - Threshold definitions, skip this
2. **Summary** (line 32-547):
   - **Key Improvements** - Team achievements with kudos
   - **Key Concerns** - Critical issues with embedded JIRA keys
   - **Summary table** - High-level metric counts across 3 months
3. **Detailed sections** (line 548+):
   - Code Coverage, SEVs, CX Escalations, Quarantined Tests
   - MMR AIs, Open Bugs
   - Service Availability, Service Latency
   - Edison Page metrics (Availability, TTVC, LCP)

### Key Parsing Insights

- **Focus on Summary section**: Contains the executive view already
- **JIRA key extraction**: Use pattern `\b[A-Z][A-Z0-9]+-[0-9]{1,4}\b` to extract clean issue keys
  - Confluence embeds extra characters like: "PROJ-123d6fe18a-c84e-31b0-943c-6e5ccea56518System Jira"
  - Word boundaries `\b` prevent UUID digits from being captured
  - Limit to 1-4 digits (e.g., TEXP-2863 not TEXP-28635) to avoid false matches
  - If a JIRA fetch fails (404), the agent retries by removing the last digit
- **Status colors**: Metrics use inline styling (not table columns)
  - Green (OK): `style="color: rgb(54,179,126);"`
  - Yellow (Warning): `style="color: rgb(255,153,31);"`
  - Red (Critical): `style="color: rgb(191,38,0);"`
- **SEV counts**: Extract from summary table, look for current month column
- **MMR AIs**: Dedicated section for action items

### Section Extraction

```bash
# Summary section (most important)
sed -n '/^# Summary/,/^# [A-Z]/p' FILE | head -n -1

# Key Improvements
sed -n '/### Key Improvements/,/### Key Concerns/p' FILE | head -n -1

# Key Concerns
sed -n '/### Key Concerns/,/^summary$/p' FILE | head -n -1

# MMR AIs
sed -n '/^# MMR AIs/,/^# [A-Z]/p' FILE | head -n -1
```

## Error Handling

Common issues and mitigations:

1. **Confluence page not accessible**:
   - Verify authentication credentials in `.env`
   - Check URL format and permissions
   - Error message shows HTTP status details

2. **JIRA issues not found**:
   - Some issues may be placeholders or drafts
   - Agent continues processing, shows warning
   - Uses `|| true` to prevent stopping on individual failures

3. **Missing MMR sections**:
   - Checks for empty sections and warns user
   - Continues with available data
   - Generates summary with "N/A" for missing sections

4. **pandoc not installed**:
   - Validates at start of execution
   - Provides installation command
   - Exits early with clear error message

5. **Malformed markdown**:
   - Uses flexible sed patterns
   - Tries multiple patterns for section extraction
   - Falls back to basic extraction if specific patterns fail

## Tips

- **Temp files**: All intermediate artifacts saved to `/tmp/mmr_exec_summary_$$`
  - Automatically cleaned up by trap on exit
  - Only final summary remains in `memory/mmr_exec_summary/`

- **JIRA enrichment**: Parallel fetching (max 5 concurrent) speeds up execution
  - Typical MMR has 10-30 JIRA issues
  - Fetching takes 5-10 seconds total

- **Summary section is key**: Don't parse entire 7000+ line document
  - Key Concerns already summarizes critical issues
  - Key Improvements contains team achievements
  - This approach is faster and more reliable

- **Slug generation**: Creates readable filenames from page titles
  - Example: "Team Alpha MMR 2026 Jan" → "team-alpha-mmr-2026-jan.md"
  - Falls back to timestamp if title extraction fails

- **JIRA links**: Uses configured JIRA base URL from `.env`
  - Format: `[PROJ-123](https://company.atlassian.net/browse/PROJ-123)`
  - Makes issues clickable in markdown viewers

- **Status checking**: Only counts issues with successful JIRA API fetch
  - Avoids false counts from placeholder issues
  - Shows realistic progress (X/Y done)

## Example Invocation

```
User: "Create an executive summary for the January MMR"
      "URL: https://company.atlassian.net/wiki/spaces/ENG/pages/1234567890"

Agent execution:
✓ Fetched 8234 lines of HTML
✓ Converted to 7333 lines of markdown
Found 15 unique JIRA issues in MMR document
✓ Successfully fetched 12 JIRA issues
✓ Extracted Key Improvements (42 lines)
✓ Extracted Key Concerns (68 lines)
✓ Parsed MMR structure
✓ Generated executive summary
✓ Executive summary saved to: memory/mmr_exec_summary/team-alpha-mmr-2026-jan.md

Summary contains:
  - Severity incidents: SEV 0/1 (0) and SEV 2/3 (0)
  - Critical metrics: 5 issues identified, 0 completed
  - Other improvements and team contributions
```

## Output Structure

Use format: 
# Exec Summary

### **Severity Incidents:** 

- **SEV 0/1**: X incidents - recap of each one 

- **SEV 2/3**: 0 incidents

### **Completed MMR AIs:** 

- SHARE-7407
- SHARE-7573
- SHARE-7574

### **Critical Metrics (Red items with non-zero counts):**

High level voice over -- X/Y are marked done

#### Issue 1: SHARE-7769

- metric that's read and the values

- Findings:

  1.  Finding 1
  1.  Finding 2

- Fix was XXX

#### Issue 2: SHARE-7770

- metric that's read and the values

- Findings:

  1.  Finding 1
  1.  Finding 2

- Fix was XXX

### **Other JIRA issues created:** 

- SHARE-7647 description and resolution 
- SHARE-7650 description and resolution 

## Other Notes

Any other interesting work for findings for this MMR. Give kudos to people if you can.

Final output saved to `memory/mmr_exec_summary/`:
- `[page-slug].md` - The executive summary (only file in directory)

Intermediate artifacts in `/tmp/mmr_exec_summary_$$/` (auto-cleaned):
- `mmr.html` - Raw HTML from Confluence
- `mmr.md` - Converted markdown (7000+ lines)
- `summary_section.txt` - Extracted Summary section
- `key_improvements.txt` - Key Improvements bullet points
- `key_concerns.txt` - Key Concerns bullet points
- `sev_section.txt` - SEV counts and details
- `mmr_ais_section.txt` - MMR AIs section
- `jira_keys.txt` - List of all JIRA issue keys
- `jira_PROJ-123.json` - JIRA API responses (one per issue)
- `summary.md` - Generated executive summary

The temp directory is automatically removed by the trap, keeping only the final summary in memory.
