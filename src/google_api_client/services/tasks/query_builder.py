from datetime import datetime, date, timedelta
from typing import Optional, List, TYPE_CHECKING
import logging
from .constants import MAX_RESULTS_LIMIT, DEFAULT_MAX_RESULTS, DEFAULT_TASK_LIST_ID

if TYPE_CHECKING:
    from .types import Task
    from .api_service import TasksApiService

logger = logging.getLogger(__name__)


class TaskQueryBuilder:
    """
    Builder pattern for constructing Google Tasks queries with a fluent API.
    Provides a clean, readable way to build complex task queries.
    
    Example usage:
        tasks = (Task.query()
            .limit(50)
            .due_before(end_date)
            .completed_after(start_date)
            .show_completed(True)
            .execute())
    """
    
    def __init__(self, api_service: "TasksApiService"):
        self._api_service = api_service
        self._max_results: Optional[int] = DEFAULT_MAX_RESULTS
        self._completed_max: Optional[datetime] = None
        self._completed_min: Optional[datetime] = None
        self._due_max: Optional[datetime] = None
        self._due_min: Optional[datetime] = None
        self._show_completed: Optional[bool] = None
        self._show_hidden: Optional[bool] = None
        self._task_list_id: str = DEFAULT_TASK_LIST_ID
        
    def limit(self, count: int) -> "TaskQueryBuilder":
        """
        Set the maximum number of tasks to retrieve.
        Args:
            count: Maximum number of tasks (1-100)
        Returns:
            Self for method chaining
        """
        if count < 1 or count > MAX_RESULTS_LIMIT:
            raise ValueError(f"Limit must be between 1 and {MAX_RESULTS_LIMIT}")
        self._max_results = count
        return self
        
    def completed_after(self, min_date: datetime) -> "TaskQueryBuilder":
        """
        Filter tasks completed after the specified date.
        Args:
            min_date: Minimum completion date (RFC 3339 timestamp)
        Returns:
            Self for method chaining
        """
        self._completed_min = min_date
        return self
        
    def completed_before(self, max_date: datetime) -> "TaskQueryBuilder":
        """
        Filter tasks completed before the specified date.
        Args:
            max_date: Maximum completion date (RFC 3339 timestamp)
        Returns:
            Self for method chaining
        """
        self._completed_max = max_date
        return self
        
    def completed_in_range(self, min_date: datetime, max_date: datetime) -> "TaskQueryBuilder":
        """
        Filter tasks completed within the specified date range.
        Args:
            min_date: Minimum completion date
            max_date: Maximum completion date
        Returns:
            Self for method chaining
        """
        if min_date >= max_date:
            raise ValueError("Start date must be before end date")
        self._completed_min = min_date
        self._completed_max = max_date
        return self
        
    def due_after(self, min_date: datetime) -> "TaskQueryBuilder":
        """
        Filter tasks due after the specified date.
        Args:
            min_date: Minimum due date (RFC 3339 timestamp)
        Returns:
            Self for method chaining
        """
        self._due_min = min_date
        return self
        
    def due_before(self, max_date: datetime) -> "TaskQueryBuilder":
        """
        Filter tasks due before the specified date.
        Args:
            max_date: Maximum due date (RFC 3339 timestamp)
        Returns:
            Self for method chaining
        """
        self._due_max = max_date
        return self
        
    def due_in_range(self, min_date: datetime, max_date: datetime) -> "TaskQueryBuilder":
        """
        Filter tasks due within the specified date range.
        Args:
            min_date: Minimum due date
            max_date: Maximum due date
        Returns:
            Self for method chaining
        """
        if min_date >= max_date:
            raise ValueError("Start date must be before end date")
        self._due_min = min_date
        self._due_max = max_date
        return self
        
    def show_completed(self, show: bool = True) -> "TaskQueryBuilder":
        """
        Include or exclude completed tasks in results.
        Args:
            show: Whether to include completed tasks
        Returns:
            Self for method chaining
        """
        self._show_completed = show
        return self
        
    def show_hidden(self, show: bool = True) -> "TaskQueryBuilder":
        """
        Include or exclude hidden tasks in results.
        Args:
            show: Whether to include hidden tasks
        Returns:
            Self for method chaining
        """
        self._show_hidden = show
        return self
        
    def in_task_list(self, task_list_id: str) -> "TaskQueryBuilder":
        """
        Specify which task list to query.
        Args:
            task_list_id: Task list identifier
        Returns:
            Self for method chaining
        """
        self._task_list_id = task_list_id
        return self
        
    # Convenience date methods
    def due_today(self) -> "TaskQueryBuilder":
        """
        Filter to tasks due today.
        Returns:
            Self for method chaining
        """
        today = date.today()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = start_of_day + timedelta(days=1)
        return self.due_in_range(start_of_day, end_of_day)
        
    def due_tomorrow(self) -> "TaskQueryBuilder":
        """
        Filter to tasks due tomorrow.
        Returns:
            Self for method chaining
        """
        tomorrow = date.today() + timedelta(days=1)
        start_of_day = datetime.combine(tomorrow, datetime.min.time())
        end_of_day = start_of_day + timedelta(days=1)
        return self.due_in_range(start_of_day, end_of_day)
        
    def due_this_week(self) -> "TaskQueryBuilder":
        """
        Filter to tasks due this week (Monday to Sunday).
        Returns:
            Self for method chaining
        """
        today = date.today()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        sunday = monday + timedelta(days=6)
        
        start_of_week = datetime.combine(monday, datetime.min.time())
        end_of_week = datetime.combine(sunday, datetime.max.time())
        return self.due_in_range(start_of_week, end_of_week)
        
    def due_next_week(self) -> "TaskQueryBuilder":
        """
        Filter to tasks due next week (Monday to Sunday).
        Returns:
            Self for method chaining
        """
        today = date.today()
        days_since_monday = today.weekday()
        next_monday = today + timedelta(days=(7 - days_since_monday))
        next_sunday = next_monday + timedelta(days=6)
        
        start_of_week = datetime.combine(next_monday, datetime.min.time())
        end_of_week = datetime.combine(next_sunday, datetime.max.time())
        return self.due_in_range(start_of_week, end_of_week)
        
    def due_next_days(self, days: int) -> "TaskQueryBuilder":
        """
        Filter to tasks due in the next N days.
        Args:
            days: Number of days from today
        Returns:
            Self for method chaining
        """
        if days < 1:
            raise ValueError("Days must be positive")
            
        today = date.today()
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today + timedelta(days=days + 1), datetime.min.time())
        return self.due_in_range(start, end)
        
    def overdue(self) -> "TaskQueryBuilder":
        """
        Filter to tasks that are overdue (due date in the past and not completed).
        Returns:
            Self for method chaining
        """
        today = datetime.combine(date.today(), datetime.min.time())
        return self.due_before(today).show_completed(False)
        
    def completed_today(self) -> "TaskQueryBuilder":
        """
        Filter to tasks completed today.
        Returns:
            Self for method chaining
        """
        today = date.today()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = start_of_day + timedelta(days=1)
        return self.completed_in_range(start_of_day, end_of_day)
        
    def completed_this_week(self) -> "TaskQueryBuilder":
        """
        Filter to tasks completed this week (Monday to Sunday).
        Returns:
            Self for method chaining
        """
        today = date.today()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        sunday = monday + timedelta(days=6)
        
        start_of_week = datetime.combine(monday, datetime.min.time())
        end_of_week = datetime.combine(sunday, datetime.max.time())
        return self.completed_in_range(start_of_week, end_of_week)
        
    def completed_last_days(self, days: int) -> "TaskQueryBuilder":
        """
        Filter to tasks completed in the last N days.
        Args:
            days: Number of days back to search
        Returns:
            Self for method chaining
        """
        if days < 1:
            raise ValueError("Days must be positive")
            
        today = date.today()
        start = datetime.combine(today - timedelta(days=days), datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
        return self.completed_in_range(start, end)
        
    def execute(self) -> List["Task"]:
        """
        Execute the query and return the results.
        Returns:
            List of Task objects matching the criteria
        Raises:
            ValueError: If query parameters are invalid
        """
        logger.info("Executing task query with builder")
        
        # Use the service layer implementation
        tasks = self._api_service.list_tasks(
            task_list_id=self._task_list_id,
            max_results=self._max_results,
            completed_min=self._completed_min,
            completed_max=self._completed_max,
            due_min=self._due_min,
            due_max=self._due_max,
            show_completed=self._show_completed,
            show_hidden=self._show_hidden
        )
        
        logger.info("Builder query returned %d tasks", len(tasks))
        return tasks
        
    def count(self) -> int:
        """
        Execute the query and return only the count of matching tasks.
        Returns:
            Number of tasks matching the criteria
        """
        return len(self.execute())
        
    def first(self) -> Optional["Task"]:
        """
        Execute the query and return only the first matching task.
        Returns:
            First Task or None if no matches
        """
        tasks = self.limit(1).execute()
        return tasks[0] if tasks else None
        
    def exists(self) -> bool:
        """
        Check if any tasks match the criteria without retrieving them.
        Returns:
            True if at least one task matches, False otherwise
        """
        return self.limit(1).count() > 0
        
    def __repr__(self):
        return f"TaskQueryBuilder(task_list_id='{self._task_list_id}', limit={self._max_results})"