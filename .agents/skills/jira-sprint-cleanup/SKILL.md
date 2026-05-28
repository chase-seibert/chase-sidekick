---
name: jira-sprint-cleanup
description: Analyze and optionally clean up Jira sprint hierarchy for current and previous sprints. Use when Codex needs to find sprint issues without Epic parents, including cross-project issues in team sprints, Epics without roadmap parents, recommend Epic or parent assignments, produce sprint cleanup reports, or apply confirmed Jira parent/comment updates across one or more teams/projects.
---

# Jira Sprint Cleanup

## Purpose

Use this skill to analyze current and previous sprint issues for missing parent relationships, including issues from other Jira projects that were placed in a team's sprint, recommend Epic or roadmap parent assignments, and optionally update Jira after confirmation.

Keep this skill generic. Derive teams, project keys, EMs, roadmap roots, and sprint quirks from the user request and local context files.

## Context Discovery

1. Read the current task, project instructions, and user-level instructions first.
2. If the user names teams or Jira projects, use those as the target set. Otherwise derive teams from local context.
3. For each team, identify the team display name, Jira project key or exact project name, EM name/email when comments or visibility notes are requested, and likely KTLO or operational Epics for the relevant period when cross-project sprint issues need parents.
4. If present, read `local/jira-sprint-cleanup.md` first, then `local/jira.md` and relevant project or roadmap context docs. Treat these files as project-specific inputs, not skill defaults.
5. Resolve EM names/emails only for reporting and plain-text notes. Do not hard-code team, manager, or roadmap data in this skill.
6. Quote project keys and project names in JQL, for example `project = "KEY"`.
7. If local context names KTLO, on-call, SEV, unplanned, support, or operational Epics, treat them as parent candidates. Otherwise search Jira for active Epics in the team project using those terms plus the current quarter or sprint period.

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

3. Deduplicate sprint IDs across issues before running cleanup queries, and keep a map of sprint ID to owning team/project. This sprint-owner map is required for issues from other Jira projects that appear in the team's sprint.
4. If no active sprint exists, inspect `futureSprints()` and report the analysis as "current/next" explicitly.
5. Do not trust a Rovo `totalCount` as a complete count when `hasNextPage` is true. Paginate, or report the count as `100+`.

## Efficient Analysis

Do not pull complete sprint issue lists unless the user asks for every issue key. For broad sprint membership, prefer JQL links/counts. For cleanup work, use targeted gap queries.

For each selected sprint ID, run sprint-scoped gap queries without a project filter. Sprint IDs are the source of truth for cleanup membership because issues from shared projects such as SEV, support, or intake queues can be assigned into a team's sprint even when their project key is different.

- Missing Epic issues:

  ```jql
  Sprint = ID AND parent is EMPTY AND issuetype != Epic ORDER BY project ASC, key ASC
  ```

- Parentless Epics:

  ```jql
  Sprint = ID AND issuetype = Epic AND parent is EMPTY ORDER BY project ASC, key ASC
  ```

You may run additional `project = "KEY" AND Sprint = ID ...` queries for project-specific counts or comparison, but do not treat the sprint as clean until the sprint-scoped queries above have also returned zero.

Fetch only the details needed to make recommendations: summary, description when useful, labels, components, issue type, sprint, existing parent fields, and nearby related issues.

For each issue returned by a sprint-scoped query, classify whether it is:

- `team-project`: the issue project matches the sprint owner's Jira project.
- `foreign-project`: the issue project differs from the sprint owner's Jira project but the issue is in the sprint owner's sprint.

Report and process both classes. Do not discard `foreign-project` issues just because their project key is outside the team's usual Jira project set.

## Recommendation Rules

- For non-Epic issues, recommend an existing Epic when possible.
- Prefer Epics in the same Jira project and the same or nearby sprint, then use summary, description, labels, components, linked issues, and local roadmap/project context to choose the best fit.
- For `foreign-project` non-Epic issues, prefer the sprint owner's team Epic when the issue is clearly team-owned operational work. KTLO, on-call, SEV action, support, false-positive, duplicate, alerting, escalation, intake, and similar maintenance work should usually map to the sprint owner's KTLO/on-call/operational Epic for the relevant quarter or sprint period.
- If several sprint-owner operational Epics could fit, prefer the most specific active Epic, such as On-Call or SEV follow-up before broader KTLO. If no specific operational Epic fits, use the broader KTLO Epic. If no suitable team Epic can be found, mark the item for manual review or recommend creating the missing team Epic.
- Foreign-project issues can still be assigned to an Epic in the sprint owner's project when Jira permits the parent relationship. Verify the parent field is editable before treating the update as ready to apply.
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
2. Include both `team-project` and `foreign-project` issues in the update set when their recommended parent is high confidence and the user has confirmed the exact updates, or when the user explicitly asks to apply the listed updates.
3. Add audit notes with `_addcommenttojiraissue` only as plain text.
4. If EM visibility is included, say "noted EM in plain text" rather than "tagged EM."
5. Continue through the update set even if one issue fails, and collect failures with issue key, attempted parent, and error.
6. Verify updates with grouped JQL by expected parent, for example:

   ```jql
   issuekey in (KEY-1, KEY-2) AND parent = EPIC-123
   ```

7. For cross-project updates, explicitly state that the issue remains in its original Jira project and only its parent was set to the sprint owner's team Epic.
8. Summarize what changed, what was verified, and any failures or manual-review items.
