import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from src.google_api_client.clients.calendar.client import CalendarEvent
from src.google_api_client.clients.calendar.async_client import AsyncCalendarEvent
from src.google_api_client.utils.datetime import today_start, days_from_today


@pytest.mark.integration
@pytest.mark.calendar
class TestCalendarIntegration:
    """Integration tests for calendar functionality with mocked API calls."""
    
    @patch('src.google_api_client.clients.calendar.client.calendar_service')
    def test_end_to_end_event_lifecycle(self, mock_context, sample_google_event):
        """Test complete event lifecycle: create, read, update, delete."""
        # Setup mock service
        mock_service = Mock()
        mock_events = Mock()
        mock_service.events.return_value = mock_events
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Mock responses for different operations
        created_event = sample_google_event.copy()
        created_event["id"] = "new_event_123"
        
        updated_event = created_event.copy()
        updated_event["summary"] = "Updated Meeting"
        
        mock_events.insert.return_value.execute.return_value = created_event
        mock_events.get.return_value.execute.return_value = created_event
        mock_events.update.return_value.execute.return_value = updated_event
        
        # Test: Create event
        start_time = today_start()
        end_time = start_time + timedelta(hours=1)
        
        event = CalendarEvent.create_event(
            start=start_time,
            end=end_time,
            summary="Test Meeting",
            description="Integration test meeting",
            location="Test Room",
            attendees=["test@example.com"]
        )
        
        assert event.id == "new_event_123"
        assert event.summary == "Test Meeting"
        mock_events.insert.assert_called_once()
        
        # Test: Get event
        retrieved_event = CalendarEvent.get_event(event.id)
        assert retrieved_event.id == event.id
        mock_events.get.assert_called_once_with(calendarId="primary", eventId=event.id)
        
        # Test: Update event
        event.update_summary("Updated Meeting")
        assert event.summary == "Updated Meeting"
        mock_events.update.assert_called_once()
        
        # Test: Delete event
        event.delete_event()
        mock_events.delete.assert_called_once_with(calendarId="primary", eventId=event.id)
    
    @patch('src.google_api_client.clients.calendar.client.calendar_service')
    def test_query_builder_integration(self, mock_context, sample_google_event):
        """Test query builder with complex filters."""
        # Setup mock
        mock_service = Mock()
        mock_events = Mock()
        mock_service.events.return_value = mock_events
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Create test events with different properties
        events_data = [
            {**sample_google_event, "id": "1", "summary": "Team Meeting", "location": "Conference Room"},
            {**sample_google_event, "id": "2", "summary": "Project Review", "location": None},
            {**sample_google_event, "id": "3", "summary": "Team Standup", "location": "Office"}
        ]
        mock_events.list.return_value.execute.return_value = {"items": events_data}
        
        # Test complex query
        results = (CalendarEvent.query()
                  .limit(50)
                  .today()
                  .search("team")
                  .with_location()
                  .execute())
        
        # Should find 2 events (both have locations and contain "team")
        assert len(results) == 2
        assert all("team" in event.summary.lower() for event in results)
        assert all(event.location for event in results)
        
        # Verify API was called correctly
        mock_events.list.assert_called_once()
        call_args = mock_events.list.call_args[1]
        assert call_args["q"] == "team"
        assert call_args["maxResults"] == 50
    
    @patch('src.google_api_client.clients.calendar.client.calendar_service')
    def test_attendee_management_integration(self, mock_context, sample_google_event):
        """Test attendee addition and removal."""
        # Setup mock
        mock_service = Mock()
        mock_events = Mock()
        mock_service.events.return_value = mock_events
        mock_context.return_value.__enter__.return_value = mock_service
        
        # Mock event with initial attendees
        event_data = sample_google_event.copy()
        mock_events.get.return_value.execute.return_value = event_data
        
        # Test: Get event and modify attendees
        event = CalendarEvent.get_event("test_123")
        initial_count = len(event.attendees)
        
        # Add attendee
        event.add_attendee("new@example.com")
        assert len(event.attendees) == initial_count + 1
        assert event.has_attendee("new@example.com")
        
        # Remove attendee
        event.remove_attendee("john@example.com")  # From sample_google_event
        assert not event.has_attendee("john@example.com")
        assert event.has_attendee("new@example.com")  # Still has the new one
        
        # Should have called sync_changes for both operations
        assert mock_events.update.call_count == 2


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncCalendarIntegration:
    """Integration tests for async calendar functionality."""
    
    @patch('src.google_api_client.clients.calendar.async_client.async_calendar_service')
    async def test_async_end_to_end_lifecycle(self, mock_context, sample_google_event):
        """Test complete async event lifecycle."""
        # Setup mock
        mock_aiogoogle = AsyncMock()
        mock_calendar_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_calendar_service)
        
        # Mock responses
        created_event = sample_google_event.copy()
        created_event["id"] = "async_event_123"
        mock_aiogoogle.as_user.return_value = created_event
        
        # Test: Create event
        start_time = today_start()
        end_time = start_time + timedelta(hours=1)
        
        event = await AsyncCalendarEvent.create_event(
            start=start_time,
            end=end_time,
            summary="Async Test Meeting",
            location="Virtual Room"
        )
        
        assert event.id == "async_event_123"
        assert event.summary == "Test Meeting"  # From sample_google_event
        
        # Test: Update event
        await event.update_summary("Updated Async Meeting")
        assert event.summary == "Updated Async Meeting"
        
        # Test: Delete event
        await event.delete_event()
        
        # Should have made 3 API calls (create, update, delete)
        assert mock_aiogoogle.as_user.call_count == 3
    
    @patch('src.google_api_client.clients.calendar.async_client.async_calendar_service')
    async def test_async_batch_operations(self, mock_context, sample_google_event):
        """Test async batch operations."""
        # Setup mock
        mock_aiogoogle = AsyncMock()
        mock_calendar_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_calendar_service)
        
        # Mock batch creation
        created_events = [
            {**sample_google_event, "id": f"batch_{i}", "summary": f"Batch Event {i}"}
            for i in range(3)
        ]
        mock_aiogoogle.as_user.side_effect = created_events
        
        # Test: Batch create events
        start_time = today_start()
        events_data = [
            {
                "start": start_time,
                "end": start_time + timedelta(hours=1),
                "summary": f"Batch Event {i}",
                "location": f"Room {i}"
            }
            for i in range(3)
        ]
        
        results = await AsyncCalendarEvent.batch_create_events(events_data)
        
        assert len(results) == 3
        assert all(event.id.startswith("batch_") for event in results)
        assert mock_aiogoogle.as_user.call_count == 3
    
    @patch('src.google_api_client.clients.calendar.async_client.async_calendar_service')
    async def test_async_query_builder_integration(self, mock_context, sample_google_event):
        """Test async query builder integration."""
        # Setup mock
        mock_aiogoogle = AsyncMock()
        mock_calendar_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_calendar_service)
        
        # Mock list response
        events_data = [
            {**sample_google_event, "id": "1", "summary": "Morning Standup"},
            {**sample_google_event, "id": "2", "summary": "Afternoon Review"}
        ]
        mock_aiogoogle.as_user.return_value = {"items": events_data}
        
        # Test: Complex async query
        results = await (AsyncCalendarEvent.query()
                        .limit(100)
                        .this_week()
                        .search("standup")
                        .execute())
        
        assert len(results) == 2
        mock_aiogoogle.as_user.assert_called_once()
    
    @patch('src.google_api_client.clients.calendar.async_client.async_calendar_service')
    async def test_async_multi_calendar_integration(self, mock_context, sample_google_event):
        """Test async multi-calendar operations."""
        # Setup mock
        mock_aiogoogle = AsyncMock()
        mock_calendar_service = Mock()
        mock_context.return_value.__aenter__.return_value = (mock_aiogoogle, mock_calendar_service)
        
        # Mock different responses for different calendars
        def mock_response(*args, **kwargs):
            # Simulate different events for different calendars
            calendar_method = args[0]  # The calendar service method
            if hasattr(calendar_method, '__self__'):
                return {"items": [{**sample_google_event, "id": "primary_1"}]}
            return {"items": [{**sample_google_event, "id": "work_1"}]}
        
        mock_aiogoogle.as_user.side_effect = mock_response
        
        # Test: Multi-calendar query
        calendar_ids = ["primary", "work@company.com"]
        results = await (AsyncCalendarEvent.query()
                        .today()
                        .execute_multiple_calendars(calendar_ids))
        
        assert len(results) == 2
        assert "primary" in results
        assert "work@company.com" in results
        assert mock_aiogoogle.as_user.call_count == 2


