

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


class DriveQuotaExceededError(DriveError):
    """Raised when Drive storage quota is exceeded."""
    pass


class FileTooLargeError(DriveError):
    """Raised when a file exceeds size limits."""
    pass


class InvalidFileTypeError(DriveError):
    """Raised when an unsupported file type is used."""
    pass


class UploadFailedError(DriveError):
    """Raised when file upload fails."""
    pass


class DownloadFailedError(DriveError):
    """Raised when file download fails."""
    pass


class SharingError(DriveError):
    """Raised when file sharing operations fail."""
    pass


class DrivePermissionError(DriveError):
    """Raised when permission operations fail."""
    pass


class InvalidQueryError(DriveError):
    """Raised when a Drive search query is invalid."""
    pass