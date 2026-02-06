# Chase Sidekick

**Build your own engineering manager toolkit, one command at a time.**

Sidekick is playground for using Claude Code not for coding per-se, but to automate real work tasks using your favorite products. You write code, but the skills and agents are about personal productivity in Confluence, JIRA, etc. You're  building and running a set of super powers to enable Claude Code to get go into your everyday tools to get context, and then take action. 

## What You Can Ask For

Here are examples of complex multi-skill tasks you can ask Claude Code to handle. 

```
"Download all the files linked to my calendar events for this week, and generate
a list of bullets as a summary for executive leadership"

"For all teams that report to me, look up completed work across JIRA Epics for 
the past 30 days and generate a team accomplishments report with kudos to specific engineers"

"Migrate Paper 1:1 docs to Confluence for direct reports with restricted access and update 
calendar event links."
```

Note that these exact scenarios are not hard coded anywhere; Claude can combine existing client code and Skills on the fly to do these, all from natural language prompts. 

## Why This Exists

Engineering management involves lots of repetitive data gathering: checking JIRA hierarchies, updating 1:1 docs, synthesizing meeting notes. Instead of building a monolithic tool with every feature baked in, this project takes a different approach:

**You write simple Python scripts that read from stdin and write to stdout. Claude Code helps you build, debug, and refine them as you go.**

The magic is in keeping things simple enough that you can always understand and modify your tools, while powerful enough to automate real work.

## What You'll Build

Here's a real example. Ask Claude Code:

```
Create an Agent to generate a project review report starting from a link to a Confluence doc. 

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

Claude will create the Agent for you. It will figure out how to call the existing clients to talk to Confluence, JIRA, Dropbox, etc. It will know how to save output in a place where it won't be committed to git. You can go back and forth iterating on the Agent to refine. For example, you could have a subsequent prompt that says "When I ask you to refresh the report, pull all the links again, update the report, and include a changelog at the bottom".

**The kicker?** It took 15 minutes for Claude Code to write this agent. I was literally able to create this agent and have it generate the report inside the silent reading period of an actual tech spec review meeting.

That's the power of this approach: simple building blocks that combine into sophisticated automation, where you can build novel use cases ***quickly***. 

## Quick Start

Get running in 60 seconds with the JIRA skill:

```bash
# Clone and setup
git clone https://github.com/yourusername/chase-sidekick.git
cd chase-sidekick

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

Now ask Claude Code to use it:
```bash
claude code "Show me all open issues in the PROJ project"
```

Claude reads the skill documentation in `.claude/skills/jira/SKILL.md` and executes the right command.

If Claude tries to use a skill that is not configured yet, it will prompt you with the steps in the README.md for the skill to provision API keys, etc. 

## Philosophy: Simple Tools, Standard I/O

Every client follows the same pattern:

1. **Single Python file** - The entire JIRA client is `sidekick/clients/jira.py` (~400 lines)
2. **Reads stdin, writes stdout** - Data flows through pipes like traditional Unix tools
3. **Human-readable output** - Not JSON blobs, but formatted text you can read
4. **Zero external dependencies** - Only Python stdlib (requests, json, urllib)

This means you (and Claude) can:
- Pipe outputs together: `python -m jira query "..." | grep "backend"`
- Save outputs: `python -m jira roadmap-hierarchy PROJ-100 > hierarchy.txt`
- Chain commands: `python -m confluence search "API" | python -m output write ...`

You typically won't ***need** to think about how these are chained together, because Claude will figure it out. 

**Why this matters:** You can inspect, modify, and understand every tool. You can see the steps, and inspect the intermediate outputs. And so can Claude. 

**Skills and agents are markdown documentation.** Look at `.claude/agents/project-review.md`:

```markdown
# Project Review Agent

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

Claude Code reads these files at the start of every session. When you ask for a project review, Claude sees the agent workflow, understands which clients to invoke, and executes the steps in order.

**Important: The `memory/` directory is in `.gitignore`** - This is where command outputs get saved (JIRA hierarchies, Confluence searches, agent results). These files provide context for Claude across sessions but aren't checked into version control. Think of them as a local knowledge base that grows as you work.

## Using CLAUDE.local.md for Context

When you ask Claude to "look up JIRA Epics for my teams", or "fetch recent content from my 1:1 docs", how does it know what to do?

Create `CLAUDE.local.md` in your project root (it's gitignored):

```markdown
# CLAUDE.local.md

## My Teams

- Platform Team, manager Alice, JIRA Project PLAT
- Infrastructure Team, manager Bob, JIRA Project INFRA
- API Team, manager Carol, JIRA Project API

## 1:1 Documents

