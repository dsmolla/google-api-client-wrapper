from datetime import datetime, date, timedelta
from typing import Optional, List, Self

from .constants import MAX_RESULTS_LIMIT, MAX_QUERY_LENGTH, DEFAULT_MAX_RESULTS, DEFAULT_CALENDAR_ID
from ...utils.datetime import current_datetime

from .types import CalendarEvent
from .api_service import CalendarApiService
from .async_api_service import AsyncCalendarApiService


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

    def __init__(self, api_service: CalendarApiService | AsyncCalendarApiService, timezone: str):
        self._api_service = api_service
        self._max_results: Optional[int] = DEFAULT_MAX_RESULTS
        self._start: Optional[datetime] = None
        self._end: Optional[datetime] = None
        self._query: Optional[str] = None
        self._calendar_id: str = DEFAULT_CALENDAR_ID
        self._attendee_filter: Optional[str] = None
        self._has_location_filter: Optional[bool] = None
        self._single_events_only: bool = True

        self._timezone = timezone

    def limit(self, count: int) -> Self:
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

    def from_date(self, start: datetime) -> Self:
        """
        Set the start date/time for the query.
        Args:
            start: Start datetime
        Returns:
            Self for method chaining
        """
        self._start = start
        return self

    def to_date(self, end: datetime) -> Self:
        """
        Set the end date/time for the query.
        Args:
            end: End datetime
        Returns:
            Self for method chaining
        """
        self._end = end
        return self

    def in_date_range(self, start: datetime, end: datetime) -> Self:
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

    def search(self, query: str) -> Self:
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

    def in_calendar(self, calendar_id: str) -> Self:
        """
        Specify which calendar to query.
        Args:
            calendar_id: Calendar identifier
        Returns:
            Self for method chaining
        """
        self._calendar_id = calendar_id
        return self

    def by_attendee(self, email: str) -> Self:
        """
        Filter events by attendee email.
        Args:
            email: Attendee email address
        Returns:
            Self for method chaining
        """
        self._attendee_filter = email
        return self

    def with_location(self) -> Self:
        """
        Filter to only events that have a location specified.
        Returns:
            Self for method chaining
        """
        self._has_location_filter = True
        return self

    def without_location(self) -> Self:
        """
        Filter to only events that do not have a location specified.
        Returns:
            Self for method chaining
        """
        self._has_location_filter = False
        return self

    def today(self) -> Self:
        """
        Filter to events happening today.
        Returns:
            Self for method chaining
        """
        today = current_datetime(self._timezone).date()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        return self.in_date_range(start_of_day, end_of_day)

    def tomorrow(self) -> Self:
        """
        Filter to events happening tomorrow.
        Returns:
            Self for method chaining
        """
        tomorrow = current_datetime(self._timezone).date() + timedelta(days=1)
        start_of_day = datetime.combine(tomorrow, datetime.min.time())
        end_of_day = datetime.combine(tomorrow, datetime.max.time())
        return self.in_date_range(start_of_day, end_of_day)

    def this_week(self) -> Self:
        """
        Filter to events happening this week (Monday to Sunday).
        Returns:
            Self for method chaining
        """
        today = current_datetime(self._timezone).date()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        sunday = monday + timedelta(days=6)

        start_of_week = datetime.combine(monday, datetime.min.time())
        end_of_week = datetime.combine(sunday, datetime.max.time())
        return self.in_date_range(start_of_week, end_of_week)

    def next_week(self) -> Self:
        """
        Filter to events happening next week (Monday to Sunday).
        Returns:
            Self for method chaining
        """
        today = current_datetime(self._timezone).date()
        days_since_monday = today.weekday()
        next_monday = today + timedelta(days=(7 - days_since_monday))
        next_sunday = next_monday + timedelta(days=6)

        start_of_week = datetime.combine(next_monday, datetime.min.time())
        end_of_week = datetime.combine(next_sunday, datetime.max.time())
        return self.in_date_range(start_of_week, end_of_week)

    def this_month(self) -> Self:
        """
        Filter to events happening this month.
        Returns:
            Self for method chaining
        """
        today = current_datetime(self._timezone).date()
        first_day = date(today.year, today.month, 1)

        # Calculate last day of month
        if today.month == 12:
            last_day = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(today.year, today.month + 1, 1) - timedelta(days=1)

        start_of_month = datetime.combine(first_day, datetime.min.time())
        end_of_month = datetime.combine(last_day, datetime.max.time())
        return self.in_date_range(start_of_month, end_of_month)

    def next_days(self, days: int) -> Self:
        """
        Filter to events happening in the next N days.
        Args:
            days: Number of days from today
        Returns:
            Self for method chaining
        """
        if days < 1:
            raise ValueError("Days must be positive")

        start = current_datetime(self._timezone).date()
        start = datetime.combine(start, datetime.min.time())
        end = start + timedelta(days=days)
        end = datetime.combine(end, datetime.max.time())
        return self.in_date_range(start, end)

    def last_days(self, days: int) -> Self:
        """
        Filter to events that happened in the last N days.
        Args:
            days: Number of days before today
        Returns:
            Self for method chaining
        """
        if days < 1:
            raise ValueError("Days must be positive")

        end = current_datetime(self._timezone).date()
        end = datetime.combine(end, datetime.max.time())
        start = end - timedelta(days=days)
        start = datetime.combine(start, datetime.min.time())
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
