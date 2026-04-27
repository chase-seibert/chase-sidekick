---
name: gsheets
description: Manage Google Sheets - download, upload, and replace sheets with CSV data
argument-hint: <operation> [args]
allowed-tools: Bash, Read
---

# Google Sheets Skill

Manage Google Sheets from the command line - download, upload, and replace sheets with CSV data.

When invoked, use the Google Sheets client to handle the request: $ARGUMENTS

## Available Commands

### List Spreadsheets
```bash
python -m sidekick.clients.gsheets list [max_results]
```

### Get Spreadsheet Info
```bash
python -m sidekick.clients.gsheets get SPREADSHEET_ID
python -m sidekick.clients.gsheets get-url "https://docs.google.com/spreadsheets/d/..."
```

### Download Sheet as CSV
```bash
python -m sidekick.clients.gsheets download SPREADSHEET_ID [sheet_name] [output.csv]
python -m sidekick.clients.gsheets download-url "URL" [sheet_name] [output.csv]
```

### Upload CSV as New Spreadsheet
```bash
python -m sidekick.clients.gsheets upload data.csv "Spreadsheet Title" [sheet_name]
```

### Replace Sheet with CSV
```bash
python -m sidekick.clients.gsheets replace SPREADSHEET_ID data.csv [sheet_name]
```

## Finding Spreadsheet IDs

The spreadsheet ID is in the URL:
```
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
                                       ^^^^^^^^^^^^^^
```

## Example Usage

When the user asks to:
- "Download this Google Sheet as CSV" - Use download or download-url
- "Upload this CSV to a new Google Sheet" - Use upload command
- "Update this Google Sheet with new data" - Use replace command
- "List my Google Sheets" - Use list command

For full documentation, see the detailed Google Sheets skill documentation in this folder.
