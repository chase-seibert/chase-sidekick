---
name: skill-audit
description: Audit Sidekick skills for maintenance signals. Use when Codex needs to create a Markdown report of skills that have not been used recently, skills that have not been updated recently, and the most used skills, with clickable links to each skill's SKILL.md file.
---

# Skill Audit

Generate a maintenance report for skills under `.agents/skills`.

## Workflow

1. Read `AGENTS.md` and any loaded override instructions for report-output conventions.
2. Discover skills with `rg --files .agents/skills -g 'SKILL.md'`, and use the parent folder name as the skill name unless frontmatter says otherwise.
3. Measure update freshness with git history. Prefer `git log -1 --date=short --format=%cs -- .agents/skills/<skill>/SKILL.md .agents/skills/<skill>/README.md .agents/skills/<skill>/agents/openai.yaml`; fall back to filesystem mtime only for untracked files.
4. Measure usage from local Codex records under `~/.codex/sessions`, `~/.codex/archived_sessions`, and `~/.codex/session_index.jsonl`. Treat usage as inferred, not authoritative.
5. Build a Markdown report in `memory/skill-audit-YYYY-MM-DD.md`.
6. Print only the relative report path at the end.

## Usage Heuristics

Count a skill as used in a session when a non-`session_meta` JSONL entry contains concrete evidence such as:

- A tool command reading or referencing `.agents/skills/<skill>/SKILL.md`.
- A tool command reading or referencing `/Users/.../.codex/skills/.../<skill>/SKILL.md` for user-level skills when the user explicitly asks to include them.
- Assistant text such as `Using the <skill> skill`, `Use $<skill>`, or `the [<skill-name> skill]`.

Do not count the always-loaded skills inventory in system prompts or `session_meta` records. Those mention every available skill and would make all skills look used.

## Report Shape

Use explicit thresholds in the summary. Defaults:

- Not used recently: no observed use in the last 14 days, or no observed use at all.
- Not updated recently: last skill-file update more than 7 days ago.
- Most used: top 10 by observed use sessions, breaking ties by most recent use.

Include these sections:

1. `## Summary` with scope, thresholds, source directories, and caveats.
2. `## Skills Not Used Recently` with columns `Skill`, `Last Observed Use`, `Use Sessions`, `Last Updated`, and `Link`.
3. `## Skills Not Updated Recently` with columns `Skill`, `Last Updated`, `Days Since Update`, `Last Observed Use`, and `Link`.
4. `## Most Used Skills` with columns `Skill`, `Observed Use Sessions`, `Last Observed Use`, `Last Updated`, and `Link`.
5. `## Method Notes` explaining that usage comes from local Codex logs and may miss skill use that did not read or name the skill explicitly.

Use relative Markdown links such as `[SKILL.md](../.agents/skills/jira/SKILL.md)` when writing from `memory/`, so the links work from the generated report.

End with the exact required footer:

`This report generated using [chase-sidekick](https://github.com/chase-seibert/chase-sidekick) and the [skill-audit skill](https://github.com/chase-seibert/chase-sidekick/tree/main/.agents/skills/skill-audit).`
