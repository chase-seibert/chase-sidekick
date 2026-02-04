# Google Sheets Skill

Manage Google Sheets from the command line - download, upload, and replace sheets with CSV data.

## Setup

### Quick Setup (Recommended)

Use the provided helper script to set up Gmail, Google Calendar, and Google Sheets with one OAuth token:

```bash
python3 tools/get_google_refresh_token.py
```

This interactive script will guide you through the entire setup process and generate the credentials you need.

### Manual Setup (Alternative)

#### 1. Create OAuth2 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable required APIs:
   - Go to "APIs & Services" > "Library"
   - Search for and enable "Google Sheets API"
   - Search for and enable "Google Drive API" (required for listing spreadsheets)
4. Create OAuth2 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Desktop app"
   - Name it (e.g., "Chase Sidekick")
   - Download the credentials JSON

#### 2. Get Refresh Token

Use this Python script to obtain a refresh token:

```python
from urllib.parse import urlencode
import webbrowser

client_id = "YOUR_CLIENT_ID"
redirect_uri = "http://localhost"
scope = "https://www.googleapis.com/auth/spreadsheets"

auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
    "client_id": client_id,
    "redirect_uri": redirect_uri,
    "response_type": "code",
    "scope": scope,
    "access_type": "offline",
    "prompt": "consent"
})

print("Visit this URL:")
print(auth_url)
webbrowser.open(auth_url)

# After authorizing, copy the 'code' from the redirect URL
code = input("Enter the authorization code: ")

# Exchange code for tokens
import urllib.request
import json

token_url = "https://oauth2.googleapis.com/token"
data = urlencode({
    "client_id": client_id,
    "client_secret": "YOUR_CLIENT_SECRET",
    "code": code,
    "redirect_uri": redirect_uri,
    "grant_type": "authorization_code"
}).encode()

req = urllib.request.Request(token_url, data=data)
with urllib.request.urlopen(req) as response:
    tokens = json.loads(response.read().decode())
    print("\nRefresh token:")
    print(tokens["refresh_token"])
```

### 3. Configure .env

Add to your `.env` file:

```bash
GOOGLE_SHEETS_CLIENT_ID=your_client_id_here
GOOGLE_SHEETS_CLIENT_SECRET=your_client_secret_here
GOOGLE_SHEETS_REFRESH_TOKEN=your_refresh_token_here
```

## Commands

### List Spreadsheets

List all spreadsheets you have access to:

```bash
# List all spreadsheets (default: 100)
python -m sidekick.clients.gsheets list

# List first 20 spreadsheets
python -m sidekick.clients.gsheets list 20
```

**Output:**
```
Found 15 spreadsheets:

Q1 Sales Report
  ID: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
  URL: https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit
  Modified: 2024-01-15T10:30:00.000Z

Budget 2024
  ID: 1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
  URL: https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890/edit
  Modified: 2024-01-10T14:22:00.000Z
```

**Note:** This requires the Google Drive API to be enabled in addition to the Google Sheets API.

### Get Spreadsheet Info

Get metadata about a spreadsheet by ID or URL:

```bash
# Get by ID
python -m sidekick.clients.gsheets get "SPREADSHEET_ID"

# Get by URL
python -m sidekick.clients.gsheets get-url "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
```

**Output:**
```
Spreadsheet ID: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
Title: Q1 Sales Report
URL: https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms

Sheets:
  - Sheet1 (sheetId: 0)
  - Sales Data (sheetId: 123456)
```

### Download Sheet as CSV

Download a Google Sheet as a CSV file by ID or URL:

```bash
# Download by ID to stdout
python -m sidekick.clients.gsheets download "SPREADSHEET_ID"

# Download by URL to stdout
python -m sidekick.clients.gsheets download-url "https://docs.google.com/spreadsheets/d/1BxiMVs0.../edit"

# Download specific sheet to stdout
python -m sidekick.clients.gsheets download "SPREADSHEET_ID" "Sales Data"

# Download to file
python -m sidekick.clients.gsheets download "SPREADSHEET_ID" "Sheet1" output.csv

# Download by URL to file
python -m sidekick.clients.gsheets download-url "https://docs.google.com/spreadsheets/d/1BxiMVs0.../edit" "Sheet1" output.csv
```

**Spreadsheet ID:** Find it in the URL:
```
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
                                       ^^^^^^^^^^^^^^
```

**Output:**
```
Downloaded sheet 'Sheet1' to output.csv
```

### Upload CSV as New Spreadsheet

Create a new Google Sheet from a CSV file:

```bash
# Upload with default sheet name "Sheet1"
python -m sidekick.clients.gsheets upload data.csv "Q1 Sales Report"

# Upload with custom sheet name
python -m sidekick.clients.gsheets upload data.csv "Q1 Sales Report" "Sales Data"
```

**Output:**
```
Uploaded CSV to new spreadsheet!
Spreadsheet ID: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
Title: Q1 Sales Report
URL: https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
```

### Replace Sheet with CSV

Replace an existing sheet's contents with CSV data:

```bash
# Replace default sheet "Sheet1"
python -m sidekick.clients.gsheets replace "SPREADSHEET_ID" data.csv

# Replace specific sheet
python -m sidekick.clients.gsheets replace "SPREADSHEET_ID" data.csv "Sales Data"
```

