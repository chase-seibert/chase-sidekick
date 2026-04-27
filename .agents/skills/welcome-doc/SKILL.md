---
name: welcome-doc
description: Create personalized employee onboarding documents in Confluence
argument-hint:
allowed-tools: AskUserQuestion, Bash, Read, Write, Skill
---

# Welcome Doc Skill

Create personalized employee onboarding documents in Confluence based on a template or example.

When invoked, use the Welcome Doc agent to handle the request: $ARGUMENTS

## Usage

```
/welcome-doc link1 link2 free text context
```

The agent will first try to figure out whatever it can by reading any provided links to templates and examples, then interactively prompt as needed for:
1. Template or example document (Confluence URL, Paper URL, or local file)
2. New employee details (name, role, team)
3. Team information and context
4. Direct reports (if applicable) and optional screenshot
5. Additional context (manager PTO, onboarding buddy, etc.)

## What This Skill Does

1. **Gathers Information**: Prompts for all necessary details through interactive questions
2. **Fetches Context**:
   - Reads template/example documents
   - Queries JIRA for roadmap information
   - Extracts team and project context
3. **Generates Document**: Creates a personalized Confluence welcome document with:
   - Personalized welcome message
   - Team and organizational structure
   - Roadmap overview with links
   - Key people to meet
   - 30/60/90 day goals
4. **Saves to Confluence**: Creates the page in the specified Confluence space

## Examples

### Basic Usage
```
/welcome-doc link1 link2 free text context
```

Agent will prompt for these if needed:
- New employee name
- Template document URL
- Team information
- Additional context

### What Gets Created

A comprehensive onboarding document including:
- Personal welcome message from manager
- Team structure and reporting relationships
- Product and company familiarization links
- Project roadmap with JIRA links and summaries
- Slack channels organized by category
- Key stakeholders to meet
- Working style and performance review process
- 30/60/90 day goals

## Required Information

The agent will prompt for:

**Employee Details:**
- Full name
- Role/title
- Team name
- Start date (optional)

**Template:**
- URL to example onboarding doc (Confluence or Paper)
- Or path to local template file

**Team Context:**
- Manager name
- Onboarding buddy
- HRBP
- Skip-level manager
- Peer managers

**Direct Reports (if applicable):**
- Whether employee has direct reports
- Screenshot of org chart or list (optional)
- Team JIRA project keys

**Additional Context:**
- Transition notes (taking over from someone?)
- Manager PTO dates
- New team members joining
- Any special circumstances

## Output

Creates a Confluence page with:
- Title: "Welcome to [Company], [Name]!"
- Location: Specified Confluence space and folder
- Format: Structured markdown with Confluence macros
- Components: Info panels, expand sections, tables

Returns the Confluence page URL when complete.

## Notes

- Uses existing skills: /confluence, /jira, /dropbox
- Fetches real roadmap data from JIRA
- Extracts content from example documents
- Filters and organizes Slack channels
- Generates appropriate 30/60/90 goals based on role
