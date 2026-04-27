# Chase Sidekick

Supported AI agents:

- Claude Code
- Codex

**Build your own engineering manager toolkit, one command at a time.**

Sidekick is a playground for using AI agents not for coding per se, but to automate real work tasks using your favorite products. You write code, but the skills are about personal productivity in Confluence, JIRA, Slack, Google Calendar, and similar tools. You're building a set of superpowers that lets an AI coding agent gather context from your everyday tools and then take action.

## Why This Exists

Engineering management involves lots of repetitive data gathering: checking JIRA hierarchies, updating 1:1 docs, synthesizing meeting notes. Instead of building a monolithic tool with every feature baked in, this project takes a different approach:

**You write simple Python scripts that read from stdin and write to stdout. Agents help you build, debug, and refine them as you go.**

The magic is in keeping things simple enough that you can always understand and modify your tools, while powerful enough to automate real work.

## What You Can Ask For

Here are examples of complex multi-skill tasks you can ask the agent to handle.

```
"Download all the files linked to my calendar events for this week, and generate
a list of bullets as a summary for executive leadership"

"For all teams that report to me, look up completed work across JIRA Epics for
the past 30 days and generate a team accomplishments report with kudos to specific engineers"

"Migrate Paper 1:1 docs to Confluence for direct reports with restricted access and update
calendar event links."

"Search Slack for activity in #engineering over the last 30 days and summarize the key
themes, decisions, and action items by person"

"Find my most recent Zoom meeting with a transcript and generate a structured summary
with key topics, decisions, and follow-up items"
```

These exact scenarios are not hard coded anywhere; agents can combine existing client code and skills on the fly from natural language prompts.

### Available Skills

Current skills in `.agents/skills`:

- **chrome** - Query Chrome browsing history.
- **confluence** - Manage Confluence pages with search, read, and write operations.
- **dependency_escalation** - Draft a document for an escalation of a dependency request.
- **dropbox** - Manage Dropbox files and Paper docs.
- **epic_assignment** - Assign active Epics to Roadmap Initiatives based on recent activity.
- **gcalendar** - Manage Google Calendar events.
- **gmail** - Search and manage Gmail messages.
- **gsheets** - Manage Google Sheets: download, upload, and replace sheets with CSV data.
- **interview_history** - Generate all-time interview count reports from Google Calendar.
- **jira** - Query and manage JIRA issues.
- **jira-roadmap** - Explore JIRA roadmap hierarchies recursively.
- **kudos** - Generate kudos for team members from recent 1:1 and meeting notes.
- **markdown** - Convert Markdown to and from other formats.
- **meeting_prep** - Analyze meeting documents and generate prep reports with wins, risks, and questions.
- **memory** - Manage command memory files with prompt metadata and auto-generated filenames.
- **mmr_exec_summary** - Generate executive summaries from MMR (Monthly Metric Review) Confluence pages.
- **omnifocus** - Manage OmniFocus tasks on macOS.
- **oneonone_prep** - Prepare copy/paste 1:1 agendas from 1:1 docs, weekly reports, project activity, Slack context, and management prompts.
- **oneonone_setup** - Create or migrate 1:1 docs from Paper, or create new Confluence docs with permissions and calendar updates.
- **prep-tomorrow-meetings** - Open all meeting docs in Chrome for the next business day.
- **project_activity** - Generate weekly project activity summaries from Slack and JIRA.
- **project_review** - Generate comprehensive project review reports from PRD and tech spec documents.
- **pto_block** - Block calendar for PTO and handle conflicting meetings.
- **recent_docs** - Generate categorized summaries of recent Paper and Confluence docs from Chrome history.
- **sev-review-prep** - Generate questions to ask during SEV review meetings based on Confluence SEV review documents.
- **slack** - Read recent messages from Slack channels using Dash MCP.
- **smoketest** - Check that basic reading of common files is working.
- **sprint_review** - Generate a sprint review report.
- **team-group-analysis** - Analyze completed work across multiple JIRA projects with automatic theme categorization.
- **tech_spec_review** - Read a tech spec doc and write an executive summary.
- **transcript** - Save conversation transcripts as structured Markdown in `memory/transcripts`.
- **weekly_report** - Generate summaries of 1:1 and meeting notes organized by audience.
- **welcome-doc** - Create personalized employee onboarding documents in Confluence.

