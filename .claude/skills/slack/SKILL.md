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
- "What channels are available?" - Use list-channels
- "Who posted in this thread?" - Use thread with channel ID and thread timestamp
- "Send a message to the team channel" - Use send-message (confirm with user first)

For full documentation, see the README in this folder.
