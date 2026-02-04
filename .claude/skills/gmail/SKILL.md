---
name: gmail
description: Search and manage Gmail messages
argument-hint: <search-query>
allowed-tools: Bash, Read
---

# Gmail Skill

Search and manage Gmail messages using the command line.

When invoked, use the Gmail client to handle the request: $ARGUMENTS

## Available Commands

### Search Messages
```bash
python -m sidekick.clients.gmail search "query" [max_results]
```

### Get Message Details
```bash
python -m sidekick.clients.gmail get MESSAGE_ID
```

### Create Draft Email
```bash
python -m sidekick.clients.gmail create-draft "to@example.com" "Subject" "Body"
```

## Gmail Search Syntax

Common search operators:
- `from:sender@example.com` - Messages from specific sender
- `to:recipient@example.com` - Messages to specific recipient
- `subject:keyword` - Messages with keyword in subject
- `is:unread` - Unread messages
- `is:starred` - Starred messages
- `has:attachment` - Messages with attachments
- `after:2024/01/01` - Messages after date
- `before:2024/12/31` - Messages before date
- `newer_than:7d` - Messages from last 7 days
- `older_than:30d` - Messages older than 30 days
- `in:inbox` - Messages in inbox
- `in:sent` - Sent messages

Combine with AND (space) or OR:
- `from:john subject:meeting` - Both conditions
- `from:john OR from:jane` - Either condition

## Example Usage

When the user asks to:
- "Search for emails from my manager" - Use the Gmail client with appropriate search query
- "Find recent emails about project X" - Search with subject and date filters
- "Show unread emails from last week" - Combine is:unread with newer_than:7d

For full documentation, see the detailed Gmail skill documentation in this folder.
