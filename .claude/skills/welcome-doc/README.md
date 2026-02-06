# Welcome Doc Skill

Create personalized employee onboarding documents in Confluence based on a template and/or example, with an optional interactive guided workflow.

## Purpose

Automate the creation of comprehensive welcome/onboarding documents for new employees. Instead of manually copying templates and filling in details, this skill guides you through an interactive process that:

- Fetches content from existing examples
- Queries JIRA for team roadmap information
- Generates personalized welcome messages
- Creates structured Confluence pages with all necessary sections

## Quick Start

Simply run:

```
/welcome-doc link1 link2 free text context
```

Claude will first try to get any information it needs from the template and example (if provided)
Claude will interactively prompt you any information it can't find itself

## What You'll Be Asked

### 1. Employee Information
- Full name (e.g., "John Smith")
- Role/title (e.g., "Engineering Manager")
- Team name (e.g., "Platform Team")
- Start date (optional)

### 2. Template/Example Document
Provide a URL or path to an existing onboarding document to use as a template:
- Confluence page URL
- Dropbox Paper URL
- Local file path
- Or select "None" to start from scratch

### 3. Team Context
- Manager name
- Onboarding buddy
- HR Business Partner (HRBP)
- Skip-level manager
- Peer managers

### 4. Direct Reports (If Applicable)
- Does the new employee have direct reports?
- Screenshot of org chart (optional but helpful)
- JIRA project keys for their team(s)

### 5. Additional Context
Free-form text for any special circumstances:
- Transition details (taking over from someone?)
- Manager PTO dates
- New team members joining
- Product partners joining
- Any other important context

### 6. Confluence Destination
- Space key (e.g., "ENG" or "TNC")
- Parent page ID (optional)
- Custom title (or use default)

## What Gets Generated

A comprehensive Confluence onboarding document with:

### 📝 Personal Welcome
- Customized introduction from manager
- Context about role and transition
- Onboarding buddy details
- Important dates and scheduling notes

### 🏢 Company & Product
- Onboarding resources and checklists
- Company culture and values
- Product learning guides
- Tools and systems

### 👥 Team Structure
- Organizational hierarchy
- Direct reports (if applicable)
- Key stakeholders to meet
- Recurring 1:1s to schedule

### 🗺️ Roadmap Overview
(If JIRA projects provided)
- Team mission and goals
- Current initiatives with status
- Links to JIRA issues and PRDs
- Project descriptions and timelines

### 💬 Communication
- Slack channels organized by type:
  - Organizational
  - Team-specific
  - Project-specific
- Meeting calendars
- Team rituals

### 📈 Growth & Performance
- Working style documentation
- Performance review process
- Career frameworks
- 30/60/90 day goals

## Example Usage

### Scenario 1: New Engineering Manager

```
/welcome-doc

> Employee: Sarah Johnson
> Role: Engineering Manager
> Team: API Platform
> Template: https://company.atlassian.net/wiki/.../example-onboarding
> Manager: Alice Smith
> Buddy: Bob Chen
> HRBP: Carol Davis
> Has direct reports: Yes
> JIRA projects: API, GATEWAY
> Context: Taking over from Dave who is moving to Architecture team.
  Alice on PTO March 15-22.
> Confluence: Space ENG, no parent
```

**Result:** Comprehensive onboarding doc with API Platform roadmap, team structure, and personalized context.

### Scenario 2: Senior Engineer (No Direct Reports)

```
/welcome-doc

> Employee: Mike Torres
> Role: Senior Software Engineer
> Team: Data Infrastructure
> Template: https://paper.dropbox.com/.../engineer-onboarding
> Manager: Emma Wilson
> Buddy: Frank Lee
> Skip: George Harris
> Has direct reports: No
> JIRA projects: DATA
> Context: First infra hire, building foundation for data platform
> Confluence: Space ENG, parent 123456
```

**Result:** IC-focused onboarding doc with technical ramp-up goals and data platform context.

## Features

### ✨ Smart Content Extraction
- Automatically fetches template documents
- Preserves relevant links and resources
- Filters out team-specific content that doesn't apply
- Keeps organizational and company-wide information

### 📊 Roadmap Integration
- Queries JIRA for active initiatives
- Fetches PRD documentation from linked Paper docs
- Generates readable summaries
- Creates organized tables with links

### 🎨 Rich Formatting
Uses native Confluence components:
- Info panels for important callouts
- Expand sections for long lists
- Tables for roadmap overviews
- Proper heading hierarchy

### 🎯 Role-Appropriate Goals
Automatically generates 30/60/90 day goals based on role:
- **Managers:** Focus on team ownership, stakeholder relationships, hiring
- **ICs:** Focus on technical ramp-up, contributions, system knowledge

### 🖼️ Screenshot Support
Upload an org chart or team structure screenshot, and it will be included in the document for visual reference.

## Tips

### 1. Use Recent Examples
The better your template/example document, the better the output. Use a recent onboarding doc that has all current links and resources.

### 2. Prepare JIRA Project Keys
If you know the new hire's team JIRA projects, have them ready. The roadmap section is one of the most valuable parts.

### 3. Include Context
The "additional context" field is your opportunity to add personality and specific details. Don't skip it!

### 4. Review Before Sharing
The generated document is comprehensive, but you should review it for:
- Outdated links (if template was old)
- Team-specific customizations needed
- Any sensitive information to remove

### 5. Iterate
After the first doc is created, you can ask Claude to update specific sections:
- "Add a section about our team's tech stack"
- "Update the 30-day goals to include security training"
- "Add links to our team's recent demo videos"

## Requirements

### Configured Skills
This skill uses other skills, which must be configured:
- `/confluence` - For creating pages
- `/jira` - For roadmap queries (optional)
- `/dropbox` - For Paper doc templates (optional)

### Permissions
You'll need:
- Confluence write access to the target space
- JIRA read access (if querying roadmap)
- Access to template documents (if using)

## Output Location

Documents are created directly in Confluence at the location you specify. A temporary HTML file is created at `/tmp/welcome-doc-[name].html` during generation but is cleaned up afterward.

## Customization

After creation, you can:
- Edit the Confluence page directly
- Ask Claude to update specific sections
- Copy the structure for other team members
- Save as a team template in Confluence

## Troubleshooting

### Template Not Found
If the template URL is inaccessible:
- Check permissions on the source document
- Try a different example doc
- Choose "None" to start from scratch

### JIRA Projects Empty
If roadmap queries return no results:
- Verify the project key is correct
- Check if issues exist in that project
- Ensure you have JIRA read permissions

### Confluence Creation Failed
If page creation fails:
- Check Confluence space permissions
- Verify parent page ID exists
- Try creating without parent ID
- HTML file is saved locally as backup

## Related Skills

- **Confluence** - For manual page updates
- **JIRA** - For additional roadmap queries
- **Memory** - For saving generated content locally
- **Transcript** - For documenting your workflow

## Future Enhancements

Ideas to suggest to Claude:
- Support for multiple template merging
- Automatic team member profile fetching
- Integration with HR systems for basic info
- Version tracking and changelog
- Batch creation for multiple new hires

Just ask Claude to add these when you need them!
