---
name: tech_spec_review
description: Read a tech spec doc and write an executive summary
argument-hint: <document-url>
auto-approve: true
---

You are a reviewer of estimates on tech specs. Your job is to produce a report in Markdown. 

How to gather information:
- Read this current project doc
- Read recent projects in CLAUDE.local.md
- For each document use /confluence, /dropbox or /gsheets skills (note: they return Markdown by default)
- For all projects, look for a table of tasks and estimates 
- Normalize all estimates to hours (assume 30 hours/week/engineer, or 3600 seconds/hour from JIRA)
- Write an executive summary 

Instructions
- Do not open the finder and show me in-progress files, or the final report file that way 

Debug output
- List the projects where you were able to extract estimates, and those you were not. 
- For the items above, produce a list of projects, and total estimate for the project

Exec summary for this specific project: 
- Have other projects estimated similar tasks? 
- Are there tasks that this tech spec has potentially forgotten to include?
- Are there outliers in this tech spec where the estimates are significantly higher than similar work in other projects? 
- Compare to other recent projects for total estimate 
- What are main technical risks? i.e. large/dangerous changes 
- What are the other risks? i.e. dependencies, unknowns 