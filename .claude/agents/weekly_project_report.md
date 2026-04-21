---
name: project_activity
description: Generate weekly project activity summaries from Slack and JIRA
argument-hint: "[days]"
auto-approve: true
---

# Project Activity Agent

Generate a weekly summary of projects focused on what shipped, demos, risks, and upcoming milestones. Pulls from both Slack channels and JIRA issue comments. Organized by activity level for quick scanning.

## Overview

This agent helps you:
1. Parse all projects from `local/projects.md` with metadata
2. Extract key project status from Slack channels AND JIRA comments
3. Generate executive summary for each project
4. Organize by activity level (High/Medium/Low/None)
5. Generate a scan-able report in 2-3 minutes

## Prerequisites

- `local/projects.md` file with project structure
- Configured Dash MCP for Slack access
- Configured JIRA client for issue access

## Usage Pattern

### Step 1: Parse Projects from local/projects.md

Read `local/projects.md` to extract all projects with their metadata.

For each project section (marked by `###` heading), extract:
- **Project Name**: The heading text (e.g., "Domain Restriction (Basic Gating)")
- **Team**: Team name and manager (e.g., "Team Formation (Dan)")
- **JIRA Team Project**: Project key (e.g., "TFM")
- **JIRA Roadmap Initiative**: All DBX-XXXX issue keys with their URLs
- **Slack Channel**: Channel name and URL (if exists)
- **C1 Category**: Which C1.X section it's under (e.g., "C1.1 - Team Formation")

Create a structured list of all projects with their metadata to process.

### Step 2: Calculate Date Range

Calculate the start date for the time period.
- Default: 7 days (if no argument provided)
- Custom: Use `$ARGUMENTS` if provided (e.g., 14 for 14 days)

```bash
# Calculate start date
DAYS=${ARGUMENTS:-7}
START_DATE=$(date -v-${DAYS}d '+%Y-%m-%d')
END_DATE=$(date '+%Y-%m-%d')
```

### Step 3: Process All Projects

For each project, fetch data from both Slack (if channel exists) and JIRA, then extract structured summary.

#### 3.1 Fetch Slack Messages (if channel exists)

If the project has a Slack channel, use the `/slack` skill approach with `slack_search_messages`:

```json
dash_invoke_search_action(
  action_id="slack_search_messages",
  params={
    "query": "after:YYYY-MM-DD in:#channel-name",
    "max_results": 100,
    "sort": "timestamp",
    "sort_direction": "desc"
  }
)
```

**Handle pagination**: Check for `next_cursor` in response. Fetch additional pages if needed (up to ~100 messages total per channel).

#### 3.2 Fetch JIRA Issue Comments

For each JIRA Roadmap Initiative (DBX-XXXX), fetch recent comments:

```bash
# Use the JIRA client to get issue with comments
python -m sidekick.clients.jira get-issue DBX-XXXX
```

Extract comments from the time period (last N days):
- Filter comments by date (compare `created` field with `START_DATE`)
- Include comment author, timestamp, and body
- Look for status updates, blockers, milestone updates

**Handle errors**: If issue fetch fails (404, auth error), note it and continue.

#### 3.3 Extract Structured Summary

For each project, immediately extract and save (combining Slack + JIRA data):

**Executive Summary:**
Generate a one-sentence summary of the project status based on:
- Recent activity level
- What shipped or key milestones
- Any major blockers
- Overall momentum (progressing, stalled, at risk)
Example: "Project is progressing well with experiment rollout complete; waiting on design approval for next phase."

**Activity Level:**
Count total Slack messages + JIRA comments in time period:
  - **High**: 20+ items
  - **Medium**: 5-19 items
  - **Low**: 1-4 items
  - **None**: 0 items

**Project Metadata:**
Include from `local/projects.md`:
- Team and manager
- JIRA Team Project
- JIRA Roadmap Initiative links
- C1 Category

**What Shipped:**
Search Slack messages AND JIRA comments for keywords (case-insensitive):
- "shipped", "deployed", "released", "launched", "live", "merged", "in production", "completed"
Extract 1-3 bullet points of what was shipped

**Demos:**
Search for keywords:
- "demo", "presentation", "recorded", "showcase", "demoed"
Extract mentions of demos (scheduled or completed)

