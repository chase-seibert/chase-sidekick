---
name: project_review
description: Generate comprehensive project review reports from PRD and tech spec documents
argument-hint: <document-urls>
allowed-tools: Bash, Read
---

# Project Review Agent

Generate comprehensive project review reports from product and technical specification documents.

## Overview

This agent helps you:
1. Identify and fetch PRD (product spec), Design, and Tech Spec documents from Confluence, Dropbox Paper, or Figma links
2. Extract key information about project scope, requirements, and technical decisions
3. Generate a structured markdown report with front matter
4. Refresh reports to incorporate document updates
5. Track changes via a changelog

## Prerequisites

- `CLAUDE.local.md` file with team and people context
- Configured Dropbox and Atlassian credentials in `.env`
- One or more links to project documents (Confluence, Paper, or Figma)

## Usage Pattern

### Step 1: Identify Document Links

The user provides one or more links to project documents. Your job is to:
1. Fetch each document
2. Identify which document is the PRD, Design Spec, and Tech Spec
3. If a document contains links to other documents, follow those links

### Step 2: Fetch Document Contents

Create temporary directory for intermediate artifacts:
```bash
mkdir -p /tmp/project_review_$$
```

**For Confluence pages:**
```bash
python -m sidekick.clients.confluence get-content-from-link "<CONFLUENCE_URL>" > /tmp/project_review_$$/doc_name.html
```

**For Dropbox Paper docs:**
```bash
python -m sidekick.clients.dropbox get-paper-contents-from-link "<PAPER_URL>" > /tmp/project_review_$$/doc_name.md
```

**For Figma files:**
Currently not supported - note this in the report as "Link provided but content not accessible"

**Important**: All intermediate artifacts (fetched documents, JIRA outputs) should be saved to `/tmp/project_review_$$/` and cleaned up after the report is generated. Only the final report should remain in `memory/project_review/`.

### Step 3: Fetch JIRA Issues

If JIRA issue IDs are found in the documents, fetch them to get additional context:

```bash
# For the Epic
python -m sidekick.clients.jira get-issue TFM-713 > /tmp/project_review_$$/jira-epic.txt

# For any related issues in the roadmap
python -m sidekick.clients.jira roadmap-hierarchy TFM-713 TFM > /tmp/project_review_$$/jira-hierarchy.txt
```

JIRA issues may contain:
- DRI names in assignee field or description
- Additional project context and requirements
- Related issues and dependencies

### Step 4: Analyze Document Content

Review each document to extract:
- Project name and goal
- JIRA Epic and/or Roadmap Initiative IDs (e.g., DBX-1234)
- Product requirements (standard and controversial/complex ones)
- Technical implementation details
- Technical decisions that could impact scope
- Estimates (prefer original units - hours, days, weeks, eng-weeks)
- DRIs (Product, Engineering Manager, Design, Engineering IC) - use names, not IDs
- Partner teams and dependencies

Look for:
- Headers like "Requirements", "Technical Approach", "Timeline", "Team", "Dependencies", "Partner Teams"
- JIRA issue links or IDs mentioned in the document
- Tables with estimates or milestones
- Names and roles of people involved (check JIRA issues if names not in docs)
- Sections highlighting risks, open questions, or dependencies
- User mention tags (may need to be resolved to names)

### Step 5: Generate Report

Create a markdown file with the following structure. Limit the length of the entire report to 1500 words. 

