import io
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, BinaryIO

from google.auth.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload, MediaIoBaseDownload

from . import utils
from .constants import DEFAULT_FILE_FIELDS, FOLDER_MIME_TYPE, DEFAULT_CHUNK_SIZE
from .exceptions import FileNotFoundError, FolderNotFoundError, PermissionDeniedError
from .types import DriveFile, DriveFolder, Permission, DriveItem
from ...utils.datetime import datetime_to_readable


class DriveApiService:
    """
    Service layer for Drive API operations.
    Contains all Drive API functionality following the user-centric approach.
    """

    def __init__(self, credentials: Credentials, timezone: str = "UTC"):
        """
        Initialize Drive service.

        Args:
            credentials: Google API credentials
            timezone: User's timezone for date/time operations (e.g., 'America/New_York')
        """
        self._service = build("drive", "v3", credentials=credentials)
        self._timezone = timezone

    def query(self):
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
        from .query_builder import DriveQueryBuilder
        return DriveQueryBuilder(self, self._timezone)

    def list(
            self,
            query: Optional[str] = None,
            max_results: Optional[int] = 100,
            order_by: Optional[str] = None,
    ) -> List[DriveItem]:
        """
        List files and folders in Drive.

        Args:
            query: Drive API query string
            max_results: Maximum number of items to return. Defaults to 100
            order_by: Field to order results by

        Returns:
            List of DriveFile and DriveFolder objects
        """
        if max_results < 1:
            raise ValueError(f"max_results must be at least 1")

        request_params = {'pageSize': max_results}

        if query:
            request_params['q'] = query
        if order_by:
            request_params['orderBy'] = order_by

        result = self._service.files().list(**request_params).execute()
        items = [utils.convert_api_file_to_correct_type(file_data) for file_data in result.get('files', [])]

        while result.get('nextPageToken') and len(items) < max_results:
            request_params['pageSize'] = max_results - len(items)
            result = self._service.files().list(**request_params, pageToken=result['nextPageToken']).execute()
            items.extend([utils.convert_api_file_to_correct_type(file_data) for file_data in result.get('files', [])])

        return items

    def get(self, item_id: str, fields: Optional[str] = None) -> DriveItem:
        """
        Get a file or folder by its id.

        Args:
            item_id: File id or folder id
            fields: Fields to include in response

        Returns:
            DriveFile or DriveFolder object
        """
        request_params = {
            'fileId': item_id,
            'fields': fields or DEFAULT_FILE_FIELDS
        }

        result = self._service.files().get(**request_params).execute()
        file_obj = utils.convert_api_file_to_correct_type(result)
        return file_obj

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
        """
        file_path = Path(file_path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Local file not found: {str(file_path)}")

        file_name = name or file_path.name
        file_mime_type = mime_type or utils.guess_mime_type(str(file_path))

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

        result = self._service.files().create(
            body=metadata,
            media_body=media,
            fields=DEFAULT_FILE_FIELDS
        ).execute()

        file_obj = utils.convert_api_file_to_drive_file(result)
        return file_obj

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
        """
        metadata = utils.build_file_metadata(
            name=utils.sanitize_filename(name),
            parents=[parent_folder_id] if parent_folder_id else None,
            description=description
        )

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

        result = self._service.files().create(
            body=metadata,
            media_body=media,
            fields=DEFAULT_FILE_FIELDS
        ).execute()

        file_obj = utils.convert_api_file_to_drive_file(result)
        return file_obj

    def download_file(
            self,
            file: DriveFile | str,
            destination_folder: str = str(Path.home() / "Downloads" / "DriveFiles"),
            file_name: str = None
    ) -> str:
        """
        Download a file from Drive to local disk.

        Args:
            file: DriveFile object to download
            destination_folder: Local directory where to save the file
            file_name: Optional file name with extension

        Returns:
            Local path of the downloaded file
        """

        destination_folder = Path(destination_folder)
        destination_folder.mkdir(parents=True, exist_ok=True)

        if isinstance(file, str):
            file = self.get(file)

        if not file_name:
            file_name = file.name
        file_path = str(destination_folder.joinpath(file_name))
        with open(file_path, "wb") as f:
            f.write(self.get_file_payload(file))

        return file_path

    def get_file_payload(self, file: DriveFile | str) -> bytes:
        """
        Download file content as bytes.

        Args:
            file: DriveFile object to download

        Returns:
            File content as bytes
        """
        if isinstance(file, str):
            file = self.get(file)
        content_io = io.BytesIO()
        if file.is_google_doc():
            request = self._service.files().export_media(
                fileId=file.file_id, mimeType=utils.convert_mime_type_to_downloadable(file.mime_type)
            )
        else:
            request = self._service.files().get_media(fileId=file.file_id)

        downloader = MediaIoBaseDownload(content_io, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        content = content_io.getvalue()
        return content

    def create_folder(
            self,
            name: str,
            parent_folder: DriveFolder | str = 'root',
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
        """
        if isinstance(parent_folder, DriveFolder):
            parent_folder = parent_folder.folder_id

        metadata = utils.build_file_metadata(
            name=utils.sanitize_filename(name),
            parents=[parent_folder],
            description=description,
            mimeType=FOLDER_MIME_TYPE
        )

        result = self._service.files().create(
            body=metadata,
            fields=DEFAULT_FILE_FIELDS
        ).execute()

        folder_obj = utils.convert_api_file_to_drive_folder(result)
        return folder_obj

    def delete(self, item: DriveItem) -> bool:
        """
        Delete a file or folder from Drive.

        Args:
            item: DriveItem object to delete

        Returns:
            True if deletion was successful

        """
        if isinstance(item, DriveItem):
            item = item.item_id
        self._service.files().delete(fileId=item).execute()
        return True

    def copy(
            self,
            item: DriveItem | str,
            destination_folder: DriveFolder | str,
            new_name: Optional[str] = None
    ) -> DriveItem:
        """
        Copy a file or folder in Drive.

        Args:
            item: DriveItem object to copy
            new_name: Name for the copied item
            destination_folder: Parent DriveFolder for the copy

        Returns:
            DriveItem object for the copied item
        """
        if isinstance(item, DriveItem):
            item = item.item_id
        if isinstance(destination_folder, DriveFolder):
            destination_folder = destination_folder.folder_id

        metadata = {}
        if new_name:
            metadata['name'] = utils.sanitize_filename(new_name)
        if destination_folder:
            metadata['parents'] = [destination_folder]

        result = self._service.files().copy(
            fileId=item,
            body=metadata,
            fields=DEFAULT_FILE_FIELDS
        ).execute()

        copied_item = utils.convert_api_file_to_correct_type(result)
        return copied_item

    def rename(
            self,
            item: DriveItem | str,
            name: str
    ) -> DriveItem:
        """
        Rename a file or folder in Drive.

        Args:
            item: DriveItem object to update
            name: New name for the item

        Returns:
            Updated DriveItem object
        """
        if isinstance(item, DriveItem):
            item = item.item_id

        result = self._service.files().update(
            fileId=item,
            body={'name': utils.sanitize_filename(name)},
            fields=DEFAULT_FILE_FIELDS
        ).execute()

        updated_item = utils.convert_api_file_to_correct_type(result)
        return updated_item

    def share(
            self,
            item: DriveItem | str,
            email: str,
            role: str = "reader",
            notify: bool = True,
            message: Optional[str] = None
    ) -> Permission:
        """
        Share a file or folder with a user.

        Args:
            item: DriveItem object or item_id to share
            email: Email address of the user to share with
            role: Permission role (reader, writer, commenter)
            notify: Whether to send notification email
            message: Custom message to include in notification

        Returns:
            Permission object for the created permission
        """
        if isinstance(item, DriveItem):
            item = item.item_id

        permission_metadata = {
            'type': 'user',
            'role': role,
            'emailAddress': email
        }

        result = self._service.permissions().create(
            fileId=item,
            body=permission_metadata,
            sendNotificationEmail=notify,
            emailMessage=message,
            fields='*'
        ).execute()

        permission = utils.convert_api_permission_to_permission(result)
        return permission

    def get_permissions(self, item: DriveItem | str) -> List[Permission]:
        """
        Get all permissions for a file or folder.

        Args:
            item: DriveItem object to get permissions for

        Returns:
            List of Permission objects
        """
        if isinstance(item, DriveItem):
            item = item.item_id

        result = self._service.permissions().list(
            fileId=item,
            fields='permissions(*)'
        ).execute()

        permissions = [utils.convert_api_permission_to_permission(perm) for perm in result.get('permissions', [])]
        return permissions

    def remove_permission(self, item: DriveItem | str, permission_id: str) -> bool:
        """
        Remove a permission from a file or folder.

        Args:
            item: DriveItem object to remove permission from
            permission_id: ID of the permission to remove

        Returns:
            True if removal was successful
        """
        if isinstance(item, DriveItem):
            item = item.item_id

        self._service.permissions().delete(
            fileId=item,
            permissionId=permission_id
        ).execute()
        return True

    def list_folder_contents(
            self,
            folder: DriveFolder | str,
            include_folders: bool = True,
            include_files: bool = True,
            max_results: Optional[int] = 100,
            order_by: Optional[str] = None
    ) -> List[DriveItem]:
        """
        List all contents (files and/or folders) within a specific folder.

        Args:
            folder: DriveFolder object representing the folder or the folder_id
            include_folders: Whether to include subfolders in results
            include_files: Whether to include files in results
            max_results: Maximum number of items to return
            order_by: Field to order results by
        """

        if isinstance(folder, DriveFolder):
            folder = folder.folder_id

        query_builder = self.query().in_folder(folder)

        if include_folders and not include_files:
            query_builder = query_builder.folders_only()
        elif include_files and not include_folders:
            query_builder = query_builder.files_only()

        if max_results:
            query_builder = query_builder.limit(max_results)

        if order_by:
            query_builder = query_builder.order_by(order_by)

        contents = query_builder.execute()

        return contents

    def move(
            self,
            item: DriveItem | str,
            target_folder: DriveFolder | str,
            remove_from_current_parents: bool = True
    ) -> DriveItem:
        """
        Move a file or folder to a different parent folder.

        Args:
            item: DriveItem object or DriveItem id to move
            target_folder: Target DriveFolder or folder_id
            remove_from_current_parents: Whether to remove from current parents

        Returns:
            Updated DriveItem object
        """
        if isinstance(item, str):
            item = self.get(item)
        if isinstance(target_folder, DriveFolder):
            target_folder = target_folder.folder_id

        update_params = {
            'fileId': item.item_id,
            'addParents': target_folder,
            'fields': DEFAULT_FILE_FIELDS
        }

        if remove_from_current_parents and item.parent_ids:
            update_params['removeParents'] = ','.join(item.parent_ids)

        result = self._service.files().update(**update_params).execute()

        updated_item = utils.convert_api_file_to_correct_type(result)
        return updated_item

    def get_parent_folder(self, item: DriveItem | str) -> Optional[DriveFolder]:
        """
        Get the parent folder of a file or folder.

        Args:
            item: DriveItem object or DriveItem id to get parent for

        Returns:
            Parent DriveFolder, or None if no parent
        """
        if isinstance(item, str):
            item = self.get(item)

        if not (parent_id := item.get_parent_folder_id()):
            return None

        result = self._service.files().get(
            fileId=parent_id,
            fields=DEFAULT_FILE_FIELDS
        ).execute()

        parent_folder = utils.convert_api_file_to_drive_folder(result)
        return parent_folder

    def get_folder_by_path(self, path: str, root_folder_id: str = "root") -> Optional[DriveFolder]:
        """
        Find a folder by its path relative to a root folder.

        Args:
            path: Folder path like "/Documents/Projects" or "Documents/Projects"
            root_folder_id: ID of the root folder to start from (default: Drive root)

        Returns:
            DriveFolder object for the folder, or None if not found
        """
        folder_names = utils.parse_folder_path(path)
        if not folder_names:
            try:
                result = self._service.files().get(
                    fileId=root_folder_id,
                    fields=DEFAULT_FILE_FIELDS
                ).execute()
                return utils.convert_api_file_to_drive_folder(result)
            except Exception:
                return None

        current_folder_id = root_folder_id

        for folder_name in folder_names:
            folders = (self.query()
                       .in_folder(current_folder_id)
                       .folders_named(folder_name)
                       .limit(1)
                       .execute())

            if not folders:
                return None

            current_folder_id = folders[0].folder_id

        result = self._service.files().get(
            fileId=current_folder_id,
            fields=DEFAULT_FILE_FIELDS
        ).execute()

        final_folder = utils.convert_api_file_to_drive_folder(result)
        return final_folder

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
        """
        folder_names = utils.parse_folder_path(path)
        if not folder_names:
            raise ValueError("Invalid folder path")

        current_folder_id = root_folder_id

        for i, folder_name in enumerate(folder_names):
            existing_folders = (self.query()
                                .in_folder(current_folder_id)
                                .folders_named(folder_name)
                                .limit(1)
                                .execute())

            if existing_folders:
                current_folder_id = existing_folders[0].item_id
            else:
                folder_desc = description if i == len(folder_names) - 1 else None
                if current_folder_id == root_folder_id:
                    parent_folder = None
                else:
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

        result = self._service.files().get(
            fileId=current_folder_id,
            fields=DEFAULT_FILE_FIELDS
        ).execute()

        final_folder = utils.convert_api_file_to_drive_folder(result)
        return final_folder

    def move_to_trash(self, item: DriveItem | str) -> DriveItem:
        """
        Move a file or folder to trash.
        Args:
            item: DriveItem object or item_id to move to trash
        Returns:
            Updated DriveItem object
        """
        if isinstance(item, DriveItem):
            item = item.item_id
        result = self._service.files().update(
            fileId=item,
            body={'trashed': True},
            fields=DEFAULT_FILE_FIELDS
        ).execute()

        updated_item = utils.convert_api_file_to_correct_type(result)
        return updated_item

    def get_directory_tree(
            self,
            folder: DriveFolder | str = 'root',
            max_depth: int = 3,
            include_files: bool = True
    ) -> Dict[str, Any]:
        """
        Get directory tree structure as nested dictionary.

        Args:
            folder: DriveFolder to get tree structure for
            max_depth: Maximum depth to traverse (prevents infinite loops)
            include_files: Whether to include files in the tree

        Returns:
            Nested dictionary representing the tree structure
        """
        if isinstance(folder, str):
            folder = self.get(folder)

        def _build_tree_recursive(current_folder: DriveFolder, current_depth: int) -> Dict[str, Any]:
            # Build current node
            node = {
                'name': current_folder.name,
                'type': 'folder',
                'id': current_folder.folder_id,
                'size': None,
                'children': []
            }

            # Stop recursion if max depth reached
            if current_depth >= max_depth:
                return node

            try:
                # Get folder contents
                contents = self.list_folder_contents(
                    current_folder,
                    include_folders=True,
                    include_files=include_files,
                    max_results=1000
                )

                # Process each item
                for item in contents:
                    if isinstance(item, DriveFolder):
                        # Recursively build subtree for folders
                        child_node = _build_tree_recursive(item, current_depth + 1)
                        node['children'].append(child_node)
                    elif isinstance(item, DriveFile) and include_files:
                        # Add file node
                        file_node = {
                            'name': item.name,
                            'type': 'file',
                            'id': item.file_id,
                            'size': item.size,
                            'children': None
                        }
                        node['children'].append(file_node)

            except (FolderNotFoundError, PermissionDeniedError) as e:
                # Handle permission errors gracefully
                node['children'] = None
                node['error'] = str(e)

            return node

        tree = _build_tree_recursive(folder, 0)
        return tree

    def print_directory_tree(
            self,
            folder: DriveFolder | str = 'root',
            max_depth: int = 3,
            show_files: bool = True,
            show_sizes: bool = True,
            show_dates: bool = False,
            _current_depth: int = 0,
            _prefix: str = ""
    ) -> None:
        """
        Print visual tree representation of folder structure.

        Args:
            folder: DriveFolder to print tree structure for
            max_depth: Maximum depth to traverse
            show_files: Whether to include files in the output
            show_sizes: Whether to show file sizes
            show_dates: Whether to show modification dates
            _current_depth: Internal parameter for recursion
            _prefix: Internal parameter for tree formatting
        """
        if isinstance(folder, str):
            folder = self.get(folder)

        # Print current folder
        if _current_depth == 0:
            print(f"📁 {folder.name}/")

        # Stop recursion if max depth reached
        if _current_depth >= max_depth:
            return

        # Get folder contents
        contents = self.list_folder_contents(
            folder,
            include_folders=True,
            include_files=show_files,
            max_results=1000,
            order_by="name"
        )

        # Sort contents: folders first, then files
        folders = [item for item in contents if isinstance(item, DriveFolder)]
        files = [item for item in contents if isinstance(item, DriveFile)]
        sorted_contents = folders + files

        for i, item in enumerate(sorted_contents):
            is_last = (i == len(sorted_contents) - 1)

            # Choose tree characters
            if is_last:
                current_prefix = _prefix + "└── "
                next_prefix = _prefix + "    "
            else:
                current_prefix = _prefix + "├── "
                next_prefix = _prefix + "│   "

            # Format item display
            if isinstance(item, DriveFolder):
                # Folder display
                display_name = f"📁 {item.name}/"
                print(current_prefix + display_name)

                # Recursively print subfolder
                self.print_directory_tree(
                    item,
                    max_depth=max_depth,
                    show_files=show_files,
                    show_sizes=show_sizes,
                    show_dates=show_dates,
                    _current_depth=_current_depth + 1,
                    _prefix=next_prefix
                )

            elif isinstance(item, DriveFile):
                # File display
                display_parts = [f"📄 {item.name}"]

                if show_sizes and item.size is not None:
                    display_parts.append(f"({item.human_readable_size()})")

                if show_dates and item.modified_time:
                    readable_date = datetime_to_readable(item.modified_time)
                    display_parts.append(f"[{readable_date}]")

                display_name = " ".join(display_parts)
                print(current_prefix + display_name)
