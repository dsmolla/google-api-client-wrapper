import pytest
import asyncio
from datetime import date, datetime
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from src.google_api_client.clients.tasks.async_client import (
    AsyncTaskList, AsyncTask, AsyncTasksError, AsyncTasksPermissionError, AsyncTasksNotFoundError
)


@pytest.mark.unit
@pytest.mark.tasks
class TestAsyncTaskList:
    """Test cases for the AsyncTaskList class."""
    
    def test_valid_task_list_creation(self):
        """Test creating a valid async task list."""
        task_list = AsyncTaskList(
            id="tasklist_123",
            title="My Task List",
            updated=datetime.now()
        )
        assert task_list.id == "tasklist_123"
        assert task_list.title == "My Task List"
        assert task_list.updated is not None
    
    def test_task_list_minimal_creation(self):
        """Test creating async task list with only title."""
        task_list = AsyncTaskList(title="Simple List")
        assert task_list.title == "Simple List"
        assert task_list.id is None
        assert task_list.updated is None
    
    def test_invalid_title_length(self):
        """Test that title exceeding max length raises ValueError."""
        long_title = "x" * 1025  # Exceeds MAX_TITLE_LENGTH (1024)
        with pytest.raises(ValueError, match="TaskList title cannot exceed"):
            AsyncTaskList(title=long_title)
    
    def test_from_google_tasklist(self):
        """Test creating AsyncTaskList from Google API response."""
        google_response = {
            "id": "tasklist_123",
            "title": "Test List",
            "updated": "2025-01-15T10:00:00.000Z"
        }
        
        task_list = AsyncTaskList._from_google_tasklist(google_response)
        assert task_list.id == "tasklist_123"
        assert task_list.title == "Test List"
        assert task_list.updated is not None
    
    def test_from_google_tasklist_invalid_date(self):
        """Test handling invalid date in Google API response."""
        google_response = {
            "id": "tasklist_123",
            "title": "Test List",
            "updated": "invalid-date"
        }
        
        task_list = AsyncTaskList._from_google_tasklist(google_response)
        assert task_list.id == "tasklist_123"
        assert task_list.title == "Test List"
        assert task_list.updated is None
    
    def test_to_dict(self):
        """Test converting AsyncTaskList to dictionary."""
        task_list = AsyncTaskList(id="tasklist_123", title="My List")
        result = task_list.to_dict()
        
        expected = {
            "id": "tasklist_123",
            "title": "My List"
        }
        assert result == expected
    
    def test_to_dict_partial(self):
        """Test converting AsyncTaskList to dictionary with only title."""
        task_list = AsyncTaskList(title="My List")
        result = task_list.to_dict()
        
        expected = {"title": "My List"}
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_list_task_lists(self, mock_get_async_tasks_service, mock_async_tasks_context):
        """Test listing task lists asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Mock API response
        mock_list_response = {
            'items': [
                {'id': 'list1', 'title': 'List 1', 'updated': '2025-01-15T10:00:00.000Z'},
                {'id': 'list2', 'title': 'List 2', 'updated': '2025-01-15T11:00:00.000Z'}
            ]
        }
        mock_aiogoogle.as_service_account.return_value = mock_list_response
        
        task_lists = await AsyncTaskList.list_task_lists()
        
        assert len(task_lists) == 2
        assert task_lists[0].id == 'list1'
        assert task_lists[0].title == 'List 1'
        assert task_lists[1].id == 'list2'
        assert task_lists[1].title == 'List 2'
        
        # Verify API was called correctly
        mock_aiogoogle.as_service_account.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_task_list(self, mock_get_async_tasks_service, mock_async_tasks_context):
        """Test getting a specific task list asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Mock API response
        mock_get_response = {
            'id': 'list_123',
            'title': 'My Task List',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_aiogoogle.as_service_account.return_value = mock_get_response
        
        task_list = await AsyncTaskList.get_task_list("list_123")
        
        assert task_list.id == 'list_123'
        assert task_list.title == 'My Task List'
        
        # Verify API was called correctly
        mock_aiogoogle.as_service_account.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_task_list(self, mock_get_async_tasks_service, mock_async_tasks_context):
        """Test creating a task list asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Mock API response
        mock_create_response = {
            'id': 'list_new_123',
            'title': 'New Task List',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_aiogoogle.as_service_account.return_value = mock_create_response
        
        task_list = await AsyncTaskList.create_task_list("New Task List")
        
        assert task_list.id == 'list_new_123'
        assert task_list.title == 'New Task List'
        
        # Verify API was called correctly
        mock_aiogoogle.as_service_account.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_task_list_invalid_title_length(self):
        """Test creating task list with invalid title length."""
        long_title = "x" * 1025
        with pytest.raises(ValueError, match="TaskList title cannot exceed"):
            await AsyncTaskList.create_task_list(long_title)
    
    @pytest.mark.asyncio
    async def test_update_task_list(self, mock_get_async_tasks_service, mock_async_tasks_context):
        """Test updating a task list asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Mock API response
        mock_update_response = {
            'id': 'list_123',
            'title': 'Updated Task List',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_aiogoogle.as_service_account.return_value = mock_update_response
        
        task_list = AsyncTaskList(id="list_123", title="Original Title")
        result = await task_list.update_task_list("Updated Task List")
        
        assert result.title == "Updated Task List"
        assert task_list.title == "Updated Task List"
        
        # Verify API was called correctly
        mock_aiogoogle.as_service_account.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_task_list(self, mock_get_async_tasks_service, mock_async_tasks_context):
        """Test deleting a task list asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Mock API response (delete returns None)
        mock_aiogoogle.as_service_account.return_value = None
        
        task_list = AsyncTaskList(id="list_123", title="To Delete")
        result = await task_list.delete_task_list()
        
        assert result is True
        
        # Verify API was called correctly
        mock_aiogoogle.as_service_account.assert_called_once()
    
    def test_repr(self):
        """Test string representation of AsyncTaskList."""
        task_list = AsyncTaskList(id="list_123", title="My List")
        expected = "AsyncTaskList(id='list_123', title='My List')"
        assert repr(task_list) == expected


class TestAsyncTask:
    """Test cases for the AsyncTask class."""
    
    def test_valid_task_creation(self):
        """Test creating a valid async task."""
        due_date = date.today()
        task = AsyncTask(
            id="task_123",
            title="Test Task",
            notes="This is a test task",
            status="needsAction",
            due=due_date,
            task_list_id="list_123"
        )
        
        assert task.id == "task_123"
        assert task.title == "Test Task"
        assert task.notes == "This is a test task"
        assert task.status == "needsAction"
        assert task.due == due_date
        assert task.task_list_id == "list_123"
    
    def test_task_minimal_creation(self):
        """Test creating async task with minimal information."""
        task = AsyncTask(title="Simple Task")
        assert task.title == "Simple Task"
        assert task.id is None
        assert task.status is None
        assert task.due is None
    
    def test_invalid_title_length(self):
        """Test that title exceeding max length raises ValueError."""
        long_title = "x" * 1025  # Exceeds MAX_TITLE_LENGTH (1024)
        with pytest.raises(ValueError, match="Task title cannot exceed"):
            AsyncTask(title=long_title)
    
    def test_invalid_notes_length(self):
        """Test that notes exceeding max length raises ValueError."""
        long_notes = "x" * 8193  # Exceeds MAX_NOTES_LENGTH (8192)
        with pytest.raises(ValueError, match="Task notes cannot exceed"):
            AsyncTask(title="Test", notes=long_notes)
    
    def test_invalid_status(self):
        """Test that invalid status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid task status"):
            AsyncTask(title="Test", status="invalid_status")
    
    def test_valid_statuses(self):
        """Test valid task statuses."""
        task1 = AsyncTask(title="Test", status="needsAction")
        task2 = AsyncTask(title="Test", status="completed")
        assert task1.status == "needsAction"
        assert task2.status == "completed"
    
    def test_from_google_task(self):
        """Test creating AsyncTask from Google API response."""
        google_response = {
            "id": "task_123",
            "title": "Test Task",
            "notes": "Test notes",
            "status": "needsAction",
            "due": "2025-01-15T00:00:00.000Z",
            "updated": "2025-01-15T10:00:00.000Z"
        }
        
        task = AsyncTask._from_google_task(google_response, "list_123")
        assert task.id == "task_123"
        assert task.title == "Test Task"
        assert task.notes == "Test notes"
        assert task.status == "needsAction"
        assert task.due == date(2025, 1, 15)
        assert task.task_list_id == "list_123"
    
    def test_from_google_task_invalid_dates(self):
        """Test handling invalid dates in Google API response."""
        google_response = {
            "id": "task_123",
            "title": "Test Task",
            "due": "invalid-date",
            "completed": "invalid-date",
            "updated": "invalid-date"
        }
        
        task = AsyncTask._from_google_task(google_response)
        assert task.id == "task_123"
        assert task.title == "Test Task"
        assert task.due is None
        assert task.completed is None
        assert task.updated is None
    
    def test_to_dict(self):
        """Test converting AsyncTask to dictionary."""
        due_date = date(2025, 1, 15)
        task = AsyncTask(
            id="task_123",
            title="Test Task",
            notes="Test notes",
            status="needsAction",
            due=due_date
        )
        result = task.to_dict()
        
        expected = {
            "id": "task_123",
            "title": "Test Task",
            "notes": "Test notes",
            "status": "needsAction",
            "due": "2025-01-15T00:00:00Z"
        }
        assert result == expected
    
    def test_to_dict_partial(self):
        """Test converting AsyncTask to dictionary with only required fields."""
        task = AsyncTask(title="Simple Task")
        result = task.to_dict()
        
        expected = {"title": "Simple Task"}
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_list_tasks(self, mock_get_async_tasks_service, mock_async_tasks_context):
        """Test listing tasks asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Mock API response
        mock_list_response = {
            'items': [
                {
                    'id': 'task1',
                    'title': 'Task 1',
                    'status': 'needsAction',
                    'updated': '2025-01-15T10:00:00.000Z'
                },
                {
                    'id': 'task2',
                    'title': 'Task 2',
                    'status': 'completed',
                    'updated': '2025-01-15T11:00:00.000Z'
                }
            ]
        }
        mock_aiogoogle.as_service_account.return_value = mock_list_response
        
        tasks = await AsyncTask.list_tasks("list_123", max_results=50)
        
        assert len(tasks) == 2
        assert tasks[0].id == 'task1'
        assert tasks[0].title == 'Task 1'
        assert tasks[0].status == 'needsAction'
        assert tasks[1].id == 'task2'
        assert tasks[1].title == 'Task 2'
        assert tasks[1].status == 'completed'
        
        # Verify API was called correctly
        mock_aiogoogle.as_service_account.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_tasks_invalid_max_results(self):
        """Test listing tasks with invalid max_results."""
        with pytest.raises(ValueError, match="max_results must be between"):
            await AsyncTask.list_tasks(max_results=0)
        
        with pytest.raises(ValueError, match="max_results must be between"):
            await AsyncTask.list_tasks(max_results=101)
    
    @pytest.mark.asyncio
    async def test_get_task(self, mock_get_async_tasks_service, mock_async_tasks_context):
        """Test getting a specific task asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Mock API response
        mock_get_response = {
            'id': 'task_123',
            'title': 'Test Task',
            'status': 'needsAction',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_aiogoogle.as_service_account.return_value = mock_get_response
        
        task = await AsyncTask.get_task("list_123", "task_123")
        
        assert task.id == 'task_123'
        assert task.title == 'Test Task'
        assert task.status == 'needsAction'
        assert task.task_list_id == 'list_123'
        
        # Verify API was called correctly
        mock_aiogoogle.as_service_account.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_task(self, mock_get_async_tasks_service, mock_async_tasks_context):
        """Test creating a task asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Mock API response
        mock_create_response = {
            'id': 'task_new_123',
            'title': 'New Task',
            'notes': 'Task notes',
            'status': 'needsAction',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_aiogoogle.as_service_account.return_value = mock_create_response
        
        due_date = date(2025, 1, 20)
        task = await AsyncTask.create_task(
            title="New Task",
            task_list_id="list_123",
            notes="Task notes",
            due=due_date
        )
        
        assert task.id == 'task_new_123'
        assert task.title == 'New Task'
        assert task.notes == 'Task notes'
        
        # Verify API was called correctly
        mock_aiogoogle.as_service_account.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_task_validation_errors(self):
        """Test task creation validation errors."""
        # Title too long
        long_title = "x" * 1025
        with pytest.raises(ValueError, match="Task title cannot exceed"):
            await AsyncTask.create_task(long_title)
        
        # Notes too long
        long_notes = "x" * 8193
        with pytest.raises(ValueError, match="Task notes cannot exceed"):
            await AsyncTask.create_task("Test", notes=long_notes)
    
    @pytest.mark.asyncio
    async def test_update_task(self, mock_get_async_tasks_service, mock_async_tasks_context):
        """Test updating a task asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Mock API response
        mock_update_response = {
            'id': 'task_123',
            'title': 'Updated Task',
            'notes': 'Updated notes',
            'status': 'completed',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_aiogoogle.as_service_account.return_value = mock_update_response
        
        task = AsyncTask(id="task_123", title="Original", task_list_id="list_123")
        result = await task.update_task(
            title="Updated Task",
            notes="Updated notes",
            status="completed"
        )
        
        assert result.title == "Updated Task"
        assert result.notes == "Updated notes"
        assert result.status == "completed"
        
        # Verify API was called correctly
        mock_aiogoogle.as_service_account.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_task_without_task_list_id(self):
        """Test updating task without task_list_id raises error."""
        task = AsyncTask(id="task_123", title="Test")
        with pytest.raises(ValueError, match="Task must have a task_list_id"):
            await task.update_task(title="Updated")
    
    @pytest.mark.asyncio
    async def test_delete_task(self, mock_get_async_tasks_service, mock_async_tasks_context):
        """Test deleting a task asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Mock API response (delete returns None)
        mock_aiogoogle.as_service_account.return_value = None
        
        task = AsyncTask(id="task_123", title="To Delete", task_list_id="list_123")
        result = await task.delete_task()
        
        assert result is True
        
        # Verify API was called correctly
        mock_aiogoogle.as_service_account.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_task_without_task_list_id(self):
        """Test deleting task without task_list_id raises error."""
        task = AsyncTask(id="task_123", title="Test")
        with pytest.raises(ValueError, match="Task must have a task_list_id"):
            await task.delete_task()
    
    @pytest.mark.asyncio
    async def test_move_task(self, mock_get_async_tasks_service, mock_async_tasks_context):
        """Test moving a task asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Mock API response
        mock_move_response = {
            'id': 'task_123',
            'title': 'Test Task',
            'parent': 'parent_123',
            'position': 'new_position',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_aiogoogle.as_service_account.return_value = mock_move_response
        
        task = AsyncTask(id="task_123", title="Test Task", task_list_id="list_123")
        result = await task.move_task(parent="parent_123", previous="prev_123")
        
        assert result.parent == "parent_123"
        
        # Verify API was called correctly
        mock_aiogoogle.as_service_account.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mark_completed(self, mock_get_async_tasks_service, mock_async_tasks_context):
        """Test marking task as completed asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Mock API response
        mock_update_response = {
            'id': 'task_123',
            'title': 'Test Task',
            'status': 'completed',
            'completed': '2025-01-15T00:00:00.000Z',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_aiogoogle.as_service_account.return_value = mock_update_response
        
        task = AsyncTask(id="task_123", title="Test Task", task_list_id="list_123")
        result = await task.mark_completed()
        
        assert result.status == "completed"
        # Verify update was called
        mock_aiogoogle.as_service_account.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mark_incomplete(self, mock_get_async_tasks_service, mock_async_tasks_context):
        """Test marking task as incomplete asynchronously."""
        # Setup mock async context manager
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Mock API response
        mock_update_response = {
            'id': 'task_123',
            'title': 'Test Task',
            'status': 'needsAction',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_aiogoogle.as_service_account.return_value = mock_update_response
        
        task = AsyncTask(id="task_123", title="Test Task", task_list_id="list_123", status="completed")
        result = await task.mark_incomplete()
        
        assert result.status == "needsAction"
        # Verify update was called
        mock_aiogoogle.as_service_account.assert_called_once()
    
    def test_is_completed(self):
        """Test checking if task is completed."""
        completed_task = AsyncTask(title="Test", status="completed")
        incomplete_task = AsyncTask(title="Test", status="needsAction")
        
        assert completed_task.is_completed() is True
        assert incomplete_task.is_completed() is False
    
    def test_is_overdue(self):
        """Test checking if task is overdue."""
        from datetime import timedelta
        
        # Task with past due date, not completed
        overdue_task = AsyncTask(
            title="Test",
            due=date.today() - timedelta(days=1),
            status="needsAction"
        )
        
        # Task with future due date
        future_task = AsyncTask(
            title="Test",
            due=date.today() + timedelta(days=1),
            status="needsAction"
        )
        
        # Completed task with past due date
        completed_overdue_task = AsyncTask(
            title="Test",
            due=date.today() - timedelta(days=1),
            status="completed"
        )
        
        # Task with no due date
        no_due_task = AsyncTask(title="Test", status="needsAction")
        
        assert overdue_task.is_overdue() is True
        assert future_task.is_overdue() is False
        assert completed_overdue_task.is_overdue() is False
        assert no_due_task.is_overdue() is False
    
    def test_repr(self):
        """Test string representation of AsyncTask."""
        due_date = date(2025, 1, 15)
        task = AsyncTask(
            id="task_123",
            title="Test Task",
            status="needsAction",
            due=due_date
        )
        
        repr_str = repr(task)
        assert "task_123" in repr_str
        assert "Test Task" in repr_str
        assert "needsAction" in repr_str
        assert "Wed 01-15-2025" in repr_str