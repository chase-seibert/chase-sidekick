"""Output file manager - handles writing command output with metadata."""

import os
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


class OutputManager:
    """Manages output files with prompt metadata and auto-generated filenames."""

    def __init__(self, base_dir: str = None):
        """Initialize output manager.

        Args:
            base_dir: Base directory for output files (defaults to project_root/output)
        """
        if base_dir is None:
            # Default to output/ in project root (2 levels up from this file)
            base_dir = Path(__file__).parent.parent.parent / "output"
        self.base_dir = Path(base_dir)

    def generate_slug(self, prompt: str, max_length: int = 50) -> str:
        """Generate a slug filename from a prompt.

        Args:
            prompt: The prompt text
            max_length: Maximum length for the slug

        Returns:
            Slug string suitable for filename

        Examples:
            "Find roadmap items nested under PROJ-1735" -> "proj-1735-roadmap-items"
            "Show me the hierarchy for PROJ-500" -> "proj-500-hierarchy"
        """
        # Extract key identifiers (issue keys, numbers) before lowercasing
        issue_keys = re.findall(r'\b[A-Z]+-\d+\b', prompt, re.IGNORECASE)
        numbers = re.findall(r'\b\d+\b', prompt)

        # Convert to lowercase
        slug = prompt.lower()

        # Remove issue keys from slug to avoid duplication (we'll add them back first)
        for key in issue_keys:
            slug = slug.replace(key.lower(), '')

        # Remove special characters, keep alphanumeric, spaces, hyphens
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)

        # Replace spaces with hyphens
        slug = re.sub(r'\s+', '-', slug)

        # Remove common words
        common_words = ['the', 'in', 'for', 'and', 'or', 'a', 'an', 'to', 'of', 'me', 'my']
        parts = slug.split('-')
        parts = [p for p in parts if p not in common_words and len(p) > 1]

        # Prioritize issue keys and important terms
        important_parts = []
        issue_keys_lower = [k.lower() for k in issue_keys]

        if issue_keys_lower:
            important_parts.extend(issue_keys_lower)

        # Add remaining parts (excluding issue keys to avoid duplication)
        remaining = [p for p in parts if p not in issue_keys_lower]
        important_parts.extend(remaining[:5])  # Limit to 5 additional parts

        # Remove duplicates while preserving order
        seen = set()
        important_parts = [p for p in important_parts if not (p in seen or seen.add(p))]

        # Join and truncate
        slug = '-'.join(important_parts)
        slug = slug[:max_length]

        # Clean up any trailing hyphens
        slug = slug.strip('-')

        return slug if slug else 'output'

    def format_output(
        self,
        prompt: str,
        client: str,
        command: str,
        content: str,
        existing_created: Optional[str] = None
    ) -> str:
        """Format output with metadata header.

        Args:
            prompt: The original prompt text
            client: Client name (e.g., 'jira', 'slack')
            command: Command that was executed
            content: The actual output content
            existing_created: Creation timestamp from existing file (if refreshing)

        Returns:
            Formatted output string with YAML frontmatter
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        header = "---\n"
        header += f"prompt: {prompt}\n"
        header += f"client: {client}\n"
        header += f"command: {command}\n"
        header += f"created: {existing_created or now}\n"
        header += f"updated: {now}\n"
        header += "---\n\n"

        return header + content

    def parse_metadata(self, file_path: Path) -> dict:
        """Parse metadata from an existing output file.

        Args:
            file_path: Path to the output file

        Returns:
            Dict with metadata fields (prompt, client, command, created, updated)
        """
        if not file_path.exists():
            return {}

        metadata = {}
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Check for YAML frontmatter
            if content.startswith('---\n'):
                end_idx = content.find('\n---\n', 4)
                if end_idx != -1:
                    frontmatter = content[4:end_idx]
                    for line in frontmatter.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            metadata[key.strip()] = value.strip()
        except Exception:
            pass

        return metadata

    def write_output(
        self,
        prompt: str,
        client: str,
        command: str,
        content: str,
        filename: Optional[str] = None,
        refresh: bool = False
    ) -> Path:
        """Write output to file with metadata.

        Args:
            prompt: The original prompt text
            client: Client name (e.g., 'jira', 'slack')
            command: Command that was executed
            content: The actual output content
            filename: Optional custom filename (without .txt extension)
            refresh: If True, preserve creation timestamp from existing file

        Returns:
            Path to the written file
        """
        # Generate filename if not provided
        if filename is None:
            slug = self.generate_slug(prompt)
            filename = f"{slug}.txt"
        elif not filename.endswith('.txt'):
            filename = f"{filename}.txt"

        # Create client directory
        client_dir = self.base_dir / client
        client_dir.mkdir(parents=True, exist_ok=True)

        file_path = client_dir / filename

        # If refreshing, try to preserve creation timestamp
        existing_created = None
        if refresh and file_path.exists():
            metadata = self.parse_metadata(file_path)
            existing_created = metadata.get('created')

        # Format and write output
        formatted_output = self.format_output(
            prompt=prompt,
            client=client,
            command=command,
            content=content,
            existing_created=existing_created
        )

        with open(file_path, 'w') as f:
            f.write(formatted_output)

        return file_path

    def find_by_prompt(self, client: str, search_text: str) -> list:
        """Find output files by searching prompt text.

        Args:
            client: Client name to search within
            search_text: Text to search for in prompts

        Returns:
            List of file paths matching the search
        """
        client_dir = self.base_dir / client
        if not client_dir.exists():
            return []

        matches = []
        search_lower = search_text.lower()

        for file_path in client_dir.glob('*.txt'):
            metadata = self.parse_metadata(file_path)
            prompt = metadata.get('prompt', '').lower()
            if search_lower in prompt:
                matches.append(file_path)

        return matches

    def list_outputs(self, client: str) -> list:
        """List all output files for a client.

        Args:
            client: Client name

        Returns:
            List of tuples (file_path, metadata_dict)
        """
        client_dir = self.base_dir / client
        if not client_dir.exists():
            return []

        outputs = []
        for file_path in sorted(client_dir.glob('*.txt'), key=lambda p: p.stat().st_mtime, reverse=True):
            metadata = self.parse_metadata(file_path)
            outputs.append((file_path, metadata))

        return outputs


def main():
    """CLI entry point for output manager.

    Usage:
        # Write output with auto-generated filename
        echo "content" | python -m sidekick.clients.output write "prompt text" jira "command"

        # Write with custom filename
        echo "content" | python -m sidekick.clients.output write "prompt text" jira "command" custom-name

        # Refresh existing file (preserve creation timestamp)
        echo "content" | python -m sidekick.clients.output write "prompt text" jira "command" --refresh

        # List outputs for a client
        python -m sidekick.clients.output list jira

        # Find outputs by prompt text
        python -m sidekick.clients.output find jira "PROJ-1735"

        # Generate slug from prompt (for testing)
        python -m sidekick.clients.output slug "Find roadmap items nested under PROJ-1735"
    """
    if len(sys.argv) < 2:
        print("Usage: python -m sidekick.clients.output <command> [args...]")
        print("\nCommands:")
        print("  write <prompt> <client> <command> [filename] [--refresh]")
        print("  list <client>")
        print("  find <client> <search-text>")
        print("  slug <prompt>")
        sys.exit(1)

    manager = OutputManager()
    command = sys.argv[1]

    try:
        if command == "write":
            prompt = sys.argv[2]
            client = sys.argv[3]
            cmd = sys.argv[4]
            filename = None
            refresh = False

            # Parse optional arguments
            for arg in sys.argv[5:]:
                if arg == "--refresh":
                    refresh = True
                elif filename is None:
                    filename = arg

            # Read content from stdin
            content = sys.stdin.read()

            file_path = manager.write_output(
                prompt=prompt,
                client=client,
                command=cmd,
                content=content,
                filename=filename,
                refresh=refresh
            )
            print(f"Output written to: {file_path}")

        elif command == "list":
            client = sys.argv[2]
            outputs = manager.list_outputs(client)

            if not outputs:
                print(f"No outputs found for {client}")
            else:
                print(f"Outputs for {client} ({len(outputs)} files):\n")
                for file_path, metadata in outputs:
                    prompt = metadata.get('prompt', 'Unknown')
                    updated = metadata.get('updated', 'Unknown')
                    print(f"{file_path.name}")
                    print(f"  Prompt: {prompt}")
                    print(f"  Updated: {updated}")
                    print()

        elif command == "find":
            client = sys.argv[2]
            search_text = sys.argv[3]
            matches = manager.find_by_prompt(client, search_text)

            if not matches:
                print(f"No matches found for '{search_text}' in {client}")
            else:
                print(f"Found {len(matches)} matches:\n")
                for file_path in matches:
                    metadata = manager.parse_metadata(file_path)
                    prompt = metadata.get('prompt', 'Unknown')
                    print(f"{file_path.name}")
                    print(f"  Prompt: {prompt}")
                    print()

        elif command == "slug":
            prompt = sys.argv[2]
            slug = manager.generate_slug(prompt)
            print(slug)

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except IndexError:
        print("Error: Missing required arguments")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
