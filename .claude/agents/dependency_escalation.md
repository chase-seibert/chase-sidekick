---
name: dependency_escalation
description: Draft a document for an escalation of a dependency request 
argument-hint: <document-url>
auto-approve: true
---

# Ask for the following if it's not provided
- One-line description of the escalation 
- PRD doc link
- List of people on both sides 
- Set of JIRA issues 
- Roadmap of dependency team, can just be their own strategic work 

# Write a report
- Draft a doc that would answer these questions. If any given answer is not available, create a blank placeholder. 
- TL;DR with the specific question that needs a decision
- State the “decision needed by” time  
- Placeholder to document the final decision 
- Who are the decision makers on both sides? Try to pair them up on each side by seniority, and be specific about their roles. The goal is to be able to escalate symmetrically, one level at a time on both sides. Make a table with this people view. Include both Product and Engineering folks. 
- Link to the single best product spec for this project, and brief summary of context and background
- Short list of other high priorities of the dependency team. 
- The above should be written collaborative with parties on both sides. The initial draft should clearly label content above as a draft that still needs collaboration. 
- What are the set of JIRA issues that represent the dependencies? Which ones are committed to, already? 
- Are there estimates on these from both the source and dependency teams? 
- What is the holistic current roadmap for the team that the dependency is being requested from? 
- What is the holistic set of all dependencies being asked from the same source team and to the same dependent team, and how does the source team stack rank them? 
- What are some possible options or tradeoffs. Give 2–3 paths with tradeoffs (cost/time/risk). Make your recommendation clear. One option might be self-funding the work -- is this acceptable? Another option might be reducing scope / work arounds. 
- Placeholder for discussion notes with both parties 