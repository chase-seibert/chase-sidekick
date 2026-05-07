---
name: mmr-exec-summary
description: Generate a Quarto executive summary report from one or more MMR (Monthly Metric Review) Confluence pages in the Teams & Sharing Core Eng Ops Review format.
argument-hint: <confluence-page-url> [more urls...] [additional context or questions]
auto-approve: true
---

# MMR Executive Summary

Generate an executive Quarto report from one or more Monthly Metric Review (MMR) Confluence pages. The default output format is the Teams & Sharing Core Eng Ops Review style: yearly SEV framing, MMR action-item throughput, time investment, top themes, the five most interesting recent MMR AIs, next steps, kudos, and a feedback table.

Use this skill for leadership-ready summaries of MMR pages, especially when the user wants themes, risks, incidents, action-item progress, or a cross-team/monthly rollup.

## Inputs

Accept:
- One or more Confluence page URLs.
- Optional user-provided context, emphasis, or questions to answer in the report.
- Optional output preference. Default to an embedded HTML report if the user does not specify a format.
- Also query JIRA for any related SEVs, SEV AIs, and MMR Action Items 

If no URL is provided, ask for the MMR Confluence URL or URLs. If the prompt includes non-URL context, preserve it as report guidance and use it to shape the narrative.

## Required Outputs

Create a Quarto source report in the root memory directory using a name like memory/mmr-exec-summary-page-or-month-slug.qmd.

Render the report with Quarto, defaulting to HTML. If the user asks for another format, render that target too when available.

When reporting completion, show relative paths only, for example:

- memory/mmr-exec-summary-example.qmd
- memory/mmr-exec-summary-example.html

All reports written under memory must end with the exact footer:

