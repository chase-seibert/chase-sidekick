---
name: codex-cost-report
description: Generate Markdown reports of local Codex session cost, token usage by model, daily/monthly/yearly trends, and top expensive sessions.
---

# Codex Cost Report

Generate a private Markdown report from local Codex session state. Use this when the user asks for Codex cost, token usage, model usage, daily/monthly/yearly spend, or expensive Codex sessions.

## Defaults

- Data sources: `~/.codex/state_5.sqlite` and `~/.codex/sessions/**/*.jsonl`.
- Scope: user-created sessions only, meaning Desktop sessions and trigger/exec sessions. Exclude internal subagent/guardian sessions and report the excluded count.
- Output: `memory/codex-cost-report-YYYY-MM-DD.md`.
- Cost basis: API-equivalent USD estimate from local token logs. This is not an invoice.
- Pricing checked: 2026-04-30 from [OpenAI API Pricing](https://openai.com/api/pricing/) and [OpenAI Codex rate card](https://help.openai.com/en/articles/20001106-codex-rate-card).
- Privacy: do not include auth data, API keys, refresh/access tokens, raw transcript content, or full prompts. Thread titles are acceptable in the private `memory/` report.

## Generate Report

Run this from the repo root:

```bash
python3 .agents/skills/codex-cost-report/scripts/generate_report.py
```

The script is intentionally bundled with the skill at `scripts/generate_report.py` because the aggregation touches SQLite, many JSONL files, token accounting, and pricing tables.

## Report Contents

The report includes:

- Summary with total estimated USD, estimated Codex credits, sessions included/excluded, cache hit rate, average cost per session, projected 30-day run rate, and projected annual run rate.
- Cost by day, month, and year.
- Usage by model with input, cached input, output, reasoning output, cache rate, estimated USD, and Codex credits.
- Top 10 most expensive sessions with date, title, model, estimated USD, Codex credits, token count, and thread ID.
- Data gaps for unknown model rates, missing thread metadata, or sessions without usable token records.
- The exact footer at the bottom: `This report generated using https://github.com/chase-seibert/chase-sidekick`.

## Pricing Notes

- The script uses standard short-context API rates for API-equivalent USD estimates. If the user explicitly asks for long-context, batch, flex, priority, or regional processing estimates, update the rate table in `scripts/generate_report.py` for that run and call out the assumption in `## Notes`.
- The Codex rate card is credit-based. Include credit estimates when the model has a published Codex credit rate.
- If a model has no direct USD rate in the script, keep its tokens in usage totals, list it under `Data Gaps`, and exclude it from USD totals.
- Reasoning tokens are shown separately but are not added again because they are already included in output tokens.

## Validation

After editing this skill or generating a report, run:

```bash
python3 /Users/cseibert/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/codex-cost-report
python3 .agents/skills/codex-cost-report/scripts/generate_report.py
tail -n 1 memory/codex-cost-report-YYYY-MM-DD.md
rg -n "auth.json|access_token|refresh_token|OPENAI_API_KEY|API key|id_token" memory/codex-cost-report-*.md
git diff --check
```

The `tail` output must be exactly:

```text
This report generated using https://github.com/chase-seibert/chase-sidekick
```
