import asyncio
from typing import Optional
from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import ServiceAccountCreds, UserCreds
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from contextlib import asynccontextmanager
import os
import json
from functools import lru_cache

# Scopes for Google APIs
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/tasks",
]

TOKEN_PATH = r"C:\Users\dagms\Projects\Credentials\token.json"
CREDENTIALS_PATH = r"C:\Users\dagms\Projects\Credentials\credentials.json"


def get_sync_credentials():
    """Get synchronous credentials for compatibility."""
    creds = None
    
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=8080)
            
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
            
    return creds


@lru_cache(maxsize=1)
def get_user_creds():
    """Get aiogoogle-compatible user credentials."""
    sync_creds = get_sync_credentials()
    
    # Convert to aiogoogle UserCreds format
    creds_dict = {
        'access_token': sync_creds.token,
        'refresh_token': sync_creds.refresh_token,
        'token_uri': sync_creds.token_uri,
        'client_id': sync_creds.client_id,
        'client_secret': sync_creds.client_secret,
        'scopes': SCOPES
    }
    
    return UserCreds(**creds_dict)


@asynccontextmanager
async def get_async_calendar_service():
    """Async context manager for calendar service."""
    user_creds = get_user_creds()
    
    async with Aiogoogle(user_creds=user_creds) as aiogoogle:
        calendar_v3 = await aiogoogle.discover('calendar', 'v3')
        yield aiogoogle, calendar_v3


@asynccontextmanager
async def get_async_gmail_service():
    """Async context manager for Gmail service."""
    user_creds = get_user_creds()
    
    async with Aiogoogle(user_creds=user_creds) as aiogoogle:
        gmail_v1 = await aiogoogle.discover('gmail', 'v1')
        yield aiogoogle, gmail_v1


@asynccontextmanager
async def get_async_tasks_service():
    """Async context manager for Tasks service."""
    user_creds = get_user_creds()
    
    async with Aiogoogle(user_creds=user_creds) as aiogoogle:
        tasks_v1 = await aiogoogle.discover('tasks', 'v1')
        yield aiogoogle, tasks_v1


@asynccontextmanager
async def get_async_drive_service():
    """Async context manager for Drive service."""
    user_creds = get_user_creds()
    
    async with Aiogoogle(user_creds=user_creds) as aiogoogle:
        drive_v3 = await aiogoogle.discover('drive', 'v3')
        yield aiogoogle, drive_v3