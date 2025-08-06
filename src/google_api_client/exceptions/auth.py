from .base import AuthenticationError


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid or expired."""
    pass


class ScopeError(AuthenticationError):
    """Raised when required OAuth scopes are not granted."""
    pass