from datetime import date, datetime, time
from typing import Optional, List, Self, TYPE_CHECKING
from ...utils.datetime import convert_datetime_to_readable, convert_datetime_to_local_timezone, convert_datetime_to_iso
from dataclasses import dataclass, field
import logging
from googleapiclient.errors import HttpError

if TYPE_CHECKING:
    from googleapiclient.discovery import Resource

logger = logging.getLogger(__name__)

# Constants
MAX_RESULTS_LIMIT = 100
MAX_TITLE_LENGTH = 1024
MAX_NOTES_LENGTH = 8192
DEFAULT_MAX_RESULTS = 100

# Import exceptions from centralized location
from ...exceptions.tasks import TasksError, TasksPermissionError, TasksNotFoundError


@dataclass
class TaskList:
    """
    Represents a Google Task List.
    Args:
        id: Unique identifier for the task list.
        title: The title of the task list.
        updated: Last modification time.
    """
    id: Optional[str] = None
    title: Optional[str] = None
    updated: Optional[datetime] = None
    _user_client: Optional["UserClient"] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        if self.title and len(self.title) > MAX_TITLE_LENGTH:
            raise ValueError(f"TaskList title cannot exceed {MAX_TITLE_LENGTH} characters")

    def set_user_client(self, user_client):
        """Set user context for this task list."""
        from ...user_client import UserClient
        self._user_client = user_client

    def _get_user_client(self):
        """Get the user client for this task list."""
        if self._user_client is None:
            raise ValueError("Task list must have user context. Use user.tasks methods to get task lists.")
        return self._user_client

    @staticmethod
    def _from_google_task_list(google_task_list: dict) -> "TaskList":
        """
        Creates a TaskList instance from a Google Tasks API response.
        Args:
            google_task_list: A dictionary containing task list data from Google Tasks API.
        Returns:
            A TaskList instance populated with the data from the dictionary.
        """
        def parse_datetime_field(field_value):
            if not field_value:
                return None
            try:
                return datetime.fromisoformat(field_value.replace('Z', '+00:00'))
            except:
                logger.warning("Failed to parse datetime: %s", field_value)
                return None

        return TaskList(
            id=google_task_list.get('id'),
            title=google_task_list.get('title'),
            updated=parse_datetime_field(google_task_list.get('updated'))
        )

    @staticmethod
    def _from_google_tasklist(google_tasklist: dict) -> "TaskList":
        """
        Creates a TaskList instance from a Google Tasks API response.
        Args:
            google_tasklist: A dictionary containing task list data from Google Tasks API.
        Returns:
            A TaskList instance populated with the data from the dictionary.
        """
        updated = None
        if google_tasklist.get('updated'):
            try:
                updated = datetime.fromisoformat(google_tasklist['updated'].replace('Z', '+00:00'))
                updated = convert_datetime_to_local_timezone(updated)
            except:
                logger.warning("Failed to parse updated time: %s", google_tasklist.get('updated'))

        return TaskList(
            id=google_tasklist.get('id'),
            title=google_tasklist.get('title'),
            updated=updated
        )

    def to_dict(self) -> dict:
        """Convert TaskList to dictionary format for Google Tasks API."""
        task_list_dict = {}
        if self.id:
            task_list_dict['id'] = self.id
        if self.title:
            task_list_dict['title'] = self.title
        return task_list_dict


    def update_task_list(self, title: str) -> "TaskList":
        """
        Updates the title of this task list.
        Args:
            title: The new title for the task list.
        Returns:
            The updated TaskList object.
        """
        if not self.id:
            raise ValueError("TaskList must have an ID to be updated")
        if len(title) > MAX_TITLE_LENGTH:
            raise ValueError(f"TaskList title cannot exceed {MAX_TITLE_LENGTH} characters")
        
        logger.info("Updating task list %s to new title: %s", self.id, title)
        user_client = self._get_user_client()
        updated_list = user_client.tasks._update_task_list(self.id, title)
        self.title = updated_list.title
        return self

    def delete_task_list(self) -> bool:
        """
        Deletes this task list.
        Returns:
            True if the task list was successfully deleted, False otherwise.
        """
        logger.info("Deleting task list with ID: %s", self.id)
        user_client = self._get_user_client()
        return user_client.tasks._delete_task_list(self.id)

    @staticmethod
    def _list_task_lists_with_service(service: "Resource") -> List["TaskList"]:
        """Implementation of list_task_lists using direct service."""
        logger.info("Fetching task lists")
        
        try:
            task_lists_result = service.tasklists().list().execute()
            task_lists_data = task_lists_result.get('items', [])
            
            task_list_objects = []
            for task_list_data in task_lists_data:
                try:
                    task_list = TaskList._from_google_task_list(task_list_data)
                    task_list_objects.append(task_list)
                except Exception as e:
                    logger.warning("Failed to parse task list %s: %s", task_list_data.get('id'), e)
                    continue
            
            logger.info("Retrieved %d task lists", len(task_list_objects))
            return task_list_objects
            
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied: {e}")
            else:
                raise TasksError(f"Tasks API error listing task lists: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected error listing task lists: {e}")

    @staticmethod
    def _get_task_list_with_service(service: "Resource", task_list_id: str) -> "TaskList":
        """Implementation of get_task_list using direct service."""
        logger.info("Fetching task list with ID: %s", task_list_id)
        
        try:
            task_list_data = service.tasklists().get(
                tasklist=task_list_id
            ).execute()
            
            task_list = TaskList._from_google_task_list(task_list_data)
            return task_list
            
        except HttpError as e:
            if e.resp.status == 404:
                raise TasksNotFoundError(f"Task list not found: {task_list_id}")
            elif e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied accessing task list: {e}")
            else:
                raise TasksError(f"Tasks API error getting task list {task_list_id}: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected error getting task list: {e}")

    @staticmethod
    def _create_task_list_with_service(service: "Resource", title: str) -> "TaskList":
        """Implementation of create_task_list using direct service."""
        logger.info("Creating task list: %s", title)
        
        if not title or not title.strip():
            raise ValueError("Task list title cannot be empty")
        
        try:
            task_list_body = {
                'title': title.strip()
            }
            
            created_task_list = service.tasklists().insert(
                body=task_list_body
            ).execute()
            
            task_list = TaskList._from_google_task_list(created_task_list)
            logger.info("Task list created successfully with ID: %s", task_list.id)
            return task_list
            
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied creating task list: {e}")
            else:
                raise TasksError(f"Tasks API error creating task list: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected error creating task list: {e}")

    def __repr__(self):
        return f"TaskList(id={self.id!r}, title={self.title!r})"


