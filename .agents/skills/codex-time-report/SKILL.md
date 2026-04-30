---
name: codex-time-report
description: Estimate human-active and agent-elapsed Codex coding vs cowork time from session logs and git commits by day, week, and month.
---

# Codex Time Report

Estimate how much human attention time the user spends interacting with Codex in
this project, split into `coding` and `cowork` time. Also report agent elapsed
time and async wait time so the user's leverage is visible.

This skill is Codex-only. Do not claim that it analyzes Claude Code sessions.

## Inputs

- Default range: all Codex sessions for the current repository found under
  `~/.codex/sessions/**/rollout-*.jsonl`.
- If the user gives a date range, filter sessions by first prompt time in that
  range.
- Default output: `memory/codex-time-YYYY-MM-DD.md`.

## Source Data

Use local Codex JSONL session logs and the current repository's git history.

1. Find the repository root with `git rev-parse --show-toplevel`.
2. Read the repository remote with `git config --get remote.origin.url`.
3. Read Codex session files from `~/.codex/sessions/**/rollout-*.jsonl`.
4. Include a session when either:
   - `session_meta.payload.cwd` is inside this repository or one of its
     worktrees, or
   - `session_meta.payload.git.repository_url` matches the current repository
     remote.
5. Group files by Codex thread id when an `event_msg` contains
   `payload.thread_id`; otherwise use `session_meta.payload.id`. Treat the
   group as one reporting session.

Do not include prompt text in the report unless the user explicitly asks for
examples. Session ids, dates, durations, changed paths, and commit subjects are
enough.

## Timing Rules

- First prompt: earliest timestamp for a `response_item` whose payload is a
  message with `payload.role == "user"`.
- Last prompt: latest timestamp for a user message in the grouped session.
- Cowork endpoint: last prompt time.
- Coding endpoint: matching git commit time when available.
- Convert all timestamps to `America/Los_Angeles` for reporting.
- Track three time metrics per session:
  - `human_active_time`: estimated time the user spent prompting, reviewing, and
    steering.
  - `agent_elapsed_time`: first prompt to cowork/coding endpoint.
  - `async_wait_time`: `agent_elapsed_time - human_active_time`, never below
    zero.

Single-prompt cowork sessions may legitimately report `0m`, because cowork time
elapsed is measured from first prompt to last prompt.

## Human-Time Heuristic

Default to the active-window model. This is intentionally conservative and
should be described as an estimate, not a precise time tracker.

1. Collapse user messages with the same timestamp into one prompt event.
2. Exclude injected context from prompt-size estimates, including:
   - AGENTS.md instructions and environment context blocks.
   - `<skill>...</skill>` blocks.
   - `<environment_context>...</environment_context>` blocks.
   - Tool or connector payloads pasted by the harness.
3. Estimate prompt drafting time from the cleaned prompt length. Use a readable
   typing/editing rate such as 900 characters per minute, clamped between `30s`
   and `8m`.
4. For the first real prompt, count the clamped drafting estimate.
5. For follow-up prompts, count the larger of:
   - the prompt drafting estimate, or
   - the time since the last visible agent activity, capped at `10m`.
6. Do not count post-final reading or review time unless the user sends another
   prompt, because there is no observable signal for it.

Visible agent activity includes assistant messages, tool calls, tool results,
and event messages before the prompt. If the last visible activity is missing,
fall back to the prompt drafting estimate.

## Classification

Classify the whole session as `coding` if it changes local workspace content
outside `memory/`. Otherwise classify it as `cowork`.

Strong coding signals:

- `apply_patch` custom tool calls that add, update, delete, or move a path
  outside `memory/`.
- Shell commands that clearly write repo files outside `memory/`, such as
  redirection, `tee`, `touch`, `mkdir`, `cp`, `mv`, `git mv`, code generators,
  formatters that rewrite files, or Python snippets using `write_text`, `open`
  in write/append mode, or similar write APIs.
- `git commit` or `git add` commands when the matching commit or staged paths
  include non-`memory/` files.

Cowork signals:

- Read-only exploration, planning, reporting, or analysis.
- Remote service reads or writes, such as Confluence/Jira/Gmail/Calendar/Slack
  operations, when they do not change this local repository.
- Writes only under `memory/`, including generated reports, cached context,
  and transcripts. Temporary and intermediate report files belong in `$TMPDIR`.

If a command looks like it may have written files but the changed path cannot be
determined, list the session under "Ambiguous Sessions" and explain the signal.
Do not classify remote writes as coding unless they also changed local
non-`memory/` workspace files.

## Commit Matching

For coding sessions, find the endpoint from git history:

1. Collect candidate changed paths from `apply_patch` and clear local write
   commands, ignoring paths under `memory/`.
2. Read commits after the session's first prompt with commit timestamp, subject,
   and changed paths, excluding `memory/**`.
3. Use the earliest commit after the first prompt that changes at least one
   candidate path.
4. If the session itself ran `git commit`, prefer that commit when it changes a
   candidate path.
5. If no matching commit exists, use last prompt as the endpoint and flag the
   session as `uncommitted/no matching commit`.

When a coding session spans past the matching commit because the user kept
chatting afterward, stop coding time at the commit time.

## Aggregation

For each session:

- `agent_elapsed_time = endpoint - first_prompt`, never below zero.
- `human_active_time` comes from the active-window heuristic, capped to
  `agent_elapsed_time` for sessions with nonzero elapsed time.
- `async_wait_time = agent_elapsed_time - human_active_time`, never below zero.
- Split human-active and agent-elapsed intervals across local day, ISO week, and
  month boundaries instead of assigning the full duration to the start date.
- Use Monday-start ISO weeks and label them as `YYYY-Www`.
- Track totals by `coding`, `cowork`, and combined total for each timing metric.

## Report Format

Write a Markdown report to `memory/codex-time-YYYY-MM-DD.md` unless
the user requested a different `memory/` path.

Include:

- Title and generated timestamp.
- Date range analyzed and number of Codex sessions included.
- Top summary of `human_active_time` for coding, cowork, and overall time.
- Secondary summary of agent elapsed time, async wait time, and the
  human/agent ratio.
- Day, week, and month tables that default to human-active time.
- Coding session details: session id/thread id, prompt count, first prompt,
  endpoint, human active, agent elapsed, async wait, matching commit if any,
  confidence notes, and changed paths.
- Cowork session details: session id/thread id, prompt count, first prompt, last
  prompt, human active, agent elapsed, async wait, and confidence notes.
- Ambiguous or uncommitted sessions, with the reason they were flagged.
- Methodology notes that briefly state the timing, human-time heuristic, and
  classification rules.

End every generated report with exactly:

```text
This report generated using https://github.com/chase-seibert/chase-sidekick
```

## Validation

After writing the report:

- Confirm the output path is `memory/codex-time-YYYY-MM-DD.md` unless the user requested
  another `memory/` path.
- Confirm the final line is the required Sidekick footer.
- Confirm human-active totals are lower than or equal to agent-elapsed totals.
- Spot-check at least one known coding session against a matching git commit
  when the date range includes one.
- Spot-check at least one memory-only report generation session as `cowork`
  when the date range includes one.
- Spot-check one session invoked with a skill block and confirm the skill body
  did not inflate prompt drafting time.
