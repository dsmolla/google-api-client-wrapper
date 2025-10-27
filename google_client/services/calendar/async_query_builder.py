from typing import Optional, List

from . import EventQueryBuilder
from .async_api_service import AsyncCalendarApiService
from .types import CalendarEvent


class AsyncEventQueryBuilder(EventQueryBuilder):
    def __init__(self, api_service: AsyncCalendarApiService, timezone: str):
        super().__init__(api_service, timezone)

    async def execute(self) -> List[CalendarEvent]:
        events = await self._api_service.list_events(
            max_results=self._max_results,
            start=self._start,
            end=self._end,
            query=self._query,
            calendar_id=self._calendar_id,
            single_events=self._single_events_only
        )

        filtered_events = self._apply_post_filters(events)

        return filtered_events

    async def count(self) -> int:
        return len(await self.execute())

    async def first(self) -> Optional[CalendarEvent]:
        events = await self.limit(1).execute()
        return events[0] if events else None

    async def exists(self) -> bool:
        return await self.limit(1).count() > 0

    def __repr__(self):
        return f"EventQueryBuilder(query='{self._query}', limit={self._max_results}, calendar_id='{self._calendar_id}')"
