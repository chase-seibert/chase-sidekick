# Markdown to PDF Skill

Convert markdown files to PDF using pandoc.

## Overview

This skill provides a simple interface to convert markdown files to PDF format using pandoc. It's useful for generating printable documentation, reports, or presentations from markdown source files.

## Prerequisites

1. **pandoc** - The universal document converter
   ```bash
   brew install pandoc
   ```

2. **LaTeX distribution** (for PDF output)
   - macOS: `brew install basictex` or download [MacTeX](https://www.tug.org/mactex/)
   - The first time you run a PDF conversion, pandoc may prompt you to install LaTeX if not present

## Usage

### Basic Conversion

Convert a markdown file to PDF with the same name:

```bash
python -m sidekick.clients.markdown_pdf README.md
```

This creates `README.pdf` in the same directory.

### Specify Output Path

```bash
python -m sidekick.clients.markdown_pdf input.md output.pdf
```

### Choose PDF Engine

Different PDF engines have different capabilities:

```bash
# XeLaTeX (default) - Best Unicode support
python -m sidekick.clients.markdown_pdf doc.md --pdf-engine=xelatex

# PDFLaTeX - Standard LaTeX
python -m sidekick.clients.markdown_pdf doc.md --pdf-engine=pdflatex

# LuaLaTeX - Lua scripting support
python -m sidekick.clients.markdown_pdf doc.md --pdf-engine=lualatex
```

## Python API

You can also use the converter programmatically:

```python
from sidekick.clients.markdown_pdf import MarkdownPdfConverter

converter = MarkdownPdfConverter()

# Basic conversion
output_path = converter.convert('README.md')
print(f"Created: {output_path}")

# With custom output and engine
output_path = converter.convert(
    'doc.md',
    output_path='report.pdf',
    pdf_engine='pdflatex'
)
```

## Common Use Cases

### Convert Project Documentation

```bash
python -m sidekick.clients.markdown_pdf ARCHITECTURE.md docs/architecture.pdf
```

### Generate Reports

```bash
python -m sidekick.clients.markdown_pdf weekly-report.md reports/$(date +%Y-%m-%d).pdf
```

### Batch Convert Multiple Files

```bash
for file in docs/*.md; do
    python -m sidekick.clients.markdown_pdf "$file"
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

### Unicode Characters Not Rendering

Use XeLaTeX engine (the default) which has better Unicode support:
```bash
python -m sidekick.clients.markdown_pdf doc.md --pdf-engine=xelatex
```

### Images Not Appearing

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
```

See the [pandoc manual](https://pandoc.org/MANUAL.html) for all available options.

## Design Philosophy

This skill follows the Chase Sidekick design principles:

- **Zero Dependencies** - Uses only Python stdlib, shells out to pandoc
- **Single-File Client** - All logic in one file: `sidekick/clients/markdown_pdf.py`
- **CLI Built-In** - Direct command-line usage via `python -m`
- **Simple Config** - No configuration files needed

## Related Skills

- **confluence** - For converting Confluence pages to PDF
- **dropbox** - For accessing markdown files from Dropbox Paper
- **output** - For managing PDF output files with metadata
