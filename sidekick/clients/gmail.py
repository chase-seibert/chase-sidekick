"""Gmail API Client - single file implementation with CLI support."""

import sys
import json
import base64
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class GmailClient:
    """Gmail API client using native Python stdlib."""

    def __init__(self, client_id: str, client_secret: str, refresh_token: str, timeout: int = 30):
        """Initialize Gmail client with OAuth2 credentials.

        Args:
            client_id: OAuth2 client ID from Google Cloud Console
            client_secret: OAuth2 client secret
            refresh_token: OAuth2 refresh token
            timeout: Request timeout in seconds
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.timeout = timeout
        self.access_token = None
        self.api_call_count = 0

    def _refresh_access_token(self) -> str:
        """Refresh OAuth2 access token using refresh token.

        Returns:
            New access token

        Raises:
            ValueError: If token refresh fails
        """
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }

        encoded_data = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(token_url, data=encoded_data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode())
                return result["access_token"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            raise ValueError(f"Failed to refresh access token: {e.code} - {error_body}")
        except (KeyError, json.JSONDecodeError):
            raise ValueError("Invalid token response")

    def _get_access_token(self) -> str:
        """Get valid access token, refreshing if necessary."""
        if not self.access_token:
            self.access_token = self._refresh_access_token()
        return self.access_token

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        retry_auth: bool = True
    ) -> dict:
        """Make HTTP request to Gmail API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            params: URL query parameters
            json_data: JSON body data
            retry_auth: Whether to retry once on auth failure

        Returns:
            Parsed JSON response as dict

        Raises:
            ConnectionError: For network errors
            ValueError: For 4xx client errors
            RuntimeError: For 5xx server errors
        """
        # Build URL
        base_url = "https://gmail.googleapis.com/gmail/v1"
        url = f"{base_url}{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        # Prepare request
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        data = json.dumps(json_data).encode() if json_data else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                self.api_call_count += 1
                body = response.read().decode()
                if not body or body.strip() == "":
                    return {}
                return json.loads(body)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""

            # Retry once on 401 (token might be expired)
            if e.code == 401 and retry_auth:
                self.access_token = None  # Force token refresh
                return self._request(method, endpoint, params, json_data, retry_auth=False)

            if e.code == 404:
                raise ValueError(f"Resource not found: {endpoint}")
            elif e.code >= 400 and e.code < 500:
                raise ValueError(f"Client error {e.code}: {error_body}")
            elif e.code >= 500:
                raise RuntimeError(f"Server error {e.code}: {error_body}")
            else:
                raise ConnectionError(f"HTTP error {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Network error: {e.reason}")

    def search_messages(
        self,
        query: str,
        max_results: int = 10,
        include_spam_trash: bool = False
    ) -> List[dict]:
        """Search for messages matching a query.

        Args:
            query: Gmail search query (uses same syntax as Gmail search box)
            max_results: Maximum number of results to return
            include_spam_trash: Whether to include spam and trash

        Returns:
            List of message dicts with id, threadId, and snippet

        Example queries:
            "from:someone@example.com"
            "subject:meeting"
            "is:unread"
            "after:2024/01/01"
        """
        params = {
            "q": query,
            "maxResults": max_results
        }
        if include_spam_trash:
            params["includeSpamTrash"] = "true"

        result = self._request("GET", "/users/me/messages", params=params)
        messages = result.get("messages", [])

        # Get full details for each message
        detailed_messages = []
        for msg in messages:
            try:
                full_msg = self.get_message(msg["id"])
                detailed_messages.append(full_msg)
            except Exception as e:
                # If we can't get details, include basic info
                detailed_messages.append(msg)

        return detailed_messages

    def get_message(self, message_id: str, format: str = "full") -> dict:
        """Get a specific message by ID.

        Args:
            message_id: The message ID
            format: Message format (full, metadata, minimal, raw)

        Returns:
            Message dict with full details
        """
        params = {"format": format}
        return self._request("GET", f"/users/me/messages/{message_id}", params=params)

    def get_message_body(self, message: dict) -> str:
        """Extract text body from a message.

        Args:
            message: Message dict from get_message()

        Returns:
            Plain text body of the message
        """
        def decode_body(part):
            """Decode base64url encoded body."""
            if "data" in part.get("body", {}):
                data = part["body"]["data"]
                # Gmail uses base64url encoding
                data = data.replace("-", "+").replace("_", "/")
                # Add padding if necessary
                padding = 4 - (len(data) % 4)
                if padding != 4:
                    data += "=" * padding
                return base64.b64decode(data).decode("utf-8", errors="ignore")
            return ""

        def extract_text(payload):
            """Recursively extract text from message payload."""
            mime_type = payload.get("mimeType", "")

            if mime_type == "text/plain":
                return decode_body(payload)
            elif mime_type == "text/html":
                # If we only have HTML, return it (better than nothing)
                return decode_body(payload)
            elif "parts" in payload:
                # Multipart message - prefer text/plain over text/html
                text_parts = []
                html_parts = []
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/plain":
                        text_parts.append(extract_text(part))
                    elif part.get("mimeType") == "text/html":
                        html_parts.append(extract_text(part))
                    else:
                        # Recurse into nested parts
                        text_parts.append(extract_text(part))

                # Return text/plain if available, otherwise HTML
                if text_parts:
                    return "\n".join(filter(None, text_parts))
                return "\n".join(filter(None, html_parts))

            return ""

        if "payload" in message:
            return extract_text(message["payload"])
        return ""

    def get_message_headers(self, message: dict) -> dict:
        """Extract common headers from a message.

        Args:
            message: Message dict from get_message()

        Returns:
            Dict with headers: from, to, subject, date
        """
        headers = {}
        if "payload" in message and "headers" in message["payload"]:
            for header in message["payload"]["headers"]:
                name = header["name"].lower()
                if name in ["from", "to", "subject", "date", "cc", "bcc"]:
                    headers[name] = header["value"]
        return headers

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ) -> dict:
        """Create a draft email.

        Args:
            to: Recipient email address(es), comma-separated
            subject: Email subject
            body: Email body (plain text)
            cc: CC recipients, comma-separated (optional)
            bcc: BCC recipients, comma-separated (optional)

        Returns:
            Draft dict with id and message
        """
        # Create MIME message
        message = MIMEMultipart()
        message["To"] = to
        message["Subject"] = subject
        if cc:
            message["Cc"] = cc
        if bcc:
            message["Bcc"] = bcc

        # Add body
        message.attach(MIMEText(body, "plain"))

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Create draft
        draft_data = {
            "message": {
                "raw": raw_message
            }
        }

        return self._request("POST", "/users/me/drafts", json_data=draft_data)


def _format_message_oneline(message: dict) -> str:
    """Format message as one-line summary."""
    headers = GmailClient(None, None, None).get_message_headers(message)
    from_addr = headers.get("from", "Unknown")
    subject = headers.get("subject", "(No subject)")
    snippet = message.get("snippet", "")
    msg_id = message.get("id", "")

    # Truncate snippet if too long
    if len(snippet) > 80:
        snippet = snippet[:77] + "..."

    return f"{msg_id}: {from_addr} - {subject}\n  {snippet}"


def _format_message_full(message: dict) -> str:
    """Format full message details."""
    client = GmailClient(None, None, None)
    headers = client.get_message_headers(message)
    body = client.get_message_body(message)

    lines = [
        f"Message ID: {message.get('id', 'Unknown')}",
        f"Thread ID: {message.get('threadId', 'Unknown')}",
        f"From: {headers.get('from', 'Unknown')}",
        f"To: {headers.get('to', 'Unknown')}",
        f"Subject: {headers.get('subject', '(No subject)')}",
        f"Date: {headers.get('date', 'Unknown')}",
    ]

    if "cc" in headers:
        lines.append(f"Cc: {headers['cc']}")
    if "bcc" in headers:
        lines.append(f"Bcc: {headers['bcc']}")

    lines.append("")
    lines.append("Body:")
    lines.append("-" * 80)
    lines.append(body)
    lines.append("-" * 80)

    return "\n".join(lines)


def main():
    """CLI interface for Gmail client."""
    if len(sys.argv) < 2:
        print("Usage: python -m sidekick.clients.gmail <command> [args]")
        print("\nCommands:")
        print("  search <query> [max_results]  - Search for messages")
        print("  get <message_id>              - Get full message details")
        print("  create-draft <to> <subject> <body> - Create draft email")
        print("\nExample:")
        print('  python -m sidekick.clients.gmail search "from:someone@example.com" 5')
        print('  python -m sidekick.clients.gmail get 18f2c4e5a1b2c3d4')
        print('  python -m sidekick.clients.gmail create-draft "user@example.com" "Hello" "Email body here"')
        sys.exit(1)

    # Load configuration
    try:
        from sidekick.config import get_google_config
        config = get_google_config()
    except ImportError:
        print("Error: Could not import config module", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Create client
    client = GmailClient(
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        refresh_token=config["refresh_token"]
    )

    command = sys.argv[1]

    try:
        if command == "search":
            if len(sys.argv) < 3:
                print("Error: Missing query argument", file=sys.stderr)
                sys.exit(1)

            query = sys.argv[2]
            max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 10

            messages = client.search_messages(query, max_results=max_results)
            print(f"Found {len(messages)} messages:\n")
            for msg in messages:
                print(_format_message_oneline(msg))
                print()

        elif command == "get":
            if len(sys.argv) < 3:
                print("Error: Missing message_id argument", file=sys.stderr)
                sys.exit(1)

            message_id = sys.argv[2]
            message = client.get_message(message_id)
            print(_format_message_full(message))

        elif command == "create-draft":
            if len(sys.argv) < 5:
                print("Error: Missing arguments. Need: to, subject, body", file=sys.stderr)
                sys.exit(1)

            to = sys.argv[2]
            subject = sys.argv[3]
            body = sys.argv[4]

            draft = client.create_draft(to, subject, body)
            print("Draft created successfully!")
            print(f"Draft ID: {draft['id']}")
            print(f"Message ID: {draft['message']['id']}")

        else:
            print(f"Error: Unknown command '{command}'", file=sys.stderr)
            sys.exit(1)

    except (ValueError, RuntimeError, ConnectionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
