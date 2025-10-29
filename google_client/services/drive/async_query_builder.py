from typing import List

from .query_builder import DriveQueryBuilder
from .async_api_service import AsyncDriveApiService
from .types import DriveItem


class AsyncDriveQueryBuilder(DriveQueryBuilder):
    """
    Async version of DriveQueryBuilder for building complex file queries with a fluent API.
    Inherits all filter methods from DriveQueryBuilder and overrides execution method to be async.
    """

    def __init__(self, api_service: AsyncDriveApiService, timezone: str = "UTC"):
        super().__init__(api_service, timezone)

    async def execute(self) -> List[DriveItem]:
        """
        Execute the query asynchronously and return results.
        Returns:
            List of DriveItem objects matching the query
        """
        query = self._build_query()

        return await self._api_service.list(
            query=query,
            max_results=self._max_results,
            order_by=self._order_by,
        )
