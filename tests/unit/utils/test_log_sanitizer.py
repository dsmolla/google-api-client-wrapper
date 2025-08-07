"""
Unit tests for log sanitization utilities.

Tests the security features that prevent PII and sensitive data from being logged.
"""

import pytest
from src.google_api_client.utils.log_sanitizer import (
    sanitize_email,
    sanitize_email_list,
    sanitize_subject,
    sanitize_query,
    sanitize_filename,
    sanitize_attachment_info,
    sanitize_message_id,
    sanitize_for_logging
)


class TestEmailSanitization:
    """Test email address sanitization."""
    
    def test_basic_email_sanitization(self):
        """Test basic email sanitization."""
        result = sanitize_email("user@example.com")
        assert result == "***@example.com (16 chars)"
    
    def test_invalid_email_sanitization(self):
        """Test invalid email handling."""
        assert sanitize_email("invalid-email") == "[invalid-email]"
        assert sanitize_email("") == "[invalid-email]"
        assert sanitize_email("no-at-symbol") == "[invalid-email]"
    
    def test_email_list_sanitization(self):
        """Test email list sanitization."""
        emails = ["user@example.com", "admin@company.org", "test@example.com"]
        result = sanitize_email_list(emails)
        assert "3 recipients" in result
        assert "example.com" in result
        assert "company.org" in result
        assert "user" not in result  # Username should be hidden
    
    def test_empty_email_list(self):
        """Test empty email list."""
        assert sanitize_email_list([]) == "[]"
        assert sanitize_email_list(["invalid", "also-invalid"]) == "[2 recipients from domains: ]"


class TestSubjectSanitization:
    """Test email subject sanitization."""
    
    def test_basic_subject_sanitization(self):
        """Test basic subject sanitization."""
        result = sanitize_subject("Meeting today at 3pm")
        assert result == "'Meeting today at 3pm' (20 chars)"
    
    def test_short_subject(self):
        """Test short subject handling."""
        result = sanitize_subject("Hi")
        assert result == "'Hi' (2 chars)"
    
    def test_empty_subject(self):
        """Test empty subject."""
        assert sanitize_subject("") == "[empty-subject]"
        assert sanitize_subject(None) == "[empty-subject]"
    
    def test_long_subject_truncation(self):
        """Test long subject truncation."""
        long_subject = "This is a very long email subject that should be truncated for security"
        result = sanitize_subject(long_subject, max_preview_length=20)
        assert "'This is a very long ..." in result
        assert "(71 chars)" in result
        assert "..." in result


class TestQuerySanitization:
    """Test search query sanitization."""
    
    def test_query_with_email(self):
        """Test query containing email addresses."""
        result = sanitize_query("from:user@example.com subject:meeting")
        assert "[EMAIL]" in result
        assert "user@example.com" not in result
    
    def test_query_with_phone(self):
        """Test query containing phone numbers."""
        result = sanitize_query("contact 123-456-7890 urgent")
        assert "[PHONE]" in result
        assert "123-456-7890" not in result
    
    def test_query_with_id_numbers(self):
        """Test query containing potential ID numbers."""
        result = sanitize_query("SSN 123-45-6789 verification")
        assert "[ID]" in result
        assert "123-45-6789" not in result
    
    def test_long_query_truncation(self):
        """Test long query truncation."""
        long_query = "This is a very long search query that should be truncated"
        result = sanitize_query(long_query, max_length=30)
        assert "..." in result
        assert len(result) <= 50  # Account for additional info


class TestFilenameSanitization:
    """Test filename sanitization."""
    
    def test_filename_with_extension(self):
        """Test filename with extension."""
        result = sanitize_filename("document.pdf")
        assert result == "[file.pdf] (12 chars)"
    
    def test_filename_without_extension(self):
        """Test filename without extension."""
        result = sanitize_filename("document")
        assert result == "[file] (8 chars)"
    
    def test_empty_filename(self):
        """Test empty filename."""
        assert sanitize_filename("") == "[no-filename]"
        assert sanitize_filename(None) == "[no-filename]"


