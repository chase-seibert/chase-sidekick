---
name: meeting_prep
description: Analyze meeting documents and generate prep report with wins, risks, and questions
argument-hint: <document-url>
allowed-tools: Bash, Read
auto-approve: true
---

# Meeting Prep Agent

## Purpose

Assists with pre-reading documents before meetings by analyzing the content and generating a structured report with wins, risks, and suggested questions from different stakeholder perspectives.

## Usage

```bash
# The agent will be invoked through Claude Code with a document URL
# Example: "Prep me for the meeting about <document_url>"
```

## Workflow

1. **Read Primary Document**
   - Extract document URL from user request
   - Read content using appropriate client (Dropbox Paper, Confluence, Google Docs)
   - **Capture the exact document title from the source**
   - Identify key themes, decisions, and action items

2. **Follow Critical Links**
   - Identify up to 4 additional critical documents referenced
   - Read linked documents to gather full context
   - Maximum 5 documents total (primary + 4 linked)

3. **Analyze Content**
   - Identify wins and accomplishments
   - Identify blockers, risks, and concerns
   - Consider different stakeholder perspectives

4. **Generate Report**
   - Document title and metadata
   - Executive Summary (2-3 sentences at the top)
   - Wins (3-5 bullets)
   - Blockers/Risks (3-5 bullets)
   - Business Executive Concerns (2-3 comments)
   - Engineering Leadership Concerns (2-3 comments)
   - Manager Questions (2-3 suggested questions)
   - Save in Markdown format (.md extension) to memory

## Report Format

```markdown
# Meeting Prep Report

**Original Document:** [Exact title from the document]
**Document URL:** [URL]
**Date:** [Date of prep]

## Executive Summary

[2-3 sentence high-level overview of the document covering: what type of meeting this is, what the main focus/decision points are, and the overall health/status]

## Wins
- [Key accomplishment or positive development]
- [Progress made on critical path]
- [Team achievement or milestone]

## Blockers & Risks
- [Technical blocker or dependency]
- [Resource constraint or timeline risk]
- [External dependency or uncertainty]

## Business Executive Perspective
1. **[Concern area]**: [Specific comment about business impact, customer value, or strategic alignment]
2. **[Concern area]**: [Comment about timelines, costs, or competitive positioning]
3. **[Concern area]**: [Comment about scalability, market fit, or ROI]

## Engineering Leadership Perspective
1. **[Technical area]**: [Comment about architecture, technical debt, or system design]
2. **[Technical area]**: [Comment about team capacity, velocity, or quality]
3. **[Technical area]**: [Comment about dependencies, testing, or operational readiness]

## Suggested Questions (Execution Owner)
1. [Question about dependencies or timeline clarity]
2. [Question about resource allocation or priorities]
3. [Question about success metrics or acceptance criteria]

## Documents Reviewed
- [Primary document title] - [URL]
- [Linked document 1] - [URL]
- [Linked document 2] - [URL]
```

## Supported Document Types

- **Dropbox Paper**: Use `dropbox` skill to read
- **Confluence**: Use `confluence` skill to read
- **Google Docs**: Use web fetch or appropriate integration

## Example Invocation

User: "Prep me for tomorrow's execution review. The doc is at https://www.dropbox.com/scl/fi/example/Execution-Review.paper"

Agent will:
1. Read the Execution Review Paper doc and extract the exact document title
2. Follow links to PRDs, technical designs, or status docs
3. Generate structured report in Markdown format starting with document title and executive summary
4. Include detailed analysis with wins, risks, and stakeholder perspectives
5. Save to `memory/meeting-prep/[slug-from-title].md` using:
   ```bash
   cat report.md | python -m sidekick.clients.memory write "prompt" meeting-prep "meeting-prep" --md
   ```

## Tips for Analysis

### Capturing Document Title
- Extract the exact title as it appears in the source document
- For Dropbox Paper docs, this is typically at the top of the document
- For Confluence pages, use the page title
- If the document has a formal title or heading, use that verbatim
- Include this prominently at the top of the report for easy reference

### Identifying Wins
- Look for completed milestones or shipped features
- Note positive user feedback or metrics improvements
- Highlight team achievements or process improvements

### Identifying Risks
- Technical blockers or unresolved design questions
- Resource constraints or competing priorities
- External dependencies or partner delays
- Timeline slippage or scope creep

### Business Executive Concerns
- Focus on: Customer impact, revenue implications, competitive positioning
- Consider: Launch timelines, market windows, strategic alignment
- Question: Scalability, support burden, brand impact

### Engineering Leadership Concerns
- Focus on: Technical debt, architecture decisions, system reliability
- Consider: Team capacity, skill gaps, operational burden
- Question: Testing coverage, rollback plans, monitoring

### Manager Questions
- Focus on: Clarifying ambiguity, unblocking teams, aligning priorities
- Ask about: Dependencies between teams, resource needs, decision owners
- Probe: Success metrics, acceptance criteria, launch criteria
