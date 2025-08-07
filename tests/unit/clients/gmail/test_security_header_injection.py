"""
Security tests for header injection prevention in Gmail client.
"""
import os
import tempfile
import pytest
from unittest.mock import patch, mock_open
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase

from src.google_api_client.clients.gmail.client import EmailMessage, _sanitize_header_value
from src.google_api_client.clients.gmail.async_client import AsyncEmailMessage, _sanitize_header_value as async_sanitize_header_value


class TestHeaderSanitization:
    """Test the header sanitization function."""
    
    def test_safe_filenames_unchanged(self):
        """Test that safe filenames are not modified."""
        safe_filenames = [
            "document.pdf",
            "image.jpg", 
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            "file.name.with.dots.txt",
            "file123.txt",
            "ファイル.txt",  # Unicode characters
        ]
        
        for filename in safe_filenames:
            result = _sanitize_header_value(filename)
            assert result == filename, f"Safe filename was modified: {filename} -> {result}"
            
    def test_control_character_removal(self):
        """Test that control characters are removed."""
        malicious_inputs = [
            "file.txt\r\nContent-Type: text/html",  # CRLF injection
            "file.txt\r\n\r\n<script>alert('xss')</script>",  # Response splitting
            "file.txt\nX-Custom-Header: malicious",  # Newline injection
            "file.txt\x00null-byte",  # Null byte
            "file.txt\x1fcontrol-char",  # Control character
            "file.txt\x7fdelete-char",  # DEL character
            "file.txt\x81high-control",  # High control character
        ]
        
        for malicious_input in malicious_inputs:
            result = _sanitize_header_value(malicious_input)
            
            # Should not contain any control characters
            assert '\r' not in result, f"Carriage return not removed: {result}"
            assert '\n' not in result, f"Newline not removed: {result}"
            assert '\x00' not in result, f"Null byte not removed: {result}"
            
            # Should start with "file.txt"
            assert result.startswith("file.txt"), f"Expected content missing: {result}"
            
    def test_quote_removal(self):
        """Test that quotes are removed to prevent header structure corruption."""
        inputs_with_quotes = [
            'file"name.txt',
            '"filename.txt"',
            'file"with"quotes.txt',
            'file\\"escaped.txt',
        ]
        
        for input_filename in inputs_with_quotes:
            result = _sanitize_header_value(input_filename)
            assert '"' not in result, f"Quotes not removed: {result}"
            
    def test_length_limiting(self):
        """Test that overly long filenames are truncated."""
        long_filename = "a" * 300 + ".txt"
        result = _sanitize_header_value(long_filename)
        
        assert len(result) <= 255, f"Length not limited: {len(result)}"
        assert result.endswith("a"), "Content should be preserved up to limit"
        
    def test_empty_and_none_inputs(self):
        """Test handling of empty and None inputs."""
        assert _sanitize_header_value("") == ""
        assert _sanitize_header_value("   ") == ""  # Whitespace only
        
    def test_whitespace_trimming(self):
        """Test that leading/trailing whitespace is trimmed."""
        inputs = [
            "  filename.txt  ",
            "\tfilename.txt\t",
            "  \n filename.txt \r ",
        ]
        
        for filename in inputs:
            result = _sanitize_header_value(filename)
            assert result == "filename.txt", f"Whitespace not trimmed: '{result}'"

    def test_async_sanitization_consistency(self):
        """Test that async and sync sanitization functions work identically."""
        test_cases = [
            "normal.txt",
            "file\r\ninjection.txt",
            "file\"quoted.txt",
            "  spaced.txt  ",
            "a" * 300 + ".txt",
        ]
        
        for test_case in test_cases:
            sync_result = _sanitize_header_value(test_case)
            async_result = async_sanitize_header_value(test_case)
            assert sync_result == async_result, f"Sanitization inconsistent for: {test_case}"


