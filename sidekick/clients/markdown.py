"""Markdown converter using pandoc."""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Optional


class MarkdownConverter:
    """Convert between markdown and other formats using pandoc."""

    def __init__(self):
        """Initialize converter and check dependencies."""
        # Check pandoc is available
        if not shutil.which('pandoc'):
            raise RuntimeError(
                "pandoc not found. Install with: brew install pandoc"
            )

        # Check tidy is available (optional but recommended)
        self.tidy_available = shutil.which('tidy') is not None
        if not self.tidy_available:
            print("Warning: tidy-html5 not found. Install with: brew install tidy-html5",
                  file=sys.stderr)
            print("HTML cleaning will be skipped.", file=sys.stderr)

    def convert_to_pdf(
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

    def convert_from_html(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        format: str = 'markdown'
    ) -> str:
        """Convert HTML file to markdown using pandoc.

        Args:
            input_path: Path to input HTML file
            output_path: Path to output markdown file (auto-generated if None)
            format: Markdown format variant (markdown, markdown_github, markdown_strict, etc.)

        Returns:
            Path to the generated markdown file

        Raises:
            FileNotFoundError: If input file doesn't exist
            RuntimeError: If conversion fails
            ValueError: If invalid format specified
        """
        # Validate input file
        input_file = Path(input_path)
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Validate format
        valid_formats = ['markdown', 'markdown_github', 'markdown_strict',
                        'markdown_mmd', 'markdown_phpextra']
        if format not in valid_formats:
            raise ValueError(
                f"Invalid format: {format}. Valid formats: {', '.join(valid_formats)}"
            )

        # Generate output path if not provided
        if output_path is None:
            output_path = str(input_file.with_suffix('.md'))

        # Build pandoc command
        cmd = [
            'pandoc',
            '-f', 'html',
            '-t', format,
            input_path,
            '-o', output_path
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

    def convert_html_to_markdown(
        self,
        html_content: str,
        format: str = 'markdown',
        clean_html: bool = True
    ) -> str:
        """Convert HTML string to markdown string in-memory using pandoc.

        Uses stdin/stdout for efficient in-memory conversion without temp files.
        Optionally cleans HTML with tidy-html5 before conversion for better output.
        Handles large files by truncating to first ~10MB before processing.

        Args:
            html_content: HTML content as string
            format: Markdown format variant (markdown, markdown_github, markdown_strict,
                    markdown_mmd, markdown_phpextra)
            clean_html: If True and tidy is available, clean HTML before conversion

        Returns:
            Markdown content as string

        Raises:
            RuntimeError: If pandoc conversion fails
            ValueError: If invalid format specified
        """
        # Validate format
        valid_formats = ['markdown', 'markdown_github', 'markdown_strict',
                        'markdown_mmd', 'markdown_phpextra']
        if format not in valid_formats:
            raise ValueError(
                f"Invalid format: {format}. Valid formats: {', '.join(valid_formats)}"
            )

        # Handle large files by truncating to first ~10MB
        MAX_SIZE = 10 * 1024 * 1024  # 10MB
        if len(html_content.encode('utf-8')) > MAX_SIZE:
            # Truncate to first 10MB worth of characters (approximate)
            char_limit = MAX_SIZE // 2  # Rough estimate for UTF-8
            html_content = html_content[:char_limit]
            # Try to close at a tag boundary to avoid breaking HTML
            last_close = html_content.rfind('>')
            if last_close > char_limit - 1000:  # Within last 1000 chars
                html_content = html_content[:last_close + 1]

        # Clean HTML with tidy if available and requested
        if clean_html and self.tidy_available:
            tidy_cmd = [
                'tidy',
                '-q',  # Quiet mode
                '--show-warnings', 'no',  # Suppress warnings
                '--show-errors', '0',  # Suppress errors
                '--force-output', 'yes',  # Output even if errors
                '--wrap', '0',  # No line wrapping
                '--drop-empty-elements', 'no',  # Keep structure
                '-ashtml',  # Treat as HTML
                '-utf8'  # UTF-8 encoding
            ]

            try:
                tidy_result = subprocess.run(
                    tidy_cmd,
                    input=html_content.encode('utf-8'),
                    capture_output=True,
                    check=False  # Tidy returns non-zero even on success
                )
                # Use cleaned output if successful
                if tidy_result.stdout:
                    html_content = tidy_result.stdout.decode('utf-8')
            except Exception:
                # If tidy fails, continue with original HTML
                pass

        # Build pandoc command
        cmd = [
            'pandoc',
            '-f', 'html',
            '-t', format
        ]

        try:
            result = subprocess.run(
                cmd,
                input=html_content.encode('utf-8'),
                capture_output=True,
                check=True
            )
            return result.stdout.decode('utf-8')
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Pandoc conversion failed:\n{e.stderr.decode('utf-8')}\n\n"
                f"Command: {' '.join(cmd)}"
            )

    def convert(self, *args, **kwargs) -> str:
        """Backward compatibility alias for convert_to_pdf."""
        return self.convert_to_pdf(*args, **kwargs)


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 -m sidekick.clients.markdown <command> [args]")
        print("")
        print("Commands:")
        print("  to-pdf <input.md> [output.pdf] [--pdf-engine=ENGINE]")
        print("  from-html <input.html> [output.md] [--format=FORMAT]")
        print("")
        print("Examples:")
        print("  python3 -m sidekick.clients.markdown to-pdf README.md")
        print("  python3 -m sidekick.clients.markdown from-html page.html")
        print("  python3 -m sidekick.clients.markdown from-html page.html output.md --format=markdown_github")
        sys.exit(1)

    command = sys.argv[1]

    # Backward compatibility: if first arg is .md file, assume to-pdf
    if command.endswith('.md') and not command.startswith('--'):
        command = 'to-pdf'
        args_start = 1
    else:
        args_start = 2

    try:
        converter = MarkdownConverter()

        if command == 'to-pdf':
            if len(sys.argv) < args_start + 1:
                print("Error: to-pdf requires input file", file=sys.stderr)
                sys.exit(1)

            input_path = sys.argv[args_start]
            output_path = None
            pdf_engine = 'xelatex'

            # Parse arguments
            for arg in sys.argv[args_start + 1:]:
                if arg.startswith('--pdf-engine='):
                    pdf_engine = arg.split('=', 1)[1]
                elif not arg.startswith('--'):
                    output_path = arg

            output = converter.convert_to_pdf(input_path, output_path, pdf_engine)
            print(f"✓ PDF created: {output}")

            # Reveal in Finder on macOS
            if sys.platform == 'darwin':
                subprocess.run(['open', '-R', output], check=False)

        elif command == 'from-html':
            if len(sys.argv) < args_start + 1:
                print("Error: from-html requires input file", file=sys.stderr)
                sys.exit(1)

            input_path = sys.argv[args_start]
            output_path = None
            format = 'markdown'

            # Parse arguments
            for arg in sys.argv[args_start + 1:]:
                if arg.startswith('--format='):
                    format = arg.split('=', 1)[1]
                elif not arg.startswith('--'):
                    output_path = arg

            output = converter.convert_from_html(input_path, output_path, format)
            print(f"✓ Markdown created: {output}")

            # Reveal in Finder on macOS
            if sys.platform == 'darwin':
                subprocess.run(['open', '-R', output], check=False)

        else:
            print(f"Error: Unknown command '{command}'", file=sys.stderr)
            print("Use 'python3 -m sidekick.clients.markdown' for usage", file=sys.stderr)
            sys.exit(1)

    except (FileNotFoundError, RuntimeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