## What You'll Build

Here's a real example. Ask your agent:

```
Create a skill workflow to generate a project review report starting from a link to a Confluence doc.

Look through the document and any linked docs (PRD, design, tech spec). Pull out the JIRA epic/initiative, figure out who the DRIs are, and create a structured report covering:

- One sentence TL;DR of what the project does
- Product requirements summary with any complex or controversial items called out
- Technical approach and decisions that could impact scope
- Estimates broken down by milestone with confidence levels, highlighting risky estimates
- Dependencies on other teams and external systems, plus what could go wrong
- Questions to ask during tech review
- Kudos for people who contributed

Keep the whole thing under 1500 words. Save it as memory/project_review/[project-name-slug]-review.md

Use the original estimate units from the doc (hours, weeks, whatever they used). Get DRI names from JIRA issues if they're not in the docs. Clean up any temp files when done - only the final report should be in memory.

```

Agents can create the skill workflow for you. It will figure out how to call the existing clients to talk to Confluence, JIRA, Dropbox, and other services. It will know how to save output in a place where it won't be committed to git. You can go back and forth iterating on the workflow to refine it. For example, you could have a subsequent prompt that says "When I ask you to refresh the report, pull all the links again, update the report, and include a changelog at the bottom".

**The kicker?** It took 15 minutes to write this workflow. I was literally able to create it and have it generate the report inside the silent reading period of an actual tech spec review meeting.

That's the power of this approach: simple building blocks that combine into sophisticated automation, where you can build novel use cases ***quickly***. 

## Quick Start

Get running in 60 seconds with the JIRA skill:

```bash
# Clone and setup
git clone https://github.com/chase-seibert/chase-sidekick.git
cd chase-sidekick

# Install dependencies (if not already installed)
brew install pandoc          # For Markdown conversion
brew install tidy-html5      # For HTML cleaning (recommended)

# Configure credentials
cp .env.example .env
# Edit .env with your JIRA details:
#   ATLASSIAN_URL=https://your-company.atlassian.net
#   ATLASSIAN_EMAIL=your-email@company.com
#   ATLASSIAN_API_TOKEN=your_token
# Get token: https://id.atlassian.com/manage-profile/security/api-tokens

# Try it out
python -m sidekick.clients.jira query "project = PROJ AND status = Open"
```

Now ask Claude Code or Codex to use it:
```bash
claude code "Show me all open issues in the PROJ project"
codex "Show me all open issues in the PROJ project"
```

The agent reads the skill documentation in `.agents/skills/jira/SKILL.md` and executes the right command.

If a skill is not configured yet, the agent should point you to that skill's README.md setup steps for API keys and other credentials.

## Philosophy: Simple Tools, Standard I/O

Every client follows the same pattern:

1. **Single Python file** - The entire JIRA client is `sidekick/clients/jira.py` (~400 lines)
2. **Reads stdin, writes stdout** - Data flows through pipes like traditional Unix tools
3. **Human-readable output** - Not JSON blobs, but formatted text you can read
4. **Zero external dependencies** - Only Python stdlib (requests, json, urllib)

This means you and the agent can:
- Pipe outputs together: `python -m jira query "..." | grep "backend"`
- Save outputs: `python -m jira roadmap-hierarchy PROJ-100 > hierarchy.txt`
- Chain commands: `python -m sidekick.clients.confluence search "API" | python -m sidekick.clients.memory write "Search Confluence for API" confluence "search API" --md`

You typically won't ***need** to think about how these are chained together, because Claude Code or Codex will figure it out.

**Why this matters:** You can inspect, modify, and understand every tool. You can see the steps and inspect the intermediate outputs. So can Claude Code and Codex.

**Skills are markdown documentation.** Look at `.agents/skills/project_review/SKILL.md`:

```markdown
# Project Review Skill

Generate comprehensive project status reports from JIRA data.

## Steps

1. Fetch roadmap hierarchy: `python -m sidekick.clients.jira roadmap-hierarchy ISSUE_KEY PROJECT`
2. Analyze recent completions (last 30 days)
3. Identify blocked items
4. Generate structured report
5. Save to memory/project-review/

## Example prompts:
- "Generate a project review for PLATFORM-100"
- "Create a status report for the Auth Migration initiative"
```

