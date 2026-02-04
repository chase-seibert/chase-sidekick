---
name: team-group-analysis
description: Analyze completed work across multiple JIRA projects with automatic theme categorization
argument-hint: <group-name> [time-period]
allowed-tools: Bash, Read
---

# Team Group Analysis Skill

Analyze completed work across multiple JIRA projects organized into "groups" with automatic theme categorization.

When invoked, analyze work for the specified group: $ARGUMENTS

## Configuration

Groups are configured in `.env` file (not checked into git):

```bash
# Define a group called "myteam" with three projects
MYTEAM_GROUP_PROJECTS=PROJ1,PROJ2,PROJ3
MYTEAM_GROUP_JQL=project IN ("PROJ1", "PROJ2", "PROJ3")
```

## Workflow

### Step 1: Query Issues

Query completed issues from your group:

```bash
python3 -m sidekick.clients.jira query \
  'project IN ("PROJ1", "PROJ2", "PROJ3") AND resolved >= -90d AND parent is EMPTY' \
  > team_completed_90days.txt
```

### Step 2: Analyze Themes

Use an analysis script to categorize work into themes. The skill provides a framework for:
- Categorizing issues into themes (Feature Work, Bug Fixes, etc.)
- Counting issues per theme
- Breaking down by team/project
- Generating summary reports

### Step 3: Run Analysis

```bash
python3 analyze_themes.py
```

## Common Theme Categories

1. **Feature Work** - New functionality and enhancements
2. **Bug Fixes** - Defect resolution
3. **Test Fixes & Quarantine** - Flaky test resolution
4. **Oncall Support** - Incident response
5. **CX Escalations** - Customer-facing issues
6. **Documentation & Spikes** - Research and documentation
7. **Onboarding & Training** - Team development
8. **Technical Debt** - Refactoring and cleanup
9. **Sprites & Reviews** - Code reviews
10. **Infrastructure** - DevOps and tooling

## Example Usage

When the user asks to:
- "What did we accomplish this quarter?" - Query and analyze last 90 days
- "Show me the breakdown of work types" - Run theme analysis
- "Are we spending too much time on maintenance?" - Compare theme percentages
- "What work is invisible in roadmaps?" - Query for parent is EMPTY

## Use Cases

1. **Sprint/Quarter Retrospectives** - What did we accomplish?
2. **Team Balance Analysis** - Too much maintenance vs features?
3. **Work Visibility** - Show non-Epic work that's "invisible"
4. **Capacity Planning** - How much capacity goes to unplanned work?

For full documentation, see the detailed Team Group Analysis skill documentation in this folder.