@pytest.mark.integration
class TestExceptionHandling:
    """Integration tests for exception handling."""
    
    @patch('src.google_api_client.clients.calendar.client.get_calendar_service')
    def test_calendar_permission_error_handling(self, mock_get_service):
        """Test handling of permission errors."""
        from googleapiclient.errors import HttpError
        from src.google_api_client.clients.calendar.client import CalendarPermissionError
        
        # Setup mock to raise 403 error
        mock_error_response = Mock()
        mock_error_response.status = 403
        http_error = HttpError(resp=mock_error_response, content=b'Permission denied')
        
        mock_get_service.side_effect = http_error
        
        # Test: Should raise CalendarPermissionError
        with pytest.raises(CalendarPermissionError):
            CalendarEvent.list_events()
    
    @patch('src.google_api_client.clients.calendar.client.get_calendar_service')
    def test_calendar_not_found_error_handling(self, mock_get_service):
        """Test handling of not found errors."""
        from googleapiclient.errors import HttpError
        from src.google_api_client.clients.calendar.client import CalendarNotFoundError
        
        # Setup mock to raise 404 error
        mock_error_response = Mock()
        mock_error_response.status = 404
        http_error = HttpError(resp=mock_error_response, content=b'Not found')
        
        mock_get_service.side_effect = http_error
        
        # Test: Should raise CalendarNotFoundError
        with pytest.raises(CalendarNotFoundError):
            CalendarEvent.get_event("nonexistent_id")
    
    @pytest.mark.asyncio
    @patch('src.google_api_client.clients.calendar.async_client.get_async_calendar_service')
    async def test_async_error_handling(self, mock_get_service):
        """Test async error handling."""
        from aiogoogle.excs import HTTPError
        from src.google_api_client.clients.calendar.async_client import AsyncCalendarPermissionError
        
        # Setup mock to raise async HTTP error
        mock_error_response = Mock()
        mock_error_response.status_code = 403
        http_error = HTTPError("Permission denied", res=mock_error_response)
        
        mock_get_service.return_value.__aenter__.side_effect = http_error
        
        # Test: Should raise AsyncCalendarPermissionError
        with pytest.raises(AsyncCalendarPermissionError):
            await AsyncCalendarEvent.list_events()


