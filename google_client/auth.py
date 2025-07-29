from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from functools import cache
import os


def get_credentials():
    scopes = [
        "https://www.googleapis.com/auth/calendar",
        "https://mail.google.com/",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/tasks",
        ]
    
    creds = None
    token_path = r"C:\Users\dagms\Projects\Credentials\token.json"
    credentials_path = r"C:\Users\dagms\Projects\Credentials\credentials.json"
    
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
def get_gmail_service():
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)

@cache
def get_calendar_service():
    creds = get_credentials()
    return build("calendar", "v3", credentials=creds)

def get_tasks_service():
    creds = get_credentials()
    return build("tasks", "v1", credentials=creds)

def get_drive_service():
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)

