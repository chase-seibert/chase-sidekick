# Markdown Conversion Skill

Convert between markdown and other formats using pandoc.

## Overview

This skill provides a unified interface for markdown conversions:
- **Markdown → PDF**: Generate printable documentation, reports, or presentations
- **HTML → Markdown**: Extract clean markdown from web pages or HTML content

## Prerequisites

1. **pandoc** - The universal document converter
   ```bash
   brew install pandoc
   ```

2. **LaTeX distribution** (for PDF output only)
   - macOS: `brew install basictex` or download [MacTeX](https://www.tug.org/mactex/)
   - The first time you run a PDF conversion, pandoc may prompt you to install LaTeX if not present

## Usage

### Markdown to PDF

Convert a markdown file to PDF:

```bash
# Basic conversion (creates README.pdf)
python3 -m sidekick.clients.markdown to-pdf README.md

# Specify output path
python3 -m sidekick.clients.markdown to-pdf input.md output.pdf

# Use different PDF engine
python3 -m sidekick.clients.markdown to-pdf doc.md --pdf-engine=pdflatex

# Both custom output and engine
python3 -m sidekick.clients.markdown to-pdf doc.md report.pdf --pdf-engine=lualatex
```

### HTML to Markdown

Convert an HTML file to markdown:

```bash
# Basic conversion (creates page.md)
python3 -m sidekick.clients.markdown from-html page.html

# Specify output path
python3 -m sidekick.clients.markdown from-html input.html output.md

# Use GitHub-flavored markdown
python3 -m sidekick.clients.markdown from-html page.html --format=markdown_github

# Use strict markdown format
python3 -m sidekick.clients.markdown from-html page.html output.md --format=markdown_strict
```

## Python API

You can also use the converter programmatically:

```python
from sidekick.clients.markdown import MarkdownConverter

converter = MarkdownConverter()

# Markdown to PDF
output_path = converter.convert_to_pdf('README.md')
print(f"Created: {output_path}")

# HTML to Markdown
output_path = converter.convert_from_html('page.html')
print(f"Created: {output_path}")

# With custom options
pdf_path = converter.convert_to_pdf(
    'doc.md',
    output_path='report.pdf',
    pdf_engine='pdflatex'
)

md_path = converter.convert_from_html(
    'article.html',
    output_path='article.md',
    format='markdown_github'
)
```

## Markdown Format Variants

When converting HTML to markdown, choose the format that best fits your needs:

- **markdown** (default) - Standard pandoc markdown with extensions
- **markdown_github** - GitHub-flavored markdown (GFM) for README files
- **markdown_strict** - Original markdown specification only
- **markdown_mmd** - MultiMarkdown format
- **markdown_phpextra** - PHP Markdown Extra format

## PDF Engines

Different PDF engines have different capabilities:

- **xelatex** (default) - Best Unicode support, handles international characters
- **pdflatex** - Standard LaTeX, fastest processing
- **lualatex** - Lua scripting support, modern features
- **wkhtmltopdf** - WebKit-based, preserves HTML styling
- **weasyprint** - Python-based, CSS support

## Common Use Cases

### Convert Web Content to Markdown

```bash
# Download HTML and convert to markdown
curl https://example.com/article.html -o article.html
python3 -m sidekick.clients.markdown from-html article.html article.md --format=markdown_github
```

### Generate PDF Documentation

```bash
python3 -m sidekick.clients.markdown to-pdf ARCHITECTURE.md docs/architecture.pdf
```

### Process Multiple Files

```bash
# Convert all markdown files to PDF
for file in docs/*.md; do
    python3 -m sidekick.clients.markdown to-pdf "$file"
done

# Convert all HTML files to markdown
for file in pages/*.html; do
    python3 -m sidekick.clients.markdown from-html "$file" --format=markdown_github
done
```

## Markdown Features

Pandoc supports extended markdown features that work well in PDF output:

- **Headers** - Document structure with # ## ### etc.
- **Lists** - Bullet points and numbered lists
- **Code blocks** - Syntax-highlighted code with ```language
- **Tables** - Markdown tables
- **Links** - Hyperlinks (converted to blue underlined text in PDF)
- **Images** - Embedded images ![alt](path/to/image.png)
- **Emphasis** - *italic* and **bold** text
- **Blockquotes** - > quoted text
- **Math** - LaTeX math expressions with $inline$ and $$display$$

## Troubleshooting

### "pandoc not found"

Install pandoc:
```bash
brew install pandoc
```

### "pdflatex not found"

Install a LaTeX distribution:
```bash
brew install basictex
# After installation, update the PATH:
eval "$(/usr/libexec/path_helper)"
```

### HTML Conversion Issues

If HTML conversion produces unexpected results:
- Try different markdown formats (markdown_github, markdown_strict)
- Clean up the HTML source before conversion
- Use pandoc directly with additional filters: `pandoc -f html -t markdown --extract-media=media page.html -o output.md`

### Unicode Characters Not Rendering in PDF

Use XeLaTeX engine (the default) which has better Unicode support:
```bash
python3 -m sidekick.clients.markdown to-pdf doc.md --pdf-engine=xelatex
```

### Images Not Appearing in PDF

Ensure image paths in markdown are relative to the markdown file location, or use absolute paths.

## Advanced Pandoc Options

For more control, you can call pandoc directly with additional options:

```bash
# Custom margins
pandoc input.md -o output.pdf -V geometry:margin=1in

# Custom font
pandoc input.md -o output.pdf -V mainfont="Arial"

# Table of contents
pandoc input.md -o output.pdf --toc

# Number sections
pandoc input.md -o output.pdf --number-sections

# Extract media from HTML
pandoc -f html -t markdown --extract-media=./media page.html -o output.md
```

See the [pandoc manual](https://pandoc.org/MANUAL.html) for all available options.

## Design Philosophy

This skill follows the project design principles:

- **Zero Dependencies** - Uses only Python stdlib, shells out to pandoc
- **Single-File Client** - All logic in one file: `sidekick/clients/markdown.py`
- **CLI Built-In** - Direct command-line usage via `python3 -m`
- **Simple Config** - No configuration files needed

## Backward Compatibility

The old markdown-pdf module path still works:
```python
# Old import (still works)
from sidekick.clients.markdown_pdf import MarkdownPdfConverter

# New import (recommended)
from sidekick.clients.markdown import MarkdownConverter
```

The old CLI usage also works:
```bash
# Old usage (still works)
python3 -m sidekick.clients.markdown README.md

# New usage (recommended)
python3 -m sidekick.clients.markdown to-pdf README.md
```

## Related Skills

- **confluence** - For converting Confluence pages to PDF
- **dropbox** - For accessing markdown files from Dropbox Paper
- **chrome** - For accessing HTML from browser history
