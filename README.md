# Google API Client Wrapper

A comprehensive Python wrapper for Google APIs, providing clean and intuitive access to Gmail, Google Drive, Google Calendar, and Google Tasks services with both synchronous and asynchronous implementations.

## Installation

```bash
pip install google-api-client-wrapper
```

or install directly from the GitHub repository:

```bash
pip install git+https://github.com/dsmolla/google-api-client-wrapper.git
```

## Features

- **Gmail Service**: Send, receive, search, and manage emails
- **Google Drive Service**: Upload, download, and manage files and folders
- **Google Calendar Service**: Create, update, and manage calendar events
- **Google Tasks Service**: Manage tasks and task lists
- **Async Support**: Full async/await support for all services with concurrent batch operations
- **OAuth2 Authentication**: Secure authentication flow with token management
- **Query Builders**: Intuitive query building for each service
- **Multi-User Authentication**: Supports multiple users to be authenticated
- **Dataclass Models**: Uses Python dataclasses for clean, type-safe data structures (EmailMessage, Task, CalendarEvent, etc.)
- **Timezone Aware**: Proper timezone handling across all services

## Quick Start

### Authentication

```python
from google_client.auth import GoogleOAuthManager, Scopes
import json

# Initialize OAuth manager
with open('credentials.json', 'r') as f:
    client_secrets = json.load(f)

oauth_manager = GoogleOAuthManager(
    client_secrets_dict=client_secrets,
    redirect_uri='http://localhost:8080/oauth2callback'
)

# Generate authorization URL
auth_url, state = oauth_manager.generate_auth_url(
    scopes=[Scopes.GMAIL, Scopes.DRIVE, Scopes.CALENDAR, Scopes.TASKS]
)

# After user authorizes, exchange code for tokens
user_info = oauth_manager.complete_auth_flow(
    code='authorization_code_from_callback',
    scopes=[Scopes.GMAIL, Scopes.DRIVE, Scopes.CALENDAR, Scopes.TASKS]
)

# Save user_info for future use
with open('user_token.json', 'w') as f:
    json.dump(user_info, f)
```

### Local Server Authentication (Development Only)

For development and testing, you can use the local server authentication method that automatically handles the OAuth callback:

```python
from google_client.auth import GoogleOAuthManager, Scopes
import json

# Load client secrets
with open('credentials.json', 'r') as f:
    client_secrets = json.load(f)

# Initialize OAuth manager (redirect_uri defaults to localhost:8080)
oauth_manager = GoogleOAuthManager(
    client_secrets_dict=client_secrets
)

# Authenticate using local server - browser opens automatically!
user_info = oauth_manager.authenticate_via_local_server(
    scopes=[Scopes.GMAIL, Scopes.DRIVE, Scopes.CALENDAR, Scopes.TASKS]
)

# Save credentials
with open('user_token.json', 'w') as f:
    json.dump(user_info, f)
```

**Important:** This method is for **NON-PRODUCTION** use only. It's perfect for:
- Local development and testing
- Personal automation scripts
- CLI tools for individual use

For production applications, use the manual `generate_auth_url()` and `complete_auth_flow()` methods with a secure HTTPS callback endpoint.

**Requirements:**
- Add `http://localhost:8080` to your Google Cloud Console OAuth2 client's authorized redirect URIs
- Ensure the port is not already in use

### Using Services (Synchronous)

```python
from google_client.api_service import APIServiceLayer
import json

# Load user credentials
with open('user_token.json', 'r') as f:
    user_info = json.load(f)

# Initialize API service layer with timezone
api_service = APIServiceLayer(user_info, timezone='America/New_York')

# Access Gmail service
gmail = api_service.gmail
emails = gmail.list_emails(max_results=10)
email = gmail.get_email(emails[0])
print(f"Subject: {email.subject}")

# Access Drive service
drive = api_service.drive
files = drive.list(max_results=10)
folder = drive.create_folder("My Project")

# Access Calendar service
calendar = api_service.calendar
from datetime import datetime, timedelta
event = calendar.create_event(
    start=datetime.now(),
    end=datetime.now() + timedelta(hours=1),
    summary="Team Meeting"
)

# Access Tasks service
tasks = api_service.tasks
task = tasks.create_task(title="Review documents")
```

### Using Services (Asynchronous)

