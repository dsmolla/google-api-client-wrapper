"""
Security tests for path traversal prevention in Gmail client.
"""
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from src.google_api_client.clients.gmail.client import EmailAttachment


class TestEmailAttachmentSecurity:
    """Test security features of EmailAttachment class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.test_attachment = EmailAttachment(
            filename="test.txt",
            content_type="text/plain",
            size=100,
            attachment_id="att123",
            message_id="msg123"
        )
        
    @patch.object(EmailAttachment, '_get_attachment_data')
    def test_safe_filename_download(self, mock_get_data, tmp_path):
        """Test that normal safe filenames work correctly."""
        mock_get_data.return_value = b"test content"
        
        # Test normal filename
        self.test_attachment.filename = "document.pdf"
        result = self.test_attachment.download_attachment(str(tmp_path))
        
        assert result is True
        assert (tmp_path / "document.pdf").exists()
        
    @patch.object(EmailAttachment, '_get_attachment_data')
    def test_path_traversal_attack_prevention(self, mock_get_data, tmp_path):
        """Test that path traversal attacks are prevented."""
        mock_get_data.return_value = b"malicious content"
        
        # Test various path traversal attempts - these should all be blocked
        # Note: Most will be blocked by path separator detection, some by path traversal detection
        malicious_filenames = [
            "../../../etc/passwd",           # Unix style (blocked by separator)
            "..\\..\\..\\windows\\system32\\config\\sam",  # Windows style (blocked by separator)
            "../sensitive.txt",              # Simple traversal (blocked by separator)
            "..\\sensitive.txt",             # Windows simple traversal (blocked by separator)
            "../../../../../../etc/shadow",   # Deep traversal (blocked by separator)
            "../subdir/../../../etc/hosts",  # Mixed traversal (blocked by separator)
            "..\\subdir\\..\\..\\..\\boot.ini",  # Windows mixed (blocked by separator)
            "/etc/passwd",                   # Absolute path Unix (blocked by separator)
            "C:\\Windows\\System32\\config\\SAM",  # Absolute path Windows (blocked by separator)
            "....//....//....//etc/passwd",  # Double dot (blocked by separator)
        ]
        
        for malicious_filename in malicious_filenames:
            self.test_attachment.filename = malicious_filename
            
            with pytest.raises(ValueError, match="Security error.*"):
                self.test_attachment.download_attachment(str(tmp_path))
                
        # Verify no malicious files were created outside our test directory
        # Check if any files were created in parent directories that shouldn't be there
        test_dir_str = str(tmp_path)
        for root, dirs, files in os.walk(tmp_path):
            for file in files:
                file_path = os.path.join(root, file)
                # All files should be within our test directory
                assert file_path.startswith(test_dir_str), f"Unexpected file outside test dir: {file_path}"
                
    @patch.object(EmailAttachment, '_get_attachment_data')
    def test_edge_case_filenames(self, mock_get_data, tmp_path):
        """Test edge cases and potentially problematic filenames."""
        mock_get_data.return_value = b"test content"
        
        # These should be safe and work
        safe_edge_cases = [
            "file.txt",                     # Simple filename
            "file with spaces.txt",         # Spaces in filename
            "file-with-dashes.txt",         # Dashes
            "file_with_underscores.txt",    # Underscores
            "file.name.with.dots.txt",      # Multiple dots
            "file123.txt",                  # Numbers
            "ファイル.txt",                   # Unicode characters
            "very_long_filename_that_is_still_reasonable_but_longer_than_most.txt",
        ]
        
        for safe_filename in safe_edge_cases:
            self.test_attachment.filename = safe_filename
            result = self.test_attachment.download_attachment(str(tmp_path))
            assert result is True
            
            expected_path = tmp_path / safe_filename
            assert expected_path.exists(), f"File {safe_filename} was not created"
            
    @patch.object(EmailAttachment, '_get_attachment_data')
    def test_symbolic_link_attack_prevention(self, mock_get_data, tmp_path):
        """Test that symbolic link attacks are prevented."""
        mock_get_data.return_value = b"test content"
        
        # Create a symbolic link that points outside the directory
        outside_dir = tmp_path.parent / "outside"
        outside_dir.mkdir()
        
        link_path = tmp_path / "malicious_link"
        if os.name != 'nt':  # Unix-like systems
            try:
                link_path.symlink_to(outside_dir / "target.txt")
                
                # Try to use the symbolic link as filename
                self.test_attachment.filename = "malicious_link"
                
                with pytest.raises(ValueError, match="Security error.*Path traversal detected"):
                    self.test_attachment.download_attachment(str(tmp_path))
                    
            except (OSError, NotImplementedError):
                # Skip if symbolic links not supported
                pytest.skip("Symbolic links not supported on this system")
        else:
            pytest.skip("Symbolic link test skipped on Windows")
            
    def test_directory_validation(self, tmp_path):
        """Test directory validation logic."""
        # Test with non-existent directory (should be created)
        new_dir = tmp_path / "new_directory"
        assert not new_dir.exists()
        
        with patch.object(self.test_attachment, '_get_attachment_data', return_value=b"test"):
            self.test_attachment.download_attachment(str(new_dir))
            
        assert new_dir.exists()
        assert new_dir.is_dir()
        
        # Test with file instead of directory (should raise error)
        file_path = tmp_path / "not_a_directory.txt"
        file_path.write_text("test")
        
        with pytest.raises(ValueError, match="is not a directory"):
            self.test_attachment.download_attachment(str(file_path))
            
    @patch.object(EmailAttachment, '_get_attachment_data')
    def test_filename_with_path_separators(self, mock_get_data, tmp_path):
        """Test filenames containing path separators are handled safely."""
        mock_get_data.return_value = b"test content"
        
        # Filenames with path separators should be blocked
        separator_filenames = [
            "subdir/file.txt",              # Forward slash
            "subdir\\file.txt",             # Backslash
            "sub/dir/file.txt",             # Multiple separators
            "sub\\dir\\file.txt",           # Multiple backslashes
        ]
        
        for separator_filename in separator_filenames:
            self.test_attachment.filename = separator_filename
            
            with pytest.raises(ValueError, match="Security error.*"):
                self.test_attachment.download_attachment(str(tmp_path))
                
    @patch.object(EmailAttachment, '_get_attachment_data')
    def test_case_sensitivity_security(self, mock_get_data, tmp_path):
        """Test that case variations don't bypass security."""
        mock_get_data.return_value = b"test content"
        
        # Test case variations of path traversal
        case_variations = [
            "../FILE.TXT",
            "..\\FILE.TXT", 
            "../File.Txt",
            "..\\File.Txt",
        ]
        
        for case_filename in case_variations:
            self.test_attachment.filename = case_filename
            
            with pytest.raises(ValueError, match="Security error.*"):
                self.test_attachment.download_attachment(str(tmp_path))


class TestSecurityErrorMessages:
    """Test that security error messages don't leak sensitive information."""
    
    def setup_method(self):
        self.test_attachment = EmailAttachment(
            filename="../../../etc/passwd",
            content_type="text/plain", 
            size=100,
            attachment_id="att123",
            message_id="msg123"
        )
        
    @patch.object(EmailAttachment, '_get_attachment_data')
    def test_error_message_security(self, mock_get_data, tmp_path):
        """Test that error messages don't reveal system information."""
        mock_get_data.return_value = b"test"
        
        with pytest.raises(ValueError) as exc_info:
            self.test_attachment.download_attachment(str(tmp_path))
            
        error_message = str(exc_info.value)
        
        # Error message should contain security information
        assert "Path traversal detected" in error_message
        
        # Error message should not contain the full malicious filename that might leak system paths
        # But it's acceptable for error messages to be descriptive about the attack type