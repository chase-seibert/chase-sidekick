#!/usr/bin/env python3
"""Helper script to obtain Dropbox OAuth2 access token.

This script helps you get an access token for Dropbox API access.

Prerequisites:
1. Go to https://www.dropbox.com/developers/apps
2. Create an app (or use existing)
3. Set redirect URI to: http://localhost:8080
4. Have your App Key and App Secret ready
5. Run: python3 tools/get_dropbox_access_token.py
"""

import sys
import json
import urllib.request
import urllib.parse
import urllib.error
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional


# Global variable to store authorization code
authorization_code = None


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""

    def log_message(self, format, *args):
        """Suppress default request logging."""
        pass

    def do_GET(self):
        """Handle GET request from OAuth callback."""
        global authorization_code

        # Parse query parameters
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if 'code' in params:
            authorization_code = params['code'][0]

            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            success_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authorization Successful</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: #f5f5f5;
                    }
                    .container {
                        text-align: center;
                        padding: 40px;
                        background: white;
                        border-radius: 8px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    }
                    .success { color: #0061ff; font-size: 48px; margin-bottom: 20px; }
                    h1 { color: #333; margin: 0 0 10px 0; }
                    p { color: #666; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success">✓</div>
                    <h1>Authorization Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode())
        elif 'error' in params:
            error = params['error'][0]
            error_description = params.get('error_description', ['Unknown error'])[0]

            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authorization Failed</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: #f5f5f5;
                    }}
                    .container {{
                        text-align: center;
                        padding: 40px;
                        background: white;
                        border-radius: 8px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    }}
                    .error {{ color: #cc0000; font-size: 48px; margin-bottom: 20px; }}
                    h1 {{ color: #333; margin: 0 0 10px 0; }}
                    p {{ color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="error">✗</div>
                    <h1>Authorization Failed</h1>
                    <p>{error}: {error_description}</p>
                    <p>Return to the terminal for more information.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode())
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Invalid callback request')


def start_local_server(port: int = 8080, timeout: int = 120) -> Optional[str]:
    """Start local HTTP server to capture OAuth callback.

    Args:
        port: Port to listen on (default: 8080)
        timeout: Timeout in seconds (default: 120)

    Returns:
        Authorization code from callback, or None if timeout/error

    Raises:
        RuntimeError: If server cannot start
    """
    global authorization_code
    authorization_code = None

    try:
        server = HTTPServer(('localhost', port), OAuthCallbackHandler)
        server.timeout = timeout

        print(f"\nLocal server started on http://localhost:{port}")
        print("Waiting for authorization callback...")

        # Handle a single request
        server.handle_request()

        server.server_close()

        return authorization_code

    except OSError as e:
        if e.errno == 48:  # Address already in use
            raise RuntimeError(
                f"Port {port} is already in use. "
                f"Please close the application using this port or specify a different port."
            )
        raise RuntimeError(f"Failed to start server: {e}")


def get_authorization_code(app_key: str, port: int = 8080) -> str:
    """Get authorization code via browser and local server.

    Args:
        app_key: Dropbox App Key
        port: Port for local callback server (default: 8080)

    Returns:
        Authorization code from Dropbox

    Raises:
        ValueError: If authorization fails or times out
    """
    redirect_uri = f"http://localhost:{port}"

    auth_url = "https://www.dropbox.com/oauth2/authorize?" + urllib.parse.urlencode({
        "client_id": app_key,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "token_access_type": "offline"
    })

    print("\n" + "=" * 80)
    print("STEP 1: Authorize the application")
    print("="*80)
    print("\nOpening your browser to authorize the application...")
    print(f"\nIf the browser doesn't open automatically, visit this URL:\n{auth_url}\n")

    try:
        webbrowser.open(auth_url)
    except Exception as e:
        print(f"Could not open browser: {e}")

    # Start local server and wait for callback
    code = start_local_server(port=port)

    if not code:
        raise ValueError(
            "Authorization failed or timed out. "
            "Please try again and make sure to click 'Allow' on the Dropbox authorization page."
        )

    return code


def exchange_code_for_token(app_key: str, app_secret: str, code: str, port: int = 8080) -> dict:
    """Exchange authorization code for access token.

    Args:
        app_key: Dropbox App Key
        app_secret: Dropbox App Secret
        code: Authorization code from OAuth callback
        port: Port used for redirect URI (default: 8080)

    Returns:
        dict with access token and metadata

    Raises:
        ValueError: If token exchange fails
    """
    token_url = "https://api.dropbox.com/oauth2/token"
    redirect_uri = f"http://localhost:{port}"

    data = urllib.parse.urlencode({
        "code": code,
        "grant_type": "authorization_code",
        "client_id": app_key,
        "client_secret": app_secret,
        "redirect_uri": redirect_uri
    }).encode()

    req = urllib.request.Request(token_url, data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req) as response:
            tokens = json.loads(response.read().decode())
            return tokens
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        raise ValueError(f"Failed to get token: {e.code} - {error_body}")


def main():
    """Main function to guide user through OAuth flow."""
    print("=" * 80)
    print("Dropbox OAuth2 Access Token Generator")
    print("=" * 80)
    print("\nThis script will help you obtain an access token for Dropbox API.")
    print("\nPrerequisites:")
    print("  1. Dropbox app created at https://www.dropbox.com/developers/apps")
    print("  2. Redirect URI set to: http://localhost:8080")
    print("  3. App Key and App Secret from app settings")
    print("\nNote: The redirect URI must be configured in your app settings.")

    input("\nPress Enter to continue...")

    # Get credentials
    print("\n" + "=" * 80)
    print("Enter your app credentials")
    print("="*80)

    app_key = input("\nApp Key: ").strip()
    if not app_key:
        print("Error: App Key is required")
        sys.exit(1)

    app_secret = input("App Secret: ").strip()
    if not app_secret:
        print("Error: App Secret is required")
        sys.exit(1)

    # Optional: custom port
    port = 8080
    custom_port = input(f"Port for local server (default: {port}): ").strip()
    if custom_port:
        try:
            port = int(custom_port)
            print(f"\nNote: Make sure your app's redirect URI is set to: http://localhost:{port}")
        except ValueError:
            print("Invalid port number, using default 8080")
            port = 8080

    try:
        # Get authorization code
        code = get_authorization_code(app_key, port=port)

        print("\n" + "=" * 80)
        print("STEP 2: Exchange code for access token")
        print("="*80)
        print("\nExchanging authorization code for access token...")

        # Exchange for token
        tokens = exchange_code_for_token(app_key, app_secret, code, port=port)

        if "access_token" not in tokens:
            print("\n" + "=" * 80)
            print("ERROR: No access token received")
            print("=" * 80)
            print("\nReceived response:", json.dumps(tokens, indent=2))
            sys.exit(1)

        # Display results
        print("\n" + "=" * 80)
        print("SUCCESS! Got your access token")
        print("=" * 80)

        print("\n" + "-" * 80)
        print("Access Token (save this!):")
        print("-" * 80)
        print(tokens["access_token"])

        print("\n" + "-" * 80)
        print("Add this to your .env file:")
        print("-" * 80)
        print(f'DROPBOX_ACCESS_TOKEN={tokens["access_token"]}')

        # Show additional token info if available
        if "refresh_token" in tokens:
            print("\n" + "-" * 80)
            print("Refresh Token (also save this!):")
            print("-" * 80)
            print(tokens["refresh_token"])
            print("\nNote: This token can be used to get new access tokens without re-authorization.")

        if "expires_in" in tokens:
            print(f"\nToken expires in: {tokens['expires_in']} seconds")

        print("\n" + "=" * 80)
        print("Next steps:")
        print("=" * 80)
        print("1. Copy the line above to your .env file")
        print("2. Verify app permissions at: https://www.dropbox.com/account/connected_apps")

        print("\n✓ All done!\n")

    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
