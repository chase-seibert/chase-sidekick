---
name: transcript
description: Save conversation transcripts as structured markdown in memory/transcripts
argument-hint: [filename]
allowed-tools: Write, Bash, Read
---

# Transcript Skill

Save conversation transcripts as markdown files in the memory/transcripts folder.

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
   - Session metrics (duration, thinking time, cost)
   - User prompts (verbatim)
   - Assistant responses (truncated to show key actions without verbose output)
   - Clear separation between exchanges
3. Saves the transcript to `memory/transcripts/[filename].md`

## Examples

```
/transcript
```
Creates a transcript with an auto-generated filename based on the conversation.

```
/transcript confluence-onboarding
```
Creates a transcript saved as `memory/transcripts/confluence-onboarding.md`.

## Output Format

The transcript follows this structure:

```markdown
# Conversation Transcript: [Topic]

**Date:** YYYY-MM-DD

**Session Duration:** [Total real-world clock time from first user prompt timestamp to last assistant response timestamp, in format: X hours Y minutes Z seconds or Xm Ys for shorter durations]

**Claude Thinking Time:** [Total time spent in thinking blocks across all responses, in format: X hours Y minutes Z seconds or Xm Ys for shorter durations]

**Cost:** $X.XX

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
- The transcript is saved in `memory/transcripts/` for future reference

### Calculating Session Metrics

Before generating the transcript, calculate and include these metrics:

1. **Session Duration**: Calculate the real-world clock time from the timestamp of the first user prompt to the timestamp of the last assistant response. Look at the conversation history metadata to find these timestamps. Format as:
   - For durations under 1 hour: "Xm Ys" (e.g., "5m 23s")
   - For durations over 1 hour: "Xh Ym Zs" (e.g., "1h 15m 42s")

2. **Claude Thinking Time**: Sum the total time spent in all thinking blocks across all assistant responses in the conversation. This can be found in the conversation history metadata for each response. Format using the same time format as Session Duration.

3. **Cost**: Before generating the transcript, run the `/cost` slash command to get the total cost of the conversation session in dollars. Include this value formatted as "$X.XX" (e.g., "$0.45" or "$2.30").

These metrics should appear at the top of the transcript, immediately after the Date line and before the first separator.
