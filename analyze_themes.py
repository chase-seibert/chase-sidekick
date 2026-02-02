#!/usr/bin/env python3
"""Analyze JIRA issues and categorize into themes."""
import re
from collections import defaultdict

def parse_issue_line(line):
    """Parse a JIRA issue line from the query output."""
    # Format: KEY: Summary [Status] (Assignee) [labels]
    match = re.match(r'^([A-Z]+-\d+):\s+(.+?)\s+\[([^\]]+)\]\s+\(([^)]+)\)(?:\s+\[([^\]]+)\])?', line.strip())
    if not match:
        return None

    key, summary, status, assignee, labels = match.groups()
    project = key.split('-')[0]
    labels_list = [l.strip() for l in labels.split(',')] if labels else []

    return {
        'key': key,
        'project': project,
        'summary': summary,
        'status': status,
        'assignee': assignee,
        'labels': labels_list
    }

def categorize_issue(issue):
    """Categorize an issue into a theme based on summary and labels."""
    summary_lower = issue['summary'].lower()
    labels = [l.lower() for l in issue['labels']]

    # Check labels first
    if 'quarantine' in labels or 'fix and re-enable' in summary_lower:
        return 'Test Fixes & Quarantine'
    if 'sprites' in labels or 'sprites' in summary_lower or 'sprite reviews' in summary_lower:
        return 'Sprites & Reviews'
    if 'cx-escalations' in labels or 'cx-' in '-'.join(labels):
        return 'CX Escalations'

    # Check summary patterns
    if 'oncall' in summary_lower:
        return 'Oncall Support'
    if 'onboarding' in summary_lower or 'training' in summary_lower:
        return 'Onboarding & Training'
    if 'placeholder' in summary_lower:
        return 'Placeholders'
    if any(word in summary_lower for word in ['spike', 'docs', 'documentation', 'knowledge sharing', 'brown bag']):
        return 'Documentation & Spikes'
    if any(word in summary_lower for word in ['bug', 'fix', 'error', 'troubleshoot']):
        return 'Bug Fixes'
    if 'sev' in summary_lower or 'sev-' in summary_lower:
        return 'Severity Issues'

    return 'Feature Work'

def main():
    with open('teams_completed_90days.txt', 'r') as f:
        lines = f.readlines()

    # Parse issues
    issues = []
    for line in lines:
        if line.strip() and not line.startswith('[Debug]') and not line.startswith('Found'):
            issue = parse_issue_line(line)
            if issue:
                issues.append(issue)

    # Categorize
    theme_counts = defaultdict(int)
    team_theme_counts = defaultdict(lambda: defaultdict(int))

    for issue in issues:
        theme = categorize_issue(issue)
        theme_counts[theme] += 1
        team_theme_counts[issue['project']][theme] += 1

    # Write analysis report
    with open('teams_analysis.txt', 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("TEAMS GROUP COMPLETED WORK ANALYSIS (Last 90 Days)\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Total Issues Analyzed: {len(issues)}\n\n")

        # Overall theme counts
        f.write("-" * 80 + "\n")
        f.write("THEME BREAKDOWN\n")
        f.write("-" * 80 + "\n")
        for theme, count in sorted(theme_counts.items(), key=lambda x: -x[1]):
            percentage = (count / len(issues)) * 100
            f.write(f"{theme:35} {count:3} ({percentage:5.1f}%)\n")

        f.write("\n")
        f.write("-" * 80 + "\n")
        f.write("THEME BREAKDOWN BY TEAM\n")
        f.write("-" * 80 + "\n\n")

        for project in sorted(team_theme_counts.keys()):
            project_total = sum(team_theme_counts[project].values())
            f.write(f"\n{project} ({project_total} issues):\n")
            for theme, count in sorted(team_theme_counts[project].items(), key=lambda x: -x[1]):
                percentage = (count / project_total) * 100
                f.write(f"  {theme:35} {count:3} ({percentage:5.1f}%)\n")

        # Detailed breakdown
        f.write("\n\n")
        f.write("=" * 80 + "\n")
        f.write("DETAILED BREAKDOWN BY THEME\n")
        f.write("=" * 80 + "\n")

        issues_by_theme = defaultdict(list)
        for issue in issues:
            theme = categorize_issue(issue)
            issues_by_theme[theme].append(issue)

        for theme in sorted(issues_by_theme.keys()):
            f.write(f"\n{theme} ({len(issues_by_theme[theme])} issues):\n")
            f.write("-" * 80 + "\n")
            for issue in issues_by_theme[theme]:
                f.write(f"  {issue['key']:12} [{issue['project']:5}] {issue['summary'][:60]}\n")

    print("Analysis complete! Results written to teams_analysis.txt")

    # Print summary to console
    print(f"\nTotal Issues: {len(issues)}")
    print("\nTheme Breakdown:")
    for theme, count in sorted(theme_counts.items(), key=lambda x: -x[1]):
        percentage = (count / len(issues)) * 100
        print(f"  {theme:35} {count:3} ({percentage:5.1f}%)")

if __name__ == '__main__':
    main()
