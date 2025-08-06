import pytest
from datetime import datetime, date, time
from unittest.mock import Mock, patch, MagicMock
from src.google_api_client.clients.calendar.client import CalendarEvent, Attendee, CalendarError, CalendarPermissionError, CalendarNotFoundError
from src.google_api_client.utils.datetime import combine_with_timezone


class TestAttendee:
    """Test cases for the Attendee class."""
    
    def test_valid_attendee_creation(self):
        """Test creating a valid attendee."""
        attendee = Attendee(
            email="john@example.com",
            display_name="John Doe",
            response_status="accepted"
        )
        assert attendee.email == "john@example.com"
        assert attendee.display_name == "John Doe"
        assert attendee.response_status == "accepted"
    
    def test_attendee_minimal_creation(self):
        """Test creating attendee with only email."""
        attendee = Attendee(email="john@example.com")
        assert attendee.email == "john@example.com"
        assert attendee.display_name is None
        assert attendee.response_status is None
    
    def test_invalid_empty_email(self):
        """Test that empty email raises ValueError."""
        with pytest.raises(ValueError, match="Attendee email cannot be empty"):
            Attendee(email="")
    
    def test_invalid_email_format(self):
        """Test that invalid email format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid email format"):
            Attendee(email="invalid-email")
    
    def test_invalid_response_status(self):
        """Test that invalid response status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid response status"):
            Attendee(email="john@example.com", response_status="invalid")
    
    def test_valid_response_statuses(self):
        """Test all valid response statuses."""
        valid_statuses = ["needsAction", "declined", "tentative", "accepted"]
        for status in valid_statuses:
            attendee = Attendee(email="john@example.com", response_status=status)
            assert attendee.response_status == status
    
    def test_to_dict_full(self):
        """Test to_dict with all fields."""
        attendee = Attendee(
            email="john@example.com",
            display_name="John Doe", 
            response_status="accepted"
        )
        expected = {
            "email": "john@example.com",
            "displayName": "John Doe",
            "responseStatus": "accepted"
        }
        assert attendee.to_dict() == expected
    
    def test_to_dict_minimal(self):
        """Test to_dict with only email."""
        attendee = Attendee(email="john@example.com")
        expected = {"email": "john@example.com"}
        assert attendee.to_dict() == expected


