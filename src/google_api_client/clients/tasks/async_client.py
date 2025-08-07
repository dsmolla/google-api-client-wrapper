import asyncio
from datetime import date, datetime, time
from typing import Optional, List, Self
from ...auth.manager import auth_manager
from ...utils.datetime import convert_datetime_to_readable, convert_datetime_to_local_timezone, convert_datetime_to_iso
from dataclasses import dataclass, field
import logging
from contextlib import asynccontextmanager
from aiogoogle.excs import HTTPError

logger = logging.getLogger(__name__)

# Constants
MAX_RESULTS_LIMIT = 100
MAX_TITLE_LENGTH = 1024
MAX_NOTES_LENGTH = 8192
DEFAULT_MAX_RESULTS = 100

# Custom Exception Classes
class AsyncTasksError(Exception):
    """Base exception for async tasks operations."""
    pass

class AsyncTasksPermissionError(AsyncTasksError):
    """Raised when the user lacks permission for a tasks operation."""
    pass

class AsyncTasksNotFoundError(AsyncTasksError):
    """Raised when a task or task list is not found."""
    pass

@asynccontextmanager
async def async_tasks_service():
    """Async context manager for tasks service connections with error handling."""
    try:
        async with auth_manager.get_async_tasks_service() as (aiogoogle, tasks_service):
            yield aiogoogle, tasks_service
    except HTTPError as e:
        if e.res.status_code == 403:
            raise AsyncTasksPermissionError(f"Permission denied: {e}")
        elif e.res.status_code == 404:
            raise AsyncTasksNotFoundError(f"Task or task list not found: {e}")
        else:
            raise AsyncTasksError(f"Tasks API error: {e}")
    except Exception as e:
        raise AsyncTasksError(f"Unexpected tasks service error: {e}")


