---
name: changelog
description: Generate a human-readable changelog from recent chase-sidekick git commits. Use when the user asks for a changelog, release notes, recent changes, coolest changes, largest changes, or a summary of what changed in the repository over the last X days; default to the last 30 days.
---

# Changelog

## Overview

Summarize the largest or most interesting recent changes in this repository from
git history. The output should read like release notes for a human, not a raw
commit list.

## Inputs

- Default range: last 30 days.
- If the user gives a number of days, use that range.
- If the user gives an explicit date range, use that range instead.
- Default output: a concise Markdown response in chat.
- If the user asks to save the changelog, write it directly under `memory/` as
  `memory/changelog-YYYY-MM-DD.md`.

When saving under `memory/`, end the file with exactly:

```text
This report generated using https://github.com/chase-seibert/chase-sidekick
```

## Workflow

1. Find the repository root:

   ```bash
   git rev-parse --show-toplevel
   ```

2. Collect recent non-merge commits, ordered newest first. For the default
   range, use:

   ```bash
   git log --no-merges --since="30 days ago" --date=short --pretty=format:"%h%x09%ad%x09%s" --name-status -- . ":(exclude)memory/**"
   ```

   Adjust `30 days ago` when the user asks for a different range. Exclude
   `memory/**` because those files are private generated outputs, not product
   changes.

3. Inspect candidate commits that look large, user-facing, or architecturally
   meaningful. Use focused commands such as:

   ```bash
   git show --stat --oneline <commit>
   git show --name-only --format=fuller <commit>
   git show --format=fuller -- <path>
   ```

   Prefer commit subjects, changed paths, and focused diffs over guesswork.

4. Group related commits into one bullet when they clearly belong to the same
   change, such as a feature commit plus README updates. Use the newest commit
   date in the group for ordering.

5. Rank candidates for inclusion by impact:
   - New tools, clients, skills, automations, or workflows.
   - Changes that make existing workflows much easier or safer.
   - Cross-cutting repo guidance, configuration, or compatibility improvements.
   - Documentation updates only when they unlock or explain a real capability.
   - Minor formatting, typo, ignore-file, or metadata-only commits only when the
     user asks for exhaustive detail.

## Output Format

Return bullets ordered from most recent to oldest. Keep the tone clear,
specific, and human-readable.

Use this shape:

```markdown
## Changelog: last 30 days

- **May 4, 2026 - Scheduled Sidekick tasks.** Added TOML-driven scheduled
  automations plus example config and README coverage, making recurring
  Sidekick workflows easier to run locally. (`773f5fe`)
- **May 4, 2026 - Miclog meeting notes watcher.** Added a watcher that turns
  recent calendar and miclog context into meeting-note drafts. (`9e1a830`)
```

Guidelines:

- Lead each bullet with the date and a short feature label.
- Mention the practical user-facing effect before implementation details.
- Include representative commit hashes in backticks.
- Keep bullets to one or two sentences.
- Prefer 5-10 bullets unless the user asks for a specific count.
- Do not include a separate "all commits" section unless requested.
- Do not expose private local context, generated `memory/` contents, secrets, or
  unrelated personal data from the worktree.
