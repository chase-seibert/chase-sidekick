# Kudos Skill

Generate formatted kudos for team members from recent 1:1 and meeting notes with proper Slack mentions.

## Overview

The Kudos skill helps engineering managers recognize team accomplishments by automatically extracting kudos from meeting notes and formatting them for sharing in Slack or other channels.

## Features

- 📝 Extract kudos from Confluence and Dropbox Paper documents
- 👥 Slack-ready mention formatting with real `<@U...>` user IDs
- 🔗 Include source references for each kudos
- 📅 Filter by time period (default: last 7 days)
- 🎯 Categorize kudos by type (launches, promotions, etc.)
- ✨ Format for easy copy-paste to Slack

## Prerequisites

### Required Files

1. **@AGENTS.override.md** - Must contain links to your 1:1 and meeting docs:
   ```markdown
   ## 1:1 Docs
   - [Alice](https://company.atlassian.net/wiki/spaces/...)
   - [Bob](https://example.com/docs/...)

   ## Recurring Meetings
   - [Team Sync](https://example.com/docs/...)
   ```

2. **memory/people.json** - Employee data for identifying people:
   ```json
   {
     "dropboxers": [
       {
         "email": "alice@example.com",
         "ldap": "alice",
         "full_name": "Alice Smith",
         "slack_user_id": "U123ABC"
       }
     ]
   }
   ```

### Environment Setup

Configure `.env` with:
```bash
# Confluence
ATLASSIAN_EMAIL=you@example.com
ATLASSIAN_API_TOKEN=your-token
ATLASSIAN_BASE_URL=https://company.atlassian.net

# Dropbox
DROPBOX_ACCESS_TOKEN=your-token
```

## Usage

### Basic Usage

```bash
/kudos
```

Generates kudos from the past 7 days.

### Custom Time Period

```bash
/kudos 2
```

Generates kudos from the past 2 weeks.

## How It Works

### 1. Document Discovery

The skill reads `@AGENTS.override.md` to find all your 1:1 and meeting document links.

### 2. Content Fetching

For each document:
- **Confluence pages**: Uses `confluence get-content-from-link`
- **Dropbox Paper docs**: Uses `dropbox get-paper-contents-from-link`

Fetched content is saved to a temporary `$TMP_DIR` for analysis and cleaned up after the final kudos are generated.

### 3. Kudos Extraction

Scans documents for recent kudos indicators:
- Performance ratings (4+, 5)
- Promotions and level changes
- Project launches and completions
- "Great job", "crushed it", "excellent work" phrases
- Specific accomplishments with impact

Only extracts from sections with recent date headers.

### 4. Slack Formatting

For each kudos:
1. Identifies people mentioned
2. Resolves each person to a Slack user ID
3. Formats real Slack mentions as raw `<@U...>` tokens:
   - Correct: `<@U123ABC>`
   - Incorrect: `` `<@U123ABC>` `` because inline code prevents Slack from rendering the mention
   - Incorrect: `@alice` because email-prefix usernames are not reliable notifying mentions

Prefer existing Slack mentions in source context or Slack user/profile lookup by name or email. If no Slack ID can be resolved, use plain non-notifying text such as `alice@example.com` or `Alice Smith`; do not imply that it will notify the person.

### 5. Output Generation

Creates formatted kudos with:
- Clear description
- Context and impact
- Slack mentions
- Source reference links

## Output Format

```markdown
## Kudos - Week of Feb 3, 2026

### [Project/Category Name]

[Description of accomplishment with context about why it matters]

[Details about approach, impact, or what made it special]

**People:** <@U123ABC>, <@U456DEF>, <@U789GHI>

[[ref]](source-document-url)

---

### [Another Category]

[Another kudos item...]
```

When sending the report to Slack, do not wrap the generated report in a code block, and do not wrap individual mention tokens in backticks. If the message is split into multiple Slack messages, preserve raw `<@U...>` tokens in every chunk.

## Tips

### Finding Kudos

Look for phrases like:
- "great job on"
- "crushed it"
- "excellent work"
- "went above and beyond"
- "really impressed"
- "promotion"
- "4+ rating", "5 rating"

### Writing Good Kudos

1. **Be Specific**: What exactly was accomplished?
2. **Show Impact**: Why does it matter?
3. **Add Context**: What made it special or challenging?
4. **Be Genuine**: Only call out real accomplishments

### Slack Mention Tips

- Real notifying mentions use Slack user IDs in the form `<@U123ABC>`
- Bare `@alice` text may not notify and should not be used for Slack-ready kudos
- Inline code such as `` `<@U123ABC>` `` renders visibly and does not notify
- If a Slack ID cannot be resolved, use plain text and treat it as non-notifying

## Troubleshooting

### "No kudos found"

- Check that documents have content from the target time period
- Verify date headers are in recognizable formats
- Try increasing the time window

### "Document fetch failed"

- Verify credentials in `.env`
- Check that URLs in `@AGENTS.override.md` are correct
- Ensure you have access to the documents

### "Wrong Slack mention"

- Verify the person's Slack user ID through Slack user/profile lookup or trusted local data
- Check that the final Slack-ready text contains raw `<@U...>` tokens
- Remove any backticks, code fences, escaped angle brackets, or quotes around mention tokens

## File Structure

```
.claude/skills/kudos/
├── SKILL.md          # Skill definition and instructions
└── README.md         # This file

$TMPDIR/kudos.*/      # Temporary during execution
├── doc1.html         # Fetched Confluence content
├── doc2.md           # Fetched Paper content
└── ...
```

## Advanced Usage

### Custom Categories

You can organize kudos by:
- Project/Initiative (e.g., "SM26 Launch", "Q4 OKRs")
- Type (e.g., "Technical Excellence", "Leadership")
- Team (e.g., "Team Formation", "Team Expansion")

### Filtering

To focus on specific types of kudos:
1. Fetch all documents as usual
2. Manually filter the output
3. Or modify the extraction criteria

### Bulk Recognition

For team-wide recognition:
1. Run `/kudos` for longer period (e.g., `/kudos 12` for a quarter)
2. Group related accomplishments
3. Combine into team update or retrospective

## Best Practices

1. **Run Regularly**: Weekly or bi-weekly to catch all kudos
2. **Review Output**: Always review before sharing publicly
3. **Add Context**: Enhance AI-generated kudos with your insights
4. **Be Timely**: Share kudos soon after accomplishments
5. **Be Inclusive**: Make sure everyone gets recognized

## Related

- See the `weekly-report` skill for broader note summaries
- See [confluence skill](.claude/skills/confluence/SKILL.md) for Confluence operations
- See [dropbox skill](.claude/skills/dropbox/SKILL.md) for Paper operations
