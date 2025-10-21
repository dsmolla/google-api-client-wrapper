
import json
import secrets

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow


class Scopes:
    GMAIL = 'https://mail.google.com/'
    CALENDAR = 'https://www.googleapis.com/auth/calendar'
    TASKS = 'https://www.googleapis.com/auth/tasks'
    DRIVE = 'https://www.googleapis.com/auth/drive'


class GoogleOAuthManager:
    """
    Manages authentication and credential storage for multiple users.
    """

    def __init__(
            self,
            client_secrets_dict: dict,
            scopes: list[str],
            redirect_uri: str,
            generate_random_state: bool = False
    ):
        self.client_secrets_dict = client_secrets_dict
        self.scopes = scopes
        self.redirect_uri = redirect_uri
        self.generate_random_state = generate_random_state

    def _create_flow(self, state: str = None):

        if state is None and self.generate_random_state:
            state = secrets.token_urlsafe(32)

        flow = Flow.from_client_config(
            client_config=self.client_secrets_dict,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri,
            state=state
        )
        return flow

    def generate_auth_url(self, state: str = None) -> tuple[str, str]:
        """
        Generate an OAuth2 authorization URL for user consent.

        Returns:
            Authorization URL string and the state
        """
        flow = self._create_flow(state=state)
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return auth_url, state

    def complete_auth_flow(self, code: str) -> dict:
        """
        Complete the OAuth2 flow and obtain user credentials.
        """
        flow = self._create_flow()
        flow.fetch_token(code=code)

        return json.loads(flow.credentials.to_json())

    @classmethod
    def refresh_user_token(
            cls,
            user_info: dict,
            scopes: list[str] = None
    ) -> dict:

        creds = Credentials.from_authorized_user_info(user_info, scopes=scopes)
        creds.refresh(Request())

        return json.loads(creds.to_json())

