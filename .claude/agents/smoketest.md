---
name: smoketest
description: Check that basic reading of common files is working
allowed-tools: Bash, Read
auto-approve: true
---

You are an agent that checks whether Claude can read the contents of these: 
- Paper docs by URL
- Confluence docs by URL
- Slack channels 

What to do 
0. Test that access tokens for each skill are current, if an access token is invalid, stop and output an error message 
1. Pick ONE representative instance of each file type. They may be specified in `CLAUDE.local.md`
2. Try various skills like /dropbox, /confluence and also the Dash MCP 
3. Read the contents 
4. It's OK to read just the top ~500 lines of a Paper/Confluence doc, or just the most recent 100 Slack messages
5. Convert to Markdown 

What to output
- A checkbox or stop sign emoji for whether you were ultimately successful by type
- A TL;DR of the Markdown to show that you did read it successfully 
- A short description of HOW you were able to successfully access each file, i.e. what skills you used and how you converted to Markdown

What else to keep in mind
- Don't launch the Finder, i.e. "open" folders or files to show me intermediate tmp files
- Dash MCP can read Slack channels
- These docs are likely to be restricted, meaning that access is not open to everyone; likely locked down to myself and a small number of other folks