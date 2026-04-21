---
name: epic_assignment
description: Assign active Epics to Roadmap Initiatives based on recent activity
argument-hint: <root-issue> [project] [issue-type] [days]
auto-approve: false
---

# Epic Assignment Agent

This agent identifies recently active Epics without parents and generates recommendations for linking them to appropriate parent issues.

## Purpose

Ensures active Epics are properly linked to Parent Epics for better project tracking and visibility. Many Epics may be created without parents, making it difficult to track which roadmap item they support.

## Prerequisites

This agent requires the following sections in `CLAUDE.local.md`:

### Teams Section
```markdown
## Teams

### My Teams
- Team Name, manager Name, JIRA Project KEY1
- Team Name, manager Name, JIRA Project KEY2
```

### Projects Section
```markdown
## Projects

The Roadmap issues are represented by the JIRA jql query:
```
project = "PROJECT" and issuetype = "Roadmap Issue Type"
```
```

## Workflow

### Step 1: Extract Configuration

You already have context form `CLAUDE.local.md` for
1. JIRA project for my teems
2. JQL for roadmap issues 

### Step 2: Query Recent Activity

Query JIRA for all issues updated in the specified time period (default 30 days):

```bash
python3 -m sidekick.clients.jira query 'project IN ("KEY1", "KEY2", "KEY3") AND updated >= -30d' 200
```

Note: escape project keys with double quotes because they can be reserved words

Fields to extract: `key`, `summary`, `issuetype`, `parent`, `labels`, `description`, `updated`

### Step 3: Extract Epics

From query results, identify Epics:
1. Epics: Issues where `issuetype.name == "Epic"`
2. Non-Epics: get parent Epics by looking at the `parent` field
3. Create a set of distinct Epics 

From THOSE Epics, create two collections:
- **Epics without parents**: `parent` field is None or empty
- **Epics with parents**: `parent` field exists (for reference)

Group by project for the analysis report.

### Step 4: Query Roadmap Initiatives and Build Hierarchies

Use the /jira-roadmap skill to query for all relevant potential parents, starting at a root issue. 

This captures:
- All Epics currently under this initiative
- The complete structure of work already organized under this initiative

### Step 5: Match Epics to Roadmap Initiatives

For each Epic without a parent, analyze potential matches based on:
- **Label overlap**: Shared labels between Epic and Initiative (or its child Epics)
- **Keyword similarity**: Keyword matches in summaries and descriptions (Epic vs Initiative + child Epics)
- **Theme alignment**: Does this Epic fit the theme/focus area of existing child Epics?
- **Sibling similarity**: Does this Epic resemble existing Epics under the Initiative?

Scoring system:
- Label match: +15 points per shared label
- Summary keyword overlap: +10 points per keyword
- Description keyword overlap: +5 points per keyword
- Sibling Epic similarity: +8 points per keyword match with existing child Epics

Assign confidence levels:
- **High**: Score >= 30 (strong label/keyword overlap)
- **Medium**: Score >= 15 (moderate overlap)
- **Low**: Score >= 5 (weak overlap, manual review needed)
- **No Match**: Score < 5

### Step 6: Generate Analysis Report

Save to `memory/epic_assignment_analysis.md`:

```markdown
# Epic Assignment Analysis
**Generated**: [timestamp]
**Activity Period**: Last [N] days

## Summary
- Total issues updated: X
- Epics identified: Y
- Epics without parents: Z
- Epics with parents: W

## Epics by Project

### Project: KEY1

#### Epics without parents
- [KEY1-123](https://company.atlassian.net/browse/KEY1-123): Epic Summary
  - Labels: label1, label2
  - Updated: YYYY-MM-DD

#### Epics with parents
- [KEY1-456](https://company.atlassian.net/browse/KEY1-456): Epic Summary
  - Parent: [INIT-789](https://company.atlassian.net/browse/INIT-789) - Initiative Name
  - Updated: YYYY-MM-DD
```

### Step 7: Generate Recommendations Report

Save to `memory/epic_assignment_recommendations.md`:

```markdown
# Epic Assignment Recommendations
**Generated**: [timestamp]

## Proposed Assignments

### High Confidence Matches
- **[KEY1-123](https://company.atlassian.net/browse/KEY1-123)**: Epic Summary
  - **Recommended Parent**: [INIT-456](https://company.atlassian.net/browse/INIT-456) - Initiative Summary
  - **Confidence**: High (score: 45)
  - **Reasoning**: Shared labels: label1, label2 • Keyword overlap with initiative • Similar to existing child Epics: KEY1-100, KEY1-105
  - **Existing Epics under this Initiative**: 3 Epics with similar themes

### Medium Confidence Matches
- **[KEY2-789](https://company.atlassian.net/browse/KEY2-789)**: Epic Summary
  - **Recommended Parent**: [INIT-234](https://company.atlassian.net/browse/INIT-234) - Initiative Summary
  - **Confidence**: Medium
  - **Reasoning**: [Explanation with caveats]

### Low Confidence / Needs Manual Review
- **[KEY3-456](https://company.atlassian.net/browse/KEY3-456)**: Epic Summary
  - **Possible Parents**:
    - [INIT-111](https://company.atlassian.net/browse/INIT-111) - Initiative A
    - [INIT-222](https://company.atlassian.net/browse/INIT-222) - Initiative B
  - **Confidence**: Low
  - **Reasoning**: [Multiple potential matches, manual review needed]

### No Match Found
- **[KEY4-789](https://company.atlassian.net/browse/KEY4-789)**: Epic Summary
  - **Reasoning**: No Roadmap Initiatives with relevant labels or keywords

## Summary Statistics
- High confidence: X
- Medium confidence: Y
- Low/manual review: Z
- No match: W
```

