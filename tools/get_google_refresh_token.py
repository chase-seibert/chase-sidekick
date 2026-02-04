#!/usr/bin/env python3
"""Helper script to obtain Google OAuth2 refresh token.

This script helps you get a refresh token for Gmail, Google Calendar, and Google Sheets.
The refresh token can be used with all three services.

Prerequisites:
1. Go to https://console.cloud.google.com/
2. Create a project (or use existing)
3. Enable APIs: Gmail API, Google Calendar API, Google Sheets API
4. Create OAuth2 credentials (Desktop app)
5. Have your Client ID and Client Secret ready
"""

import sys
import json
import urllib.request
import urllib.parse
import webbrowser
from typing import Optional


def get_authorization_code(client_id: str) -> str:
    """Open browser for authorization and get code."""
    redirect_uri = "http://localhost"

    # Combined scopes for Gmail, Calendar, Sheets, and Drive (read-only for listing)
    scopes = [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    scope = " ".join(scopes)

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent"
    })

    print("\n" + "="*80)
    print("STEP 1: Authorize the application")
    print("="*80)
    print("\nOpening your browser to authorize the application...")
    print(f"\nIf the browser doesn't open automatically, visit this URL:\n{auth_url}\n")

    try:
        webbrowser.open(auth_url)
    except Exception as e:
        print(f"Could not open browser: {e}")

    print("\nAfter authorizing, you'll be redirected to a URL like:")
    print("  http://localhost/?code=4/0A...&scope=https://...")
    print("\nCopy the ENTIRE redirect URL from your browser's address bar.")

    redirect_url = input("\nPaste the redirect URL here: ").strip()

    # Extract code from URL
    if "code=" in redirect_url:
        code = redirect_url.split("code=")[1].split("&")[0]
        return code
    else:
        raise ValueError("Could not find authorization code in URL")


def exchange_code_for_tokens(client_id: str, client_secret: str, code: str) -> dict:
    """Exchange authorization code for access and refresh tokens."""
    token_url = "https://oauth2.googleapis.com/token"
    redirect_uri = "http://localhost"

    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }).encode()

    req = urllib.request.Request(token_url, data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req) as response:
            tokens = json.loads(response.read().decode())
            return tokens
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        raise ValueError(f"Failed to get tokens: {e.code} - {error_body}")


def main():
    """Main function to guide user through OAuth flow."""
    print("="*80)
    print("Google Services OAuth2 Refresh Token Generator")
    print("="*80)
    print("\nThis script will help you obtain a refresh token for:")
    print("  - Gmail")
    print("  - Google Calendar")
    print("  - Google Sheets")
    print("\nThe same refresh token works for all three services!")
    print("\nPrerequisites:")
    print("  1. Google Cloud project with APIs enabled")
    print("  2. OAuth2 credentials (Desktop app)")
    print("  3. Client ID and Client Secret")
    print("\nIf you don't have these, visit:")
    print("  https://console.cloud.google.com/")

    input("\nPress Enter to continue...")

    # Get credentials
    print("\n" + "="*80)
    print("Enter your OAuth2 credentials")
    print("="*80)

    client_id = input("\nClient ID: ").strip()
    if not client_id:
        print("Error: Client ID is required")
        sys.exit(1)

    client_secret = input("Client Secret: ").strip()
    if not client_secret:
        print("Error: Client Secret is required")
        sys.exit(1)

    try:
        # Get authorization code
        code = get_authorization_code(client_id)

        print("\n" + "="*80)
        print("STEP 2: Exchange code for tokens")
        print("="*80)
        print("\nExchanging authorization code for tokens...")

        # Exchange for tokens
        tokens = exchange_code_for_tokens(client_id, client_secret, code)

        if "refresh_token" not in tokens:
            print("\n" + "="*80)
            print("WARNING: No refresh token received!")
            print("="*80)
            print("\nThis can happen if you've already authorized this app.")
            print("To get a refresh token:")
            print("  1. Go to https://myaccount.google.com/permissions")
            print("  2. Remove access for your app")
            print("  3. Run this script again")
            sys.exit(1)

        # Display results
        print("\n" + "="*80)
        print("SUCCESS! Got your tokens")
        print("="*80)

        print("\n" + "-"*80)
        print("Refresh Token (save this!):")
        print("-"*80)
        print(tokens["refresh_token"])

        print("\n" + "-"*80)
        print("Add these to your .env file:")
        print("-"*80)
        print(f'GOOGLE_CLIENT_ID={client_id}')
        print(f'GOOGLE_CLIENT_SECRET={client_secret}')
        print(f'GOOGLE_REFRESH_TOKEN={tokens["refresh_token"]}')

        print("\n" + "="*80)
        print("Next steps:")
        print("="*80)
        print("1. Copy the three lines above to your .env file")
        print("2. Test with: python -m sidekick.clients.gmail search 'is:unread'")
        print("3. The same credentials work for calendar and sheets too!")

        print("\n✓ All done!\n")

    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
