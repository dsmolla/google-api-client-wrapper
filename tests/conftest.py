import pytest
import sys
from datetime import datetime, date
from pathlib import Path
from unittest.mock import Mock, patch

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture
def mock_calendar_service():
    """Mock calendar service for testing."""
    mock_service = Mock()
    mock_events = Mock()
    mock_service.events.return_value = mock_events
    return mock_service

@pytest.fixture
def sample_google_event():
    """Sample Google Calendar API event response."""
    return {
        "id": "test_event_123",
        "summary": "Test Meeting",
        "description": "A test meeting for unit testing",
        "location": "Test Room",
        "start": {"dateTime": "2025-01-15T09:00:00-05:00"},
        "end": {"dateTime": "2025-01-15T10:00:00-05:00"},
        "htmlLink": "https://calendar.google.com/event?eid=test123",
        "attendees": [
            {
                "email": "john@example.com",
                "displayName": "John Doe",
                "responseStatus": "accepted"
            },
            {
                "email": "jane@example.com", 
                "displayName": "Jane Smith",
                "responseStatus": "tentative"
            }
        ],
        "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO"],
        "recurringEventId": "recurring_123"
    }

@pytest.fixture
def sample_datetime():
    """Sample timezone-aware datetime for testing."""
    from src.google_api_client.utils.datetime import combine_with_timezone
    return combine_with_timezone(date(2025, 1, 15), datetime.min.time().replace(hour=9))

@pytest.fixture
def sample_datetime_end():
    """Sample end datetime for testing."""
    from src.google_api_client.utils.datetime import combine_with_timezone
    return combine_with_timezone(date(2025, 1, 15), datetime.min.time().replace(hour=10))

@pytest.fixture
def mock_get_calendar_service(mock_calendar_service):
    """Mock the calendar_service context manager."""
    with patch('src.google_api_client.clients.calendar.client.calendar_service') as mock_context:
        mock_context.return_value.__enter__.return_value = mock_calendar_service
        mock_context.return_value.__exit__.return_value = None
        yield mock_context

@pytest.fixture
def mock_get_async_calendar_service(mock_async_calendar_context):
    """Mock the async calendar service context manager."""
    with patch('src.google_api_client.clients.calendar.async_client.async_calendar_service') as mock_context:
        mock_context.return_value.__aenter__.return_value = mock_async_calendar_context
        mock_context.return_value.__aexit__.return_value = None
        yield mock_context

@pytest.fixture
def mock_async_calendar_context():
    """Mock async calendar service context with aiogoogle and service."""
    from unittest.mock import AsyncMock
    mock_aiogoogle = AsyncMock()
    mock_calendar_service = Mock()
    return mock_aiogoogle, mock_calendar_service

# Gmail-specific fixtures
@pytest.fixture
def mock_gmail_service():
    """Mock Gmail service for testing."""
    mock_service = Mock()
    mock_users = Mock()
    mock_service.users.return_value = mock_users
    return mock_service

@pytest.fixture
def sample_gmail_message():
    """Sample Gmail API message response."""
    return {
        "id": "msg_123",
        "threadId": "thread_456",
        "snippet": "This is a test email snippet...",
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Subject", "value": "Test Email Subject"},
                {"name": "Date", "value": "Mon, 15 Jan 2025 09:00:00 -0500"},
                {"name": "Message-ID", "value": "<msg123@example.com>"}
            ],
            "body": {
                "data": "VGhpcyBpcyBhIHRlc3QgZW1haWwgYm9keS4="  # Base64: "This is a test email body."
            },
            "mimeType": "text/plain"
        }
    }

@pytest.fixture
def sample_email_address():
    """Sample email address for testing."""
    from src.google_api_client.clients.gmail.client import EmailAddress
    return EmailAddress(email="test@example.com", name="Test User")

@pytest.fixture
def sample_async_email_address():
    """Sample async email address for testing."""
    from src.google_api_client.clients.gmail.async_client import AsyncEmailAddress
    return AsyncEmailAddress(email="test@example.com", name="Test User")