### Step 8: User Confirmation

Output to console:

```
I've analyzed X Epics without parents and generated recommendations.

Summary:
- High confidence matches: X
- Medium confidence matches: Y
- Needs manual review: Z
- No match found: W

Reports saved to:
- memory/epic_assignment_analysis.md
- memory/epic_assignment_recommendations.md

Would you like me to:
1. Proceed with HIGH confidence assignments only? (type "high")
2. Proceed with HIGH + MEDIUM confidence assignments? (type "all")
3. Skip updates and just review? (type "skip")
```

Wait for user response before proceeding.

### Step 9: Execute Updates

Based on user selection, update JIRA for each confirmed Epic assignment:

```bash
python3 -m sidekick.clients.jira update-issue KEY1-123 '{"parent": {"key": "INIT-456"}}'
```

**Error Handling:**
- Catch and log all errors without stopping
- Continue processing remaining Epics if one fails
- Report all failures in the changelog

### Step 10: Generate Change Log

After executing updates, save to `memory/epic_assignment_changelog.md`:

```markdown
# Epic Assignment Change Log
**Executed**: [timestamp]
**Execution Mode**: [High only / High + Medium / Skipped]

## Successfully Updated
- [KEY1-123](https://company.atlassian.net/browse/KEY1-123): Epic Summary
  - **Parent Set**: [INIT-456](https://company.atlassian.net/browse/INIT-456) - Initiative Summary
  - **Confidence**: High
  - **Time**: [timestamp]

## Failed Updates
- [KEY2-789](https://company.atlassian.net/browse/KEY2-789): Epic Summary
  - **Attempted Parent**: [INIT-234](https://company.atlassian.net/browse/INIT-234)
  - **Error**: [error message]
  - **Time**: [timestamp]

## Not Updated (Below Threshold)
- [KEY3-456](https://company.atlassian.net/browse/KEY3-456): Epic Summary
  - **Reason**: Medium confidence, user chose "high" only
  - **Recommended Parent**: [INIT-111](https://company.atlassian.net/browse/INIT-111)

## Summary
- Successfully assigned: X
- Failed: Y
- Skipped: Z
```

## Output Files

All reports are saved to the `memory/` directory:

- **epic_assignment_analysis.md** - Initial analysis of all Epics (with and without parents)
- **epic_assignment_recommendations.md** - Matching recommendations with confidence levels
- **epic_assignment_changelog.md** - Log of updates made (created only after execution)

## Edge Cases

1. **Epic already has parent**: Appears in "Epics with parents" section only
2. **Reserved JQL keyword**: Project names that are keywords must be quoted
3. **Update permission failure**: Logged as error, processing continues
4. **No Epics without parents**: Report states "No Epics without parents found"
5. **No matching Roadmap Initiatives**: Epics appear in "No Match Found" section
6. **Ambiguous matches**: Multiple initiatives listed as options in Low Confidence section


## Verification Steps

After running the agent:

1. **Review analysis report**: Check that Epics are correctly categorized by project
2. **Review recommendations**: Verify confidence levels match reasoning quality
3. **Test dry-run**: Select "skip" to generate reports without making changes
4. **Review changelog**: After updates, verify changelog accurately reflects changes
5. **Check JIRA**: Manually verify a sample of updated Epics show correct parent links

## Notes

- **Hierarchy-based matching**: Uses `get_issue_hierarchy()` to analyze existing Epic structure under each Initiative, enabling "sibling similarity" matching - if an Epic looks like existing Epics under an Initiative, it's likely a good fit
- Agent uses temporary files for intermediate JSON if needed
- Only final reports are saved to memory/ directory
- Agent provides verbose console output showing progress
- All console output uses relative paths for readability
- JIRA parent field syntax: `{"parent": {"key": "PARENT-KEY"}}`
- Default activity window is 30 days (customizable via argument)
- Roadmap Initiatives filtered to 90-day activity window to avoid stale initiatives
- **Matching quality**: Hierarchy analysis significantly improves matching accuracy by considering the context of existing work organization, not just keyword overlap
