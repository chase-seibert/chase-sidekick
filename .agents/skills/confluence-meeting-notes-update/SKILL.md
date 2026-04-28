---
name: confluence-meeting-notes-update
description: Safely update Confluence meeting notes by changing only Next, the top dated section, a unique placeholder, or the current user's table row/cell.
---

# Safe Confluence Meeting Notes Update

Use this skill when asked to update a Confluence meeting notes page, add an item to a future agenda, replace an AI placeholder, or add notes to the current meeting section.

This skill is intentionally instruction-only. Do not create helper scripts for the workflow. Use the existing Confluence client directly, edit raw Confluence storage HTML, and validate that the full-page update changes only the intended region.

## Commands

Use `python3`:

```bash
python3 -m sidekick.clients.confluence get-page-from-link "<confluence-url>"
python3 -m sidekick.clients.confluence read-page <page-id> --html
python3 -m sidekick.clients.confluence update-page <page-id> <content.html>
```

For best-effort agenda date lookup, use the existing Google Calendar client:

```bash
python3 -m sidekick.clients.gcalendar list <time-min> <time-max> <max-results>
```

Never update from Markdown conversion. Read Markdown only for human orientation if useful; all writes must be based on raw storage HTML from `read-page --html`.

## Safe Targets

A valid update must affect exactly one of these regions:

- The body of an existing `Next` H1 section.
- The body of the top-most dated H1 section.
- A unique `$AI_REPLACE` placeholder.
- The first empty Confluence Note macro.
- For table-format agenda updates, one intended table row or one intended table cell inside the chosen section.

Confluence meeting docs use H1 sections. A date heading may be visible text such as `Apr 23, 2026`, or a Confluence date object:

```html
<h1><time datetime="2026-04-30" /></h1>
```

When creating a dated section, prefer the Confluence date object form above. If the next meeting date cannot be found confidently, create `Next` instead.

## Workflow

1. Resolve the page ID from the link if needed, then fetch page details and raw storage HTML.
2. Identify H1 section boundaries in raw HTML. A section starts after its `<h1>` and ends before the next top-level `<h1>` or end of document.
3. Build the proposed after-HTML by changing only one safe target.
4. Before writing, compare before and after HTML and verify every changed byte is within the intended target range.
5. Immediately before writing, fetch raw storage HTML again. If the page changed outside the intended target, stop and re-plan against the latest content.
6. Write the entire after-HTML with `update-page`.
7. Fetch raw storage HTML again and verify the live page matches the intended after-HTML, with no out-of-target changes relative to the original.

Do not save rollback files. If a post-update check fails, report the unsafe region and point the user to Confluence version history.

## Placeholder Updates

Use placeholder mode when the user asks to replace a placeholder or when section targeting is too broad.

`$AI_REPLACE` takes precedence:

- If `$AI_REPLACE` appears exactly once, replace only that marker.
- If `$AI_REPLACE` appears more than once, refuse and ask for a more specific target.
- If `$AI_REPLACE` is absent, find the first empty Confluence Note macro.

An empty Note macro is an `ac:structured-macro` with `ac:name="note"` whose body has no meaningful text after stripping tags, empty paragraphs, comments, and whitespace. Replace the empty Note macro body, not unrelated page content. If Note detection is ambiguous, refuse.

## Agenda Updates

For "add an item to the agenda", choose the target section in this order:

1. Existing `Next` H1 section.
2. Existing H1 date section for today or the future.
3. A new dated section from the next Google Calendar instance, if exactly one confident match is found.
4. A new `Next` section if Calendar is unavailable or ambiguous.

Calendar matching is best effort. Search the next 60 days and match by supplied meeting title, Confluence page title, or the page URL in the event description. Fail closed to `Next` rather than inventing a date.

When adding a new section, place it before historical dated sections but after any non-meeting preamble only if that preamble is clearly static context. If unsure, place `Next` at the top.

## Format Detection

Inspect the chosen section in raw HTML:

- If the first meaningful structure is `<table>`, treat it as table format.
- If the first meaningful structure is `<ul>` or `<ol>`, treat it as bullet format.
- If the section is empty, default to bullet format unless the user explicitly asks for a table row.

Ignore lists nested inside a table when deciding whether the section itself is table or bullet format.

## Bullet Format

Append a new item to the first top-level list in the target section:

```html
<li><p>Agenda item text</p></li>
```

If the target section has no list, create a `<ul>` at the start of the section body. Escape user-provided text for HTML unless intentionally inserting reviewed storage HTML.

## Table Format

Table-format docs often have one row per person or one row per agenda/demo item. Prefer updating the current user's row when it exists.

Find the current user from `sidekick.config.get_user_config()` or `.env` (`USER_NAME`, `USER_EMAIL`), and resolve the Confluence account ID with `ConfluenceClient.get_user_account_id(USER_EMAIL)` when needed.

To find the user's row, look for exactly one body row containing any of:

- `<ri:user ri:account-id="...">` for the current user's account ID.
- A visible mention or text matching `USER_NAME`.
- A visible email or username matching `USER_EMAIL`.

If exactly one own row is found, update that row instead of adding a new row. Choose the target cell by matching header text, preferring `Agenda`, `Topic`, `Top of mind`, `Discussion`, `Notes`, or `Item`; otherwise use the last content cell. Append the item inside that cell using a list if a list already exists there, or add a paragraph/list consistent with the cell's existing content.

If no own row exists, clone an existing body row only when the table clearly uses one row per person or agenda item. Fill a name/owner cell with the current user's Confluence mention when practical, and put the item in the agenda-like cell. If multiple own rows are plausible, refuse and ask for a more specific row or column.

## Safety Validation

Before writing, compute the exact target range in the original HTML. Then compare before and after content:

- Prefix before the target range must be byte-for-byte identical.
- Suffix after the target range must be byte-for-byte identical.
- All inserted or replaced content must be inside the target range.
- Page title and unrelated sections must not change.
- Re-fetch the page immediately before `update-page`; if latest storage HTML no longer matches the original outside the target range, do not write.

For section updates, the target range is the section body after the H1 and before the next top-level H1. For placeholder updates, it is the marker span or empty Note macro body. For table updates, narrow the target range to the intended row or cell whenever possible.

After writing, fetch the page again with `read-page --html`. Verify the live HTML equals the intended after-HTML. If Confluence normalizes storage HTML, compare again using the same allowed-range confinement check and report any unexpected normalization.

## Refusal Cases

Refuse to update when:

- The page is not a Confluence page.
- Raw storage HTML cannot be fetched.
- No safe target can be identified.
- Multiple `Next` sections or placeholders make the target ambiguous.
- A table has multiple plausible current-user rows.
- The proposed diff touches content outside the intended region.
- Calendar lookup is ambiguous and creating `Next` would conflict with an existing convention.

When refusing, explain the specific ambiguity and suggest using `$AI_REPLACE` or an empty Note macro as a precise target.