@pytest.fixture
def sample_email_attachment():
    """Sample email attachment for testing."""
    from src.google_api_client.clients.gmail.client import EmailAttachment
    return EmailAttachment(
        filename="test.pdf",
        content_type="application/pdf",
        size=1024,
        attachment_id="att_123",
        message_id="msg_456"
    )

@pytest.fixture
def sample_gmail_label():
    """Sample Gmail label for testing."""
    return {
        "id": "label_123",
        "name": "Important",
        "type": "user"
    }

@pytest.fixture
def mock_get_gmail_service(mock_gmail_service):
    """Mock the gmail_service context manager."""
    with patch('src.google_api_client.clients.gmail.client.gmail_service') as mock_context:
        mock_context.return_value.__enter__.return_value = mock_gmail_service
        mock_context.return_value.__exit__.return_value = None
        yield mock_context

@pytest.fixture
def mock_get_async_gmail_service(mock_async_gmail_context):
    """Mock the async Gmail service context manager."""
    with patch('src.google_api_client.clients.gmail.async_client.async_gmail_service') as mock_context:
        mock_context.return_value.__aenter__.return_value = mock_async_gmail_context
        mock_context.return_value.__aexit__.return_value = None
        yield mock_context

@pytest.fixture
def mock_async_gmail_context():
    """Mock async Gmail service context with aiogoogle and service."""
    from unittest.mock import AsyncMock
    mock_aiogoogle = AsyncMock()
    mock_gmail_service = Mock()
    return mock_aiogoogle, mock_gmail_service

# Auth manager fixtures for error handling tests
@pytest.fixture
def mock_auth_manager_get_calendar_service():
    """Mock the auth manager get_calendar_service method."""
    with patch('src.google_api_client.auth.manager.auth_manager.get_calendar_service') as mock:
        yield mock

@pytest.fixture  
def mock_auth_manager_get_async_calendar_service():
    """Mock the auth manager get_async_calendar_service method."""
    with patch('src.google_api_client.auth.manager.auth_manager.get_async_calendar_service') as mock:
        yield mock

# Tasks-specific fixtures
@pytest.fixture
def mock_tasks_service():
    """Mock tasks service for testing."""
    mock_service = Mock()
    mock_tasks = Mock()
    mock_tasklists = Mock()
    mock_service.tasks.return_value = mock_tasks
    mock_service.tasklists.return_value = mock_tasklists
    return mock_service

@pytest.fixture
def sample_task_response():
    """Sample Google Tasks API task response."""
    return {
        "id": "task_123",
        "title": "Sample Task",
        "notes": "This is a sample task for testing",
        "status": "needsAction",
        "due": "2025-01-20T00:00:00.000Z",
        "updated": "2025-01-15T10:00:00.000Z"
    }

@pytest.fixture
def sample_task_list_response():
    """Sample Google Tasks API task list response."""
    return {
        "id": "list_123",
        "title": "Sample Task List",
        "updated": "2025-01-15T10:00:00.000Z"
    }

@pytest.fixture
def mock_get_tasks_service(mock_tasks_service):
    """Mock the tasks_service context manager."""
    with patch('src.google_api_client.clients.tasks.client.tasks_service') as mock_context:
        mock_context.return_value.__enter__.return_value = mock_tasks_service
        mock_context.return_value.__exit__.return_value = None
        yield mock_context

@pytest.fixture
def mock_get_async_tasks_service(mock_async_tasks_context):
    """Mock the async tasks service context manager."""
    with patch('src.google_api_client.clients.tasks.async_client.async_tasks_service') as mock_context:
        mock_context.return_value.__aenter__.return_value = mock_async_tasks_context
        mock_context.return_value.__aexit__.return_value = None
        yield mock_context

@pytest.fixture
def mock_async_tasks_context():
    """Mock async tasks service context with aiogoogle and service."""
    from unittest.mock import AsyncMock
    mock_aiogoogle = AsyncMock()
    mock_tasks_service = Mock()
    return mock_aiogoogle, mock_tasks_service