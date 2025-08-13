

class GmailError(Exception):
    """Base exception for Gmail API errors."""
    pass


class EmailNotFoundError(GmailError):
    """Raised when an email message is not found."""
    pass


class LabelNotFoundError(GmailError):
    """Raised when a Gmail label is not found."""
    pass


class AttachmentNotFoundError(GmailError):
    """Raised when an email attachment is not found."""
    pass


class ThreadNotFoundError(GmailError):
    """Raised when an email thread is not found."""
    pass


class GmailPermissionError(GmailError):
    """Raised when the user lacks permission for a Gmail operation."""
    pass


class GmailQuotaExceededError(GmailError):
    """Raised when Gmail API quota is exceeded."""
    pass


class InvalidEmailFormatError(GmailError):
    """Raised when an email address has invalid format."""
    pass


class MessageTooLargeError(GmailError):
    """Raised when an email message exceeds size limits."""
    pass