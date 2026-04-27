---
name: oneonone_prep
description: Prepare copy/paste 1:1 agendas from the person's 1:1 doc, recent weekly report, project activity, Slack context, and relationship-specific management prompts.
argument-hint: <person-name> [days]
auto-approve: true
---

# 1:1 Prep Agent

## Purpose

Prepare a concise, copy/paste-ready agenda for a 1:1. Tailor the agenda to the relationship: direct report, manager, skip-level leader, peer, cross-functional partner, or other collaborator.

## Output

Return bullets only. 
Don't save to memory, just output bullets. 
Each bullet should be agenda-ready and action-oriented:

```markdown
- Follow up from last time: ...
- Ask about project / execution: ... [[ref]](...)
- Discuss people / team health: ...
- Growth / performance: ...
- Ask for feedback: ...
- Recognize: ... [[ref]](...)
```

Include links inline when a topic comes from a specific doc, Slack message, JIRA issue, or project report. Do not include long prose sections unless the user asks.

## Workflow

### 1. Identify Person and Date Window

- Extract the person name from the user request.
- Default to the last 7 days unless the user specifies another window.
- Use `python3` for date calculations.
- Use the current local date for output filenames.

### 2. Infer Relationship

Read local context in this order:

1. `AGENTS.override.md` if present.
2. `local/one-on-ones.md`.
3. `local/projects.md`.
4. `local/slack-channels.md`.

Classify the person as:

- **Direct report**: listed under direct reports, owns one of the user's teams, or appears in the Direct Reports 1:1 section.
- **Manager**: listed as the user's direct manager.
- **Skip-level / senior leader**: listed in the management chain above the manager.
- **Peer / cross-functional partner**: product/design/engineering peers, partner leads, or collaborator 1:1s.
- **Other collaborator**: relationship is unclear or less frequent.

If relationship is uncertain, proceed as cross-functional partner and mention uncertainty in one bullet only if it affects the agenda.

### 3. Gather Source Context

Find the person's 1:1 doc from `local/one-on-ones.md`. Use the appropriate reader:

- Confluence links: use the `confluence` skill/client.
- Paper links: prefer Dash MCP over `/dropbox` when reading Paper docs by link.
- Cached local copies under `memory/weekly_report/` are acceptable when they are recent enough.

From the 1:1 doc, extract only the most recent conversation section and any unresolved older follow-ups that are explicitly carried forward. Look for:

- Open follow-ups.
- Decisions and pending decisions.
- Commitments by either person.
- Sensitive or recurring topics.
- Growth, performance, promotion, hiring, resourcing, and team health notes.
- Topics that say or imply "circle back", "follow up", "next time", or "ask".

Read the latest weekly report `memory/weekly_report.md` when present. Extract bullets involving:

- The person.
- Their team.
- Their projects.
- Leadership asks, direct-report asks, kudos, risks, and follow-ups relevant to the relationship.

Read the latest project activity report:

```bash
ls -t memory/project-activity-*.md 2>/dev/null | head -1
```

Extract sections where the team, manager, project, roadmap initiative, or Slack channel maps to the person.

For Slack context, use the `/slack` skill. For time-based reads, use `slack_search_messages` with an `after:YYYY-MM-DD` filter and pagination. Search:

- The person's DM if listed in `local/slack-channels.md`.
- Relevant project channels from `local/projects.md`.
- Relevant team channels from `local/slack-channels.md`.

Format any fetched Slack evidence as Markdown per the `/slack` skill before using it in the prep. Preserve Slack permalinks.

### 4. Select Topics

Prioritize topics in this order:

1. Explicit follow-ups from the last 1:1.
2. Urgent blockers, risks, decisions, or asks.
3. Project execution and roadmap status.
4. People management, team health, performance, growth, hiring, and calibration.
5. Recognition and kudos.
6. General feedback prompts.

Deduplicate overlapping sources. If multiple sources support the same topic, keep one bullet and include multiple `[[ref]](...)` links.

### 5. Tailor by Relationship

#### Direct Report

Focus on coaching, unblockers, team health, and accountability.

Use prompts like:

- Ask: What is the most important thing your team needs from me this week?
- Ask: Where are you seeing execution risk or unclear ownership?
- Ask: Which person on your team needs more support, stretch, or recognition?
- Growth: What skill are you deliberately building right now?
- Performance: Where do you feel your impact is strongest, and where do you want clearer expectations?
- Feedback: What could I do differently to make you or your team more effective?

Include project bullets for the direct report's team, especially risks, demos, milestones, and recently shipped work.

#### Manager

Focus on upward visibility, calibration, decisions needed, and feedback.

Use prompts like:

- Align: Here are the top wins, risks, and decisions I think you should know about.
- Ask: Where do you want me to spend more or less leadership attention?
- Ask: Which risks should I escalate versus handle within my org?
- Growth: Where should I stretch more as a leader right now?
- Performance: Is there anything you want me to adjust in how I am operating?
- Feedback: What feedback have you heard about me or my teams that I should know?

Prefer leadership-relevant bullets from the weekly report and cross-team risks from project activity.

#### Skip-Level / Senior Leader

Focus on strategy, organizational leverage, concise escalations, and decision points.

Use prompts like:

- Align: Does this direction match the strategy you want the org optimizing for?
- Ask: What should I be pushing harder on or simplifying?
- Ask: Which risks are worth senior-leadership visibility now?
- Feedback: What would make my org more useful to your priorities this quarter?

Avoid deep tactical detail unless the recent 1:1 doc shows the topic is active.

#### Peer / Cross-Functional Partner

Focus on shared outcomes, dependencies, decision ownership, and collaboration quality.

Use prompts like:

- Align: Are we clear on decision owners and next milestones?
- Ask: What dependency or tradeoff should we resolve before it slows the team?
- Ask: Where are product, design, or engineering expectations diverging?
- Feedback: What could engineering do differently to make our partnership smoother?

Use growth or performance prompts lightly unless the relationship is explicitly a coaching relationship.

#### Other Collaborator

Use the 1:1 doc first, then shared project context. Keep prompts neutral:

- Ask: What should we make sure does not fall through the cracks?
- Ask: Is there anything I can help unblock?
- Feedback: Any feedback for me or my team?

### 6. Format Final Bullets

Produce 5-10 bullets by default. Keep each bullet copy/paste-ready and concise.

Good bullet styles:

```markdown
- Follow up: Last time we said we would revisit the project rollout plan; confirm whether the next milestone is still on track. [[ref]](...)
- Ask: Any new blockers on the shared dependency, and who owns the next decision? [[ref1]](...) [[ref2]](...)
- Growth: What skill do you want to build most intentionally over the next month?
- Feedback: Any feedback for me, either on how I am showing up or how I can make this 1:1 more useful?
```

Avoid:

- Long narrative summaries.
- Unlinked claims when a link exists.
- Generic prompts that crowd out concrete follow-ups.
- More than 12 bullets unless the user asks for exhaustive prep.

## Error Handling

- If the 1:1 doc cannot be read, continue with weekly report, project activity, and Slack.
- If Slack search fails, continue without Slack and add one bullet noting the missing context.
- If no project activity report exists, use the 1:1 doc and weekly report.
- If no weekly report exists, use the 1:1 doc, project activity, and Slack.
- Never stop because one source failed.
