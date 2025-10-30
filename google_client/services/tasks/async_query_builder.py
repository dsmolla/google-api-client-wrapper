from typing import Optional, List

from .async_api_service import AsyncTasksApiService
from .query_builder import TaskQueryBuilder
from .types import Task


class AsyncTaskQueryBuilder(TaskQueryBuilder):
    """
    Async version of TaskQueryBuilder for building complex task queries with a fluent API.
    Inherits all filter methods from TaskQueryBuilder and overrides execution methods to be async.
    """

    def __init__(self, api_service: AsyncTasksApiService, timezone: str):
        super().__init__(api_service, timezone)

    async def execute(self) -> List[Task]:
        """
        Execute the query asynchronously and return the results.
        Returns:
            List of Task objects matching the criteria
        Raises:
            ValueError: If query parameters are invalid
        """
        tasks = await self._api_service.list_tasks(
            task_list_id=self._task_list_id,
            max_results=self._max_results,
            completed_min=self._completed_min,
            completed_max=self._completed_max,
            due_min=self._due_min,
            due_max=self._due_max,
            show_completed=self._show_completed,
        )

        return tasks

    async def count(self) -> int:
        """
        Execute the query asynchronously and return only the count of matching tasks.
        Returns:
            Number of tasks matching the criteria
        """
        return len(await self.execute())

    async def first(self) -> Optional[Task]:
        """
        Execute the query asynchronously and return only the first matching task.
        Returns:
            First Task or None if no matches
        """
        tasks = await self.limit(1).execute()
        return tasks[0] if tasks else None

    async def exists(self) -> bool:
        """
        Check asynchronously if any tasks match the criteria without retrieving them.
        Returns:
            True if at least one task matches, False otherwise
        """
        return await self.limit(1).count() > 0
