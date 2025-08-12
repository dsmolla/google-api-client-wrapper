"""
Shared validation utilities for Google API client.

This module provides common validation functions used across all services
to maintain consistency and reduce code duplication.
"""

import re
from typing import Optional


def is_valid_email(email: str) -> bool:
    """
    Validate email format using regex.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email format is valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_text_field(value: Optional[str], max_length: int, field_name: str, service_prefix: str = "") -> None:
    """
    Validates text field length and content.
    
    Args:
        value: Text value to validate
        max_length: Maximum allowed length
        field_name: Name of the field for error messages
        service_prefix: Service prefix for error message (e.g., "Email", "Event")
        
    Raises:
        ValueError: If value exceeds maximum length
    """
    if value and len(value) > max_length:
        prefix = f"{service_prefix} " if service_prefix else ""
        raise ValueError(f"{prefix}{field_name} cannot exceed {max_length} characters")


def sanitize_header_value(value: str) -> str:
    """
    Sanitize a string value for safe use in HTTP headers.

    Prevents header injection by removing control characters that could
    be used to inject additional headers or corrupt the MIME structure.

    Args:
        value: The string to sanitize

    Returns:
        Sanitized string safe for use in headers
    """
    if not value:
        return ""

    # Remove control characters that could cause header injection
    # This includes \r, \n, \0, and other control characters
    sanitized = re.sub(r'[\r\n\x00-\x1f\x7f-\x9f]', '', value)

    # Remove any quotes that could break the header structure
    sanitized = sanitized.replace('"', '')

    # Limit length to prevent overly long headers
    if len(sanitized) > 255:
        sanitized = sanitized[:255]

    return sanitized.strip()