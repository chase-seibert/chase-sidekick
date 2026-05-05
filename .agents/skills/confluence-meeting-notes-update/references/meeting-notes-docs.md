# Confluence Meeting Notes Document Shapes

Read this reference when working with Confluence 1:1 or recurring meeting notes. Use raw Confluence storage HTML for writes; Markdown is only for human orientation.

## Sections

- Meeting docs use top-level H1 sections. A section starts after its `<h1>` and ends before the next top-level `<h1>` or the end of the document.
- The future agenda section may be named `Next`.
- Dated sections may use visible text such as `Apr 23, 2026`, or a Confluence date object:

```html
<h1><time datetime="2026-04-30" /></h1>
```

- When creating a dated section, prefer the Confluence date object form. If the next meeting date cannot be found confidently, use `Next`.
- Static preamble content can appear before meeting sections. Do not treat obvious owner/context/link/setup content as a meeting instance.
- In bullet-format sections, an image or embedded media block on the page does not end the section. Treat it as part of the same section, and continue scanning after it because bullets may resume below the image.
- If the section order is ambiguous, prefer the smallest safe edit and refuse rather than moving unrelated content.

## Top Templates

Some meeting docs have a template at the top that defines the format of each new meeting section.

- Treat a top template as present only when the top content clearly labels itself as a template, format guide, agenda template, or "copy this" section/block.
- A template may be an H1 section, a paragraph/list/table block before the first dated or `Next` section, or a Confluence macro whose purpose is clearly to describe new-section format.
- The template is static context, not a meeting instance. Do not update it as the current meeting section.
- When creating a new meeting section and a clear template exists, copy the template body into the new section exactly enough to preserve its structure. Do not copy the template heading itself into the new dated or `Next` section.
- If top content could be either a template or real notes, do not silently treat it as a template.

## Calendar Matching

When a meeting doc link is available, the authoritative way to find the next dated instance is to match that doc link in future calendar event descriptions.

- Search future calendar events, then fetch event details as needed so descriptions can be inspected.
- Prefer events whose description body contains the meeting doc link.
- Normalize links where practical: HTML-decode, URL-decode, strip fragments/query strings, compare Confluence page IDs from `/pages/<id>/...`, and accept equivalent canonical or copied Confluence URLs for the same page.
- If multiple future events contain the doc link, choose the earliest future start time.
- Only fall back to event title, supplied meeting title, or Confluence page title matching when no event description contains the doc link.
- If no confident date is found, use `Next`. If calendar evidence conflicts with existing page conventions, refuse or use `Next` rather than inventing a date.

## Format Detection

Inspect the chosen meeting section body in raw HTML.

- If the first meaningful top-level structure is `<table>`, treat it as table format.
- If the first meaningful top-level structure is `<ul>` or `<ol>`, treat it as bullet format.
- If the section is empty, default to bullet format unless the user explicitly asks for a table row.
- Ignore lists nested inside a table when deciding whether the section itself is table or bullet format.

## Bullet Format

Bullet-format sections keep agenda items in the first top-level list.

- Append agenda items as list items, for example `<li><p>Agenda item text</p></li>`.
- If a target section has no list, create a top-level `<ul>` at the start of the section body.
- For a newly created non-template bullet section, use a single empty bullet.

## Table Format

Table-format docs often have one row per person or one row per agenda/demo item.

- Header rows and header text are structural and should be preserved.
- Person/name/owner cells may contain text, email addresses, or Confluence mentions such as `<ri:user ri:account-id="...">`; preserve those cells when cloning a table shape.
- Agenda-like content cells usually have headers such as `Agenda`, `Topic`, `Top of mind`, `Discussion`, `Notes`, or `Item`.
- When creating a new table section without a template, clone the table shape from the most recent prior meeting instance. Preserve headers, row count, row order, people/name cells, and mentions. Empty the other content cells.
- If the latest instance has multiple tables, nested tables, merged cells, or unclear person/content columns, refuse instead of cloning the wrong structure.

## Insertion Point

New meeting sections should appear before historical dated sections and after static preamble or template content when that boundary is clear.

- If an existing `Next` section is present, do not create another.
- If a confident next date is known and that date section already exists, do not create another.
- If placement would require moving unrelated content, refuse.
