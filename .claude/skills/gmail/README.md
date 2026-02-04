# Gmail Skill

Search and manage Gmail messages using the command line.

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
2. Create a new project (or select existing)
3. Enable Gmail API:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"
4. Create OAuth2 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Desktop app"
   - Name it (e.g., "Chase Sidekick")
   - Download the credentials JSON

#### 2. Get Refresh Token

You need to obtain a refresh token. Use this Python script:

```python
from urllib.parse import urlencode
import webbrowser

client_id = "YOUR_CLIENT_ID"
redirect_uri = "http://localhost"
scope = "https://www.googleapis.com/auth/gmail.modify"

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
GMAIL_CLIENT_ID=your_client_id_here
GMAIL_CLIENT_SECRET=your_client_secret_here
GMAIL_REFRESH_TOKEN=your_refresh_token_here
```

## Commands

### Search Messages

Search for messages using Gmail search syntax:

```bash
# Search from specific sender
python -m sidekick.clients.gmail search "from:someone@example.com"

# Search by subject
python -m sidekick.clients.gmail search "subject:meeting"

# Search unread messages
python -m sidekick.clients.gmail search "is:unread"

# Search with date filter
python -m sidekick.clients.gmail search "after:2024/01/01"

# Combine filters
python -m sidekick.clients.gmail search "from:boss@company.com is:unread" 5

# Search in specific folder
python -m sidekick.clients.gmail search "in:inbox is:starred"
```

**Output format** (one line per message):
```
18f2c4e5a1b2c3d4: John Doe <john@example.com> - Weekly Meeting
  Let's schedule our weekly sync for next Tuesday...
```

### Get Full Message

Get complete details of a specific message:

```bash
python -m sidekick.clients.gmail get MESSAGE_ID
```

**Output includes:**
- Message and thread IDs
- From, To, Subject, Date headers
- Full message body (plain text)

Example:
```
Message ID: 18f2c4e5a1b2c3d4
Thread ID: 18f2c4e5a1b2c3d4
From: John Doe <john@example.com>
To: you@example.com
Subject: Weekly Meeting
Date: Mon, 15 Jan 2024 10:30:00 -0800

Body:
--------------------------------------------------------------------------------
Let's schedule our weekly sync for next Tuesday at 2pm.

Best,
John
--------------------------------------------------------------------------------
```

### Create Draft Email

Create a draft email (does not send):

```bash
python -m sidekick.clients.gmail create-draft "recipient@example.com" "Subject" "Body text"
```

Example:
```bash
python -m sidekick.clients.gmail create-draft \
  "team@example.com" \
  "Sprint Planning" \
  "Hi team, let's meet tomorrow to plan the next sprint."
```

**Output:**
```
Draft created successfully!
Draft ID: r-1234567890
Message ID: 18f2c4e5a1b2c3d4
```

## Python Usage

```python
from sidekick.clients.gmail import GmailClient

client = GmailClient(
    client_id="your_client_id",
    client_secret="your_client_secret",
    refresh_token="your_refresh_token"
)

# Search messages
messages = client.search_messages("from:boss@example.com", max_results=5)
for msg in messages:
    headers = client.get_message_headers(msg)
    print(f"From: {headers['from']}")
    print(f"Subject: {headers['subject']}")

# Get full message
message = client.get_message("MESSAGE_ID")
body = client.get_message_body(message)
print(body)

# Create draft
draft = client.create_draft(
    to="recipient@example.com",
    subject="Hello",
    body="This is a draft email",
    cc="cc@example.com"  # optional
)
print(f"Draft ID: {draft['id']}")
```

## Gmail Search Syntax

Common search operators:

- `from:sender@example.com` - Messages from specific sender
- `to:recipient@example.com` - Messages to specific recipient
- `subject:keyword` - Messages with keyword in subject
- `is:unread` - Unread messages
- `is:starred` - Starred messages
- `is:important` - Important messages
- `has:attachment` - Messages with attachments
- `after:2024/01/01` - Messages after date
- `before:2024/12/31` - Messages before date
- `newer_than:7d` - Messages from last 7 days
- `older_than:30d` - Messages older than 30 days
- `in:inbox` - Messages in inbox
- `in:sent` - Sent messages
- `label:work` - Messages with label "work"

Combine with AND (space) or OR:
- `from:john subject:meeting` - Both conditions
- `from:john OR from:jane` - Either condition

## Limitations

- Draft creation does NOT send emails (by design)
- Plain text emails only (no HTML formatting)
- No attachment support in current version
- Requires OAuth2 setup (one-time process)

## Troubleshooting

**"Failed to refresh access token"**
- Verify your client_id and client_secret are correct
- Ensure refresh_token is valid (may need to regenerate)
- Check that Gmail API is enabled in Google Cloud Console

**"403 Forbidden"**
- Ensure Gmail API is enabled for your project
- Check OAuth2 scopes include `gmail.modify`

**"401 Unauthorized"**
- Your refresh token may have expired or been revoked
- Regenerate the refresh token using the setup script
