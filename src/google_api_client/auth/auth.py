import os
from functools import cache

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/calendar',
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/tasks'
]
TOKEN_PATH = 'token.json'
CREDENTIALS_PATH = 'credentials.json'


def get_credentials_from_info(app_credentials: dict, user_token_data: dict=None, scopes: list=None):
    """
    Handle OAuth flow without file storage.

    Args:
        app_credentials (dict): OAuth client configuration (contents of credentials.json)
        user_token_data (dict, optional): Previously stored token data.
        scopes (list[str]): List of scopes to request

    Returns:
        tuple: (credentials, updated_token_data_to_store)
    """
    scopes = scopes or SCOPES
    creds = None

    # Try to load existing credentials from memory
    if user_token_data:
        creds = Credentials.from_authorized_user_info(user_token_data, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(app_credentials, scopes)
            creds = flow.run_local_server(port=8080)

    # Return credentials and token data to store
    token_data_to_store = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }

    return creds, token_data_to_store

def get_credentials_from_file(credentials_path: str=None, token_path: str=None, scopes: list=None):
    token_path = token_path or TOKEN_PATH
    credentials_path = credentials_path or CREDENTIALS_PATH
    scopes = scopes or SCOPES

    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, scopes
            )
            creds = flow.run_local_server(port=8080)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return creds


@cache
def get_gmail_service(credentials: Credentials):
    return build("gmail", "v1", credentials=credentials)

@cache
def get_calendar_service(credentials: Credentials):
    return build("calendar", "v3", credentials=credentials)

@cache
def get_tasks_service(credentials: Credentials):
    return build("tasks", "v1", credentials=credentials)

def get_service(service_name: str, version: str, credentials: Credentials):
    """
    Generic function to build any Google API service.
    
    Args:
        service_name: Name of the Google service (e.g., 'gmail', 'calendar', 'tasks')
        version: API version (e.g., 'v1', 'v3')
        credentials: Google OAuth2 credentials
        
    Returns:
        Google API service instance
    """
    return build(service_name, version, credentials=credentials)