@dataclass
class AsyncTaskList:
    """
    Async version of TaskList with all async methods.
    Args:
        id: Unique identifier for the task list.
        title: The title of the task list.
        updated: Last modification time.
    """
    id: Optional[str] = None
    title: Optional[str] = None
    updated: Optional[datetime] = None

    def __post_init__(self):
        if self.title and len(self.title) > MAX_TITLE_LENGTH:
            raise ValueError(f"TaskList title cannot exceed {MAX_TITLE_LENGTH} characters")

    @staticmethod
    def _from_google_tasklist(google_tasklist: dict) -> "AsyncTaskList":
        """
        Creates an AsyncTaskList instance from a Google Tasks API response.
        Args:
            google_tasklist: A dictionary containing task list data from Google Tasks API.
        Returns:
            An AsyncTaskList instance populated with the data from the dictionary.
        """
        updated = None
        if google_tasklist.get('updated'):
            try:
                updated = datetime.fromisoformat(google_tasklist['updated'].replace('Z', '+00:00'))
                updated = convert_datetime_to_local_timezone(updated)
            except:
                logger.warning("Failed to parse updated time: %s", google_tasklist.get('updated'))

        return AsyncTaskList(
            id=google_tasklist.get('id'),
            title=google_tasklist.get('title'),
            updated=updated
        )

    def to_dict(self) -> dict:
        """Convert AsyncTaskList to dictionary format for Google Tasks API."""
        task_list_dict = {}
        if self.id:
            task_list_dict['id'] = self.id
        if self.title:
            task_list_dict['title'] = self.title
        return task_list_dict

    @classmethod
    async def list_task_lists(cls) -> List["AsyncTaskList"]:
        """
        Fetches a list of task lists from Google Tasks asynchronously.
        Returns:
            A list of AsyncTaskList objects representing the task lists found.
        """
        logger.info("Fetching task lists from Google Tasks (async)")
        
        async with async_tasks_service() as (aiogoogle, service):
            try:
                result = await aiogoogle.as_service_account(service.tasklists.list())
                task_lists = result.get('items', [])
                logger.info("Found %d task lists", len(task_lists))
                
                task_list_objects = []
                for task_list in task_lists:
                    try:
                        task_list_objects.append(cls._from_google_tasklist(task_list))
                    except Exception as e:
                        logger.warning("Skipping invalid task list: %s", e)
                
                return task_list_objects
            except Exception as e:
                logger.error("Error fetching task lists: %s", e)
                raise

    @classmethod
    async def get_task_list(cls, task_list_id: str) -> "AsyncTaskList":
        """
        Retrieves a specific task list by its ID asynchronously.
        Args:
            task_list_id: The unique identifier of the task list to retrieve.
        Returns:
            An AsyncTaskList object representing the task list.
        """
        logger.info("Retrieving task list with ID: %s (async)", task_list_id)
        
        async with async_tasks_service() as (aiogoogle, service):
            try:
                google_tasklist = await aiogoogle.as_service_account(
                    service.tasklists.get(tasklist=task_list_id)
                )
                logger.info("Task list retrieved successfully")
                return cls._from_google_tasklist(google_tasklist)
            except Exception as e:
                logger.error("Error retrieving task list: %s", e)
                raise

    @classmethod
    async def create_task_list(cls, title: str) -> "AsyncTaskList":
        """
        Creates a new task list in Google Tasks asynchronously.
        Args:
            title: The title of the task list to create.
        Returns:
            An AsyncTaskList object representing the created task list.
        """
        if len(title) > MAX_TITLE_LENGTH:
            raise ValueError(f"TaskList title cannot exceed {MAX_TITLE_LENGTH} characters")
        
        logger.info("Creating task list with title: %s (async)", title)
        
        async with async_tasks_service() as (aiogoogle, service):
            try:
                body = {'title': title}
                google_tasklist = await aiogoogle.as_service_account(
                    service.tasklists.insert(body=body)
                )
                logger.info("Task list created successfully with ID: %s", google_tasklist.get('id'))
                return cls._from_google_tasklist(google_tasklist)
            except Exception as e:
                logger.error("Error creating task list: %s", e)
                raise

    async def update_task_list(self, title: str) -> "AsyncTaskList":
        """
        Updates the title of this task list asynchronously.
        Args:
            title: The new title for the task list.
        Returns:
            The updated AsyncTaskList object.
        """
        if len(title) > MAX_TITLE_LENGTH:
            raise ValueError(f"TaskList title cannot exceed {MAX_TITLE_LENGTH} characters")
        
        logger.info("Updating task list %s to new title: %s (async)", self.id, title)
        
        async with async_tasks_service() as (aiogoogle, service):
            try:
                body = {
                    'id': self.id,
                    'title': title
                }
                google_tasklist = await aiogoogle.as_service_account(
                    service.tasklists.update(tasklist=self.id, body=body)
                )
                self.title = google_tasklist.get('title')
                return self
            except Exception as e:
                logger.error("Error updating task list: %s", e)
                raise

    async def delete_task_list(self) -> bool:
        """
        Deletes this task list asynchronously.
        Returns:
            True if the task list was successfully deleted, False otherwise.
        """
        logger.info("Deleting task list with ID: %s (async)", self.id)
        
        async with async_tasks_service() as (aiogoogle, service):
            try:
                await aiogoogle.as_service_account(service.tasklists.delete(tasklist=self.id))
                logger.info("Task list deleted successfully")
                return True
            except Exception as e:
                logger.error("Error deleting task list: %s", e)
                return False

    def __repr__(self):
        return f"AsyncTaskList(id={self.id!r}, title={self.title!r})"


