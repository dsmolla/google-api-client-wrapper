import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow


class GoogleOAuthManager:
    """
    Manages authentication and credential storage for multiple users.

    Supports two authentication methods:
    1. Manual OAuth flow (production): generate_auth_url() + complete_auth_flow()
    2. Local server auth (development): authenticate_via_local_server()
    """

    def __init__(
            self,
            client_secrets_dict: dict,
            redirect_uri: str = 'http://localhost:8080',
    ):
        self.client_secrets_dict = client_secrets_dict
        self.redirect_uri = redirect_uri

    def _create_flow(self, scopes: list[str], state: str = None):
        flow = Flow.from_client_config(
            client_config=self.client_secrets_dict,
            scopes=scopes,
            redirect_uri=self.redirect_uri,
            state=state
        )
        return flow

    def generate_auth_url(self, scopes: list[str], state: str = None) -> tuple[str, str]:
        """
        Generate an OAuth2 authorization URL for user consent.

        Returns:
            Authorization URL string and the state
        """
        flow = self._create_flow(state=state, scopes=scopes)
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return auth_url, state

    def complete_auth_flow(self, code: str, scopes: list[str] = None) -> dict:
        """
        Complete the OAuth2 flow and obtain user credentials.

        Args:
            code: The authorization code from the OAuth callback
            scopes: List of OAuth scopes to request. If None, uses scopes from state.
        """
        flow = self._create_flow(scopes=scopes)
        flow.fetch_token(code=code)

        return json.loads(flow.credentials.to_json())

    def authenticate_via_local_server(
            self,
            scopes: list[str],
            port: int = 8080,
            open_browser: bool = True,
            timeout_seconds: int = 300,
            state: str = None
    ) -> dict:
        """
        NON-PRODUCTION USE ONLY: Authenticate using a local web server.

        This method starts a temporary local web server to handle the OAuth2 callback
        automatically. It is intended for development, testing, and local automation
        scripts only. DO NOT use in production environments.

        Args:
            scopes: List of OAuth scopes to request (e.g., [Scopes.GMAIL, Scopes.DRIVE])
            port: Port for local server (default: 8080). Must match your OAuth client config.
            open_browser: Whether to automatically open browser (default: True)
            timeout_seconds: Maximum time to wait for authorization (default: 300)
            state: Optional state parameter for CSRF protection

        Returns:
            dict: User credentials in JSON format, compatible with other auth methods

        Raises:
            TimeoutError: If user doesn't complete auth within timeout period
            RuntimeError: If server fails to start on specified port
            OSError: If the specified port is already in use

        Note:
            The redirect_uri specified in __init__ will be overridden to use
            http://localhost:{port} for this method. Ensure your Google Cloud
            Console OAuth2 client has http://localhost:{port} configured as an
            authorized redirect URI.
        """
        flow = InstalledAppFlow.from_client_config(
            client_config=self.client_secrets_dict,
            scopes=scopes,
            state=state
        )

        try:
            # Run local server to handle OAuth callback
            credentials = flow.run_local_server(
                port=port,
                open_browser=open_browser,
                timeout_seconds=timeout_seconds,
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent',

            )

            # Convert credentials to JSON format compatible with other methods
            return json.loads(credentials.to_json())

        except TimeoutError as e:
            raise TimeoutError(
                f"Authentication timed out after {timeout_seconds} seconds. "
                f"Please try again and complete the authorization process more quickly."
            ) from e
        except OSError as e:
            if "Address already in use" in str(e) or "WinError 10048" in str(e):
                raise RuntimeError(
                    f"Port {port} is already in use. Please specify a different port "
                    f"using the 'port' parameter, or stop the application using port {port}."
                ) from e
            raise

    @classmethod
    def refresh_user_token(
            cls,
            user_info: dict,
            scopes: list[str] = None
    ) -> dict:

        creds = Credentials.from_authorized_user_info(user_info, scopes=scopes)
        creds.refresh(Request())

        return json.loads(creds.to_json())


class Scopes:
    class Scopes:
        # Gmail scopes
        GMAIL = 'https://mail.google.com/'
        GMAIL_READONLY = 'https://www.googleapis.com/auth/gmail.readonly'
        GMAIL_SEND = 'https://www.googleapis.com/auth/gmail.send'
        GMAIL_COMPOSE = 'https://www.googleapis.com/auth/gmail.compose'
        GMAIL_INSERT = 'https://www.googleapis.com/auth/gmail.insert'
        GMAIL_LABELS = 'https://www.googleapis.com/auth/gmail.labels'
        GMAIL_MODIFY = 'https://www.googleapis.com/auth/gmail.modify'
        GMAIL_METADATA = 'https://www.googleapis.com/auth/gmail.metadata'
        GMAIL_SETTINGS_BASIC = 'https://www.googleapis.com/auth/gmail.settings.basic'
        GMAIL_SETTINGS_SHARING = 'https://www.googleapis.com/auth/gmail.settings.sharing'

        # Calendar scopes
        CALENDAR = 'https://www.googleapis.com/auth/calendar'
        CALENDAR_READONLY = 'https://www.googleapis.com/auth/calendar.readonly'
        CALENDAR_EVENTS = 'https://www.googleapis.com/auth/calendar.events'
        CALENDAR_EVENTS_READONLY = 'https://www.googleapis.com/auth/calendar.events.readonly'
        CALENDAR_SETTINGS_READONLY = 'https://www.googleapis.com/auth/calendar.settings.readonly'

        # Tasks scopes
        TASKS = 'https://www.googleapis.com/auth/tasks'
        TASKS_READONLY = 'https://www.googleapis.com/auth/tasks.readonly'

        # Drive scopes
        DRIVE = 'https://www.googleapis.com/auth/drive'
        DRIVE_READONLY = 'https://www.googleapis.com/auth/drive.readonly'
        DRIVE_FILE = 'https://www.googleapis.com/auth/drive.file'
        DRIVE_APPDATA = 'https://www.googleapis.com/auth/drive.appdata'
        DRIVE_METADATA = 'https://www.googleapis.com/auth/drive.metadata'
        DRIVE_METADATA_READONLY = 'https://www.googleapis.com/auth/drive.metadata.readonly'
        DRIVE_PHOTOS_READONLY = 'https://www.googleapis.com/auth/drive.photos.readonly'
        DRIVE_SCRIPTS = 'https://www.googleapis.com/auth/drive.scripts'

        # User info scopes
        USERINFO_EMAIL = 'https://www.googleapis.com/auth/userinfo.email'
        USERINFO_PROFILE = 'https://www.googleapis.com/auth/userinfo.profile'

