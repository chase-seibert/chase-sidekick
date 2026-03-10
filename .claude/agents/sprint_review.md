---
name: sprint_review
description: Generate a sprint review report 
argument-hint: <google-sheets-url>
allowed-tools: Bash, Read
auto-approve: true
---

# Sprint Review Agent

Given a Google Sheet of notes about a recent sprint, create an executive summary 

# Steps
1. User will provide a URL to a Google Sheet, if not prompt the user
2. Make sure you can access the sheet with /gsheets. If not, stop and prompt the user to copy/paste content into the chat. 
3. Look at the first tab with results (should be the tab specified in the URL) just the rows for the teams that report to me. This context should be in  CLAUDE.local.md. 
4. For any projects mentioned, look at recent memories to see if there are upcoming milestones or launch updates. Especially the weekly report. 
5. If there are linked Sprint Retro docs, read them as well for context

# Basic Output 
- Confirmation that the sheet was able to be read
- Specify what sprint this was for
- List which teams you looked at in the sheet
- List which teams had actual content in the sheet, and warn on any teams that did NOT seem to have content
- List any docs you were able to read or NOT able to read

# Executive summary output
Speak to these questions. If there are no instances for a given bullet, you can just skip it. 
- Are there any common patterns across my teams? 
- Are there any common patterns between my teams and other teams? 
- Are there any recent launch milestones or risks associated with mentioned projects? 
- If you have references for any of the above, include links