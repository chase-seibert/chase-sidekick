---
name: top-projects-exec-summary
description: Generate executive summaries for the user's top five projects using local project context, source docs, Slack, and JIRA; writes a Markdown report to memory.
argument-hint: [days]
auto-approve: true
---

# Top Projects Executive Summary

Generate an executive summary report for the user's top five projects. Use local context as the source of truth, gather context from docs, Slack, and JIRA, then write a Markdown report under `memory/`.

## Defaults

- Time window: last 14 days, unless the user passes a numeric day count.
- Output: `memory/top-projects-exec-summary-YYYY-MM-DD.md`.
- Temporary files: create a temp directory with `mktemp -d "${TMPDIR:-/tmp}/top-projects-exec-summary.XXXXXX"` and clean it up. Do not leave intermediate files in the repo.
- Final chat output: print a short processing summary and the relative report path.

## Project Selection

Select projects in this order:

1. **Explicit local labels**: read `local/projects.md` and any local context files referenced by `AGENTS.override.md`. Prefer sections clearly labeled with names like `Top Projects`, `Top Projects for Executive Summary`, `Executive Summary Projects`, `Active Priorities`, or `On My Plate`.
2. **Configured project metadata**: within each selected project entry, use local metadata for docs, Slack channels, JIRA initiatives, alternate names, teams, status meetings, roadmap docs, and tech specs. These specifics belong in `AGENTS.override.md`, `local/*.md`, or `memory/`, not in this skill. See the `README.md` section "Local Context Without Committing It" for the intended configuration pattern.
3. **Weekly-report inference**: if fewer than five projects are explicitly labeled, read the latest weekly report from `memory/weekly_report.md` or the newest relevant `memory/weekly_report*` file. Infer likely top projects from repeated themes, leadership-facing bullets, recent risks, major milestones, and roadmap/dependency mentions.

Stop when five projects or project areas are selected. If more than five are labeled, use the first five unless the user explicitly asks for a different ranking. If fewer than five can be found, include every discovered project and add the shortfall to `Data Gaps`.

Treat a "project area" as valid when local context groups several related initiatives under one executive-level priority. Keep the group name from local context; do not invent company- or org-specific names that are not supported by the sources.

## Source Gathering

Read likely local indices before fetching remote content. Common files include:

- `local/projects.md`
- `local/strategy-docs.md`
- `local/meetings.md`
- `local/slack-channels.md`
- `local/tech-specs.md`
- `AGENTS.override.md`
- `memory/weekly_report.md`

For each project area:

1. Collect links and source hints from the selected project entry, related local index entries, recent weekly-report references, and any local context files they point to.
2. Add shared strategic context only when local context links it to the selected project. Do not add hard-coded docs, channels, or roadmap items from the skill itself.
3. Fetch Confluence pages with Atlassian Rovo MCP when Markdown or ADF is sufficient. Fall back to the Confluence client or skill only when Rovo is unavailable or raw storage HTML is required.
4. For Dropbox Paper links, use Dropbox MCP (`dropbox-mcp`) `paper_read_document` first, following local connector preferences from `AGENTS.override.md` or repo guidance. If Dropbox MCP is unavailable, lacks the needed operation, debugging the local client, running standalone workflows, or the user explicitly asks for the local client, use the Dropbox skill/client as a fallback.
5. Use JIRA as a supporting source for milestones and status through Atlassian Rovo MCP. Fetch direct issues with Rovo search/fetch and child epics with Rovo JQL such as `parent = ISSUE-123`; fall back to `sidekick.clients.jira` only when Rovo is unavailable or lacks the needed field.
   Fetch linked roadmap initiatives first, then child epics. Use status fields, summaries, target dates, and recent comments where available.
6. Use the `/slack` skill pattern for Slack. For time-based reading, search with `after:YYYY-MM-DD`:
   ```json
   {
     "query": "after:YYYY-MM-DD in:#channel-name",
     "max_results": 20,
     "sort": "timestamp",
     "sort_direction": "desc"
   }
   ```
   Paginate when there are more results, but keep only extracted notes, representative links, dates, senders, and excerpts.

## Configuring Top Projects

Keep project-specific configuration in local/private context, following `README.md` guidance:

- Put short always-loaded personal context in `AGENTS.override.md`.
- Put longer private project, doc, Slack, and meeting indexes in `local/*.md`.
- Put generated reports and cached context in `memory/`.

Recommended local project entry shape:

```markdown
## Top Projects for Executive Summary

### Project or Priority Name
- **Why it matters:** Business, customer, product, or engineering impact.
- **JIRA Roadmap Initiative:** [ISSUE-123](https://...)
- **Docs:** [PRD](https://...), [Tech Spec](https://...), [Status Doc](https://...)
- **Slack Channels:** [#project-channel](https://...)
- **Status Meetings:** [Meeting Notes](https://...)
- **Keywords:** alternate names, product names, initiative names, acronyms
```

The exact headings and fields may vary. Preserve the user's local labels and use links, issue keys, channel names, and keywords from local context.

## Extraction Rules

For each project area, extract:

- What the project is: concise explanation of the goal and scope.
- Impact: business, product, customer, platform, or engineering productivity impact.
- Past milestones shipped: launched, GA, rollout, completed spike, completed tech review, shipped demo, or Done epics.
- Future milestones: upcoming rollout, GA, spike, review, design, implementation, target date, or deadline.
- Recent status updates: only from the selected time window unless older context is needed to explain the current state.
- Risks, blockers, and dependencies: cross-team dependencies, unclear decisions, rollout risk, staffing, technical risk, or missing docs.
- Sources: source links used for each project area.

When sources disagree, prefer the newest dated source. Prioritize sources in this order:

1. Recent docs or meeting notes with dates.
2. Recent Slack updates and threads.
3. JIRA comments and status fields.
4. Static roadmap/project metadata.

## Report Format

Write the final report as:

```markdown
# Top Projects Executive Summary - YYYY-MM-DD

**Generated:** YYYY-MM-DD
**Period:** YYYY-MM-DD to YYYY-MM-DD
**Projects:** 5

## Executive Themes
- [3-5 bullets synthesizing the biggest cross-project themes, risks, or decisions.]

## 1. Project Area Name

**High-Level Summary:** ...

**Impact:** ...

**Past Milestones Shipped:**
- ...

**Future Milestones:**
- ...

**Recent Status Updates:**
- ...

**Risks / Blockers / Dependencies:**
- ...

**Sources Used:**
- [Doc or channel](url)

[Repeat for projects 2-5]

## Data Gaps
- [Missing channels, inaccessible docs, ambiguous milestone dates, or stale source areas.]

This report generated using [chase-sidekick](https://github.com/chase-seibert/chase-sidekick) and the [top-projects-exec-summary skill](https://github.com/chase-seibert/chase-sidekick/tree/main/.agents/skills/top-projects-exec-summary).
```

Keep the report executive-readable: concise bullets, no raw dumps, and enough links to audit the summary. Prefer concrete dates over relative dates.

## Error Handling

- Continue on individual source failures.
- Record inaccessible docs, channels, or JIRA issues under `Data Gaps`.
- If a project has little or no recent activity, still include it with the best static context and say no recent status was found in the selected window.
- If Slack returns too much data, summarize by topic and keep 3-5 representative message links.
- If JIRA child epic counts are large, summarize aggregate status instead of listing every epic.

## Final Output

After writing the report, print:

```text
Top projects executive summary generated
Period: YYYY-MM-DD to YYYY-MM-DD
Projects summarized: 5
Report saved to: memory/top-projects-exec-summary-YYYY-MM-DD.md
```
