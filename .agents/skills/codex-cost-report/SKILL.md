---
name: codex-cost-report
description: Generate Quarto and HTML reports of local Codex session cost, token usage by model, project, coding vs cowork cost, weekly trends, annual projections, and top expensive sessions.
---

# Codex Cost Report

Generate a private Quarto report from local Codex session state and render it to HTML. Use this when the user asks for Codex cost, token usage, model usage, project-level spend, daily/monthly/yearly spend, projected annual cost, coding vs cowork spend, weekly spend trends, or expensive Codex sessions.

## Defaults

- Data sources: `~/.codex/state_5.sqlite` and `~/.codex/sessions/**/*.jsonl`.
- Scope: user-created sessions only, meaning Desktop sessions and trigger/exec sessions. Exclude internal subagent/guardian sessions and report the excluded count.
- Output source: `memory/codex-cost-report-YYYY-MM-DD.qmd`.
- Rendered output: `memory/codex-cost-report-YYYY-MM-DD.html`.
- Cost basis: prefer actual recorded USD from local Codex token logs when present; otherwise use API-equivalent USD estimates from local token logs. This is not an invoice.
- Pricing checked: 2026-07-01 from [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing) and [OpenAI Codex rate card](https://help.openai.com/en/articles/20001106-codex-rate-card).
- Project cost state: update `COSTS.md` at each tracked project's canonical project/repo root on every successful run.
- Privacy: do not include auth data, API keys, refresh/access tokens, raw transcript content, or full prompts. Thread titles are acceptable in the private `memory/` report.

## Generate Report

Run this from the repo root:

```bash
python3 .agents/skills/codex-cost-report/scripts/generate_report.py
```

The script is intentionally bundled with the skill at `scripts/generate_report.py` because the aggregation touches SQLite, many JSONL files, token accounting, and pricing tables.

The script must render HTML on every run with Quarto. If `quarto` is missing or rendering fails, treat that as a report generation failure after preserving the `.qmd` source for debugging.

## Report Contents

The report includes:

- Summary with total USD, cost basis, actual-recorded-USD session count, estimated Codex credits, sessions included/excluded, cache hit rate, average cost per session, projected 30-day run rate, and projected annual run rate.
- Cost by day, month, year, project, and coding/cowork work type.
- Charts in the `.qmd` and rendered HTML:
  - Bar chart of the top 10 most expensive projects.
  - Bar chart of the top 10 most expensive sessions.
  - Pie chart of coding vs cowork cost.
  - Line graph of cost per ISO week.
- Usage by model with input, cached input, output, reasoning output, cache rate, estimated USD, and Codex credits.
- Cost by project with primary working directory, session count, coding/cowork split, USD, share, average session cost, Codex credits, token count, and cache rate.
- Project `COSTS.md` files with total completed-month USD at the top and a reverse-chronological monthly totals table beneath it.
- Top 10 most expensive sessions with date, project, title, model, USD, Codex credits, token count, and thread ID.
- Data gaps for unknown model rates, missing thread metadata, or sessions without usable token records.
- Bottom methodology executive summary explaining how local Codex metadata and JSONL logs are queried and how token costs and full-year projections are calculated.
- The exact footer at the bottom: `This report generated using [chase-sidekick](https://github.com/chase-seibert/chase-sidekick) and the [codex-cost-report skill](https://github.com/chase-seibert/chase-sidekick/tree/main/.agents/skills/codex-cost-report).`.

## Pricing Notes

- The script uses actual recorded USD when local Codex token-count events expose dollar fields. If no actual USD fields are available, it uses standard short-context API rates for API-equivalent USD estimates. If the user explicitly asks for long-context, batch, flex, priority, or regional processing estimates, update the rate table in `scripts/generate_report.py` for that run and call out the assumption in `## Notes`.
- The Codex rate card is credit-based. Include credit estimates when the model has a published Codex credit rate.
- If a model has no direct USD rate in the script, keep its tokens in usage totals, list it under `Data Gaps`, and exclude it from estimate-backed USD totals for sessions without actual recorded USD.
- Reasoning tokens are shown separately but are not added again because they are already included in output tokens.
- Full-year projected cost is extrapolated from observed average daily USD across the covered period, multiplied by 365.
- Project is derived from the thread git origin repo name when present, otherwise from the thread current working directory name.
- For project cost state, write `COSTS.md` at the project's git root when available, otherwise at the canonical project directory. Skip Codex cache/worktree/temp directories so they do not receive stray tracker files.
- Only completed months belong in `COSTS.md`; exclude the current partial month. The monthly totals table must be newest month first and the total must appear above the monthly list.
- Coding vs cowork is a best-effort local-write heuristic. Classify a session as coding when its log shows local non-`memory/` file writes; otherwise classify it as cowork.

## Validation

After editing this skill or generating a report, run:

```bash
python3 /Users/cseibert/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/codex-cost-report
python3 .agents/skills/codex-cost-report/scripts/generate_report.py
tail -n 1 memory/codex-cost-report-YYYY-MM-DD.qmd
test -f memory/codex-cost-report-YYYY-MM-DD.html
test -f COSTS.md
rg -n "codex-cost-report:start|## Total|## Monthly Totals" COSTS.md
rg -n "auth.json|access_token|refresh_token|OPENAI_API_KEY|API key|id_token" memory/codex-cost-report-*.qmd memory/codex-cost-report-*.html
git diff --check
```

The `tail` output must be exactly:

```text
This report generated using [chase-sidekick](https://github.com/chase-seibert/chase-sidekick) and the [codex-cost-report skill](https://github.com/chase-seibert/chase-sidekick/tree/main/.agents/skills/codex-cost-report).
```