- [Alice](https://company.atlassian.net/wiki/spaces/ENG/pages/123/MyName+Alice+1+1)
- [Bob](https://www.dropbox.com/scl/fi/xyz/MyName-Bob-11.paper)

## Key Projects

- Auth Migration: PLAT-1500, PLAT-1520 - Migrate to OAuth2
- API Gateway: API-200 - Centralized API routing
```

The content here can be in ANY format. It's just additional text content for all your prompts. Now when you ask Claude "Add a topic to my 1:1 with Alice," it knows where to look. When you say "Show me all Platform issues," it knows to query `project = PLAT`.

**This is your personal context layer.** It makes Claude's responses more relevant without cluttering the shared codebase.

## Using "Memory" for file-based context 

Sidekick includes a Skill called "memory". This can read and write the results of any prompt in a local directory structure at `./memory`. The folder structure is namespaced by skill. The entire folder is ignored by git; meaning that it's OK to have secrets or personal/work data in there. 

You can ask Claude to "download the spreadsheet at link X and save as CSV in memory". It will handle naming it, etc. Now, at any point in the future you can at-mention this file in your prompts to reload that context. 

You can also manually add any file you want to the memory folder. 

For example, you can prompt Claude "@employee.csv show me employees at L5+ in San Francisco". If that data is in the file, there is a very good change Claude will nail this. 

***Note: in order to be able to at-mention .gitignored files, you need to toggle the Claude setting for "Claude Code: Respect Git Ignore".***

## Design Decisions

### Why No External Libraries?

Every external dependency is a future maintenance burden:
- Version conflicts
- Installation complexity
- Breaking API changes
- Another thing to understand

By using only Python stdlib, everything just works. Clone the repo, set environment variables, run commands. No `pip install`, no virtual environments (unless you want them), no dependency hell.

**The trade-off:** You write more code. The `jira.py` client has a `_request()` method instead of using `requests`. That's ~50 lines of HTTP handling, but it's code you can read and fix.

**The Claude Code advantage:** When clients are short (300-500 lines) and use only stdlib, Claude can load the entire implementation into context. It doesn't need to make assumptions about external library implementation details. It knows exactly how authentication works, how errors are handled, what the API surface looks like - because it wrote that code, the docstrings, the calling conventions. This makes debugging and extending clients remarkably fast.

### Why No Unit Tests?

This is a toolkit for your own use, not a library for others. The test is: **does it work when you run it?**

When something breaks:
1. You notice immediately (you're the only user)
2. Claude Code helps you fix it in real-time
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

When you need a new field from JIRA, you add it. When your Confluence doc structure changes, you adjust the parser. Claude Code helps with the changes, but you understand what's happening.

This is the opposite of a SaaS tool where you file a feature request and wait. Here, you just ask Claude to make the change, review the diff, and run it.

## Warning: Live Network Calls

⚠️ **These tools make real API calls while you're writing and debugging them.**

When Claude is developing a new JIRA command, it will test it against your actual JIRA instance. When debugging Confluence integration, it will read from your real wiki.

This is by design - you see results immediately - but be aware:
- Failed experiments might create test issues (clean them up after)
- API rate limits are real (JIRA allows ~100 requests/minute)
- Bugs in write operations affect real data (though most skills are read-only)

**Safety guardrails:** The `CLAUDE.md` instructions specify that Claude should ask for confirmation before making calls that write data to remote services (creating issues, updating pages, sending emails). Read operations do not require confirmation - Claude can query JIRA, search Confluence, or read files without asking.

**Start with read operations and queries.** Once you trust a command, move to writes.

## Project Structure

```
chase-sidekick/
├── .claude/
│   ├── skills/              # Command documentation (Claude reads these)
│   │   ├── jira/
│   │   │   ├── SKILL.md     # JIRA skill documentation (Claude reads this)
│   │   │   └── README.md    # Extended JIRA reference (for humans)
│   │   ├── confluence/
│   │   │   ├── SKILL.md     # Confluence skill documentation
│   │   │   └── README.md    # Extended reference
│   │   ├── omnifocus/
│   │   │   ├── SKILL.md     # OmniFocus skill documentation
│   │   │   └── README.md    # Extended reference
│   │   ├── dropbox/
│   │   │   ├── SKILL.md     # Dropbox skill documentation
│   │   │   └── README.md    # Extended reference
│   │   └── ...              # Other skills follow same pattern
│   └── agents/              # Multi-step workflows
│       ├── weekly_report.md    # Generate weekly summaries
│       └── project_review.md   # Generate project status reports
├── sidekick/
│   ├── config.py            # Load from .env
│   └── clients/             # Single-file service clients
│       ├── jira.py          # ~400 lines, stdlib only
│       ├── confluence.py    # ~500 lines, stdlib only
│       ├── chrome.py        # ~600 lines, stdlib only
│       ├── dropbox.py       # ~300 lines, stdlib only
│       ├── omnifocus.py     # ~400 lines, stdlib only
│       ├── gmail.py         # ~300 lines, stdlib only
│       └── gcalendar.py     # ~250 lines, stdlib only
├── memory/                  # Saved command outputs (gitignored)
│   ├── jira/               # JIRA query results
│   ├── confluence/         # Confluence search results
│   ├── weekly_report/      # Weekly report outputs
│   └── project_review/     # Project review outputs
├── .env                     # Your credentials (gitignored)
└── CLAUDE.local.md          # Your personal context (optional, gitignored)
```

## Available Skills

Current skills (each is a single-file client + markdown docs):

- **JIRA** - Query issues, traverse hierarchies, manage labels
- **Confluence** - Search pages, read/write content, manage 1:1 docs
- **Chrome** - Query browsing history, search visited pages, filter by service (Confluence, JIRA, Paper, etc.)
- **Dropbox** - Read/write files and Paper docs
- **OmniFocus** - Task management (macOS only)
- **Gmail** - Search messages, create drafts
- **Google Calendar** - Manage events
- **Google Sheets** - CSV import/export
- **Markdown to PDF** - Convert docs with pandoc
- **Transcript** - Save conversation transcripts as markdown to memory/prompts
- **Welcome Doc** - Create personalized employee onboarding documents in Confluence


## Configuration

All credentials go in `.env` (gitignored):

```bash
# Atlassian (JIRA + Confluence)
ATLASSIAN_URL=https://company.atlassian.net
ATLASSIAN_EMAIL=your@email.com
ATLASSIAN_API_TOKEN=your_token_here

# User info (for 1:1 docs)
USER_NAME=Chase
USER_EMAIL=your@email.com

# Dropbox
DROPBOX_ACCESS_TOKEN=your_token_here

# Google (Gmail, Calendar, Sheets)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_secret
GOOGLE_REFRESH_TOKEN=your_refresh_token
```

**Getting tokens:** Check the README for each skill for provisioning instructions, including where to generate API tokens:

## Adding New Skills

Want to add a Slack client? Claude is really good at writing this kind of thing; it's been done thousands of times in its training set. 

1. **Ask Claude to write the client:**
   ```
   "Write a Slack client that can list channels, send messages, and search message history."
   ```

Claude will nail this, and give you examples of how to call the client at the command line. 

2. **Test it until it works:**
   ```bash
   python -m sidekick.clients.slack list-channels
   ```

This is where you will need to create and copy in to `.env` any credentials that Claude identifies for this client. 

3. **Ask Claude to document it:**
   ```
   "Now write a Skill for this client"
   ```

4. **Use it:**
   ```
   "Show me recent messages in #engineering"
   ```

Claude reads the skill documentation and knows how to invoke your new command. You don't need to register anything or update a central config. You can use subsequent prompts to refine the client and the Skill as you debug, find new use cases, etc. 

## Why This Is Fun

Building these tools is satisfying because:

1. **You see results immediately** - Run a command, get real data
2. **No yak shaving** - No build systems, dependency management, or framework configuration
3. **You own the code** - Simple enough to understand, small enough to modify
4. **You could write it, but you don't have to** - Claude handles HTTP parsing, error checking, argument parsing, docstrings, CLI interfaces
5. **It compounds** - Each skill makes the next one easier to build

This is coding as conversation with an AI, where you focus on what you want and Claude handles implementation details.

It's also a great way to stay technical as a manager. You're writing real code that solves real problems, but without the overhead of maintaining production systems. You could absolutely write this code yourself, but having Claude do the tedious parts means you actually finish projects instead of abandoning them after the fun parts are done.

---

## Full Command Reference

### Available Skills

See individual skill documentation for detailed command usage:

- [JIRA](.claude/skills/jira/README.md) - Query issues, traverse hierarchies, manage labels
- [Confluence](.claude/skills/confluence/README.md) - Search pages, read/write content, manage 1:1 docs
- [Chrome](.claude/skills/chrome/README.md) - Query browsing history, search visited pages, filter by service
- [OmniFocus](.claude/skills/omnifocus/README.md) - Task management (macOS only)
- [Dropbox](.claude/skills/dropbox/README.md) - Read/write files and Paper docs
- [Gmail](.claude/skills/gmail/README.md) - Search messages, create drafts
- [Google Calendar](.claude/skills/gcalendar/README.md) - Manage events
- [Google Sheets](.claude/skills/gsheets/README.md) - CSV import/export
- [Memory Management](.claude/skills/memory/README.md) - Save command outputs with metadata
- [Markdown to PDF](.claude/skills/markdown-pdf/README.md) - Convert docs with pandoc
- [Transcript](.claude/skills/transcript/README.md) - Save conversation transcripts to memory/prompts
- [Welcome Doc](.claude/skills/welcome-doc/README.md) - Create personalized employee onboarding documents

### Available Agents

Multi-step workflows that coordinate multiple clients:

- [Weekly Report](.claude/agents/weekly_report.md) - Generate weekly summaries from 1:1 and meeting docs
- [Project Review](.claude/agents/project_review.md) - Generate project status reports from JIRA data
- [Welcome Doc](.claude/agents/welcome-doc.md) - Create personalized employee onboarding documents with interactive prompts

Or just ask Claude Code:
```
"How do I query JIRA issues by label?"
"Show me how to add topics to my 1:1 docs"
"What can I do with the Dropbox client?"
"What agents are available?"
```
