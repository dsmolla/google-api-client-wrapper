import asyncio
import io
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, BinaryIO

from google.auth.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload, MediaIoBaseDownload

from . import utils
from .constants import DEFAULT_FILE_FIELDS, FOLDER_MIME_TYPE, DEFAULT_CHUNK_SIZE
from .exceptions import FileNotFoundError, FolderNotFoundError, PermissionDeniedError
from .types import DriveFile, DriveFolder, Permission, DriveItem
from .utils import convert_mime_type_to_downloadable
from ...utils.datetime import datetime_to_readable


class AsyncDriveApiService:
    """
    Async service layer for Drive API operations.
    Contains all Drive API functionality following the user-centric approach.
    """

    def __init__(self, credentials: Credentials, timezone: str = "UTC"):
        self._executor = ThreadPoolExecutor()
        self._credentials = credentials
        self._timezone = timezone

    def __del__(self):
        """Cleanup ThreadPoolExecutor on deletion."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)

    def _service(self):
        return build("drive", "v3", credentials=self._credentials)

    def query(self):
        from .async_query_builder import AsyncDriveQueryBuilder
        return AsyncDriveQueryBuilder(self, self._timezone)

    async def list(
            self,
            query: Optional[str] = None,
            max_results: Optional[int] = 100,
            order_by: Optional[str] = None
    ) -> List[DriveItem]:
        if max_results < 1:
            raise ValueError(f"max_results must be at least 1")

        request_params = {'pageSize': max_results}

        if query:
            request_params['q'] = query
        if order_by:
            request_params['orderBy'] = order_by

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().files().list(**request_params).execute()
        )

        items = [utils.convert_api_file_to_correct_type(file_data) for file_data in result.get('files', [])]
        while result.get('nextPageToken') and len(items) < max_results:
            request_params['pageSize'] = max_results - len(items)
            result = await loop.run_in_executor(
                self._executor,
                lambda: self._service().files().list(**request_params).execute()
            )
            items.extend([utils.convert_api_file_to_correct_type(file_data) for file_data in result.get('files', [])])

        return items

    async def get(self, item_id: str, fields: Optional[str] = None) -> DriveItem:
        request_params = {
            'fileId': item_id,
            'fields': fields or DEFAULT_FILE_FIELDS
        }

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().files().get(**request_params).execute()
        )
        file_obj = utils.convert_api_file_to_correct_type(result)
        return file_obj

    async def upload_file(
            self,
            file_path: str,
            name: Optional[str] = None,
            parent_folder_id: Optional[str] = None,
            description: Optional[str] = None,
            mime_type: Optional[str] = None
    ) -> DriveFile:
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

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().files().create(
                body=metadata,
                media_body=media,
                fields=DEFAULT_FILE_FIELDS
            ).execute()
        )

        file_obj = utils.convert_api_file_to_drive_file(result)
        return file_obj

    async def upload_file_content(
            self,
            content: Union[str, bytes, BinaryIO],
            name: str,
            parent_folder_id: Optional[str] = None,
            description: Optional[str] = None,
            mime_type: str = "text/plain"
    ) -> DriveFile:
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

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().files().create(
                body=metadata,
                media_body=media,
                fields=DEFAULT_FILE_FIELDS
            ).execute()
        )

        file_obj = utils.convert_api_file_to_drive_file(result)
        return file_obj

    async def download_file(
            self,
            file: DriveFile | str,
            destination_folder: str = str(Path.home() / "Downloads" / "DriveFiles"),
            file_name: str = None
    ) -> str:
        destination_folder = Path(destination_folder)
        destination_folder.mkdir(parents=True, exist_ok=True)

        if isinstance(file, str):
            file = await self.get(file)

        if not file_name:
            file_name = file.name
        file_path = str(destination_folder.joinpath(file_name))
        with open(file_path, "wb") as f:
            f.write(await self.get_file_payload(file))

        return file_path

    async def get_file_payload(self, file: DriveFile | str) -> bytes:
        if isinstance(file, str):
            file = await self.get(file)

        def _download():
            content_io = io.BytesIO()
            if file.is_google_doc():
                request = self._service().files().export_media(
                    fileId=file.file_id, mimeType=convert_mime_type_to_downloadable(file.mime_type)
                )
            else:
                request = self._service().files().get_media(fileId=file.file_id)

            downloader = MediaIoBaseDownload(content_io, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

            return content_io.getvalue()

        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(self._executor, _download)
        return content

    async def create_folder(
            self,
            name: str,
            parent_folder: DriveFolder | str = 'root',
            description: Optional[str] = None
    ) -> DriveFolder:
        if isinstance(parent_folder, DriveFolder):
            parent_folder = parent_folder.folder_id

        metadata = utils.build_file_metadata(
            name=utils.sanitize_filename(name),
            parents=[parent_folder],
            description=description,
            mimeType=FOLDER_MIME_TYPE
        )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().files().create(
                body=metadata,
                fields=DEFAULT_FILE_FIELDS
            ).execute()
        )

        folder_obj = utils.convert_api_file_to_drive_folder(result)
        return folder_obj

    async def delete(self, item: DriveItem | str) -> bool:
        if isinstance(item, DriveItem):
            item = item.item_id
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor,
            lambda: self._service().files().delete(fileId=item).execute()
        )
        return True

    async def copy(
            self,
            item: DriveItem | str,
            destination_folder: DriveFolder | str,
            new_name: Optional[str] = None
    ) -> DriveItem:
        if isinstance(item, DriveItem):
            item = item.item_id
        if isinstance(destination_folder, DriveFolder):
            destination_folder = destination_folder.folder_id

        metadata = {}
        if new_name:
            metadata['name'] = utils.sanitize_filename(new_name)
        if destination_folder:
            metadata['parents'] = [destination_folder]

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().files().copy(
                fileId=item.item_id,
                body=metadata,
                fields=DEFAULT_FILE_FIELDS
            ).execute()
        )

        copied_item = utils.convert_api_file_to_correct_type(result)
        return copied_item

    async def rename(
            self,
            item: DriveItem | str,
            name: str,
    ) -> DriveItem:
        if isinstance(item, DriveItem):
            item = item.item_id

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().files().update(
                fileId=item,
                body={'name': utils.sanitize_filename(name)},
                fields=DEFAULT_FILE_FIELDS
            ).execute()
        )

        updated_item = utils.convert_api_file_to_correct_type(result)
        return updated_item

    async def share(
            self,
            item: DriveItem | str,
            email: str,
            role: str = "reader",
            notify: bool = True,
            message: Optional[str] = None
    ) -> Permission:
        if isinstance(item, DriveItem):
            item = item.item_id

        permission_metadata = {
            'type': 'user',
            'role': role,
            'emailAddress': email
        }

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().permissions().create(
                fileId=item,
                body=permission_metadata,
                sendNotificationEmail=notify,
                emailMessage=message,
                fields='*'
            ).execute()
        )

        permission = utils.convert_api_permission_to_permission(result)
        return permission

    async def get_permissions(self, item: DriveItem | str) -> List[Permission]:
        if isinstance(item, DriveItem):
            item = item.item_id

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().permissions().list(
                fileId=item,
                fields='permissions(*)'
            ).execute()
        )

        permissions = [utils.convert_api_permission_to_permission(perm) for perm in result.get('permissions', [])]
        return permissions

    async def remove_permission(self, item: DriveItem | str, permission_id: str) -> bool:
        if isinstance(item, DriveItem):
            item = item.item_id

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor,
            lambda: self._service().permissions().delete(
                fileId=item,
                permissionId=permission_id
            ).execute()
        )
        return True

    async def list_folder_contents(
            self,
            folder: DriveFolder | str,
            include_folders: bool = True,
            include_files: bool = True,
            max_results: Optional[int] = 100,
            order_by: Optional[str] = None
    ) -> List[DriveItem]:
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

        contents = await query_builder.execute()

        return contents

    async def move(
            self,
            item: DriveItem | str,
            target_folder: DriveFolder,
            remove_from_current_parents: bool = True
    ) -> DriveItem:
        if isinstance(item, str):
            item = await self.get(item)
        if isinstance(target_folder, DriveFolder):
            target_folder = target_folder.folder_id

        update_params = {
            'fileId': item.item_id,
            'addParents': target_folder,
            'fields': DEFAULT_FILE_FIELDS
        }

        if remove_from_current_parents and item.parent_ids:
            update_params['removeParents'] = ','.join(item.parent_ids)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().files().update(**update_params).execute()
        )

        updated_item = utils.convert_api_file_to_correct_type(result)
        return updated_item

    async def get_parent_folder(self, item: DriveItem | str) -> Optional[DriveFolder]:
        if isinstance(item, str):
            item = await self.get(item)

        parent_id = item.get_parent_folder_id()
        if not parent_id:
            return None

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().files().get(
                fileId=parent_id,
                fields=DEFAULT_FILE_FIELDS
            ).execute()
        )

        parent_folder = utils.convert_api_file_to_drive_folder(result)
        return parent_folder

    async def get_folder_by_path(self, path: str, root_folder_id: str = "root") -> Optional[DriveFolder]:

        folder_names = utils.parse_folder_path(path)
        if not folder_names:
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self._executor,
                    lambda: self._service().files().get(
                        fileId=root_folder_id,
                        fields=DEFAULT_FILE_FIELDS
                    ).execute()
                )
                return utils.convert_api_file_to_drive_folder(result)
            except Exception:
                return None

        current_folder_id = root_folder_id

        for folder_name in folder_names:
            folders = await (self.query()
                             .in_folder(current_folder_id)
                             .folders_named(folder_name)
                             .limit(1)
                             .execute())

            if not folders:
                return None

            current_folder_id = folders[0].folder_id

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().files().get(
                fileId=current_folder_id,
                fields=DEFAULT_FILE_FIELDS
            ).execute()
        )

        final_folder = utils.convert_api_file_to_drive_folder(result)
        return final_folder

    async def create_folder_path(
            self,
            path: str,
            root_folder_id: str = "root",
            description: Optional[str] = None
    ) -> DriveFolder:
        folder_names = utils.parse_folder_path(path)
        if not folder_names:
            raise ValueError("Invalid folder path")

        current_folder_id = root_folder_id

        for i, folder_name in enumerate(folder_names):
            existing_folders = await (self.query()
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
                    loop = asyncio.get_event_loop()
                    parent_result = await loop.run_in_executor(
                        self._executor,
                        lambda: self._service().files().get(
                            fileId=current_folder_id,
                            fields=DEFAULT_FILE_FIELDS
                        ).execute()
                    )
                    parent_folder = utils.convert_api_file_to_drive_folder(parent_result)

                new_folder = await self.create_folder(
                    name=folder_name,
                    parent_folder=parent_folder,
                    description=folder_desc
                )
                current_folder_id = new_folder.folder_id

        # Return the final folder
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().files().get(
                fileId=current_folder_id,
                fields=DEFAULT_FILE_FIELDS
            ).execute()
        )

        final_folder = utils.convert_api_file_to_drive_folder(result)
        return final_folder

    async def move_to_trash(self, item: DriveItem | str) -> DriveItem:
        if isinstance(item, DriveItem):
            item = item.item_id

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self._service().files().update(
                fileId=item,
                body={'trashed': True},
                fields=DEFAULT_FILE_FIELDS
            ).execute()
        )

        updated_item = utils.convert_api_file_to_correct_type(result)
        return updated_item

    async def get_directory_tree(
            self,
            folder: DriveFolder | str = 'root',
            max_depth: int = 3,
            include_files: bool = True
    ) -> Dict[str, Any]:
        if isinstance(folder, str):
            folder = await self.get(folder)

        async def _build_tree_recursive(current_folder: DriveFolder, current_depth: int) -> Dict[str, Any]:
            node = {
                'name': current_folder.name,
                'type': 'folder',
                'id': current_folder.folder_id,
                'size': None,
                'children': []
            }

            if current_depth >= max_depth:
                return node

            try:
                contents = await self.list_folder_contents(
                    current_folder,
                    include_folders=True,
                    include_files=include_files,
                    max_results=1000
                )

                for item in contents:
                    if isinstance(item, DriveFolder):
                        child_node = await _build_tree_recursive(item, current_depth + 1)
                        node['children'].append(child_node)
                    elif isinstance(item, DriveFile) and include_files:
                        file_node = {
                            'name': item.name,
                            'type': 'file',
                            'id': item.file_id,
                            'size': item.size,
                            'children': None
                        }
                        node['children'].append(file_node)

            except (FolderNotFoundError, PermissionDeniedError) as e:
                node['children'] = None
                node['error'] = str(e)

            return node

        tree = await _build_tree_recursive(folder, 0)
        return tree

    async def print_directory_tree(
            self,
            folder: DriveFolder | str = 'root',
            max_depth: int = 3,
            show_files: bool = True,
            show_sizes: bool = True,
            show_dates: bool = False,
            _current_depth: int = 0,
            _prefix: str = ""
    ) -> None:
        if isinstance(folder, str):
            folder = await self.get(folder)

        if _current_depth == 0:
            print(f"📁 {folder.name}/")

        if _current_depth >= max_depth:
            return

        contents = await self.list_folder_contents(
            folder,
            include_folders=True,
            include_files=show_files,
            max_results=1000,
            order_by="name"
        )

        folders = [item for item in contents if isinstance(item, DriveFolder)]
        files = [item for item in contents if isinstance(item, DriveFile)]
        sorted_contents = folders + files

        for i, item in enumerate(sorted_contents):
            is_last = (i == len(sorted_contents) - 1)

            if is_last:
                current_prefix = _prefix + "└── "
                next_prefix = _prefix + "    "
            else:
                current_prefix = _prefix + "├── "
                next_prefix = _prefix + "│   "

            if isinstance(item, DriveFolder):
                display_name = f"📁 {item.name}/"
                print(current_prefix + display_name)

                await self.print_directory_tree(
                    item,
                    max_depth=max_depth,
                    show_files=show_files,
                    show_sizes=show_sizes,
                    show_dates=show_dates,
                    _current_depth=_current_depth + 1,
                    _prefix=next_prefix
                )

            elif isinstance(item, DriveFile):
                display_parts = [f"📄 {item.name}"]

                if show_sizes and item.size is not None:
                    display_parts.append(f"({item.human_readable_size()})")

                if show_dates and item.modified_time:
                    readable_date = datetime_to_readable(item.modified_time)
                    display_parts.append(f"[{readable_date}]")

                display_name = " ".join(display_parts)
                print(current_prefix + display_name)
