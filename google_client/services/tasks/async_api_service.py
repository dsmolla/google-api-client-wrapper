import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date
from typing import Optional, List, Any, Dict, Union

from google.auth.credentials import Credentials
from googleapiclient.discovery import build

from . import utils
from .constants import (
    DEFAULT_MAX_RESULTS, MAX_RESULTS_LIMIT, DEFAULT_TASK_LIST_ID,
    TASK_STATUS_COMPLETED, TASK_STATUS_NEEDS_ACTION
)
from .types import Task, TaskList
from ...utils.datetime import datetime_to_iso, datetime_to_zone


class AsyncTasksApiService:
    """
    Async service layer for Tasks API operations.
    Contains all Tasks API functionality that was removed from dataclasses.
    """

    def __init__(self, credentials: Credentials, timezone: str):
        self._executor = ThreadPoolExecutor()
        self._credentials = credentials
        self._timezone = timezone

    def __del__(self):
        """Cleanup ThreadPoolExecutor on deletion."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)

    def _service(self):
        return build("tasks", "v1", credentials=self._credentials)

    def query(self):
        from .async_query_builder import AsyncTaskQueryBuilder
        return AsyncTaskQueryBuilder(self, self._timezone)

    async def list_tasks(
            self,
            task_list_id: str = DEFAULT_TASK_LIST_ID,
            max_results: Optional[int] = DEFAULT_MAX_RESULTS,
            completed_min: Optional[datetime] = None,
            completed_max: Optional[datetime] = None,
            due_min: Optional[datetime] = None,
            due_max: Optional[datetime] = None,
            show_completed: Optional[bool] = False,
    ) -> List[Task]:
        if max_results < 1:
            raise ValueError(f"max_results must be at least 1")

        request_params = {
            'tasklist': task_list_id,
            'maxResults': max_results,
            'showCompleted': show_completed,
        }

        if completed_min:
            request_params['completedMin'] = datetime_to_iso(completed_min, self._timezone)
        if completed_max:
            request_params['completedMax'] = datetime_to_iso(completed_max, self._timezone)
        if due_min:
            request_params['dueMin'] = datetime_to_iso(due_min, self._timezone)
        if due_max:
            request_params['dueMax'] = datetime_to_iso(due_max, self._timezone)
        if show_completed:
            request_params['showHidden'] = True

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().tasks().list(**request_params).execute()
        )

        tasks = [utils.from_google_task(task, task_list_id, self._timezone) for task in result.get('items', [])]
        while result.get('nextPageToken') and len(tasks) < max_results:
            request_params['maxResults'] = max_results - len(tasks)
            result = await loop.run_in_executor(
                self._executor,
                lambda: self._service().tasks().list(**request_params, pageToken=result['nextPageToken']).execute()
            )
            tasks.extend([utils.from_google_task(task, task_list_id, self._timezone) for task in result.get('items', [])])

        return tasks

    async def get_task(self, task_id: str, task_list_id: str = DEFAULT_TASK_LIST_ID) -> Task:
        loop = asyncio.get_event_loop()
        task_data = await loop.run_in_executor(
            self._executor,
            lambda: self._service().tasks().get(
                tasklist=task_list_id,
                task=task_id
            ).execute()
        )

        return utils.from_google_task(task_data, task_list_id, self._timezone)

    async def create_task(
            self,
            title: str,
            task_list_id: str = DEFAULT_TASK_LIST_ID,
            notes: Optional[str] = None,
            due: Optional[date] = None,
            parent: Optional[str] = None,
            position: Optional[str] = None
    ) -> Task:
        task_body = utils.create_task_body(
            title=title,
            notes=notes,
            due=due,
            parent=parent,
            position=position
        )

        loop = asyncio.get_event_loop()
        created_task = await loop.run_in_executor(
            self._executor,
            lambda: self._service().tasks().insert(
                tasklist=task_list_id,
                body=task_body
            ).execute()
        )

        task = utils.from_google_task(created_task, task_list_id, self._timezone)
        return task

    async def update_task(self, task: Task, task_list_id: str = DEFAULT_TASK_LIST_ID) -> Task:
        task_body = task.to_dict()

        loop = asyncio.get_event_loop()
        updated_task = await loop.run_in_executor(
            self._executor,
            lambda: self._service().tasks().update(
                tasklist=task_list_id,
                task=task.task_id,
                body=task_body
            ).execute()
        )

        task = utils.from_google_task(updated_task, task_list_id, self._timezone)
        return task

    async def delete_task(self, task: Union[Task, str], task_list_id: str = DEFAULT_TASK_LIST_ID) -> bool:
        if isinstance(task, Task):
            task = task.task_id

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor,
            lambda: self._service().tasks().delete(
                tasklist=task_list_id,
                task=task
            ).execute()
        )
        return True

    async def move_task(
            self,
            task: Task,
            task_list_id: str = DEFAULT_TASK_LIST_ID,
            parent: Optional[str] = None,
            previous: Optional[str] = None
    ) -> Task:
        request_params = {
            'tasklist': task_list_id,
            'task': task.task_id
        }
        if parent:
            request_params['parent'] = parent
        if previous:
            request_params['previous'] = previous

        loop = asyncio.get_event_loop()
        moved_task = await loop.run_in_executor(
            self._executor,
            lambda: self._service().tasks().move(**request_params).execute()
        )

        task = utils.from_google_task(moved_task, task_list_id, self._timezone)
        return task

    async def mark_completed(self, task: Union[str, Task], task_list_id: str = DEFAULT_TASK_LIST_ID) -> Task:
        if isinstance(task, str):
            task = await self.get_task(task_id=task, task_list_id=task_list_id)
        task.status = TASK_STATUS_COMPLETED
        task.completed = date.today()
        return await self.update_task(task=task, task_list_id=task_list_id)

    async def mark_incomplete(self, task: Union[str, Task], task_list_id: str = DEFAULT_TASK_LIST_ID) -> Task:
        if isinstance(task, str):
            task = await self.get_task(task_id=task, task_list_id=task_list_id)
        task.completed = None
        task.status = TASK_STATUS_NEEDS_ACTION
        return await self.update_task(task=task, task_list_id=task_list_id)

    async def list_task_lists(self) -> List[TaskList]:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().tasklists().list().execute()
        )
        task_lists = [utils.from_google_task_list(task_list, self._timezone) for task_list in result.get('items', [])]
        return task_lists

    async def get_task_list(self, task_list_id: str) -> TaskList:
        loop = asyncio.get_event_loop()
        task_list_data = await loop.run_in_executor(
            self._executor,
            lambda: self._service().tasklists().get(
                tasklist=task_list_id
            ).execute()
        )

        return utils.from_google_task_list(task_list_data, self._timezone)

    async def create_task_list(self, title: str) -> TaskList:
        task_list_body = utils.create_task_list_body(title)

        loop = asyncio.get_event_loop()
        created_task_list = await loop.run_in_executor(
            self._executor,
            lambda: self._service().tasklists().insert(
                body=task_list_body
            ).execute()
        )

        task_list = utils.from_google_task_list(created_task_list, self._timezone)
        return task_list

    async def update_task_list(self, task_list: TaskList, title: str) -> TaskList:
        task_list_body = utils.create_task_list_body(title)
        task_list_body['id'] = task_list.task_list_id

        loop = asyncio.get_event_loop()
        updated_task_list = await loop.run_in_executor(
            self._executor,
            lambda: self._service().tasklists().update(
                tasklist=task_list.task_list_id,
                body=task_list_body
            ).execute()
        )

        task_list.title = title
        task_list = utils.from_google_task_list(updated_task_list, self._timezone)
        return task_list

    async def delete_task_list(self, task_list: TaskList) -> bool:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor,
            lambda: self._service().tasklists().delete(
                tasklist=task_list.task_list_id
            ).execute()
        )

        return True

    async def batch_get_tasks(self, task_list_id: str, task_ids: List[str]) -> List[Task]:
        tasks = []
        for task_id in task_ids:
            task = asyncio.create_task(self.get_task(task_id, task_list_id))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    async def batch_create_tasks(self, tasks_data: List[Dict[str, Any]], task_list_id: str = DEFAULT_TASK_LIST_ID) -> \
    List[Task]:
        tasks = []
        for task_data in tasks_data:
            task = asyncio.create_task(self.create_task(task_list_id=task_list_id, **task_data))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
