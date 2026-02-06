---
name: transcript
description: Save conversation transcripts as structured markdown in memory/prompts
argument-hint: [filename]
allowed-tools: Write, Bash, Read
---

# Transcript Skill

Save conversation transcripts as markdown files in the memory/prompts folder.

When invoked, use the Transcript agent to handle the request: $ARGUMENTS

## Usage

When the user asks to save a transcript of the conversation, invoke this skill:

```
/transcript [optional-filename]
```

If no filename is provided, a filename will be auto-generated based on the conversation topic.

## What This Skill Does

1. Extracts the conversation history from the current session
2. Formats it as a structured markdown document with:
   - Date and context header
   - User prompts (verbatim)
   - Assistant responses (truncated to show key actions without verbose output)
   - Clear separation between exchanges
3. Saves the transcript to `memory/prompts/[filename].md`

## Examples

```
/transcript
```
Creates a transcript with an auto-generated filename based on the conversation.

```
/transcript confluence-onboarding
```
Creates a transcript saved as `memory/prompts/confluence-onboarding.md`.

## Output Format

The transcript follows this structure:

```markdown
# Conversation Transcript: [Topic]

**Date:** YYYY-MM-DD

---

## User Prompt 1

[Exact text of user's first prompt]

---

## Assistant Response 1

[Summary of assistant's response, with verbose content truncated]

[Tool invocations shown in brackets]
[Key outcomes and results]

---

## User Prompt 2

[Next user prompt...]

---
```

## Notes

- User prompts are captured exactly as entered
- Assistant responses are intelligently summarized to show:
  - Tool invocations and commands run
  - Key results and outcomes
  - Links to created resources
  - Decisions and approach taken
- Verbose content (large data outputs, full file contents) is truncated
- The transcript is saved in `memory/prompts/` for future reference
