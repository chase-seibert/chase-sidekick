"""Markdown to PDF converter using pandoc."""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Optional


class MarkdownPdfConverter:
    """Convert markdown files to PDF using pandoc."""

    def __init__(self):
        """Initialize converter."""
        if not shutil.which('pandoc'):
            raise RuntimeError(
                "pandoc not found. Install with: brew install pandoc"
            )

    def convert(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        pdf_engine: str = 'xelatex'
    ) -> str:
        """Convert markdown file to PDF using pandoc.

        Args:
            input_path: Path to input markdown file
            output_path: Path to output PDF file (auto-generated if None)
            pdf_engine: PDF engine to use (xelatex, pdflatex, lualatex, etc.)

        Returns:
            Path to the generated PDF file

        Raises:
            FileNotFoundError: If input file doesn't exist
            RuntimeError: If conversion fails
        """
        # Validate input file
        input_file = Path(input_path)
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Generate output path if not provided
        if output_path is None:
            output_path = str(input_file.with_suffix('.pdf'))

        # Build pandoc command
        cmd = [
            'pandoc',
            input_path,
            '-o', output_path,
            f'--pdf-engine={pdf_engine}'
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Pandoc conversion failed:\n{e.stderr}\n\n"
                f"Command: {' '.join(cmd)}"
            )

        return output_path


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m sidekick.clients.markdown_pdf <input.md> [output.pdf] [--pdf-engine=ENGINE]")
        print("")
        print("Examples:")
        print("  python -m sidekick.clients.markdown_pdf README.md")
        print("  python -m sidekick.clients.markdown_pdf doc.md output.pdf")
        print("  python -m sidekick.clients.markdown_pdf doc.md --pdf-engine=pdflatex")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = None
    pdf_engine = 'xelatex'

    # Parse arguments
    for arg in sys.argv[2:]:
        if arg.startswith('--pdf-engine='):
            pdf_engine = arg.split('=', 1)[1]
        elif not arg.startswith('--'):
            output_path = arg

    try:
        converter = MarkdownPdfConverter()
        output = converter.convert(input_path, output_path, pdf_engine)
        print(f"✓ PDF created: {output}")

        # Reveal in Finder on macOS
        if sys.platform == 'darwin':
            subprocess.run(['open', '-R', output], check=False)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
