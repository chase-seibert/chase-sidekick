# Slack Skill

Command-line interface for Slack operations.

## Configuration

Configuration is automatically loaded from `.env` file in project root.

Create or update your `.env` file:
```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
```

### Getting a Bot Token

1. Go to https://api.slack.com/apps and create a new app (from scratch)
2. Navigate to **OAuth & Permissions**
3. Add these **Bot Token Scopes**:
   - `channels:history` — Read messages in public channels
   - `channels:read` — List public channels and their info
   - `groups:history` — Read messages in private channels the bot is in
   - `groups:read` — List private channels the bot is in
   - `users:read` — Look up user names and profiles
   - `users:read.email` — Look up user email addresses
   - `chat:write` — Send messages (optional, only for send-message)
4. Install the app to your workspace
5. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

**Note**: The bot must be invited to private channels before it can read them.

## Commands

All commands use the module form (`python -m sidekick.clients.slack`).

### List Channels

```bash
python -m sidekick.clients.slack list-channels
```

Lists all channels the bot has access to:
```
Found 15 channels:
#general (42 members) [Team announcements]
#engineering (28 members) [Engineering discussion]
#random (35 members)
```

### Get Channel Info

```bash
python -m sidekick.clients.slack channel-info C0EXAMPLE1
```

Shows detailed channel information:
```
#engineering
  Members: 28
  Topic: Engineering discussion
  Purpose: For engineering team conversations
  ID: C0EXAMPLE1
```

### Get Channel History

```bash
python -m sidekick.clients.slack history C0EXAMPLE1
python -m sidekick.clients.slack history C0EXAMPLE1 --limit 50
```

Shows recent messages with user names resolved:
```
Last 100 messages:
[2026-03-01 10:30] Alice Smith: Good morning team!
[2026-03-01 10:32] Bob Jones: Morning! Ready for standup?
[2026-03-01 10:35] Alice Smith: Let's do it
```

### Get Thread Replies

```bash
python -m sidekick.clients.slack thread C0EXAMPLE1 1709312200.123456
```

Shows all replies in a thread:
```
Thread (3 messages):
[2026-03-01 10:30] Alice Smith: Should we update the API?
[2026-03-01 10:32] Bob Jones: Yes, let's do v2
[2026-03-01 10:35] Charlie Brown: +1
```

### List Users

```bash
python -m sidekick.clients.slack users
```

Lists active, non-bot users:
```
Found 50 users:
@alice (Alice Smith) [alice@example.com]
@bob (Bob Jones) [bob@example.com]
```

### Get User Info

```bash
python -m sidekick.clients.slack user-info U0EXAMPLE1
```

Shows detailed user information:
```
@alice
  Name: Alice Smith
  Title: Senior Engineer
  Email: alice@example.com
  ID: U0EXAMPLE1
```

### Send Message

```bash
python -m sidekick.clients.slack send-message C0EXAMPLE1 "Hello team!"
```

Sends a message to a channel. **Note**: Always confirm with the user before sending messages.

## Python Usage

```python
from sidekick.clients.slack import SlackClient

client = SlackClient(bot_token="xoxb-your-token")

# List channels
channels = client.list_channels()
for ch in channels:
    print(f"#{ch['name']} ({ch['num_members']} members)")

# Get channel history
messages = client.get_channel_history("C0EXAMPLE1", limit=50)
for msg in messages:
    print(f"{msg['user']}: {msg['text']}")

# Get thread replies
replies = client.get_thread_replies("C0EXAMPLE1", "1709312200.123456")

# Get user info
user = client.get_user_info("U0EXAMPLE1")
print(user["real_name"])

# Send a message
client.send_message("C0EXAMPLE1", "Hello from Sidekick!")
```
