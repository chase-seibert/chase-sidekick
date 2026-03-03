---
name: slack
description: Search channels, read messages, and interact with Slack
argument-hint: <operation> [args]
allowed-tools: Bash, Read
---

# Slack Skill

Command-line interface for Slack operations.

When invoked, use the Slack client to handle the request: $ARGUMENTS

## Available Commands

### List Channels
```bash
python -m sidekick.clients.slack list-channels
```

### List My Channels
```bash
python -m sidekick.clients.slack my-channels
```

### Get Channel Info
```bash
python -m sidekick.clients.slack channel-info CHANNEL_ID
```

### Get Channel History
```bash
python -m sidekick.clients.slack history CHANNEL_ID [--limit N]
```

### Get Thread Replies
```bash
python -m sidekick.clients.slack thread CHANNEL_ID THREAD_TS
```

### Search Messages
```bash
python -m sidekick.clients.slack search "query string" [--count N]
```

### Saved Items (Later)
```bash
python -m sidekick.clients.slack saved-items [--count N]
```

### List Users
```bash
python -m sidekick.clients.slack users
```

### Get User Info
```bash
python -m sidekick.clients.slack user-info USER_ID
```

### Send Message
```bash
python -m sidekick.clients.slack send-message CHANNEL_ID "message text"
```

## Example Usage

When the user asks to:
- "Show me the recent messages in #general" - Use history with the channel ID
- "What channels are available?" - Use list-channels or my-channels
- "What channels am I in?" - Use my-channels
- "Who posted in this thread?" - Use thread with channel ID and thread timestamp
- "Find messages about X" - Use search with a query string
- "Show my saved items" - Use saved-items
- "Send a message to the team channel" - Use send-message (confirm with user first)

## Search Query Syntax

The search command supports Slack search operators:
- `is:saved` - Messages saved for later
- `in:#channel` - Messages in a specific channel
- `from:@user` - Messages from a specific user
- `before:2026-03-01` / `after:2026-02-01` - Date filters
- `has:link` / `has:reaction` - Messages with links or reactions

For full documentation, see the README in this folder.