```markdown
---
project_name: "Project Name Here"
jira_epic: "DBX-1234"
jira_initiative: "DBX-5678"
prd_link: "https://..."
design_link: "https://..."
tech_spec_link: "https://..."
product_dri: "Name <email@company.com>"
eng_manager_dri: "Name <email@company.com>"
design_dri: "Name <email@company.com>"
eng_ic_dri: "Name <email@company.com>"
first_generated: "YYYY-MM-DD HH:MM:SS"
last_updated: "YYYY-MM-DD HH:MM:SS"
---

# [Project Name] - Project Review

## Artifacts
- **JIRA Epic**: [DBX-1234](https://company.atlassian.net/browse/DBX-1234)
- **JIRA Initiative**: [DBX-5678](https://company.atlassian.net/browse/DBX-5678) or N/A
- **Product Spec**: [Link](<prd_link>)
- **Design Spec**: [Link](<design_link>)
- **Tech Spec**: [Link](<tech_spec_link>)

## Team
- **Product DRI**: Name <email@company.com>
- **Engineering Manager DRI**: Name <email@company.com>
- **Design DRI**: Name <email@company.com>
- **Engineering IC DRI**: Name <email@company.com>

## Timestamps
- **Report Generated**: YYYY-MM-DD HH:MM:SS
- **Last Updated**: YYYY-MM-DD HH:MM:SS

---

## TL;DR

[One sentence describing the project goal]

## Product Requirements Summary

[2-3 paragraph summary of what the product aims to deliver and key user-facing features]

## Complex/Controversial Requirements

Requirements that may add complexity or could be debated:

- **[Requirement name]**: [Why this is complex or controversial, impact on scope]
- **[Requirement name]**: [Why this is complex or controversial, impact on scope]

## Technical Implementation Summary

[2-3 paragraph summary of the technical approach, architecture decisions, and key technical components]

## Scope-Impacting Technical Decisions

Technical decisions that could greatly affect project scope:

- **[Decision name]**: [What was decided, why it impacts scope, potential risks]
- **[Decision name]**: [What was decided, why it impacts scope, potential risks]

## Estimates

**Total Engineering Time**: [X weeks/hours] (use the unit from the source document)

### By Milestone

| Milestone | Estimate | Confidence | Notes |
|-----------|----------|------------|-------|
| [Name]    | [X hours/days/weeks] | High/Medium/Low | [Any relevant notes] |
| [Name]    | [X hours/days/weeks] | High/Medium/Low | [Any relevant notes] |

### High-Risk Estimates

Areas where estimates could be higher than anticipated:

1. **[Item name]**: [Why this might take longer, estimated range]
2. **[Item name]**: [Why this might take longer, estimated range]
3. **[Item name]**: [Why this might take longer, estimated range]

## Dependencies & Risks

### Partner Team Dependencies

| Partner Team | Dependency | Risk Level | Mitigation |
|--------------|------------|------------|------------|
| [Team name or Slack channel] | [What we need from them] | High/Medium/Low | [How to mitigate] |

### External Dependencies

- **[System/Service name]**: [Description of dependency and potential impact]
- **[Concurrent project/experiment]**: [How this affects or interacts with our project]

### Dependency Risks

Key risks from dependencies that could block or delay the project:

1. **[Risk name]**: [Description of risk, likelihood, impact if it occurs]
2. **[Risk name]**: [Description of risk, likelihood, impact if it occurs]

## Tech Review Questions

Questions to ask during technical review with an engineering audience:

1. [Question about technical approach or feasibility]
2. [Question about dependencies or integration points]
3. [Question about scalability or performance considerations]
4. [Question about testing strategy or rollout plan]
5. [Question about maintenance or operational concerns]

## Kudos

Recognition for people who contributed to the project planning:

- **[Name]**: [What they did well, specific contribution]
- **[Name]**: [What they did well, specific contribution]

---

## Changelog

### [YYYY-MM-DD HH:MM:SS]
- Initial report generated
- Analyzed [N] documents: [list document names]

```

**Save the report as:**

The filename should be a slug version of the project title:
- Convert project name to lowercase
- Replace spaces with hyphens
- Remove special characters
- Append `-review.md`

```bash
# Example: "Basic Gating" -> basic-gating-review.md
# Example: "Team Formation: Converting Basic Free" -> team-formation-converting-basic-free-review.md
mkdir -p memory/project_review
memory/project_review/[project-name-slug]-review.md
```

**After generating the report, clean up temporary files:**

```bash
rm -rf /tmp/project_review_$$
```

This ensures only the final report remains in `memory/project_review/`, with no intermediate artifacts.

### Step 6: Refreshing Reports

When asked to refresh a report:
1. Read the existing report to get document links from front matter
2. Re-fetch all documents from their original URLs
3. Compare new content with previous analysis
4. Update all sections that have changed; prefer applying small diffs to the sections versus re-writing them
5. Update the `last_updated` timestamp
6. Add an entry to the changelog describing what changed