```python
import asyncio
from google_client.api_service import APIServiceLayer
import json

async def main():
    # Load user credentials
    with open('user_token.json', 'r') as f:
        user_info = json.load(f)

    # Initialize API service layer
    api_service = APIServiceLayer(user_info, timezone='America/New_York')

    # Access async Gmail service
    gmail = api_service.async_gmail
    message_ids = await gmail.list_emails(max_results=50)

    # Batch get emails concurrently (much faster than sync!)
    emails = await gmail.batch_get_emails(message_ids[:10])
    for email in emails:
        print(f"Subject: {email.subject}")

    # Access async Drive service
    drive = api_service.async_drive
    files = await drive.list(max_results=20)

    # Access async Calendar service
    calendar = api_service.async_calendar
    from datetime import datetime, timedelta
    events = await calendar.list_events(
        start=datetime.now(),
        end=datetime.now() + timedelta(days=7)
    )

    # Access async Tasks service
    tasks = api_service.async_tasks
    all_tasks = await tasks.list_tasks(show_completed=True)

# Run async code
asyncio.run(main())
```

## Synchronous vs Asynchronous APIs

This library provides both synchronous and asynchronous versions of all services:

### Synchronous (Blocking)
- Use for simple scripts, CLIs, or sequential operations
- Access via: `api_service.gmail`, `api_service.drive`, etc.
- Methods are regular functions that block until complete

### Asynchronous (Non-blocking)
- Use for high-throughput applications or concurrent operations
- Access via: `api_service.async_gmail`, `api_service.async_drive`, etc.
- Methods are async functions using `async`/`await`
- **10x-100x faster** for batch operations (e.g., fetching 100 emails)

### Performance Example

```python
import time
import asyncio

# Synchronous - Sequential (slower)
start = time.time()
emails = []
for msg_id in message_ids[:50]:
    emails.append(gmail.get_email(msg_id))
print(f"Sync: {time.time() - start:.2f}s")  # ~15-20 seconds

# Asynchronous - Concurrent (faster)
start = time.time()
emails = await async_gmail.batch_get_emails(message_ids[:50])
print(f"Async: {time.time() - start:.2f}s")  # ~1-2 seconds
```

## Authentication Methods Comparison

### Manual OAuth Flow (Production)
**Use for:** Web applications, mobile apps, production services

```python
# Step 1: Generate auth URL
auth_url, state = oauth_manager.generate_auth_url(scopes=[Scopes.GMAIL])
print(f"Visit: {auth_url}")

# Step 2: User authorizes and you receive callback with code
# Your web server captures the code parameter

# Step 3: Complete the flow
user_info = oauth_manager.complete_auth_flow(
    code='authorization_code_from_callback',
    scopes=[Scopes.GMAIL]
)
```

**Pros:**
- Production-ready with HTTPS
- Scalable for multiple users
- Works in web applications
- Full control over callback handling

**Cons:**
- Requires manual code copying/pasting (if not automated)
- More steps to implement

### Local Server Auth (Development)
**Use for:** Local scripts, testing, development, personal tools

```python
# One-step authentication
user_info = oauth_manager.authenticate_via_local_server(
    scopes=[Scopes.GMAIL]
)
# Browser opens, user authorizes, done!
```

**Pros:**
- Extremely simple one-liner
- Automatic browser handling
- No manual code copying
- Great developer experience
- Perfect for local automation

**Cons:**
- localhost only (NOT for production)
- Requires browser access
- Single-user scenarios only
- Must configure localhost in Google Console

## Service Documentation

Each service has detailed documentation with examples and API reference:

- **[Gmail Service](google_client/services/gmail/README.md)** - Email management and operations
- **[Google Drive Service](google_client/services/drive/README.md)** - File and folder management
- **[Google Calendar Service](google_client/services/calendar/README.md)** - Calendar and event management
- **[Google Tasks Service](google_client/services/tasks/README.md)** - Task and task list management

## Available Scopes

```python
from google_client.auth import Scopes

Scopes.GMAIL      # Full Gmail access
Scopes.DRIVE      # Full Drive access
Scopes.CALENDAR   # Full Calendar access
Scopes.TASKS      # Full Tasks access
```

## Token Refresh

```python
from google_client.auth import GoogleOAuthManager

# Refresh expired tokens
refreshed_token = GoogleOAuthManager.refresh_user_token(
    user_info=user_info,
    scopes=[Scopes.GMAIL, Scopes.DRIVE]
)

# Or use the built-in method on APIServiceLayer
api_service = APIServiceLayer(user_info)
refreshed_token = api_service.refresh_token()
```

## Links

- **[Google OAuth2 Documentation](https://developers.google.com/identity/protocols/oauth2/web-server#python)**
- **[Gmail API Reference](https://developers.google.com/gmail/api)**
- **[Drive API Reference](https://developers.google.com/drive/api)**
- **[Calendar API Reference](https://developers.google.com/calendar/api)**
- **[Tasks API Reference](https://developers.google.com/tasks/reference/rest)**

---

See individual service documentation for detailed usage examples and API references.
