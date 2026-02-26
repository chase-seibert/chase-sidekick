"""Backward compatibility shim for markdown_pdf module.

DEPRECATED: Use sidekick.clients.markdown instead.
This module will be removed in a future version.
"""

import warnings

# Import everything from new module
from sidekick.clients.markdown import (
    MarkdownConverter as MarkdownPdfConverter,
    main
)

# Show deprecation warning
warnings.warn(
    "sidekick.clients.markdown_pdf is deprecated. "
    "Use sidekick.clients.markdown instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ['MarkdownPdfConverter', 'main']

if __name__ == "__main__":
    main()
