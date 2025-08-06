"""
Unified Authentication Manager for Google API Client.

This module provides a centralized authentication system that works with both
synchronous and asynchronous Google API clients. It handles OAuth2 flow,
token storage, refresh, and provides adapters for different client libraries.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from functools import lru_cache
from contextlib import asynccontextmanager, contextmanager

# Google Auth imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Async imports
from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import UserCreds, ClientCreds

logger = logging.getLogger(__name__)

# Configuration
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/tasks",
]

# Allow environment variable override for credentials paths
TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", r"C:\Users\dagms\Projects\Credentials\token.json")
CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", r"C:\Users\dagms\Projects\Credentials\credentials.json")


class AuthManager:
    """
    Unified authentication manager for Google APIs.
    
    Handles OAuth2 authentication, token storage, refresh, and provides
    adapters for both sync and async Google API clients.
    """
    
    _instance = None
    _credentials = None
    _client_creds = None
    
    def __new__(cls):
        """Singleton pattern to ensure single auth instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_credentials(self, force_refresh: bool = False) -> Credentials:
        """
        Get or refresh Google OAuth2 credentials.
        
        Args:
            force_refresh: Force token refresh even if valid
            
        Returns:
            Google OAuth2 Credentials object
        """
        # Use cached credentials if available and valid
        if self._credentials and self._credentials.valid and not force_refresh:
            return self._credentials
            
        logger.info("Loading or refreshing credentials")
        
        creds = None
        
        # Load existing token if available
        if os.path.exists(TOKEN_PATH):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
                logger.info("Loaded credentials from token file")
            except Exception as e:
                logger.warning("Failed to load existing token: %s", e)
        
        # Refresh or obtain new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing expired credentials")
                    creds.refresh(Request())
                except Exception as e:
                    logger.error("Failed to refresh credentials: %s", e)
                    creds = None
            
            # If refresh failed or no credentials, start OAuth flow
            if not creds:
                logger.info("Starting OAuth2 flow")
                if not os.path.exists(CREDENTIALS_PATH):
                    raise FileNotFoundError(
                        f"Credentials file not found at {CREDENTIALS_PATH}. "
                        "Please download it from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=8080)
                logger.info("OAuth2 flow completed successfully")
            
            # Save updated credentials
            try:
                os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
                with open(TOKEN_PATH, "w") as token:
                    token.write(creds.to_json())
                logger.info("Credentials saved to token file")
            except Exception as e:
                logger.error("Failed to save credentials: %s", e)
        
        # Cache the credentials
        self._credentials = creds
        return creds
    
    @lru_cache(maxsize=1)
    def get_user_creds_for_aiogoogle(self) -> UserCreds:
        """
        Get aiogoogle-compatible UserCreds from Google credentials.
        
        Returns:
            UserCreds object for use with aiogoogle
        """
        sync_creds = self.get_credentials()
        
        creds_dict = {
            'access_token': sync_creds.token,
            'refresh_token': sync_creds.refresh_token,
            'token_uri': sync_creds.token_uri,
            'scopes': SCOPES
        }
        
        return UserCreds(**creds_dict)
    
    @lru_cache(maxsize=1)
    def get_client_creds_for_aiogoogle(self) -> ClientCreds:
        """
        Get aiogoogle-compatible ClientCreds from credentials.json file.
        
        Returns:
            ClientCreds object for use with aiogoogle
        """
        if not os.path.exists(CREDENTIALS_PATH):
            raise FileNotFoundError(
                f"Credentials file not found at {CREDENTIALS_PATH}. "
                "Please download it from Google Cloud Console."
            )
        
        try:
            with open(CREDENTIALS_PATH, 'r') as f:
                creds_data = json.load(f)
            
            # Handle both installed app and web app credential formats
            if 'installed' in creds_data:
                client_info = creds_data['installed']
            elif 'web' in creds_data:
                client_info = creds_data['web']
            else:
                raise ValueError("Invalid credentials.json format - missing 'installed' or 'web' section")
            
            client_creds_dict = {
                'client_id': client_info['client_id'],
                'client_secret': client_info['client_secret'],
                'scopes': SCOPES,
            }
            
            return ClientCreds(**client_creds_dict)
            
        except Exception as e:
            logger.error("Failed to load client credentials: %s", e)
            raise
    
    def invalidate_cache(self):
        """Invalidate cached credentials to force refresh."""
        self._credentials = None
        self.get_user_creds_for_aiogoogle.cache_clear()
        self.get_client_creds_for_aiogoogle.cache_clear()
        logger.info("Authentication cache invalidated")
    
    # Sync service builders
    @lru_cache(maxsize=4)
    def get_sync_service(self, service_name: str, version: str):
        """
        Get a synchronous Google API service.
        
        Args:
            service_name: Name of the Google service (e.g., 'gmail', 'calendar')
            version: API version (e.g., 'v1', 'v3')
            
        Returns:
            Google API service object
        """
        creds = self.get_credentials()
        return build(service_name, version, credentials=creds)
    
    def get_gmail_service(self):
        """Get Gmail API service."""
        return self.get_sync_service('gmail', 'v1')
    
    def get_calendar_service(self):
        """Get Calendar API service."""
        return self.get_sync_service('calendar', 'v3')
    
    def get_tasks_service(self):
        """Get Tasks API service."""
        return self.get_sync_service('tasks', 'v1')
    
    def get_drive_service(self):
        """Get Drive API service."""
        return self.get_sync_service('drive', 'v3')
    
    # Async service context managers
    @asynccontextmanager
    async def get_async_service(self, service_name: str, version: str):
        """
        Get an asynchronous Google API service context manager.
        
        Args:
            service_name: Name of the Google service
            version: API version
            
        Yields:
            Tuple of (aiogoogle instance, service)
        """
        user_creds = self.get_user_creds_for_aiogoogle()
        client_creds = self.get_client_creds_for_aiogoogle()
        
        async with Aiogoogle(user_creds=user_creds, client_creds=client_creds) as aiogoogle:
            service = await aiogoogle.discover(service_name, version)
            yield aiogoogle, service
    
    @asynccontextmanager
    async def get_async_gmail_service(self):
        """Get async Gmail service context manager."""
        async with self.get_async_service('gmail', 'v1') as (aiogoogle, service):
            yield aiogoogle, service
    
    @asynccontextmanager
    async def get_async_calendar_service(self):
        """Get async Calendar service context manager."""
        async with self.get_async_service('calendar', 'v3') as (aiogoogle, service):
            yield aiogoogle, service
    
    @asynccontextmanager
    async def get_async_tasks_service(self):
        """Get async Tasks service context manager."""
        async with self.get_async_service('tasks', 'v1') as (aiogoogle, service):
            yield aiogoogle, service
    
    @asynccontextmanager
    async def get_async_drive_service(self):
        """Get async Drive service context manager."""
        async with self.get_async_service('drive', 'v3') as (aiogoogle, service):
            yield aiogoogle, service


auth_manager = AuthManager()
