import pytest
import asyncio
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, AsyncMock
from src.google_api_client.clients.tasks.client import TaskList, Task
from src.google_api_client.clients.tasks.async_client import AsyncTaskList, AsyncTask


@pytest.mark.integration
@pytest.mark.tasks


@pytest.mark.integration
class TestTasksIntegration:
    """Integration tests for Tasks functionality with mocked API calls."""
    
    def test_end_to_end_task_lifecycle(self, mock_get_tasks_service, mock_tasks_service, sample_task_response):
        """Test complete task lifecycle: create, read, update, complete, delete."""
        # Setup mock service using fixture
        mock_service = mock_tasks_service
        
        # Mock responses for different operations
        created_task_response = {
            "id": "task_created_123",
            "title": "Integration Test Task",
            "notes": "This is a test task for integration testing.",
            "status": "needsAction",
            "updated": "2025-01-15T10:00:00.000Z"
        }
        
        updated_task_response = {
            "id": "task_created_123",
            "title": "Updated Integration Test Task",
            "notes": "This task has been updated.",
            "status": "completed",
            "completed": "2025-01-15T12:00:00.000Z",
            "updated": "2025-01-15T12:00:00.000Z"
        }
        
        mock_service.tasks.return_value.insert.return_value.execute.return_value = created_task_response
        mock_service.tasks.return_value.get.return_value.execute.return_value = sample_task_response
        mock_service.tasks.return_value.update.return_value.execute.return_value = updated_task_response
        
        # Test: Create task
        created_task = Task.create_task(
            title="Integration Test Task",
            task_list_id="@default",
            notes="This is a test task for integration testing.",
            due=date(2025, 1, 20)
        )
        
        assert created_task.id == "task_created_123"
        assert created_task.title == "Integration Test Task"
        assert created_task.notes == "This is a test task for integration testing."
        mock_service.tasks.return_value.insert.assert_called_once()
        
        # Test: Get task
        retrieved_task = Task.get_task("@default", "task_123")
        assert retrieved_task.id == "task_123"
        assert retrieved_task.title == "Sample Task"
        mock_service.tasks.return_value.get.assert_called()
        
        # Test: Update task
        result = retrieved_task.update_task(
            title="Updated Integration Test Task",
            notes="This task has been updated.",
            status="completed"
        )
        assert result.title == "Updated Integration Test Task"
        assert result.notes == "This task has been updated."
        assert result.status == "completed"
        mock_service.tasks.return_value.update.assert_called()
        
        # Test: Delete task
        result = retrieved_task.delete_task()
        assert result is True
        mock_service.tasks.return_value.delete.assert_called_once()
    
    def test_task_list_management_workflow(self, mock_get_tasks_service, mock_tasks_service):
        """Test complete task list management workflow."""
        # Setup mock service using fixture
        mock_service = mock_tasks_service
        
        # Mock responses
        created_list_response = {
            "id": "list_new_123",
            "title": "Integration Test List",
            "updated": "2025-01-15T10:00:00.000Z"
        }
        
        updated_list_response = {
            "id": "list_new_123",
            "title": "Updated Integration Test List",
            "updated": "2025-01-15T11:00:00.000Z"
        }
        
        lists_response = {
            "items": [
                {"id": "@default", "title": "My Tasks", "updated": "2025-01-15T09:00:00.000Z"},
                {"id": "list_new_123", "title": "Updated Integration Test List", "updated": "2025-01-15T11:00:00.000Z"}
            ]
        }
        
        mock_service.tasklists.return_value.insert.return_value.execute.return_value = created_list_response
        mock_service.tasklists.return_value.update.return_value.execute.return_value = updated_list_response
        mock_service.tasklists.return_value.list.return_value.execute.return_value = lists_response
        
        # Test: Create task list
        new_list = TaskList.create_task_list("Integration Test List")
        assert new_list.id == "list_new_123"
        assert new_list.title == "Integration Test List"
        mock_service.tasklists.return_value.insert.assert_called_once()
        
        # Test: Update task list
        updated_list = new_list.update_task_list("Updated Integration Test List")
        assert updated_list.title == "Updated Integration Test List"
        mock_service.tasklists.return_value.update.assert_called_once()
        
        # Test: List task lists
        lists = TaskList.list_task_lists()
        assert len(lists) == 2
        assert any(task_list.id == "list_new_123" for task_list in lists)
        mock_service.tasklists.return_value.list.assert_called_once()
        
        # Test: Delete task list
        result = updated_list.delete_task_list()
        assert result is True
        mock_service.tasklists.return_value.delete.assert_called_once()
    
    def test_task_query_and_filtering_workflow(self, mock_get_tasks_service, mock_tasks_service, sample_task_response):
        """Test complex task search and filtering workflow."""
        # Setup mock service using fixture
        mock_service = mock_tasks_service
        
        # Mock task list response
        tasks_response = {
            "items": [
                {
                    "id": "task_123",
                    "title": "Overdue Task",
                    "status": "needsAction",
                    "due": "2025-01-10T00:00:00.000Z",
                    "updated": "2025-01-10T10:00:00.000Z"
                },
                {
                    "id": "task_456",
                    "title": "Completed Task",
                    "status": "completed",
                    "completed": "2025-01-14T12:00:00.000Z",
                    "updated": "2025-01-14T12:00:00.000Z"
                },
                {
                    "id": "task_789",
                    "title": "Future Task",
                    "status": "needsAction",
                    "due": "2025-01-25T00:00:00.000Z",
                    "updated": "2025-01-15T08:00:00.000Z"
                }
            ]
        }
        
        mock_service.tasks.return_value.list.return_value.execute.return_value = tasks_response
        
        # Test: Basic task listing
        tasks = Task.list_tasks("@default", max_results=50)
        assert len(tasks) == 3
        mock_service.tasks.return_value.list.assert_called_once_with(
            tasklist='@default',
            maxResults=50
        )
        
        # Reset mock for query builder test
        mock_service.reset_mock()
        mock_service.tasks.return_value.list.return_value.execute.return_value = tasks_response
        
        # Test: Query builder with filters
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        filtered_tasks = (Task.query()
                         .limit(25)
                         .show_completed(True)
                         .completed_after(yesterday)
                         .in_task_list("@default")
                         .execute())
        
        assert len(filtered_tasks) == 3
        mock_service.tasks.return_value.list.assert_called_once()
        list_call_args = mock_service.tasks.return_value.list.call_args
        assert list_call_args[1]['maxResults'] == 25
        assert list_call_args[1]['showCompleted'] is True
        assert 'completedMin' in list_call_args[1]
        assert list_call_args[1]['tasklist'] == '@default'
        
        # Test: Convenience query methods
        mock_service.reset_mock()
        mock_service.tasks.return_value.list.return_value.execute.return_value = {"items": []}
        
        overdue_tasks = Task.query().overdue().execute()
        assert len(overdue_tasks) == 0
        mock_service.tasks.return_value.list.assert_called_once()
        overdue_call_args = mock_service.tasks.return_value.list.call_args
        assert overdue_call_args[1]['showCompleted'] is False
        assert 'dueMax' in overdue_call_args[1]
    
    def test_task_operations_workflow(self, mock_get_tasks_service, mock_tasks_service, sample_task_response):
        """Test various task operations workflow."""
        # Setup mock service using fixture
        mock_service = mock_tasks_service
        
        # Mock responses for task operations
        completed_task_response = {
            "id": "task_123",
            "title": "Sample Task",
            "notes": "This is a sample task for testing",
            "status": "completed",
            "due": "2025-01-20T00:00:00.000Z",
            "completed": "2025-01-15T12:00:00.000Z",
            "updated": "2025-01-15T12:00:00.000Z"
        }
        
        moved_task_response = {
            "id": "task_123",
            "title": "Sample Task",
            "notes": "This is a sample task for testing",
            "status": "completed",  # Preserve completed status after move
            "due": "2025-01-20T00:00:00.000Z",
            "completed": "2025-01-15T12:00:00.000Z",
            "parent": "parent_task_456",
            "position": "new_position_123",
            "updated": "2025-01-15T13:00:00.000Z"
        }
        
        mock_service.tasks.return_value.get.return_value.execute.return_value = sample_task_response
        mock_service.tasks.return_value.update.return_value.execute.return_value = completed_task_response
        mock_service.tasks.return_value.move.return_value.execute.return_value = moved_task_response
        
        # Test: Get task and mark as completed
        task = Task.get_task("@default", "task_123")
        assert task.id == "task_123"
        assert task.title == "Sample Task"
        assert task.status == "needsAction"
        
        # Test: Mark task as completed
        completed_task = task.mark_completed()
        assert completed_task.status == "completed"
        mock_service.tasks.return_value.update.assert_called_once()
        
        # Test: Move task - use completed_task instead of original task
        moved_task = completed_task.move_task(parent="parent_task_456", previous="prev_task_789")
        assert moved_task.parent == "parent_task_456"
        mock_service.tasks.return_value.move.assert_called_once_with(
            tasklist='@default',
            task='task_123',
            parent='parent_task_456',
            previous='prev_task_789'
        )
        
        # Test utility methods on the moved task (which should still be completed)
        assert moved_task.is_completed(), f"Expected moved task to still be completed, but status is: {moved_task.status}"
        # A completed task should not be overdue regardless of due date
        assert not moved_task.is_overdue(), "Completed task should not be overdue"
    
    def test_bulk_operations_workflow(self, mock_get_tasks_service, mock_tasks_service):
        """Test bulk task operations workflow."""
        # Setup mock service using fixture
        mock_service = mock_tasks_service
        
        # Mock responses for bulk operations
        tasks_to_create = [
            {
                "title": "Bulk Task 1",
                "notes": "This is bulk task 1",
                "due": date(2025, 1, 20)
            },
            {
                "title": "Bulk Task 2", 
                "notes": "This is bulk task 2",
                "due": date(2025, 1, 21)
            },
            {
                "title": "Bulk Task 3",
                "notes": "This is bulk task 3",
                "due": date(2025, 1, 22)
            }
        ]
        
        created_responses = [
            {
                "id": f"task_bulk_{i}",
                "title": task_data["title"],
                "notes": task_data["notes"],
                "status": "needsAction",
                "updated": "2025-01-15T10:00:00.000Z"
            }
            for i, task_data in enumerate(tasks_to_create, 1)
        ]
        
        mock_service.tasks.return_value.insert.return_value.execute.side_effect = created_responses
        
        # Test: Bulk create tasks
        created_tasks = []
        for task_data in tasks_to_create:
            task = Task.create_task(
                title=task_data["title"],
                notes=task_data["notes"],
                due=task_data["due"],
                task_list_id="@default"
            )
            created_tasks.append(task)
        
        assert len(created_tasks) == 3
        assert all(task.id.startswith("task_bulk_") for task in created_tasks)
        assert mock_service.tasks.return_value.insert.call_count == 3
        
        # Test: Batch operations using list comprehension
        # This simulates how users might perform bulk operations
        task_titles = [task.title for task in created_tasks]
        assert "Bulk Task 1" in task_titles
        assert "Bulk Task 2" in task_titles
        assert "Bulk Task 3" in task_titles


