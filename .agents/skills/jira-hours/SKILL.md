---
name: jira-hours
description: Calculate a team's average Jira hours from Rovo Jira completed work, with optional Workday Approved Time Off absence adjustments for a date window and team roster.
argument-hint: <date-window> <reports> <approved-time-off.xlsx>
---

# jira-hours

Use this skill when asked to calculate a team's average completed Jira original-estimate hours, especially when comparing against weekly assignment capacity or adjusting for PTO and other approved absences.

## Required Inputs

Ask for any missing input before running the report:

| Input | Meaning |
| --- | --- |
| `START_DATE` | Inclusive start date, `YYYY-MM-DD`. |
| `END_DATE` | Inclusive end date, `YYYY-MM-DD`. |
| `REPORTS` | Exact display names for the people to include. |
| `ABSENCE_SHEET` | Workday Approved Time Off `.xlsx` export. |

The absence sheet can be fetched from Workday's **Approved Time Off** report. It should include columns like `Worker`, `Request Type`, `Time Off Date`, `Approved`, and `Unit of Time`.

Optional input:

| Input | Meaning |
| --- | --- |
| `TARGET_HOURS_PER_WEEK` | Weekly assignment target. Default to `30` if the user does not specify one. |

## Jira Query

Use Atlassian Rovo MCP first for Jira reads. Query all pages; do not calculate from truncated chat output.

Use this JQL shape:

```jql
assignee in ("REPORT 1", "REPORT 2")
AND status = Done
AND resolutiondate >= "START_DATE"
AND resolutiondate <= "END_DATE"
AND originalEstimate > 0
AND issuetype != Epic
ORDER BY assignee ASC, resolutiondate ASC
```

Fields to request:

```text
assignee,timeoriginalestimate,issuetype
```

Notes:

- Use `status = Done`, not `statusCategory = Done`, so Cancelled work is not counted as completed.
- Exclude Epics because this report is intended to measure assignable completed work tickets.
- Jira `timeoriginalestimate` is seconds. Convert to hours by dividing by `3600`.
- If the user explicitly wants a project, status, issue-type filter, or completion date field, restate the changed assumption in the final output.

## Absence Adjustment

Read the Workday Approved Time Off sheet and filter rows:

- `Worker` is one of `REPORTS`.
- `Request Type` is exactly `Absence Request`.
- `Unit of Time` is `Hours`.
- `Time Off Date` is within `START_DATE` through `END_DATE`, inclusive.

Exclude `Absence Correction` rows unless the user explicitly asks to net corrections into the absence calculation.

For each person:

```text
absence_adjustment_hours = approved_absence_hours * 6 / 8
adjusted_original_estimate_hours = non_epic_original_estimate_hours + absence_adjustment_hours
```

## Weekly Average

Use elapsed weeks in the inclusive date window:

```text
inclusive_days = (END_DATE - START_DATE).days + 1
weeks = inclusive_days / 7
adjusted_hours_per_week = adjusted_original_estimate_hours / weeks
```

Do not bucket by calendar weeks unless the user asks for week-by-week output.

## Output

Return a compact Markdown table:

| Person | Done non-Epic issues | Non-Epic original estimate hours | Absence adjustment | Adjusted avg hrs/week | Vs target |
| --- | ---: | ---: | ---: | ---: | ---: |

Round hours and averages to one decimal, except keep fractional absence adjustments if needed for auditability.

After the table, include the assumptions:

- Jira scope, including any project filter if the user requested one.
- Inclusive date range and week denominator.
- `status = Done`, `originalEstimate > 0`, and `issuetype != Epic`.
- Absence source was Workday Approved Time Off, using only `Absence Request` rows.
- Target hours/week used.

If any report has no matching Jira work or no matching absence rows, include them with `0.0` values rather than dropping them.
