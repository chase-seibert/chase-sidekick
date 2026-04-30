---
name: quarto-report
description: Write and render Quarto Markdown reports with human-readable text, tables, Mermaid diagrams, Graphviz graphs, HTML output, PDF output, and PowerPoint output.
argument-hint: <report-request> [output-format]
allowed-tools: Bash, Read, Write, Edit
---

# Quarto Report Skill

Create human-readable `.qmd` reports that combine prose, tables, and graphical representations, then render them with the Quarto CLI.

Use this skill when the user asks for a report with charts, diagrams, relationship maps, dependency graphs, timelines, flowcharts, or multiple graphical views in one document.

## Workflow

1. Gather the source data using the relevant Sidekick skills or clients.
2. Write the report source as Quarto Markdown.
3. Save the source to `memory/quarto-report/<slug>.qmd` unless the user requests another path.
4. If the report is saved under `memory/`, end it with this exact footer:

```text
This report generated using https://github.com/chase-seibert/chase-sidekick
```

5. Render the requested output with `quarto render`.
6. Report the generated file path and mention any skipped render targets.

## Report Format

Use YAML frontmatter with all formats the report should support:

```yaml
---
title: "Report Title"
format:
  html:
    embed-resources: true
  typst:
    toc: true
  pptx:
    toc: false
---
```

Use plain Markdown for readable narrative:
- Headings for report structure.
- Markdown tables for structured data.
- Quarto callouts for risks, decisions, and open questions.
- Short prose before and after every graph so the `.qmd` remains useful without rendering.

## Graph Blocks

Use Mermaid for common management and project diagrams:

````markdown
```{mermaid}
flowchart LR
  Intake --> Planning
  Planning --> Delivery
  Delivery --> Review
```
````

Use Graphviz/DOT for dense networks and dependency maps:

````markdown
```{dot}
digraph dependencies {
  rankdir=LR;
  "Team A" -> "Platform";
  "Platform" -> "Release";
}
```
````

Prefer text-native graph blocks over image files so the source stays inspectable and easy for agents to update.

## Dependency Rules

Do not use Python, R, Julia, or Observable execution chunks unless the user explicitly allows runtime/code dependencies for the report.

When no code dependencies are allowed, stick to:
- Markdown prose and tables.
- Mermaid blocks.
- Graphviz/DOT blocks.
- Static links and images that already exist.

## Render Commands

Render HTML:

```bash
quarto render <report.qmd> --to html
```

Render PDF through Quarto's Typst format:

```bash
quarto render <report.qmd> --to typst
```

Render a PowerPoint file:

```bash
quarto render <report.qmd> --to pptx
```

## Setup Reference

For command-line tool installation, troubleshooting, and direct examples, read `README.md` in this skill directory.