Example changelog entry for refresh:
```markdown
### [YYYY-MM-DD HH:MM:SS]
- Refreshed report from source documents
- Updated estimates: Total eng weeks increased from 12 to 15
- Added new requirement: [requirement name]
- Updated Tech Spec link (document was moved)
```

## Report Sections Guide

### TL;DR
A single, clear sentence that captures the essence of what this project aims to achieve. Should be understandable to anyone in the company.

### Product Requirements Summary
A narrative summary (not a list) that explains:
- What problem are we solving?
- Who is the target user?
- What are the key features or capabilities?
- What is the expected user impact?

### Complex/Controversial Requirements
Focus on requirements that:
- Have significant technical complexity
- Could be controversial among stakeholders
- Might need to be descoped
- Have dependencies on other teams
- Are at risk of scope creep

### Technical Implementation Summary
A narrative summary (not a list) that explains:
- Overall architecture or design pattern
- Key technical components or systems involved
- Integration points with existing systems
- Technology choices (languages, frameworks, services)

### Scope-Impacting Technical Decisions
Focus on decisions that:
- Could significantly increase or decrease scope
- Have major architectural implications
- Involve tradeoffs between speed and quality
- Might require significant refactoring
- Could affect other teams or systems

### Estimates
Extract all estimation data from documents:
- Look for tables with milestones and durations
- **Preserve original units**: If document uses hours, show hours; if weeks, show weeks
- Check for "Timeline" or "Schedule" sections
- Sum up total time across all workstreams
- Note any caveats or assumptions in estimates
- Include confidence levels if provided (High/Medium/Low)

For high-risk estimates, identify items that:
- Are marked as uncertain or have wide ranges
- Depend on external teams or systems
- Involve new or unfamiliar technology
- Have significant unknowns
- Touch legacy systems or complex code

