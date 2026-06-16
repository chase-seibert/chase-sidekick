# Engineer 2026 YTD PR/Jira Report Notes

CSV: `tmp/engineer_2026_ytd_pr_jira_report.csv`

Rows: 310 Core Engineering rows from `memory/tmp_activity_jira_completion/source_master.csv`.
Window used for YTD rate columns: 2026-01-01 through 2026-06-16 inclusive (23.86 weeks).

Populated columns:
- `median_pr_size_lines`: copied from cached `median_pr_size_lines`; the prior activity analysis identifies this source as `DXLast12Months`.
- `github_pr_review_comment_count`: copied from cached `review_comment_count`; this is a review comment count, not a distinct PR-commented-on count.
- `merged_pr_count`, `jira_issues_completed`, `issue_predictability_pct`: copied from the same cached activity export.
- `jira_completed_issues_per_week`: derived as `jira_issues_completed / 23.86` for a directional rate fallback.

Blocked columns:
- `jira_completed_hours_per_week`: the local shell has no Atlassian/Jira API config, and the available Rovo connector can query Jira but does not provide a scriptable aggregate export path for all 310 rows in this unattended run.
- `github_prs_approved`: local `gh auth status` reports an invalid token. The GitHub connector can search PRs and fetch individual PRs, but its PR search response does not return aggregate counts, so producing approval counts for all engineers would require broad paginated per-user/per-PR fetching that is not reliable through the connector alone.
