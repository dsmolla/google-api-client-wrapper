from datetime import datetime, date
from typing import Optional, List, Any, Dict
import logging

from googleapiclient.errors import HttpError

from ...utils.log_sanitizer import sanitize_for_logging
from .types import Task, TaskList
from . import utils
from .constants import (
    DEFAULT_MAX_RESULTS, MAX_RESULTS_LIMIT, DEFAULT_TASK_LIST_ID,
    TASK_STATUS_COMPLETED, TASK_STATUS_NEEDS_ACTION
)
from .exceptions import (
    TasksError, TasksPermissionError, TasksNotFoundError,
    TaskConflictError, InvalidTaskDataError, TaskMoveError
)

logger = logging.getLogger(__name__)


class TasksApiService:
    """
    Service layer for Tasks API operations.
    Contains all Tasks API functionality that was removed from dataclasses.
    """
    
    def __init__(self, service: Any):
        """
        Initialize Tasks service.
        
        Args:
            service: The Tasks API service instance
        """
        self._service = service

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
        return TaskQueryBuilder(self)

    # Task Operations
    def list_tasks(
            self,
            task_list_id: str = DEFAULT_TASK_LIST_ID,
            max_results: Optional[int] = DEFAULT_MAX_RESULTS,
            completed_min: Optional[datetime] = None,
            completed_max: Optional[datetime] = None,
            due_min: Optional[datetime] = None,
            due_max: Optional[datetime] = None,
            show_completed: Optional[bool] = None,
            show_hidden: Optional[bool] = None
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
            show_hidden: Flag indicating whether hidden tasks are returned.

        Returns:
            A list of Task objects representing the tasks found.
        """
        # Input validation
        if max_results and (max_results < 1 or max_results > MAX_RESULTS_LIMIT):
            raise ValueError(f"max_results must be between 1 and {MAX_RESULTS_LIMIT}")

        sanitized = sanitize_for_logging(
            task_list_id=task_list_id, max_results=max_results,
            show_completed=show_completed, show_hidden=show_hidden
        )
        logger.info(
            "Fetching tasks from task_list_id=%s, max_results=%s, show_completed=%s, show_hidden=%s",
            sanitized['task_list_id'], sanitized['max_results'], 
            sanitized['show_completed'], sanitized['show_hidden']
        )

        try:
            # Build request parameters
            request_params = {
                'tasklist': task_list_id,
                'maxResults': max_results
            }
            
            # Add optional filters
            if completed_min:
                request_params['completedMin'] = completed_min.isoformat() + 'Z'
            if completed_max:
                request_params['completedMax'] = completed_max.isoformat() + 'Z'
            if due_min:
                request_params['dueMin'] = due_min.isoformat() + 'Z'
            if due_max:
                request_params['dueMax'] = due_max.isoformat() + 'Z'
            if show_completed is not None:
                request_params['showCompleted'] = show_completed
            if show_hidden is not None:
                request_params['showHidden'] = show_hidden

            # Make API call
            result = self._service.tasks().list(**request_params).execute()
            tasks_data = result.get('items', [])

            logger.info("Found %d task items", len(tasks_data))

            # Parse tasks
            tasks = []
            for task_data in tasks_data:
                try:
                    tasks.append(utils.from_google_task(task_data, task_list_id))
                except Exception as e:
                    logger.warning("Failed to parse task: %s", e)

            logger.info("Successfully parsed %d complete tasks", len(tasks))
            return tasks

        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise TasksNotFoundError(f"Task list not found: {task_list_id}")
            else:
                raise TasksError(f"Tasks API error listing tasks: {e}")
        except Exception as e:
            logger.error("An error occurred while fetching tasks: %s", e)
            raise TasksError(f"Unexpected error listing tasks: {e}")

    def get_task(self, task_id: str, task_list_id: str = DEFAULT_TASK_LIST_ID) -> Task:
        """
        Retrieves a specific task from Google Tasks using its unique identifier.

        Args:
            task_list_id: The task list identifier containing the task.
            task_id: The unique identifier of the task to be retrieved.

        Returns:
            A Task object representing the task with the specified ID.
        """
        logger.info("Retrieving task with ID: %s from task list: %s", task_id, task_list_id)

        try:
            task_data = self._service.tasks().get(
                tasklist=task_list_id,
                task=task_id
            ).execute()
            
            logger.info("Task retrieved successfully")
            return utils.from_google_task(task_data, task_list_id)
            
        except HttpError as e:
            if e.resp.status == 404:
                raise TasksNotFoundError(f"Task not found: {task_id}")
            elif e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied accessing task: {e}")
            else:
                raise TasksError(f"Tasks API error getting task {task_id}: {e}")
        except Exception as e:
            logger.error("Error retrieving task: %s", e)
            raise TasksError(f"Unexpected error getting task: {e}")

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
        sanitized = sanitize_for_logging(title=title, task_list_id=task_list_id)
        logger.info("Creating task with title=%s in task_list_id=%s", 
                   sanitized['title'], sanitized['task_list_id'])

        try:
            # Create task body using utils
            task_body = utils.create_task_body(
                title=title,
                notes=notes,
                due=due,
                parent=parent,
                position=position
            )

            # Make API call
            created_task = self._service.tasks().insert(
                tasklist=task_list_id,
                body=task_body
            ).execute()
            
            task = utils.from_google_task(created_task, task_list_id)
            logger.info("Task created successfully with ID: %s", task.task_id)
            return task
            
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied creating task: {e}")
            elif e.resp.status == 404:
                raise TasksNotFoundError(f"Task list not found: {task_list_id}")
            else:
                raise TasksError(f"Tasks API error creating task: {e}")
        except ValueError as e:
            raise InvalidTaskDataError(f"Invalid task data: {e}")
        except Exception as e:
            logger.error("Error creating task: %s", e)
            raise TasksError(f"Unexpected error creating task: {e}")

    def update_task(self, task: Task, task_list_id: str = DEFAULT_TASK_LIST_ID) -> Task:
        """
        Updates an existing task.

        Args:
            task: The task to update.
            task_list_id: Task list identifier containing the task.

        Returns:
            A Task object representing the updated task.
        """
        logger.info("Updating task with ID: %s in task list: %s", task.task_id, task_list_id)

        try:
            # Build update body
            task_body = task.to_dict()

            # Make API call
            updated_task = self._service.tasks().update(
                tasklist=task_list_id,
                task=task.task_id,
                body=task_body
            ).execute()
            
            task = utils.from_google_task(updated_task, task_list_id)
            logger.info("Task updated successfully")
            return task
            
        except HttpError as e:
            if e.resp.status == 404:
                raise TasksNotFoundError(f"Task not found: {task.task_id}")
            elif e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied updating task: {e}")
            else:
                raise TasksError(f"Tasks API error updating task {task.task_id}: {e}")
        except ValueError as e:
            raise InvalidTaskDataError(f"Invalid task data: {e}")
        except Exception as e:
            logger.error("Error updating task: %s", e)
            raise TasksError(f"Unexpected error updating task: {e}")

    def delete_task(self, task: Task, task_list_id: str = DEFAULT_TASK_LIST_ID) -> bool:
        """
        Deletes a task.

        Args:
            task: The task to delete.
            task_list_id: Task list identifier containing the task.

        Returns:
            True if the operation was successful.
        """
        logger.info("Deleting task with ID: %s from task list: %s", task.task_id, task_list_id)

        try:
            self._service.tasks().delete(
                tasklist=task_list_id,
                task=task.task_id
            ).execute()
            
            logger.info("Task deleted successfully")
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                raise TasksNotFoundError(f"Task not found: {task.task_id}")
            elif e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied deleting task: {e}")
            else:
                raise TasksError(f"Tasks API error deleting task {task.task_id}: {e}")
        except Exception as e:
            logger.error("Error deleting task: %s", e)
            raise TasksError(f"Unexpected error deleting task: {e}")

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
        logger.info("Moving task with ID: %s in task list: %s", task.task_id, task_list_id)

        try:
            request_params = {
                'tasklist': task_list_id,
                'task': task.task_id
            }
            if parent:
                request_params['parent'] = parent
            if previous:
                request_params['previous'] = previous

            moved_task = self._service.tasks().move(**request_params).execute()
            
            task = utils.from_google_task(moved_task, task_list_id)
            logger.info("Task moved successfully")
            return task
            
        except HttpError as e:
            if e.resp.status == 404:
                raise TasksNotFoundError(f"Task not found: {task.task_id}")
            elif e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied moving task: {e}")
            else:
                raise TaskMoveError(f"Tasks API error moving task {task.task_id}: {e}")
        except Exception as e:
            logger.error("Error moving task: %s", e)
            raise TaskMoveError(f"Unexpected error moving task: {e}")

    def mark_completed(self, task: Task, task_list_id: str = DEFAULT_TASK_LIST_ID) -> Task:
        """
        Marks a task as completed.

        Args:
            task: The task to mark as completed.
            task_list_id: Task list identifier containing the task.

        Returns:
            A Task object representing the updated task.
        """
        task.status = TASK_STATUS_COMPLETED
        task.completed = date.today()
        return self.update_task(task=task, task_list_id=task_list_id)

    def mark_incomplete(self, task: Task, task_list_id: str = DEFAULT_TASK_LIST_ID) -> Task:
        """
        Marks a task as needing action (incomplete).

        Args:
            task: The task to mark as incomplete.
            task_list_id: Task list identifier containing the task.

        Returns:
            A Task object representing the updated task.
        """
        task.completed = None
        task.status = TASK_STATUS_NEEDS_ACTION
        return self.update_task(task=task, task_list_id=task_list_id)

    # Task List Operations
    def list_task_lists(self) -> List[TaskList]:
        """
        Fetches a list of task lists from Google Tasks.

        Returns:
            A list of TaskList objects representing the task lists found.
        """
        logger.info("Fetching task lists")

        try:
            result = self._service.tasklists().list().execute()
            task_lists_data = result.get('items', [])

            logger.info("Found %d task list items", len(task_lists_data))

            # Parse task lists
            task_lists = []
            for task_list_data in task_lists_data:
                try:
                    task_lists.append(utils.from_google_task_list(task_list_data))
                except Exception as e:
                    logger.warning("Failed to parse task list: %s", e)

            logger.info("Successfully parsed %d complete task lists", len(task_lists))
            return task_lists

        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied: {e}")
            else:
                raise TasksError(f"Tasks API error listing task lists: {e}")
        except Exception as e:
            logger.error("An error occurred while fetching task lists: %s", e)
            raise TasksError(f"Unexpected error listing task lists: {e}")

    def get_task_list(self, task_list_id: str) -> TaskList:
        """
        Retrieves a specific task list from Google Tasks.

        Args:
            task_list_id: The unique identifier of the task list.

        Returns:
            A TaskList object representing the task list with the specified ID.
        """
        logger.info("Retrieving task list with ID: %s", task_list_id)

        try:
            task_list_data = self._service.tasklists().get(
                tasklist=task_list_id
            ).execute()
            
            logger.info("Task list retrieved successfully")
            return utils.from_google_task_list(task_list_data)
            
        except HttpError as e:
            if e.resp.status == 404:
                raise TasksNotFoundError(f"Task list not found: {task_list_id}")
            elif e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied accessing task list: {e}")
            else:
                raise TasksError(f"Tasks API error getting task list {task_list_id}: {e}")
        except Exception as e:
            logger.error("Error retrieving task list: %s", e)
            raise TasksError(f"Unexpected error getting task list: {e}")

    def create_task_list(self, title: str) -> TaskList:
        """
        Creates a new task list.

        Args:
            title: The title of the task list.

        Returns:
            A TaskList object representing the created task list.
        """
        sanitized = sanitize_for_logging(title=title)
        logger.info("Creating task list with title=%s", sanitized['title'])

        try:
            # Create task list body using utils
            task_list_body = utils.create_task_list_body(title)

            # Make API call
            created_task_list = self._service.tasklists().insert(
                body=task_list_body
            ).execute()
            
            task_list = utils.from_google_task_list(created_task_list)
            logger.info("Task list created successfully with ID: %s", task_list.task_list_id)
            return task_list
            
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied creating task list: {e}")
            else:
                raise TasksError(f"Tasks API error creating task list: {e}")
        except ValueError as e:
            raise InvalidTaskDataError(f"Invalid task list data: {e}")
        except Exception as e:
            logger.error("Error creating task list: %s", e)
            raise TasksError(f"Unexpected error creating task list: {e}")

    def update_task_list(self, task_list: TaskList, title: str) -> TaskList:
        """
        Updates an existing task list.

        Args:
            task_list: The task list to update.
            title: New title for the task list.

        Returns:
            A TaskList object representing the updated task list.
        """
        logger.info("Updating task list with ID: %s", task_list.task_list_id)

        try:
            # Create update body
            task_list_body = utils.create_task_list_body(title)
            task_list_body['id'] = task_list.task_list_id

            # Make API call
            updated_task_list = self._service.tasklists().update(
                tasklist=task_list.task_list_id,
                body=task_list_body
            ).execute()

            task_list.title = title
            task_list = utils.from_google_task_list(updated_task_list)
            logger.info("Task list updated successfully")
            return task_list
            
        except HttpError as e:
            if e.resp.status == 404:
                raise TasksNotFoundError(f"Task list not found: {task_list.task_list_id}")
            elif e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied updating task list: {e}")
            else:
                raise TasksError(f"Tasks API error updating task list {task_list.task_list_id}: {e}")
        except ValueError as e:
            raise InvalidTaskDataError(f"Invalid task list data: {e}")
        except Exception as e:
            logger.error("Error updating task list: %s", e)
            raise TasksError(f"Unexpected error updating task list: {e}")

    def delete_task_list(self, task_list: TaskList) -> bool:
        """
        Deletes a task list.

        Args:
            task_list: The task list to delete.

        Returns:
            True if the operation was successful.
        """
        logger.info("Deleting task list with ID: %s", task_list.task_list_id)

        try:
            self._service.tasklists().delete(
                tasklist=task_list.task_list_id
            ).execute()
            
            logger.info("Task list deleted successfully")
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                raise TasksNotFoundError(f"Task list not found: {task_list.task_list_id}")
            elif e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied deleting task list: {e}")
            elif e.resp.status == 400:
                raise TasksError(f"Cannot delete default task list: {task_list.task_list_id}")
            else:
                raise TasksError(f"Tasks API error deleting task list {task_list.task_list_id}: {e}")
        except Exception as e:
            logger.error("Error deleting task list: %s", e)
            raise TasksError(f"Unexpected error deleting task list: {e}")

    # Batch Operations
    def batch_get_tasks(self, task_list_id: str, task_ids: List[str]) -> List[Task]:
        """
        Retrieves multiple tasks by their IDs.

        Args:
            task_list_id: Task list identifier containing the tasks.
            task_ids: List of task IDs to retrieve.

        Returns:
            List of Task objects.
        """
        logger.info("Batch retrieving %d tasks from task list: %s", len(task_ids), task_list_id)

        tasks = []
        for task_id in task_ids:
            try:
                tasks.append(self.get_task(task_list_id, task_id))
            except Exception as e:
                logger.warning("Failed to fetch task %s: %s", task_id, e)

        return tasks

    def batch_create_tasks(self, tasks_data: List[Dict[str, Any]], task_list_id: str = DEFAULT_TASK_LIST_ID) -> List[Task]:
        """
        Creates multiple tasks.

        Args:
            task_list_id: Task list identifier to create tasks in.
            tasks_data: List of dictionaries containing task parameters.

        Returns:
            List of created Task objects.
        """
        logger.info("Batch creating %d tasks in task list: %s", len(tasks_data), task_list_id)

        created_tasks = []
        for task_data in tasks_data:
            try:
                created_tasks.append(self.create_task(task_list_id=task_list_id, **task_data))
            except Exception as e:
                logger.warning("Failed to create task: %s", e)

        return created_tasks