**Output:**
```
Replaced sheet 'Sales Data' with CSV data
Updated 100 rows, 5 columns
```

### Get Spreadsheet Info

Get metadata about a spreadsheet:

```bash
python -m sidekick.clients.gsheets get "SPREADSHEET_ID"
```

**Output:**
```
Spreadsheet ID: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
Title: Q1 Sales Report
URL: https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms

Sheets:
  - Sheet1 (sheetId: 0)
  - Sales Data (sheetId: 123456)
```

## Python Usage

```python
from sidekick.clients.gsheets import GSheetsClient

client = GSheetsClient(
    client_id="your_client_id",
    client_secret="your_client_secret",
    refresh_token="your_refresh_token"
)

# List spreadsheets
spreadsheets = client.list_spreadsheets(max_results=20)
for sheet in spreadsheets:
    print(f"{sheet['name']}: {sheet['id']}")

# Get spreadsheet by URL
url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
spreadsheet = client.get_spreadsheet_by_url(url)
print(f"Title: {spreadsheet['properties']['title']}")

# Extract ID from URL
spreadsheet_id = GSheetsClient.extract_spreadsheet_id(url)
print(f"ID: {spreadsheet_id}")

# Download as CSV
csv_content = client.download_as_csv(
    spreadsheet_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
    sheet_name="Sheet1",
    output_path="output.csv"
)

# Upload CSV as new spreadsheet
spreadsheet = client.upload_csv(
    csv_path="data.csv",
    title="My Spreadsheet",
    sheet_name="Data"
)
print(f"Created: {spreadsheet['spreadsheetId']}")

# Replace sheet with CSV
result = client.replace_sheet_with_csv(
    spreadsheet_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
    csv_path="data.csv",
    sheet_name="Sheet1"
)

# Get raw values (2D list)
values = client.get_values(
    spreadsheet_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
    range_name="Sheet1!A1:D10"
)
for row in values:
    print(row)

# Update values
client.update_values(
    spreadsheet_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
    range_name="Sheet1!A1:B2",
    values=[
        ["Name", "Age"],
        ["Alice", "30"]
    ]
)
```

## Working with CSV Files

### Creating CSV Files

Use Python's csv module:

```python
import csv

data = [
    ["Name", "Email", "Department"],
    ["Alice", "alice@example.com", "Engineering"],
    ["Bob", "bob@example.com", "Sales"]
]

with open("data.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(data)
```

### Reading CSV Files

```python
import csv

with open("data.csv", "r", newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        print(row)
```

## Range Notation

Google Sheets uses A1 notation for ranges:

- `Sheet1` - Entire sheet
- `Sheet1!A1` - Single cell
- `Sheet1!A1:D10` - Range of cells
- `Sheet1!A:A` - Entire column A
- `Sheet1!1:1` - Entire row 1
- `Sheet1!A1:D` - Column A to D (all rows)

## Use Cases

### Export Dashboard Data

```bash
# Download weekly metrics
python -m sidekick.clients.gsheets download \
  "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms" \
  "Weekly Metrics" \
  weekly_metrics_$(date +%Y%m%d).csv
```

### Bulk Data Import

```bash
# Generate CSV from database
sqlite3 -header -csv database.db "SELECT * FROM users" > users.csv

# Upload to Google Sheets
python -m sidekick.clients.gsheets upload users.csv "User Export"
```

### Update Shared Spreadsheet

```bash
# Export data from system
./generate_report.sh > report.csv

# Update shared Google Sheet
python -m sidekick.clients.gsheets replace \
  "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms" \
  report.csv \
  "Latest Report"
```

### Backup Spreadsheets

```bash
# Backup all sheets in a spreadsheet
SPREADSHEET_ID="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
BACKUP_DIR="backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Get sheet names (requires jq)
python -m sidekick.clients.gsheets get "$SPREADSHEET_ID" | grep "  -" | cut -d' ' -f4 > /tmp/sheets.txt

# Download each sheet
while IFS= read -r sheet; do
    python -m sidekick.clients.gsheets download "$SPREADSHEET_ID" "$sheet" "$BACKUP_DIR/$sheet.csv"
done < /tmp/sheets.txt
```

## Limitations

- CSV format only (no formulas, formatting, or charts)
- Values are treated as raw text (not numbers or dates)
- Large sheets may take longer to download/upload
- No support for multiple simultaneous edits

## Troubleshooting

**"Failed to refresh access token"**
- Verify your client_id and client_secret are correct
- Ensure refresh_token is valid (may need to regenerate)
- Check that Sheets API is enabled in Google Cloud Console

**"Resource not found"**
- Verify the spreadsheet ID is correct
- Ensure you have access to the spreadsheet
- Sheet name is case-sensitive

**"403 Forbidden"**
- Ensure Google Sheets API is enabled for your project
- Check OAuth2 scopes include `spreadsheets` access
- Verify you have edit permissions on the spreadsheet

**CSV encoding issues**
- Ensure CSV files are UTF-8 encoded
- Use `encoding="utf-8"` when reading/writing CSV files in Python

## Finding Spreadsheet IDs

The spreadsheet ID is in the URL:

```
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit#gid=SHEET_ID
                                       ^^^^^^^^^^^^^^
                                       This is the ID you need
```

You can also share the spreadsheet and get the ID from the share URL.
