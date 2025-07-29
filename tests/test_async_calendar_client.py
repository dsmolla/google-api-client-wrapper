import pytest
import asyncio
from datetime import datetime, date, time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from google_client.async_calendar_client import AsyncCalendarEvent, AsyncAttendee, AsyncCalendarError, AsyncCalendarPermissionError, AsyncCalendarNotFoundError
from utils.datetime_util import combine_with_timezone


class TestAsyncAttendee:
    """Test cases for the AsyncAttendee class."""
    
    def test_valid_attendee_creation(self):
        """Test creating a valid async attendee."""
        attendee = AsyncAttendee(
            email="john@example.com",
            display_name="John Doe",
            response_status="accepted"
        )
        assert attendee.email == "john@example.com"
        assert attendee.display_name == "John Doe"
        assert attendee.response_status == "accepted"
    
    def test_attendee_minimal_creation(self):
        """Test creating attendee with only email."""
        attendee = AsyncAttendee(email="john@example.com")
        assert attendee.email == "john@example.com"
        assert attendee.display_name is None
        assert attendee.response_status is None
    
    def test_invalid_empty_email(self):
        """Test that empty email raises ValueError."""
        with pytest.raises(ValueError, match="Attendee email cannot be empty"):
            AsyncAttendee(email="")
    
    def test_invalid_email_format(self):
        """Test that invalid email format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid email format"):
            AsyncAttendee(email="invalid-email")
    
    def test_invalid_response_status(self):
        """Test that invalid response status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid response status"):
            AsyncAttendee(email="john@example.com", response_status="invalid")
    
    def test_to_dict_full(self):
        """Test to_dict with all fields."""
        attendee = AsyncAttendee(
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


class TestAsyncCalendarEvent:
    """Test cases for the AsyncCalendarEvent class."""
    
    def test_valid_event_creation(self, sample_datetime, sample_datetime_end):
        """Test creating a valid async calendar event."""
        event = AsyncCalendarEvent(
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
        event = AsyncCalendarEvent()
        assert event.id is None
        assert event.summary is None
        assert event.attendees == []
        assert event.recurrence == []
    
    def test_invalid_datetime_range(self, sample_datetime):
        """Test that invalid datetime range raises ValueError."""
        with pytest.raises(ValueError, match="Event start time must be before end time"):
            AsyncCalendarEvent(start=sample_datetime, end=sample_datetime)
    
    def test_from_google_event(self, sample_google_event):
        """Test creating AsyncCalendarEvent from Google API response."""
        event = AsyncCalendarEvent._from_google_event(sample_google_event)
        
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
    
    def test_to_dict(self, sample_datetime, sample_datetime_end):
        """Test converting event to dictionary."""
        attendee = AsyncAttendee(email="john@example.com")
        event = AsyncCalendarEvent(
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
    
    def test_utility_methods(self, sample_datetime, sample_datetime_end):
        """Test utility methods like duration, is_today, etc."""
        event = AsyncCalendarEvent(start=sample_datetime, end=sample_datetime_end)
        
        # Test duration
        assert event.duration() == 60  # 1 hour in minutes
        
        # Test attendee methods
        attendee1 = AsyncAttendee(email="john@example.com")
        attendee2 = AsyncAttendee(email="jane@example.com")
        event.attendees = [attendee1, attendee2]
        
        assert event.get_attendee_emails() == ["john@example.com", "jane@example.com"]
        assert event.has_attendee("john@example.com") is True
        assert event.has_attendee("missing@example.com") is False
    
    @pytest.mark.asyncio
    @patch('google_client.async_calendar_client.async_calendar_service')
    async def test_list_events(self, mock_context, sample_google_event):
        """Test list_events async class method."""
        # Setup mock
        mock_aiogoogle = AsyncMock()
        mock_calendar_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_calendar_service)
        mock_aiogoogle.as_user.return_value = {"items": [sample_google_event]}
        
        # Test
        events = await AsyncCalendarEvent.list_events(number_of_results=10)
        
        # Assertions
        assert len(events) == 1
        assert events[0].id == "test_event_123"
        assert events[0].summary == "Test Meeting"
        mock_aiogoogle.as_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_events_validation(self):
        """Test list_events input validation."""
        with pytest.raises(ValueError, match="number_of_results must be between"):
            await AsyncCalendarEvent.list_events(number_of_results=3000)
        
        with pytest.raises(ValueError, match="Query string cannot exceed"):
            await AsyncCalendarEvent.list_events(query="x" * 501)
    
    @pytest.mark.asyncio
    @patch('google_client.async_calendar_client.async_calendar_service')
    async def test_get_event(self, mock_context, sample_google_event):
        """Test get_event async class method."""
        # Setup mock
        mock_aiogoogle = AsyncMock()
        mock_calendar_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_calendar_service)
        mock_aiogoogle.as_user.return_value = sample_google_event
        
        # Test
        event = await AsyncCalendarEvent.get_event("test_123")
        
        # Assertions
        assert event.id == "test_event_123"
        assert event.summary == "Test Meeting"
        mock_aiogoogle.as_user.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('google_client.async_calendar_client.async_calendar_service')
    async def test_create_event(self, mock_context, sample_datetime, sample_datetime_end, sample_google_event):
        """Test create_event async class method."""
        # Setup mock
        mock_aiogoogle = AsyncMock()
        mock_calendar_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_calendar_service)
        mock_aiogoogle.as_user.return_value = sample_google_event
        
        # Test
        event = await AsyncCalendarEvent.create_event(
            start=sample_datetime,
            end=sample_datetime_end,
            summary="Test Meeting",
            location="Test Room"
        )
        
        # Assertions
        assert event.id == "test_event_123"
        assert event.summary == "Test Meeting"
        mock_aiogoogle.as_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_event_validation(self, sample_datetime):
        """Test create_event input validation."""
        with pytest.raises(ValueError, match="Event start time must be before end time"):
            await AsyncCalendarEvent.create_event(start=sample_datetime, end=sample_datetime)
    
    @pytest.mark.asyncio
    @patch('google_client.async_calendar_client.async_calendar_service')
    async def test_sync_changes(self, mock_context, sample_datetime, sample_datetime_end):
        """Test sync_changes async instance method."""
        # Setup mock
        mock_aiogoogle = AsyncMock()
        mock_calendar_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_calendar_service)
        
        # Test
        event = AsyncCalendarEvent(
            id="test_123",
            summary="Test Meeting",
            start=sample_datetime,
            end=sample_datetime_end
        )
        await event.sync_changes()
        
        # Assertions
        mock_aiogoogle.as_user.assert_called_once()
        call_args = mock_aiogoogle.as_user.call_args[0][0]
        # Check that it's calling the update method on the calendar service
        assert hasattr(call_args, '__call__')  # It's a callable (method)
    
    @pytest.mark.asyncio
    @patch('google_client.async_calendar_client.async_calendar_service')
    async def test_delete_event(self, mock_context):
        """Test delete_event async instance method."""
        # Setup mock
        mock_aiogoogle = AsyncMock()
        mock_calendar_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_calendar_service)
        
        # Test
        event = AsyncCalendarEvent(id="test_123")
        await event.delete_event()
        
        # Assertions
        mock_aiogoogle.as_user.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('google_client.async_calendar_client.async_calendar_service')
    async def test_update_methods(self, mock_context, sample_datetime, sample_datetime_end):
        """Test various async update methods."""
        # Setup mock
        mock_aiogoogle = AsyncMock()
        mock_calendar_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_calendar_service)
        
        # Test event
        event = AsyncCalendarEvent(
            id="test_123",
            summary="Original",
            start=sample_datetime,
            end=sample_datetime_end
        )
        
        # Test update_summary
        await event.update_summary("New Summary")
        assert event.summary == "New Summary"
        
        # Test update_description
        await event.update_description("New Description")
        assert event.description == "New Description"
        
        # Test update_location
        await event.update_location("New Location")
        assert event.location == "New Location"
        
        # All should trigger sync_changes (async update API calls)
        assert mock_aiogoogle.as_user.call_count == 3
    
    @pytest.mark.asyncio
    @patch('google_client.async_calendar_client.async_calendar_service')
    async def test_add_remove_attendee(self, mock_context, sample_datetime, sample_datetime_end):
        """Test add_attendee and remove_attendee async methods."""
        # Setup mock
        mock_aiogoogle = AsyncMock()
        mock_calendar_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_calendar_service)
        
        # Test event
        event = AsyncCalendarEvent(
            id="test_123",
            start=sample_datetime,
            end=sample_datetime_end
        )
        
        # Test add_attendee
        await event.add_attendee("john@example.com")
        assert len(event.attendees) == 1
        assert event.attendees[0].email == "john@example.com"
        
        # Test remove_attendee
        await event.remove_attendee("john@example.com")
        assert len(event.attendees) == 0
        
        # Should trigger sync_changes for both operations
        assert mock_aiogoogle.as_user.call_count == 2
    
    @pytest.mark.asyncio
    @patch.object(AsyncCalendarEvent, 'create_event')
    async def test_batch_create_events(self, mock_create):
        """Test batch_create_events method."""
        # Setup mock
        mock_events = [
            AsyncCalendarEvent(id="1", summary="Event 1"),
            AsyncCalendarEvent(id="2", summary="Event 2")
        ]
        mock_create.side_effect = mock_events
        
        # Test data
        events_data = [
            {"start": datetime.now(), "end": datetime.now(), "summary": "Event 1"},
            {"start": datetime.now(), "end": datetime.now(), "summary": "Event 2"}
        ]
        
        # Test
        result = await AsyncCalendarEvent.batch_create_events(events_data)
        
        # Assertions
        assert len(result) == 2
        assert result[0].id == "1"
        assert result[1].id == "2"
        assert mock_create.call_count == 2
    
    @pytest.mark.asyncio
    @patch.object(AsyncCalendarEvent, 'get_event')
    async def test_batch_get_events(self, mock_get):
        """Test batch_get_events method."""
        # Setup mock
        mock_events = [
            AsyncCalendarEvent(id="1", summary="Event 1"),
            AsyncCalendarEvent(id="2", summary="Event 2")
        ]
        mock_get.side_effect = mock_events
        
        # Test
        result = await AsyncCalendarEvent.batch_get_events(["1", "2"])
        
        # Assertions
        assert len(result) == 2
        assert result[0].id == "1"
        assert result[1].id == "2"
        assert mock_get.call_count == 2
    
    @pytest.mark.asyncio
    @patch('google_client.async_calendar_client.async_calendar_service')
    async def test_batch_update_events(self, mock_context, sample_datetime, sample_datetime_end):
        """Test batch_update_events method."""
        # Setup mock
        mock_aiogoogle = AsyncMock()
        mock_calendar_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_calendar_service)
        
        # Test events
        events = [
            AsyncCalendarEvent(id="1", summary="Event 1", start=sample_datetime, end=sample_datetime_end),
            AsyncCalendarEvent(id="2", summary="Event 2", start=sample_datetime, end=sample_datetime_end)
        ]
        
        # Test
        await AsyncCalendarEvent.batch_update_events(events)
        
        # Should call sync_changes for each event (2 calls total)
        assert mock_aiogoogle.as_user.call_count == 2
    
    @pytest.mark.asyncio
    @patch('google_client.async_calendar_client.async_calendar_service')
    async def test_batch_delete_events(self, mock_context):
        """Test batch_delete_events method."""
        # Setup mock
        mock_aiogoogle = AsyncMock()
        mock_calendar_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_calendar_service)
        
        # Test
        await AsyncCalendarEvent.batch_delete_events(["1", "2"])
        
        # Should call delete for each event (2 calls total)
        assert mock_aiogoogle.as_user.call_count == 2
    
    @pytest.mark.asyncio
    @patch.object(AsyncCalendarEvent, 'list_events')
    async def test_concurrent_list_multiple_calendars(self, mock_list):
        """Test concurrent_list_multiple_calendars method."""
        # Setup mock
        mock_events1 = [AsyncCalendarEvent(id="1", summary="Event 1")]
        mock_events2 = [AsyncCalendarEvent(id="2", summary="Event 2")]
        mock_list.side_effect = [mock_events1, mock_events2]
        
        # Test
        calendar_ids = ["primary", "work@company.com"]
        result = await AsyncCalendarEvent.concurrent_list_multiple_calendars(calendar_ids)
        
        # Assertions
        assert len(result) == 2
        assert "primary" in result
        assert "work@company.com" in result
        assert len(result["primary"]) == 1
        assert len(result["work@company.com"]) == 1
        assert mock_list.call_count == 2
    
    @pytest.mark.asyncio
    async def test_batch_operation_exception_handling(self):
        """Test that batch operations handle exceptions properly."""
        with patch.object(AsyncCalendarEvent, 'create_event') as mock_create:
            # Make the second call raise an exception
            mock_create.side_effect = [
                AsyncCalendarEvent(id="1"),
                Exception("API Error")
            ]
            
            events_data = [
                {"start": datetime.now(), "end": datetime.now(), "summary": "Event 1"},
                {"start": datetime.now(), "end": datetime.now(), "summary": "Event 2"}
            ]
            
            # Should raise AsyncCalendarError due to the exception
            with pytest.raises(AsyncCalendarError, match="Failed to create event"):
                await AsyncCalendarEvent.batch_create_events(events_data)