**Risks:**
Search for keywords:
- "blocker", "blocked", "risk", "issue", "concern", "problem", "stuck", "waiting on", "dependency"
Extract 1-3 key risks or blockers

**Next Milestone:**
Search for keywords and patterns:
- "milestone", "M1", "M2", "M3", etc., "deadline", "target", "due"
- Date patterns: "Apr 28", "2026-04-28", "end of month", "next week"
Extract milestone name/number and target date if found

**Sample Activity:**
Save 3-5 representative items (Slack messages OR JIRA comments) with:
- Source (Slack or JIRA issue key)
- Timestamp (YYYY-MM-DD HH:MM format)
- Author/sender username
- Brief excerpt (first 80 characters)
- Link to message/comment

#### 3.4 Error Handling

If a Slack channel or JIRA issue fails to fetch:
1. **Log the error** with project name, source (Slack/JIRA), and error type
2. **Continue to next source** - DO NOT stop processing
3. **Track failures** in a list by error category:
   - **404 Not Found**: Channel/issue archived, renamed, or doesn't exist
   - **429 Rate Limit**: Too many API calls (wait 30 sec, retry once)
   - **403 Forbidden**: Auth error or no access
   - **Other**: Any other error type
4. **Partial data is OK**: If Slack works but JIRA fails (or vice versa), use what's available

#### 3.5 Context Management

**IMPORTANT**: To preserve context window:
1. **Extract summary immediately** after fetching each project's data (Slack + JIRA)
2. **Write to intermediate file** `memory/project_activity/project_summaries.md` (append mode)
3. **Discard full message/comment content** - only keep the structured summary
4. **Process projects sequentially** (one at a time)
5. **For JIRA**: Only fetch issue summary and recent comments, not full issue details

### Step 4: Generate Final Report

After processing all channels, generate consolidated report.

#### 4.1 Organize by Activity Level and C1 Category

Group projects into sections:
1. **High Activity Projects** (20+ items from Slack + JIRA)
2. **Medium Activity Projects** (5-19 items)
3. **Low Activity Projects** (1-4 items)
4. **No Activity** (0 items)
5. **Errors** (failed to fetch both Slack and JIRA)

Within each activity level, optionally group by C1 category (C1.1, C1.2, etc.).

#### 4.2 Format Report

Create report with this structure:

```markdown
# Project Activity Report
**Generated:** [END_DATE]
**Period:** [START_DATE] to [END_DATE] ([DAYS] days)
**Projects Processed:** [success_count] successful, [failure_count] failed

---

## High Activity Projects (20+ items)

### Project Name
**Executive Summary:** [One-sentence summary of status, momentum, and key issues]

**Metadata:**
- **C1 Category:** C1.X - [Category Name]
- **Team:** [Team Name] ([Manager])
- **JIRA Project:** [KEY]
- **Roadmap Initiatives:** [DBX-1234](link), [DBX-5678](link)
- **Slack Channel:** [#channel-name](link)

**Activity:** [count] items ([X] Slack messages, [Y] JIRA comments)

**What Shipped:**
- [Item 1]
- [Item 2]
- [Or "None mentioned" if nothing found]

**Demos:**
- [Item 1]
- [Or "None mentioned" if nothing found]

**Risks:**
- [Item 1]
- [Item 2]
- [Or "None mentioned" if nothing found]

**Next Milestone:**
- **[Milestone name]: [Description]** - Target: [Date]
- [Or "Not specified in recent activity" if not found]

**Sample Activity:**
- [Slack] [2026-04-20 14:30] @user: [Brief excerpt] [link]
- [DBX-1234] [2026-04-19 09:15] @user: [Brief excerpt] [link]
- [Slack] [2026-04-18 16:20] @user: [Brief excerpt] [link]

---

[Repeat for each High Activity channel]

## Medium Activity Projects (5-19 messages)
[Same format as above]

## Low Activity Projects (1-4 messages)
[Same format as above]

## No Activity (0 items)

### Project Name 1
**Team:** [Team Name] ([Manager])  
**C1 Category:** C1.X - [Category Name]

No Slack or JIRA activity in the last [DAYS] days.

### Project Name 2
**Team:** [Team Name] ([Manager])  
**C1 Category:** C1.X - [Category Name]

No Slack or JIRA activity in the last [DAYS] days.

---

## Errors

### Project Name
**Team:** [Team Name] ([Manager])  
**Slack Error:** [404 Not Found / Rate Limit / N/A]  
**JIRA Error:** [403 Forbidden / N/A]  
**Reason:** [Brief explanation]
```