This report generated using [chase-sidekick](https://github.com/chase-seibert/chase-sidekick) and the [mmr-exec-summary skill](https://github.com/chase-seibert/chase-sidekick/tree/main/.agents/skills/mmr-exec-summary).

## Workflow

1. Load the quarto-report skill before writing the final report.
2. Fetch each Confluence page as Markdown. Prefer the Confluence client or Confluence skill for Confluence links.
3. Keep a temporary working directory under the system temp directory for fetched Markdown, extracted sections, and issue metadata.
4. Parse each MMR for title, covered month, Summary, Key Improvements, Key Concerns, SEVs, MMR AIs, SEV AIs, and any detailed metric sections referenced by Summary.
5. Query JIRA for MMR AIs, SEVs, SEV AIs, issue status, issue estimates, assignees/reporters, linked issues, labels, resolution dates, and comments when needed to explain investigation outcomes.
6. Determine the reporting year and the most recent full calendar month relative to the current date. For example, if the current date is in May, the most recent full month is April 1 through May 1 exclusive.
7. Generate a Quarto report in the required Core Eng Ops Review structure below. Preserve the user's additional context or questions in the narrative, next steps, or feedback response.
8. Render the report and verify the output file exists.

Use python3 for any local scripting. Prefer structured parsing through Python or service clients over brittle ad hoc text manipulation when the Markdown structure is irregular.

## Analysis Requirements

The report must synthesize across all supplied MMR URLs. De-duplicate repeated issues and call out when pages disagree or when a source section is missing.

Answer any user-provided context or questions directly in the report, preferably in the TL;DR, Top Themes, Next Steps, or Feedback sections depending on fit.

Avoid copying large tables from the MMR. Summarize the signal executives need: what changed, why it matters, where risk remains, and what should happen next.

Do not include private project names, real employee names, real email addresses, internal document IDs, or raw issue IDs in examples inside this skill. In generated reports, include only the details needed for the user's work and avoid unnecessary personal data.

## Required Report Structure

Use this structure by default. Keep headings close to these names so the report is easy to scan and compare month over month.

1. **TL;DR**: One bold/italic opening paragraph that says this is an executive summary of the relevant group/team MMR reviews for the year through the latest available month. Link to the source MMR pages when useful.
2. **Table of Contents**: Keep this section, even if the rendered format already has a TOC. Use `none` if no manual TOC is needed.
3. **SEVs in YYYY**: Summarize real, non-false-positive SEVs for the reporting year. Include the count, a link to the JIRA query or source, and one subsection per notable real SEV with plain-English cause, impact, remediation, and continuing process change. Include a **Discussion** subsection with:
   - how many false-positive SEVs are being seen
   - whether threshold work is reducing false positives
   Add a **False-Positive SEV Graph** after Discussion. Insert a pie chart of false-positive SEVs vs non false positives. 
4. **MMR Deep Dive**: Link the latest team MMR reports and summarize whether the local MMR process is reliably producing and burning down MMR AIs.
5. **MMR Action Items**: Include a month-by-month table for the reporting year with columns `Month`, `Resolved`, `Unresolved`, and `Total`. Use full months plus the current partial month when available, labeling partial months clearly. Add a short interpretation of average monthly added/resolved throughput. Immediately after the table, include the stacked resolved/unresolved chart described in **MMR Action-Item Movement**.
6. **Time Investment**: Include a team table with `Team`, `Avg MMR AIs / sprint`, and `Avg original estimate / sprint` when estimates are available. If estimates are missing, infer from original estimate fields only when present and state the caveat. Put this table immediately under the Time Investment heading before any explanatory prose.
7. **Top Themes**: Categorize MMR AIs into executive themes. Include a table with `Theme`, `Issue Count`, and `Status Mix`. Add observations about what the distribution means, especially whether performance/reliability work is staying open longer than instrumentation or threshold work. Put the table first, followed by a concise paragraph and optional per-theme issue/action detail.
8. **Top Issues from Most Recent MMR**: Pick the five most interesting MMR AIs from the most recent full month or latest MMR cycle. For each issue, link the JIRA issue and provide an executive summary of:
   - the metric movement that triggered the flag,
   - what the team observed during investigation,
   - what the team is doing next or why no more work is needed.
9. **Next Steps**: Write crisp action items with enough specificity to become owner-trackable work. Prefer allocation, review-process, training, roadmap, or escalation actions over generic "monitor" actions.
10. **Kudos**: Recognize engineering ICs who led meaningful MMR investigations, SLO cleanup, reliability fixes, or process improvements. Prefer named engineers from JIRA assignees/reporters and MMR callouts; avoid inventing names.
11. **Feedback**: End with an empty or partially-filled feedback table with columns `From`, `Feedback Or Question`, and `Response`. Include blocking/non-blocking language when the source report or user asks for review feedback.
12. **Source Notes**: Include source page titles/links, query caveats, and data limitations.

## Required Analyses

### MMR Action-Item Movement

Compute monthly MMR AI throughput for the reporting year:

- MMR AIs are JIRA issues listed in the MMR AIs section or clearly labeled as MMR follow-up action items.
- Also compute monthly created and monthly resolved counts separately for the prose throughput sentence. The default sentence should be like: "For any given full month in YYYY so far, the teams are resolving about X action items and adding about Y action items." Use full months only for this average unless the user explicitly asks for MTD.

#### MMR Action-Item Chart

Generate a stacked resolved/unresolved chart from the same monthly snapshot table and place it immediately after the MMR Action Items table. The chart should make the inventory shape obvious, not introduce a second data definition.

- Use the same issue set, month rows, and counts as the `Month`, `Resolved`, `Unresolved`, `Total` table.
- Use a stacked area or stacked line chart. Label the key exactly as `Unresolved` and `Resolved`. 
- If generating the chart manually as SVG, write it under `memory/` next to the report and reference it from the Quarto file. Also write the chart data CSV under `memory/` when useful for auditability.
- If using Quarto-native charting, prepare data before writing the report rather than using executable chunks unless the user asks for live code chunks.
- Title the chart plainly, for example `MMR AIs: Unresolved and Resolved by Month`.
- Add one caveat sentence below the chart when the current month is partial or when Jira `resolutiondate` is missing for otherwise terminal statuses.

### Time Investment by Team

Generate the Time Investment table from Jira sprint membership and original estimates:

- Use the same Teams & Sharing MMR AI JQL scope as the MMR Action Items section.
- Fetch fields: `key`, `summary`, `created`, `resolutiondate`, `project`,`timeoriginalestimate`, `timeestimate`, and Sprint (may be a custom field).
- Map teams by JIRA Project 
- Assign each MMR AI to its latest started sprint on its own team's board. This avoids double-counting carryover issues that appear in multiple sprints.
- The default table columns are `Team`, `Avg MMR AIs / sprint`, and `Avg original estimate / sprint`. Add `Sprints included`, `Sprints with MMR AIs`, or `Not in started sprint` only when they help explain the numbers.
- Place this table in **Time Investment**, immediately under the heading. Follow it with a caveat if Jira logged time is missing or if many issues are unsprinted/backlog.

### SEV and SEV AI Analysis

Query SEVs for the reporting year using the relevant group/team labels, service/team fields embedded in the MMR pages, or explicit JQL links in the source. Separate:

- real SEVs,
- false positives,
- duplicates/cancelled issues,
- downgraded alerts,
- open SEV AIs.

Only present the detailed SEV subsections for the real/non-false-positive incidents that matter for executive review. Keep false positives in aggregate discussion unless one explains an important alert-quality theme.

#### False-Positive SEV Graph

Generate a false-positive versus non-false-positive SEV pie chart and place it in **SEVs in YYYY**, immediately after the **Discussion** subsection.

- Use the same SEV issue set discussed in the section.
- Classify each SEV as `False positive / cancelled / duplicate / downgraded` or `Real SEV` based on issue status, resolution, labels, MMR notes, and Jira comments.
- If the MMR narrative says the ticket stream contains false positives or AutoSEV noise, preserve that distinction in the chart caption so executives do not confuse alert volume with incident volume.
- Write the chart asset under `memory/` next to the report, preferably as SVG or PNG, and reference it from the Quarto report. If using a CSV for the chart, write it under `memory/` and reference it in Source Notes.
- Include the source JQL or source page links under the chart or in Source Notes.

### Top Themes

Classify MMR AIs into five to seven themes. Good default buckets are:

- MMR instrumentation, thresholds, and reporting quality.
- Performance latency, TTVC, and LCP.
- Reliability, availability, and error rates.
- Ownership, component, and backlog hygiene.
- Code coverage and test quality.
- SEV/incident prevention and operational process.

Use JIRA summaries, labels, MMR sections, and issue comments to classify. Include status mix counts such as `Done: 24, Open: 2`. The observations below the table should explain the management implication.

Theme counts should be multi-label: one MMR AI can count in more than one theme when it spans both a metric symptom and a measurement/process fix. Do not count generic mentions of "MMR report" or dashboard links as instrumentation unless the issue is actually about thresholds, rollups, queries, service flags, or metric correctness.

For each theme, use Jira comments to summarize what action was taken. Good action-summary patterns include:

- root cause documented,
- follow-up remediation ticket created,
- metric recovered and issue closed with monitoring,
- low-traffic/not-yet-live route triaged as low impact,
- route/component deprecated or migrated,
- SLA/SLO/threshold/reporting config updated,
- coverage improved or coverage-tooling issue identified,
- deferred pending broader Core or platform alignment.

In the final report, place the top-level theme table in **Top Themes** with columns `Theme`, `Issue Count`, and `Status Mix`. If space allows, add a compact detail table under the observations with `Theme`, `Representative Issues`, and `Executive Summary Of Actions`; otherwise link to a separate `memory/mmr-ai-top-themes-YYYY.csv` audit file in Source Notes.

### Top Issues From Most Recent MMR

Select the five most interesting MMR AIs, not necessarily the newest five. Prefer issues with:

- a large red/yellow metric movement,
- a surprising investigation result,
- cross-team dependency,
- clear executive risk,
- meaningful process learning,
- completed work that changed future MMR interpretation.

Each issue summary must link the JIRA issue and include three pieces in prose: metric trigger, investigation observation, and current action/disposition.

### Kudos

Generate a short kudos list for engineering ICs leading the work. Use JIRA assignee/reporter data, source MMR callouts, and investigation comments. Tie each kudos item to a concrete operational outcome.

## Quarto Guidance

The Quarto source should be readable as Markdown before rendering. Use YAML frontmatter with an informative title and HTML embedding enabled by default.

Use tables for MMR action-item throughput, time investment, top themes, and feedback. Use charts only when the user asks for them or when they materially improve the Core Eng Ops Review narrative; the reference format is primarily prose and tables.

Do not add Python, R, Julia, Observable, or other executable report chunks unless the user explicitly asks for computed charts or runtime analysis inside the report. Do data preparation before writing the Quarto source.

## Data Extraction Notes

MMR pages commonly contain:

- Summary.
- Key Improvements.
- Key Concerns.
- SEVs.
- MMR AIs.
- SEV AIs.
- Detailed metric sections such as bugs, availability, latency, tests, escalations, and page performance.

Use the Summary section as the primary executive source, then verify details against specific sections when a concern or action item needs context.

For issue keys, use a generic JIRA key pattern and then validate each candidate through JIRA before treating it as real. Some Confluence exports may glue issue keys to HTML or UUID-like text, so validation matters.

For terminal status, treat Done, Resolved, Closed, Canceled, and equivalent workflow statuses as terminal. If a status is unfamiliar, infer conservatively and mention the ambiguity if it affects counts.

## Error Handling

If a Confluence page cannot be read, continue with other supplied pages and report the failed URL in Source Notes.

If JIRA enrichment fails for some issues, still produce the report from MMR evidence and mark those issues as unenriched in caveats.

If a required section is absent, do not invent data. Write a short caveat and continue with the sections that exist.

If the Quarto render fails, leave the .qmd report in memory, explain the render failure briefly, and report the relative .qmd path.
