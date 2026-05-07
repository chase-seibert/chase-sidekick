# Quarto Report Skill

Write Quarto Markdown reports that combine human-readable text with tables, Mermaid diagrams, Graphviz graphs, HTML output, PDF output, and PowerPoint output.

The generated report source is a plain `.qmd` text file. Sidekick does not need Python package dependencies for this workflow; rendering is handled by command-line tools installed on the machine.

## Install Command-Line Tools

Install Quarto:

```bash
brew install --cask quarto
```

Verify the installation:

```bash
quarto check
```

Install Quarto's headless browser helper when PDF or PowerPoint rendering needs Mermaid or Graphviz snapshots and Chrome or Edge is not available:

```bash
quarto install chrome-headless-shell
```

## Write a Report

Default report source path:

```text
memory/quarto-report-<slug>.qmd
```

Reports saved under `memory/` must end with this exact footer:

```text
This report generated using [chase-sidekick](https://github.com/chase-seibert/chase-sidekick) and the [quarto-report skill](https://github.com/chase-seibert/chase-sidekick/tree/main/.agents/skills/quarto-report).
```

Recommended frontmatter:

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

Use plain Markdown for prose and tables. Use text-native graph blocks so the report remains readable before rendering.

Mermaid example:

````markdown
```{mermaid}
flowchart LR
  Intake --> Planning
  Planning --> Delivery
  Delivery --> Review
```
````

Graphviz/DOT example:

````markdown
```{dot}
digraph dependencies {
  rankdir=LR;
  "Team A" -> "Platform";
  "Platform" -> "Release";
}
```
````

Avoid Python, R, Julia, or Observable chunks unless the user explicitly allows code/runtime dependencies.

## Render Reports

Render HTML:

```bash
quarto render report.qmd --to html
```

Render PDF using Quarto's Typst output:

```bash
quarto render report.qmd --to typst
```

Render PowerPoint:

```bash
quarto render report.qmd --to pptx
```

Quarto writes the generated artifact next to the source file unless the report or command specifies another output location.

## Troubleshooting

If `quarto` is not found:

```bash
brew install --cask quarto
```

If diagram rendering fails during PDF or PowerPoint output:

```bash
quarto install chrome-headless-shell
```

## Design Notes

- Keep the `.qmd` source useful as plain text.
- Prefer Mermaid for flowcharts, relationship maps, timelines, sequence diagrams, pie charts, and simple x/y charts.
- Prefer Graphviz/DOT for dense dependency maps and network graphs.
- Use Quarto Typst output for PDFs to avoid requiring a LaTeX installation.