### Step 5: Save and Report Output

1. **Write final report** to `memory/project-activity-YYYY-MM-DD.md` where YYYY-MM-DD is the end date

2. **Print processing summary:**
   ```
   Project Activity Report Generated
   
   Processed: [success_count] projects successfully
   Failed: [failure_count] projects (partial data may be available)
   Time Period: [START_DATE] to [END_DATE] ([DAYS] days)
   
   Activity Breakdown:
   - High activity (20+ items): [count] projects
   - Medium activity (5-19 items): [count] projects
   - Low activity (1-4 items): [count] projects
   - No activity (0 items): [count] projects
   
   Data Sources:
   - Slack messages: [total_count] across [channel_count] channels
   - JIRA comments: [total_count] across [issue_count] issues
   ```

3. **Output relative path** to the memory file:
   ```bash
   echo "Report saved to: memory/project-activity-${END_DATE}.md"
   ```

4. **Clean up intermediate files**:
   ```bash
   rm -f memory/project_activity/project_summaries.md
   ```

### Step 6: Update local/projects.md with JIRA Status

After generating the report, update `local/projects.md` with the latest JIRA status for each project.

#### 6.1 Collect JIRA Status Data

For each project processed in Step 3, collect the current status of all roadmap initiatives:

```bash
# For each JIRA issue (DBX-XXXX), get the status
python -m sidekick.clients.jira get-issue DBX-XXXX
```

Extract the `status` field (e.g., "In Progress", "Done", "To Do", "Blocked", etc.)

Track:
- Issue key (e.g., DBX-1234)
- Status (e.g., "In Progress")
- Summary (issue title)

#### 6.2 Add Status to projects.md

For each project section in `local/projects.md`, add a **Status** line after the **JIRA Roadmap Initiative** line.

**Format:**
```markdown
- **JIRA Roadmap Initiative:** [DBX-1234](link), [DBX-5678](link)
- **Status:** DBX-1234: In Progress, DBX-5678: Done
```

If multiple initiatives:
- Show status for each issue
- Format: `[Issue-Key]: [Status], [Issue-Key]: [Status]`

If no initiatives or error fetching status:
- Skip adding Status line (or show "Unknown" if line already exists)

#### 6.3 Update the File

Use the Edit tool to update `local/projects.md`:
- For each project section, find the line after "JIRA Roadmap Initiative"
- If "Status" line exists, update it
- If "Status" line doesn't exist, add it as a new line

**Important**: 
- Only update Status lines, don't modify other content
- Preserve exact formatting and spacing
- If a project has no JIRA issues, skip it

#### 6.4 Identify Done Projects

After updating statuses, scan `local/projects.md` for projects where ALL roadmap initiatives are "Done":

1. **Find Done projects**: Projects where every JIRA issue has status "Done" or "Closed"
2. **Count Done projects**: Track how many projects are fully complete
3. **Prepare list**: Create a list of project names that are Done

#### 6.5 Offer to Prune Done Projects

Print to the user:

```
✓ Updated local/projects.md with latest JIRA statuses

Found [count] project(s) with all initiatives Done:
- [Project Name 1] (C1.X)
- [Project Name 2] (C1.X)

Would you like to archive these completed projects?
Options:
1. Remove from projects.md (clean file)
2. Move to archive section at bottom of file
3. Keep as-is (no changes)
```

**Wait for user input** - DO NOT automatically delete or move projects.

If user chooses option 1 (Remove):
- Use Edit tool to remove the entire project section (from `###` heading to next `###` or section boundary)
- Echo confirmation: "Removed [count] completed projects from local/projects.md"

If user chooses option 2 (Archive):
- Create "## Archived Projects" section at bottom of file if doesn't exist
- Move project sections to archive (preserve all metadata including Status)
- Echo confirmation: "Moved [count] completed projects to archive section"

If user chooses option 3 or doesn't respond:
- Do nothing, projects stay in place
- Echo: "Keeping completed projects in place"

## Category Extraction Guidelines

### Executive Summary
Synthesize a one-sentence status update covering:
- **Current state**: What phase/milestone the project is in
- **Key achievement or blocker**: Most important recent development
- **Momentum**: Is it progressing, stalled, at risk, or waiting on something

