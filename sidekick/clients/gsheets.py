"""Google Sheets API Client - single file implementation with CLI support."""

import sys
import json
import csv
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, List
from io import StringIO


class GSheetsClient:
    """Google Sheets API client using native Python stdlib."""

    def __init__(self, client_id: str, client_secret: str, refresh_token: str, timeout: int = 30):
        """Initialize Google Sheets client with OAuth2 credentials.

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
        except (KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid token response: {e}")

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
    ) -> Optional[dict]:
        """Make HTTP request to Google Sheets API.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
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
        base_url = "https://sheets.googleapis.com/v4"
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

    def _drive_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        retry_auth: bool = True
    ) -> Optional[dict]:
        """Make HTTP request to Google Drive API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: URL query parameters
            retry_auth: Whether to retry once on auth failure

        Returns:
            Parsed JSON response as dict

        Raises:
            ConnectionError: For network errors
            ValueError: For 4xx client errors
            RuntimeError: For 5xx server errors
        """
        # Build URL
        base_url = "https://www.googleapis.com/drive/v3"
        url = f"{base_url}{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        # Prepare request
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Accept": "application/json"
        }
        req = urllib.request.Request(url, headers=headers, method=method)

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
                return self._drive_request(method, endpoint, params, retry_auth=False)

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

    @staticmethod
    def extract_spreadsheet_id(url: str) -> str:
        """Extract spreadsheet ID from a Google Sheets URL.

        Args:
            url: Google Sheets URL

        Returns:
            Spreadsheet ID

        Raises:
            ValueError: If URL format is invalid

        Examples:
            >>> GSheetsClient.extract_spreadsheet_id(
            ...     "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
            ... )
            '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms'
        """
        if "/spreadsheets/d/" in url:
            # Extract ID from URL
            parts = url.split("/spreadsheets/d/")
            if len(parts) > 1:
                spreadsheet_id = parts[1].split("/")[0].split("?")[0].split("#")[0]
                return spreadsheet_id
        raise ValueError(f"Invalid Google Sheets URL: {url}")

    def list_spreadsheets(self, max_results: int = 100) -> List[dict]:
        """List all spreadsheets accessible to the user.

        Note: This requires the Google Drive API to be enabled in addition to Sheets API.

        Args:
            max_results: Maximum number of spreadsheets to return

        Returns:
            List of spreadsheet dicts with id, name, and webViewLink

        Example:
            >>> spreadsheets = client.list_spreadsheets(max_results=10)
            >>> for sheet in spreadsheets:
            ...     print(f"{sheet['name']}: {sheet['id']}")
        """
        params = {
            "q": "mimeType='application/vnd.google-apps.spreadsheet'",
            "pageSize": max_results,
            "fields": "files(id,name,webViewLink,modifiedTime)"
        }

        result = self._drive_request("GET", "/files", params=params)
        return result.get("files", [])

    def get_spreadsheet_by_url(self, url: str) -> dict:
        """Get spreadsheet metadata by URL.

        Args:
            url: Google Sheets URL

        Returns:
            Spreadsheet metadata dict

        Raises:
            ValueError: If URL format is invalid

        Example:
            >>> sheet = client.get_spreadsheet_by_url(
            ...     "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
            ... )
        """
        spreadsheet_id = self.extract_spreadsheet_id(url)
        return self.get_spreadsheet(spreadsheet_id)

    def get_spreadsheet(self, spreadsheet_id: str) -> dict:
        """Get spreadsheet metadata.

        Args:
            spreadsheet_id: The spreadsheet ID

        Returns:
            Spreadsheet metadata dict
        """
        return self._request("GET", f"/spreadsheets/{spreadsheet_id}")

    def get_values(
        self,
        spreadsheet_id: str,
        range_name: str = "Sheet1"
    ) -> List[List[str]]:
        """Get cell values from a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID
            range_name: Range in A1 notation (e.g., "Sheet1" or "Sheet1!A1:D10")

        Returns:
            2D list of cell values
        """
        result = self._request(
            "GET",
            f"/spreadsheets/{spreadsheet_id}/values/{range_name}"
        )
        return result.get("values", [])

    def download_as_csv(
        self,
        spreadsheet_id: str,
        sheet_name: str = "Sheet1",
        output_path: Optional[str] = None
    ) -> str:
        """Download a sheet as CSV.

        Args:
            spreadsheet_id: The spreadsheet ID
            sheet_name: Name of the sheet to download
            output_path: Path to save CSV (if None, returns CSV string)

        Returns:
            CSV content as string
        """
        values = self.get_values(spreadsheet_id, sheet_name)

        # Convert to CSV
        output = StringIO()
        writer = csv.writer(output)
        for row in values:
            writer.writerow(row)

        csv_content = output.getvalue()

        # Save to file if path provided
        if output_path:
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                f.write(csv_content)

        return csv_content

    def create_spreadsheet(self, title: str) -> dict:
        """Create a new spreadsheet.

        Args:
            title: Title for the new spreadsheet

        Returns:
            Spreadsheet metadata dict with spreadsheetId
        """
        request_body = {
            "properties": {
                "title": title
            }
        }
        return self._request("POST", "/spreadsheets", json_data=request_body)

    def upload_csv(
        self,
        csv_path: str,
        title: str,
        sheet_name: str = "Sheet1"
    ) -> dict:
        """Upload a CSV file as a new spreadsheet.

        Args:
            csv_path: Path to CSV file
            title: Title for the new spreadsheet
            sheet_name: Name for the sheet

        Returns:
            Spreadsheet metadata dict with spreadsheetId
        """
        # Read CSV file
        with open(csv_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            values = list(reader)

        # Create new spreadsheet
        spreadsheet = self.create_spreadsheet(title)
        spreadsheet_id = spreadsheet["spreadsheetId"]

        # Update sheet name if not "Sheet1"
        if sheet_name != "Sheet1":
            self._request(
                "POST",
                f"/spreadsheets/{spreadsheet_id}:batchUpdate",
                json_data={
                    "requests": [{
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": 0,
                                "title": sheet_name
                            },
                            "fields": "title"
                        }
                    }]
                }
            )

        # Write data
        self.update_values(spreadsheet_id, sheet_name, values)

        return spreadsheet

    def update_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: List[List[str]]
    ) -> dict:
        """Update cell values in a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID
            range_name: Range in A1 notation (e.g., "Sheet1" or "Sheet1!A1:D10")
            values: 2D list of cell values

        Returns:
            Update response dict
        """
        request_body = {
            "values": values
        }
        return self._request(
            "PUT",
            f"/spreadsheets/{spreadsheet_id}/values/{range_name}",
            params={"valueInputOption": "RAW"},
            json_data=request_body
        )

    def clear_sheet(self, spreadsheet_id: str, range_name: str = "Sheet1") -> dict:
        """Clear all values in a sheet.

        Args:
            spreadsheet_id: The spreadsheet ID
            range_name: Range to clear (default: entire sheet)

        Returns:
            Clear response dict
        """
        return self._request(
            "POST",
            f"/spreadsheets/{spreadsheet_id}/values/{range_name}:clear"
        )

    def replace_sheet_with_csv(
        self,
        spreadsheet_id: str,
        csv_path: str,
        sheet_name: str = "Sheet1"
    ) -> dict:
        """Replace a sheet's contents with CSV data.

        Args:
            spreadsheet_id: The spreadsheet ID
            csv_path: Path to CSV file
            sheet_name: Name of the sheet to replace

        Returns:
            Update response dict
        """
        # Read CSV file
        with open(csv_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            values = list(reader)

        # Clear existing data
        self.clear_sheet(spreadsheet_id, sheet_name)

        # Write new data
        return self.update_values(spreadsheet_id, sheet_name, values)


def main():
    """CLI interface for Google Sheets client."""
    if len(sys.argv) < 2:
        print("Usage: python -m sidekick.clients.gsheets <command> [args]")
        print("\nCommands:")
        print("  list [max_results]                                    - List all spreadsheets")
        print("  download <spreadsheet_id> [sheet_name] [output_path] - Download sheet as CSV")
        print("  download-url <url> [sheet_name] [output_path]        - Download sheet by URL")
        print("  upload <csv_path> <title> [sheet_name]               - Upload CSV as new spreadsheet")
        print("  replace <spreadsheet_id> <csv_path> [sheet_name]     - Replace sheet with CSV")
        print("  get <spreadsheet_id>                                  - Get spreadsheet metadata")
        print("  get-url <url>                                         - Get spreadsheet metadata by URL")
        print("\nExamples:")
        print('  python -m sidekick.clients.gsheets list 20')
        print('  python -m sidekick.clients.gsheets download "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms" Sheet1 data.csv')
        print('  python -m sidekick.clients.gsheets download-url "https://docs.google.com/spreadsheets/d/1Bxi.../edit"')
        print('  python -m sidekick.clients.gsheets upload data.csv "My Spreadsheet" Sheet1')
        print('  python -m sidekick.clients.gsheets replace "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms" data.csv Sheet1')
        print('  python -m sidekick.clients.gsheets get-url "https://docs.google.com/spreadsheets/d/1Bxi.../edit"')
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
    client = GSheetsClient(
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        refresh_token=config["refresh_token"]
    )

    command = sys.argv[1]

    try:
        if command == "list":
            max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 100

            spreadsheets = client.list_spreadsheets(max_results=max_results)
            print(f"Found {len(spreadsheets)} spreadsheets:\n")
            for sheet in spreadsheets:
                modified = sheet.get("modifiedTime", "Unknown")
                print(f"{sheet['name']}")
                print(f"  ID: {sheet['id']}")
                print(f"  URL: {sheet.get('webViewLink', 'N/A')}")
                print(f"  Modified: {modified}")
                print()

        elif command == "download":
            if len(sys.argv) < 3:
                print("Error: Missing spreadsheet_id argument", file=sys.stderr)
                sys.exit(1)

            spreadsheet_id = sys.argv[2]
            sheet_name = sys.argv[3] if len(sys.argv) > 3 else "Sheet1"
            output_path = sys.argv[4] if len(sys.argv) > 4 else None

            csv_content = client.download_as_csv(spreadsheet_id, sheet_name, output_path)

            if output_path:
                print(f"Downloaded sheet '{sheet_name}' to {output_path}")
            else:
                print(csv_content)

        elif command == "download-url":
            if len(sys.argv) < 3:
                print("Error: Missing URL argument", file=sys.stderr)
                sys.exit(1)

            url = sys.argv[2]
            sheet_name = sys.argv[3] if len(sys.argv) > 3 else "Sheet1"
            output_path = sys.argv[4] if len(sys.argv) > 4 else None

            spreadsheet_id = client.extract_spreadsheet_id(url)
            csv_content = client.download_as_csv(spreadsheet_id, sheet_name, output_path)

            if output_path:
                print(f"Downloaded sheet '{sheet_name}' to {output_path}")
            else:
                print(csv_content)

        elif command == "upload":
            if len(sys.argv) < 4:
                print("Error: Missing arguments. Need: csv_path, title", file=sys.stderr)
                sys.exit(1)

            csv_path = sys.argv[2]
            title = sys.argv[3]
            sheet_name = sys.argv[4] if len(sys.argv) > 4 else "Sheet1"

            spreadsheet = client.upload_csv(csv_path, title, sheet_name)

            print("Uploaded CSV to new spreadsheet!")
            print(f"Spreadsheet ID: {spreadsheet['spreadsheetId']}")
            print(f"Title: {spreadsheet['properties']['title']}")
            print(f"URL: https://docs.google.com/spreadsheets/d/{spreadsheet['spreadsheetId']}")

        elif command == "replace":
            if len(sys.argv) < 4:
                print("Error: Missing arguments. Need: spreadsheet_id, csv_path", file=sys.stderr)
                sys.exit(1)

            spreadsheet_id = sys.argv[2]
            csv_path = sys.argv[3]
            sheet_name = sys.argv[4] if len(sys.argv) > 4 else "Sheet1"

            result = client.replace_sheet_with_csv(spreadsheet_id, csv_path, sheet_name)

            print(f"Replaced sheet '{sheet_name}' with CSV data")
            print(f"Updated {result.get('updatedRows', 0)} rows, {result.get('updatedColumns', 0)} columns")

        elif command == "get":
            if len(sys.argv) < 3:
                print("Error: Missing spreadsheet_id argument", file=sys.stderr)
                sys.exit(1)

            spreadsheet_id = sys.argv[2]
            spreadsheet = client.get_spreadsheet(spreadsheet_id)

            print(f"Spreadsheet ID: {spreadsheet['spreadsheetId']}")
            print(f"Title: {spreadsheet['properties']['title']}")
            print(f"URL: https://docs.google.com/spreadsheets/d/{spreadsheet['spreadsheetId']}")
            print("\nSheets:")
            for sheet in spreadsheet.get("sheets", []):
                props = sheet["properties"]
                print(f"  - {props['title']} (sheetId: {props['sheetId']})")

        elif command == "get-url":
            if len(sys.argv) < 3:
                print("Error: Missing URL argument", file=sys.stderr)
                sys.exit(1)

            url = sys.argv[2]
            spreadsheet = client.get_spreadsheet_by_url(url)

            print(f"Spreadsheet ID: {spreadsheet['spreadsheetId']}")
            print(f"Title: {spreadsheet['properties']['title']}")
            print(f"URL: https://docs.google.com/spreadsheets/d/{spreadsheet['spreadsheetId']}")
            print("\nSheets:")
            for sheet in spreadsheet.get("sheets", []):
                props = sheet["properties"]
                print(f"  - {props['title']} (sheetId: {props['sheetId']})")

        else:
            print(f"Error: Unknown command '{command}'", file=sys.stderr)
            sys.exit(1)

    except (ValueError, RuntimeError, ConnectionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
