from datetime import datetime, date
from typing import Optional, List, Union, TYPE_CHECKING
import logging

from .constants import FOLDER_MIME_TYPE, MAX_RESULTS_LIMIT, DEFAULT_MAX_RESULTS
from ...utils.datetime import convert_datetime_to_iso

if TYPE_CHECKING:
    from .api_service import DriveFile, DriveFolder

logger = logging.getLogger(__name__)


class DriveQueryBuilder:
    """
    Builder pattern for constructing Drive queries with a fluent API.
    Provides a clean, readable way to build complex file queries.
    
    Example usage:
        files = (user.drive.query()
            .limit(50)
            .in_folder("parent_folder_id")
            .search("meeting")
            .file_type("pdf")
            .execute())
    """
    
    def __init__(self, api_service_class):
        self._api_service = api_service_class
        self._max_results: Optional[int] = DEFAULT_MAX_RESULTS
        self._query_parts: List[str] = []
        self._fields: Optional[str] = None
        self._order_by: Optional[str] = None
        self._page_token: Optional[str] = None
        
    def limit(self, count: int) -> "DriveQueryBuilder":
        """
        Set the maximum number of files to retrieve.
        Args:
            count: Maximum number of files (1-1000)
        Returns:
            Self for method chaining
        """
        if count < 1 or count > MAX_RESULTS_LIMIT:
            raise ValueError(f"Limit must be between 1 and {MAX_RESULTS_LIMIT}")
        self._max_results = count
        return self
        
    def search(self, query: str) -> "DriveQueryBuilder":
        """
        Add a search term to the query (searches name and content).
        Args:
            query: Search term to add
        Returns:
            Self for method chaining
        """
        if query:
            escaped_query = query.replace("'", "\\'")
            self._query_parts.append(f"fullText contains '{escaped_query}'")
        return self
        
    def name_contains(self, text: str) -> "DriveQueryBuilder":
        """
        Filter files whose name contains the specified text.
        Args:
            text: Text to search for in file names
        Returns:
            Self for method chaining
        """
        if text:
            escaped_text = text.replace("'", "\\'")
            self._query_parts.append(f"name contains '{escaped_text}'")
        return self
        
    def name_equals(self, name: str) -> "DriveQueryBuilder":
        """
        Filter files with the exact name.
        Args:
            name: Exact name to match
        Returns:
            Self for method chaining
        """
        if name:
            escaped_name = name.replace("'", "\\'")
            self._query_parts.append(f"name = '{escaped_name}'")
        return self
        
    def in_folder(self, folder: Union[str, "DriveFolder"]) -> "DriveQueryBuilder":
        """
        Filter files within a specific folder.
        Args:
            folder: DriveFolder object or folder ID string
        Returns:
            Self for method chaining
        """
        if folder:
            # Handle both DriveFolder objects and string IDs for backwards compatibility
            folder_id = folder.folder_id if hasattr(folder, 'folder_id') else folder
            self._query_parts.append(f"'{folder_id}' in parents")
        return self

    def in_any_folder(self, folders: List[Union[str, "DriveFolder"]]) -> "DriveQueryBuilder":
        """
        Filter files within any of the specified folders.
        Args:
            folders: List of DriveFolder objects or folder ID strings
        Returns:
            Self for method chaining
        """
        if folders:
            folder_ids = []
            for folder in folders:
                folder_id = folder.folder_id if hasattr(folder, 'folder_id') else folder
                folder_ids.append(folder_id)
            folder_conditions = [f"'{folder_id}' in parents" for folder_id in folder_ids]
            combined_condition = " or ".join(folder_conditions)
            self._query_parts.append(f"({combined_condition})")
        return self

    def not_in_folder(self, folder: Union[str, "DriveFolder"]) -> "DriveQueryBuilder":
        """
        Filter files NOT within a specific folder.
        Args:
            folder: DriveFolder object or folder ID string to exclude
        Returns:
            Self for method chaining
        """
        if folder:
            folder_id = folder.folder_id if hasattr(folder, 'folder_id') else folder
            self._query_parts.append(f"not '{folder_id}' in parents")
        return self
        
    def file_type(self, mime_type: str) -> "DriveQueryBuilder":
        """
        Filter files by MIME type.
        Args:
            mime_type: MIME type to filter by
        Returns:
            Self for method chaining
        """
        if mime_type:
            self._query_parts.append(f"mimeType = '{mime_type}'")
        return self
        
    def folders_only(self) -> "DriveQueryBuilder":
        """
        Filter to show only folders.
        Returns:
            Self for method chaining
        """
        self._query_parts.append(f"mimeType = '{FOLDER_MIME_TYPE}'")
        return self
        
    def files_only(self) -> "DriveQueryBuilder":
        """
        Filter to show only files (exclude folders).
        Returns:
            Self for method chaining
        """
        self._query_parts.append(f"mimeType != '{FOLDER_MIME_TYPE}'")
        return self

    def folders_named(self, name: str) -> "DriveQueryBuilder":
        """
        Filter to show only folders with a specific name.
        Args:
            name: Folder name to match
        Returns:
            Self for method chaining
        """
        if name:
            escaped_name = name.replace("'", "\\'")
            self._query_parts.append(f"mimeType = '{FOLDER_MIME_TYPE}' and name = '{escaped_name}'")
        return self

    def folders_containing(self, text: str) -> "DriveQueryBuilder":
        """
        Filter to show only folders whose name contains specific text.
        Args:
            text: Text to search for in folder names
        Returns:
            Self for method chaining
        """
        if text:
            escaped_text = text.replace("'", "\\'")
            self._query_parts.append(f"mimeType = '{FOLDER_MIME_TYPE}' and name contains '{escaped_text}'")
        return self
        
    def shared_with_me(self) -> "DriveQueryBuilder":
        """
        Filter to show only files shared with the user.
        Returns:
            Self for method chaining
        """
        self._query_parts.append("sharedWithMe = true")
        return self
        
    def owned_by_me(self) -> "DriveQueryBuilder":
        """
        Filter to show only files owned by the user.
        Returns:
            Self for method chaining
        """
        self._query_parts.append("'me' in owners")
        return self
        
    def starred(self) -> "DriveQueryBuilder":
        """
        Filter to show only starred files.
        Returns:
            Self for method chaining
        """
        self._query_parts.append("starred = true")
        return self
        
    def trashed(self, include_trashed: bool = True) -> "DriveQueryBuilder":
        """
        Filter files based on trash status.
        Args:
            include_trashed: If True, show only trashed files. If False, exclude trashed files.
        Returns:
            Self for method chaining
        """
        if include_trashed:
            self._query_parts.append("trashed = true")
        else:
            self._query_parts.append("trashed = false")
        return self
        
    def created_after(self, date_time: datetime) -> "DriveQueryBuilder":
        """
        Filter files created after the specified datetime.
        Args:
            date_time: Datetime to filter by
        Returns:
            Self for method chaining
        """
        if date_time:
            iso_date = convert_datetime_to_iso(date_time)
            self._query_parts.append(f"createdTime > '{iso_date}'")
        return self
        
    def created_before(self, date_time: datetime) -> "DriveQueryBuilder":
        """
        Filter files created before the specified datetime.
        Args:
            date_time: Datetime to filter by
        Returns:
            Self for method chaining
        """
        if date_time:
            iso_date = convert_datetime_to_iso(date_time)
            self._query_parts.append(f"createdTime < '{iso_date}'")
        return self
        
    def modified_after(self, date_time: datetime) -> "DriveQueryBuilder":
        """
        Filter files modified after the specified datetime.
        Args:
            date_time: Datetime to filter by
        Returns:
            Self for method chaining
        """
        if date_time:
            iso_date = convert_datetime_to_iso(date_time)
            self._query_parts.append(f"modifiedTime > '{iso_date}'")
        return self
        
    def modified_before(self, date_time: datetime) -> "DriveQueryBuilder":
        """
        Filter files modified before the specified datetime.
        Args:
            date_time: Datetime to filter by
        Returns:
            Self for method chaining
        """
        if date_time:
            iso_date = convert_datetime_to_iso(date_time)
            self._query_parts.append(f"modifiedTime < '{iso_date}'")
        return self
        
    def with_extension(self, extension: str) -> "DriveQueryBuilder":
        """
        Filter files by file extension.
        Args:
            extension: File extension (with or without dot)
        Returns:
            Self for method chaining
        """
        if extension:
            # Ensure extension starts with dot
            if not extension.startswith('.'):
                extension = '.' + extension
            self._query_parts.append(f"fileExtension = '{extension[1:]}'")
        return self

    def custom_query(self, query: str) -> "DriveQueryBuilder":
        """
        Add a custom query string.
        Args:
            query: Custom query string
        Returns:
            Self for method chaining
        """
        if query:
            self._query_parts.append(query)
        return self
        
    def order_by(self, field: str, ascending: bool = True) -> "DriveQueryBuilder":
        """
        Set the order of results.
        Args:
            field: Field to order by (name, createdTime, modifiedTime, etc.)
            ascending: If True, order ascending; if False, order descending
        Returns:
            Self for method chaining
        """
        direction = "asc" if ascending else "desc"
        self._order_by = f"{field} {direction}"
        return self
        
    def order_by_name(self, ascending: bool = True) -> "DriveQueryBuilder":
        """
        Order results by name.
        Args:
            ascending: If True, order A-Z; if False, order Z-A
        Returns:
            Self for method chaining
        """
        return self.order_by("name", ascending)
        
    def order_by_modified_time(self, ascending: bool = False) -> "DriveQueryBuilder":
        """
        Order results by modification time.
        Args:
            ascending: If True, oldest first; if False, newest first (default)
        Returns:
            Self for method chaining
        """
        return self.order_by("modifiedTime", ascending)
        
    def order_by_created_time(self, ascending: bool = False) -> "DriveQueryBuilder":
        """
        Order results by creation time.
        Args:
            ascending: If True, oldest first; if False, newest first (default)
        Returns:
            Self for method chaining
        """
        return self.order_by("createdTime", ascending)
        
    def fields(self, fields: str) -> "DriveQueryBuilder":
        """
        Set specific fields to retrieve from the API.
        Args:
            fields: Comma-separated list of fields
        Returns:
            Self for method chaining
        """
        self._fields = fields
        return self
        
    def _build_query(self) -> str:
        """
        Build the final query string.
        Returns:
            Combined query string
        """
        if not self._query_parts:
            return ""
        
        return " and ".join(f"({part})" for part in self._query_parts)
        
    def execute(self) -> List[Union["DriveFile", "DriveFolder"]]:
        """
        Execute the query and return results.
        Returns:
            List of DriveFile and DriveFolder objects matching the query
        """
        query = self._build_query()
        
        logger.debug(f"Executing Drive query: {query}")
        
        return self._api_service.list(
            query=query,
            max_results=self._max_results,
            order_by=self._order_by,
            fields=self._fields,
            page_token=self._page_token
        )