Examples:
- "Experiment launched and ramped to 90% with positive early results; next phase focused on holdout analysis."
- "Design review blocked on cross-team dependency; M2 milestone at risk of slipping by 2 weeks."
- "No visible activity this period; project may be paused or transitioning."

### What Shipped
Look in both Slack messages and JIRA comments for past-tense or completion language:
- "deployed to production"
- "shipped feature X"
- "released version Y"
- "merged PR"
- "launched experiment"
- "went live"
- "completed"

**Focus on**: Concrete deliverables that shipped in the time period

### Demos
Look for scheduled or completed presentations:
- "demo scheduled for Friday"
- "demoed to leadership"
- "recorded demo"
- "presentation shared"
- "showcase at all-hands"

**Focus on**: Any demos that happened or are scheduled soon

### Risks
Look for blocking or concerning language:
- "blocked by X"
- "waiting on Team Y"
- "risk of missing deadline"
- "dependency on Z"
- "approval needed"
- "concern about X"
- JIRA comments about blockers or issues

**Focus on**: Actionable blockers or risks that need attention

### Next Milestone
Look for forward-looking milestone language:
- "M2 target: April 28"
- "next milestone is X"
- "deadline for Y is Z"
- "launching by end of month"
- "beta testing in May"
- JIRA issue status transitions (e.g., moving to "In Progress")

**Focus on**: The immediate next milestone with target date

## Error Handling Strategy

**For Slack channel errors:**
- **404 Not Found**: Channel renamed or archived → Note in Errors, continue
- **429 Rate Limit**: Wait 30 seconds, retry once → If fails, note in Errors, continue
- **403 Forbidden**: Auth issue or no access → Note in Errors, continue
- **No channel**: Some projects don't have Slack channels → This is normal, skip Slack data

**For JIRA issue errors:**
- **404 Not Found**: Issue doesn't exist or deleted → Note in Errors, continue
- **403 Forbidden**: No access to issue → Note in Errors, continue
- **Invalid issue key**: Parse error from projects.md → Note in Errors, continue
- **No roadmap initiative**: Some projects don't have JIRA issues yet → This is normal, skip JIRA data

**Partial data handling:**
- If Slack works but JIRA fails → Use Slack data only, note JIRA error
- If JIRA works but Slack fails → Use JIRA data only, note Slack error
- If both fail → Report in Errors section with both error details

**NEVER stop processing all projects due to a single project failure.**

## Tips

- **Parsing projects.md**: Look for `###` headings for project names, extract metadata from bullets below
- **Multiple JIRA issues**: A project may have multiple roadmap initiatives - fetch all of them
- **Date Extraction**: Look for various date formats in Slack and JIRA (ISO, natural language, relative)
- **Keyword Matching**: Use case-insensitive matching for category keywords
- **Context Matters**: "blocking" might be resolved - look for current vs. past tense
- **JIRA Comments**: Only fetch comments from the time period, ignore older ones
- **Thread Context**: Important Slack discussions often in threads, but API may not return thread context
- **Sample Activity Selection**: Pick items that represent different topics/days/sources
- **Milestone Dates**: Extract dates even if approximate ("end of month", "next week")
- **Empty Categories**: It's normal and expected to have "None mentioned" for some categories
- **Activity Level**: Combine Slack + JIRA count - high activity projects need more attention
- **Executive Summary**: Should be scan-able - user should understand status in one sentence
- **Metadata Accuracy**: Link to actual JIRA issues and Slack channels from projects.md

## Output Location

- **Final report**: `memory/project-activity-YYYY-MM-DD.md`
- **Intermediate file**: `memory/project_activity/project_summaries.md` (deleted after completion)

## Related Agents

- **weekly_report**: Comprehensive weekly summary (1:1s + meetings + all Slack)
- **kudos**: Extract accomplishments from notes and channels

## Performance Notes

- **Expected time**: ~5-7 minutes for ~15-20 projects (depending on JIRA issue count)
- **Context window**: Stays manageable with immediate extraction and discard pattern
- **API calls per project**: 
  - Slack: ~1-3 calls (search + pagination)
  - JIRA: ~1 call per roadmap initiative
- **Rate limiting**: Should be rare, but handled with retry logic for both Slack and JIRA
- **Parsing**: `local/projects.md` is parsed once at the beginning
