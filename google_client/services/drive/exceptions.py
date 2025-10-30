

class DriveError(Exception):
    """Base exception for Drive API errors."""
    pass


class FileNotFoundError(DriveError):
    """Raised when a file or folder is not found."""
    pass


class FolderNotFoundError(DriveError):
    """Raised when a folder is not found."""
    pass


class PermissionDeniedError(DriveError):
    """Raised when the user lacks permission for a Drive operation."""
    pass

