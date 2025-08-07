import pytest
from datetime import date, datetime
from unittest.mock import Mock, MagicMock, patch
from src.google_api_client.clients.tasks.client import (
    TaskList, Task, TasksError, TasksPermissionError, TasksNotFoundError
)


@pytest.mark.unit
@pytest.mark.tasks


class TestTaskList:
    """Test cases for the TaskList class."""
    
    def test_valid_task_list_creation(self):
        """Test creating a valid task list."""
        task_list = TaskList(
            id="tasklist_123",
            title="My Task List",
            updated=datetime.now()
        )
        assert task_list.id == "tasklist_123"
        assert task_list.title == "My Task List"
        assert task_list.updated is not None
    
    def test_task_list_minimal_creation(self):
        """Test creating task list with only title."""
        task_list = TaskList(title="Simple List")
        assert task_list.title == "Simple List"
        assert task_list.id is None
        assert task_list.updated is None
    
    def test_invalid_title_length(self):
        """Test that title exceeding max length raises ValueError."""
        long_title = "x" * 1025  # Exceeds MAX_TITLE_LENGTH (1024)
        with pytest.raises(ValueError, match="TaskList title cannot exceed"):
            TaskList(title=long_title)
    
    def test_from_google_tasklist(self):
        """Test creating TaskList from Google API response."""
        google_response = {
            "id": "tasklist_123",
            "title": "Test List",
            "updated": "2025-01-15T10:00:00.000Z"
        }
        
        task_list = TaskList._from_google_tasklist(google_response)
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
        
        task_list = TaskList._from_google_tasklist(google_response)
        assert task_list.id == "tasklist_123"
        assert task_list.title == "Test List"
        assert task_list.updated is None
    
    def test_to_dict(self):
        """Test converting TaskList to dictionary."""
        task_list = TaskList(id="tasklist_123", title="My List")
        result = task_list.to_dict()
        
        expected = {
            "id": "tasklist_123",
            "title": "My List"
        }
        assert result == expected
    
    def test_to_dict_partial(self):
        """Test converting TaskList to dictionary with only title."""
        task_list = TaskList(title="My List")
        result = task_list.to_dict()
        
        expected = {"title": "My List"}
        assert result == expected
    
    def test_list_task_lists(self, mock_get_tasks_service, mock_tasks_service):
        """Test listing task lists."""
        # Setup mock service
        mock_service = mock_tasks_service
        
        # Mock API response
        mock_list_response = {
            'items': [
                {'id': 'list1', 'title': 'List 1', 'updated': '2025-01-15T10:00:00.000Z'},
                {'id': 'list2', 'title': 'List 2', 'updated': '2025-01-15T11:00:00.000Z'}
            ]
        }
        mock_service.tasklists.return_value.list.return_value.execute.return_value = mock_list_response
        
        task_lists = TaskList.list_task_lists()
        
        assert len(task_lists) == 2
        assert task_lists[0].id == 'list1'
        assert task_lists[0].title == 'List 1'
        assert task_lists[1].id == 'list2'
        assert task_lists[1].title == 'List 2'
        
        # Verify API was called correctly
        mock_service.tasklists.return_value.list.assert_called_once()
    
    def test_get_task_list(self, mock_get_tasks_service, mock_tasks_service):
        """Test getting a specific task list."""
        # Setup mock service
        mock_service = mock_tasks_service
        
        # Mock API response
        mock_get_response = {
            'id': 'list_123',
            'title': 'My Task List',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_service.tasklists.return_value.get.return_value.execute.return_value = mock_get_response
        
        task_list = TaskList.get_task_list("list_123")
        
        assert task_list.id == 'list_123'
        assert task_list.title == 'My Task List'
        
        # Verify API was called correctly
        mock_service.tasklists.return_value.get.assert_called_once_with(tasklist='list_123')
    
    def test_create_task_list(self, mock_get_tasks_service, mock_tasks_service):
        """Test creating a task list."""
        # Setup mock service
        mock_service = mock_tasks_service
        
        # Mock API response
        mock_create_response = {
            'id': 'list_new_123',
            'title': 'New Task List',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_service.tasklists.return_value.insert.return_value.execute.return_value = mock_create_response
        
        task_list = TaskList.create_task_list("New Task List")
        
        assert task_list.id == 'list_new_123'
        assert task_list.title == 'New Task List'
        
        # Verify API was called correctly
        mock_service.tasklists.return_value.insert.assert_called_once_with(
            body={'title': 'New Task List'}
        )
    
    def test_create_task_list_invalid_title_length(self):
        """Test creating task list with invalid title length."""
        long_title = "x" * 1025
        with pytest.raises(ValueError, match="TaskList title cannot exceed"):
            TaskList.create_task_list(long_title)
    
    def test_update_task_list(self, mock_get_tasks_service, mock_tasks_service):
        """Test updating a task list."""
        # Setup mock service
        mock_service = mock_tasks_service
        
        # Mock API response
        mock_update_response = {
            'id': 'list_123',
            'title': 'Updated Task List',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_service.tasklists.return_value.update.return_value.execute.return_value = mock_update_response
        
        task_list = TaskList(id="list_123", title="Original Title")
        result = task_list.update_task_list("Updated Task List")
        
        assert result.title == "Updated Task List"
        assert task_list.title == "Updated Task List"
        
        # Verify API was called correctly
        mock_service.tasklists.return_value.update.assert_called_once_with(
            tasklist='list_123',
            body={'id': 'list_123', 'title': 'Updated Task List'}
        )
    
    def test_delete_task_list(self, mock_get_tasks_service, mock_tasks_service):
        """Test deleting a task list."""
        # Setup mock service
        mock_service = mock_tasks_service
        
        task_list = TaskList(id="list_123", title="To Delete")
        result = task_list.delete_task_list()
        
        assert result is True
        
        # Verify API was called correctly
        mock_service.tasklists.return_value.delete.assert_called_once_with(tasklist='list_123')
    
    def test_repr(self):
        """Test string representation of TaskList."""
        task_list = TaskList(id="list_123", title="My List")
        expected = "TaskList(id='list_123', title='My List')"
        assert repr(task_list) == expected


class TestTask:
    """Test cases for the Task class."""
    
    def test_valid_task_creation(self):
        """Test creating a valid task."""
        due_date = date.today()
        task = Task(
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
        """Test creating task with minimal information."""
        task = Task(title="Simple Task")
        assert task.title == "Simple Task"
        assert task.id is None
        assert task.status is None
        assert task.due is None
    
    def test_invalid_title_length(self):
        """Test that title exceeding max length raises ValueError."""
        long_title = "x" * 1025  # Exceeds MAX_TITLE_LENGTH (1024)
        with pytest.raises(ValueError, match="Task title cannot exceed"):
            Task(title=long_title)
    
    def test_invalid_notes_length(self):
        """Test that notes exceeding max length raises ValueError."""
        long_notes = "x" * 8193  # Exceeds MAX_NOTES_LENGTH (8192)
        with pytest.raises(ValueError, match="Task notes cannot exceed"):
            Task(title="Test", notes=long_notes)
    
    def test_invalid_status(self):
        """Test that invalid status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid task status"):
            Task(title="Test", status="invalid_status")
    
    def test_valid_statuses(self):
        """Test valid task statuses."""
        task1 = Task(title="Test", status="needsAction")
        task2 = Task(title="Test", status="completed")
        assert task1.status == "needsAction"
        assert task2.status == "completed"
    
    def test_from_google_task(self):
        """Test creating Task from Google API response."""
        google_response = {
            "id": "task_123",
            "title": "Test Task",
            "notes": "Test notes",
            "status": "needsAction",
            "due": "2025-01-15T00:00:00.000Z",
            "updated": "2025-01-15T10:00:00.000Z"
        }
        
        task = Task._from_google_task(google_response, "list_123")
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
        
        task = Task._from_google_task(google_response)
        assert task.id == "task_123"
        assert task.title == "Test Task"
        assert task.due is None
        assert task.completed is None
        assert task.updated is None
    
    def test_to_dict(self):
        """Test converting Task to dictionary."""
        due_date = date(2025, 1, 15)
        task = Task(
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
        """Test converting Task to dictionary with only required fields."""
        task = Task(title="Simple Task")
        result = task.to_dict()
        
        expected = {"title": "Simple Task"}
        assert result == expected
    
    def test_list_tasks(self, mock_get_tasks_service, mock_tasks_service):
        """Test listing tasks."""
        # Setup mock service
        mock_service = mock_tasks_service
        
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
        mock_service.tasks.return_value.list.return_value.execute.return_value = mock_list_response
        
        tasks = Task.list_tasks("list_123", max_results=50)
        
        assert len(tasks) == 2
        assert tasks[0].id == 'task1'
        assert tasks[0].title == 'Task 1'
        assert tasks[0].status == 'needsAction'
        assert tasks[1].id == 'task2'
        assert tasks[1].title == 'Task 2'
        assert tasks[1].status == 'completed'
        
        # Verify API was called correctly
        mock_service.tasks.return_value.list.assert_called_once_with(
            tasklist='list_123',
            maxResults=50
        )
    
    def test_list_tasks_invalid_max_results(self):
        """Test listing tasks with invalid max_results."""
        # Test validation without needing API service (validation happens before service call)
        with pytest.raises(ValueError, match="max_results must be between"):
            Task.list_tasks(max_results=0)
        
        with pytest.raises(ValueError, match="max_results must be between"):
            Task.list_tasks(max_results=101)
    
    def test_get_task(self, mock_get_tasks_service, mock_tasks_service):
        """Test getting a specific task."""
        # Setup mock service
        mock_service = mock_tasks_service
        
        # Mock API response
        mock_get_response = {
            'id': 'task_123',
            'title': 'Test Task',
            'status': 'needsAction',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_service.tasks.return_value.get.return_value.execute.return_value = mock_get_response
        
        task = Task.get_task("list_123", "task_123")
        
        assert task.id == 'task_123'
        assert task.title == 'Test Task'
        assert task.status == 'needsAction'
        assert task.task_list_id == 'list_123'
        
        # Verify API was called correctly
        mock_service.tasks.return_value.get.assert_called_once_with(
            tasklist='list_123',
            task='task_123'
        )
    
    def test_create_task(self, mock_get_tasks_service, mock_tasks_service):
        """Test creating a task."""
        # Setup mock service
        mock_service = mock_tasks_service
        
        # Mock API response
        mock_create_response = {
            'id': 'task_new_123',
            'title': 'New Task',
            'notes': 'Task notes',
            'status': 'needsAction',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_service.tasks.return_value.insert.return_value.execute.return_value = mock_create_response
        
        due_date = date(2025, 1, 20)
        task = Task.create_task(
            title="New Task",
            task_list_id="list_123",
            notes="Task notes",
            due=due_date
        )
        
        assert task.id == 'task_new_123'
        assert task.title == 'New Task'
        assert task.notes == 'Task notes'
        
        # Verify API was called correctly
        mock_service.tasks.return_value.insert.assert_called_once()
        call_args = mock_service.tasks.return_value.insert.call_args
        assert call_args[1]['tasklist'] == 'list_123'
        assert call_args[1]['body']['title'] == 'New Task'
        assert call_args[1]['body']['notes'] == 'Task notes'
        assert 'due' in call_args[1]['body']
    
    def test_create_task_validation_errors(self):
        """Test task creation validation errors."""
        # Title too long
        long_title = "x" * 1025
        with pytest.raises(ValueError, match="Task title cannot exceed"):
            Task.create_task(long_title)
        
        # Notes too long
        long_notes = "x" * 8193
        with pytest.raises(ValueError, match="Task notes cannot exceed"):
            Task.create_task("Test", notes=long_notes)
    
    def test_update_task(self, mock_get_tasks_service, mock_tasks_service):
        """Test updating a task."""
        # Setup mock service
        mock_service = mock_tasks_service
        
        # Mock API response
        mock_update_response = {
            'id': 'task_123',
            'title': 'Updated Task',
            'notes': 'Updated notes',
            'status': 'completed',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_service.tasks.return_value.update.return_value.execute.return_value = mock_update_response
        
        task = Task(id="task_123", title="Original", task_list_id="list_123")
        result = task.update_task(
            title="Updated Task",
            notes="Updated notes",
            status="completed"
        )
        
        assert result.title == "Updated Task"
        assert result.notes == "Updated notes"
        assert result.status == "completed"
        
        # Verify API was called correctly
        mock_service.tasks.return_value.update.assert_called_once()
    
    def test_update_task_without_task_list_id(self):
        """Test updating task without task_list_id raises error."""
        task = Task(id="task_123", title="Test")
        with pytest.raises(ValueError, match="Task must have a task_list_id"):
            task.update_task(title="Updated")
    
    def test_delete_task(self, mock_get_tasks_service, mock_tasks_service):
        """Test deleting a task."""
        # Setup mock service
        mock_service = mock_tasks_service
        
        task = Task(id="task_123", title="To Delete", task_list_id="list_123")
        result = task.delete_task()
        
        assert result is True
        
        # Verify API was called correctly
        mock_service.tasks.return_value.delete.assert_called_once_with(
            tasklist='list_123',
            task='task_123'
        )
    
    def test_delete_task_without_task_list_id(self):
        """Test deleting task without task_list_id raises error."""
        task = Task(id="task_123", title="Test")
        with pytest.raises(ValueError, match="Task must have a task_list_id"):
            task.delete_task()
    
    def test_move_task(self, mock_get_tasks_service, mock_tasks_service):
        """Test moving a task."""
        # Setup mock service
        mock_service = mock_tasks_service
        
        # Mock API response
        mock_move_response = {
            'id': 'task_123',
            'title': 'Test Task',
            'parent': 'parent_123',
            'position': 'new_position',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_service.tasks.return_value.move.return_value.execute.return_value = mock_move_response
        
        task = Task(id="task_123", title="Test Task", task_list_id="list_123")
        result = task.move_task(parent="parent_123", previous="prev_123")
        
        assert result.parent == "parent_123"
        
        # Verify API was called correctly
        mock_service.tasks.return_value.move.assert_called_once_with(
            tasklist='list_123',
            task='task_123',
            parent='parent_123',
            previous='prev_123'
        )
    
    def test_mark_completed(self, mock_get_tasks_service, mock_tasks_service):
        """Test marking task as completed."""
        # Setup mock service
        mock_service = mock_tasks_service
        
        # Mock API response
        mock_update_response = {
            'id': 'task_123',
            'title': 'Test Task',
            'status': 'completed',
            'completed': '2025-01-15T00:00:00.000Z',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_service.tasks.return_value.update.return_value.execute.return_value = mock_update_response
        
        task = Task(id="task_123", title="Test Task", task_list_id="list_123")
        result = task.mark_completed()
        
        assert result.status == "completed"
        # Verify update was called
        mock_service.tasks.return_value.update.assert_called_once()
    
    def test_mark_incomplete(self, mock_get_tasks_service, mock_tasks_service):
        """Test marking task as incomplete."""
        # Setup mock service
        mock_service = mock_tasks_service
        
        # Mock API response
        mock_update_response = {
            'id': 'task_123',
            'title': 'Test Task',
            'status': 'needsAction',
            'updated': '2025-01-15T10:00:00.000Z'
        }
        mock_service.tasks.return_value.update.return_value.execute.return_value = mock_update_response
        
        task = Task(id="task_123", title="Test Task", task_list_id="list_123", status="completed")
        result = task.mark_incomplete()
        
        assert result.status == "needsAction"
        # Verify update was called
        mock_service.tasks.return_value.update.assert_called_once()
    
    def test_is_completed(self):
        """Test checking if task is completed."""
        completed_task = Task(title="Test", status="completed")
        incomplete_task = Task(title="Test", status="needsAction")
        
        assert completed_task.is_completed() is True
        assert incomplete_task.is_completed() is False
    
    def test_is_overdue(self):
        """Test checking if task is overdue."""
        from datetime import timedelta
        
        # Task with past due date, not completed
        overdue_task = Task(
            title="Test",
            due=date.today() - timedelta(days=1),
            status="needsAction"
        )
        
        # Task with future due date
        future_task = Task(
            title="Test",
            due=date.today() + timedelta(days=1),
            status="needsAction"
        )
        
        # Completed task with past due date
        completed_overdue_task = Task(
            title="Test",
            due=date.today() - timedelta(days=1),
            status="completed"
        )
        
        # Task with no due date
        no_due_task = Task(title="Test", status="needsAction")
        
        assert overdue_task.is_overdue() is True
        assert future_task.is_overdue() is False
        assert completed_overdue_task.is_overdue() is False
        assert no_due_task.is_overdue() is False
    
    def test_repr(self):
        """Test string representation of Task."""
        due_date = date(2025, 1, 15)
        task = Task(
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