@pytest.mark.integration  
@pytest.mark.tasks
@pytest.mark.asyncio
class TestAsyncTasksIntegration:
    """Async integration tests for Tasks functionality with mocked API calls."""
    
    async def test_async_end_to_end_task_lifecycle(self, mock_get_async_tasks_service, mock_async_tasks_context, sample_task_response):
        """Test complete async task lifecycle: create, read, update, complete, delete."""
        # Setup mock async context manager using fixture
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Mock responses
        created_task_response = {
            "id": "task_async_123",
            "title": "Async Integration Test Task",
            "notes": "This is an async test task for integration testing.",
            "status": "needsAction",
            "updated": "2025-01-15T10:00:00.000Z"
        }
        
        updated_task_response = {
            "id": "task_async_123",
            "title": "Updated Async Integration Test Task",
            "notes": "This async task has been updated.",
            "status": "completed",
            "completed": "2025-01-15T12:00:00.000Z",
            "updated": "2025-01-15T12:00:00.000Z"
        }
        
        # Set up sequential responses for aiogoogle.as_service_account calls
        mock_aiogoogle.as_service_account.side_effect = [
            created_task_response,  # create_task
            sample_task_response,   # get_task
            updated_task_response,  # update_task
            updated_task_response,  # mark_completed (update)
            None                    # delete_task
        ]
        
        # Test: Create task
        created_task = await AsyncTask.create_task(
            title="Async Integration Test Task",
            task_list_id="@default",
            notes="This is an async test task for integration testing.",
            due=date(2025, 1, 20)
        )
        
        assert created_task.id == "task_async_123"
        assert created_task.title == "Async Integration Test Task"
        assert created_task.notes == "This is an async test task for integration testing."
        
        # Test: Get task
        retrieved_task = await AsyncTask.get_task("@default", "task_123")
        assert retrieved_task.id == "task_123"
        assert retrieved_task.title == "Sample Task"
        
        # Test: Update task
        result = await retrieved_task.update_task(
            title="Updated Async Integration Test Task",
            notes="This async task has been updated.",
            status="completed"
        )
        assert result.title == "Updated Async Integration Test Task"
        assert result.notes == "This async task has been updated."
        assert result.status == "completed"
        
        # Test: Mark as completed (additional update call)
        result = await retrieved_task.mark_completed()
        assert result.status == "completed"
        
        # Test: Delete task
        result = await retrieved_task.delete_task()
        assert result is True
        
        # Verify all API calls were made
        assert mock_aiogoogle.as_service_account.call_count == 5
    
    async def test_async_task_list_management_workflow(self, mock_get_async_tasks_service, mock_async_tasks_context):
        """Test complete async task list management workflow."""
        # Setup mock async context manager using fixture
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Mock responses
        created_list_response = {
            "id": "list_async_123",
            "title": "Async Integration Test List",
            "updated": "2025-01-15T10:00:00.000Z"
        }
        
        updated_list_response = {
            "id": "list_async_123",
            "title": "Updated Async Integration Test List",
            "updated": "2025-01-15T11:00:00.000Z"
        }
        
        lists_response = {
            "items": [
                {"id": "@default", "title": "My Tasks", "updated": "2025-01-15T09:00:00.000Z"},
                {"id": "list_async_123", "title": "Updated Async Integration Test List", "updated": "2025-01-15T11:00:00.000Z"}
            ]
        }
        
        mock_aiogoogle.as_service_account.side_effect = [
            created_list_response,  # create_task_list
            updated_list_response,  # update_task_list
            lists_response,         # list_task_lists
            None                    # delete_task_list
        ]
        
        # Test: Create task list
        new_list = await AsyncTaskList.create_task_list("Async Integration Test List")
        assert new_list.id == "list_async_123"
        assert new_list.title == "Async Integration Test List"
        
        # Test: Update task list
        updated_list = await new_list.update_task_list("Updated Async Integration Test List")
        assert updated_list.title == "Updated Async Integration Test List"
        
        # Test: List task lists
        lists = await AsyncTaskList.list_task_lists()
        assert len(lists) == 2
        assert any(task_list.id == "list_async_123" for task_list in lists)
        
        # Test: Delete task list
        result = await updated_list.delete_task_list()
        assert result is True
        
        # Verify all API calls were made
        assert mock_aiogoogle.as_service_account.call_count == 4
    
    async def test_async_bulk_operations_workflow(self, mock_get_async_tasks_service, mock_async_tasks_context):
        """Test async bulk operations workflow."""
        # Setup mock async context manager using fixture
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Test concurrent task creation using asyncio.gather
        tasks_to_create = [
            {"title": "Async Bulk Task 1", "notes": "Async bulk task 1"},
            {"title": "Async Bulk Task 2", "notes": "Async bulk task 2"},
            {"title": "Async Bulk Task 3", "notes": "Async bulk task 3"}
        ]
        
        created_responses = [
            {
                "id": f"task_async_bulk_{i}",
                "title": task_data["title"],
                "notes": task_data["notes"],
                "status": "needsAction",
                "updated": "2025-01-15T10:00:00.000Z"
            }
            for i, task_data in enumerate(tasks_to_create, 1)
        ]
        
        mock_aiogoogle.as_service_account.side_effect = created_responses
        
        # Test: Concurrent task creation
        async def create_task_async(task_data):
            return await AsyncTask.create_task(
                title=task_data["title"],
                notes=task_data["notes"],
                task_list_id="@default"
            )
        
        created_tasks = await asyncio.gather(*[
            create_task_async(task_data) for task_data in tasks_to_create
        ])
        
        assert len(created_tasks) == 3
        assert all(task.id.startswith("task_async_bulk_") for task in created_tasks)
        assert mock_aiogoogle.as_service_account.call_count == 3
        
        # Test: Async batch operations
        task_titles = [task.title for task in created_tasks]
        assert "Async Bulk Task 1" in task_titles
        assert "Async Bulk Task 2" in task_titles
        assert "Async Bulk Task 3" in task_titles
    
    async def test_async_query_builder_workflow(self, mock_get_async_tasks_service, mock_async_tasks_context, sample_task_response):
        """Test async query builder workflow."""
        # Setup mock async context manager using fixture
        mock_aiogoogle, mock_service = mock_async_tasks_context
        mock_get_async_tasks_service.return_value.__aenter__.return_value = mock_async_tasks_context
        
        # Mock task list response for query
        tasks_response = {
            "items": [
                {
                    "id": "task_async_query_1",
                    "title": "Urgent Task",
                    "status": "needsAction",
                    "due": "2025-01-16T00:00:00.000Z",
                    "updated": "2025-01-15T08:00:00.000Z"
                },
                {
                    "id": "task_async_query_2",
                    "title": "Completed Task",
                    "status": "completed",
                    "completed": "2025-01-14T12:00:00.000Z",
                    "updated": "2025-01-14T12:00:00.000Z"
                }
            ]
        }
        
        mock_aiogoogle.as_service_account.return_value = tasks_response
        
        # Test: Complex async query
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        
        filtered_tasks = await (AsyncTask.query()
                               .limit(20)
                               .show_completed(True)
                               .due_before(tomorrow)
                               .in_task_list("@default")
                               .execute())
        
        assert len(filtered_tasks) == 2
        
        # Verify the correct API call was made
        assert mock_aiogoogle.as_service_account.call_count == 1
        
        # Test utility methods
        mock_aiogoogle.reset_mock()
        mock_aiogoogle.as_service_account.side_effect = [
            {"items": [tasks_response["items"][0]]},  # first() query
            {"items": []}                             # exists() query (no results)
        ]
        
        first_task = await (AsyncTask.query()
                           .due_tomorrow()
                           .first())
        
        assert first_task.id == "task_async_query_1"
        
        exists_result = await (AsyncTask.query()
                              .overdue()
                              .exists())
        
        assert exists_result is False
        assert mock_aiogoogle.as_service_account.call_count == 2


@pytest.fixture
def sample_task_response():
    """Sample Google Tasks API task response for integration tests."""
    return {
        "id": "task_123",
        "title": "Sample Task",
        "notes": "This is a sample task for testing",
        "status": "needsAction",
        "due": "2025-01-20T00:00:00.000Z",
        "updated": "2025-01-15T10:00:00.000Z"
    }