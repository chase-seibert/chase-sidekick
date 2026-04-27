---
name: markdown
description: Convert markdown to/from other formats
argument-hint: <command> [args]
allowed-tools: Bash, Read
---

# Markdown Conversion Skill

Convert markdown to PDF and HTML to markdown using pandoc.

When invoked, use the markdown converter to handle the request: $ARGUMENTS

## Available Commands

### Convert Markdown to PDF
```bash
python3 -m sidekick.clients.markdown to-pdf <input.md> [output.pdf] [--pdf-engine=ENGINE]
```

### Convert HTML to Markdown
```bash
python3 -m sidekick.clients.markdown from-html <input.html> [output.md] [--format=FORMAT]
```

## Arguments

### to-pdf Command
- `input.md` - Path to input markdown file (required)
- `output.pdf` - Path to output PDF file (optional, defaults to input filename with .pdf extension)
- `--pdf-engine=ENGINE` - PDF engine to use (optional, defaults to xelatex)

### from-html Command
- `input.html` - Path to input HTML file (required)
- `output.md` - Path to output markdown file (optional, defaults to input filename with .md extension)
- `--format=FORMAT` - Markdown format variant (optional, defaults to markdown)

## Markdown Format Variants

- `markdown` - Default pandoc markdown
- `markdown_github` - GitHub-flavored markdown
- `markdown_strict` - Original markdown specification
- `markdown_mmd` - MultiMarkdown
- `markdown_phpextra` - PHP Markdown Extra

## PDF Engines

- `xelatex` - Default, best Unicode support
- `pdflatex` - Standard LaTeX engine
- `lualatex` - Lua-based LaTeX engine
- `wkhtmltopdf` - WebKit-based HTML to PDF
- `weasyprint` - Python-based HTML to PDF

## Example Usage

When the user asks to:
- "Convert README.md to PDF" - Use `to-pdf` with default output
- "Convert page.html to markdown" - Use `from-html` with default format
- "Convert with GitHub markdown format" - Use `from-html` with `--format=markdown_github`

## Examples

```bash
# Markdown to PDF (basic)
python3 -m sidekick.clients.markdown to-pdf README.md

# Markdown to PDF (custom output and engine)
python3 -m sidekick.clients.markdown to-pdf doc.md report.pdf --pdf-engine=pdflatex

# HTML to Markdown (basic)
python3 -m sidekick.clients.markdown from-html page.html

# HTML to Markdown (GitHub format)
python3 -m sidekick.clients.markdown from-html page.html output.md --format=markdown_github

# HTML to Markdown (strict format)
python3 -m sidekick.clients.markdown from-html article.html --format=markdown_strict
```

## Requirements

- `pandoc` must be installed: `brew install pandoc`
- For PDF output, a LaTeX distribution is also required

## Output

The tool will print the path to the generated file on success:
```
✓ PDF created: /path/to/output.pdf
✓ Markdown created: /path/to/output.md
```

## Backward Compatibility

For backward compatibility with the old markdown-pdf skill, you can still use:
```bash
python3 -m sidekick.clients.markdown README.md
```
This automatically runs the `to-pdf` command.

For full documentation, see the detailed markdown skill documentation in this folder.
