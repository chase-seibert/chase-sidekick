# Kudos Skill

Generate formatted kudos for team members from recent 1:1 and meeting notes with proper Slack mentions.

## Overview

The Kudos skill helps engineering managers recognize team accomplishments by automatically extracting kudos from meeting notes and formatting them for sharing in Slack or other channels.

## Features

- 📝 Extract kudos from Confluence and Dropbox Paper documents
- 👥 Automatic Slack username formatting from email addresses
- 🔗 Include source references for each kudos
- 📅 Filter by time period (default: last 7 days)
- 🎯 Categorize kudos by type (launches, promotions, etc.)
- ✨ Format for easy copy-paste to Slack

## Prerequisites

### Required Files

1. **CLAUDE.local.md** - Must contain links to your 1:1 and meeting docs:
   ```markdown
   ## 1:1 Docs
   - [Alice](https://company.atlassian.net/wiki/spaces/...)
   - [Bob](https://example.com/docs/...)

   ## Recurring Meetings
   - [Team Sync](https://example.com/docs/...)
   ```

2. **memory/people.json** - Employee data for email to Slack mapping:
   ```json
   {
     "dropboxers": [
       {
         "email": "alice@example.com",
         "ldap": "alice",
         "full_name": "Alice Smith"
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

The skill reads `CLAUDE.local.md` to find all your 1:1 and meeting document links.

### 2. Content Fetching

For each document:
- **Confluence pages**: Uses `confluence get-content-from-link`
- **Dropbox Paper docs**: Uses `dropbox get-paper-contents-from-link`

Content is saved to `memory/kudos/` for analysis.

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
2. Looks up their email from context
3. Converts email to Slack username:
   - `alice@example.com` → `@alice`
   - `bob.smith@example.com` → `@bob.smith`

### 5. Output Generation

Creates formatted kudos with:
- Clear description
- Context and impact
- Slack mentions
- Source reference links

## Output Format

```markdown
## Kudos - Week of Feb 3, 2026

### 🎉 [Project/Category Name]

[Description of accomplishment with context about why it matters]

[Details about approach, impact, or what made it special]

**People:** @username1, @username2, @username3

[[ref]](source-document-url)

---

### 🌟 [Another Category]

[Another kudos item...]
```

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

### Slack Username Tips

- Username is always the email prefix before @example.com
- Keep dots, hyphens, underscores from email
- Case doesn't matter in Slack (@Alice = @alice)

## Troubleshooting

### "No kudos found"

- Check that documents have content from the target time period
- Verify date headers are in recognizable formats
- Try increasing the time window

### "Document fetch failed"

- Verify credentials in `.env`
- Check that URLs in `CLAUDE.local.md` are correct
- Ensure you have access to the documents

### "Wrong Slack username"

- Verify the person's email in your company's directory
- Username = email prefix before @example.com
- Check `memory/people.json` has current data

## File Structure

```
.claude/skills/kudos/
├── SKILL.md          # Skill definition and instructions
└── README.md         # This file

memory/kudos/         # Generated during execution
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
