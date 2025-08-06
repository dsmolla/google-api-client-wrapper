"""
Unit tests for unified authentication manager.

Tests cover authentication flow, token management, service creation,
and compatibility with both sync and async clients.
"""

import os
import json
import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock, call
from datetime import datetime, timedelta

from src.google_api_client.auth.manager import AuthManager, auth_manager
from google.oauth2.credentials import Credentials
from aiogoogle.auth.creds import UserCreds


class TestAuthManager:
    """Test cases for AuthManager class."""
    
    @pytest.fixture
    def auth_mgr(self):
        """Create a fresh AuthManager instance for testing."""
        # Reset singleton for testing
        AuthManager._instance = None
        AuthManager._credentials = None
        return AuthManager()
    
    @pytest.fixture
    def mock_credentials(self):
        """Create mock OAuth2 credentials."""
        creds = Mock(spec=Credentials)
        creds.valid = True
        creds.expired = False
        creds.token = "mock_token"
        creds.refresh_token = "mock_refresh_token"
        creds.token_uri = "https://oauth2.googleapis.com/token"
        creds.client_id = "mock_client_id"
        creds.client_secret = "mock_client_secret"
        creds.to_json.return_value = json.dumps({
            "token": "mock_token",
            "refresh_token": "mock_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "mock_client_id",
            "client_secret": "mock_client_secret"
        })
        return creds
    
    def test_singleton_pattern(self):
        """Test that AuthManager follows singleton pattern."""
        manager1 = AuthManager()
        manager2 = AuthManager()
        assert manager1 is manager2
        assert manager1 is auth_manager
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.google_api_client.auth.manager.Credentials.from_authorized_user_file')
    def test_get_credentials_from_existing_token(
        self, mock_from_file, mock_file, mock_exists, auth_mgr, mock_credentials
    ):
        """Test loading credentials from existing token file."""
        mock_exists.return_value = True
        mock_from_file.return_value = mock_credentials
        
        result = auth_mgr.get_credentials()
        
        assert result is mock_credentials
        mock_from_file.assert_called_once()
        assert auth_mgr._credentials is mock_credentials
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.google_api_client.auth.manager.Credentials.from_authorized_user_file')
    @patch('src.google_api_client.auth.manager.Request')
    def test_get_credentials_refresh_expired(
        self, mock_request, mock_from_file, mock_file, mock_exists, auth_mgr
    ):
        """Test refreshing expired credentials."""
        mock_exists.return_value = True
        
        expired_creds = Mock(spec=Credentials)
        expired_creds.valid = False
        expired_creds.expired = True
        expired_creds.refresh_token = "refresh_token"
        expired_creds.to_json.return_value = '{"token": "new_token"}'
        
        mock_from_file.return_value = expired_creds
        mock_request_instance = Mock()
        mock_request.return_value = mock_request_instance
        
        # After refresh, make credentials valid
        def refresh_side_effect(request):
            expired_creds.valid = True
            expired_creds.expired = False
            
        expired_creds.refresh.side_effect = refresh_side_effect
        
        result = auth_mgr.get_credentials()
        
        expired_creds.refresh.assert_called_once_with(mock_request_instance)
        assert result.valid
        mock_file.assert_called()  # Token should be saved
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.google_api_client.auth.manager.InstalledAppFlow.from_client_secrets_file')
    @patch('os.makedirs')
    def test_get_credentials_oauth_flow(
        self, mock_makedirs, mock_flow_from_file, mock_file, mock_exists, auth_mgr, mock_credentials
    ):
        """Test OAuth2 flow for new credentials."""
        # First call (token file) returns False, second call (credentials file) returns True
        mock_exists.side_effect = [False, True]
        
        mock_flow = Mock()
        mock_flow.run_local_server.return_value = mock_credentials
        mock_flow_from_file.return_value = mock_flow
        
        result = auth_mgr.get_credentials()
        
        mock_flow.run_local_server.assert_called_once_with(port=8080)
        assert result is mock_credentials
        mock_makedirs.assert_called_once()  # Should create directory
        mock_file.assert_called()  # Should save token
    
    @patch('os.path.exists')
    def test_get_credentials_missing_credentials_file(self, mock_exists, auth_mgr):
        """Test error when credentials file is missing."""
        mock_exists.return_value = False  # Both token and credentials files missing
        
        with pytest.raises(FileNotFoundError, match="Credentials file not found"):
            auth_mgr.get_credentials()
    
    def test_get_user_creds_for_aiogoogle(self, auth_mgr, mock_credentials):
        """Test conversion to aiogoogle UserCreds."""
        with patch.object(auth_mgr, 'get_credentials', return_value=mock_credentials):
            result = auth_mgr.get_user_creds_for_aiogoogle()
            
            assert isinstance(result, UserCreds)
            # Note: Can't easily test the internal values due to UserCreds implementation
    
    @patch('src.google_api_client.auth.manager.build')
    def test_get_sync_service(self, mock_build, auth_mgr, mock_credentials):
        """Test synchronous service creation."""
        with patch.object(auth_mgr, 'get_credentials', return_value=mock_credentials):
            mock_service = Mock()
            mock_build.return_value = mock_service
            
            result = auth_mgr.get_sync_service('gmail', 'v1')
            
            mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_credentials)
            assert result is mock_service
    
    @patch('src.google_api_client.auth.manager.build')
    def test_service_shortcuts(self, mock_build, auth_mgr, mock_credentials):
        """Test service shortcut methods."""
        with patch.object(auth_mgr, 'get_credentials', return_value=mock_credentials):
            mock_service = Mock()
            mock_build.return_value = mock_service
            
            # Test all service shortcuts
            gmail = auth_mgr.get_gmail_service()
            calendar = auth_mgr.get_calendar_service()
            tasks = auth_mgr.get_tasks_service()
            drive = auth_mgr.get_drive_service()
            
            assert gmail is mock_service
            assert calendar is mock_service
            assert tasks is mock_service
            assert drive is mock_service
            
            # Verify correct API calls
            expected_calls = [
                (('gmail', 'v1'), {'credentials': mock_credentials}),
                (('calendar', 'v3'), {'credentials': mock_credentials}),
                (('tasks', 'v1'), {'credentials': mock_credentials}),
                (('drive', 'v3'), {'credentials': mock_credentials})
            ]
            assert mock_build.call_args_list == [
                call(*args, **kwargs) for args, kwargs in expected_calls
            ]
    
    def test_invalidate_cache(self, auth_mgr):
        """Test cache invalidation."""
        # Set some cached values
        auth_mgr._credentials = Mock()
        
        # Call cache_clear manually since we can't easily mock bound method
        auth_mgr.invalidate_cache()
        
        assert auth_mgr._credentials is None
        # Note: Can't easily test LRU cache clear due to bound method
    
    def test_force_refresh(self, auth_mgr, mock_credentials):
        """Test forcing credential refresh."""
        # Set up cached credentials
        auth_mgr._credentials = mock_credentials
        
        with patch.object(auth_mgr, 'get_credentials', wraps=auth_mgr.get_credentials) as mock_get:
            with patch('os.path.exists', return_value=True):
                with patch('src.google_api_client.auth.manager.Credentials.from_authorized_user_file', 
                          return_value=mock_credentials):
                    
                    # First call should use cache
                    result1 = auth_mgr.get_credentials()
                    assert result1 is mock_credentials
                    
                    # Force refresh should ignore cache
                    result2 = auth_mgr.get_credentials(force_refresh=True)
                    assert result2 is mock_credentials
    
    @pytest.mark.asyncio
    async def test_async_service_context_manager(self, auth_mgr):
        """Test async service context managers."""
        with patch.object(auth_mgr, 'get_user_creds_for_aiogoogle') as mock_get_creds:
            mock_creds = Mock()
            mock_get_creds.return_value = mock_creds
            
            # Mock aiogoogle and service
            mock_aiogoogle = Mock()
            mock_service = Mock()
            
            with patch('src.google_api_client.auth.manager.Aiogoogle') as mock_aiogoogle_class:
                mock_aiogoogle_instance = MagicMock()
                mock_aiogoogle_instance.__aenter__.return_value = mock_aiogoogle
                mock_aiogoogle_instance.__aexit__.return_value = None
                mock_aiogoogle_class.return_value = mock_aiogoogle_instance
                
                # Make discover async
                async def mock_discover(service_name, version):
                    return mock_service
                mock_aiogoogle.discover = mock_discover
                
                # Test async Gmail service
                async with auth_mgr.get_async_gmail_service() as (aiogoogle, service):
                    assert aiogoogle is mock_aiogoogle
                    assert service is mock_service
                    # Can't easily assert on async function calls

