---
name: databricks
description: Run Databricks SQL queries, saved reports, and AI/BI Genie prompts
argument-hint: <operation> [args]
allowed-tools: Bash, Read
---

# Databricks Skill

Use the local Databricks client for Databricks SQL and AI/BI Genie work: $ARGUMENTS

## Configuration

Required in `.env`:

```bash
DATABRICKS_HOST=https://dropbox-prod.cloud.databricks.com
DATABRICKS_TOKEN=...
```

Optional defaults:

```bash
DATABRICKS_WAREHOUSE_ID=...
DATABRICKS_CATALOG=...
DATABRICKS_SCHEMA=...
DATABRICKS_GENIE_SPACE_ID=...
```

## Commands

### List SQL Warehouses

```bash
python3 -m sidekick.clients.databricks warehouses
```

Use this first when `DATABRICKS_WAREHOUSE_ID` is not configured.

### Run SQL

```bash
python3 -m sidekick.clients.databricks query "SELECT 1" --warehouse-id WAREHOUSE_ID
```

With named parameters:

```bash
python3 -m sidekick.clients.databricks query \
  "SELECT * FROM catalog.schema.table WHERE id = :id" \
  --warehouse-id WAREHOUSE_ID \
  --param id:STRING=abc123
```

### Run SQL From A File

```bash
python3 -m sidekick.clients.databricks query-file path/to/query.sql --warehouse-id WAREHOUSE_ID
```

### List Saved Reports

Saved Databricks SQL queries are treated as reports by this client.

```bash
python3 -m sidekick.clients.databricks list-reports
python3 -m sidekick.clients.databricks list-reports "weekly active"
```

### Get Or Run A Saved Report

```bash
python3 -m sidekick.clients.databricks get-report "Report Name"
python3 -m sidekick.clients.databricks run-report "Report Name"
```

Saved reports can be addressed by query ID, exact display name, or a unique name substring.

### Fetch Dashboard Dataset Results

For AI/BI dashboards, the client fetches the dashboard definition, extracts SQL datasets from `serialized_dashboard`, and executes those datasets on the dashboard warehouse.

```bash
python3 -m sidekick.clients.databricks dashboard-results "https://workspace/dashboardsv3/DASHBOARD_ID/published"
```

Run one dataset only:

```bash
python3 -m sidekick.clients.databricks dashboard-results DASHBOARD_ID --dataset DATASET_NAME
```

Use `--row-limit N` to cap fetched rows per dataset. This re-executes dashboard dataset SQL with the configured Databricks token, so dashboards published with embedded credentials can still fail if the token lacks direct table or schema permissions.

### List Genie Spaces

```bash
python3 -m sidekick.clients.databricks genie-spaces
```

Use this first when `DATABRICKS_GENIE_SPACE_ID` is not configured.

### Ask Genie

```bash
python3 -m sidekick.clients.databricks ask "How many active teams did we have last week?" --space-id SPACE_ID
```

The `ask` command starts or continues a Genie conversation, waits for completion, prints generated SQL when Genie returns it, and fetches query attachment results.

Continue a conversation:

```bash
python3 -m sidekick.clients.databricks ask \
  "Break that down by team" \
  --space-id SPACE_ID \
  --conversation-id CONVERSATION_ID
```

### Fetch A Genie Query Attachment Result

```bash
python3 -m sidekick.clients.databricks genie-result SPACE_ID CONVERSATION_ID MESSAGE_ID ATTACHMENT_ID
```

Use `--execute` to execute or re-execute an attachment query when the cached result has expired.

## Output

By default, commands print compact tables for humans. Add `--json` for raw API payloads when another tool needs to parse the response.