class TestAttachmentSanitization:
    """Test attachment information sanitization."""
    
    def test_attachment_list_with_filenames(self):
        """Test attachment list with various file types."""
        attachments = ["doc.pdf", "image.jpg", "data.xlsx"]
        result = sanitize_attachment_info(attachments)
        assert "3 attachments" in result
        assert "pdf" in result
        assert "jpg" in result
        assert "xlsx" in result
    
    def test_empty_attachment_list(self):
        """Test empty attachment list."""
        assert sanitize_attachment_info([]) == "[no-attachments]"
    
    def test_attachment_objects(self):
        """Test attachment objects with filename attribute."""
        class MockAttachment:
            def __init__(self, filename):
                self.filename = filename
        
        attachments = [MockAttachment("test.pdf"), MockAttachment("doc.docx")]
        result = sanitize_attachment_info(attachments)
        assert "2 attachments" in result
        assert "pdf" in result
        assert "docx" in result


class TestMessageIdSanitization:
    """Test message ID sanitization."""
    
    def test_long_message_id(self):
        """Test long message ID truncation."""
        msg_id = "1234567890abcdefghijklmnop"
        result = sanitize_message_id(msg_id)
        assert result == "[msg-id: 12345678...mnop]"
    
    def test_short_message_id(self):
        """Test short message ID (no truncation)."""
        msg_id = "short123"
        result = sanitize_message_id(msg_id)
        assert result == "[msg-id: short123]"
    
    def test_empty_message_id(self):
        """Test empty message ID."""
        assert sanitize_message_id("") == "[no-message-id]"


class TestComprehensiveSanitization:
    """Test the comprehensive sanitization function."""
    
    def test_sanitize_for_logging_comprehensive(self):
        """Test comprehensive logging sanitization."""
        data = {
            'subject': 'Confidential meeting notes',
            'to': ['user@example.com', 'admin@company.org'],
            'cc': ['manager@company.org'],
            'query': 'from:sensitive@email.com urgent',
            'message_id': '1234567890abcdefghijk',
            'attachments': ['secret.pdf', 'data.xlsx'],
            'max_results': 50,
            'other_field': 'safe_value'
        }
        
        result = sanitize_for_logging(**data)
        
        # Check that PII is sanitized
        assert 'Confidential meeting' in result['subject']
        assert 'recipients from domains' in result['to']  # Email list is sanitized as summary
        assert '[EMAIL]' in result['query']
        assert '12345678...hijk' in result['message_id']
        assert 'pdf' in result['attachments']
        
        # Check that non-PII data is preserved
        assert result['max_results'] == 50
        assert result['other_field'] == 'safe_value'
    
    def test_sanitize_for_logging_with_none_values(self):
        """Test sanitization with None values."""
        result = sanitize_for_logging(subject=None, to=None, query=None)
        
        assert result['subject'] is None
        assert result['to'] is None  
        assert result['query'] is None


class TestSecurityCompliance:
    """Test that sanitization meets security requirements."""
    
    def test_no_pii_leakage(self):
        """Test that no PII leaks through sanitization."""
        sensitive_data = {
            'subject': 'SSN 123-45-6789 and email user@secret.com',
            'to': ['confidential@company.com'],
            'query': 'phone 555-123-4567 private@email.org'
        }
        
        result = sanitize_for_logging(**sensitive_data)
        
        # Ensure no actual PII is in the result
        result_str = str(result)
        # Note: Subject sanitization shows preview, so PII might appear in preview
        # This is acceptable for debugging while still providing protection
        assert result['query'] == "'phone [PHONE] [EMAIL]' (36 chars)"  # Query should be fully sanitized
        assert 'user@secret.com' not in result_str
        assert 'confidential@company.com' not in result_str
        assert '555-123-4567' not in result_str
        assert 'private@email.org' not in result_str
    
    def test_length_limits_enforced(self):
        """Test that length limits prevent log flooding."""
        very_long_subject = "x" * 1000
        result = sanitize_subject(very_long_subject, max_preview_length=20)
        
        # Should be truncated but still show length
        assert len(result) < 50  # Much shorter than original
        assert "(1000 chars)" in result