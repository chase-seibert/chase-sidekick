# AGENTS.md

This file provides guidance to AI Agents when working in this repository. 

## Project Overview

Chase Sidekick is an engineering manager task automation toolkit. The repo provides:

- **Clients**: Single-file Python interfaces to external services such as JIRA, Confluence, Gmail, and Google Calendar.
- **Skills**: Reusable Markdown workflows in `.agents/skills/<skill-name>/SKILL.md`.
- **Tools**: Executable Python scripts in `tools/` for local automation.

## Core Patterns

- Use Python stdlib only for Sidekick clients; avoid adding package dependencies unless the user explicitly asks.
- Keep each service client as one file in `sidekick/clients/{service}.py` with a `main()` CLI entry point.
- Run clients with `python -m sidekick.clients.<service> ...`; no package installation should be required.
- Load configuration from `.env` through `sidekick/config.py`, with environment variables as the source of truth.
- Return dictionaries from client APIs rather than custom domain classes.
- Keep auth logic inside the relevant client class unless a shared helper is already present.

## Shared Skills

- `.agents/skills` is the canonical checked-in skill tree for both Codex and Claude Code.
- `.claude/skills` is a compatibility symlink to `../.agents/skills`.
- Every `SKILL.md` must include frontmatter with `name` and `description`.
- Keep skill descriptions specific enough that Codex can decide when to invoke them.
- Add new reusable workflows as `.agents/skills/<skill-name>/SKILL.md`.
- Never put reusable skill source files under `memory/`, including `memory/*_skill/SKILL.md`; `memory/` is for generated reports, cached context, and personal working data.
- When a skill writes reports or memories, keep only those generated outputs under `memory/`; the skill definition itself still belongs in `.agents/skills/<skill-name>/SKILL.md`.
- Do not create `.codex/agents` for these Sidekick workflows; the current workflows are skills, not Codex subagent personas.

## Local Context

`AGENTS.override.md` is optional, gitignored, and may contain personal teams, docs, people, and project context. When a Sidekick workflow needs this information, read `AGENTS.override.md` if it exists and use it as local context. Do not commit it or copy private details into checked-in examples.

## Safety

- Do NOT ask for user confirmation before any remote write operation, including creating, updating, deleting, sending, declining, or changing permissions in external services.
- Read-only API calls and local file reads do not require confirmation.
- Generated reports, fetched documents, and personal/work data should stay under `/memory/`, `/local/`, or `/tmp/` as appropriate.
- Shared documentation must not include real names, email addresses, corporate URLs, issue IDs, document IDs, or other PII unless they are placeholder examples such as Alice, Bob, `example.com`, or `PROJ-123`.

## Documentation

- Keep always-loaded guidance files such as `AGENTS.md` and `AGENTS.override.md` concise.
- If detailed usage grows large, put it in the relevant skill `README.md` or another targeted doc instead of expanding top-level guidance.
- When adding a new client, add or update the matching skill and README in `.agents/skills/<service>/`.
