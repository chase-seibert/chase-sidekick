---
name: markdown-pdf
description: Convert markdown files to PDF
argument-hint: <markdown-file> [output.pdf]
allowed-tools: Bash, Read
---

# Markdown to PDF Skill

Convert markdown files to PDF using pandoc.

When invoked, use the markdown PDF converter to handle the request: $ARGUMENTS

## Available Commands

### Convert Markdown to PDF
```bash
python -m sidekick.clients.markdown_pdf <input.md> [output.pdf] [--pdf-engine=ENGINE]
```

## Arguments

- `input.md` - Path to input markdown file (required)
- `output.pdf` - Path to output PDF file (optional, defaults to input filename with .pdf extension)
- `--pdf-engine=ENGINE` - PDF engine to use (optional, defaults to xelatex)

## PDF Engines

- `xelatex` - Default, best Unicode support
- `pdflatex` - Standard LaTeX engine
- `lualatex` - Lua-based LaTeX engine
- `wkhtmltopdf` - WebKit-based HTML to PDF
- `weasyprint` - Python-based HTML to PDF

## Example Usage

When the user asks to:
- "Convert README.md to PDF" - Use default output path
- "Convert doc.md to report.pdf" - Specify custom output path
- "Convert with pdflatex" - Use --pdf-engine=pdflatex option

## Examples

```bash
# Basic conversion (creates README.pdf)
python -m sidekick.clients.markdown_pdf README.md

# Specify output file
python -m sidekick.clients.markdown_pdf doc.md report.pdf

# Use different PDF engine
python -m sidekick.clients.markdown_pdf doc.md --pdf-engine=pdflatex

# Both custom output and engine
python -m sidekick.clients.markdown_pdf doc.md report.pdf --pdf-engine=lualatex
```

## Requirements

- `pandoc` must be installed: `brew install pandoc`
- For PDF output, a LaTeX distribution is also required (pandoc will prompt if missing)

## Output

The tool will print the path to the generated PDF file on success:
```
✓ PDF created: /path/to/output.pdf
```

For full documentation, see the detailed markdown-pdf skill documentation in this folder.
