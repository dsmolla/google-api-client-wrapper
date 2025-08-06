class GoogleAPIClientError(Exception):
    """Base exception for all Google API client errors."""
    pass


class AuthenticationError(GoogleAPIClientError):
    """Raised when authentication fails."""
    pass


class APIError(GoogleAPIClientError):
    """Raised when API calls fail."""
    pass


class ValidationError(GoogleAPIClientError):
    """Raised when input validation fails."""
    pass