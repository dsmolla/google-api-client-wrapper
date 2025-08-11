import io
import os
from typing import Optional, List, Dict, Any, Union, BinaryIO
import logging

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload, MediaIoBaseDownload

from .utils import convert_mime_type_to_downloadable
from ...utils.log_sanitizer import sanitize_for_logging
from .types import DriveFile, DriveFolder, Permission, DriveComment
from .query_builder import DriveQueryBuilder
from . import utils
from .constants import (
    DEFAULT_MAX_RESULTS, MAX_RESULTS_LIMIT, DEFAULT_FILE_FIELDS,
    FOLDER_MIME_TYPE, DEFAULT_CHUNK_SIZE
)
from .exceptions import (
    DriveError, FileNotFoundError, FolderNotFoundError, PermissionDeniedError, FileTooLargeError,
    UploadFailedError, DownloadFailedError, SharingError, DrivePermissionError, InvalidQueryError
)

logger = logging.getLogger(__name__)


class DriveApiService:
    """
    Service layer for Drive API operations.
    Contains all Drive API functionality following the user-centric approach.
    """
    
    def __init__(self, service: Any):
        """
        Initialize Drive service.
        
        Args:
            service: The Drive API service instance
        """
        self._service = service

    def query(self) -> DriveQueryBuilder:
        """
        Create a new DriveQueryBuilder for building complex file queries with a fluent API.

        Returns:
            DriveQueryBuilder instance for method chaining

        Example:
            files = (user.drive.query()
                .limit(50)
                .in_folder("parent_folder_id")
                .search("meeting")
                .file_type("pdf")
                .execute())
        """
        return DriveQueryBuilder(self)

    def list(
        self,
        query: Optional[str] = None,
        max_results: Optional[int] = DEFAULT_MAX_RESULTS,
        order_by: Optional[str] = None,
        fields: Optional[str] = None,
        page_token: Optional[str] = None
    ) -> List[Union[DriveFile, DriveFolder]]:
        """
        List files and folders in Drive.
        
        Args:
            query: Drive API query string
            max_results: Maximum number of items to return
            order_by: Field to order results by
            fields: Fields to include in response
            page_token: Token for pagination
            
        Returns:
            List of DriveFile and DriveFolder objects
            
        Raises:
            DriveError: If the API request fails
        """
        try:
            if max_results and (max_results < 1 or max_results > MAX_RESULTS_LIMIT):
                raise ValueError(f"max_results must be between 1 and {MAX_RESULTS_LIMIT}")

            request_params = {
                'pageSize': max_results or DEFAULT_MAX_RESULTS,
                'fields': f'nextPageToken, files({fields or DEFAULT_FILE_FIELDS})'
            }
            
            if query:
                request_params['q'] = query
            if order_by:
                request_params['orderBy'] = order_by
            if page_token:
                request_params['pageToken'] = page_token

            logger.debug(f"Listing files with params: {sanitize_for_logging(**request_params)}")

            result = self._service.files().list(**request_params).execute()
            files_data = result.get('files', [])
            
            items = [utils.convert_api_file_to_correct_type(file_data) for file_data in files_data]
            
            logger.info(f"Retrieved {len(items)} items from Drive")
            return items

        except HttpError as e:
            error_msg = f"Failed to list files: {e}"
            logger.error(error_msg)
            
            if e.resp.status == 403:
                raise PermissionDeniedError(f"Permission denied: {e}")
            elif e.resp.status == 400:
                raise InvalidQueryError(f"Invalid query: {e}")
            else:
                raise DriveError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error listing files: {e}"
            logger.error(error_msg)
            raise DriveError(error_msg)

    def get(self, item_id: str, fields: Optional[str] = None) -> Union[DriveFile, DriveFolder]:
        """
        Get a file or folder by its id.
        
        Args:
            item_id: File id or folder id
            fields: Fields to include in response
            
        Returns:
            DriveFile object
            
        Raises:
            FileNotFoundError: If the file is not found
            DriveError: If the API request fails
        """
        try:
            logger.debug(f"Getting item: {item_id}")
            
            request_params = {
                'fileId': item_id,
                'fields': fields or DEFAULT_FILE_FIELDS
            }
            
            result = self._service.files().get(**request_params).execute()
            file_obj = utils.convert_api_file_to_correct_type(result)
            
            logger.info(f"Retrieved file: {file_obj.name}")
            return file_obj

        except HttpError as e:
            if e.resp.status == 404:
                raise FileNotFoundError(f"File not found: {item_id}")
            elif e.resp.status == 403:
                raise PermissionDeniedError(f"Permission denied for file: {item_id}")
            else:
                error_msg = f"Failed to get file {item_id}: {e}"
                logger.error(error_msg)
                raise DriveError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error getting file {item_id}: {e}"
            logger.error(error_msg)
            raise DriveError(error_msg)

    def upload_file(
        self,
        file_path: str,
        name: Optional[str] = None,
        parent_folder_id: Optional[str] = None,
        description: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> DriveFile:
        """
        Upload a file to Drive.
        
        Args:
            file_path: Local path to the file to upload
            name: Name for the file in Drive (defaults to filename)
            parent_folder_id: ID of parent folder
            description: File description
            mime_type: MIME type (auto-detected if not provided)
            
        Returns:
            DriveFile object for the uploaded file
            
        Raises:
            FileNotFoundError: If the local file doesn't exist
            UploadFailedError: If the upload fails
            DriveError: If the API request fails
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Local file not found: {file_path}")

            file_name = name or os.path.basename(file_path)
            file_mime_type = mime_type or utils.guess_mime_type(file_path)
            
            metadata = utils.build_file_metadata(
                name=utils.sanitize_filename(file_name),
                parents=[parent_folder_id] if parent_folder_id else None,
                description=description
            )
            
            media = MediaFileUpload(
                file_path,
                mimetype=file_mime_type,
                resumable=True,
                chunksize=DEFAULT_CHUNK_SIZE
            )
            
            logger.debug(f"Uploading file: {file_path} as {file_name}")
            
            result = self._service.files().create(
                body=metadata,
                media_body=media,
                fields=DEFAULT_FILE_FIELDS
            ).execute()
            
            file_obj = utils.convert_api_file_to_drive_file(result)
            logger.info(f"Successfully uploaded file: {file_obj.name} ({file_obj.file_id})")
            return file_obj

        except HttpError as e:
            if e.resp.status == 403:
                raise PermissionDeniedError(f"Permission denied uploading file: {e}")
            elif e.resp.status == 413:
                raise FileTooLargeError(f"File too large: {file_path}")
            else:
                error_msg = f"Failed to upload file {file_path}: {e}"
                logger.error(error_msg)
                raise UploadFailedError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error uploading file {file_path}: {e}"
            logger.error(error_msg)
            raise UploadFailedError(error_msg)

    def upload_file_content(
        self,
        content: Union[str, bytes, BinaryIO],
        name: str,
        parent_folder_id: Optional[str] = None,
        description: Optional[str] = None,
        mime_type: str = "text/plain"
    ) -> DriveFile:
        """
        Upload file content directly to Drive.
        
        Args:
            content: File content (string, bytes, or file-like object)
            name: Name for the file in Drive
            parent_folder_id: ID of parent folder
            description: File description
            mime_type: MIME type of the content
            
        Returns:
            DriveFile object for the uploaded file
            
        Raises:
            UploadFailedError: If the upload fails
            DriveError: If the API request fails
        """
        try:
            metadata = utils.build_file_metadata(
                name=utils.sanitize_filename(name),
                parents=[parent_folder_id] if parent_folder_id else None,
                description=description
            )
            
            # Convert content to file-like object
            if isinstance(content, str):
                content_io = io.StringIO(content)
            elif isinstance(content, bytes):
                content_io = io.BytesIO(content)
            else:
                content_io = content
            
            media = MediaIoBaseUpload(
                content_io,
                mimetype=mime_type,
                resumable=True
            )
            
            logger.debug(f"Uploading content as file: {name}")
            
            result = self._service.files().create(
                body=metadata,
                media_body=media,
                fields=DEFAULT_FILE_FIELDS
            ).execute()
            
            file_obj = utils.convert_api_file_to_drive_file(result)
            logger.info(f"Successfully uploaded content as file: {file_obj.name} ({file_obj.file_id})")
            return file_obj

        except HttpError as e:
            if e.resp.status == 403:
                raise PermissionDeniedError(f"Permission denied uploading content: {e}")
            else:
                error_msg = f"Failed to upload content as {name}: {e}"
                logger.error(error_msg)
                raise UploadFailedError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error uploading content as {name}: {e}"
            logger.error(error_msg)
            raise UploadFailedError(error_msg)

    def download_file(self, file: DriveFile, local_path: str) -> str:
        """
        Download a file from Drive to local disk.
        
        Args:
            file: DriveFile object to download
            local_path: Local path where to save the file
            
        Returns:
            Local path of the downloaded file
            
        Raises:
            FileNotFoundError: If the file is not found
            DownloadFailedError: If the download fails
            DriveError: If the API request fails
        """
        logger.debug(f"Downloading file {file.file_id} to {local_path}")

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        with open(local_path, "wb") as f:
            f.write(self.download_file_content(file))

        return local_path

    def download_file_content(self, file: DriveFile) -> bytes:
        """
        Download file content as bytes.
        
        Args:
            file: DriveFile object to download
            
        Returns:
            File content as bytes
            
        Raises:
            FileNotFoundError: If the file is not found
            DownloadFailedError: If the download fails
            DriveError: If the API request fails
        """
        try:
            logger.debug(f"Downloading content of file: {file.file_id}")
            content_io = io.BytesIO()

            request = None
            if file.is_google_doc():
                request = self._service.files().export_media(
                    fileId=file.file_id, mimeType=convert_mime_type_to_downloadable(file.mime_type)
                )
            else:
                request = self._service.files().get_media(fileId=file.file_id)

            downloader = MediaIoBaseDownload(content_io, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

            content = content_io.getvalue()
            logger.info(f"Successfully downloaded file content ({len(content)} bytes)")
            return content

        except HttpError as e:
            if e.resp.status == 404:
                raise FileNotFoundError(f"File not found: {file.file_id}")
            elif e.resp.status == 403:
                raise PermissionDeniedError(f"Permission denied downloading file: {file.file_id}")
            else:
                error_msg = f"Failed to download file content {file.file_id}: {e}"
                logger.error(error_msg)
                raise DownloadFailedError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error downloading file content {file.file_id}: {e}"
            logger.error(error_msg)
            raise DownloadFailedError(error_msg)

    def create_folder(
        self,
        name: str,
        parent_folder: Optional[DriveFolder] = None,
        description: Optional[str] = None
    ) -> DriveFolder:
        """
        Create a new folder in Drive.
        
        Args:
            name: Name of the folder
            parent_folder: Parent DriveFolder (optional)
            description: Folder description
            
        Returns:
            DriveFolder object for the created folder
            
        Raises:
            DriveError: If the API request fails
        """
        try:
            parent_id = parent_folder.folder_id if parent_folder else None
            metadata = utils.build_file_metadata(
                name=utils.sanitize_filename(name),
                parents=[parent_id] if parent_id else None,
                description=description,
                mimeType=FOLDER_MIME_TYPE
            )
            
            logger.debug(f"Creating folder: {name}")
            
            result = self._service.files().create(
                body=metadata,
                fields=DEFAULT_FILE_FIELDS
            ).execute()
            
            folder_obj = utils.convert_api_file_to_drive_folder(result)
            logger.info(f"Successfully created folder: {folder_obj.name} ({folder_obj.folder_id})")
            return folder_obj

        except HttpError as e:
            if e.resp.status == 403:
                raise PermissionDeniedError(f"Permission denied creating folder: {e}")
            else:
                error_msg = f"Failed to create folder {name}: {e}"
                logger.error(error_msg)
                raise DriveError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error creating folder {name}: {e}"
            logger.error(error_msg)
            raise DriveError(error_msg)

    def delete(self, item: Union[DriveFile, DriveFolder]) -> bool:
        """
        Delete a file or folder from Drive.
        
        Args:
            item: DriveFile or DriveFolder object to delete
            
        Returns:
            True if deletion was successful
            
        Raises:
            FileNotFoundError: If the item is not found
            DriveError: If the API request fails
        """
        item_id = item.file_id if isinstance(item, DriveFile) else item.folder_id
        try:
            logger.debug(f"Deleting item: {item_id}")
            
            self._service.files().delete(fileId=item_id).execute()
            
            logger.info(f"Successfully deleted item: {item_id}")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                raise FileNotFoundError(f"Item not found: {item_id}")
            elif e.resp.status == 403:
                raise PermissionDeniedError(f"Permission denied deleting item: {item_id}")
            else:
                error_msg = f"Failed to delete item {item_id}: {e}"
                logger.error(error_msg)
                raise DriveError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error deleting item {item_id}: {e}"
            logger.error(error_msg)
            raise DriveError(error_msg)

    def copy(
        self,
        item: Union[DriveFile, DriveFolder],
        new_name: Optional[str] = None,
        parent_folder: Optional[DriveFolder] = None
    ) -> Union[DriveFile, DriveFolder]:
        """
        Copy a file or folder in Drive.
        
        Args:
            item: DriveFile or DriveFolder object to copy
            new_name: Name for the copied item
            parent_folder: Parent DriveFolder for the copy
            
        Returns:
            DriveFile or DriveFolder object for the copied item
            
        Raises:
            FileNotFoundError: If the source item is not found
            DriveError: If the API request fails
        """
        item_id = item.file_id if isinstance(item, DriveFile) else item.folder_id
        try:
            metadata = {}
            if new_name:
                metadata['name'] = utils.sanitize_filename(new_name)
            if parent_folder:
                metadata['parents'] = [parent_folder.folder_id]
            
            logger.debug(f"Copying item: {item_id}")
            
            result = self._service.files().copy(
                fileId=item_id,
                body=metadata,
                fields=DEFAULT_FILE_FIELDS
            ).execute()
            
            copied_item = utils.convert_api_file_to_correct_type(result)
            copied_id = copied_item.file_id if isinstance(copied_item, DriveFile) else copied_item.folder_id
            logger.info(f"Successfully copied item: {copied_item.name} ({copied_id})")
            return copied_item

        except HttpError as e:
            if e.resp.status == 404:
                raise FileNotFoundError(f"Item not found: {item_id}")
            elif e.resp.status == 403:
                raise PermissionDeniedError(f"Permission denied copying item: {item_id}")
            else:
                error_msg = f"Failed to copy item {item_id}: {e}"
                logger.error(error_msg)
                raise DriveError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error copying item {item_id}: {e}"
            logger.error(error_msg)
            raise DriveError(error_msg)

    def rename(
        self,
        item: Union[DriveFile, DriveFolder],
        name: Optional[str] = None,
    ) -> Union[DriveFile, DriveFolder]:
        """
        Rename a file or folder in Drive.
        
        Args:
            item: DriveFile or DriveFolder object to update
            name: New name for the item
            
        Returns:
            Updated DriveFile or DriveFolder object
            
        Raises:
            FileNotFoundError: If the item is not found
            DriveError: If the API request fails
        """
        item_id = item.file_id if isinstance(item, DriveFile) else item.folder_id
        try:
            logger.debug(f"Updating item metadata: {item_id}")
            
            result = self._service.files().update(
                fileId=item_id,
                body={'name': utils.sanitize_filename(name)},
                fields=DEFAULT_FILE_FIELDS
            ).execute()
            
            updated_item = utils.convert_api_file_to_correct_type(result)
            logger.info(f"Successfully renamed item: {updated_item.name}")
            return updated_item

        except HttpError as e:
            if e.resp.status == 404:
                raise FileNotFoundError(f"Item not found: {item_id}")
            elif e.resp.status == 403:
                raise PermissionDeniedError(f"Permission denied renaming item: {item_id}")
            else:
                error_msg = f"Failed to rename item {item_id}: {e}"
                logger.error(error_msg)
                raise DriveError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error renaming item {item_id}: {e}"
            logger.error(error_msg)
            raise DriveError(error_msg)

    def share(
        self,
        item: Union[DriveFile, DriveFolder],
        email: str,
        role: str = "reader",
        notify: bool = True,
        message: Optional[str] = None
    ) -> Permission:
        """
        Share a file or folder with a user.
        
        Args:
            item: DriveFile or DriveFolder object to share
            email: Email address of the user to share with
            role: Permission role (reader, writer, commenter)
            notify: Whether to send notification email
            message: Custom message to include in notification
            
        Returns:
            Permission object for the created permission
            
        Raises:
            FileNotFoundError: If the item is not found
            SharingError: If sharing fails
            DriveError: If the API request fails
        """
        item_id = item.file_id if isinstance(item, DriveFile) else item.folder_id
        try:
            permission_metadata = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }
            
            logger.debug(f"Sharing item {item_id} with {email} as {role}")
            
            result = self._service.permissions().create(
                fileId=item_id,
                body=permission_metadata,
                sendNotificationEmail=notify,
                emailMessage=message,
                fields='*'
            ).execute()
            
            permission = utils.convert_api_permission_to_permission(result)
            logger.info(f"Successfully shared item with {email}")
            return permission

        except HttpError as e:
            if e.resp.status == 404:
                raise FileNotFoundError(f"Item not found: {item_id}")
            elif e.resp.status == 403:
                raise PermissionDeniedError(f"Permission denied sharing item: {item_id}")
            else:
                error_msg = f"Failed to share item {item_id} with {email}: {e}"
                logger.error(error_msg)
                raise SharingError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error sharing item {item_id} with {email}: {e}"
            logger.error(error_msg)
            raise SharingError(error_msg)

    def get_permissions(self, item: Union[DriveFile, DriveFolder]) -> List[Permission]:
        """
        Get all permissions for a file or folder.
        
        Args:
            item: DriveFile or DriveFolder object to get permissions for
            
        Returns:
            List of Permission objects
            
        Raises:
            FileNotFoundError: If the item is not found
            DriveError: If the API request fails
        """
        item_id = item.file_id if isinstance(item, DriveFile) else item.folder_id
        try:
            logger.debug(f"Getting permissions for item: {item_id}")
            
            result = self._service.permissions().list(
                fileId=item_id,
                fields='permissions(*)'
            ).execute()
            
            permissions_data = result.get('permissions', [])
            permissions = [utils.convert_api_permission_to_permission(perm) 
                         for perm in permissions_data]
            
            logger.info(f"Retrieved {len(permissions)} permissions for item {item_id}")
            return permissions

        except HttpError as e:
            if e.resp.status == 404:
                raise FileNotFoundError(f"Item not found: {item_id}")
            elif e.resp.status == 403:
                raise PermissionDeniedError(f"Permission denied getting permissions: {item_id}")
            else:
                error_msg = f"Failed to get permissions for item {item_id}: {e}"
                logger.error(error_msg)
                raise DriveError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error getting permissions for item {item_id}: {e}"
            logger.error(error_msg)
            raise DriveError(error_msg)

    def remove_permission(self, item: Union[DriveFile, DriveFolder], permission_id: str) -> bool:
        """
        Remove a permission from a file or folder.
        
        Args:
            item: DriveFile or DriveFolder object to remove permission from
            permission_id: ID of the permission to remove
            
        Returns:
            True if removal was successful
            
        Raises:
            FileNotFoundError: If the item is not found
            DrivePermissionError: If permission removal fails
            DriveError: If the API request fails
        """
        item_id = item.file_id if isinstance(item, DriveFile) else item.folder_id
        try:
            logger.debug(f"Removing permission {permission_id} from item {item_id}")
            
            self._service.permissions().delete(
                fileId=item_id,
                permissionId=permission_id
            ).execute()
            
            logger.info(f"Successfully removed permission {permission_id}")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                raise FileNotFoundError(f"File or permission not found")
            elif e.resp.status == 403:
                raise PermissionDeniedError(f"Permission denied removing permission")
            else:
                error_msg = f"Failed to remove permission {permission_id}: {e}"
                logger.error(error_msg)
                raise DrivePermissionError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error removing permission {permission_id}: {e}"
            logger.error(error_msg)
            raise DrivePermissionError(error_msg)

    def list_folder_contents(
        self,
        folder: DriveFolder,
        include_folders: bool = True,
        include_files: bool = True,
        max_results: Optional[int] = DEFAULT_MAX_RESULTS,
        order_by: Optional[str] = None
    ) -> List[Union[DriveFile, DriveFolder]]:
        """
        List all contents (files and/or folders) within a specific folder.
        
        Args:
            folder: DriveFolder object representing the folder
            include_folders: Whether to include subfolders in results
            include_files: Whether to include files in results
            max_results: Maximum number of items to return
            order_by: Field to order results by
            
        Returns:
            List of DriveFile and DriveFolder objects in the folder
            
        Raises:
            FolderNotFoundError: If the folder is not found
            DriveError: If the API request fails
        """
        
        try:
            query_builder = self.query().in_folder(folder.folder_id)
            
            if include_folders and not include_files:
                query_builder = query_builder.folders_only()
            elif include_files and not include_folders:
                query_builder = query_builder.files_only()
            
            if max_results:
                query_builder = query_builder.limit(max_results)
            
            if order_by:
                query_builder = query_builder.order_by(order_by)
            
            contents = query_builder.execute()
            
            logger.info(f"Retrieved {len(contents)} items from folder: {folder.name}")
            return contents

        except Exception as e:
            if "not found" in str(e).lower():
                raise FolderNotFoundError(f"Folder not found: {folder.folder_id}")
            error_msg = f"Failed to list contents of folder {folder.folder_id}: {e}"
            logger.error(error_msg)
            raise DriveError(error_msg)

    def move_to_folder(
        self,
        item: Union[DriveFile, DriveFolder],
        target_folder: DriveFolder,
        remove_from_current_parents: bool = True
    ) -> Union[DriveFile, DriveFolder]:
        """
        Move a file or folder to a different parent folder.
        
        Args:
            item: DriveFile or DriveFolder object to move
            target_folder: Target DriveFolder
            remove_from_current_parents: Whether to remove from current parents
            
        Returns:
            Updated DriveFile or DriveFolder object
            
        Raises:
            FileNotFoundError: If the item or target folder is not found
            DriveError: If the API request fails
        """
        # Get the appropriate ID and parents
        item_id = item.file_id if isinstance(item, DriveFile) else item.folder_id
        item_parents = item.parents
        try:
            # Prepare the update metadata
            update_params = {
                'fileId': item_id,
                'addParents': target_folder.folder_id,
                'fields': DEFAULT_FILE_FIELDS
            }
            
            # Remove from current parents if requested
            if remove_from_current_parents and item_parents:
                update_params['removeParents'] = ','.join(item_parents)
            
            logger.debug(f"Moving item {item_id} to folder {target_folder.folder_id}")
            
            result = self._service.files().update(**update_params).execute()
            
            updated_item = utils.convert_api_file_to_correct_type(result)
            logger.info(f"Successfully moved {item.name} to {target_folder.name}")
            return updated_item

        except HttpError as e:
            if e.resp.status == 404:
                raise FileNotFoundError(f"File or folder not found")
            elif e.resp.status == 403:
                raise PermissionDeniedError(f"Permission denied moving file")
            else:
                error_msg = f"Failed to move item {item_id}: {e}"
                logger.error(error_msg)
                raise DriveError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error moving item {item_id}: {e}"
            logger.error(error_msg)
            raise DriveError(error_msg)

    def get_parent_folder(self, item: Union[DriveFile, DriveFolder]) -> Optional[DriveFolder]:
        """
        Get the parent folder of a file or folder.
        
        Args:
            item: DriveFile or DriveFolder object to get parent for
            
        Returns:
            Parent DriveFolder, or None if no parent
            
        Raises:
            DriveError: If the API request fails
        """
        parent_id = item.get_parent_folder_id()
        if not parent_id:
            return None
        
        try:
            result = self._service.files().get(
                fileId=parent_id,
                fields=DEFAULT_FILE_FIELDS
            ).execute()
            
            parent_folder = utils.convert_api_file_to_drive_folder(result)
            logger.info(f"Retrieved parent folder: {parent_folder.name}")
            return parent_folder

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Parent folder {parent_id} not found")
                return None
            else:
                error_msg = f"Failed to get parent folder {parent_id}: {e}"
                logger.error(error_msg)
                raise DriveError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error getting parent folder {parent_id}: {e}"
            logger.error(error_msg)
            raise DriveError(error_msg)

    def get_folder_by_path(self, path: str, root_folder_id: str = "root") -> Optional[DriveFolder]:
        """
        Find a folder by its path relative to a root folder.
        
        Args:
            path: Folder path like "/Documents/Projects" or "Documents/Projects"
            root_folder_id: ID of the root folder to start from (default: Drive root)
            
        Returns:
            DriveFolder object for the folder, or None if not found
            
        Raises:
            DriveError: If the API request fails
        """
        from . import utils as drive_utils
        
        folder_names = drive_utils.parse_folder_path(path)
        if not folder_names:
            # Return root folder
            try:
                result = self._service.files().get(
                    fileId=root_folder_id,
                    fields=DEFAULT_FILE_FIELDS
                ).execute()
                return utils.convert_api_file_to_drive_folder(result)
            except Exception:
                return None
        
        current_folder_id = root_folder_id
        
        try:
            for folder_name in folder_names:
                # Search for folder with this name in current folder
                folders = (self.query()
                          .in_folder(current_folder_id)
                          .folders_named(folder_name)
                          .limit(1)
                          .execute())
                
                if not folders:
                    logger.info(f"Folder '{folder_name}' not found in path: {path}")
                    return None
                
                current_folder_id = folders[0].folder_id
            
            # Get the final folder
            result = self._service.files().get(
                fileId=current_folder_id,
                fields=DEFAULT_FILE_FIELDS
            ).execute()
            
            final_folder = utils.convert_api_file_to_drive_folder(result)
            logger.info(f"Found folder at path '{path}': {final_folder.name}")
            return final_folder

        except Exception as e:
            error_msg = f"Failed to get folder by path '{path}': {e}"
            logger.error(error_msg)
            raise DriveError(error_msg)

    def create_folder_path(
        self,
        path: str,
        root_folder_id: str = "root",
        description: Optional[str] = None
    ) -> DriveFolder:
        """
        Create a nested folder structure from a path, creating missing folders as needed.
        
        Args:
            path: Folder path like "/Documents/Projects/MyProject"
            root_folder_id: ID of the root folder to start from
            description: Description for the final folder
            
        Returns:
            DriveFolder object for the final folder in the path
            
        Raises:
            DriveError: If the API request fails
        """
        from . import utils as drive_utils
        
        folder_names = drive_utils.parse_folder_path(path)
        if not folder_names:
            raise ValueError("Invalid folder path")
        
        current_folder_id = root_folder_id
        
        try:
            for i, folder_name in enumerate(folder_names):
                # Check if folder already exists
                existing_folders = (self.query()
                                   .in_folder(current_folder_id)
                                   .folders_named(folder_name)
                                   .limit(1)
                                   .execute())
                
                if existing_folders:
                    current_folder_id = existing_folders[0].file_id
                    logger.debug(f"Folder '{folder_name}' already exists")
                else:
                    # Create the folder - get parent folder object first
                    folder_desc = description if i == len(folder_names) - 1 else None
                    if current_folder_id == root_folder_id:
                        parent_folder = None  # Root folder
                    else:
                        # Get parent folder as DriveFolder
                        parent_result = self._service.files().get(
                            fileId=current_folder_id,
                            fields=DEFAULT_FILE_FIELDS
                        ).execute()
                        parent_folder = utils.convert_api_file_to_drive_folder(parent_result)
                    
                    new_folder = self.create_folder(
                        name=folder_name,
                        parent_folder=parent_folder,
                        description=folder_desc
                    )
                    current_folder_id = new_folder.folder_id
                    logger.info(f"Created folder: {folder_name}")
            
            # Return the final folder
            result = self._service.files().get(
                fileId=current_folder_id,
                fields=DEFAULT_FILE_FIELDS
            ).execute()
            
            final_folder = utils.convert_api_file_to_drive_folder(result)
            logger.info(f"Created/found folder path '{path}': {final_folder.name}")
            return final_folder

        except Exception as e:
            error_msg = f"Failed to create folder path '{path}': {e}"
            logger.error(error_msg)
            raise DriveError(error_msg)



