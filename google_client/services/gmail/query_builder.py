from datetime import datetime, date, timedelta
from typing import Optional, List, TYPE_CHECKING

from ...utils.datetime import convert_datetime_to_local_timezone

if TYPE_CHECKING:
    from .api_service import EmailMessage
    from .types import EmailThread

# Constants (imported from gmail_client)
MAX_RESULTS_LIMIT = 2500
DEFAULT_MAX_RESULTS = 30


class EmailQueryBuilder:
    """
    Builder pattern for constructing Gmail queries with a fluent API.
    Provides a clean, readable way to build complex email queries.
    
    Example usage:
        emails = (EmailMessage.query()
            .limit(50)
            .from_sender("sender@example.com")
            .search("meeting")
            .with_attachments()
            .execute())
    """
    
    def __init__(self, api_service_class):
        self._api_service = api_service_class
        self._max_results: Optional[int] = DEFAULT_MAX_RESULTS
        self._query_parts: List[str] = []
        self._include_spam_trash: bool = False
        self._label_ids: List[str] = []
        
    def limit(self, count: int) -> "EmailQueryBuilder":
        """
        Set the maximum number of emails to retrieve.
        Args:
            count: Maximum number of emails (1-2500)
        Returns:
            Self for method chaining
        """
        if count < 1 or count > MAX_RESULTS_LIMIT:
            raise ValueError(f"Limit must be between 1 and {MAX_RESULTS_LIMIT}")
        self._max_results = count
        return self
        
    def search(self, query: str, exact_match: bool = False) -> "EmailQueryBuilder":
        """
        Add a search term to the query.
        Args:
            query: Search term to add
            exact_match: Boolean indicating whether to return exact matches only
        Returns:
            Self for method chaining
        """
        if query:
            if exact_match:
                query = f'"{query}"'
            self._query_parts.append(query)
        return self
        
    def from_sender(self, email: str) -> "EmailQueryBuilder":
        """
        Filter emails from a specific sender.
        Args:
            email: Sender email address
        Returns:
            Self for method chaining
        """
        if email:
            self._query_parts.append(f"from:{email}")
        return self
        
    def to_recipient(self, email: str) -> "EmailQueryBuilder":
        """
        Filter emails sent to a specific recipient.
        Args:
            email: Recipient email address
        Returns:
            Self for method chaining
        """
        if email:
            self._query_parts.append(f"to:{email}")
        return self
        
    def with_subject(self, subject: str) -> "EmailQueryBuilder":
        """
        Filter emails with specific subject content.
        Args:
            subject: Subject content to search for
        Returns:
            Self for method chaining
        """
        if subject:
            self._query_parts.append(f"subject:{subject}")
        return self
        
    def with_attachments(self) -> "EmailQueryBuilder":
        """
        Filter emails that have attachments.
        Returns:
            Self for method chaining
        """
        self._query_parts.append("has:attachment")
        return self
        
    def without_attachments(self) -> "EmailQueryBuilder":
        """
        Filter emails that don't have attachments.
        Returns:
            Self for method chaining
        """
        self._query_parts.append("-has:attachment")
        return self
        
    def is_read(self) -> "EmailQueryBuilder":
        """
        Filter emails that are read.
        Returns:
            Self for method chaining
        """
        self._query_parts.append("-is:unread")
        return self
        
    def is_unread(self) -> "EmailQueryBuilder":
        """
        Filter emails that are unread.
        Returns:
            Self for method chaining
        """
        self._query_parts.append("is:unread")
        return self
        
    def is_starred(self) -> "EmailQueryBuilder":
        """
        Filter emails that are starred.
        Returns:
            Self for method chaining
        """
        self._query_parts.append("is:starred")
        return self
        
    def is_important(self) -> "EmailQueryBuilder":
        """
        Filter emails that are marked as important.
        Returns:
            Self for method chaining
        """
        self._query_parts.append("is:important")
        return self
        
    def in_folder(self, folder: str) -> "EmailQueryBuilder":
        """
        Filter emails in a specific folder/label.
        Args:
            folder: Folder/label name (inbox, sent, drafts, trash, spam, etc.)
        Returns:
            Self for method chaining
        """
        if folder:
            self._query_parts.append(f"in:{folder}")
        return self

    def with_label(self, label: str) -> "EmailQueryBuilder":
        """
        Filter emails with a specific label.
        Args:
            label: Label name
        Returns:
            Self for method chaining
        """
        if label:
            self._query_parts.append(f"label:{label}")
        return self

    def without_label(self, label: str) -> "EmailQueryBuilder":
        """
        Filter emails without a specific label.
        Args:
            label: Label name
        Returns:
            Self for method chaining
        """
        if label:
            self._query_parts.append(f"-label:{label}")
        return self
        
    def in_date_range(self, start_date: date, end_date: date) -> "EmailQueryBuilder":
        """
        Filter emails within a specific date range.
        Args:
            start_date: Start of date range
            end_date: End of date range
        Returns:
            Self for method chaining
        """
        if start_date > end_date:
            raise ValueError("Start date must be before end date")

        start_date = datetime.combine(start_date, datetime.min.time())
        start_date = convert_datetime_to_local_timezone(start_date)
        start_date_timestamp = int(start_date.timestamp())

        end_date = datetime.combine(end_date, datetime.min.time())
        end_date = convert_datetime_to_local_timezone(end_date)
        end_date_timestamp = int(end_date.timestamp())

        self._query_parts.append(f"after:{start_date_timestamp}")
        self._query_parts.append(f"before:{end_date_timestamp}")
        return self
        
    def after_date(self, date_obj: date) -> "EmailQueryBuilder":
        """
        Filter emails after a specific date.
        Args:
            date_obj: Date to filter after
        Returns:
            Self for method chaining
        """
        date_obj = datetime.combine(date_obj, datetime.min.time())
        date_obj = convert_datetime_to_local_timezone(date_obj)
        date_obj_timestamp = int(date_obj.timestamp())

        self._query_parts.append(f"after:{date_obj_timestamp}")
        return self
        
    def before_date(self, date_obj: date) -> "EmailQueryBuilder":
        """
        Filter emails before a specific date.
        Args:
            date_obj: Date to filter before
        Returns:
            Self for method chaining
        """
        date_obj = datetime.combine(date_obj, datetime.min.time())
        date_obj = convert_datetime_to_local_timezone(date_obj)
        date_timestamp = int(date_obj.timestamp())
        self._query_parts.append(f"before:{date_timestamp}")
        return self
        
    def today(self) -> "EmailQueryBuilder":
        """
        Filter emails from today only.
        Returns:
            Self for method chaining
        """
        today = datetime.combine(datetime.today(), datetime.min.time())
        today = convert_datetime_to_local_timezone(today)
        today_timestamp = int(today.timestamp())

        self._query_parts.append(f"after:{today_timestamp}")
        return self
        
    def yesterday(self) -> "EmailQueryBuilder":
        """
        Filter emails from yesterday only.
        Returns:
            Self for method chaining
        """
        yesterday = datetime.now().date() - timedelta(days=1)
        yesterday = datetime.combine(yesterday, datetime.min.time())
        yesterday = convert_datetime_to_local_timezone(yesterday)
        yesterday_timestamp = int(yesterday.timestamp())

        today = datetime.now().date()
        today = datetime.combine(today, datetime.min.time())
        today = convert_datetime_to_local_timezone(today)
        today_timestamp = int(today.timestamp())

        self._query_parts.append(f"after:{yesterday_timestamp}")
        self._query_parts.append(f"before:{today_timestamp}")

        return self
        
    def last_days(self, days: int) -> "EmailQueryBuilder":
        """
        Filter emails from the last N days.
        Args:
            days: Number of days back to search
        Returns:
            Self for method chaining
        """
        if days < 0:
            raise ValueError("Days must be positive")
            
        start_date = datetime.now() - timedelta(days=days)
        start_date = datetime.combine(start_date, datetime.min.time())
        start_date = convert_datetime_to_local_timezone(start_date)
        start_date_timestamp = int(start_date.timestamp())

        self._query_parts.append(f"after:{start_date_timestamp}")
        return self
        
    def this_week(self) -> "EmailQueryBuilder":
        """
        Filter emails from this week.
        Returns:
            Self for method chaining
        """
        days_since_monday = date.weekday(date.today() )  # Monday is 0
        return self.last_days(days_since_monday)
        
    def this_month(self) -> "EmailQueryBuilder":
        """
        Filter emails from this month.
        Returns:
            Self for method chaining
        """
        days_since_month_started = date.today().day - 1# Days in current month
        return self.last_days(days_since_month_started)
        
    def larger_than(self, size_mb: int) -> "EmailQueryBuilder":
        """
        Filter emails larger than specified size.
        Args:
            size_mb: Size in megabytes
        Returns:
            Self for method chaining
        """
        if size_mb < 1:
            raise ValueError("Size must be positive")
        self._query_parts.append(f"larger:{size_mb}M")
        return self
        
    def smaller_than(self, size_mb: int) -> "EmailQueryBuilder":
        """
        Filter emails smaller than specified size.
        Args:
            size_mb: Size in megabytes
        Returns:
            Self for method chaining
        """
        if size_mb < 1:
            raise ValueError("Size must be positive")
        self._query_parts.append(f"smaller:{size_mb}M")
        return self
        
    def include_spam_trash(self, include: bool = True) -> "EmailQueryBuilder":
        """
        Include or exclude spam and trash emails.
        Args:
            include: Whether to include spam and trash
        Returns:
            Self for method chaining
        """
        self._include_spam_trash = include
        return self
        
    def with_label_ids(self, label_ids: List[str]) -> "EmailQueryBuilder":
        """
        Filter emails with specific label IDs.
        Args:
            label_ids: List of label IDs
        Returns:
            Self for method chaining
        """
        self._label_ids.extend(label_ids)
        return self
        
    def execute(self) -> List["EmailMessage"]:
        """
        Execute the query and return the results.
        Returns:
            List of EmailMessage objects matching the query
        """
        query_string = " ".join(self._query_parts) if self._query_parts else None
        

        
        # Use the service layer implementation instead of dataclass methods
        emails = self._api_service.list_emails(
            max_results=self._max_results,
            query=query_string,
            include_spam_trash=self._include_spam_trash,
            label_ids=self._label_ids if self._label_ids else None
        )

        return emails

    def first(self) -> Optional["EmailMessage"]:
        """
        Get the first email matching the query.
        Returns:
            First EmailMessage object or None if no matches
        """

        results = self.limit(1).execute()

        return results[0] if results else None

    def exists(self) -> bool:
        """
        Check if any emails match the query.
        Returns:
            True if at least one email matches, False otherwise
        """
        return self.first() is not None

    def get_threads(self) -> List["EmailThread"]:
        """
        Execute the query and return threads instead of individual messages.
        Returns:
            List of EmailThread objects matching the query
        """
        query_string = " ".join(self._query_parts) if self._query_parts else None
        
        
        
        # Use the service layer implementation to get threads
        threads = self._api_service.list_threads(
            max_results=self._max_results,
            query=query_string,
            include_spam_trash=self._include_spam_trash,
            label_ids=self._label_ids if self._label_ids else None
        )

        return threads
        
    def __repr__(self):
        query_string = " ".join(self._query_parts) if self._query_parts else "None"
        return f"EmailQueryBuilder(query='{query_string}', limit={self._max_results})"