import pytest
import asyncio
from datetime import datetime, date, time, timedelta
from unittest.mock import Mock, patch, AsyncMock
from google_client.async_event_query_builder import AsyncEventQueryBuilder
from google_client.async_calendar_client import AsyncCalendarEvent, AsyncAttendee


class TestAsyncEventQueryBuilder:
    """Test cases for the AsyncEventQueryBuilder class."""
    
    def test_builder_creation(self):
        """Test creating an async query builder."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        assert builder._async_calendar_event_class == AsyncCalendarEvent
        assert builder._number_of_results == 100  # DEFAULT_MAX_RESULTS
        assert builder._start is None
        assert builder._end is None
        assert builder._query is None
        assert builder._calendar_id == "primary"
    
    def test_limit_method(self):
        """Test limit method."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        result = builder.limit(50)
        
        assert result is builder  # Method chaining
        assert builder._number_of_results == 50
    
    def test_limit_validation(self):
        """Test limit method validation."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        
        with pytest.raises(ValueError, match="Limit must be between 1 and 2500"):
            builder.limit(0)
        
        with pytest.raises(ValueError, match="Limit must be between 1 and 2500"):
            builder.limit(3000)
    
    def test_date_methods(self):
        """Test from_date and to_date methods."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        start_date = datetime(2025, 1, 15, 9, 0)
        end_date = datetime(2025, 1, 15, 17, 0)
        
        result1 = builder.from_date(start_date)
        result2 = builder.to_date(end_date)
        
        assert result1 is builder
        assert result2 is builder
        assert builder._start == start_date
        assert builder._end == end_date
    
    def test_in_date_range(self):
        """Test in_date_range method."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        start_date = datetime(2025, 1, 15, 9, 0)
        end_date = datetime(2025, 1, 15, 17, 0)
        
        result = builder.in_date_range(start_date, end_date)
        
        assert result is builder
        assert builder._start == start_date
        assert builder._end == end_date
    
    def test_in_date_range_validation(self):
        """Test in_date_range validation."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        start_date = datetime(2025, 1, 15, 17, 0)
        end_date = datetime(2025, 1, 15, 9, 0)  # Before start
        
        with pytest.raises(ValueError, match="Start date must be before end date"):
            builder.in_date_range(start_date, end_date)
    
    def test_search_method(self):
        """Test search method."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        result = builder.search("meeting")
        
        assert result is builder
        assert builder._query == "meeting"
    
    def test_search_validation(self):
        """Test search method validation."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        long_query = "x" * 501  # MAX_QUERY_LENGTH + 1
        
        with pytest.raises(ValueError, match="Query string cannot exceed 500 characters"):
            builder.search(long_query)
    
    def test_in_calendar(self):
        """Test in_calendar method."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        result = builder.in_calendar("work@company.com")
        
        assert result is builder
        assert builder._calendar_id == "work@company.com"
    
    def test_filter_methods(self):
        """Test filtering methods."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        
        result1 = builder.by_attendee("john@example.com")
        result2 = builder.with_location()
        result3 = builder.without_location()
        
        assert result1 is builder
        assert result2 is builder
        assert result3 is builder
        
        assert builder._attendee_filter == "john@example.com"
        assert builder._has_location_filter is False  # Last call wins
    
    def test_today_method(self):
        """Test today convenience method."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        result = builder.today()
        
        assert result is builder
        # Should set start to beginning of today and end to end of today
        assert builder._start is not None
        assert builder._end is not None
        assert builder._start.date() == date.today()
        assert builder._end.date() == date.today()
        assert builder._start.time() == time.min
        assert builder._end.time() == time.max
    
    def test_tomorrow_method(self):
        """Test tomorrow convenience method."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        result = builder.tomorrow()
        
        assert result is builder
        tomorrow_date = date.today() + timedelta(days=1)
        assert builder._start.date() == tomorrow_date
        assert builder._end.date() == tomorrow_date
    
    def test_this_week_method(self):
        """Test this_week convenience method."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        result = builder.this_week()
        
        assert result is builder
        assert builder._start is not None
        assert builder._end is not None
        
        # Should span from Monday to Sunday
        days_diff = (builder._end.date() - builder._start.date()).days
        assert days_diff == 6  # Monday to Sunday is 6 days difference
    
    def test_this_month_method(self):
        """Test this_month convenience method."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        result = builder.this_month()
        
        assert result is builder
        assert builder._start is not None
        assert builder._end is not None
        
        # Should be first and last day of current month
        today = date.today()
        assert builder._start.date().year == today.year
        assert builder._start.date().month == today.month
        assert builder._start.date().day == 1
        assert builder._end.date().year == today.year
        assert builder._end.date().month == today.month
    
    def test_next_days_method(self):
        """Test next_days convenience method."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        result = builder.next_days(7)
        
        assert result is builder
        assert builder._start is not None
        assert builder._end is not None
        
        # Should span 7 days from today
        days_diff = (builder._end.date() - builder._start.date()).days
        assert days_diff == 7
    
    def test_next_days_validation(self):
        """Test next_days validation."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        
        with pytest.raises(ValueError, match="Days must be positive"):
            builder.next_days(0)
        
        with pytest.raises(ValueError, match="Days must be positive"):
            builder.next_days(-1)
    
    def test_last_days_method(self):
        """Test last_days convenience method."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        result = builder.last_days(7)
        
        assert result is builder
        assert builder._start is not None
        assert builder._end is not None
        
        # End should be today, start should be 7 days ago
        assert builder._end.date() == date.today()
        days_diff = (builder._end.date() - builder._start.date()).days
        assert days_diff == 7
    
    def test_apply_post_filters_attendee(self):
        """Test post-filtering by attendee."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        builder.by_attendee("john@example.com")
        
        # Create test events
        attendee1 = AsyncAttendee(email="john@example.com")
        attendee2 = AsyncAttendee(email="jane@example.com")
        
        event1 = AsyncCalendarEvent(id="1", attendees=[attendee1])
        event2 = AsyncCalendarEvent(id="2", attendees=[attendee2])
        event3 = AsyncCalendarEvent(id="3", attendees=[attendee1, attendee2])
        
        events = [event1, event2, event3]
        filtered = builder._apply_post_filters(events)
        
        assert len(filtered) == 2  # event1 and event3
        assert filtered[0].id == "1"
        assert filtered[1].id == "3"
    
    def test_apply_post_filters_location(self):
        """Test post-filtering by location."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        builder.with_location()
        
        # Create test events
        event1 = AsyncCalendarEvent(id="1", location="Conference Room")
        event2 = AsyncCalendarEvent(id="2", location=None)
        event3 = AsyncCalendarEvent(id="3", location="")
        event4 = AsyncCalendarEvent(id="4", location="Office")
        
        events = [event1, event2, event3, event4]
        filtered = builder._apply_post_filters(events)
        
        assert len(filtered) == 2  # event1 and event4 (have non-empty locations)
        assert filtered[0].id == "1"
        assert filtered[1].id == "4"
    
    @pytest.mark.asyncio
    @patch.object(AsyncCalendarEvent, 'list_events')
    async def test_execute(self, mock_list_events):
        """Test execute method."""
        # Setup mock
        mock_events = [
            AsyncCalendarEvent(id="1", summary="Meeting 1"),
            AsyncCalendarEvent(id="2", summary="Meeting 2")
        ]
        mock_list_events.return_value = mock_events
        
        # Test
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        builder.limit(50).search("meeting").in_calendar("test@example.com")
        
        result = await builder.execute()
        
        # Assertions
        assert result == mock_events
        mock_list_events.assert_called_once_with(
            number_of_results=50,
            start=None,
            end=None,
            query="meeting",
            calendar_id="test@example.com"
        )
    
    @pytest.mark.asyncio
    @patch.object(AsyncCalendarEvent, 'list_events')
    async def test_count(self, mock_list_events):
        """Test count method."""
        mock_events = [AsyncCalendarEvent(id="1"), AsyncCalendarEvent(id="2")]
        mock_list_events.return_value = mock_events
        
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        result = await builder.count()
        
        assert result == 2
    
    @pytest.mark.asyncio
    @patch.object(AsyncCalendarEvent, 'list_events')
    async def test_first(self, mock_list_events):
        """Test first method."""
        mock_events = [AsyncCalendarEvent(id="1"), AsyncCalendarEvent(id="2")]
        mock_list_events.return_value = mock_events
        
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        result = await builder.first()
        
        assert result.id == "1"
        # Should limit to 1
        mock_list_events.assert_called_once()
        args = mock_list_events.call_args[1]
        assert args['number_of_results'] == 1
    
    @pytest.mark.asyncio
    @patch.object(AsyncCalendarEvent, 'list_events')
    async def test_first_no_results(self, mock_list_events):
        """Test first method with no results."""
        mock_list_events.return_value = []
        
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        result = await builder.first()
        
        assert result is None
    
    @pytest.mark.asyncio
    @patch.object(AsyncCalendarEvent, 'list_events')
    async def test_exists(self, mock_list_events):
        """Test exists method."""
        mock_list_events.return_value = [AsyncCalendarEvent(id="1")]
        
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        result = await builder.exists()
        
        assert result is True
        # Should limit to 1 for efficiency
        args = mock_list_events.call_args[1]
        assert args['number_of_results'] == 1
    
    @pytest.mark.asyncio
    @patch.object(AsyncCalendarEvent, 'list_events')
    async def test_exists_no_results(self, mock_list_events):
        """Test exists method with no results."""
        mock_list_events.return_value = []
        
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        result = await builder.exists()
        
        assert result is False
    
    @pytest.mark.asyncio
    @patch.object(AsyncCalendarEvent, 'list_events')
    async def test_execute_multiple_calendars(self, mock_list_events):
        """Test execute_multiple_calendars method."""
        # Setup mock to return different events for different calendars
        def side_effect(*args, **kwargs):
            calendar_id = kwargs.get('calendar_id', 'primary')
            if calendar_id == 'primary':
                return [AsyncCalendarEvent(id="1", summary="Event 1")]
            else:
                return [AsyncCalendarEvent(id="2", summary="Event 2")]
        
        mock_list_events.side_effect = side_effect
        
        # Test
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        builder.search("meeting")
        
        calendar_ids = ["primary", "work@company.com"]
        result = await builder.execute_multiple_calendars(calendar_ids)
        
        # Assertions
        assert len(result) == 2
        assert "primary" in result
        assert "work@company.com" in result
        assert len(result["primary"]) == 1
        assert len(result["work@company.com"]) == 1
        assert result["primary"][0].id == "1"
        assert result["work@company.com"][0].id == "2"
        assert mock_list_events.call_count == 2
    
    @pytest.mark.asyncio
    async def test_execute_multiple_calendars_exception_handling(self):
        """Test that execute_multiple_calendars handles exceptions properly."""
        with patch.object(AsyncCalendarEvent, 'list_events') as mock_list:
            # Make the second call raise an exception
            mock_list.side_effect = [
                [AsyncCalendarEvent(id="1")],
                Exception("API Error")
            ]
            
            builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
            calendar_ids = ["primary", "work@company.com"]
            
            # Should re-raise the exception
            with pytest.raises(Exception, match="API Error"):
                await builder.execute_multiple_calendars(calendar_ids)
    
    def test_method_chaining(self):
        """Test that all methods support chaining."""
        builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
        
        # This should not raise any errors and return the builder
        result = (builder
                 .limit(50)
                 .search("meeting")
                 .in_calendar("work@example.com")
                 .by_attendee("john@example.com")
                 .with_location()
                 .today())
        
        assert result is builder
        assert builder._number_of_results == 50
        assert builder._query == "meeting"
        assert builder._calendar_id == "work@example.com"
        assert builder._attendee_filter == "john@example.com"
        assert builder._has_location_filter is True
    
    @pytest.mark.asyncio
    async def test_builder_with_complex_query(self):
        """Test builder with a complex, realistic query."""
        with patch.object(AsyncCalendarEvent, 'list_events') as mock_list:
            # Create events with attendees for attendee filtering
            event1 = AsyncCalendarEvent(id="1", summary="Team Meeting", location="Conference Room A")
            event1.attendees = [AsyncAttendee(email="manager@company.com")]
            
            event2 = AsyncCalendarEvent(id="2", summary="Project Review", location="Office B")
            event2.attendees = [AsyncAttendee(email="manager@company.com")]
            
            # Event without location to be filtered out
            event3 = AsyncCalendarEvent(id="3", summary="Other Meeting", location=None)
            event3.attendees = [AsyncAttendee(email="manager@company.com")]
            
            mock_events = [event1, event2, event3]
            mock_list.return_value = mock_events
            
            builder = AsyncEventQueryBuilder(AsyncCalendarEvent)
            
            # Build a complex query
            events = await (builder
                           .limit(100)
                           .this_week()
                           .search("meeting")
                           .in_calendar("work@company.com")
                           .by_attendee("manager@company.com")
                           .with_location()
                           .execute())
            
            # Should call list_events with proper parameters
            mock_list.assert_called_once()
            call_kwargs = mock_list.call_args[1]
            assert call_kwargs['number_of_results'] == 100
            assert call_kwargs['query'] == "meeting"
            assert call_kwargs['calendar_id'] == "work@company.com"
            assert call_kwargs['start'] is not None
            assert call_kwargs['end'] is not None
            
            # Post-filtering should be applied
            assert len(events) == 2  # Both events have locations