### Dependencies & Risks
Extract dependency information from:
- "Dependencies" or "Partner Teams" sections
- "Risks and Mitigations" sections
- Slack channel references (e.g., #commerce-gtm-help)
- Mentions of concurrent experiments or projects
- External systems or services required

For each partner team dependency:
- Identify the team (name or Slack channel)
- Describe what's needed from them
- Assess risk level (High/Medium/Low)
- Note any mitigation strategies

For dependency risks:
- Describe how the dependency could block or delay
- Assess likelihood and impact
- Note any timing concerns (e.g., "needs review before we can start")

### Tech Review Questions
Generate thoughtful questions that would help an engineering audience:
- Validate technical approach
- Identify risks or gaps
- Consider alternatives
- Think about edge cases
- Plan for scale and maintenance

Questions should be specific to the project, not generic.

### Kudos
Recognize specific contributions:
- Who wrote clear, thorough specs?
- Who identified important risks or edge cases?
- Who proposed innovative solutions?
- Who facilitated good collaboration?

Be specific about what each person did well.

## Tips

- **Intermediate Files**: Always save fetched documents, JIRA outputs, and other artifacts to `/tmp/project_review_$$/` (not `memory/project_review/`). Clean up the temp directory with `rm -rf /tmp/project_review_$$` after generating the report. Only the final report should exist in `memory/project_review/`.
- **JIRA Issue IDs**: Look for JIRA issue keys (e.g., DBX-1234, TEXP-567) in:
  - Document titles or headers
  - Links to JIRA (e.g., "https://company.atlassian.net/browse/DBX-1234")
  - Text mentioning "Epic" or "Initiative"
  - If multiple JIRA issues are mentioned, use the primary Epic or Initiative
  - If no JIRA issues found, set to "N/A" in front matter
  - Always fetch JIRA issues to get additional context and DRI information
- **DRI Identification**: Find actual names, not user IDs. Check these sources in order:
  1. JIRA issue assignee field (`get-issue` command)
  2. "Driver (DRI)" or "Contributors" tables in documents
  3. Document metadata (authors, last modified by)
  4. CLAUDE.local.md for team roster information
  5. If a document shows `<ri:user ri:account-id="..."/>` tags, try to resolve via JIRA
  6. Only use "Unknown" or "TBD" if names truly cannot be found
- **Estimate Units**: Preserve the original units from the source document:
  - If document shows hours, use hours
  - If document shows days, use days
  - If document shows weeks or eng-weeks, use weeks
  - Convert only if necessary for clarity (e.g., "180 hours (4.5 weeks)")
- **Dependencies**: Look for "Dependencies", "Partner Teams", "Risks and Mitigations" sections
  - Extract Slack channel references (e.g., #commerce-gtm-help)
  - Identify concurrent experiments or projects that interact
  - Note systems or services that must be available
- **Missing Documents**: If you can't find a specific document type (e.g., no separate Design doc), note this in the front matter with "N/A" and explain in the report
- **Document Links**: When a document references other documents, follow those links to get complete context
- **Multiple Documents**: If there are multiple versions of a document, use the most recent one
- **Link Format**: Store full URLs in front matter for easy reference and refresh
- **Figma**: For Figma links, note the link in the front matter but explain that content couldn't be fetched
- **Context from CLAUDE.local.md**: Use team and people information to enrich DRI identification and kudos
- **Filename Slugs**: Always convert project name to a slug (lowercase, hyphens, no special chars) for the filename

## Example Workflow

```bash
# Create temporary directory for intermediate files
TMP_DIR=/tmp/project_review_$$
mkdir -p $TMP_DIR

# Create output directory for final report
mkdir -p memory/project_review

# User provides links
# Link 1: https://company.atlassian.net/wiki/spaces/ERP/pages/3002434012/
# Link 2: https://example.com/docs/project-brief

# Fetch Confluence page
python -m sidekick.clients.confluence get-content-from-link "https://company.atlassian.net/wiki/spaces/ERP/pages/3002434012/" > $TMP_DIR/tech_spec.html

# Fetch Paper doc
python -m sidekick.clients.dropbox get-paper-contents-from-link "https://example.com/docs/project-brief" > $TMP_DIR/prd.md

# Fetch JIRA epic
python -m sidekick.clients.jira get-issue DBX-1234 > $TMP_DIR/jira-epic.txt

# Analyze documents and generate report at memory/project_review/project-name-review.md

# Clean up temporary files
rm -rf $TMP_DIR
```

## Refreshing a Report

```bash
# User: "Refresh the Basic Gating project review"

# Create temporary directory
TMP_DIR=/tmp/project_review_$$
mkdir -p $TMP_DIR

# Read existing report to get links
cat memory/project_review/basic-gating-review.md

# Extract links from front matter:
# prd_link: "https://..."
# tech_spec_link: "https://..."

# Re-fetch documents
python -m sidekick.clients.dropbox get-paper-contents-from-link "$PRD_LINK" > $TMP_DIR/prd-new.md
python -m sidekick.clients.confluence get-content-from-link "$TECH_SPEC_LINK" > $TMP_DIR/tech-spec-new.html

# Compare with previous versions
# Update report sections that changed
# Update last_updated timestamp
# Add changelog entry

# Clean up temporary files
rm -rf $TMP_DIR
```

## Error Handling

- **Document not accessible**: Note in the report that the document couldn't be fetched and why
- **Missing DRI information**: Use "Unknown" or "TBD" and note in report to confirm with team
- **No estimates**: Explicitly state "No estimates available" rather than leaving section empty
- **Ambiguous document type**: If unclear whether a doc is PRD vs Tech Spec, make a best guess and note the ambiguity

## Output Structure

Final output is saved to `memory/project_review/`:
- `[project-slug]-review.md` - The main report (only file in output directory)

Intermediate artifacts are stored in `/tmp/project_review_$$/` during generation:
- `[doc-name].html` or `[doc-name].md` - Fetched source documents
- `jira-epic.txt` - JIRA issue details
- `jira-hierarchy.txt` - Roadmap hierarchy

These temporary files are deleted after the report is generated.

This approach:
- Keeps output directory clean with only final reports
- Prevents clutter from intermediate artifacts
- Reports can be refreshed by re-fetching documents from source URLs
