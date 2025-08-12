# Google API Client

A comprehensive Python wrapper for Google APIs, providing clean and intuitive access to Gmail, Google Drive, Google Calendar, and Google Tasks services.

## Features

- **Gmail Service**: Send, receive, search, and manage emails
- **Google Drive Service**: Upload, download, and manage files and folders
- **Google Calendar Service**: Create, update, and manage calendar events
- **Google Tasks Service**: Manage tasks and task lists
- **OAuth2 Authentication**: Secure authentication flow
- **Query Builders**: Intuitive query building for each service
- **Multi-User Authentication**: Supports multiple users to be authenticated

## Installation


## Quick Start

```python
from src.google_api_client.user_client import UserClient
from datetime import datetime, timedelta

# Authenticate User
user_1 = UserClient.from_file("< user_1_token_path >", "< app_credentials_path >")
user_2, user_2_token = UserClient.from_credentials_info({"< user_2_token_dict >": 1}, {"< app_credentials_dict >": 2})

# List User 1's emails
user_1_emails = user_1.gmail.list_emails()

# Create a calendar event for User 2
user_2_event = user_2.calendar.create_event(datetime.now(), datetime.now() + timedelta(hours=1))
```

## Package Documentation

Each service has detailed documentation with examples and API reference:

- **[Gmail Service](src/google_api_client/services/gmail/README.md)** - Email management and operations
- **[Google Drive Service](src/google_api_client/services/drive/README.md)** - File and folder management
- **[Google Calendar Service](src/google_api_client/services/calendar/README.md)** - Calendar and event management
- **[Google Tasks Service](src/google_api_client/services/tasks/README.md)** - Task and task list management

## License

See individual package documentation for detailed usage examples and API references.