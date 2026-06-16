---
name: dx
description: Run DX Data Studio SQL queries, saved query datafeeds, and CSV downloads
argument-hint: <operation> [args]
allowed-tools: Bash, Read
---

# DX Skill

Use the local DX client for Data Studio query execution, query-run polling, saved query datafeeds, and result downloads: $ARGUMENTS

## Configuration

Required in `.env`:

```bash
DX_API_TOKEN=...
```

Optional defaults for DX Cloud:

```bash
DX_WEB_BASE_URL=https://app.getdx.com
DX_API_BASE_URL=https://api.getdx.com
```

For dedicated or managed DX deployments, set the deployment-specific web and API base URLs.

## Commands

### Check Auth

```bash
python3 -m sidekick.clients.dx whoami
```

Use this first when diagnosing token or scope issues.

### Run SQL

```bash
python3 -m sidekick.clients.dx query "SELECT id, name FROM github_repositories LIMIT 10"
```

The client submits the query, polls until completion, and prints a compact table. Add `--json` for the raw JSON response.

### Run SQL From A File

```bash
python3 -m sidekick.clients.dx query-file path/to/query.sql
```

### Template Variables

Use variables without the leading `$`:

```bash
python3 -m sidekick.clients.dx query \
  "SELECT * FROM github_repositories WHERE id IN ($repo_ids)" \
  --var repo_ids=1,2,3
```

For complex values:

```bash
python3 -m sidekick.clients.dx query-file query.sql \
  --variables-json '{"repo_ids":["1","2","3"]}'
```

### Download Full Results

JSON results are limited by DX. Use CSV downloads for the full result set:

```bash
python3 -m sidekick.clients.dx query \
  "SELECT * FROM github_pulls" \
  --csv memory/dx-github-pulls.csv
```

For an existing query run:

```bash
python3 -m sidekick.clients.dx results QUERY_RUN_ID --csv memory/dx-results.csv
```

### Query Run Status And Results

Submit without waiting:

```bash
python3 -m sidekick.clients.dx execute "SELECT 1"
```

Check or wait for status:

```bash
python3 -m sidekick.clients.dx status QUERY_RUN_ID
python3 -m sidekick.clients.dx status QUERY_RUN_ID --wait
```

Fetch JSON rows for a completed run:

```bash
python3 -m sidekick.clients.dx results QUERY_RUN_ID
```

### Saved Query Datafeeds

Use a saved query datafeed token:

```bash
python3 -m sidekick.clients.dx datafeed FEED_TOKEN
python3 -m sidekick.clients.dx datafeed FEED_TOKEN --var team_id=123 --columns date,count
```

Save returned datafeed rows as CSV:

```bash
python3 -m sidekick.clients.dx datafeed FEED_TOKEN --csv memory/dx-datafeed.csv
```

## DX AI Prompt-To-SQL

DX Data Studio AI can generate SQL from prompts in the DX product UI. As of the current public docs and DX CLI package, there is not a documented Web API or CLI command for submitting a natural-language prompt to the platform AI and receiving generated SQL.

When a user asks for platform AI query generation:

1. Use the DX UI at `DX_WEB_BASE_URL` and Data Studio AI when browser access is appropriate.
2. Paste the generated SQL into `python3 -m sidekick.clients.dx query ...` or save it to a `.sql` file and use `query-file`.
3. Do not call undocumented internal app endpoints unless the user explicitly asks for that brittle workflow.

The local command `python3 -m sidekick.clients.dx ai "prompt"` explains this limitation and exits without making an API request.

## Output

By default, commands print compact tables for humans. Add `--json` for raw API payloads when another tool needs to parse the response. Use `--csv path/to/file.csv` when the result set may exceed JSON row limits.
