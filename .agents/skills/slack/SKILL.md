---
name: slack
description: Read recent messages from Slack channels using Dash MCP
argument-hint: (documentation only)
invocable: false
---

# Read Slack Channels

This skill documents how to read recent messages from Slack channels using Dash MCP tools.

## Overview

Dash MCP provides two Slack tools with different use cases:

### `slack_get_conversation_context` (RECOMMENDED for reading channels)
- **Use when**: Reading recent messages from a specific channel
- **Advantages**: Can retrieve up to **300 messages** in a single call
- **No pagination needed**: Simple, efficient workflow

### `slack_search_messages` (for searching with queries)
- **Use when**: Searching across channels with specific query terms
- **Limitation**: Returns max 20 messages per page, requires pagination for more
- **Best for**: Finding messages about specific topics, not just reading recent activity

## Primary Use Case: Reading Recent Messages from a Channel

### Option A: Get Last N Messages (Most Recent)

To get the most recent 100+ messages from a channel like `#my-channel`:

### Step 1: Get Slack Connection ID

```bash
dash_get_sources
```

Filter response for `connector_id="slack"` and extract the `source_id` (format: `slack-<id>`).

### Step 2: Get a Recent Message from the Channel

```json
dash_invoke_search_action(
  action_id="slack_search_messages",
  params={
    "query": "in:#my-channel",
    "max_results": 1,
    "sort": "timestamp",
    "sort_direction": "desc"
  }
)
```

Extract the `message_id` from the response (format: `"C123456-1234567890.123456"`).

### Step 3: Get Message Context

```json
dash_invoke_search_action(
  action_id="slack_get_conversation_context",
  params={
    "message_id": "<message_id_from_step_2>",
    "context_lines": 100
  }
)
```

**Notes**:
- `context_lines` default: 100, max: 300
- Returns messages before and after the specified message
- Since we used the most recent message, this effectively gives us the last ~100-300 messages


### Option B: Get Messages from Last X Days

To get messages from the last X days (e.g., last 7 days, last 10 days) from a specific channel:

**Step 1: Calculate the Date**

Use bash to calculate the date X days ago.

**Step 2: Search with Date Filter**

Search for messages after that date. Since this may return more than 20 messages, use pagination.

**Step 3: Alternative - Combine with Context Retrieval**

For better message quality (full text), combine search + context.


**When to Use:**
- **Option A** (most recent N messages): When you want a fixed number of recent messages regardless of time
- **Option B** (last X days): When you need all messages within a specific time window (e.g., weekly reports)


## Key Limitations

1. **`slack_search_messages` hard limit**: 20 messages per page (cannot be increased)
2. **`slack_get_conversation_context` limit**: 300 messages max per call
3. **Rate limits**: Be mindful of API rate limits when making multiple calls

## Formatting Messages as Markdown

After retrieving messages, format them as a unified Markdown document for easy reading.

```markdown
# Messages from #channel-name

**Date Range**: March 12-19, 2026
**Total Messages**: 42

---

## March 19, 2026

### 16:47 - Person 1
Message here

[View message](link-to-slack)

---

### 15:22 - Person 1
Message here

[View message](link-to-slack)

---
```

**Formatting Guidelines:**
- Group messages by date with H2 headers (`## Date`)
- Each message gets H3 header with time and sender name (`### HH:MM - Name`)
- Include message text (truncate if very long)
- Add permalink to original message
- Use horizontal rules (`---`) to separate messages
- Include summary at top (date range, message count)

## Best Practices

- **For reading most recent N messages**: Use `slack_get_conversation_context` (simpler, more efficient, up to 300 messages)
- **For reading last X days of messages**: Use `slack_search_messages` with `after:YYYY-MM-DD` date filter and pagination
- **For keyword search queries**: Use `slack_search_messages` with search terms and pagination
- **Cache results**: Save fetched messages to avoid redundant API calls
- **Error handling**: Check for `next_cursor` to detect if more pages exist
- **Date calculations**: Use bash `date` command or Python `datetime` for calculating date ranges
- **Format as Markdown**: Convert message results to readable Markdown format with dates, times, senders, and permalinks
