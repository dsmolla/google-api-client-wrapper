"""
Example: Local Server Authentication (Development Only)

This example demonstrates how to use the local server authentication method
for easy development and testing. The browser will open automatically and
handle the OAuth callback.

IMPORTANT: This is for NON-PRODUCTION use only!

Prerequisites:
1. Create a Google Cloud Project and enable the APIs you need
2. Create OAuth 2.0 credentials (Desktop application type)
3. Download the credentials as 'credentials.json'
4. Add http://localhost:8080 to authorized redirect URIs in Google Console

Usage:
    python example_local_auth.py
"""

from google_client.auth import GoogleOAuthManager, Scopes
from google_client.api_service import APIServiceLayer
import json


def main():
    print("=" * 60)
    print("Local Server Authentication Example")
    print("=" * 60)
    print()

    # Load client secrets
    try:
        with open(r'C:\Users\dagms\Projects\Credentials\credentials-2.json', 'r') as f:
            client_secrets = json.load(f)
    except FileNotFoundError:
        print("ERROR: credentials.json not found!")
        print("Please download your OAuth credentials from Google Cloud Console")
        print("and save them as 'credentials.json' in this directory.")
        return

    # Initialize OAuth manager (redirect_uri defaults to localhost:8080)
    oauth_manager = GoogleOAuthManager(
        client_secrets_dict=client_secrets
    )

    print("Starting authentication...")
    print("Your browser will open automatically.")
    print()

    try:
        # Authenticate using local server
        user_info = oauth_manager.authenticate_via_local_server(
            scopes=[
                Scopes.GMAIL,
                Scopes.DRIVE,
                Scopes.CALENDAR,
                Scopes.TASKS
            ],
            port=8080,
            timeout_seconds=300
        )

        print()
        print("✓ Authentication successful!")
        print()

        # Save credentials for future use
        with open('user_token.json', 'w') as f:
            json.dump(user_info, f)
        print("✓ Credentials saved to user_token.json")
        print()

        # Test the credentials by initializing API service
        print("Testing credentials...")
        api_service = APIServiceLayer(user_info, timezone='America/New_York')

        # Try to list emails (just get the count)
        try:
            gmail = api_service.gmail
            message_ids = gmail.list_emails(max_results=5)
            print(f"✓ Gmail API working! Found {len(message_ids)} recent emails")
        except Exception as e:
            print(f"✗ Gmail test failed: {e}")

        print()
        print("=" * 60)
        print("Setup complete! You can now use the saved credentials.")
        print("=" * 60)

    except TimeoutError:
        print()
        print("✗ Authentication timed out. Please try again.")
    except RuntimeError as e:
        print()
        print(f"✗ Error: {e}")
        if "port" in str(e).lower():
            print()
            print("Try using a different port:")
            print("  user_info = oauth_manager.authenticate_via_local_server(")
            print("      scopes=[...],")
            print("      port=9090  # Use a different port")
            print("  )")
    except Exception as e:
        print()
        print(f"✗ Unexpected error: {e}")


if __name__ == '__main__':
    main()
