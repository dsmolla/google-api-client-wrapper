from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from src.google_api_client.services.drive.constants import GOOGLE_DOCS_MIME_TYPE, GOOGLE_SHEETS_MIME_TYPE, \
    GOOGLE_SLIDES_MIME_TYPE
from src.google_api_client.utils.datetime import convert_datetime_to_readable


@dataclass
class Permission:
    """
    Represents a permission for a Drive file or folder.
    Args:
        permission_id: The unique identifier for this permission.
        type: The type of permission (user, group, domain, anyone).
        role: The role of the permission (reader, writer, commenter, owner).
        email_address: The email address for user/group permissions.
        domain: The domain name for domain permissions.
        display_name: Display name of the person/group.
        deleted: Whether this permission has been deleted.
    """
    permission_id: Optional[str] = None
    type: Optional[str] = None
    role: Optional[str] = None
    email_address: Optional[str] = None
    domain: Optional[str] = None
    display_name: Optional[str] = None
    deleted: bool = False

    def to_dict(self) -> dict:
        """
        Converts the Permission instance to a dictionary representation.
        Returns:
            A dictionary containing the permission data.
        """
        result = {}
        if self.permission_id:
            result["id"] = self.permission_id
        if self.type:
            result["type"] = self.type
        if self.role:
            result["role"] = self.role
        if self.email_address:
            result["emailAddress"] = self.email_address
        if self.domain:
            result["domain"] = self.domain
        if self.display_name:
            result["displayName"] = self.display_name
        if self.deleted:
            result["deleted"] = self.deleted
        return result

    def __str__(self):
        if self.email_address:
            return f"{self.display_name or self.email_address} ({self.role})"
        elif self.domain:
            return f"Domain: {self.domain} ({self.role})"
        else:
            return f"{self.type} ({self.role})"


@dataclass
class DriveFile:
    """
    Represents a file or folder in Google Drive.
    Args:
        file_id: The unique identifier for the file.
        name: The name of the file.
        mime_type: The MIME type of the file.
        size: The size of the file in bytes (None for folders).
        created_time: When the file was created.
        modified_time: When the file was last modified.
        parents: List of parent folder IDs.
        web_view_link: Link to view the file in Drive web interface.
        web_content_link: Link to download the file content.
        owners: List of file owners.
        permissions: List of file permissions.
        description: Description of the file.
        starred: Whether the file is starred.
        trashed: Whether the file is in the trash.
        shared: Whether the file is shared.
        original_filename: Original filename if different from name.
        file_extension: File extension.
        md5_checksum: MD5 checksum of the file content.
    """
    file_id: Optional[str] = None
    name: Optional[str] = None
    mime_type: Optional[str] = None
    size: Optional[int] = None
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None
    parents: List[str] = field(default_factory=list)
    web_view_link: Optional[str] = None
    web_content_link: Optional[str] = None
    owners: List[str] = field(default_factory=list)
    permissions: List[Permission] = field(default_factory=list)
    description: Optional[str] = None
    starred: bool = False
    trashed: bool = False
    shared: bool = False
    original_filename: Optional[str] = None
    file_extension: Optional[str] = None
    md5_checksum: Optional[str] = None

    def is_google_doc(self) -> bool:
        """
        Check if this file is a Google Workspace document.
        Returns:
            True if the file is a Google Workspace document.
        """
        google_mime_types = [
            GOOGLE_DOCS_MIME_TYPE,
            GOOGLE_SHEETS_MIME_TYPE,
            GOOGLE_SLIDES_MIME_TYPE,
            "application/vnd.google-apps.drawing",
            "application/vnd.google-apps.form",
        ]
        return self.mime_type in google_mime_types

    def human_readable_size(self) -> str:
        """
        Get human-readable file size.
        Returns:
            Size in human-readable format (e.g., "1.2 MB").
        """
        if self.size is None:
            return "Unknown"
        
        if self.size == 0:
            return "0 B"
        
        size = self.size
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.1f} {units[unit_index]}"

    def get_parent_folder_id(self) -> Optional[str]:
        """
        Get the first parent folder ID.
        Returns:
            The first parent folder ID, or None if no parents.
        """
        return self.parents[0] if self.parents else None

    def has_parent(self) -> bool:
        """
        Check if this file/folder has a parent folder.
        Returns:
            True if file has at least one parent folder.
        """
        return bool(self.parents)

    def get_all_parent_ids(self) -> List[str]:
        """
        Get all parent folder IDs.
        Returns:
            List of all parent folder IDs.
        """
        return self.parents.copy()

    def is_in_folder(self, folder_id: str) -> bool:
        """
        Check if this file/folder is in a specific parent folder.
        Args:
            folder_id: ID of the folder to check
        Returns:
            True if this file is in the specified folder.
        """
        return folder_id in self.parents

    def to_dict(self) -> dict:
        """
        Converts the DriveFile instance to a dictionary representation.
        Returns:
            A dictionary containing the file data.
        """
        result = {}
        if self.file_id:
            result["id"] = self.file_id
        if self.name:
            result["name"] = self.name
        if self.mime_type:
            result["mimeType"] = self.mime_type
        if self.size is not None:
            result["size"] = str(self.size)
        if self.created_time:
            result["createdTime"] = self.created_time.isoformat() + "Z"
        if self.modified_time:
            result["modifiedTime"] = self.modified_time.isoformat() + "Z"
        if self.parents:
            result["parents"] = self.parents
        if self.web_view_link:
            result["webViewLink"] = self.web_view_link
        if self.web_content_link:
            result["webContentLink"] = self.web_content_link
        if self.description:
            result["description"] = self.description
        if self.permissions:
            result["permissions"] = [p.to_dict() for p in self.permissions]
        
        result.update({
            "starred": self.starred,
            "trashed": self.trashed,
            "shared": self.shared,
        })
        
        return result

    def __str__(self):
        size_str = f"({self.human_readable_size()})"
        return f"{self.name} {size_str}"

    def __repr__(self):
        return f"DriveFile(id={self.file_id!r}, name={self.name!r}, mime_type={self.mime_type!r})"


