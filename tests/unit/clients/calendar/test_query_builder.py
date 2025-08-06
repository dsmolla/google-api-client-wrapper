import pytest
from datetime import datetime, date, time, timedelta
from unittest.mock import Mock, patch
from src.google_api_client.clients.calendar.query_builder import EventQueryBuilder
from src.google_api_client.clients.calendar.client import CalendarEvent, Attendee
from src.google_api_client.utils.datetime import combine_with_timezone, date_start, date_end


class TestEventQueryBuilder:
    """Test cases for the EventQueryBuilder class."""
    
    def test_builder_creation(self):
        """Test creating a query builder."""
        builder = EventQueryBuilder(CalendarEvent)
        assert builder._calendar_event_class == CalendarEvent
        assert builder._number_of_results == 100  # DEFAULT_MAX_RESULTS
        assert builder._start is None
        assert builder._end is None
        assert builder._query is None
        assert builder._calendar_id == "primary"
    
    def test_limit_method(self):
        """Test limit method."""
        builder = EventQueryBuilder(CalendarEvent)
        result = builder.limit(50)
        
        assert result is builder  # Method chaining
        assert builder._number_of_results == 50
    
    def test_limit_validation(self):
        """Test limit method validation."""
        builder = EventQueryBuilder(CalendarEvent)
        
        with pytest.raises(ValueError, match="Limit must be between 1 and 2500"):
            builder.limit(0)
        
        with pytest.raises(ValueError, match="Limit must be between 1 and 2500"):
            builder.limit(3000)
    
    def test_date_methods(self):
        """Test from_date and to_date methods."""
        builder = EventQueryBuilder(CalendarEvent)
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
        builder = EventQueryBuilder(CalendarEvent)
        start_date = datetime(2025, 1, 15, 9, 0)
        end_date = datetime(2025, 1, 15, 17, 0)
        
        result = builder.in_date_range(start_date, end_date)
        
        assert result is builder
        assert builder._start == start_date
        assert builder._end == end_date
    
    def test_in_date_range_validation(self):
        """Test in_date_range validation."""
        builder = EventQueryBuilder(CalendarEvent)
        start_date = datetime(2025, 1, 15, 17, 0)
        end_date = datetime(2025, 1, 15, 9, 0)  # Before start
        
        with pytest.raises(ValueError, match="Start date must be before end date"):
            builder.in_date_range(start_date, end_date)
    
    def test_search_method(self):
        """Test search method."""
        builder = EventQueryBuilder(CalendarEvent)
        result = builder.search("meeting")
        
        assert result is builder
        assert builder._query == "meeting"
    
    def test_search_validation(self):
        """Test search method validation."""
        builder = EventQueryBuilder(CalendarEvent)
        long_query = "x" * 501  # MAX_QUERY_LENGTH + 1
        
        with pytest.raises(ValueError, match="Query string cannot exceed 500 characters"):
            builder.search(long_query)
    
    def test_in_calendar(self):
        """Test in_calendar method."""
        builder = EventQueryBuilder(CalendarEvent)
        result = builder.in_calendar("work@company.com")
        
        assert result is builder
        assert builder._calendar_id == "work@company.com"
    
    def test_filter_methods(self):
        """Test filtering methods."""
        builder = EventQueryBuilder(CalendarEvent)
        
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
        builder = EventQueryBuilder(CalendarEvent)
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
        builder = EventQueryBuilder(CalendarEvent)
        result = builder.tomorrow()
        
        assert result is builder
        tomorrow_date = date.today() + timedelta(days=1)
        assert builder._start.date() == tomorrow_date
        assert builder._end.date() == tomorrow_date
    
    def test_this_week_method(self):
        """Test this_week convenience method."""
        builder = EventQueryBuilder(CalendarEvent)
        result = builder.this_week()
        
        assert result is builder
        assert builder._start is not None
        assert builder._end is not None
        
        # Should span from Monday to Sunday
        days_diff = (builder._end.date() - builder._start.date()).days
        assert days_diff == 6  # Monday to Sunday is 6 days difference
    
    def test_this_month_method(self):
        """Test this_month convenience method."""
        builder = EventQueryBuilder(CalendarEvent)
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
        builder = EventQueryBuilder(CalendarEvent)
        result = builder.next_days(7)
        
        assert result is builder
        assert builder._start is not None
        assert builder._end is not None
        
        # Should span 7 days from today
        days_diff = (builder._end.date() - builder._start.date()).days
        assert days_diff == 7
    
    def test_next_days_validation(self):
        """Test next_days validation."""
        builder = EventQueryBuilder(CalendarEvent)
        
        with pytest.raises(ValueError, match="Days must be positive"):
            builder.next_days(0)
        
        with pytest.raises(ValueError, match="Days must be positive"):
            builder.next_days(-1)
    
    def test_last_days_method(self):
        """Test last_days convenience method."""
        builder = EventQueryBuilder(CalendarEvent)
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
        builder = EventQueryBuilder(CalendarEvent)
        builder.by_attendee("john@example.com")
        
        # Create test events
        attendee1 = Attendee(email="john@example.com")
        attendee2 = Attendee(email="jane@example.com")
        
        event1 = CalendarEvent(id="1", attendees=[attendee1])
        event2 = CalendarEvent(id="2", attendees=[attendee2])
        event3 = CalendarEvent(id="3", attendees=[attendee1, attendee2])
        
        events = [event1, event2, event3]
        filtered = builder._apply_post_filters(events)
        
        assert len(filtered) == 2  # event1 and event3
        assert filtered[0].id == "1"
        assert filtered[1].id == "3"
    
    def test_apply_post_filters_location(self):
        """Test post-filtering by location."""
        builder = EventQueryBuilder(CalendarEvent)
        builder.with_location()
        
        # Create test events
        event1 = CalendarEvent(id="1", location="Conference Room")
        event2 = CalendarEvent(id="2", location=None)
        event3 = CalendarEvent(id="3", location="")
        event4 = CalendarEvent(id="4", location="Office")
        
        events = [event1, event2, event3, event4]
        filtered = builder._apply_post_filters(events)
        
        assert len(filtered) == 2  # event1 and event4 (have non-empty locations)
        assert filtered[0].id == "1"
        assert filtered[1].id == "4"
    
    def test_apply_post_filters_without_location(self):
        """Test post-filtering for events without location."""
        builder = EventQueryBuilder(CalendarEvent)
        builder.without_location()
        
        # Create test events
        event1 = CalendarEvent(id="1", location="Conference Room")
        event2 = CalendarEvent(id="2", location=None)
        event3 = CalendarEvent(id="3", location="")
        
        events = [event1, event2, event3]
        filtered = builder._apply_post_filters(events)
        
        assert len(filtered) == 2  # event2 and event3 (no location)
        assert filtered[0].id == "2"
        assert filtered[1].id == "3"
    
    @patch.object(CalendarEvent, 'list_events')
    def test_execute(self, mock_list_events):
        """Test execute method."""
        # Setup mock
        mock_events = [
            CalendarEvent(id="1", summary="Meeting 1"),
            CalendarEvent(id="2", summary="Meeting 2")
        ]
        mock_list_events.return_value = mock_events
        
        # Test
        builder = EventQueryBuilder(CalendarEvent)
        builder.limit(50).search("meeting").in_calendar("test@example.com")
        
        result = builder.execute()
        
        # Assertions
        assert result == mock_events
        mock_list_events.assert_called_once_with(
            number_of_results=50,
            start=None,
            end=None,
            query="meeting",
            calendar_id="test@example.com"
        )
    
    @patch.object(CalendarEvent, 'list_events')
    def test_count(self, mock_list_events):
        """Test count method."""
        mock_events = [CalendarEvent(id="1"), CalendarEvent(id="2")]
        mock_list_events.return_value = mock_events
        
        builder = EventQueryBuilder(CalendarEvent)
        result = builder.count()
        
        assert result == 2
    
    @patch.object(CalendarEvent, 'list_events')
    def test_first(self, mock_list_events):
        """Test first method."""
        mock_events = [CalendarEvent(id="1"), CalendarEvent(id="2")]
        mock_list_events.return_value = mock_events
        
        builder = EventQueryBuilder(CalendarEvent)
        result = builder.first()
        
        assert result.id == "1"
        # Should limit to 1
        mock_list_events.assert_called_once()
        args = mock_list_events.call_args[1]
        assert args['number_of_results'] == 1
    
    @patch.object(CalendarEvent, 'list_events')
    def test_first_no_results(self, mock_list_events):
        """Test first method with no results."""
        mock_list_events.return_value = []
        
        builder = EventQueryBuilder(CalendarEvent)
        result = builder.first()
        
        assert result is None
    
    @patch.object(CalendarEvent, 'list_events')
    def test_exists(self, mock_list_events):
        """Test exists method."""
        mock_list_events.return_value = [CalendarEvent(id="1")]
        
        builder = EventQueryBuilder(CalendarEvent)
        result = builder.exists()
        
        assert result is True
        # Should limit to 1 for efficiency
        args = mock_list_events.call_args[1]
        assert args['number_of_results'] == 1
    
    @patch.object(CalendarEvent, 'list_events')
    def test_exists_no_results(self, mock_list_events):
        """Test exists method with no results."""
        mock_list_events.return_value = []
        
        builder = EventQueryBuilder(CalendarEvent)
        result = builder.exists()
        
        assert result is False
    
    def test_method_chaining(self):
        """Test that all methods support chaining."""
        builder = EventQueryBuilder(CalendarEvent)
        
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