class TestCalendarEvent:
    """Test cases for the CalendarEvent class."""
    
    def test_valid_event_creation(self, sample_datetime, sample_datetime_end):
        """Test creating a valid calendar event."""
        event = CalendarEvent(
            id="test_123",
            summary="Test Meeting",
            description="A test meeting",
            location="Test Room",
            start=sample_datetime,
            end=sample_datetime_end
        )
        assert event.id == "test_123"
        assert event.summary == "Test Meeting"
        assert event.description == "A test meeting"
        assert event.location == "Test Room"
        assert event.start == sample_datetime
        assert event.end == sample_datetime_end
    
    def test_event_minimal_creation(self):
        """Test creating event with minimal fields."""
        event = CalendarEvent()
        assert event.id is None
        assert event.summary is None
        assert event.attendees == []
        assert event.recurrence == []
    
    def test_invalid_datetime_range(self, sample_datetime):
        """Test that invalid datetime range raises ValueError."""
        with pytest.raises(ValueError, match="Event start time must be before end time"):
            CalendarEvent(start=sample_datetime, end=sample_datetime)
    
    def test_summary_too_long(self):
        """Test that overly long summary raises ValueError."""
        long_summary = "x" * 1025  # MAX_SUMMARY_LENGTH + 1
        with pytest.raises(ValueError, match="Event summary cannot exceed 1024 characters"):
            CalendarEvent(summary=long_summary)
    
    def test_description_too_long(self):
        """Test that overly long description raises ValueError."""
        long_description = "x" * 8193  # MAX_DESCRIPTION_LENGTH + 1
        with pytest.raises(ValueError, match="Event description cannot exceed 8192 characters"):
            CalendarEvent(description=long_description)
    
    def test_location_too_long(self):
        """Test that overly long location raises ValueError."""
        long_location = "x" * 1025  # MAX_LOCATION_LENGTH + 1
        with pytest.raises(ValueError, match="Event location cannot exceed 1024 characters"):
            CalendarEvent(location=long_location)
    
    def test_from_google_event(self, sample_google_event):
        """Test creating CalendarEvent from Google API response."""
        event = CalendarEvent._from_google_event(sample_google_event)
        
        assert event.id == "test_event_123"
        assert event.summary == "Test Meeting"
        assert event.description == "A test meeting for unit testing"
        assert event.location == "Test Room"
        assert event.htmlLink == "https://calendar.google.com/event?eid=test123"
        assert len(event.attendees) == 2
        assert event.attendees[0].email == "john@example.com"
        assert event.attendees[1].email == "jane@example.com"
        assert event.recurrence == ["RRULE:FREQ=WEEKLY;BYDAY=MO"]
        assert event.recurringEventId == "recurring_123"
    
    def test_from_google_event_invalid_attendee(self):
        """Test that invalid attendees are skipped during creation."""
        google_event = {
            "id": "test_123",
            "attendees": [
                {"email": "valid@example.com"},
                {"email": "invalid-email"},  # Invalid format
                {"email": ""},  # Empty email
            ]
        }
        event = CalendarEvent._from_google_event(google_event)
        assert len(event.attendees) == 1
        assert event.attendees[0].email == "valid@example.com"
    
    def test_to_dict(self, sample_datetime, sample_datetime_end):
        """Test converting event to dictionary."""
        attendee = Attendee(email="john@example.com")
        event = CalendarEvent(
            id="test_123",
            summary="Test Meeting",
            description="A test meeting",
            location="Test Room",
            start=sample_datetime,
            end=sample_datetime_end,
            attendees=[attendee],
            recurrence=["RRULE:FREQ=WEEKLY"]
        )
        
        result = event.to_dict()
        assert result["summary"] == "Test Meeting"
        assert result["description"] == "A test meeting"
        assert result["location"] == "Test Room"
        assert "start" in result
        assert "end" in result
        assert len(result["attendees"]) == 1
        assert result["attendees"][0]["email"] == "john@example.com"
        assert result["id"] == "test_123"
        assert result["recurrence"] == ["RRULE:FREQ=WEEKLY"]
    
    def test_to_dict_missing_datetime(self):
        """Test that to_dict raises error when start/end missing."""
        event = CalendarEvent(summary="Test")
        with pytest.raises(ValueError, match="Event must have both start and end times"):
            event.to_dict()
    
    def test_duration(self, sample_datetime, sample_datetime_end):
        """Test duration calculation."""
        event = CalendarEvent(start=sample_datetime, end=sample_datetime_end)
        assert event.duration() == 60  # 1 hour in minutes
    
    def test_duration_none(self):
        """Test duration returns None when dates missing."""
        event = CalendarEvent()
        assert event.duration() is None
    
    def test_is_today(self):
        """Test is_today method."""
        today = combine_with_timezone(date.today(), time(9, 0))
        event = CalendarEvent(start=today)
        assert event.is_today() is True
        
        # Test with different date
        yesterday = combine_with_timezone(date.today(), time(9, 0))
        yesterday = yesterday.replace(day=yesterday.day - 1)
        event2 = CalendarEvent(start=yesterday)
        assert event2.is_today() is False
    
    def test_is_all_day(self):
        """Test is_all_day method."""
        start = combine_with_timezone(date.today(), time.min)
        end = combine_with_timezone(date.today(), time.min).replace(day=start.day + 1)
        event = CalendarEvent(start=start, end=end)
        assert event.is_all_day() is True
        
        # Test non-all-day event
        start2 = combine_with_timezone(date.today(), time(9, 0))
        end2 = combine_with_timezone(date.today(), time(10, 0))
        event2 = CalendarEvent(start=start2, end=end2)
        assert event2.is_all_day() is False
    
    def test_conflicts_with(self, sample_datetime, sample_datetime_end): 
        """Test conflicts_with method."""
        event1 = CalendarEvent(start=sample_datetime, end=sample_datetime_end)
        
        # Overlapping event
        overlap_start = sample_datetime.replace(minute=30)
        overlap_end = sample_datetime_end.replace(minute=30)
        event2 = CalendarEvent(start=overlap_start, end=overlap_end)
        assert event1.conflicts_with(event2) is True
        
        # Non-overlapping event
        later_start = sample_datetime_end.replace(minute=1)
        later_end = later_start.replace(hour=later_start.hour + 1)
        event3 = CalendarEvent(start=later_start, end=later_end)
        assert event1.conflicts_with(event3) is False
    
    def test_attendee_methods(self):
        """Test attendee-related methods."""
        attendee1 = Attendee(email="john@example.com")
        attendee2 = Attendee(email="jane@example.com")
        event = CalendarEvent(attendees=[attendee1, attendee2])
        
        assert event.get_attendee_emails() == ["john@example.com", "jane@example.com"]
        assert event.has_attendee("john@example.com") is True
        assert event.has_attendee("missing@example.com") is False
    
    @patch('src.google_api_client.clients.calendar.client.calendar_service')
    def test_list_events(self, mock_context, sample_google_event):
        """Test list_events class method."""
        # Setup mock
        mock_service = Mock()
        mock_events = Mock()
        mock_service.events.return_value = mock_events
        mock_events.list.return_value.execute.return_value = {
            "items": [sample_google_event]
        }
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Test
        events = CalendarEvent.list_events(number_of_results=10)
        
        # Assertions
        assert len(events) == 1
        assert events[0].id == "test_event_123"
        assert events[0].summary == "Test Meeting"
        mock_events.list.assert_called_once()
    
    def test_list_events_validation(self):
        """Test list_events input validation."""
        with pytest.raises(ValueError, match="number_of_results must be between"):
            CalendarEvent.list_events(number_of_results=3000)
        
        with pytest.raises(ValueError, match="Query string cannot exceed"):
            CalendarEvent.list_events(query="x" * 501)
    
    @patch('src.google_api_client.clients.calendar.client.calendar_service')
    def test_get_event(self, mock_context, sample_google_event):
        """Test get_event class method."""
        # Setup mock
        mock_service = Mock()
        mock_events = Mock()
        mock_service.events.return_value = mock_events
        mock_events.get.return_value.execute.return_value = sample_google_event
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Test
        event = CalendarEvent.get_event("test_123")
        
        # Assertions
        assert event.id == "test_event_123"
        assert event.summary == "Test Meeting"
        mock_events.get.assert_called_once_with(calendarId="primary", eventId="test_123")
    
    @patch('src.google_api_client.clients.calendar.client.calendar_service')
    def test_create_event(self, mock_context, sample_datetime, sample_datetime_end, sample_google_event):
        """Test create_event class method."""
        # Setup mock
        mock_service = Mock()
        mock_events = Mock()
        mock_service.events.return_value = mock_events
        mock_events.insert.return_value.execute.return_value = sample_google_event
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Test
        event = CalendarEvent.create_event(
            start=sample_datetime,
            end=sample_datetime_end,
            summary="Test Meeting",
            location="Test Room"
        )
        
        # Assertions
        assert event.id == "test_event_123"
        assert event.summary == "Test Meeting"
        mock_events.insert.assert_called_once()
    
    def test_create_event_validation(self, sample_datetime):
        """Test create_event input validation."""
        with pytest.raises(ValueError, match="Event start time must be before end time"):
            CalendarEvent.create_event(start=sample_datetime, end=sample_datetime)
    
    @patch('src.google_api_client.clients.calendar.client.calendar_service')
    def test_sync_changes(self, mock_context, sample_datetime, sample_datetime_end):
        """Test sync_changes instance method."""
        # Setup mock
        mock_service = Mock()
        mock_events = Mock()
        mock_service.events.return_value = mock_events
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Test
        event = CalendarEvent(
            id="test_123",
            summary="Test Meeting",
            start=sample_datetime,
            end=sample_datetime_end
        )
        event.sync_changes()
        
        # Assertions
        mock_events.update.assert_called_once()
        call_args = mock_events.update.call_args
        assert call_args[1]['calendarId'] == "primary"
        assert call_args[1]['eventId'] == "test_123"
    
    @patch('src.google_api_client.clients.calendar.client.calendar_service')
    def test_delete_event(self, mock_context):
        """Test delete_event instance method."""
        # Setup mock
        mock_service = Mock()
        mock_events = Mock()
        mock_service.events.return_value = mock_events
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Test
        event = CalendarEvent(id="test_123")
        event.delete_event()
        
        # Assertions
        mock_events.delete.assert_called_once_with(calendarId="primary", eventId="test_123")
    
    @patch('src.google_api_client.clients.calendar.client.calendar_service')
    def test_update_methods(self, mock_context, sample_datetime, sample_datetime_end):
        """Test various update methods."""
        # Setup mock
        mock_service = Mock()
        mock_events = Mock()
        mock_service.events.return_value = mock_events
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Test event
        event = CalendarEvent(
            id="test_123",
            summary="Original",
            start=sample_datetime,
            end=sample_datetime_end
        )
        
        # Test update_summary
        event.update_summary("New Summary")
        assert event.summary == "New Summary"
        
        # Test update_description
        event.update_description("New Description")
        assert event.description == "New Description"
        
        # Test update_location
        event.update_location("New Location")
        assert event.location == "New Location"
        
        # All should trigger sync_changes (update API calls)
        assert mock_events.update.call_count == 3