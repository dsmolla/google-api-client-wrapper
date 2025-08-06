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
def mock_get_calendar_service():
    """Mock the get_calendar_service function."""
    with patch('src.google_api_client.auth.oauth.get_calendar_service') as mock:
        yield mock

@pytest.fixture
def mock_get_async_calendar_service():
    """Mock the async calendar service context manager."""
    with patch('src.google_api_client.auth.credentials.get_async_calendar_service') as mock:
        yield mock