@dataclass
class DriveComment:
    """
    Represents a comment on a Drive file.
    Args:
        comment_id: The unique identifier for the comment.
        content: The plain text content of the comment.
        author: The author of the comment.
        created_time: When the comment was created.
        modified_time: When the comment was last modified.
        deleted: Whether the comment has been deleted.
        resolved: Whether the comment has been resolved.
        anchor: The region of the document that this comment is anchored to.
    """
    comment_id: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None
    deleted: bool = False
    resolved: bool = False
    anchor: Optional[str] = None

    def to_dict(self) -> dict:
        """
        Converts the DriveComment instance to a dictionary representation.
        Returns:
            A dictionary containing the comment data.
        """
        result = {}
        if self.comment_id:
            result["id"] = self.comment_id
        if self.content:
            result["content"] = self.content
        if self.author:
            result["author"] = self.author
        if self.created_time:
            result["createdTime"] = self.created_time.isoformat() + "Z"
        if self.modified_time:
            result["modifiedTime"] = self.modified_time.isoformat() + "Z"
        if self.anchor:
            result["anchor"] = self.anchor
        
        result.update({
            "deleted": self.deleted,
            "resolved": self.resolved,
        })
        
        return result

    def __str__(self):
        author_str = f"by {self.author}" if self.author else "by Unknown"
        return f"Comment {author_str}: {self.content[:50]}{'...' if len(self.content or '') > 50 else ''}"


@dataclass
class DriveFolder:
    """
    Represents a folder in Google Drive.
    Args:
        folder_id: The unique identifier for the folder.
        name: The name of the folder.
        created_time: When the folder was created.
        modified_time: When the folder was last modified.
        parents: List of parent folder IDs.
        web_view_link: Link to view the folder in Drive web interface.
        owners: List of folder owners.
        permissions: List of folder permissions.
        description: Description of the folder.
        starred: Whether the folder is starred.
        trashed: Whether the folder is in the trash.
        shared: Whether the folder is shared.
    """
    folder_id: Optional[str] = None
    name: Optional[str] = None
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None
    parents: List[str] = field(default_factory=list)
    web_view_link: Optional[str] = None
    owners: List[str] = field(default_factory=list)
    permissions: List[Permission] = field(default_factory=list)
    description: Optional[str] = None
    starred: bool = False
    trashed: bool = False
    shared: bool = False

    def get_parent_folder_id(self) -> Optional[str]:
        """
        Get the first parent folder ID.
        Returns:
            The first parent folder ID, or None if no parents.
        """
        return self.parents[0] if self.parents else None

    def has_parent(self) -> bool:
        """
        Check if this folder has a parent folder.
        Returns:
            True if folder has at least one parent folder.
        """
        return bool(self.parents)

    def get_all_parent_ids(self) -> List[str]:
        """
        Get all parent folder IDs.
        Returns:
            List of all parent folder IDs.
        """
        return self.parents.copy()

    def is_in_folder(self, folder_id: str) -> bool:
        """
        Check if this folder is in a specific parent folder.
        Args:
            folder_id: ID of the folder to check
        Returns:
            True if this folder is in the specified folder.
        """
        return folder_id in self.parents

    def to_dict(self) -> dict:
        """
        Converts the DriveFolder instance to a dictionary representation.
        Returns:
            A dictionary containing the folder data.
        """
        result = {}
        if self.folder_id:
            result["id"] = self.folder_id
        if self.name:
            result["name"] = self.name
        result["mimeType"] = "application/vnd.google-apps.folder"
        if self.created_time:
            result["createdTime"] = self.created_time.isoformat() + "Z"
        if self.modified_time:
            result["modifiedTime"] = self.modified_time.isoformat() + "Z"
        if self.parents:
            result["parents"] = self.parents
        if self.web_view_link:
            result["webViewLink"] = self.web_view_link
        if self.description:
            result["description"] = self.description
        if self.permissions:
            result["permissions"] = [p.to_dict() for p in self.permissions]
        
        result.update({
            "starred": self.starred,
            "trashed": self.trashed,
            "shared": self.shared,
        })
        
        return result

    def __str__(self):
        return f"[Folder] {self.name}"

    def __repr__(self):
        return f"DriveFolder(id={self.folder_id!r}, name={self.name!r})"