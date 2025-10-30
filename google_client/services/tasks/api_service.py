from datetime import datetime, date, timedelta
from typing import Optional, List, Any, Dict, Union

from google.auth.credentials import Credentials
from googleapiclient.discovery import build

from . import utils
from .constants import DEFAULT_TASK_LIST_ID, TASK_STATUS_COMPLETED, TASK_STATUS_NEEDS_ACTION
from .types import Task, TaskList
from ...utils.datetime import datetime_to_iso


class TasksApiService:
    """
    Service layer for Tasks API operations.
    Contains all Tasks API functionality that was removed from dataclasses.
    """

    def __init__(self, credentials: Credentials, timezone: str):
        """
        Initialize Tasks service.

        Args:
            credentials: Google API credentials
            timezone: User's timezone for date/time operations (e.g., 'America/New_York')
        """
        self._service = build("tasks", "v1", credentials=credentials)
        self._timezone = timezone

    def query(self):
        """
        Create a new TaskQueryBuilder for building complex task queries with a fluent API.

        Returns:
            TaskQueryBuilder instance for method chaining

        Example:
            tasks = (user.tasks.query()
                .limit(50)
                .due_today()
                .show_completed(False)
                .in_task_list("my_list_id")
                .execute())
        """
        from .query_builder import TaskQueryBuilder
        return TaskQueryBuilder(self, self._timezone)

    def list_tasks(
            self,
            task_list_id: str = DEFAULT_TASK_LIST_ID,
            max_results: Optional[int] = 100,
            completed_min: Optional[date] = None,
            completed_max: Optional[date] = None,
            due_min: Optional[date] = None,
            due_max: Optional[date] = None,
            show_completed: Optional[bool] = False,
            show_assigned: Optional[bool] = True,
            show_hidden: Optional[bool] = False,
    ) -> List[Task]:
        """
        Fetches a list of tasks from Google Tasks with optional filtering.

        Args:
            task_list_id: Task list identifier (default: '@default').
            max_results: Maximum number of tasks to retrieve.
            completed_min: Lower bound for a task's completion date (RFC 3339).
            completed_max: Upper bound for a task's completion date (RFC 3339).
            due_min: Lower bound for a task's due date (RFC 3339).
            due_max: Upper bound for a task's due date (RFC 3339).
            show_completed: Flag indicating whether completed tasks are returned.

        Returns:
            A list of Task objects representing the tasks found.
        """
        if max_results < 1:
            raise ValueError(f"max_results must be at least 1")

        request_params = {
            'tasklist': task_list_id,
            'maxResults': max_results,
            'showCompleted': show_completed,
            'showHidden': show_hidden,
            'showAssigned': show_assigned,
        }

        if completed_min:
            completed_min = datetime.combine(completed_min, datetime.min.time())
            request_params['completedMin'] = completed_min.isoformat() + 'Z'
        if completed_max:
            completed_max = datetime.combine(completed_max, datetime.min.time())
            request_params['completedMax'] = completed_max.isoformat() + 'Z'
        if due_min:
            due_min = datetime.combine(due_min, datetime.min.time())
            request_params['dueMin'] = due_min.isoformat() + 'Z'
        if due_max:
            due_max = datetime.combine(due_max, datetime.min.time())
            request_params['dueMax'] = due_max.isoformat() + 'Z'
        if show_completed:
            request_params['showHidden'] = True

        result = self._service.tasks().list(**request_params).execute()
        tasks = [utils.from_google_task(task, task_list_id, self._timezone) for task in result.get('items', [])]
        while result.get('nextPageToken') and len(tasks) < max_results:
            request_params['maxResults'] = max_results - len(tasks)
            result = self._service.tasks().list(**request_params).execute()
            tasks.extend(
                [utils.from_google_task(task, task_list_id, self._timezone) for task in result.get('items', [])])

        return tasks

    def get_task(self, task_id: str, task_list_id: str = DEFAULT_TASK_LIST_ID) -> Task:
        """
        Retrieves a specific task from Google Tasks using its unique identifier.

        Args:
            task_list_id: The task list identifier containing the task.
            task_id: The unique identifier of the task to be retrieved.

        Returns:
            A Task object representing the task with the specified ID.
        """
        task_data = self._service.tasks().get(
            tasklist=task_list_id,
            task=task_id
        ).execute()

        return utils.from_google_task(task_data, task_list_id, self._timezone)

    def create_task(
            self,
            title: str,
            task_list_id: str = DEFAULT_TASK_LIST_ID,
            notes: Optional[str] = None,
            due: Optional[date] = None,
            parent: Optional[str] = None,
            position: Optional[str] = None
    ) -> Task:
        """
        Creates a new task.

        Args:
            title: The title of the task.
            task_list_id: Task list identifier (default: '@default').
            notes: Notes describing the task.
            due: Due date of the task.
            parent: Parent task identifier.
            position: Position in the task list.

        Returns:
            A Task object representing the created task.
        """
        task_body = utils.create_task_body(
            title=title,
            notes=notes,
            due=due,
            parent=parent,
            position=position
        )

        created_task = self._service.tasks().insert(tasklist=task_list_id, body=task_body).execute()

        task = utils.from_google_task(created_task, task_list_id, self._timezone)
        return task

    def update_task(self, task: Task, task_list_id: str = DEFAULT_TASK_LIST_ID) -> Task:
        """
        Updates an existing task.

        Args:
            task: The task to update.
            task_list_id: Task list identifier containing the task.

        Returns:
            A Task object representing the updated task.
        """
        task_body = task.to_dict()
        updated_task = self._service.tasks().update(
            tasklist=task_list_id,
            task=task.task_id,
            body=task_body
        ).execute()

        task = utils.from_google_task(updated_task, task_list_id, self._timezone)
        return task

    def delete_task(self, task: Union[Task, str], task_list_id: str = DEFAULT_TASK_LIST_ID) -> bool:
        """
        Deletes a task.

        Args:
            task: The task to delete.
            task_list_id: Task list identifier containing the task.

        Returns:
            True if the operation was successful.
        """

        if isinstance(task, Task):
            task = task.task_id
        self._service.tasks().delete(
            tasklist=task_list_id,
            task=task
        ).execute()

        return True

    def move_task(
            self,
            task: Task,
            task_list_id: str = DEFAULT_TASK_LIST_ID,
            parent: Optional[str] = None,
            previous: Optional[str] = None
    ) -> Task:
        """
        Moves a task to a different position in the task list.

        Args:
            task: The task to move.
            task_list_id: Task list identifier containing the task.
            parent: Parent task identifier (optional).
            previous: Previous sibling task identifier (optional).

        Returns:
            A Task object representing the moved task.
        """
        request_params = {
            'tasklist': task_list_id,
            'task': task.task_id
        }
        if parent:
            request_params['parent'] = parent
        if previous:
            request_params['previous'] = previous

        moved_task = self._service.tasks().move(**request_params).execute()

        task = utils.from_google_task(moved_task, task_list_id, self._timezone)
        return task

    def mark_completed(self, task: Union[str, Task], task_list_id: str = DEFAULT_TASK_LIST_ID) -> Task:
        """
        Marks a task as completed.

        Args:
            task: The task to mark as completed.
            task_list_id: Task list identifier containing the task.

        Returns:
            A Task object representing the updated task.
        """
        if isinstance(task, str):
            task = self.get_task(task_id=task, task_list_id=task_list_id)
        task.status = TASK_STATUS_COMPLETED
        task.completed = date.today()
        return self.update_task(task=task, task_list_id=task_list_id)

    def mark_incomplete(self, task: Union[str, Task], task_list_id: str = DEFAULT_TASK_LIST_ID) -> Task:
        """
        Marks a task as needing action (incomplete).

        Args:
            task: The task to mark as incomplete.
            task_list_id: Task list identifier containing the task.

        Returns:
            A Task object representing the updated task.
        """
        if isinstance(task, str):
            task = self.get_task(task_id=task, task_list_id=task_list_id)
        task.completed = None
        task.status = TASK_STATUS_NEEDS_ACTION
        return self.update_task(task=task, task_list_id=task_list_id)

    def list_task_lists(self) -> List[TaskList]:
        """
        Fetches a list of task lists from Google Tasks.

        Returns:
            A list of TaskList objects representing the task lists found.
        """

        result = self._service.tasklists().list().execute()
        task_lists = [utils.from_google_task_list(task_list, self._timezone) for task_list in result.get('items', [])]
        return task_lists

    def get_task_list(self, task_list_id: str) -> TaskList:
        """
        Retrieves a specific task list from Google Tasks.

        Args:
            task_list_id: The unique identifier of the task list.

        Returns:
            A TaskList object representing the task list with the specified ID.
        """
        task_list_data = self._service.tasklists().get(tasklist=task_list_id).execute()

        return utils.from_google_task_list(task_list_data, self._timezone)

    def create_task_list(self, title: str) -> TaskList:
        """
        Creates a new task list.

        Args:
            title: The title of the task list.

        Returns:
            A TaskList object representing the created task list.
        """
        task_list_body = utils.create_task_list_body(title)
        created_task_list = self._service.tasklists().insert(body=task_list_body).execute()

        task_list = utils.from_google_task_list(created_task_list, self._timezone)
        return task_list

    def update_task_list(self, task_list: TaskList, title: str) -> TaskList:
        """
        Updates an existing task list.

        Args:
            task_list: The task list to update.
            title: New title for the task list.

        Returns:
            A TaskList object representing the updated task list.
        """
        task_list_body = utils.create_task_list_body(title)
        task_list_body['id'] = task_list.task_list_id

        updated_task_list = self._service.tasklists().update(
            tasklist=task_list.task_list_id,
            body=task_list_body
        ).execute()

        task_list.title = title
        task_list = utils.from_google_task_list(updated_task_list, self._timezone)
        return task_list

    def delete_task_list(self, task_list: TaskList) -> bool:
        """
        Deletes a task list.

        Args:
            task_list: The task list to delete.

        Returns:
            True if the operation was successful.
        """
        self._service.tasklists().delete(
            tasklist=task_list.task_list_id
        ).execute()

        return True

    def batch_get_tasks(self, task_list_id: str, task_ids: List[str]) -> List[Task]:
        """
        Retrieves multiple tasks by their IDs.

        Args:
            task_list_id: Task list identifier containing the tasks.
            task_ids: List of task IDs to retrieve.

        Returns:
            List of Task objects.
        """

        tasks = [self.get_task(task_list_id, task_id) for task_id in task_ids]
        return tasks

    def batch_create_tasks(
            self,
            tasks_data: List[Dict[str, Any]],
            task_list_id: str = DEFAULT_TASK_LIST_ID) -> List[Task]:
        """
        Creates multiple tasks.

        Args:
            task_list_id: Task list identifier to create tasks in.
            tasks_data: List of dictionaries containing task parameters.

        Returns:
            List of created Task objects.
        """

        created_tasks = [self.create_task(task_list_id=task_list_id, **task_data) for task_data in tasks_data]
        return created_tasks
