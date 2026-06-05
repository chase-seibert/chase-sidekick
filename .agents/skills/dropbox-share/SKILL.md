---
name: dropbox-share
description: Copy or publish local or Dropbox files into a Dropbox "Codex Shared" folder and return a durable Dropbox shared link. Use when Codex needs to share HTML dashboards or reports that Dropbox can render for team viewers, or to share Markdown, text files, images, PDFs, and other files through Dropbox links.
---

# Dropbox Share

## Overview

Use this skill to put a file in a Dropbox folder named `Codex Shared` and create or reuse a Dropbox shared link for that file. This is especially useful for `.html` dashboards and reports because Dropbox web links can render the page for authenticated team viewers instead of forcing a raw download.

Prefer Dropbox MCP for Dropbox operations. Use shell commands only to inspect local files or to perform a byte-preserving copy into a local Dropbox sync folder when Dropbox MCP cannot upload the file type directly.

## Workflow

1. Resolve the source file.
   - For a local path or Markdown link, resolve it relative to the current workspace and verify it exists with `ls -l` or equivalent.
   - For a Dropbox path, URL, or file ID, inspect it with Dropbox MCP before copying or linking.
   - Record the basename, byte size, and whether the content is UTF-8 text.

2. Find the destination folder.
   - Default destination is the Dropbox folder named `Codex Shared`.
   - First try a known or user-provided path only if it has been verified with `dropbox.list_folder` or `dropbox.get_file_metadata`.
   - If root lookup such as `/Codex Shared` fails in a team account, search or browse mounted namespaces. The  pattern is usually `/My Name/Codex Shared`, with an ns path such as `ns:<home_namespace>//Codex Shared`.
   - If more than one exact `Codex Shared` folder is found, ask which one to use.

3. Check for destination conflicts.
   - List the destination folder children with `recursive=false`.
   - If the destination filename already exists, ask whether to reuse the existing file/link, choose a new name, or replace it. Do not silently overwrite.

4. Summarize the mutation plan and get explicit confirmation before creating, copying, moving, deleting, or sharing through Dropbox MCP. Include source path, destination path, filename, file size, and the planned link creation.

5. Copy or create the file.
   - For Dropbox-to-Dropbox copies, use `dropbox.copy` with the source identifier and destination path. Prefer this over download-and-reupload.
   - For local UTF-8 text files up to 5 MB, including `.html`, `.md`, `.txt`, `.json`, `.csv`, `.css`, and `.js`, read the full local content and use `dropbox.create_file`.
   - For local binary files or text files that must preserve exact bytes, do not use `dropbox.create_file`. Use a byte-preserving local Dropbox sync copy if available, then verify the synced file through Dropbox MCP. Common macOS sync roots include `$HOME/Library/CloudStorage/Dropbox-Dropbox`, `$HOME/Library/CloudStorage/Dropbox-Personal`, and `$HOME/Dropbox`.
   - If no byte-preserving upload path is available for a binary file, stop and explain that the available MCP create path is text-only.

6. Verify the Dropbox object.
   - Use the returned file object, `dropbox.get_file_metadata`, or a fresh `dropbox.list_folder` result.
   - Prefer the returned `file_id` for follow-on calls.
   - For local uploads, compare Dropbox size with local `wc -c` when size is available.

7. Create or reuse the shared link.
   - Use `dropbox.create_shared_link` for the uploaded/copied file. Do not use `dropbox.download_link`; it creates a sensitive, single-use temporary URL.
   - Inspect the response. Existing links are returned without changing their settings.
   - Report whether the link was newly created or reused, and include effective `audience`, `access_level`, `allow_download`, `expires`, and `password_protected` values when present.

8. Final response.
   - Give the Dropbox path and the shared link.
   - Mention any setting mismatch or partial success.
   - Include a revert path: created files can be deleted with `dropbox.delete` after separate confirmation; link settings or revocation are managed in the Dropbox web UI.

## Notes

- Keep `dl=0` Dropbox links for human viewing and HTML rendering. Only change link parameters if the user specifically asks for direct download or raw content behavior.
- Always display `path_display` when Dropbox MCP returns it. Use ns paths or file IDs for follow-on tool calls exactly as returned.
- Treat links as durable shared links, not public hosting guarantees. If the user needs access beyond people who can open the returned link, tell them the effective audience from the response and suggest adjusting sharing in Dropbox web UI.
