from datetime import datetime, date, time, timedelta
from typing import Optional, List, TYPE_CHECKING
from ...utils.datetime import date_start, date_end, days_from_today
from .constants import MAX_RESULTS_LIMIT, MAX_QUERY_LENGTH, DEFAULT_MAX_RESULTS, DEFAULT_CALENDAR_ID

if TYPE_CHECKING:
    from .types import CalendarEvent
    from .api_service import CalendarApiService


class EventQueryBuilder:
    """
    Builder pattern for constructing calendar event queries with a fluent API.
    Provides a clean, readable way to build complex event queries.
    
    Example usage:
        events = (CalendarEvent.query()
            .limit(50)
            .in_date_range(start_date, end_date)
            .search("meeting")
            .in_calendar("work@company.com")
            .execute())
    """
    
    def __init__(self, api_service: "CalendarApiService"):
        self._api_service = api_service
        self._max_results: Optional[int] = DEFAULT_MAX_RESULTS
        self._start: Optional[datetime] = None
        self._end: Optional[datetime] = None
        self._query: Optional[str] = None
        self._calendar_id: str = DEFAULT_CALENDAR_ID
        self._attendee_filter: Optional[str] = None
        self._has_location_filter: Optional[bool] = None
        self._single_events_only: bool = True
        
    def limit(self, count: int) -> "EventQueryBuilder":
        """
        Set the maximum number of events to retrieve.
        Args:
            count: Maximum number of events (1-2500)
        Returns:
            Self for method chaining
        """
        if count < 1 or count > MAX_RESULTS_LIMIT:
            raise ValueError(f"Limit must be between 1 and {MAX_RESULTS_LIMIT}")
        self._max_results = count
        return self
        
    def from_date(self, start: datetime) -> "EventQueryBuilder":
        """
        Set the start date/time for the query.
        Args:
            start: Start datetime
        Returns:
            Self for method chaining
        """
        self._start = start
        return self
        
    def to_date(self, end: datetime) -> "EventQueryBuilder":
        """
        Set the end date/time for the query.
        Args:
            end: End datetime
        Returns:
            Self for method chaining
        """
        self._end = end
        return self
        
    def in_date_range(self, start: datetime, end: datetime) -> "EventQueryBuilder":
        """
        Set both start and end dates for the query.
        Args:
            start: Start datetime
            end: End datetime
        Returns:
            Self for method chaining
        """
        if start >= end:
            raise ValueError("Start date must be before end date")
        self._start = start
        self._end = end
        return self
        
    def search(self, query: str) -> "EventQueryBuilder":
        """
        Add a text search query to filter events.
        Args:
            query: Search string for event content
        Returns:
            Self for method chaining
        """
        if len(query) > MAX_QUERY_LENGTH:
            raise ValueError(f"Query string cannot exceed {MAX_QUERY_LENGTH} characters")
        self._query = query
        return self
        
    def in_calendar(self, calendar_id: str) -> "EventQueryBuilder":
        """
        Specify which calendar to query.
        Args:
            calendar_id: Calendar identifier
        Returns:
            Self for method chaining
        """
        self._calendar_id = calendar_id
        return self
    
    def by_attendee(self, email: str) -> "EventQueryBuilder":
        """
        Filter events by attendee email.
        Args:
            email: Attendee email address
        Returns:
            Self for method chaining
        """
        self._attendee_filter = email
        return self
        
    def with_location(self) -> "EventQueryBuilder":
        """
        Filter to only events that have a location specified.
        Returns:
            Self for method chaining
        """
        self._has_location_filter = True
        return self
        
    def without_location(self) -> "EventQueryBuilder":
        """
        Filter to only events that do not have a location specified.
        Returns:
            Self for method chaining
        """
        self._has_location_filter = False
        return self
        
    # Convenience date methods
    def today(self) -> "EventQueryBuilder":
        """
        Filter to events happening today.
        Returns:
            Self for method chaining
        """
        today = date.today()
        start_of_day = date_start(today)
        end_of_day = date_end(today)
        return self.in_date_range(start_of_day, end_of_day)
        
    def tomorrow(self) -> "EventQueryBuilder":
        """
        Filter to events happening tomorrow.
        Returns:
            Self for method chaining
        """
        tomorrow = date.today() + timedelta(days=1)
        start_of_day = date_start(tomorrow)
        end_of_day = date_end(tomorrow)
        return self.in_date_range(start_of_day, end_of_day)
        
    def this_week(self) -> "EventQueryBuilder":
        """
        Filter to events happening this week (Monday to Sunday).
        Returns:
            Self for method chaining
        """
        today = date.today()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        sunday = monday + timedelta(days=6)
        
        start_of_week = date_start(monday)
        end_of_week = date_end(sunday)
        return self.in_date_range(start_of_week, end_of_week)
        
    def next_week(self) -> "EventQueryBuilder":
        """
        Filter to events happening next week (Monday to Sunday).
        Returns:
            Self for method chaining
        """
        today = date.today()
        days_since_monday = today.weekday()
        next_monday = today + timedelta(days=(7 - days_since_monday))
        next_sunday = next_monday + timedelta(days=6)
        
        start_of_week = date_start(next_monday)
        end_of_week = date_end(next_sunday)
        return self.in_date_range(start_of_week, end_of_week)
        
    def this_month(self) -> "EventQueryBuilder":
        """
        Filter to events happening this month.
        Returns:
            Self for method chaining
        """
        today = date.today()
        first_day = date(today.year, today.month, 1)
        
        # Calculate last day of month
        if today.month == 12:
            last_day = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(today.year, today.month + 1, 1) - timedelta(days=1)
            
        start_of_month = date_start(first_day)
        end_of_month = date_end(last_day)
        return self.in_date_range(start_of_month, end_of_month)
        
    def next_days(self, days: int) -> "EventQueryBuilder":
        """
        Filter to events happening in the next N days.
        Args:
            days: Number of days from today
        Returns:
            Self for method chaining
        """
        if days < 1:
            raise ValueError("Days must be positive")
            
        start = days_from_today(0)  # Start of today
        end = days_from_today(days)
        return self.in_date_range(start, end)
        
    def last_days(self, days: int) -> "EventQueryBuilder":
        """
        Filter to events that happened in the last N days.
        Args:
            days: Number of days before today
        Returns:
            Self for method chaining
        """
        if days < 1:
            raise ValueError("Days must be positive")
            
        end = date_end(date.today())
        start = days_from_today(-days)
        return self.in_date_range(start, end)
        
    def _apply_post_filters(self, events: List["CalendarEvent"]) -> List["CalendarEvent"]:
        """
        Apply client-side filters that can't be handled by the API.
        Args:
            events: List of events from API
        Returns:
            Filtered list of events
        """
        filtered = events
        
        # Filter by attendee
        if self._attendee_filter:
            filtered = [event for event in filtered if event.has_attendee(self._attendee_filter)]
            
        # Filter by location presence
        if self._has_location_filter is not None:
            if self._has_location_filter:
                filtered = [event for event in filtered if event.location]
            else:
                filtered = [event for event in filtered if not event.location]
                
        return filtered
        
    def execute(self) -> List["CalendarEvent"]:
        """
        Execute the query and return the results.
        Returns:
            List of CalendarEvent objects matching the criteria
        Raises:
            ValueError: If query parameters are invalid
        """
        
        # Use the service layer implementation
        events = self._api_service.list_events(
            max_results=self._max_results,
            start=self._start,
            end=self._end,
            query=self._query,
            calendar_id=self._calendar_id,
            single_events=self._single_events_only
        )
        
        # Apply any client-side filters
        filtered_events = self._apply_post_filters(events)
        
        return filtered_events
        
    def count(self) -> int:
        """
        Execute the query and return only the count of matching events.
        Returns:
            Number of events matching the criteria
        """
        return len(self.execute())
        
    def first(self) -> Optional["CalendarEvent"]:
        """
        Execute the query and return only the first matching event.
        Returns:
            First CalendarEvent or None if no matches
        """
        events = self.limit(1).execute()
        return events[0] if events else None
        
    def exists(self) -> bool:
        """
        Check if any events match the criteria without retrieving them.
        Returns:
            True if at least one event matches, False otherwise
        """
        return self.limit(1).count() > 0
        
    def __repr__(self):
        return f"EventQueryBuilder(query='{self._query}', limit={self._max_results}, calendar_id='{self._calendar_id}')"