@dataclass
class Task:
    """
    Represents a Google Task.
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
    _user_client: Optional["UserClient"] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        if self.title and len(self.title) > MAX_TITLE_LENGTH:
            raise ValueError(f"Task title cannot exceed {MAX_TITLE_LENGTH} characters")
        if self.notes and len(self.notes) > MAX_NOTES_LENGTH:
            raise ValueError(f"Task notes cannot exceed {MAX_NOTES_LENGTH} characters")
        if self.status and self.status not in ['needsAction', 'completed']:
            raise ValueError(f"Invalid task status: {self.status}. Must be 'needsAction' or 'completed'")

    def set_user_client(self, user_client):
        """Set user context for this task."""
        from ...user_client import UserClient
        self._user_client = user_client

    def _get_user_client(self):
        """Get the user client for this task."""
        if self._user_client is None:
            raise ValueError("Task must have user context. Use user.tasks methods to get tasks.")
        return self._user_client

    @staticmethod
    def _from_google_task(google_task: dict, task_list_id: Optional[str] = None) -> "Task":
        """
        Creates a Task instance from a Google Tasks API response.
        Args:
            google_task: A dictionary containing task data from Google Tasks API.
            task_list_id: The ID of the task list this task belongs to.
        Returns:
            A Task instance populated with the data from the dictionary.
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

        return Task(
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
        """Convert Task to dictionary format for Google Tasks API."""
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


    def update_task(
            self,
            title: str=None,
            notes: str=None,
            status: str=None,
            completed: date=None,
            due: date=None
    ) -> "Task":
        """
        Updates this task in Google Tasks.
        Args:
            title: The title of the task (optional).
            notes: Notes for the task (optional).
            status: The status of the task (optional).
            completed: The completed date of the task (optional).
            due: Due date for the task (optional).

        Returns:
            The updated Task object.
        """
        if not self.task_list_id:
            raise ValueError("Task must have a task_list_id to be updated")
        
        logger.info("Updating task with ID: %s", self.id)
        user_client = self._get_user_client()
        return user_client.tasks._update_task(self.task_list_id, self.id, title, notes, status, completed, due)

    def delete_task(self) -> bool:
        """
        Deletes this task.
        Returns:
            True if the task was successfully deleted, False otherwise.
        """
        if not self.task_list_id:
            raise ValueError("Task must have a task_list_id to be deleted")
        
        logger.info("Deleting task with ID: %s", self.id)
        user_client = self._get_user_client()
        return user_client.tasks._delete_task(self.task_list_id, self.id)

    def move_task(self, parent: Optional[str] = None, previous: Optional[str] = None) -> "Task":
        """
        Moves this task to a different position in the task list.
        Args:
            parent: Parent task ID (optional).
            previous: Previous sibling task ID (optional).
        Returns:
            The updated Task object.
        """
        if not self.task_list_id:
            raise ValueError("Task must have a task_list_id to be moved")
        
        logger.info("Moving task with ID: %s", self.id)
        user_client = self._get_user_client()
        return user_client.tasks._move_task(self.task_list_id, self.id, parent, previous)

    def mark_completed(self) -> "Task":
        """
        Marks this task as completed.
        Returns:
            The updated Task object.
        """
        return self.update_task(status='completed', completed=date.today())

    def mark_incomplete(self) -> "Task":
        """
        Marks this task as needing action (incomplete).
        Returns:
            The updated Task object.
        """
        return self.update_task(status='needsAction')

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

    @staticmethod
    def _list_tasks_with_service(service: "Resource", task_list_id: str='@default', max_results: Optional[int] = 100) -> List["Task"]:
        """Implementation of list_tasks using direct service."""
        logger.info("Fetching tasks from task list: %s, max_results: %s", task_list_id, max_results)
        
        if max_results and (max_results < 1 or max_results > MAX_RESULTS_LIMIT):
            raise ValueError(f"max_results must be between 1 and {MAX_RESULTS_LIMIT}")
        
        try:
            request_params = {
                'tasklist': task_list_id,
                'maxResults': max_results or DEFAULT_MAX_RESULTS
            }
            
            tasks_result = service.tasks().list(**request_params).execute()
            tasks_data = tasks_result.get('items', [])
            
            task_objects = []
            for task_data in tasks_data:
                try:
                    task = Task._from_google_task(task_data, task_list_id)
                    task_objects.append(task)
                except Exception as e:
                    logger.warning("Failed to parse task %s: %s", task_data.get('id'), e)
                    continue
            
            logger.info("Retrieved %d tasks", len(task_objects))
            return task_objects
            
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied: {e}")
            elif e.resp.status == 404:
                raise TasksNotFoundError(f"Task list not found: {task_list_id}")
            else:
                raise TasksError(f"Tasks API error listing tasks: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected error listing tasks: {e}")

    @staticmethod
    def _get_task_with_service(service: "Resource", task_list_id: str, task_id: str) -> "Task":
        """Implementation of get_task using direct service."""
        logger.info("Fetching task with ID: %s from task list: %s", task_id, task_list_id)
        
        try:
            task_data = service.tasks().get(
                tasklist=task_list_id,
                task=task_id
            ).execute()
            
            task = Task._from_google_task(task_data, task_list_id)
            return task
            
        except HttpError as e:
            if e.resp.status == 404:
                raise TasksNotFoundError(f"Task not found: {task_id}")
            elif e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied accessing task: {e}")
            else:
                raise TasksError(f"Tasks API error getting task {task_id}: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected error getting task: {e}")

    @staticmethod
    def _create_task_with_service(service: "Resource", title: str, task_list_id: str = '@default', **kwargs) -> "Task":
        """Implementation of create_task using direct service."""
        logger.info("Creating task: %s in task list: %s", title, task_list_id)
        
        if not title or not title.strip():
            raise ValueError("Task title cannot be empty")
        
        try:
            task_body = {
                'title': title.strip()
            }
            
            # Add optional fields if provided
            if kwargs.get('notes'):
                task_body['notes'] = kwargs['notes']
            if kwargs.get('due'):
                # Convert due date to the format expected by Tasks API
                if isinstance(kwargs['due'], date):
                    task_body['due'] = datetime.combine(kwargs['due'], time.min).isoformat() + 'Z'
                elif isinstance(kwargs['due'], datetime):
                    task_body['due'] = kwargs['due'].isoformat() + 'Z'
            if kwargs.get('parent'):
                task_body['parent'] = kwargs['parent']
            if kwargs.get('position'):
                task_body['position'] = kwargs['position']
            
            created_task = service.tasks().insert(
                tasklist=task_list_id,
                body=task_body
            ).execute()
            
            task = Task._from_google_task(created_task, task_list_id)
            logger.info("Task created successfully with ID: %s", task.id)
            return task
            
        except HttpError as e:
            if e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied creating task: {e}")
            elif e.resp.status == 404:
                raise TasksNotFoundError(f"Task list not found: {task_list_id}")
            else:
                raise TasksError(f"Tasks API error creating task: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected error creating task: {e}")

    def __repr__(self):
        return (
            f"Task(id={self.id!r}, title={self.title!r}, "
            f"status={self.status!r}, due={self.due.strftime("%a %m-%d-%Y") if self.due else None})"
        )


class TasksService:
    """
    Service layer for Tasks API operations.
    Contains all Tasks API functionality that was removed from dataclasses.
    """
    
    def __init__(self, service: "Resource", user_client: "UserClient"):
        """
        Initialize Tasks service.
        
        Args:
            service: The Tasks API service instance
            user_client: The user client for context
        """
        self._service = service
        self._user_client = user_client

    def list_tasks(self, task_list_id: str = '@default', max_results: Optional[int] = 100) -> List[Task]:
        """List tasks for the user."""
        tasks = Task._list_tasks_with_service(self._service, task_list_id, max_results)
        # Set user context for each task
        for task in tasks:
            task.set_user_client(self._user_client)
        return tasks

    def get_task(self, task_list_id: str, task_id: str) -> Task:
        """Get specific task by ID."""
        task = Task._get_task_with_service(self._service, task_list_id, task_id)
        task.set_user_client(self._user_client)
        return task

    def create_task(self, title: str, task_list_id: str = '@default', **kwargs) -> Task:
        """Create task for the user."""
        task = Task._create_task_with_service(self._service, title, task_list_id, **kwargs)
        task.set_user_client(self._user_client)
        return task

    def list_task_lists(self) -> List[TaskList]:
        """List task lists for the user."""
        task_lists = TaskList._list_task_lists_with_service(self._service)
        # Set user context for each task list
        for task_list in task_lists:
            task_list.set_user_client(self._user_client)
        return task_lists

    def get_task_list(self, task_list_id: str) -> TaskList:
        """Get specific task list by ID."""
        task_list = TaskList._get_task_list_with_service(self._service, task_list_id)
        task_list.set_user_client(self._user_client)
        return task_list

    def create_task_list(self, title: str) -> TaskList:
        """Create task list for the user."""
        task_list = TaskList._create_task_list_with_service(self._service, title)
        task_list.set_user_client(self._user_client)
        return task_list

    def _update_task(self, task_list_id: str, task_id: str, title: str = None, notes: str = None, 
                    status: str = None, completed: date = None, due: date = None) -> Task:
        """Update task."""
        logger.info("Updating task %s in task list %s", task_id, task_list_id)
        
        try:
            task_body = {}
            if title:
                task_body['title'] = title
            if notes is not None:
                task_body['notes'] = notes
            if status:
                task_body['status'] = status
            if completed:
                task_body['completed'] = datetime.combine(completed, time.min).isoformat() + 'Z'
            if due:
                task_body['due'] = datetime.combine(due, time.min).isoformat() + 'Z'
            
            updated_task = self._service.tasks().update(
                tasklist=task_list_id,
                task=task_id,
                body=task_body
            ).execute()
            
            task = Task._from_google_task(updated_task, task_list_id)
            task.set_user_client(self._user_client)
            logger.info("Task updated successfully")
            return task
            
        except HttpError as e:
            if e.resp.status == 404:
                raise TasksNotFoundError(f"Task not found: {task_id}")
            elif e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied updating task: {e}")
            else:
                raise TasksError(f"Tasks API error updating task {task_id}: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected error updating task: {e}")

    def _delete_task(self, task_list_id: str, task_id: str) -> bool:
        """Delete task."""
        logger.info("Deleting task %s from task list %s", task_id, task_list_id)
        
        try:
            self._service.tasks().delete(
                tasklist=task_list_id,
                task=task_id
            ).execute()
            
            logger.info("Task deleted successfully")
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                raise TasksNotFoundError(f"Task not found: {task_id}")
            elif e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied deleting task: {e}")
            else:
                raise TasksError(f"Tasks API error deleting task {task_id}: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected error deleting task: {e}")

    def _move_task(self, task_list_id: str, task_id: str, parent: Optional[str] = None, previous: Optional[str] = None) -> Task:
        """Move task."""
        logger.info("Moving task %s in task list %s", task_id, task_list_id)
        
        try:
            request_params = {
                'tasklist': task_list_id,
                'task': task_id
            }
            if parent:
                request_params['parent'] = parent
            if previous:
                request_params['previous'] = previous
            
            moved_task = self._service.tasks().move(**request_params).execute()
            
            task = Task._from_google_task(moved_task, task_list_id)
            task.set_user_client(self._user_client)
            logger.info("Task moved successfully")
            return task
            
        except HttpError as e:
            if e.resp.status == 404:
                raise TasksNotFoundError(f"Task not found: {task_id}")
            elif e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied moving task: {e}")
            else:
                raise TasksError(f"Tasks API error moving task {task_id}: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected error moving task: {e}")

    def _update_task_list(self, task_list_id: str, title: str) -> TaskList:
        """Update task list."""
        logger.info("Updating task list %s with title: %s", task_list_id, title)
        
        if not title or not title.strip():
            raise ValueError("Task list title cannot be empty")
        
        try:
            task_list_body = {
                'id': task_list_id,
                'title': title.strip()
            }
            
            updated_task_list = self._service.tasklists().update(
                tasklist=task_list_id,
                body=task_list_body
            ).execute()
            
            task_list = TaskList._from_google_task_list(updated_task_list)
            task_list.set_user_client(self._user_client)
            logger.info("Task list updated successfully")
            return task_list
            
        except HttpError as e:
            if e.resp.status == 404:
                raise TasksNotFoundError(f"Task list not found: {task_list_id}")
            elif e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied updating task list: {e}")
            else:
                raise TasksError(f"Tasks API error updating task list {task_list_id}: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected error updating task list: {e}")

    def _delete_task_list(self, task_list_id: str) -> bool:
        """Delete task list."""
        logger.info("Deleting task list %s", task_list_id)
        
        try:
            self._service.tasklists().delete(
                tasklist=task_list_id
            ).execute()
            
            logger.info("Task list deleted successfully")
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                raise TasksNotFoundError(f"Task list not found: {task_list_id}")
            elif e.resp.status == 403:
                raise TasksPermissionError(f"Permission denied deleting task list: {e}")
            elif e.resp.status == 400:
                raise TasksError(f"Cannot delete default task list: {task_list_id}")
            else:
                raise TasksError(f"Tasks API error deleting task list {task_list_id}: {e}")
        except Exception as e:
            raise TasksError(f"Unexpected error deleting task list: {e}")

    def query(self):
        """Create task query builder for this user."""
        from .query_builder import TaskQueryBuilder
        return TaskQueryBuilder(Task, self._service, self._user_client)