from datetime import datetime
from typing import Optional, Dict, Any, List, Union
import mimetypes
import os

from .types import DriveFile, DriveFolder, Permission, DriveComment
from .constants import FOLDER_MIME_TYPE, GOOGLE_DOCS_MIME_TYPE, MICROSOFT_WORD_MIME_TYPE, GOOGLE_SHEETS_MIME_TYPE, \
    MICROSOFT_EXCEL_MIME_TYPE, GOOGLE_SLIDES_MIME_TYPE, MICROSOFT_POWERPOINT_MIME_TYPE


def convert_mime_type_to_downloadable(mime_type: str) -> str:
    mime_type_conversion = {
        GOOGLE_DOCS_MIME_TYPE: MICROSOFT_WORD_MIME_TYPE,
        GOOGLE_SHEETS_MIME_TYPE: MICROSOFT_EXCEL_MIME_TYPE,
        GOOGLE_SLIDES_MIME_TYPE: MICROSOFT_POWERPOINT_MIME_TYPE
    }

    return mime_type_conversion[mime_type]

def convert_api_file_to_drive_file(api_file: Dict[str, Any]) -> DriveFile:
    """
    Convert a file resource from the Drive API to a DriveFile object.
    
    Args:
        api_file: File resource dictionary from Drive API
        
    Returns:
        DriveFile object
    """
    # Parse datetime fields
    created_time = None
    if api_file.get("createdTime"):
        created_time = datetime.fromisoformat(api_file["createdTime"].replace("Z", "+00:00"))
    
    modified_time = None
    if api_file.get("modifiedTime"):
        modified_time = datetime.fromisoformat(api_file["modifiedTime"].replace("Z", "+00:00"))
    
    # Parse size (API returns it as string)
    size = None
    if api_file.get("size"):
        try:
            size = int(api_file["size"])
        except (ValueError, TypeError):
            size = None
    
    # Parse permissions
    permissions = []
    if api_file.get("permissions"):
        for perm_data in api_file["permissions"]:
            permissions.append(convert_api_permission_to_permission(perm_data))
    
    # Extract owners
    owners = []
    if api_file.get("owners"):
        owners = [owner.get("emailAddress", owner.get("displayName", "Unknown")) 
                 for owner in api_file["owners"]]
    
    return DriveFile(
        file_id=api_file.get("id"),
        name=api_file.get("name"),
        mime_type=api_file.get("mimeType"),
        size=size,
        created_time=created_time,
        modified_time=modified_time,
        parents=api_file.get("parents", []),
        web_view_link=api_file.get("webViewLink"),
        web_content_link=api_file.get("webContentLink"),
        owners=owners,
        permissions=permissions,
        description=api_file.get("description"),
        starred=api_file.get("starred", False),
        trashed=api_file.get("trashed", False),
        shared=api_file.get("shared", False),
        original_filename=api_file.get("originalFilename"),
        file_extension=api_file.get("fileExtension"),
        md5_checksum=api_file.get("md5Checksum"),
    )


def convert_api_file_to_drive_folder(api_file: Dict[str, Any]) -> DriveFolder:
    """
    Convert a folder resource from the Drive API to a DriveFolder object.
    
    Args:
        api_file: File resource dictionary from Drive API (must be a folder)
        
    Returns:
        DriveFolder object
    """
    # Parse datetime fields
    created_time = None
    if api_file.get("createdTime"):
        created_time = datetime.fromisoformat(api_file["createdTime"].replace("Z", "+00:00"))
    
    modified_time = None
    if api_file.get("modifiedTime"):
        modified_time = datetime.fromisoformat(api_file["modifiedTime"].replace("Z", "+00:00"))
    
    # Parse permissions
    permissions = []
    if api_file.get("permissions"):
        for perm_data in api_file["permissions"]:
            permissions.append(convert_api_permission_to_permission(perm_data))
    
    # Extract owners
    owners = []
    if api_file.get("owners"):
        owners = [owner.get("emailAddress", owner.get("displayName", "Unknown")) 
                 for owner in api_file["owners"]]
    
    return DriveFolder(
        folder_id=api_file.get("id"),
        name=api_file.get("name"),
        created_time=created_time,
        modified_time=modified_time,
        parents=api_file.get("parents", []),
        web_view_link=api_file.get("webViewLink"),
        owners=owners,
        permissions=permissions,
        description=api_file.get("description"),
        starred=api_file.get("starred", False),
        trashed=api_file.get("trashed", False),
        shared=api_file.get("shared", False),
    )


def convert_api_file_to_correct_type(api_file: Dict[str, Any]) -> Union[DriveFile, DriveFolder]:
    """
    Convert a file/folder resource from the Drive API to the correct type.
    
    Args:
        api_file: File resource dictionary from Drive API
        
    Returns:
        DriveFile or DriveFolder object based on MIME type
    """
    mime_type = api_file.get("mimeType")
    
    if mime_type == FOLDER_MIME_TYPE:
        return convert_api_file_to_drive_folder(api_file)
    else:
        return convert_api_file_to_drive_file(api_file)


