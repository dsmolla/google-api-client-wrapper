"""
Log sanitization utilities to prevent PII and sensitive data leakage.

This module provides functions to sanitize sensitive information before logging,
ensuring compliance with privacy regulations and security best practices.
"""

import re
from typing import Optional, List, Union


def sanitize_email(email: str) -> str:
    """
    Sanitize email address for logging by showing only domain and length.
    
    Args:
        email: Email address to sanitize
        
    Returns:
        Sanitized email representation
        
    Example:
        "user@example.com" -> "***@example.com (15 chars)"
    """
    if not email or '@' not in email:
        return "[invalid-email]"
    
    local_part, domain = email.split('@', 1)
    return f"***@{domain} ({len(email)} chars)"


def sanitize_email_list(emails: List[str]) -> str:
    """
    Sanitize list of email addresses for logging.
    
    Args:
        emails: List of email addresses
        
    Returns:
        Sanitized representation of email list
    """
    if not emails:
        return "[]"
    
    domains = []
    for email in emails:
        if '@' in email:
            domain = email.split('@', 1)[1]
            domains.append(domain)
    
    return f"[{len(emails)} recipients from domains: {', '.join(set(domains))}]"


def sanitize_subject(subject: str, max_preview_length: int = 20) -> str:
    """
    Sanitize email subject for logging.
    
    Args:
        subject: Email subject to sanitize
        max_preview_length: Maximum characters to show from subject
        
    Returns:
        Sanitized subject representation
    """
    if not subject:
        return "[empty-subject]"
    
    # Show first few characters and total length
    preview = subject[:max_preview_length]
    if len(subject) > max_preview_length:
        preview += "..."
    
    return f"'{preview}' ({len(subject)} chars)"


def sanitize_query(query: str, max_length: int = 30) -> str:
    """
    Sanitize search query for logging by removing potential PII.
    
    Args:
        query: Search query to sanitize
        max_length: Maximum length to show
        
    Returns:
        Sanitized query representation
    """
    if not query:
        return "[empty-query]"
    
    # Replace email addresses in query
    sanitized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                      '[EMAIL]', query)
    
    # Replace phone numbers (basic patterns)
    sanitized = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', sanitized)
    
    # Replace potential SSNs or similar ID numbers
    sanitized = re.sub(r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b', '[ID]', sanitized)
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return f"'{sanitized}' ({len(query)} chars)"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for logging.
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        Sanitized filename representation
    """
    if not filename:
        return "[no-filename]"
    
    # Show only extension and length for privacy
    parts = filename.split('.')
    if len(parts) > 1:
        extension = parts[-1].lower()
        return f"[file.{extension}] ({len(filename)} chars)"
    else:
        return f"[file] ({len(filename)} chars)"


def sanitize_attachment_info(attachments: List) -> str:
    """
    Sanitize attachment information for logging.
    
    Args:
        attachments: List of attachment objects or filenames
        
    Returns:
        Sanitized attachment summary
    """
    if not attachments:
        return "[no-attachments]"
    
    count = len(attachments)
    extensions = set()
    
    for attachment in attachments:
        filename = ""
        if hasattr(attachment, 'filename'):
            filename = attachment.filename
        elif isinstance(attachment, str):
            filename = attachment
        
        if filename and '.' in filename:
            ext = filename.split('.')[-1].lower()
            extensions.add(ext)
    
    ext_info = f"types: {', '.join(sorted(extensions))}" if extensions else "unknown types"
    return f"[{count} attachments, {ext_info}]"


def sanitize_message_id(message_id: str) -> str:
    """
    Sanitize message ID for logging.
    
    Args:
        message_id: Message ID to sanitize
        
    Returns:
        Sanitized message ID representation
    """
    if not message_id:
        return "[no-message-id]"
    
    # Show only first 8 and last 4 characters
    if len(message_id) <= 12:
        return f"[msg-id: {message_id}]"
    else:
        return f"[msg-id: {message_id[:8]}...{message_id[-4:]}]"


def sanitize_for_logging(**kwargs) -> dict:
    """
    Sanitize multiple fields for logging in one call.
    
    Args:
        **kwargs: Fields to sanitize (subject, to, cc, query, etc.)
        
    Returns:
        Dictionary with sanitized values
    """
    sanitized = {}
    
    for key, value in kwargs.items():
        if key in ('to', 'cc', 'bcc', 'recipients') and isinstance(value, list):
            sanitized[key] = sanitize_email_list(value)
        elif key == 'subject':
            sanitized[key] = sanitize_subject(value) if value else None
        elif key == 'query':
            sanitized[key] = sanitize_query(value) if value else None
        elif key in ('from', 'sender') and isinstance(value, str):
            sanitized[key] = sanitize_email(value)
        elif key == 'message_id':
            sanitized[key] = sanitize_message_id(value) if value else None
        elif key == 'attachments':
            sanitized[key] = sanitize_attachment_info(value)
        else:
            # For other fields, just include as-is (non-PII data)
            sanitized[key] = value
    
    return sanitized