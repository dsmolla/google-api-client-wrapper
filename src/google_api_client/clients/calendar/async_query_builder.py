import asyncio
from datetime import datetime, date, time, timedelta
from typing import Optional, List, TYPE_CHECKING
import logging
from ...utils.datetime import date_start, date_end, days_from_today

if TYPE_CHECKING:
    from .async_client import AsyncCalendarEvent

logger = logging.getLogger(__name__)

# Constants (imported from async_calendar_client)
MAX_RESULTS_LIMIT = 2500
MAX_QUERY_LENGTH = 500
DEFAULT_MAX_RESULTS = 100


class AsyncEventQueryBuilder:
    """
    Async builder pattern for constructing calendar event queries with a fluent API.
    Provides a clean, readable way to build complex event queries asynchronously.
    
    Example usage:
        events = await (AsyncCalendarEvent.query()
            .limit(50)
            .in_date_range(start_date, end_date)
            .search("meeting")
            .in_calendar("work@company.com")
            .execute())
    """
    
    def __init__(self, async_calendar_event_class):
        self._async_calendar_event_class = async_calendar_event_class
        self._number_of_results: Optional[int] = DEFAULT_MAX_RESULTS
        self._start: Optional[datetime] = None
        self._end: Optional[datetime] = None
        self._query: Optional[str] = None
        self._calendar_id: str = "primary"
        self._attendee_filter: Optional[str] = None
        self._has_location_filter: Optional[bool] = None
        self._single_events_only: bool = True  # Default from original API
        
    def limit(self, count: int) -> "AsyncEventQueryBuilder":
        """
        Set the maximum number of events to retrieve.
        Args:
            count: Maximum number of events (1-2500)
        Returns:
            Self for method chaining
        """
        if count < 1 or count > MAX_RESULTS_LIMIT:
            raise ValueError(f"Limit must be between 1 and {MAX_RESULTS_LIMIT}")
        self._number_of_results = count
        return self
        
    def from_date(self, start: datetime) -> "AsyncEventQueryBuilder":
        """
        Set the start date/time for the query.
        Args:
            start: Start datetime
        Returns:
            Self for method chaining
        """
        self._start = start
        return self
        
    def to_date(self, end: datetime) -> "AsyncEventQueryBuilder":
        """
        Set the end date/time for the query.
        Args:
            end: End datetime
        Returns:
            Self for method chaining
        """
        self._end = end
        return self
        
    def in_date_range(self, start: datetime, end: datetime) -> "AsyncEventQueryBuilder":
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
        
    def search(self, query: str) -> "AsyncEventQueryBuilder":
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
        
    def in_calendar(self, calendar_id: str) -> "AsyncEventQueryBuilder":
        """
        Specify which calendar to query.
        Args:
            calendar_id: Calendar identifier
        Returns:
            Self for method chaining
        """
        self._calendar_id = calendar_id
        return self
    
    def by_attendee(self, email: str) -> "AsyncEventQueryBuilder":
        """
        Filter events by attendee email.
        Args:
            email: Attendee email address
        Returns:
            Self for method chaining
        """
        self._attendee_filter = email
        return self
        
    def with_location(self) -> "AsyncEventQueryBuilder":
        """
        Filter to only events that have a location specified.
        Returns:
            Self for method chaining
        """
        self._has_location_filter = True
        return self
        
    def without_location(self) -> "AsyncEventQueryBuilder":
        """
        Filter to only events that do not have a location specified.
        Returns:
            Self for method chaining
        """
        self._has_location_filter = False
        return self
        
    # Convenience date methods
    def today(self) -> "AsyncEventQueryBuilder":
        """
        Filter to events happening today.
        Returns:
            Self for method chaining
        """
        today = date.today()
        start_of_day = date_start(today)
        end_of_day = date_end(today)
        return self.in_date_range(start_of_day, end_of_day)
        
    def tomorrow(self) -> "AsyncEventQueryBuilder":
        """
        Filter to events happening tomorrow.
        Returns:
            Self for method chaining
        """
        tomorrow = date.today() + timedelta(days=1)
        start_of_day = date_start(tomorrow)
        end_of_day = date_end(tomorrow)
        return self.in_date_range(start_of_day, end_of_day)
        
    def this_week(self) -> "AsyncEventQueryBuilder":
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
        
    def next_week(self) -> "AsyncEventQueryBuilder":
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
        
    def this_month(self) -> "AsyncEventQueryBuilder":
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
        
    def next_days(self, days: int) -> "AsyncEventQueryBuilder":
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
        
    def last_days(self, days: int) -> "AsyncEventQueryBuilder":
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
        
    def _apply_post_filters(self, events: List["AsyncCalendarEvent"]) -> List["AsyncCalendarEvent"]:
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
        
    async def execute(self) -> List["AsyncCalendarEvent"]:
        """
        Execute the query asynchronously and return the results.
        Returns:
            List of AsyncCalendarEvent objects matching the criteria
        Raises:
            ValueError: If query parameters are invalid
            AsyncCalendarError: If API call fails
        """
        logger.info("Executing async event query with builder")
        
        # Use the original async list_events method
        events = await self._async_calendar_event_class.list_events(
            number_of_results=self._number_of_results,
            start=self._start,
            end=self._end,
            query=self._query,
            calendar_id=self._calendar_id,
        )
        
        # Apply any client-side filters
        filtered_events = self._apply_post_filters(events)
        
        logger.info("Async builder query returned %d events (filtered from %d)", 
                   len(filtered_events), len(events))
        return filtered_events
        
    async def count(self) -> int:
        """
        Execute the query asynchronously and return only the count of matching events.
        Returns:
            Number of events matching the criteria
        """
        events = await self.execute()
        return len(events)
        
    async def first(self) -> Optional["AsyncCalendarEvent"]:
        """
        Execute the query asynchronously and return only the first matching event.
        Returns:
            First AsyncCalendarEvent or None if no matches
        """
        events = await self.limit(1).execute()
        return events[0] if events else None
        
    async def exists(self) -> bool:
        """
        Check asynchronously if any events match the criteria without retrieving them.
        Returns:
            True if at least one event matches, False otherwise
        """
        count = await self.limit(1).count()
        return count > 0
        
    # Async batch operations using the builder pattern
    async def execute_multiple_calendars(self, calendar_ids: List[str]) -> dict:
        """
        Execute the same query across multiple calendars concurrently.
        Args:
            calendar_ids: List of calendar IDs to query
        Returns:
            Dictionary mapping calendar_id to list of events
        """
        logger.info("Executing builder query across %d calendars", len(calendar_ids))
        
        async def query_calendar(calendar_id: str):
            # Create a copy of this builder for the specific calendar
            builder_copy = AsyncEventQueryBuilder(self._async_calendar_event_class)
            builder_copy._number_of_results = self._number_of_results
            builder_copy._start = self._start
            builder_copy._end = self._end
            builder_copy._query = self._query
            builder_copy._calendar_id = calendar_id
            builder_copy._attendee_filter = self._attendee_filter
            builder_copy._has_location_filter = self._has_location_filter
            builder_copy._single_events_only = self._single_events_only
            
            return await builder_copy.execute()
        
        # Execute queries concurrently
        tasks = [query_calendar(calendar_id) for calendar_id in calendar_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build result dictionary, handling any exceptions
        calendar_events = {}
        for i, result in enumerate(results):
            calendar_id = calendar_ids[i]
            if isinstance(result, Exception):
                logger.error("Failed to query calendar %s: %s", calendar_id, result)
                raise result  # Re-raise the exception
            calendar_events[calendar_id] = result
            
        return calendar_events