def convert_api_permission_to_permission(api_permission: Dict[str, Any]) -> Permission:
    """
    Convert a permission resource from the Drive API to a Permission object.
    
    Args:
        api_permission: Permission resource dictionary from Drive API
        
    Returns:
        Permission object
    """
    return Permission(
        permission_id=api_permission.get("id"),
        type=api_permission.get("type"),
        role=api_permission.get("role"),
        email_address=api_permission.get("emailAddress"),
        domain=api_permission.get("domain"),
        display_name=api_permission.get("displayName"),
        deleted=api_permission.get("deleted", False),
    )


def convert_api_comment_to_comment(api_comment: Dict[str, Any]) -> DriveComment:
    """
    Convert a comment resource from the Drive API to a DriveComment object.
    
    Args:
        api_comment: Comment resource dictionary from Drive API
        
    Returns:
        DriveComment object
    """
    # Parse datetime fields
    created_time = None
    if api_comment.get("createdTime"):
        created_time = datetime.fromisoformat(api_comment["createdTime"].replace("Z", "+00:00"))
    
    modified_time = None
    if api_comment.get("modifiedTime"):
        modified_time = datetime.fromisoformat(api_comment["modifiedTime"].replace("Z", "+00:00"))
    
    # Extract author information
    author = None
    if api_comment.get("author"):
        author_data = api_comment["author"]
        author = author_data.get("displayName") or author_data.get("emailAddress") or "Unknown"
    
    return DriveComment(
        comment_id=api_comment.get("id"),
        content=api_comment.get("content"),
        author=author,
        created_time=created_time,
        modified_time=modified_time,
        deleted=api_comment.get("deleted", False),
        resolved=api_comment.get("resolved", False),
        anchor=api_comment.get("anchor"),
    )


def guess_mime_type(file_path: str) -> str:
    """
    Guess the MIME type of a file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MIME type string
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"


def build_file_metadata(
    name: str,
    parents: Optional[List[str]] = None,
    description: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Build file metadata dictionary for Drive API operations.
    
    Args:
        name: File name
        parents: List of parent folder IDs
        description: File description
        **kwargs: Additional metadata fields
        
    Returns:
        Metadata dictionary
    """
    metadata = {"name": name}
    
    if parents:
        metadata["parents"] = parents
    
    if description:
        metadata["description"] = description
    
    # Add any additional metadata
    metadata.update(kwargs)
    
    return metadata


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to be safe for Drive upload.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Characters that are problematic in Drive
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '/', '\\']
    
    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip('. ')
    
    # Ensure filename is not empty
    if not sanitized:
        sanitized = "untitled"
    
    return sanitized


def format_file_size(size_bytes: Optional[int]) -> str:
    """
    Format file size in bytes to human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string
    """
    if size_bytes is None:
        return "Unknown"
    
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(size_bytes)
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.1f} {units[unit_index]}"


def is_folder_mime_type(mime_type: str) -> bool:
    """
    Check if a MIME type represents a folder.
    
    Args:
        mime_type: MIME type string
        
    Returns:
        True if the MIME type is for a folder
    """
    return mime_type == FOLDER_MIME_TYPE


def build_search_query(*query_parts: str) -> str:
    """
    Build a Drive search query from multiple parts.
    
    Args:
        *query_parts: Query parts to combine
        
    Returns:
        Combined search query
    """
    # Filter out empty query parts
    valid_parts = [part.strip() for part in query_parts if part and part.strip()]
    
    if not valid_parts:
        return ""
    
    # Join with AND operator
    return " and ".join(f"({part})" for part in valid_parts)


def extract_file_id_from_url(url: str) -> Optional[str]:
    """
    Extract file ID from a Google Drive URL.
    
    Args:
        url: Google Drive URL
        
    Returns:
        File ID if found, None otherwise
    """
    # Common Drive URL patterns
    patterns = [
        r"/file/d/([a-zA-Z0-9-_]+)",  # /file/d/FILE_ID/view or /file/d/FILE_ID/edit
        r"/folders/([a-zA-Z0-9-_]+)",  # /folders/FOLDER_ID
        r"id=([a-zA-Z0-9-_]+)",       # ?id=FILE_ID
    ]
    
    import re
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def parse_folder_path(path: str) -> List[str]:
    """
    Parse a folder path into individual folder names.
    
    Args:
        path: Folder path like "/Documents/Projects" or "Documents/Projects"
        
    Returns:
        List of folder names
    """
    if not path:
        return []
    
    # Remove leading/trailing slashes and split
    path = path.strip('/')
    if not path:
        return []
    
    return [name.strip() for name in path.split('/') if name.strip()]


def build_folder_path(folder_names: List[str]) -> str:
    """
    Build a folder path from a list of folder names.
    
    Args:
        folder_names: List of folder names
        
    Returns:
        Folder path string
    """
    if not folder_names:
        return "/"
    
    return "/" + "/".join(folder_names)


def normalize_folder_path(path: str) -> str:
    """
    Normalize a folder path by removing extra slashes and whitespace.
    
    Args:
        path: Raw folder path
        
    Returns:
        Normalized folder path
    """
    if not path:
        return "/"
    
    folder_names = parse_folder_path(path)
    return build_folder_path(folder_names)