@pytest.mark.integration
class TestTimezoneIntegration:
    """Integration tests for timezone handling."""
    
    def test_timezone_consistency_across_operations(self, sample_datetime, sample_datetime_end):
        """Test that timezone handling is consistent across all operations."""
        from src.google_api_client.utils.datetime import today_start, today_end, days_from_today
        
        # All these should return timezone-aware datetimes
        timezone_aware_dates = [
            today_start(),
            today_end(),
            days_from_today(1),
            days_from_today(-1)
        ]
        
        # All should have the same timezone
        base_tz = timezone_aware_dates[0].tzinfo
        for dt in timezone_aware_dates:
            assert dt.tzinfo == base_tz
            assert dt.tzinfo is not None
        
        # Should be able to compare all of them without errors
        start = today_start()
        end = today_end()
        tomorrow = days_from_today(1)
        
        assert start < end
        assert start < tomorrow
        assert end < tomorrow
    
    @patch('src.google_api_client.clients.calendar.client.calendar_service')
    def test_builder_timezone_integration(self, mock_context, sample_google_event):
        """Test that query builder timezone methods work correctly."""
        # Setup mock
        mock_service = Mock()
        mock_events = Mock()
        mock_service.events.return_value = mock_events
        mock_context.return_value.__enter__.return_value = mock_service
        mock_events.list.return_value.execute.return_value = {"items": [sample_google_event]}
        
        # Test various time-based queries
        builders = [
            CalendarEvent.query().today(),
            CalendarEvent.query().tomorrow(),
            CalendarEvent.query().this_week(),
            CalendarEvent.query().this_month(),
            CalendarEvent.query().next_days(7),
            CalendarEvent.query().last_days(3)
        ]
        
        for builder in builders:
            # All should have timezone-aware start/end times
            assert builder._start is not None
            assert builder._end is not None
            assert builder._start.tzinfo is not None
            assert builder._end.tzinfo is not None
            assert builder._start < builder._end
            
            # Should be able to execute without timezone errors
            results = builder.execute()
            assert isinstance(results, list)