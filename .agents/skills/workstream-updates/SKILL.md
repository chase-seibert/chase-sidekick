---
name: workstream-updates
description: Generate leadership-ready quarterly workstream update reports from high-priority Jira Roadmap Initiatives. Use when Codex needs to summarize current-quarter roadmap commitments by work stream and sub-work stream, identify shipped/green/yellow/red items, call out top shipped impact, and surface overall risks.
---

# Workstream Updates

Generate a concise Markdown report on high-priority Roadmap Initiatives due in a quarter. The report is for executive/leadership review: focus on shipped impact, current delivery health, and top risks rather than raw Jira dumps.

## Defaults

- Quarter: current calendar quarter unless the user supplies one, for example `Q3 2026`.
- Output: `memory/workstream-updates-YYYY-QN.md`.
- Sources: read `AGENTS.override.md`, `local/jira.md`, `local/projects.md`, and `local/strategy-docs.md` before remote fetches.
- Final chat output: print a short summary and relative report path only.
- Temporary files: use `mktemp -d "${TMPDIR:-/tmp}/workstream-updates.XXXXXX"` for intermediate notes and clean it up.

## Source Gathering

Use Atlassian Rovo MCP first for Jira searches, issue details, comments, and Confluence pages. Use local Sidekick clients only when Rovo is unavailable, lacks a needed field, local output is specifically useful, or the user explicitly asks for them.

Jira fallback examples:

```bash
python3 -m sidekick.clients.jira query "<JQL>" 100
python3 -m sidekick.clients.jira get-issue ISSUE-123
python3 -m sidekick.clients.jira get-issues-bulk ISSUE-1 ISSUE-2
python3 -m sidekick.clients.jira query-by-parent ISSUE-123 100
```

Build the Roadmap Initiative query from the local roadmap JQL when available, then add the quarter and priority filters. Use local files for source hints, work stream names, impact, and risk context; do not use `local/projects.md` as the authoritative row list.

When the Jira roadmap uses a `Quarter` field or a Jira Sheet/JXL view filtered by `Quarter`, treat `Quarter = "YYYY QN"` as the committed-quarter selector and use Jira `duedate` as delivery evidence. If the `Quarter` field and `duedate` disagree, keep the item in scope and treat the mismatch as slip risk.

For Teams & Sharing C1 reports, prefer the Sheet-equivalent shape the user expects:

```text
project = "DBX"
AND issuetype = "Roadmap Initiative"
AND priority = P0
AND Quarter = "YYYY QN"
```

Then include only rows whose returned `parent.fields.summary` starts with `C1`. If JQL cannot filter by parent summary directly, discover C1 parent keys first using Jira parent/summary searches, then query `parent in (...)`. Do not hard-code the discovered private keys into the skill.

If the user asks for P0 items, use Jira Priority `P0`. If the local project uses `High`/`Highest` instead, use `priority in (High, Highest)`. If a screenshot or Sheet appears to include visible `[P1]`/`[P2]` titles while the user says P0, honor the explicit written priority and note the mismatch under `Data Gaps`.

Default JQL shape:

```text
(<roadmap initiative JQL from local/jira.md>)
AND priority in (<high-priority values for this project, e.g. P0 or High/Highest>)
AND duedate >= "YYYY-MM-DD"
AND duedate <= "YYYY-MM-DD"
ORDER BY priority DESC, duedate ASC
```

Fetch each matching Roadmap Initiative with fields for key, summary, description, status, resolution, priority, due date, labels, parent, children, linked issues, assignee/owner fields when present, and recent comments. Fetch child Epics or direct children with `parent = ISSUE-123` to assess progress and shipped evidence. Use linked docs from local context only when they materially explain impact, work stream, or risk.

## Selection Rules

