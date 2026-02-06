# Transcript Skill

Save conversation transcripts as structured markdown files in the `memory/prompts/` folder.

## Purpose

The transcript skill helps you preserve important conversations with Claude Code as readable markdown documents. This is useful for:

- Documenting complex multi-step workflows you created
- Saving examples of effective prompts and approaches
- Building a personal library of reusable patterns
- Sharing workflows with teammates

## Usage

### Basic Usage

To save the current conversation:

```
/transcript
```

Claude will analyze the conversation, generate an appropriate filename based on the topic, and save the transcript to `memory/prompts/`.

### Custom Filename

To specify your own filename:

```
/transcript my-custom-filename
```

This saves the transcript as `memory/prompts/my-custom-filename.md`.

## Output Format

Transcripts are saved in a structured format:

```markdown
# Conversation Transcript: [Topic]

**Date:** YYYY-MM-DD

**Session Duration:** [Real-world time from first prompt to last response]

**Claude Thinking Time:** [Total time spent in thinking blocks]

**Cost:** $X.XX

---

## User Prompt 1

[Your exact prompt text]

---

## Assistant Response 1

[Summary of Claude's response]

[Tool invocations shown in brackets]
[Key results and outcomes]

---

## User Prompt 2

[Next prompt...]

---
```

### What Gets Saved

**Session Metrics:** Each transcript now includes:
- **Session Duration:** Total real-world clock time from when you submitted the first prompt until the last response was generated. This helps you understand how long the entire interaction took.
- **Claude Thinking Time:** Total time Claude spent in thinking blocks across all responses. This shows how much of the session was spent in deliberation vs. execution.
- **Cost:** Total cost in dollars for the conversation session, calculated using the `/cost` command. This helps track API usage costs.

**User Prompts:** Captured verbatim, exactly as you typed them.

**Assistant Responses:** Intelligently summarized to show:
- Tool invocations (e.g., `[Used JIRA skill to query issues]`)
- Commands executed (e.g., `[Ran: python3 -m sidekick.clients.jira...]`)
- Key findings and data (truncated if verbose)
- Results and outcomes (e.g., `[Created Confluence page: URL]`)
- Important decisions and reasoning

**Truncation:** Large outputs, file contents, and verbose data are summarized rather than included in full, keeping transcripts readable.

## Examples

### Example 1: Document Creation Workflow

```
/transcript confluence-onboarding-template
```

Saves a transcript showing how you created an onboarding template, including all JIRA queries, Dropbox exports, and Confluence page creation steps.

### Example 2: Debugging Session

```
/transcript debug-api-timeout
```

Captures the conversation where you debugged an API timeout issue, including all diagnostic commands and the final solution.

### Example 3: Custom Agent Creation

```
/transcript create-status-report-agent
```

Documents the process of creating a new agent, including requirements clarification, implementation, and testing.

## Tips

1. **Save early, save often:** You can run `/transcript` multiple times as your conversation evolves. Each creates a new snapshot.

2. **Use descriptive filenames:** When specifying a filename, use kebab-case and make it descriptive:
   - `jira-roadmap-summary` ✓
   - `transcript` ✗
   - `confluence-doc-migration` ✓
   - `test` ✗

3. **Review before sharing:** Transcripts may contain your specific project names, URLs, or team member names. Review before sharing externally.

4. **Build a library:** Over time, `memory/prompts/` becomes a valuable reference of patterns and workflows you've developed.

## Storage Location

All transcripts are saved to:
```
memory/prompts/[filename].md
```

This directory is gitignored, so transcripts remain local to your machine and won't be committed to version control.

## No Configuration Required

The transcript skill requires no setup, credentials, or external dependencies. It works out of the box.

## Related

- **Memory Skill** - For saving command outputs and data files
- **Project Documentation** - Consider saving key transcripts to your project's documentation folder (outside `memory/`) if they represent stable workflows

## Future Enhancements

Potential improvements to suggest to Claude:

- Add frontmatter metadata (tags, participants, duration)
- Support filtering by time range ("last 10 messages")
- Generate table of contents for long transcripts
- Export to PDF or other formats
- Index transcripts for searching

Just ask Claude to add these features when you need them!