@dataclass
class AsyncTask:
    """
    Async version of Task with all async methods.
    Args:
        id: Unique identifier for the task.
        title: The title of the task.
        notes: Notes describing the task.
        status: Status of the task ('needsAction' or 'completed').
        due: Due date of the task.
        completed: Completion date of the task.
        updated: Last modification time.
        parent: Parent task identifier.
        position: Position in the task list.
        task_list_id: ID of the task list this task belongs to.
    """
    id: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    due: Optional[date] = None
    completed: Optional[date] = None
    updated: Optional[date] = None
    parent: Optional[str] = None
    position: Optional[str] = None
    task_list_id: Optional[str] = None

    def __post_init__(self):
        if self.title and len(self.title) > MAX_TITLE_LENGTH:
            raise ValueError(f"Task title cannot exceed {MAX_TITLE_LENGTH} characters")
        if self.notes and len(self.notes) > MAX_NOTES_LENGTH:
            raise ValueError(f"Task notes cannot exceed {MAX_NOTES_LENGTH} characters")
        if self.status and self.status not in ['needsAction', 'completed']:
            raise ValueError(f"Invalid task status: {self.status}. Must be 'needsAction' or 'completed'")

    @staticmethod
    def _from_google_task(google_task: dict, task_list_id: Optional[str] = None) -> "AsyncTask":
        """
        Creates an AsyncTask instance from a Google Tasks API response.
        Args:
            google_task: A dictionary containing task data from Google Tasks API.
            task_list_id: The ID of the task list this task belongs to.
        Returns:
            An AsyncTask instance populated with the data from the dictionary.
        """
        def parse_datetime_field(field_value):
            if not field_value:
                return None
            try:
                dt = datetime.fromisoformat(field_value.replace('Z', '+00:00'))
                dt = date(dt.year, dt.month, dt.day)
                return dt
            except:
                logger.warning("Failed to parse datetime: %s", field_value)
                return None

        return AsyncTask(
            id=google_task.get('id'),
            title=google_task.get('title'),
            notes=google_task.get('notes'),
            status=google_task.get('status'),
            due=parse_datetime_field(google_task.get('due')),
            completed=parse_datetime_field(google_task.get('completed')),
            updated=parse_datetime_field(google_task.get('updated')),
            parent=google_task.get('parent'),
            position=google_task.get('position'),
            task_list_id=task_list_id
        )

    def to_dict(self) -> dict:
        """Convert AsyncTask to dictionary format for Google Tasks API."""
        task_dict = {}
        if self.id:
            task_dict['id'] = self.id
        if self.title:
            task_dict['title'] = self.title
        if self.notes:
            task_dict['notes'] = self.notes
        if self.status:
            task_dict['status'] = self.status
        if self.due:
            task_dict['due'] = datetime.combine(self.due, time.min).isoformat() + 'Z'
        if self.completed:
            task_dict['completed'] = datetime.combine(self.completed, time.min).isoformat() + 'Z'
        if self.parent:
            task_dict['parent'] = self.parent
        if self.position:
            task_dict['position'] = self.position
        return task_dict

    @classmethod
    def query(cls) -> "AsyncTaskQueryBuilder":
        """
        Create a new AsyncTaskQueryBuilder for building complex task queries with a fluent API.
        
        Returns:
            AsyncTaskQueryBuilder instance for method chaining
            
        Example:
            tasks = await (AsyncTask.query()
                .limit(50)
                .due_before(end_date)
                .completed_after(start_date)
                .show_completed(True)
                .execute())
        """
        from .async_query_builder import AsyncTaskQueryBuilder
        return AsyncTaskQueryBuilder(cls)

    @classmethod
    async def _list_tasks_with_filters(cls, **kwargs) -> List["AsyncTask"]:
        """
        Internal method to fetch tasks with advanced filtering support for query builder.
        Args:
            **kwargs: Request parameters including tasklist, maxResults, completedMin, etc.
        Returns:
            A list of AsyncTask objects representing the tasks found.
        """
        task_list_id = kwargs.get('tasklist', '@default')
        max_results = kwargs.get('maxResults', DEFAULT_MAX_RESULTS)
        
        if max_results is not None and (max_results < 1 or max_results > MAX_RESULTS_LIMIT):
            raise ValueError(f"maxResults must be between 1 and {MAX_RESULTS_LIMIT}")

        logger.info("Fetching tasks from task list with filters: %s (async)", task_list_id)
        
        async with async_tasks_service() as (aiogoogle, service):
            try:
                # Filter out None values and prepare request params
                request_params = {k: v for k, v in kwargs.items() if v is not None}
                
                result = await aiogoogle.as_service_account(service.tasks.list(**request_params))
                tasks = result.get('items', [])
                logger.info("Found %d tasks", len(tasks))
                
                task_objects = []
                for task in tasks:
                    try:
                        task_objects.append(cls._from_google_task(task, task_list_id))
                    except Exception as e:
                        logger.warning("Skipping invalid task: %s", e)
                
                return task_objects
            except Exception as e:
                logger.error("Error fetching tasks: %s", e)
                raise

    @classmethod
    async def list_tasks(cls, task_list_id: str='@default', max_results: Optional[int] = DEFAULT_MAX_RESULTS) -> List["AsyncTask"]:
        """
        Fetches a list of tasks from a specific task list asynchronously.
        Args:
            task_list_id: The ID of the task list to fetch tasks from.
            max_results: Maximum number of tasks to retrieve.
        Returns:
            A list of AsyncTask objects representing the tasks found.
        """
        if max_results is not None and (max_results < 1 or max_results > MAX_RESULTS_LIMIT):
            raise ValueError(f"max_results must be between 1 and {MAX_RESULTS_LIMIT}")

        logger.info("Fetching tasks from task list: %s (async)", task_list_id)
        
        async with async_tasks_service() as (aiogoogle, service):
            try:
                request_params = {
                    'tasklist': task_list_id,
                    'maxResults': max_results
                }
                
                result = await aiogoogle.as_service_account(service.tasks.list(**request_params))
                tasks = result.get('items', [])
                logger.info("Found %d tasks", len(tasks))
                
                task_objects = []
                for task in tasks:
                    try:
                        task_objects.append(cls._from_google_task(task, task_list_id))
                    except Exception as e:
                        logger.warning("Skipping invalid task: %s", e)
                
                return task_objects
            except Exception as e:
                logger.error("Error fetching tasks: %s", e)
                raise

    @classmethod
    async def get_task(cls, task_list_id: str, task_id: str) -> "AsyncTask":
        """
        Retrieves a specific task by its ID asynchronously.
        Args:
            task_list_id: The ID of the task list containing the task.
            task_id: The unique identifier of the task to retrieve.
        Returns:
            An AsyncTask object representing the task.
        """
        logger.info("Retrieving task with ID: %s from list: %s (async)", task_id, task_list_id)
        
        async with async_tasks_service() as (aiogoogle, service):
            try:
                google_task = await aiogoogle.as_service_account(
                    service.tasks.get(tasklist=task_list_id, task=task_id)
                )
                logger.info("Task retrieved successfully")
                return cls._from_google_task(google_task, task_list_id)
            except Exception as e:
                logger.error("Error retrieving task: %s", e)
                raise

    @classmethod
    async def create_task(
        cls,
        title: str,
        task_list_id: str = '@default',
        notes: Optional[str] = None,
        due: Optional[date] = None,
        parent: Optional[str] = None
    ) -> "AsyncTask":
        """
        Creates a new task in the specified task list asynchronously.
        Args:
            task_list_id: The ID of the task list to create the task in.
            title: The title of the task.
            notes: Notes for the task (optional).
            due: Due date for the task (optional). Time not supported by Google API.
            parent: Parent task ID (optional).
        Returns:
            An AsyncTask object representing the created task.
        """
        if len(title) > MAX_TITLE_LENGTH:
            raise ValueError(f"Task title cannot exceed {MAX_TITLE_LENGTH} characters")
        if notes and len(notes) > MAX_NOTES_LENGTH:
            raise ValueError(f"Task notes cannot exceed {MAX_NOTES_LENGTH} characters")
        
        logger.info("Creating task with title: %s in list: %s (async)", title, task_list_id)
        
        async with async_tasks_service() as (aiogoogle, service):
            try:
                body = {'title': title}
                if notes:
                    body['notes'] = notes
                if due:
                    body['due'] = datetime.combine(due, time.min).isoformat() + 'Z'
                if parent:
                    body['parent'] = parent
                
                google_task = await aiogoogle.as_service_account(
                    service.tasks.insert(tasklist=task_list_id, body=body)
                )
                logger.info("Task created successfully with ID: %s", google_task.get('id'))
                return cls._from_google_task(google_task, task_list_id)
            except Exception as e:
                logger.error("Error creating task: %s", e)
                raise

    async def update_task(
            self,
            title: str=None,
            notes: str=None,
            status: str=None,
            completed: date=None,
            due: date=None
    ) -> "AsyncTask":
        """
        Updates this task in Google Tasks asynchronously.
        Args:
            title: The title of the task (optional).
            notes: Notes for the task (optional).
            status: The status of the task (optional).
            completed: The completed date of the task (optional).
            due: Due date for the task (optional).

        Returns:
            The updated AsyncTask object.
        """
        if not self.task_list_id:
            raise ValueError("Task must have a task_list_id to be updated")
        
        logger.info("Updating task with ID: %s (async)", self.id)
        
        async with async_tasks_service() as (aiogoogle, service):
            try:
                body = self.to_dict()
                if title:
                    body['title'] = title
                if notes:
                    body['notes'] = notes
                if status:
                    body['status'] = status
                if completed:
                    body['completed'] = datetime.combine(completed, time.min).isoformat() + 'Z'
                if due:
                    body['due'] = datetime.combine(due, time.min).isoformat() + 'Z'

                google_task = await aiogoogle.as_service_account(
                    service.tasks.update(tasklist=self.task_list_id, task=self.id, body=body)
                )

                logger.info("Task updated successfully")
                # Update the current object with the response
                updated_task = self._from_google_task(google_task, self.task_list_id)
                self.__dict__.update(updated_task.__dict__)
                return self
            except Exception as e:
                logger.error("Error updating task: %s", e)
                raise

    async def delete_task(self) -> bool:
        """
        Deletes this task asynchronously.
        Returns:
            True if the task was successfully deleted, False otherwise.
        """
        if not self.task_list_id:
            raise ValueError("Task must have a task_list_id to be deleted")
        
        logger.info("Deleting task with ID: %s (async)", self.id)
        
        async with async_tasks_service() as (aiogoogle, service):
            try:
                await aiogoogle.as_service_account(
                    service.tasks.delete(tasklist=self.task_list_id, task=self.id)
                )
                logger.info("Task deleted successfully")
                return True
            except Exception as e:
                logger.error("Error deleting task: %s", e)
                return False

    async def move_task(self, parent: Optional[str] = None, previous: Optional[str] = None) -> "AsyncTask":
        """
        Moves this task to a different position in the task list asynchronously.
        Args:
            parent: Parent task ID (optional).
            previous: Previous sibling task ID (optional).
        Returns:
            The updated AsyncTask object.
        """
        if not self.task_list_id:
            raise ValueError("Task must have a task_list_id to be moved")
        
        logger.info("Moving task with ID: %s (async)", self.id)
        
        async with async_tasks_service() as (aiogoogle, service):
            try:
                request_params = {
                    'tasklist': self.task_list_id,
                    'task': self.id
                }
                if parent:
                    request_params['parent'] = parent
                if previous:
                    request_params['previous'] = previous
                
                google_task = await aiogoogle.as_service_account(service.tasks.move(**request_params))
                logger.info("Task moved successfully")
                # Update the current object with the response
                updated_task = self._from_google_task(google_task, self.task_list_id)
                self.__dict__.update(updated_task.__dict__)
                return self
            except Exception as e:
                logger.error("Error moving task: %s", e)
                raise

    async def mark_completed(self) -> "AsyncTask":
        """
        Marks this task as completed asynchronously.
        Returns:
            The updated AsyncTask object.
        """
        return await self.update_task(status='completed', completed=date.today())

    async def mark_incomplete(self) -> "AsyncTask":
        """
        Marks this task as needing action (incomplete) asynchronously.
        Returns:
            The updated AsyncTask object.
        """
        return await self.update_task(status='needsAction')

    def is_completed(self) -> bool:
        """
        Checks if the task is completed.
        Returns:
            True if the task is completed, False otherwise.
        """
        return self.status == 'completed'

    def is_overdue(self) -> bool:
        """
        Checks if the task is overdue.
        Returns:
            True if the task has a due date that has passed and is not completed.
        """
        if not self.due or self.is_completed():
            return False
        return self.due < date.today()

    def __repr__(self):
        return (
            f"AsyncTask(id={self.id!r}, title={self.title!r}, "
            f"status={self.status!r}, due={self.due.strftime('%a %m-%d-%Y') if self.due else None})"
        )