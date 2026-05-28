# Confluence Meeting Notes Document Shapes

Read this reference when working with Confluence 1:1 or recurring meeting notes. Use Atlassian Rovo MCP ADF for reads and writes; Markdown is only for human orientation. Use raw Confluence storage HTML only as a fallback when Rovo is unavailable.

## Sections

- Meeting docs use real top-level H1 meeting sections. In ADF, a section starts after a top-level `heading` node with `attrs.level == 1` and ends before the next real top-level H1 or the end of the document.
- Ignore headings nested inside ADF panels, tables, notes, or other non-top-level containers when identifying meeting-section boundaries.
- The future agenda section may be named `Next`.
- Dated sections may use visible text such as `Apr 23, 2026`, or an ADF date object:

```json
{"type":"heading","attrs":{"level":1},"content":[{"type":"date","attrs":{"timestamp":"1777507200000"}}]}
```

- When creating a dated section, prefer the ADF date object form using UTC-midnight milliseconds. If the next meeting date cannot be found confidently, use `Next`.
- Static preamble content can appear before meeting sections, and it may itself use H1 headings such as goals, context, quick references, links, or setup material. Do not treat those H1s as meeting instances unless the heading is `Next` or a recognizable meeting date.
- In bullet-format sections, an image or embedded media block on the page does not end the section. Treat it as part of the same section, and continue scanning after it because bullets may resume below the image.
- If the section order is ambiguous, prefer the smallest safe edit and refuse rather than moving unrelated content.

## Top Templates

Some meeting docs have a template at the top that defines the format of each new meeting section.

- Treat a top template as present only when the top content clearly labels itself as a template, format guide, agenda template, or "copy this" section/block.
- A template may be an H1 section, a paragraph/list/table block before the first dated or `Next` section, or a Confluence macro/panel whose purpose is clearly to describe new-section format.
- Confluence note/info panels can be standing agenda templates when they appear after static preamble content and before the first real meeting section, and their ADF body clearly labels itself as an agenda/template/copyable format.
- The template is static context, not a meeting instance. Do not update it as the current meeting section.
- When creating a new meeting section and a clear template exists, copy the template body ADF nodes into the new section exactly enough to preserve its structure. Do not copy the template heading itself into the new dated or `Next` section.
- For an ADF `panel` with a note/info panel type, copy reusable child nodes from the panel content only. Do not copy the surrounding panel wrapper or create a new note/info block.
- For a legacy storage-HTML fallback, copy reusable children from the macro body only. Do not copy the macro wrapper.
- If the copied panel/macro body starts with an H1 that is just the template label, such as `Agenda` or `Agenda (30 min)`, treat that first H1 as the template heading and omit it from the new section. Never insert an extra top-level H1 inside the new meeting section; if a non-template H1 appears necessary to preserve meaning, refuse instead of breaking section boundaries.
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

Inspect the chosen meeting section body in ADF.

- If the first meaningful top-level structure is a `table` node, treat it as table format.
- If the first meaningful top-level structure is a `bulletList` or `orderedList` node, treat it as bullet format.
- If the section is empty, default to bullet format unless the user explicitly asks for a table row.
- Ignore lists nested inside a table when deciding whether the section itself is table or bullet format.

## Bullet Format

Bullet-format sections keep agenda items in the first top-level list.

- Append agenda items as ADF `listItem` nodes with paragraph text.
- If a target section has exactly one empty bullet placeholder, replace that placeholder with the new agenda item.
- If a target section has no list, create a top-level `bulletList` at the start of the section body.
- For a newly created non-template bullet section, use a single empty bullet.

## AI Summary Notes

AI summary notes should be inserted as top-level ADF `panel` nodes with `attrs.panelType == "note"` inside the chosen meeting section only. Do not update preamble/template panels above the first real meeting section when adding a summary to meeting notes.

For Chrome/live-editor fallback updates, preserve the same shape as a real note
panel rather than pasting plain Markdown. In Confluence live docs, slash commands
such as `/note` or `/panel` may insert literal text instead of opening the insert
menu. A verified fallback is to paste rich HTML with a ProseMirror slice wrapper:

```html
<div data-pm-slice="0 0 []">
  <div class="ak-editor-panel" data-panel-type="note"
       data-prosemirror-content-type="node"
       data-prosemirror-node-name="panel"
       data-prosemirror-node-block="true">
    <div class="ak-editor-panel__content">
      <h2 data-prosemirror-node-name="heading">AI Notes</h2>
      <p>Summary text...</p>
    </div>
  </div>
</div>
```

Include `text/html` and `text/plain` clipboard entries, paste into the intended
blank paragraph inside the target meeting section, then verify by reloading the
browser tab and confirming the summary still appears under an `img "note panel"`
marker before the next meeting heading. For live docs, a Rovo Markdown read may
omit the live-editor note panel body even when the browser-reload verification
shows the panel persisted.

## Table Format

Table-format docs often have one row per person or one row per agenda/demo item.

- Header rows and header text are structural and should be preserved.
- Person/name/owner cells may contain text, email addresses, or ADF mention nodes; preserve those cells when cloning a table shape.
- Agenda-like content cells usually have headers such as `Agenda`, `Topic`, `Top of mind`, `Discussion`, `Notes`, or `Item`.
- When creating a new table section without a template, clone the table shape from the most recent prior meeting instance. Preserve headers, row count, row order, people/name cells, and mentions. Empty the other content cells.
- If the latest instance has multiple tables, nested tables, merged cells, or unclear person/content columns, refuse instead of cloning the wrong structure.

## Insertion Point

New meeting sections should appear before historical dated sections and after static preamble or template content when that boundary is clear.

- If an existing `Next` section is present, do not create another.
- If a confident next date is known and that date section already exists, do not create another.
- If a clear top note/info panel template appears after static preamble and before the first real dated or `Next` section, insert the new meeting section immediately after the whole template block and immediately before the first real meeting section.
- H1 static preamble sections above a clear template are not historical meeting sections and should not block this insertion point.
- If placement would require moving unrelated content, refuse.

## ADF Safety Validation

- Before writing, preserve the original top-level ADF node sequence outside the target section or insertion point.
- Immediately before `updateConfluencePage`, re-fetch ADF and stop if anything outside the intended target changed.
- After writing, fetch ADF and Markdown through Rovo. Verify existing preamble, templates, dated sections, nested bullets, and unrelated tables are unchanged.
- Confluence may add `localId` values to newly inserted nodes. Ignore those new-node `localId` differences during post-write comparison, but do not ignore structural or text changes outside the target.
- Never write meeting notes from Markdown. Markdown is lossy for dates, panels, mentions, and nested structure.
