---
name: jira-ga-date-report
description: Generate evidence-backed Markdown reports that identify GA/general availability dates for one or more user-supplied Jira Epics or Roadmap Initiatives. Use when Codex is asked when Jira work GAs, launches, reaches general availability, ships broadly, or needs GA-date analysis across Epics, Roadmap Initiatives, parent/child roadmap hierarchies, related GA trackers, linked Confluence PRDs, tech specs, Jira comments, or launch plans.
---

# Jira GA Date Report

Find GA dates for Jira Epics or Roadmap Initiatives and write a concise Markdown report with the evidence trail behind each selected date.

## Defaults

- Inputs: one or more user-supplied Jira issue keys or Jira URLs. Do not use baked-in issue keys or examples as test fixtures.
- Output: `memory/jira-ga-date-report-YYYY-MM-DD-HHMM.md`.
- Final chat output: print a short summary and the relative report path only.
- Sources: Atlassian Rovo MCP first for Jira and Confluence. Use local Sidekick Jira clients only when Rovo is unavailable, lacks a needed field, local output is specifically useful, or the user explicitly asks for them.
- Writes: do not perform Jira, Confluence, Slack, Dropbox, or other external writes.
- Evidence dates: use concrete absolute dates. Avoid relative dates like `next week`.

## Source Gathering

Normalize each input into an issue key. For URLs, extract the key from `/browse/<ISSUE-KEY>` or equivalent Jira URL forms.

When Rovo tools are not already available, search for the Atlassian Rovo Jira and Confluence tools before falling back to local commands.

For each starting issue, fetch details with field names expanded when possible. Prefer field names from the returned `names` map over hard-coded custom field IDs. Gather:

- Issue metadata: key, URL, summary, issue type, status, resolution, assignee, parent, labels, fix versions, affected versions, updated date.
- Date fields: `GA`, `End Date`, due date, start date, target release/date fields, sprint block, and any visible roadmap-quarter fields.
- Planning links: PRD link, tech spec link, design spec link, remote links, linked issues, and comments.
- Hierarchy context: parent Roadmap Initiative, direct children, siblings under the same parent, and any child or sibling issue whose title indicates GA/general availability.
- Document context: linked Confluence PRDs, tech specs, launch plans, and Rovo search results mentioning the input key, normalized summary terms, `GA`, `general availability`, `launch`, `rollout`, `release`, or milestone names.

Rovo-first examples to adapt with the user-supplied keys:

```text
Fetch issue: issueIdOrKey = <ISSUE-KEY>, expand = names,renderedFields,changelog
JQL children: parent = <ISSUE-KEY>
JQL siblings: parent = <PARENT-KEY>
Rovo search: "<ISSUE-KEY>" GA "general availability" launch
Rovo search: "<normalized summary terms>" GA launch roadmap
```

Fallback examples:

```bash
python3 -m sidekick.clients.jira get-issue <ISSUE-KEY>
python3 -m sidekick.clients.jira query "parent = <ISSUE-KEY>" 100
python3 -m sidekick.clients.jira query "parent = <PARENT-KEY>" 100
```

## GA Date Resolution

Choose one selected GA date per input using this precedence:

1. Populated `GA` field on the starting issue or on an explicit related GA tracker.
2. Closely related issue whose title contains `GA` or `General Availability`, preferring issues in the same parent/root roadmap family; if that issue is clearly the GA tracker, use its `GA` field, then `End Date`, then due date, then release/fix-version date.
3. If the starting issue title itself is explicitly a GA/general-availability tracker, use its `GA` field, then `End Date`, then due date, then release/fix-version date.
4. Linked PRD, tech spec, or launch plan timeline with an explicit GA or general-availability date.
5. Jira comments or linked docs with dated GA/launch statements, preferring newest concrete evidence.
6. `Unknown` when no concrete GA evidence exists.

Do not confuse milestone completion with GA. If the starting issue is a rollout, beta, soft intervention, silent scoring, launch phase, or sub-milestone, treat its `End Date` or due date as milestone evidence only unless the issue or linked evidence explicitly says it is GA.

When sources conflict, prefer the newest authoritative source in this order: Jira GA tracker fields, current Jira issue fields, current PRD/tech spec timeline, recent Jira comments, older docs/comments. Note the conflict in the report.

## Confidence

Assign exactly one confidence value:

- `High`: direct populated `GA` field, or an explicit related GA tracker with a concrete Jira date field.
- `Medium`: current PRD/tech-spec timeline, launch plan, or strong same-parent/same-roadmap inference.
- `Low`: comments-only, stale evidence, conflicting evidence without a clear winner, or weak relationship between the starting issue and the GA evidence.
- `Unknown`: no concrete GA date found.

## Report Format

Write this Markdown structure:

```markdown
# Jira GA Date Report

**Generated:** YYYY-MM-DD HH:MM TZ
**Inputs:** <comma-separated user-supplied inputs>

## Findings

| Input | Selected GA Date | Confidence | Source | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| [<ISSUE-KEY>](<url>) | YYYY-MM-DD or Unknown | High/Medium/Low/Unknown | Direct GA field / related GA tracker / PRD / comment / none | Jira status | One concise sentence explaining the choice. |

## Evidence by Item

### [<ISSUE-KEY>](<url>) - <summary>

- Selected GA date: YYYY-MM-DD or Unknown
- Confidence: High/Medium/Low/Unknown
- Evidence:
  - [Source title](<url>): concrete date and why it counts.
  - [Source title](<url>): milestone date, conflict, or corroborating detail.
- Interpretation: one short paragraph distinguishing GA from rollout or milestone dates.

## Data Gaps

- Missing or blank GA field: [<ISSUE-KEY>](<url>).
- Inaccessible linked doc, missing comments, conflicting dates, or inferred family relationship.
```

Keep the report concise. Include enough evidence for the user to audit the date, not a raw dump of every fetched field.

## Error Handling

- Continue when one issue, comment set, child query, or linked document cannot be fetched.
- Record inaccessible sources and missing fields under `Data Gaps`.
- If an input is not an Epic or Roadmap Initiative, still analyze it when useful, but note the issue type in `Data Gaps`.
- If no GA date can be selected, report `Unknown` with the best available milestone dates clearly labeled as non-GA evidence.

