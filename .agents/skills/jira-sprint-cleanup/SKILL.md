---
name: jira-sprint-cleanup
description: Analyze and optionally clean up Jira sprint hierarchy for current and previous sprints. Use when Codex needs to find sprint issues without Epic parents, Epics without roadmap parents, recommend Epic or parent assignments, produce sprint cleanup reports, or apply confirmed Jira parent/comment updates across one or more teams/projects.
---

# Jira Sprint Cleanup

## Purpose

Use this skill to analyze current and previous sprint issues for missing parent relationships, recommend Epic or roadmap parent assignments, and optionally update Jira after confirmation.

Keep this skill generic. Derive teams, project keys, EMs, roadmap roots, and sprint quirks from the user request and local context files.

## Context Discovery

1. Read the current task, project instructions, and user-level instructions first.
2. If the user names teams or Jira projects, use those as the target set. Otherwise derive teams from local context.
3. For each team, identify the team display name, Jira project key or exact project name, and EM name/email when comments or visibility notes are requested.
4. If present, read `local/jira-sprint-cleanup.md` first, then `local/jira.md` and relevant project or roadmap context docs. Treat these files as project-specific inputs, not skill defaults.
5. Resolve EM names/emails only for reporting and plain-text notes. Do not hard-code team, manager, or roadmap data in this skill.
6. Quote project keys and project names in JQL, for example `project = "KEY"`.

## Jira Tools

Use Atlassian Rovo first.

- Use `tool_search` to load Atlassian Rovo Jira tools when they are not already callable.
- Use `_searchjiraissuesusingjql` for explicit JQL reads.
- Use `_getjiraissue` for issue details, field inspection, comments, and update verification.
- Use `_editjiraissue` for parent updates, using payloads like `{"parent": {"key": "EPIC-123"}}`.
- Use `_lookupjiraaccountid` only when useful for identity disambiguation in reports or plain-text notes. Do not use it to simulate mentions.
- Use `_addcommenttojiraissue` only for plain-text comments.
- Use local Jira clients only as fallbacks if Rovo is unavailable or lacks a needed read/update capability. Verify authentication first and use `python3`.

## Rovo Comment Limitation

Rovo `_addcommenttojiraissue` cannot currently create real Jira mention nodes. Text such as `@Name` or `[~accountid:...]` is stored as plain text, not as an actual Jira mention.

Do not claim that an EM was tagged, mentioned, or notified when adding comments through Rovo.

If the user asks to tag or notify EMs, state this limitation before adding comments. Add plain-text EM visibility notes only if the user accepts that limitation, and describe the result as "noted EM in plain text."

## Sprint Discovery

For each Jira project:

1. Find the active sprint with:

   ```jql
   project = "KEY" AND Sprint in openSprints() ORDER BY key ASC
   ```

2. Discover the previous sprint from closed sprint metadata. Query recent closed-sprint issues, inspect Sprint field metadata, and choose the most recently closed sprint before the active sprint:

   ```jql
   project = "KEY" AND Sprint in closedSprints() ORDER BY updated DESC
   ```

3. Deduplicate sprint IDs across issues before running cleanup queries.
4. If no active sprint exists, inspect `futureSprints()` and report the analysis as "current/next" explicitly.
5. Do not trust a Rovo `totalCount` as a complete count when `hasNextPage` is true. Paginate, or report the count as `100+`.

## Efficient Analysis

Do not pull complete sprint issue lists unless the user asks for every issue key. For broad sprint membership, prefer JQL links/counts. For cleanup work, use targeted gap queries.

For each selected sprint ID:

- Missing Epic issues:

  ```jql
  project = "KEY" AND Sprint = ID AND parent is EMPTY AND issuetype != Epic ORDER BY key ASC
  ```

- Parentless Epics:

  ```jql
  project = "KEY" AND Sprint = ID AND issuetype = Epic AND parent is EMPTY ORDER BY key ASC
  ```

Fetch only the details needed to make recommendations: summary, description when useful, labels, components, issue type, sprint, existing parent fields, and nearby related issues.

## Recommendation Rules

- For non-Epic issues, recommend an existing Epic when possible.
- Prefer Epics in the same Jira project and the same or nearby sprint, then use summary, description, labels, components, linked issues, and local roadmap/project context to choose the best fit.
- Do not recommend assigning a Story, Task, or Bug directly to a Roadmap Initiative. If no existing Epic fits, recommend creating a new Epic and identify the likely roadmap parent for that new Epic.
- For parentless Epics, recommend Roadmap Initiative or parent candidates using local roadmap JQL, project context, existing sibling Epics, and naming conventions.
- Include a short rationale and confidence signal. If confidence is low, mark the item for manual review instead of treating it as ready to update.

## Reporting

Default to an inline chat report unless the user explicitly asks for a file.

For "Issues Not Tied To An Epic", use a table with these columns:

```markdown
| Issue | Issue Summary | Suggested Epic | Suggested Epic Summary | Rationale |
```

Link Jira issue keys to their issue URLs when the site base URL is known.

For "Epics Without Parents", use a compact list or table with these fields:

```markdown
Epic | Summary | Suggested Parent | Parent Summary | Rationale
```

Mention sprint caveats, such as no active sprint or use of current/next sprint, in prose. Do not include a separate sprint discovery table unless the user asks for it.

## Updates And Verification

Before mutating Jira, require confirmation unless the user already requested the exact updates to apply.

When applying updates:

1. Use `_editjiraissue` to set the parent.
2. Add audit notes with `_addcommenttojiraissue` only as plain text.
3. If EM visibility is included, say "noted EM in plain text" rather than "tagged EM."
4. Continue through the update set even if one issue fails, and collect failures with issue key, attempted parent, and error.
5. Verify updates with grouped JQL by expected parent, for example:

   ```jql
   issuekey in (KEY-1, KEY-2) AND parent = EPIC-123
   ```

6. Summarize what changed, what was verified, and any failures or manual-review items.
