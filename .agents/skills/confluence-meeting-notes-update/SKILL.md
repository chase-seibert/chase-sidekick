---
name: confluence-meeting-notes-update
description: Safely update Confluence meeting notes by changing only Next, the top dated section, a unique placeholder, or the current user's table row/cell.
---

# Safe Confluence Meeting Notes Update

Use this skill when asked to update a Confluence meeting notes page, add an item to a future agenda, replace an AI placeholder, or add notes to the current meeting section.

This skill is intentionally instruction-only. Do not create helper scripts for the workflow. Use Atlassian Rovo MCP for Confluence reads and writes, and use ADF as the safe structured edit format when the Rovo page read is complete. For fallback edits, use the Chrome plugin/live editor first, then use the local Confluence client only when the Chrome path is unavailable or unsuitable and `ATLASSIAN_API_TOKEN` is set.

Rovo is safe for this workflow only when its page read returns the complete ADF body. Rovo updates replace the full Confluence page body, but Rovo reads can truncate large pages and Rovo does not currently provide partial page updates or paginated full-page reads. If the page is large or the Rovo body appears truncated, do not write with Rovo; use Chrome plugin/live-editor automation instead. Use the local Confluence REST API raw-storage HTML fallback only when Chrome is unavailable or unsuitable and `ATLASSIAN_API_TOKEN` is set. The token may rotate every 3 days.

Before identifying meeting sections, date headings, templates, or bullet/table formats, read [meeting-notes-docs.md](references/meeting-notes-docs.md). That reference is the shared source of truth for Confluence meeting notes document shapes.

## Commands

Use Atlassian Rovo MCP for the primary workflow:

```text
getConfluencePage(cloudId, pageId, contentFormat="adf")
updateConfluencePage(cloudId, pageId, body=<ADF JSON>, contentFormat="adf")
getConfluencePage(cloudId, pageId, contentFormat="markdown")
```

Use `python3` only as a final fallback when Rovo and Chrome plugin/live-editor automation are unavailable or unsuitable and `ATLASSIAN_API_TOKEN` is set:

```bash
python3 -m sidekick.clients.confluence get-page-from-link "<confluence-url>"
python3 -m sidekick.clients.confluence read-page <page-id> --html
python3 -m sidekick.clients.confluence update-page <page-id> <content.html>
```

For best-effort agenda date lookup, use the existing Google Calendar client:

```bash
python3 -m sidekick.clients.gcalendar list <time-min> <time-max> <max-results>
python3 -m sidekick.clients.gcalendar get <event-id>
```

Never update meeting notes from Markdown conversion. Read Markdown only for human orientation if useful; all writes must be based on the ADF document fetched from Rovo. If falling back to the local client, use raw storage HTML and the legacy range checks.

## Safe Targets

A valid update must affect exactly one of these regions:

- The body of an existing `Next` H1 section.
- The body of the top-most dated H1 section.
- The insertion point for one new dated or `Next` H1 section.
- A unique `$AI_REPLACE` placeholder.
- The first empty Confluence Note macro.
- A new AI summary note panel inserted inside exactly one chosen meeting section.
- For table-format agenda updates, one intended table row or one intended table cell inside the chosen section.

## Workflow

1. Resolve the page ID from the link if needed, then fetch page details and ADF with Rovo.
2. Identify top-level ADF H1 section boundaries. A section starts after a top-level `heading` node with `attrs.level == 1` and ends before the next top-level H1 or end of document.
3. Build the proposed after-ADF by changing only one safe target.
4. Before writing, compare before and after ADF and verify every changed top-level node is inside the intended target section or insertion point.
5. Immediately before writing, fetch ADF again. If the page changed outside the intended target, stop and re-plan against the latest content.
6. Write the entire after-ADF with Rovo `updateConfluencePage(..., contentFormat="adf")`.
7. Fetch ADF again and verify the live page matches the intended after-ADF, with no out-of-target changes relative to the original.

Do not save rollback files. If a post-update check fails, report the unsafe region and point the user to Confluence version history.

## Placeholder Updates

Use placeholder mode when the user asks to replace a placeholder or when section targeting is too broad.

`$AI_REPLACE` takes precedence:

- If `$AI_REPLACE` appears exactly once, replace only that marker.
- If `$AI_REPLACE` appears more than once, refuse and ask for a more specific target.
- If `$AI_REPLACE` is absent, find the first empty Confluence Note macro.