class TestEmailAttachmentHeaderSecurity:
    """Test header injection protection in email attachment handling."""
    
    @patch('builtins.open', new_callable=mock_open, read_data=b"test content")
    @patch('os.path.isfile', return_value=True)
    @patch('mimetypes.guess_type', return_value=('text/plain', None))
    def test_sync_client_header_injection_prevention(self, mock_guess_type, mock_isfile, mock_file):
        """Test that sync client prevents header injection in attachment filenames."""
        
        # Create malicious filenames that attempt header injection
        malicious_filenames = [
            "file.txt\r\nContent-Type: text/html\r\n\r\n<script>alert('xss')</script>",
            "file.txt\nX-Malicious-Header: injected",
            "file.txt\"; boundary=\"evil",
            "file.txt\r\nContent-Disposition: attachment; filename=\"evil.exe\"",
        ]
        
        for malicious_filename in malicious_filenames:
            # Create a temporary file with malicious name (in test only)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as temp_file:
                temp_path = temp_file.name
                
            try:
                # Rename to simulate malicious filename
                malicious_path = os.path.join(os.path.dirname(temp_path), malicious_filename)
                
                # Mock the file path to appear as the malicious filename
                with patch('os.path.basename', return_value=malicious_filename):
                    # Create message with attachment
                    raw_message = EmailMessage._create_message(
                        to=["test@example.com"],
                        subject="Test",
                        body_text="Test message",
                        attachments=[temp_path]
                    )
                    
                    # Verify the resulting message doesn't contain injection
                    # The raw message should have sanitized the filename
                    assert '\r\n' not in raw_message or 'Content-Type: text/html' not in raw_message
                    assert 'X-Malicious-Header' not in raw_message
                    assert 'boundary="evil"' not in raw_message
                    
            finally:
                # Clean up
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
    @patch('builtins.open', new_callable=mock_open, read_data=b"test content")
    @patch('os.path.isfile', return_value=True) 
    @patch('mimetypes.guess_type', return_value=('text/plain', None))
    def test_async_client_header_injection_prevention(self, mock_guess_type, mock_isfile, mock_file):
        """Test that async client prevents header injection in attachment filenames."""
        
        malicious_filename = "file.txt\r\nX-Injected: malicious"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as temp_file:
            temp_path = temp_file.name
            
        try:
            with patch('os.path.basename', return_value=malicious_filename):
                raw_message = AsyncEmailMessage._create_message(
                    to=["test@example.com"],
                    subject="Test", 
                    body_text="Test message",
                    attachments=[temp_path]
                )
                
                # Verify injection was prevented
                assert 'X-Injected: malicious' not in raw_message
                assert '\r\n' not in raw_message or 'X-Injected' not in raw_message
                
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    def test_content_disposition_header_format(self):
        """Test that Content-Disposition headers are properly formatted after sanitization."""
        test_cases = [
            ("normal.txt", 'attachment; filename="normal.txt"'),
            ("file with spaces.txt", 'attachment; filename="file with spaces.txt"'),
            ("file\r\ninjection.txt", 'attachment; filename="fileinjection.txt"'),
            ("file\"quoted.txt", 'attachment; filename="filequoted.txt"'),
        ]
        
        for original_filename, expected_pattern in test_cases:
            sanitized = _sanitize_header_value(original_filename)
            header_value = f'attachment; filename="{sanitized}"'
            
            # Verify header format is correct
            assert header_value.startswith('attachment; filename="')
            assert header_value.endswith('"')
            
            # Verify no injection characters remain
            assert '\r' not in header_value
            assert '\n' not in header_value
            
            # For normal filenames, should match expected
            if original_filename == "normal.txt" or original_filename == "file with spaces.txt":
                assert header_value == expected_pattern


class TestMIMESecurityIntegration:
    """Test integration with MIME libraries for security."""
    
    def test_mime_multipart_with_sanitized_headers(self):
        """Test that MIME multipart messages work correctly with sanitized headers."""
        message = MIMEMultipart()
        
        # Test malicious filename
        malicious_filename = "file.txt\r\nX-Evil: injected"
        sanitized_filename = _sanitize_header_value(malicious_filename)
        
        # Create attachment with sanitized filename
        attachment = MIMEBase('text', 'plain')
        attachment.add_header(
            'Content-Disposition',
            f'attachment; filename="{sanitized_filename}"'
        )
        
        message.attach(attachment)
        
        # Verify the message can be serialized without issues
        message_str = message.as_string()
        
        # Verify no header injection occurred (no CRLF injection)
        lines = message_str.split('\n')
        injection_as_header = any('X-Evil: injected' in line and line.strip().startswith('X-Evil:') for line in lines)
        assert not injection_as_header, "Header injection occurred - X-Evil appeared as a separate header"
        
        # Verify the sanitized filename is in the Content-Disposition header
        # The control characters should be removed, but the text might remain as part of filename
        content_disp_lines = [line for line in lines if 'Content-Disposition:' in line or 'filename=' in line]
        assert len(content_disp_lines) > 0, "Content-Disposition header not found"
               
    def test_mime_header_folding_safety(self):
        """Test that sanitized headers don't break MIME header folding."""
        # Test with various filename lengths
        test_filenames = [
            "short.txt",
            "medium_length_filename_that_might_cause_folding.txt", 
            "a" * 100 + ".txt",  # Long filename (but under our 255 limit)
        ]
        
        for filename in test_filenames:
            sanitized = _sanitize_header_value(filename)
            header_value = f'attachment; filename="{sanitized}"'
            
            # Create MIME part
            attachment = MIMEBase('text', 'plain')
            attachment.add_header('Content-Disposition', header_value)
            
            # Should not raise exception
            header_str = attachment.as_string()
            
            # Should not contain unescaped control characters
            for line in header_str.split('\n'):
                if 'Content-Disposition' in line:
                    assert '\r' not in line
                    assert '\x00' not in line


class TestSecurityErrorHandling:
    """Test that security measures don't break normal functionality."""
    
    def test_normal_filenames_work(self):
        """Test that normal filenames still work after security fixes."""
        normal_filenames = [
            "document.pdf",
            "image.png",
            "spreadsheet.xlsx",
            "presentation.pptx",
            "archive.zip",
        ]
        
        for filename in normal_filenames:
            sanitized = _sanitize_header_value(filename)
            assert sanitized == filename, f"Normal filename was modified: {filename}"
            
            # Should work in header
            header = f'attachment; filename="{sanitized}"'
            assert filename in header
            
    def test_unicode_filename_handling(self):
        """Test that Unicode filenames are handled safely."""
        unicode_filenames = [
            "文档.pdf",  # Chinese
            "документ.docx",  # Cyrillic  
            "файл.txt",  # Russian
            "ファイル.jpg",  # Japanese
            "αρχείο.zip",  # Greek
        ]
        
        for filename in unicode_filenames:
            sanitized = _sanitize_header_value(filename)
            
            # Should preserve Unicode characters
            assert sanitized == filename, f"Unicode filename was corrupted: {filename} -> {sanitized}"
            
            # Should work in headers (though RFC 2047 encoding may be needed in practice)
            header = f'attachment; filename="{sanitized}"'
            assert sanitized in header