- Include only Roadmap Initiatives with the selected high-priority values, usually Jira Priority `P0` for DBX roadmap work or `High`/`Highest` when that is the local scheme.
- Include only items committed to the selected quarter. Prefer the Jira `Quarter` field when the roadmap view uses it; otherwise use due dates in the quarter. If a discovered high-priority item lacks the selected commitment field, exclude it from the main table and list it under `Data Gaps`.
- Treat `Quarter = "YYYY QN"` or, when no Quarter field is used, a due date in the selected quarter as the commitment to ship in that quarter.
- Exclude KTLO work streams. Prefer explicit work stream metadata first; otherwise exclude items whose labels, title, parent, description, or local metadata indicate `KTLO`, `Keep the Lights On`, `on-call`, `operational`, maintenance-only work, support queues, SEV follow-up, alerting cleanup, or similar non-roadmap operations.
- Group by work stream and sub-work stream. Prefer explicit Jira fields; then local project metadata and roadmap headings; then parent initiative names; then labels. Use `Unmapped` only when sources do not support a better grouping.
- Order work streams as `Product`, then `Foundation`, then remaining non-KTLO work streams alphabetically. Order sub-work streams alphabetically unless local roadmap order is clear.

## Status Classification

Assign exactly one status per initiative:

- `Shipped`: terminal Jira status/resolution, or explicit shipped/launched/GA/live evidence in comments, child issues, Slack/doc source, or release notes.
- `Green`: active progress, no blocker, no slip signal, and the due date still looks plausible.
- `Yellow`: risk, blocker, dependency, stale updates, slipped once, or close-to-due with weak ship evidence.
- `Red`: due date passed without ship, explicitly slipped out of quarter, blocked/off-track, deferred, or cancelled after being a quarterly commitment.

Prefer the newest dated evidence. When sources disagree, cite the disagreement in the risk/dependency note and use the more conservative status.

In report tables, display color statuses with emojis for scanning: `🟢 Green`, `🟡 Yellow`, and `🔴 Red`. Keep `Shipped` as plain text unless the user asks for a shipped emoji.

## Report Format

Write this Markdown structure:

```markdown
# Workstream Updates - YYYY QN

**Generated:** YYYY-MM-DD
**Quarter:** YYYY QN (YYYY-MM-DD to YYYY-MM-DD)
**Scope:** High/Highest priority Roadmap Initiatives due in quarter, excluding KTLO

## Top Shipped Items

| Item | Executive Summary | Ship Evidence | Expected Impact |
| --- | --- | --- | --- |
| [Title](url) | One sentence on what shipped. | Link/date/status. | One sentence on business, customer, product, or platform impact. |

## Top Overall Risks

| Severity | Risk | Affected Item(s) | Why It Matters | Next Action |
| --- | --- | --- | --- | --- |
| 🔴 Red / 🟡 Yellow | ... | ... | ... | ... |

## Roadmap Progress

### Product

#### Sub Work Stream

| Status | Item | Executive Summary | Due | Progress Evidence | Risk / Dependency |
| --- | --- | --- | --- | --- | --- |
| 🟢 Green | [Title](url) | One sentence on what it is. | YYYY-MM-DD | Recent evidence. | Current risk or `None known`. |

### Foundation

[Repeat grouped tables.]

## Data Gaps

- High-priority item excluded because it lacks a due date: [ISSUE-123](url).
- Inaccessible or stale source: ...

This report generated using [chase-sidekick](https://github.com/chase-seibert/chase-sidekick) and the [workstream-updates skill](https://github.com/chase-seibert/chase-sidekick/tree/main/.agents/skills/workstream-updates).
```

Keep executive summaries to one sentence. Keep tables limited to the high-priority items in scope; do not include every child Epic unless it is the best evidence for status or impact.

## Analysis Guidance

- Top Shipped Items should be denormalized across all work streams and include the most important already-shipped items, ranked by expected impact.
- Top Overall Risks should be denormalized across all work streams and include the highest-impact delivery, dependency, date, staffing, customer, or business risks.
- Expected impact should be supported by the initiative description, local roadmap docs, linked strategy docs, comments, or nearby project context. If impact is inferred, phrase it cautiously.
- Shipped evidence can come from Roadmap Initiative status, child Epic terminal status, comments saying shipped/launched/GA/live, or linked docs. Include a source link whenever possible.
- For stale initiatives, treat lack of recent evidence as a risk only when the due date is close, already passed, or the item otherwise appears active/committed.
- Use concrete dates, not relative terms like `next week`, in the final report.

## Error Handling

- Continue when individual Jira issues, comments, docs, or child queries fail.
- Record inaccessible sources, missing due dates, missing work stream mapping, and ambiguous shipped evidence under `Data Gaps`.
- If no matching high-priority initiatives are found, still write the report with empty tables and a `Data Gaps` explanation that includes the JQL/source used.
- Do not perform any Jira, Confluence, Slack, or Dropbox writes.