An empty Note macro is an ADF `panel` with `attrs.panelType == "note"` whose body has no meaningful text after stripping empty paragraphs and whitespace. Replace the empty note panel body, not unrelated page content. If Note detection is ambiguous, refuse.

## Agenda Updates

For "add an item to the agenda", choose the target section in this order:

1. Existing `Next` H1 section.
2. Existing H1 date section for today or the future.
3. A new dated section from the next Google Calendar instance, if exactly one confident match is found.
4. A new `Next` section if Calendar is unavailable or ambiguous.

Calendar matching is best effort, with doc-link matching as the strongest signal. Search future events, fetch event details when needed, and first match the meeting doc link in event descriptions. Normalize copied Confluence links where practical. Only fall back to supplied meeting title or Confluence page title matching when no event description contains the doc link. Fail closed to `Next` rather than inventing a date.

When adding a new section, use the shared document-shape reference for placement, template handling, date headings, and initial bullet/table structure. Place the new section before historical dated sections and after any clear static preamble or top template. If unsure, place `Next` at the top only when that is safer than editing existing content.

## Format Detection

Use the shared document-shape reference to classify the chosen section as bullet format, table format, or empty. Do not count lists nested inside a table node as the section's top-level list format.

## Bullet Format

Append a new item to the first top-level ADF `bulletList` in the target section:

```json
{"type":"listItem","content":[{"type":"paragraph","content":[{"type":"text","text":"Agenda item text"}]}]}
```

If the target section has exactly one empty bullet placeholder, replace that placeholder with the new bullet. If the target section has no list, create a top-level ADF `bulletList` at the start of the section body. Insert user-provided text as ADF text nodes, not HTML.

## AI Summary Notes

For "insert an AI summary note", insert a top-level ADF `panel` with `attrs.panelType == "note"` inside the chosen meeting section. The panel content should be one or more paragraphs containing the supplied summary text. Do not modify preamble/template panels above the first real meeting section.

## Table Format

Table-format docs often have one row per person or one row per agenda/demo item. Prefer updating the current user's row when it exists.

Find the current user from local context or `.env` (`USER_NAME`, `USER_EMAIL`) when needed.

To find the user's row, look for exactly one body row containing any of:

- ADF mention nodes for the current user.
- A visible mention or text matching `USER_NAME`.
- A visible email or username matching `USER_EMAIL`.

If exactly one own row is found, update that row instead of adding a new row. Choose the target cell by matching header text, preferring `Agenda`, `Topic`, `Top of mind`, `Discussion`, `Notes`, or `Item`; otherwise use the last content cell. Append the item inside that cell using a list if a list already exists there, or add a paragraph/list consistent with the cell's existing content.

If no own row exists, clone an existing body row only when the table clearly uses one row per person or agenda item. Fill a name/owner cell with the current user's Confluence mention when practical, and put the item in the agenda-like cell. If multiple own rows are plausible, refuse and ask for a more specific row or column.

## Safety Validation

Before writing, compute the exact target section or insertion index in the original ADF. Then compare before and after content:

- All top-level nodes before the target range must be structurally identical.
- All top-level nodes after the target range must be structurally identical.
- All inserted or replaced nodes must be inside the target range.
- Page title, preamble, templates, unrelated sections, and existing dated meeting notes must not change.
- Re-fetch the page immediately before `updateConfluencePage`; if latest ADF no longer matches the original outside the target range, do not write.

For section updates, the target range is the section body after the H1 and before the next top-level H1. For placeholder updates, it is the marker text node or empty note panel body. For table updates, narrow the target range to the intended row or cell whenever possible.

After writing, fetch the page again with Rovo ADF and Markdown. Verify the live ADF equals the intended after-ADF except for Confluence-added `localId` values on newly inserted nodes. Compare again using the same allowed-range confinement check and report any unexpected normalization.

## Refusal Cases

Refuse to update when:

- The page is not a Confluence page.
- ADF cannot be fetched through Rovo.
- No safe target can be identified.
- Multiple `Next` sections or placeholders make the target ambiguous.
- A top template or static preamble is ambiguous and the requested update could modify it by mistake.
- A table has multiple plausible current-user rows.
- The proposed diff touches content outside the intended region.
- Calendar lookup is ambiguous and creating `Next` would conflict with an existing convention.

When refusing, explain the specific ambiguity and suggest using `$AI_REPLACE` or an empty Note macro as a precise target.
