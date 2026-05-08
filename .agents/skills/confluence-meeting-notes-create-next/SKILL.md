---
name: confluence-meeting-notes-create-next
description: Create the next dated or Next H1 section in an existing Confluence meeting notes doc using calendar doc-link matching, templates, or prior table shape.
---

# Create Next Confluence Meeting Notes Section

Use this skill when asked to prepare, create, or add the next instance section for an existing Confluence 1:1 or recurring meeting notes page.

This skill is intentionally instruction-only. Do not create helper scripts for the workflow. Use the existing Confluence and Google Calendar clients directly, edit raw Confluence storage HTML, and validate that the full-page update changes only the intended insertion range.

Before editing, read [meeting-notes-docs.md](../confluence-meeting-notes-update/references/meeting-notes-docs.md). That reference is the shared source of truth for meeting-section boundaries, templates, bullet/table formats, calendar matching, and insertion placement.

## Commands

Use `python3`:

```bash
python3 -m sidekick.clients.confluence get-page-from-link "<confluence-url>"
python3 -m sidekick.clients.confluence read-page <page-id> --html
python3 -m sidekick.clients.confluence update-page <page-id> <content.html>
python3 -m sidekick.clients.gcalendar list <time-min> <time-max> <max-results>
python3 -m sidekick.clients.gcalendar get <event-id>
```

Never update from Markdown conversion. Read Markdown only for human orientation if useful; all writes must be based on raw storage HTML from `read-page --html`.

## Workflow

1. Resolve the page ID from the Confluence link if needed, then fetch page details and raw storage HTML.
2. Read the shared document-shape reference and identify real top-level meeting section boundaries, static preamble, top template, existing `Next`, dated sections, and the most recent prior meeting instance. Ignore static H1 preamble headings and H1s nested inside Confluence macros, ADF panels, note/info blocks, fallback renderings, tables, or other containers.
3. If `Next` already exists, stop without writing.
4. Find the next calendar instance. Search the next 60 days, fetch event details as needed, and first match the Confluence meeting doc link in event descriptions. If one or more events contain the doc link, choose the earliest future start date.
5. Only if no event description contains the doc link, fall back to supplied meeting title, Confluence page title, or an exact title-like match. If matching is not confident, use `Next`.
6. If a confident next date was found and that H1 date section already exists, stop without writing.
7. Build exactly one new H1 section:
   - Confident date: `<h1><time datetime="YYYY-MM-DD" /></h1>`.
   - No confident date: `<h1>Next</h1>`.
8. Build the new section body from the first applicable source:
   - Clear top template: copy the template body without copying the template heading.
   - Clear top Confluence note/info template: copy reusable children from the macro body or ADF `<ac:adf-content>` only. Do not copy the note/info wrapper, ADF panel wrapper, fallback rendering, or create a new note block.
   - Non-template table doc: clone the most recent prior meeting table shape, preserving headers, row count, row order, and people/name cells while emptying other content cells.
   - Otherwise: create a bullet section with one empty bullet.
9. Insert the new section before historical dated sections and after clear static preamble or template content. When a clear agenda/template note block follows static preamble and precedes the first real meeting section, insert immediately after the whole note block and immediately before the first real meeting section. If the insertion point is ambiguous, refuse.
10. Before writing, compare before and after HTML and verify every changed byte is within the intended insertion range.
11. Immediately before writing, fetch raw storage HTML again. If the page changed outside the intended insertion range, stop and re-plan against the latest content.
12. Write the entire after-HTML with `update-page`.
13. Fetch raw storage HTML again and verify the live page matches the intended after-HTML, with no out-of-target changes relative to the original.

Do not save rollback files. If a post-update check fails, report the unsafe region and point the user to Confluence version history.

## Calendar Matching

Doc-link matching is the authoritative signal for the next meeting date.

- Normalize candidate links where practical: HTML-decode, URL-decode, strip fragments/query strings, compare Confluence page IDs from `/pages/<id>/...`, and accept equivalent canonical or copied URLs for the same page.
- Calendar `list` output is useful for event IDs and start times. Use `get` for candidate events so descriptions can be inspected.
- Prefer the earliest future event whose description contains the meeting doc link.
- Title matching is only a fallback when no future event description contains the doc link.
- If conflicting calendar evidence would create the wrong dated section, create `Next` or refuse rather than inventing a date.

## Body Creation Rules

For template docs, copy the template body as storage HTML. Do not copy explanatory template labels that are outside the reusable body.

For top templates stored in Confluence note/info blocks:

- Treat ADF panels such as `<ac:adf-extension>` with a note/info `panel-type` as possible top templates when they clearly label themselves as an agenda, template, format guide, or copyable section.
- Copy reusable children from `<ac:adf-content>` only. Do not copy `ac:adf-extension`, `ac:adf-node`, `ac:adf-fallback`, rendered fallback HTML, or any panel wrapper into the new section.
- For legacy note/info macros, copy reusable children from the macro body only. Do not copy the macro wrapper.
- If the panel/macro body starts with an H1 that is just the template label, such as `Agenda` or `Agenda (30 min)`, omit that heading from the new section. Never insert an extra top-level H1 inside the new meeting section; if a non-template H1 appears necessary to preserve meaning, refuse rather than breaking section boundaries.
- Static H1 headings above the note/info template, such as goals or quick-reference sections, are preamble. Ignore them for meeting-section detection and place the new section after the whole template block, not above it.

For bullet docs without a template, use:

```html
<ul><li><p /></li></ul>
```

For table docs without a template:

- Clone from the most recent prior meeting instance, not from arbitrary page tables or static preamble tables.
- Preserve header rows, column order, row order, people/name/owner cells, Confluence user mentions, and visible person names.
- Empty agenda, notes, discussion, topic, status, update, and action-item cells.
- Use an empty paragraph such as `<p />` for emptied cells when the cell would otherwise be blank.
- Refuse when the table has multiple plausible person columns, nested tables, merged cells that make blanking unsafe, or multiple tables with no clear primary meeting table.

## Safety Validation

Before writing, compute the exact insertion range in the original HTML. Then compare before and after content:

- Prefix before the insertion range must be byte-for-byte identical.
- Suffix after the insertion range must be byte-for-byte identical.
- All new heading and body content must be inside the insertion range.
- Page title, template, preamble, existing sections, and unrelated tables must not change.
- Re-fetch the page immediately before `update-page`; if latest storage HTML no longer matches the original outside the insertion range, do not write.

After writing, fetch the page again with `read-page --html`. Verify the live HTML equals the intended after-HTML. If Confluence normalizes storage HTML, compare again using the same insertion-range confinement check and report any unexpected normalization.

## Refusal Cases

Refuse or stop without writing when:

- The page is not a Confluence page.
- Raw storage HTML cannot be fetched.
- `Next` already exists.
- The matching dated section already exists.
- Multiple `Next` sections or duplicate future date sections make the page convention ambiguous.
- Calendar lookup is ambiguous and creating `Next` would conflict with an existing convention.
- The top template cannot be distinguished from real notes.
- The insertion point is ambiguous.
- A non-template table layout cannot be cloned while preserving people/name cells and emptying content cells.
- The proposed diff touches content outside the intended insertion range.

When refusing, explain the specific ambiguity and suggest adding a clear `Next` section, a top template, or a unique meeting doc link in the calendar event description.
