import pytest
import asyncio
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, AsyncMock
from src.google_api_client.clients.tasks.async_query_builder import AsyncTaskQueryBuilder
from src.google_api_client.clients.tasks.async_client import AsyncTask


@pytest.mark.unit
@pytest.mark.tasks
class TestAsyncTaskQueryBuilder:
    """Test cases for the AsyncTaskQueryBuilder class."""
    
    def test_query_builder_initialization(self):
        """Test async query builder initialization."""
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        assert builder._async_task_class == mock_task_class
        assert builder._max_results == 100  # DEFAULT_MAX_RESULTS
        assert builder._task_list_id == '@default'
        assert builder._completed_max is None
        assert builder._completed_min is None
        assert builder._due_max is None
        assert builder._due_min is None
        assert builder._show_completed is None
        assert builder._show_hidden is None
    
    def test_limit(self):
        """Test setting result limit."""
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        result = builder.limit(50)
        assert result is builder  # Method chaining
        assert builder._max_results == 50
    
    def test_limit_validation(self):
        """Test limit validation."""
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        # Invalid limits
        with pytest.raises(ValueError, match="Limit must be between 1 and"):
            builder.limit(0)
        
        with pytest.raises(ValueError, match="Limit must be between 1 and"):
            builder.limit(101)
        
        # Valid limits
        builder.limit(1)
        assert builder._max_results == 1
        
        builder.limit(100)
        assert builder._max_results == 100
    
    def test_completed_after(self):
        """Test filtering by completion after date."""
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        min_date = datetime(2025, 1, 15, 10, 0, 0)
        result = builder.completed_after(min_date)
        
        assert result is builder
        assert builder._completed_min == min_date
    
    def test_completed_before(self):
        """Test filtering by completion before date."""
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        max_date = datetime(2025, 1, 20, 18, 0, 0)
        result = builder.completed_before(max_date)
        
        assert result is builder
        assert builder._completed_max == max_date
    
    def test_completed_in_range(self):
        """Test filtering by completion date range."""
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        min_date = datetime(2025, 1, 15, 10, 0, 0)
        max_date = datetime(2025, 1, 20, 18, 0, 0)
        result = builder.completed_in_range(min_date, max_date)
        
        assert result is builder
        assert builder._completed_min == min_date
        assert builder._completed_max == max_date
    
    def test_completed_in_range_validation(self):
        """Test validation for completion date range."""
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        min_date = datetime(2025, 1, 20, 10, 0, 0)
        max_date = datetime(2025, 1, 15, 18, 0, 0)  # Before min_date
        
        with pytest.raises(ValueError, match="Start date must be before end date"):
            builder.completed_in_range(min_date, max_date)
    
    def test_due_after(self):
        """Test filtering by due after date."""
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        min_date = datetime(2025, 1, 15, 10, 0, 0)
        result = builder.due_after(min_date)
        
        assert result is builder
        assert builder._due_min == min_date
    
    def test_due_before(self):
        """Test filtering by due before date."""
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        max_date = datetime(2025, 1, 20, 18, 0, 0)
        result = builder.due_before(max_date)
        
        assert result is builder
        assert builder._due_max == max_date
    
    def test_due_in_range(self):
        """Test filtering by due date range."""
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        min_date = datetime(2025, 1, 15, 10, 0, 0)
        max_date = datetime(2025, 1, 20, 18, 0, 0)
        result = builder.due_in_range(min_date, max_date)
        
        assert result is builder
        assert builder._due_min == min_date
        assert builder._due_max == max_date
    
    def test_due_in_range_validation(self):
        """Test validation for due date range."""
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        min_date = datetime(2025, 1, 20, 10, 0, 0)
        max_date = datetime(2025, 1, 15, 18, 0, 0)  # Before min_date
        
        with pytest.raises(ValueError, match="Start date must be before end date"):
            builder.due_in_range(min_date, max_date)
    
    def test_show_completed(self):
        """Test show completed flag."""
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        result = builder.show_completed(True)
        assert result is builder
        assert builder._show_completed is True
        
        result = builder.show_completed(False)
        assert result is builder
        assert builder._show_completed is False
        
        # Test default value
        builder = AsyncTaskQueryBuilder(mock_task_class)
        result = builder.show_completed()
        assert result is builder
        assert builder._show_completed is True
    
    def test_show_hidden(self):
        """Test show hidden flag."""
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        result = builder.show_hidden(True)
        assert result is builder
        assert builder._show_hidden is True
        
        result = builder.show_hidden(False)
        assert result is builder
        assert builder._show_hidden is False
        
        # Test default value
        builder = AsyncTaskQueryBuilder(mock_task_class)
        result = builder.show_hidden()
        assert result is builder
        assert builder._show_hidden is True
    
    def test_in_task_list(self):
        """Test setting task list ID."""
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        result = builder.in_task_list("custom_list_123")
        assert result is builder
        assert builder._task_list_id == "custom_list_123"
    
    @patch('src.google_api_client.clients.tasks.async_query_builder.date')
    def test_due_today(self, mock_date):
        """Test filtering by due today."""
        mock_date.today.return_value = date(2025, 1, 15)
        
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        result = builder.due_today()
        assert result is builder
        
        # Check that due range was set to today
        expected_start = datetime(2025, 1, 15, 0, 0, 0)
        expected_end = datetime(2025, 1, 16, 0, 0, 0)
        
        assert builder._due_min == expected_start
        assert builder._due_max == expected_end
    
    @patch('src.google_api_client.clients.tasks.async_query_builder.date')
    def test_due_tomorrow(self, mock_date):
        """Test filtering by due tomorrow."""
        mock_date.today.return_value = date(2025, 1, 15)
        
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        result = builder.due_tomorrow()
        assert result is builder
        
        # Check that due range was set to tomorrow
        expected_start = datetime(2025, 1, 16, 0, 0, 0)
        expected_end = datetime(2025, 1, 17, 0, 0, 0)
        
        assert builder._due_min == expected_start
        assert builder._due_max == expected_end
    
    @patch('src.google_api_client.clients.tasks.async_query_builder.date')
    def test_due_this_week(self, mock_date):
        """Test filtering by due this week."""
        # Wednesday, Jan 15, 2025
        mock_date.today.return_value = date(2025, 1, 15)
        
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        result = builder.due_this_week()
        assert result is builder
        
        # Monday Jan 13 to Sunday Jan 19
        expected_start = datetime(2025, 1, 13, 0, 0, 0)  # Monday
        expected_end = datetime(2025, 1, 19, 23, 59, 59, 999999)  # Sunday
        
        assert builder._due_min == expected_start
        assert builder._due_max == expected_end
    
    @patch('src.google_api_client.clients.tasks.async_query_builder.date')
    def test_due_next_week(self, mock_date):
        """Test filtering by due next week."""
        # Wednesday, Jan 15, 2025
        mock_date.today.return_value = date(2025, 1, 15)
        
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        result = builder.due_next_week()
        assert result is builder
        
        # Monday Jan 20 to Sunday Jan 26
        expected_start = datetime(2025, 1, 20, 0, 0, 0)  # Next Monday
        expected_end = datetime(2025, 1, 26, 23, 59, 59, 999999)  # Next Sunday
        
        assert builder._due_min == expected_start
        assert builder._due_max == expected_end
    
    @patch('src.google_api_client.clients.tasks.async_query_builder.date')
    def test_due_next_days(self, mock_date):
        """Test filtering by due in next N days."""
        mock_date.today.return_value = date(2025, 1, 15)
        
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        result = builder.due_next_days(7)
        assert result is builder
        
        # Today to 7 days from today
        expected_start = datetime(2025, 1, 15, 0, 0, 0)
        expected_end = datetime(2025, 1, 23, 0, 0, 0)
        
        assert builder._due_min == expected_start
        assert builder._due_max == expected_end
    
    def test_due_next_days_validation(self):
        """Test validation for due next days."""
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        with pytest.raises(ValueError, match="Days must be positive"):
            builder.due_next_days(0)
        
        with pytest.raises(ValueError, match="Days must be positive"):
            builder.due_next_days(-1)
    
    @patch('src.google_api_client.clients.tasks.async_query_builder.date')
    def test_overdue(self, mock_date):
        """Test filtering by overdue tasks."""
        mock_date.today.return_value = date(2025, 1, 15)
        
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        result = builder.overdue()
        assert result is builder
        
        # Due before end of yesterday and not completed
        expected_max = datetime(2025, 1, 15, 0, 0, 0)  # End of yesterday
        
        assert builder._due_max == expected_max
        assert builder._show_completed is False
    
    @patch('src.google_api_client.clients.tasks.async_query_builder.date')
    def test_completed_today(self, mock_date):
        """Test filtering by completed today."""
        mock_date.today.return_value = date(2025, 1, 15)
        
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        result = builder.completed_today()
        assert result is builder
        
        # Check that completed range was set to today
        expected_start = datetime(2025, 1, 15, 0, 0, 0)
        expected_end = datetime(2025, 1, 16, 0, 0, 0)
        
        assert builder._completed_min == expected_start
        assert builder._completed_max == expected_end
    
    @patch('src.google_api_client.clients.tasks.async_query_builder.date')
    def test_completed_this_week(self, mock_date):
        """Test filtering by completed this week."""
        # Wednesday, Jan 15, 2025
        mock_date.today.return_value = date(2025, 1, 15)
        
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        result = builder.completed_this_week()
        assert result is builder
        
        # Monday Jan 13 to Sunday Jan 19
        expected_start = datetime(2025, 1, 13, 0, 0, 0)  # Monday
        expected_end = datetime(2025, 1, 19, 23, 59, 59, 999999)  # Sunday
        
        assert builder._completed_min == expected_start
        assert builder._completed_max == expected_end
    
    @patch('src.google_api_client.clients.tasks.async_query_builder.date')
    def test_completed_last_days(self, mock_date):
        """Test filtering by completed in last N days."""
        mock_date.today.return_value = date(2025, 1, 15)
        
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        result = builder.completed_last_days(7)
        assert result is builder
        
        # 7 days ago to today
        expected_start = datetime(2025, 1, 8, 0, 0, 0)
        expected_end = datetime(2025, 1, 15, 23, 59, 59, 999999)
        
        assert builder._completed_min == expected_start
        assert builder._completed_max == expected_end
    
    def test_completed_last_days_validation(self):
        """Test validation for completed last days."""
        mock_task_class = Mock()
        builder = AsyncTaskQueryBuilder(mock_task_class)
        
        with pytest.raises(ValueError, match="Days must be positive"):
            builder.completed_last_days(0)
        
        with pytest.raises(ValueError, match="Days must be positive"):
            builder.completed_last_days(-1)
    
    @pytest.mark.asyncio
    async def test_execute(self):
        """Test executing the async query."""
        mock_task_class = Mock()
        mock_tasks = [Mock(), Mock(), Mock()]
        mock_task_class._list_tasks_with_filters = AsyncMock(return_value=mock_tasks)
        
        builder = AsyncTaskQueryBuilder(mock_task_class)
        builder.limit(50).show_completed(True).in_task_list("list_123")
        
        result = await builder.execute()
        
        assert result == mock_tasks
        
        # Verify the correct parameters were passed
        mock_task_class._list_tasks_with_filters.assert_called_once_with(
            tasklist='list_123',
            maxResults=50,
            showCompleted=True
        )
    
    @pytest.mark.asyncio
    async def test_execute_with_date_filters(self):
        """Test executing async query with date filters."""
        mock_task_class = Mock()
        mock_tasks = [Mock()]
        mock_task_class._list_tasks_with_filters = AsyncMock(return_value=mock_tasks)
        
        builder = AsyncTaskQueryBuilder(mock_task_class)
        completed_min = datetime(2025, 1, 10, 0, 0, 0)
        completed_max = datetime(2025, 1, 20, 23, 59, 59)
        due_min = datetime(2025, 1, 15, 0, 0, 0)
        due_max = datetime(2025, 1, 25, 23, 59, 59)
        
        builder.completed_in_range(completed_min, completed_max)
        builder.due_in_range(due_min, due_max)
        builder.show_hidden(False)
        
        result = await builder.execute()
        
        assert result == mock_tasks
        
        # Verify the correct parameters were passed
        expected_params = {
            'tasklist': '@default',
            'maxResults': 100,
            'completedMin': '2025-01-10T00:00:00Z',
            'completedMax': '2025-01-20T23:59:59Z',
            'dueMin': '2025-01-15T00:00:00Z',
            'dueMax': '2025-01-25T23:59:59Z',
            'showHidden': False
        }
        mock_task_class._list_tasks_with_filters.assert_called_once_with(**expected_params)
    
    @pytest.mark.asyncio
    async def test_count(self):
        """Test counting matching tasks."""
        mock_task_class = Mock()
        mock_tasks = [Mock(), Mock(), Mock()]
        mock_task_class._list_tasks_with_filters = AsyncMock(return_value=mock_tasks)
        
        builder = AsyncTaskQueryBuilder(mock_task_class)
        result = await builder.count()
        
        assert result == 3
    
    @pytest.mark.asyncio
    async def test_first(self):
        """Test getting first matching task."""
        mock_task_class = Mock()
        mock_tasks = [Mock(), Mock(), Mock()]
        mock_task_class._list_tasks_with_filters = AsyncMock(return_value=mock_tasks)
        
        builder = AsyncTaskQueryBuilder(mock_task_class)
        result = await builder.first()
        
        assert result == mock_tasks[0]
        
        # Verify limit was set to 1
        mock_task_class._list_tasks_with_filters.assert_called_once()
        call_args = mock_task_class._list_tasks_with_filters.call_args
        assert call_args[1]['maxResults'] == 1
    
    @pytest.mark.asyncio
    async def test_first_no_results(self):
        """Test getting first task when no results."""
        mock_task_class = Mock()
        mock_task_class._list_tasks_with_filters = AsyncMock(return_value=[])
        
        builder = AsyncTaskQueryBuilder(mock_task_class)
        result = await builder.first()
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_exists_true(self):
        """Test exists when tasks match."""
        mock_task_class = Mock()
        mock_tasks = [Mock()]
        mock_task_class._list_tasks_with_filters = AsyncMock(return_value=mock_tasks)
        
        builder = AsyncTaskQueryBuilder(mock_task_class)
        result = await builder.exists()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_exists_false(self):
        """Test exists when no tasks match."""
        mock_task_class = Mock()
        mock_task_class._list_tasks_with_filters = AsyncMock(return_value=[])
        
        builder = AsyncTaskQueryBuilder(mock_task_class)
        result = await builder.exists()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_method_chaining(self):
        """Test that all methods support chaining."""
        mock_task_class = Mock()
        mock_tasks = [Mock()]
        mock_task_class._list_tasks_with_filters = AsyncMock(return_value=mock_tasks)
        
        # Test complex chaining
        result = await (AsyncTaskQueryBuilder(mock_task_class)
                       .limit(25)
                       .show_completed(False)
                       .show_hidden(True)
                       .in_task_list("custom_list")
                       .due_next_days(7)
                       .completed_last_days(14)
                       .execute())
        
        assert result == mock_tasks
        
        # Verify all parameters were applied
        call_args = mock_task_class._list_tasks_with_filters.call_args[1]
        assert call_args['maxResults'] == 25
        assert call_args['showCompleted'] is False
        assert call_args['showHidden'] is True
        assert call_args['tasklist'] == 'custom_list'
        assert 'dueMin' in call_args
        assert 'dueMax' in call_args
        assert 'completedMin' in call_args
        assert 'completedMax' in call_args