Claude Code and Codex discover these skills from `.agents/skills`. When you ask for a project review, the agent sees the workflow, understands which clients to invoke, and executes the steps in order.

**Important: The `memory/` directory is in `.gitignore`** - This is where command outputs get saved (JIRA hierarchies, Confluence searches, workflow results). These files provide context across sessions but aren't checked into version control. Think of them as a local knowledge base that grows as you work.

## Using AGENTS.override.md for Context

When you ask your agent to "look up JIRA Epics for my teams", or "fetch recent content from my 1:1 docs", how does it know what to do?

Create `AGENTS.override.md` in your project root (it's gitignored):

```markdown
# AGENTS.override.md 

## My Teams

- Platform Team, manager Alice, JIRA Project PLAT
- Infrastructure Team, manager Bob, JIRA Project INFRA
- API Team, manager Carol, JIRA Project API

## 1:1 Documents

- [Alice](https://company.atlassian.net/wiki/spaces/ENG/pages/123/MyName+Alice+1+1)
- [Bob](https://example.com/docs/xyz/MyName-Bob-11)

## Key Projects

- Auth Migration: PLAT-1500, PLAT-1520 - Migrate to OAuth2
- API Gateway: API-200 - Centralized API routing

Load [AGENTS.md](AGENTS.md)
```

**The last line is very important, that's what tells the agent to also load the main Markdown file, in an agent-neutral way.**

The content here can be in ANY format. It's just additional text content for workflows that need your local context. Now when you ask "Add a topic to my 1:1 with Alice," the agent knows where to look. When you say "Show me all Platform issues," it knows to query `project = PLAT`.

**This is your personal context layer.** It makes responses more relevant without cluttering the shared codebase.

## Using "Memory" for file-based context 

Sidekick includes a Skill called "memory". This can read and write the results of any prompt in a local directory structure at `./memory`. The folder structure is namespaced by skill. The entire folder is ignored by git; meaning that it's OK to have secrets or personal/work data in there. 

You can ask the agent to "download the spreadsheet at link X and save as CSV in memory". It will handle naming it, etc. Now, at any point in the future you can at-mention this file in your prompts to reload that context.

You can also manually add any file you want to the memory folder. 

For example, you can prompt "@employee.csv show me employees at L5+ in San Francisco". If that data is in the file, there is a very good chance the agent will nail this.

## Design Decisions

### Why No External Libraries?

Every external dependency is a future maintenance burden:
- Version conflicts
- Installation complexity
- Breaking API changes
- Another thing to understand

By using only Python stdlib, everything just works. Clone the repo, set environment variables, run commands. No `pip install`, no virtual environments (unless you want them), no dependency hell.

**The trade-off:** You write more code. The `jira.py` client has a `_request()` method instead of using `requests`. That's ~50 lines of HTTP handling, but it's code you can read and fix.

**The AI coding agent advantage:** When clients are short (300-500 lines) and use only stdlib, Claude Code or Codex can load the entire implementation into context. It doesn't need to make assumptions about external library implementation details. It can see exactly how authentication works, how errors are handled, and what the API surface looks like. This makes debugging and extending clients remarkably fast.

### Why No Unit Tests?

This is a toolkit for your own use, not a library for others. The test is: **does it work when you run it?**

When something breaks:
1. You notice immediately (you're the only user)
2. Claude Code or Codex helps you fix it in real-time
3. You learn how it works by debugging

Traditional testing makes sense for software that ships to users. This is software you use yourself, and you're paired with an AI that can refactor and fix issues as they arise.

**The REST API reality:** Virtually all operations here invoke REST APIs over the network - JIRA, Confluence, Dropbox, Gmail. Testing this properly would require:
- Verbose mocking code (often more code than the client itself)
- Constant vigilance to prevent actual network calls during tests
- Fixture files that assume specific API responses (which change over time)
- Mock setup that duplicates the real API behavior (and inevitably diverges)

The effort-to-value ratio is poor. You'd spend more time maintaining mocks than you'd save in bug prevention. Just run the command and see if it works.

### Keeping You in the Loop

The goal isn't to give you a finished product. **It's to give you something good enough to use, and simple enough to modify.**

When you need a new field from JIRA, you add it. When your Confluence doc structure changes, you adjust the parser. Claude Code or Codex helps with the changes, but you understand what's happening.

This is the opposite of a SaaS tool where you file a feature request and wait. Here, you ask Claude Code or Codex to make the change, review the diff, and run it.

## Warning: Live Network Calls

⚠️ **These tools make real API calls while you're writing and debugging them.**

When an agent is developing a new JIRA command, it may test it against your actual JIRA instance. When debugging Confluence integration, it may read from your real wiki.

This is by design - you see results immediately - but be aware:
- Failed experiments might create test issues (clean them up after)
- API rate limits are real (JIRA allows ~100 requests/minute)
- Bugs in write operations affect real data (though most skills are read-only)

**Safety guardrails:** `CLAUDE.md` and `AGENTS.md` both specify that the agent should ask for confirmation before making calls that write data to remote services (creating issues, updating pages, sending emails). Read operations do not require confirmation; the agent can query JIRA, search Confluence, or read files without asking.

**Start with read operations and queries.** Once you trust a command, move to writes.

## Project Structure

```
chase-sidekick/
├── .agents/
│   └── skills/              # Canonical shared skills for Claude Code and Codex
│       ├── chrome/
│       ├── confluence/
│       ├── dependency_escalation/
│       ├── dropbox/
│       ├── epic_assignment/
│       ├── gcalendar/
│       ├── gmail/
│       ├── gsheets/
│       ├── interview_history/
│       ├── jira/
│       ├── jira-roadmap/
│       ├── kudos/
│       ├── markdown/
│       ├── meeting_prep/
│       ├── memory/
│       ├── mmr_exec_summary/
│       ├── omnifocus/
│       ├── oneonone_prep/
│       ├── oneonone_setup/
│       ├── prep-tomorrow-meetings/
│       ├── project_activity/
│       ├── project_review/
│       ├── pto_block/
│       ├── recent_docs/
│       ├── sev-review-prep/
│       ├── slack/
│       ├── smoketest/
│       ├── sprint_review/
│       ├── team-group-analysis/
│       ├── tech_spec_review/
│       ├── transcript/
│       ├── weekly_report/
│       └── welcome-doc/
├── .claude/
│   ├── settings.json        # Claude-specific permissions/config
│   └── skills -> ../.agents/skills
├── tools/
│   ├── email_trigger_watcher.py  # Phone-to-desktop Claude/Codex email triggers
│   ├── prep_tomorrow_meetings.py # Open meeting docs in browser
│   └── smoketest.py              # Test access to Paper, Confluence, Slack
├── sidekick/
│   ├── config.py            # Load from .env
│   └── clients/             # Single-file service clients
│       ├── chrome.py        # Chrome history queries
│       ├── confluence.py    # Confluence search/read/write
│       ├── dropbox.py       # Dropbox files and Paper docs
│       ├── gcalendar.py     # Google Calendar events
│       ├── gmail.py         # Gmail search and drafts
│       ├── gsheets.py       # Google Sheets CSV workflows
│       ├── jira.py          # JIRA issue queries and updates
│       ├── markdown.py      # Markdown/HTML conversion
│       ├── markdown_pdf.py  # Markdown to PDF rendering
│       ├── memory.py        # Local memory file management
│       └── omnifocus.py     # OmniFocus task management
├── memory/                  # Saved command outputs (gitignored)
│   ├── jira/               # JIRA query results
│   ├── confluence/         # Confluence search results
│   ├── weekly_report/      # Weekly report outputs
│   └── project_review/     # Project review outputs
├── .env                     # Your credentials (gitignored)
├── AGENTS.md                # Codex guidance
├── CLAUDE.md                # Claude Code guidance
└── CLAUDE.local.md          # Your personal context (optional, gitignored)
```

## Configuration

All credentials go in `.env` (gitignored):

```bash
# Atlassian (JIRA + Confluence)
ATLASSIAN_URL=https://company.atlassian.net
ATLASSIAN_EMAIL=your@email.com
ATLASSIAN_API_TOKEN=your_token_here

# User info (for 1:1 docs)
USER_NAME=Alice
USER_EMAIL=alice@example.com

# Dropbox
DROPBOX_ACCESS_TOKEN=your_token_here

# Google (Gmail, Calendar, Sheets)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_secret
GOOGLE_REFRESH_TOKEN=your_refresh_token
```

**Getting tokens:** Check the README for each skill for provisioning instructions, including where to generate API tokens.

### Connecting Dash MCP

To enable Slack, Zoom, and other Dropbox Dash integrations via MCP (Model Context Protocol):

1. **Install Dash MCP Server:**
   - Open Claude Code or Codex in the terminal
   - Use /mcp and add via URL [https://mcp.dropbox.com/dash](https://mcp.dropbox.com/dash)
   - It will prompt you to authenticate in a browser
   - Make sure you enable the desired connectors on Dash web

2. **Available Dash Connectors:**
   - **Slack** - Search messages, channels, files with full Slack search syntax
   - **Zoom** - Access meeting transcripts and recordings

It also has connectors for Jira and Confluence; which has long-lived authentication tokens. 

3. **Usage:**
   Once connected, Claude Code or Codex can use Dash MCP to:
   ```
   "Search Slack #engineering for discussions about API changes this week"
   "Find my recent Zoom meetings and summarize the transcripts"
   ```

Try adding your most important Slack channels to `CLAUDE.local.md` for quick context.

## Phone to Desktop: Email Triggers

You can trigger Claude Code or Codex from your phone by sending yourself an email. The subject prefix chooses the agent: use `Claude <prompt>` or `Codex <prompt>`.

### Setup

**Prerequisites:**
- Gmail client must be configured (see [Gmail skill](.agents/skills/gmail/README.md) for OAuth setup)
- Claude Code CLI must be available in PATH (`/Users/username/.local/bin/claude`)
- Codex CLI must be available in PATH for Codex triggers (`/opt/homebrew/bin/codex`)
- Python 3 installed

**Setup:**

1. **Configure allowed sender emails** in `.env`:

   Add your email addresses (comma-separated for multiple). Codex triggers use `CODEX_TRIGGER_EMAILS` if present and fall back to `CLAUDE_TRIGGER_EMAILS`.
   ```bash
   CLAUDE_TRIGGER_EMAILS=your-work@company.com,your-personal@email.com
   CODEX_TRIGGER_EMAILS=your-work@company.com,your-personal@email.com
   ```

2. **Add to system crontab** (runs every 5 minutes):

   ```bash
   crontab -e
   ```

   Add this line (replace paths if needed):
   ```bash
   */5 * * * * cd chase-sidekick && /usr/local/bin/python3 tools/email_trigger_watcher.py >> /tmp/email_trigger_watcher.log 2>&1
   ```

## Adding New Skills

Want to add a Slack client? Claude Code or Codex is good at writing this kind of thing.

1. **Ask the agent to write the client:**
   ```
   "Write a Slack client that can list channels, send messages, and search message history."
   ```

The agent should give you examples of how to call the client at the command line.

2. **Test it until it works:**
   ```bash
   python -m sidekick.clients.slack list-channels
   ```

This is where you will need to create and copy in to `.env` any credentials the agent identifies for this client.

3. **Ask the agent to document it:**
   ```
   "Now write a Skill for this client"
   ```

4. **Use it:**
   ```
   "Show me recent messages in #engineering"
   ```

Claude Code and Codex read the skill documentation and know how to invoke your new command. You don't need to register anything or update a central config. You can use subsequent prompts to refine the client and the skill as you debug, find new use cases, etc.

## Why This Is Fun

Building these tools is satisfying because:

1. **You see results immediately** - Run a command, get real data
2. **No yak shaving** - No build systems, dependency management, or framework configuration
3. **You own the code** - Simple enough to understand, small enough to modify
4. **You could write it, but you don't have to** - the agent handles HTTP parsing, error checking, argument parsing, docstrings, and CLI interfaces
5. **It compounds** - Each skill makes the next one easier to build

This is coding as conversation with an AI, where you focus on what you want and the agent handles implementation details.

It's also a great way to stay technical as a manager. You're writing real code that solves real problems, but without the overhead of maintaining production systems. You could absolutely write this code yourself, but having Claude Code or Codex do the tedious parts means you actually finish projects instead of abandoning them after the fun parts are done.
