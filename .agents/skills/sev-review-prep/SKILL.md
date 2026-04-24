---
name: sev-review-prep
description: Generate questions to ask during SEV review meetings based on Confluence SEV review documents
---

# SEV Review Prep Skill

## Overview

This skill helps prepare for SEV (Severity/Incident) review meetings by reading a Confluence SEV review document and generating a list of questions to ask during the review. The output is saved as a Markdown file in the memory directory.

## Usage

When invoked with a Confluence URL to a SEV review document:

```
/sev-review-prep <confluence_url>
```

Example:
```
/sev-review-prep $CONFLUENCE_URL
```

## What This Skill Does

### Read the SEV Document

Use the `/confluence` skill to read the provided Confluence page. The page should be a completed (or in-progress) SEV review document.

### Analyze Completeness

Check for gaps or areas needing clarification:
- Are root causes clearly articulated and complete?
- Is the 5-whys analysis thorough?
- Are prevention measures sufficient?
- Are there obvious missing action items?
- Are process issues addressed?

### Generate Questions Document

Create a questions document with the following sections. Don't include each question below, these are just ideas. Focus on the biggest risks or unknowns. 

#### Executive Summary
- 1-2 sentences: what happened and the outcome
- Teams involved

#### Root Cause Questions

If the root cause is not clear or incomplete:
- What questions would help clarify the root cause?
- What's missing from the 5-whys analysis?
- Are we addressing symptoms vs. root causes?

#### Technical Questions

Questions to understand the technical details:
- What exactly was the fix? 
- Could this have been caught by existing monitoring?
- What assumptions did we make that turned out to be wrong?

#### Impact Questions

Questions about the scope and severity:
- Was the impact assessment complete? What might we be missing?

#### Process Questions

Questions about response and coordination:
- What slowed our response?
- Was ownership clear?
- What would have helped us respond faster?

#### Prevention Questions

Questions about avoiding recurrence:
- How do we prevent this from happening again?
- Are we addressing root causes or symptoms?
- What's our confidence level in the prevention measures?

#### Missing Action Items
- What action items are conspicuously absent?
- Should there be AIs for detection, process, or tooling improvements?
- Do the AIs match the severity and learnings from this incident?

### Write to Memory

Save the questions document as a Markdown file in the memory directory:

**Filename format:** `memory/sev-review-[sev-name]-[date].md`

Example: `memory/sev-review-sev-name-2026-04-21.md`

Use the SEV name from the document (lowercase, hyphens) and today's date.

## Output Format

The questions document should be formatted as Markdown with clear sections and bullet points for easy scanning during the review meeting.

**Document Structure:**
```markdown
# SEV Review Questions: [SEV Name]

**SEV Level:** [Level] | **Type:** [Type] | **Review Date:** [Date]
**TLOC:** [Name] | **Teams:** [Teams]

## Executive Summary
[1-2 sentence summary]

## Root Cause Questions
[Questions about root causes, with clarifications if unclear]

## Technical Questions
[Questions about technical details]

## Impact Questions
[Questions about scope and impact]

## Process Questions
[Questions about response and coordination]

## Prevention Questions
[Questions about prevention, including missing AIs]
```

## Tips for Generating Good Questions

- **Probe unclear areas**: If something in the doc is vague, ask about it
- **Challenge assumptions**: Question revenue estimates, impact scope, prevention confidence
- **Look for gaps**: What's not discussed that should be?
- **Ask "why" repeatedly**: Don't accept first-level explanations
- **Focus on prevention**: Are the AIs sufficient to prevent recurrence?
- **Process improvements**: What systemic issues need addressing?
